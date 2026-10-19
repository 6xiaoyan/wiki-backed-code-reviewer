"""
入口模块 — 启动代码合规审查流水线。

支持两种仓库来源：
  - 本地路径:    python -m code_checker.main
  - GitHub URL:  python -m code_checker.main https://github.com/owner/repo
                 python -m code_checker.main owner/repo

GitHub 模式需要设置个人访问令牌（只读权限即可）：
  $env:GITHUB_TOKEN = "ghp_xxxxxxxxxxxx"

降级模式:
  --offline    零 API 调用，只跑确定性检查 + format_fixer
  --strict     API 故障即 crash（CI 门禁用）

Usage:
    cd langgraph
    python -m code_checker.main [--offline|--strict] [repo_path_or_url]
"""

import os
import sys
import json
import re
import uuid
import datetime

# ── 项目根目录（langgraph/）──
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 确保上级目录在 Python 路径中，支持直接运行 main.py
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from code_checker.graph import app
from code_checker.config import (
    is_github_url, TRACES_DIR, llm_flash,
    set_degradation_mode, get_degradation_mode,
)
from code_checker.wiki_search import get_wiki_stats, get_wiki_log, clear_wiki_log
from code_checker.tracer import PipelineTracer, set_current_tracer
from code_checker.tools import (
    enrich_violations_from_wiki,
    get_contradiction_candidates,
    clear_contradiction_candidates,
)
from code_checker.wiki_arbitration import run_wiki_arbitration
from langchain_core.messages import HumanMessage
import threading

# ── 进程级运行锁：防止多个 pipeline 并发执行导致全局变量数据污染 ──
_run_lock = threading.Lock()

# ── Fix Patterns 路径 ──
_FIX_PATTERNS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rules-wiki", "fix-patterns")
_FIX_PATTERNS_RAW_DIR = os.path.join(_FIX_PATTERNS_DIR, "raw")
_FIX_PATTERNS_LOG_PATH = os.path.join(_FIX_PATTERNS_DIR, "log.md")
_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache", "violations")


def run(repo_path: str = None, degradation_mode: str = None) -> None:
    """
    执行完整的代码合规审查流程。

    Args:
        repo_path: 待审查的仓库路径。可以是本地目录或 GitHub URL。
                   默认 ../password-manager（相对于项目根）。
                   示例:
                     run()                                    # 本地默认
                     run("https://github.com/owner/repo")     # GitHub
                     run("owner/repo")                        # GitHub 简写
        degradation_mode: 降级模式覆盖。
                    "strict"  — 不降级，API 故障即 crash
                    "normal"  — LLM 阶段降级但继续（默认）
                    "offline" — 零 API 调用，只跑确定性检查
    """
    if repo_path is None:
        repo_path = os.path.join(_PROJECT_ROOT, "password-manager")

    # ── 进程级运行锁：拒绝并发执行，防止全局变量数据污染 ──
    if not _run_lock.acquire(blocking=False):
        raise RuntimeError(
            "另一个 pipeline 正在运行中。"
            "当前架构不支持同一进程内并发执行多个审查 pipeline"
            "（全局变量 _state_ref / _violations_buffers / _merged_buffer 等会相互污染）。"
            "请等待当前运行完成后再启动。"
        )

    try:
        _run_impl(repo_path, degradation_mode)
    finally:
        _run_lock.release()


def _run_impl(repo_path: str, degradation_mode: str | None) -> None:
    """run() 的实际实现。由 run() 在获取进程级锁后调用。"""
    # ── 应用降级模式覆盖 ──
    if degradation_mode:
        set_degradation_mode(degradation_mode)

    # ── 清空上一轮的 wiki 访问日志 ──
    clear_wiki_log()

    # ── 打印 wiki 统计 ──
    stats = get_wiki_stats()
    mode_label = "GitHub 远程扫描" if is_github_url(repo_path) else "本地扫描"
    mode = get_degradation_mode()
    if mode == "offline":
        mode_label += " | 🔒 离线模式"
    elif mode == "strict":
        mode_label += " | 🛡️ strict 模式"
    print("=" * 60)
    print(f"LangGraph 合规审查启动 ({mode_label})")
    print("=" * 60)
    print(f"  仓库: {repo_path}")
    print(f"  LLM Wiki: {stats['total_pages']} 页 ({', '.join(f'{d}({n})' for d, n in stats['domains'].items())})")
    print(f"  Wiki 日志: wiki_access.log")
    print()

    # ── 生成 run_id 并初始化全流程追踪器 ──
    run_id = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:8]
    tracer = PipelineTracer(run_id, TRACES_DIR)
    set_current_tracer(tracer)

    # ── 清空上轮遗留的矛盾候选 ──
    clear_contradiction_candidates()

    # ── 注入降级模式到初始 state ──
    result = app.invoke({
        "repo_path": repo_path,
        "run_id": run_id,
        "file_list": None,
        "file_contents": None,
        "cpp_violations": None,
        "qt_violations": None,
        "git_violations": None,
        "sqlite_violations": None,
        "refuted_violations": None,
        "merged_violations": None,
        "fix_plans": None,
        "fix_iteration": 0,
        "final_report": None,
        "messages": [],
        "degradation_log": [],
        "offline_mode": (mode == "offline"),
    })

    # ── Wiki 后处理：从 wiki 页面确定性提取 rule_clause（须先完成，会修改 result）──
    for key in ("merged_violations", "cpp_violations", "qt_violations",
                "sqlite_violations", "git_violations"):
        violations = result.get(key)
        if violations:
            result[key] = enrich_violations_from_wiki(violations)

    # ── 完成追踪 ──
    tracer.finish(result)
    set_current_tracer(None)

    # ── 收尾三步并行：fix_patterns / 矛盾候选 / wiki 仲裁（互不依赖，只读 result）──
    # wiki 仲裁门禁：运行不完整时跳过——不可在不可信数据上做规范冲突裁决
    from concurrent.futures import ThreadPoolExecutor, as_completed
    run_incomplete = result.get("run_incomplete", False)
    with ThreadPoolExecutor(max_workers=3) as executor:
        fut_patterns = executor.submit(_fix_patterns_after_run, result, run_id)
        fut_contra = executor.submit(_contradiction_candidates_after_run, result, run_id)
        if not run_incomplete:
            fut_arb = executor.submit(run_wiki_arbitration, result, run_id)
        else:
            fut_arb = None
            print("[main] ⚠️ 运行不完整，跳过 wiki 仲裁")
        new_patterns = fut_patterns.result()
        new_contradictions = fut_contra.result()
        arbitration = fut_arb.result() if fut_arb else None

    _print_summary(result, new_patterns, new_contradictions, arbitration)

    # ── 打印时间线摘要 ──
    print(tracer.timeline_summary())


def _fix_patterns_after_run(result: dict, run_id: str) -> list[str]:
    """流水线结束后，扫描需要多轮修复才通过的违规，自动生成 fix-pattern 草稿。

    触发条件：违规通过审查，但经历了 ≥2 轮 fix-review 迭代。

    Returns:
        生成的 raw 文件路径列表（供 _print_summary 提示用户审核）
    """
    fix_plans = result.get("fix_plans") or []
    violations = result.get("merged_violations") or []
    fix_iteration = result.get("fix_iteration", 0)

    if fix_iteration < 2:
        return []

    candidates = []
    for i, plan in enumerate(fix_plans):
        if plan is None:
            continue
        if plan.get("fix_status") != "passed":
            continue
        if i >= len(violations):
            continue

        # 从审查缓存读取尝试次数
        cache = _read_review_cache(i)
        if cache is None:
            continue
        attempts = cache.get("attempts", [])
        if len(attempts) < 2:
            continue  # 至少迭代 2 轮才算"难修"，值得沉淀记忆

        candidates.append({
            "idx": i,
            "violation": violations[i],
            "plan": plan,
            "cache": cache,
        })

    if not candidates:
        return []

    # ── 用 Flash 为每条候选生成草稿 ──
    generated = []
    for c in candidates:
        draft_md = _generate_pattern_draft(c, run_id)
        if not draft_md:
            continue
        filename = _write_pattern_draft(c, draft_md)
        if filename:
            generated.append(filename)

    return generated


def _read_review_cache(index: int) -> dict | None:
    """读取单条违规的审查缓存文件。"""
    path = os.path.join(_CACHE_DIR, f"{index}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return None


def _generate_pattern_draft(candidate: dict, run_id: str) -> str | None:
    """调用 Flash 模型，将违规 + 修复历史总结为 fix-pattern 草稿。

    Args:
        candidate: {idx, violation, plan, cache}
        run_id: 本次 run 标识

    Returns:
        markdown 格式的草稿内容，失败返回 None
    """
    v = candidate["violation"]
    plan = candidate["plan"]
    cache = candidate["cache"]

    # 构建 prompt
    rule_name = v.get("rule", "未知规则")
    file_name = os.path.basename(v.get("file", ""))
    current_code = v.get("current", "")[:800]
    expected_code = v.get("expected", "")[:800]
    reason = v.get("reason", "")[:500]

    # 修复历史摘要
    attempts_summary = []
    for a in cache.get("attempts", []):
        status = "✅ 通过" if a.get("passed") else f"❌ 驳回(score={a.get('score', '?')})"
        fb = (a.get("feedback") or "")[:200]
        suggestion = (a.get("suggestion") or "")[:200]
        attempts_summary.append(
            f"### 第 {a.get('iter', '?')} 轮 — {status}\n"
            f"- 修复前: `{a.get('fix_before', '')[:200]}`\n"
            f"- 修复后: `{a.get('fix_after', '')[:200]}`\n"
            f"- 审查意见: {fb}\n"
            f"- 修改建议: {suggestion}\n"
        )

    # 最终通过的修复
    final_fix = ""
    if plan.get("changes"):
        # PatchSet
        changes_desc = []
        for ch in plan["changes"][:5]:
            changes_desc.append(
                f"  - {ch.get('file', '')}: {ch.get('operation', '')} "
                f"`{ch.get('before', '')[:100]}` → `{ch.get('after', ch.get('code', ''))[:100]}`"
            )
        final_fix = "\n".join(changes_desc)
    else:
        final_fix = (
            f"  - 修复前: `{plan.get('fix_before', '')[:300]}`\n"
            f"  - 修复后: `{plan.get('fix_after', '')[:300]}`"
        )

    prompt = f"""你是一个技术文档撰写助手。请根据以下代码审查信息，生成一份**修复模式（fix-pattern）**文档。

生成的文档采用 Markdown 格式，结构如下：

---
title: {rule_name}
rule_id: fix-pattern/{_slugify(rule_name)}
priority: pattern
related_pages: []
---

# {rule_name}

## 关联规则
（从违规信息中提取涉及的规则名称）

## 代码特征
（描述什么代码模式会导致这个违规——让 fix_agent 能"按图索骥"识别同类问题）

## 修复步骤
（列出具体的修复步骤，按顺序编号，每一步有明确的代码改写指令）

## 来源
run: {run_id}, 迭代 {cache.get('attempts', [])[-1].get('iter', '?')} 轮, 最终 {cache['attempts'][-1].get('score', '?')}/10

---

=== 以下是输入信息 ===

**违规规则**: {rule_name}
**文件**: {file_name}
**严重度**: {v.get('severity', '')}
**违规原因**: {reason}
**当前代码**:
```
{current_code}
```
**期望代码**:
```
{expected_code}
```

**修复历史**（多轮迭代）:
{chr(10).join(attempts_summary)}

**最终通过的修复**:
{final_fix}

**审查通过理由**: {cache.get('attempts', [])[-1].get('feedback', '')[:300]}

---

请生成修复模式文档。要求：
1. 「代码特征」要足够具体，让 fix_agent 能通过关键词/代码模式匹配到同类问题
2. 「修复步骤」每一步都要是可执行的代码改写指令，不要模糊描述
3. 使用中文撰写
4. 只输出 markdown 文档本身，不要添加额外说明"""

    try:
        response = llm_flash.invoke([HumanMessage(content=prompt)])
        content = response.content.strip()
        # 去掉可能的 markdown 代码块包裹
        if content.startswith("```markdown"):
            content = content[len("```markdown"):].strip()
        if content.startswith("```"):
            content = content[3:].strip()
        if content.endswith("```"):
            content = content[:-3].strip()
        return content
    except Exception as e:
        print(f"  [fix-patterns] Flash 生成草稿失败 (idx={candidate['idx']}): {e}")
        return None


def _slugify(text: str) -> str:
    """将规则名转为 kebab-case slug。"""
    # 移除括号内容
    text = re.sub(r"[（(][^)）]*[)）]", "", text)
    # 非字母数字/中文 → -
    text = re.sub(r"[^\w一-鿿-]", "-", text).strip("-")
    # 合并连续 -
    text = re.sub(r"-{2,}", "-", text)
    return text.lower()[:60]


def _write_pattern_draft(candidate: dict, draft_md: str) -> str | None:
    """将 fix-pattern 草稿写入 raw/ 目录。

    Returns:
        文件名（不含路径），失败返回 None
    """
    v = candidate["violation"]
    rule_name = v.get("rule", "unknown")
    slug = _slugify(rule_name)

    # 确保 raw 目录存在
    os.makedirs(_FIX_PATTERNS_RAW_DIR, exist_ok=True)

    # 处理重名
    base = slug
    counter = 1
    while os.path.exists(os.path.join(_FIX_PATTERNS_RAW_DIR, f"{slug}.md")):
        slug = f"{base}-{counter}"
        counter += 1

    filepath = os.path.join(_FIX_PATTERNS_RAW_DIR, f"{slug}.md")
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(draft_md)
        # 追加到 log
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        log_entry = (
            f"| {timestamp} | 自动生成 | raw/{slug}.md | "
            f"来源 run, idx={candidate['idx']}, "
            f"规则: {rule_name} |\n"
        )
        with open(_FIX_PATTERNS_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(log_entry)
        return f"{slug}.md"
    except OSError as e:
        print(f"  [fix-patterns] 写入草稿失败: {e}")
        return None


def _contradiction_candidates_after_run(result: dict, run_id: str) -> int:
    """流水线结束后，收集 review_agent 标记的矛盾候选，对比已知矛盾表，
    生成 contradiction-candidates.md 供人工审核入库。

    Returns:
        新候选数量（排除已记录在 CONTRADICTIONS.md 中的已知矛盾）
    """
    candidates = get_contradiction_candidates()
    if not candidates:
        return 0

    # ── 加载已知矛盾表 ──
    contradictions_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "rules-wiki", "CONTRADICTIONS.md",
    )
    known_ids: set[str] = set()
    if os.path.exists(contradictions_path):
        try:
            with open(contradictions_path, "r", encoding="utf-8") as f:
                content = f.read()
            # 提取所有 CONTRADICTION-\d+ 标识
            import re as _re
            known_ids = set(_re.findall(r'CONTRADICTION-\d+', content))
        except Exception:
            pass

    # ── 去重：用描述文本的归一化哈希识别是否与已知矛盾相似 ──
    import hashlib
    known_sigs: set[str] = set()
    # 提取已知矛盾的关键词对
    _known_keywords = [
        ("camelCase", "snake_case", "测试"),
        ("Allman", "K&R", "大括号"),
        ("裸new", "父子模型", "Qt"),
        ("裸 new", "parent", "Qt"),
        ("noexcept", "throw"),
    ]
    for kw_set in _known_keywords:
        sig = "|".join(sorted(kw_set))
        known_sigs.add(hashlib.md5(sig.encode()).hexdigest()[:16])

    # ── 分类：新候选 vs 已知矛盾 ──
    new_candidates = []
    known_matches = []
    for c in candidates:
        desc_lower = c["description"].lower()
        # 简单关键词匹配判断是否已记录
        is_known = False
        for kw_set in _known_keywords:
            if all(kw.lower() in desc_lower for kw in kw_set):
                is_known = True
                break
        if is_known:
            known_matches.append(c)
        else:
            new_candidates.append(c)

    # ── 生成候选文件 ──
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
    os.makedirs(output_dir, exist_ok=True)
    candidates_path = os.path.join(output_dir, "contradiction-candidates.md")

    lines = [
        "# 规范矛盾候选（人工审核后入库）",
        "",
        f"**Run**: {run_id}",
        f"**日期**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**仓库**: {result.get('repo_path', '?')}",
        "",
        f"## 新候选（{len(new_candidates)} 条）— 需审核",
        "",
    ]

    if new_candidates:
        for i, c in enumerate(new_candidates):
            v = c.get("violation", {})
            lines.append(f"### 候选 #{i+1}: {c['description'][:120]}")
            lines.append("")
            lines.append(f"- **来源 finding**: idx={c['idx']}, {c.get('file', '?')}:{c.get('line', 0)}")
            lines.append(f"- **关联规则**: {v.get('rule', '?')}")
            lines.append(f"- **违规代码**: `{v.get('current', '?')[:200]}`")
            lines.append(f"- **修复后代码**: `{c.get('fix_after', '?')[:200]}`")
            lines.append(f"- **审查意见**: {c.get('feedback', '?')[:300]}")
            lines.append("")
            lines.append("**审核操作**:")
            lines.append("1. 确认矛盾真实存在")
            lines.append("2. 确定裁决方向（哪条规范优先）")
            lines.append(f"3. 在 `rules-wiki/CONTRADICTIONS.md` 中添加 `CONTRADICTION-{len(known_ids)+i+1:03d}` 条目")
            lines.append("4. 运行 wiki 仲裁（或手动修改受影响的 wiki 页面）")
            lines.append("5. 删除本文件或标记为已处理")
            lines.append("")
    else:
        lines.append("（本次 run 未发现新的规范矛盾候选）")
        lines.append("")

    if known_matches:
        lines.append(f"## 已知矛盾匹配（{len(known_matches)} 条）— 已记录，无需处理")
        lines.append("")
        for i, c in enumerate(known_matches):
            lines.append(f"- #{c['idx']}: {c['description'][:150]}")
        lines.append("")

    try:
        with open(candidates_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except OSError:
        pass

    return len(new_candidates)


def _print_summary(
    result: dict,
    new_patterns: list[str] | None = None,
    new_contradictions: int = 0,
    arbitration: dict | None = None,
) -> None:
    """打印审查摘要到控制台。"""
    violations = result.get("merged_violations") or []
    fix_plans = result.get("fix_plans") or []
    refuted_violations = result.get("refuted_violations") or []
    fact_refuted = len(refuted_violations)

    crit = sum(1 for v in violations if v.get("severity") == "critical")
    warn = sum(1 for v in violations if v.get("severity") == "warning")
    sugg = sum(1 for v in violations if v.get("severity") == "suggestion")
    info = sum(1 for v in violations if v.get("severity") == "info")
    infra_fp = sum(1 for p in fix_plans if p is not None and p.get("fix_status") == "infra")

    passed = sum(1 for p in fix_plans if p is not None and p.get("fix_status") == "passed")
    failed = sum(1 for p in fix_plans if p is not None and p.get("fix_status") == "failed")
    refuted = sum(1 for p in fix_plans if p is not None and p.get("fix_status") == "refuted")
    unreviewed = sum(1 for p in fix_plans if p is not None and p.get("fix_status") == "unreviewed")
    unresolved = sum(1 for p in fix_plans if p is not None and p.get("fix_status") == "unresolved")
    proposed = sum(1 for p in fix_plans if p is not None and p.get("fix_status") == "proposed")
    null_plans = sum(1 for p in fix_plans if p is None)
    valid_plans = sum(1 for p in fix_plans if p is not None)

    # ── Wiki 访问统计 ──
    wiki_log = get_wiki_log()
    wiki_searches = [e for e in wiki_log if e["action"] == "search"]
    wiki_pages = [e for e in wiki_log if e["action"] == "get_page"]

    print(f"\n{'=' * 60}")
    print("  审查摘要")
    print(f"{'=' * 60}")
    severity_parts = [f"Critical {crit}", f"Warning {warn}", f"Suggestion {sugg}"]
    if info:
        severity_parts.append(f"Info {info}")
    print(f"  违规: {len(violations)} ({', '.join(severity_parts)})")
    print(f"  修复方案: {valid_plans}条")
    print(f"  审查通过: {passed}/{valid_plans} (迭代{result.get('fix_iteration', 0)}次)")
    if refuted:
        print(f"  🚨 幻觉驳回: {refuted}条 — checker agent 声称的代码结构在源文件中不存在")
    if fact_refuted:
        print(f"  🚨 事实核验驳回: {fact_refuted}条 — 合并前发现声称代码与源文件不匹配，已拦截")
    if failed:
        print(f"  ❌ 未通过: {failed}条，需人工复核")
    if infra_fp:
        print(f"  🔧 基础设施: {infra_fp}条 — 非代码编辑工具能修（Git/流程类），需人工处理")
    if unreviewed:
        print(f"  ⚠️ 审查不可用: {unreviewed}条 — review_agent 因 API 故障未能执行，需人工验证")
    if unresolved:
        print(f"  ⚠️ 无法修复: {unresolved}条 — LLM 无法生成修复方案，需人工处理")
    if proposed:
        print(f"  ⚠️ 未审查: {proposed}条 — 修复方案已产出但审查未执行，运行异常")
    if null_plans:
        print(f"  ⚠️ 无方案: {null_plans}条 — fix_agent 未产出修复方案，运行不完整")

    # ── 完整性门禁 ──
    is_incomplete = bool(unreviewed or proposed or null_plans)
    if is_incomplete:
        print(f"\n  ⚠️⚠️ 运行不完整 ⚠️⚠️")
        issues = []
        if unreviewed:
            issues.append(f"{unreviewed}条审查不可用")
        if proposed:
            issues.append(f"{proposed}条未审查")
        if null_plans:
            issues.append(f"{null_plans}条无方案")
        print(f"  原因: {', '.join(issues)}")
        print("  不可声称'已通过'——请人工验证后手动确认")

    # ── Wiki 查阅统计 ──
    if wiki_log:
        print(f"\n  Wiki 查阅: {len(wiki_log)} 次")
        print(f"    搜索: {len(wiki_searches)} 次 | 读页: {len(wiki_pages)} 次")
        # 按 agent 分组统计
        agent_counts = {}
        for e in wiki_log:
            a = e.get("agent", "unknown")
            agent_counts[a] = agent_counts.get(a, 0) + 1
        for agent, count in sorted(agent_counts.items()):
            print(f"      {agent}: {count} 次")
        print(f"  详细日志: wiki_access.log")

    report_path = os.path.join(os.getcwd(), "compliance_report.md")
    print(f"\n  完整报告: {report_path}")

    # ── 矛盾候选提示 ──
    if new_contradictions > 0:
        candidates_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            ".cache", "contradiction-candidates.md",
        )
        print(f"\n  📋 规范矛盾候选: {new_contradictions} 条新候选")
        print(f"     审核文件: {candidates_path}")
        print(f"     审核后 → 更新 rules-wiki/CONTRADICTIONS.md")
        print(f"           → 或运行 wiki 仲裁自动生成规则修改建议")

    # ── Wiki 仲裁提示 ──
    if arbitration and arbitration.get("report_path"):
        ar = arbitration
        print(f"\n  ⚖️  Wiki 仲裁报告:")
        print(f"     规则修改建议: {ar.get('changes_proposed', 0)} 条")
        print(f"     确认真实冲突: {ar.get('contradictions_confirmed', 0)} 条")
        print(f"     排除非冲突: {ar.get('contradictions_false_alarm', 0)} 条")
        print(f"     报告文件: {ar['report_path']}")
        print(f"  ⚠️  请人工审核报告后，手动应用 wiki 变更。")

    # ── Fix Patterns 提示 ──
    if new_patterns:
        raw_dir = _FIX_PATTERNS_RAW_DIR
        print(f"\n  📝 Fix Patterns: 本次 run 产生 {len(new_patterns)} 条修复模式草稿:")
        for p in new_patterns:
            print(f"     raw/{p}")
        print(f"  ⚠️  请审核草稿后移动到 {_FIX_PATTERNS_DIR}/ 正式目录方可被 fix_agent 检索。")


# ── 直接运行 ──
if __name__ == "__main__":
    # 解析命令行参数
    #   python -m code_checker.main [--offline|--strict] [repo_path_or_url]
    #   python -m code_checker.main pr <analyze|publish|local> ...   # PR 模式新入口
    args = sys.argv[1:]

    # PR 模式子入口：保留本地旧入口不变，PR 相关逻辑在独立模块中
    if args and args[0] == "pr":
        from code_checker.pr_review.cli import main as pr_main

        sys.exit(pr_main(args[1:]))

    mode_override = None
    repo = None

    for arg in args:
        if arg == "--offline":
            mode_override = "offline"
        elif arg == "--strict":
            mode_override = "strict"
        elif not arg.startswith("--"):
            repo = arg

    run(repo, degradation_mode=mode_override)
