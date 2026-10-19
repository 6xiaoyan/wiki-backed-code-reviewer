"""
Agent 共享工具模块。

所有 checker/fixer/reviewer agent 的工具函数集中定义在此。
每个工具通过 @tool 装饰器注册，供 create_react_agent 使用。

状态访问：工具通过模块级 _state_ref 访问 AgentState（由节点函数在调用 agent 前设置）。
违规/修复方案通过模块级列表累积，节点函数在 agent 运行后取出。
"""

import os
import re
import json
import subprocess
import threading
from typing import Optional

from langchain_core.tools import tool

from code_checker.config import (
    CXX_EXTENSIONS, QT_SPECIAL_EXTENSIONS, QT_MARKERS, SQLITE_MARKERS,
    VALID_COMMIT_TYPES, COMMIT_MESSAGE_RE, SEVERITY_ORDER,
    CPP_RULES_FILE, QT_RULES_FILE, SQLITE_RULES_FILE,
    filter_rules_by_phase,
)
from code_checker.utils import read_rules_file, enrich_violation_context
from code_checker.wiki_search import (
    search_wiki_pages, get_wiki_page as _get_wiki_page_raw, get_related_pages, list_domain_pages,
    get_wiki_stats, get_wiki_log, clear_wiki_log,
)

# ============================================================================
# 模块级状态引用（由节点函数在调用前设置）
# ============================================================================
_state_ref: Optional[dict] = None
"""当前 AgentState 的引用，工具通过此引用读取共享状态。"""

# 共享累积列表（线程安全）
# ── 按 checker domain 隔离的违规缓冲区 ──
# 四个 checker agent（cpp/qt/sqlite/git）在同一个进程中运行，
# 共享 _violations_buffer 会导致跨 checker 数据污染：
#   - 任一路 set_state() 清空全局缓冲 → 其他路的违规丢失或混杂
#   - 任一路 get_violations_buffer() 复制当时的全部内容 → 重复计数
# 修复：每个 checker domain 独立缓冲区，report_violation 按 domain 路由。
_violations_buffers: dict[str, list[dict]] = {}
"""按 checker domain（cpp/qt/sqlite/git）隔离的违规累积缓冲区。"""

_fix_plans_buffer: list[dict] = []
"""Fix agent 累积的修复方案列表。"""

_buffer_lock = threading.Lock()
"""保护 _violations_buffers 和 _fix_plans_buffer 的线程锁。"""

# ============================================================================
# PR 模式工具权限
# ============================================================================
_pr_mode = False
"""PR 模式标记。开启后，全仓/写操作工具在入口直接拒绝调用。"""

_PR_FORBIDDEN_TOOLS = frozenset({
    "run_git_log",       # 只应检查 PR 提交范围，不允许全仓最近 N 条
    "propose_fix",       # PR 模式不自动修复
    "propose_patchset",  # PR 模式不自动修复
    "submit_review",     # PR 模式不运行 fix/review 循环
})

#: PR 模式允许的工具面：读固定快照、搜索、查可信 Wiki、提交结构化问题。
#: 不包含 shell、网络、写规则/skill、GitHub 发布接口。
PR_MODE_ALLOWED_TOOLS = frozenset({
    "read_file",
    "search_in_file",
    "list_files",
    "report_violation",
    "search_wiki",
    "get_wiki_page",
    "get_rules_text",
})


def set_pr_mode(enabled: bool = True) -> None:
    """开启/关闭 PR 模式。由 PR 入口在运行前调用。"""
    global _pr_mode
    _pr_mode = bool(enabled)


def is_pr_mode() -> bool:
    return _pr_mode


def assert_tool_allowed(tool_name: str) -> str | None:
    """PR 模式的工具权限校验。返回 None 表示允许，否则返回拒绝原因。

    代码注释、PR 描述与模型输出不能改变这里的结果。
    """
    if _pr_mode and tool_name in _PR_FORBIDDEN_TOOLS:
        return (
            f"❌ PR 模式工具约束：'{tool_name}' 不可用。"
            f"PR 模式只允许读取固定快照、搜索代码、查询可信 Wiki 与提交结构化问题。"
        )
    return None


def _get_checker_domain() -> str:
    """从当前线程的 agent_name 推断 checker domain。

    线程 agent_name 示例:
      - 主线程（_traced 包装器设置）: "cpp_agent", "qt_agent"
      - 工作线程（_run_single_file 设置）: "cpp_agent/file1", "sqlite_agent/file3"
      - tracer span: "cpp_agent", "qt_agent"

    从 agent_name 提取 domain: cpp / qt / sqlite / git。
    """
    name = _get_agent_name()
    for domain in ("cpp", "qt", "sqlite", "git"):
        if domain in name:
            return domain
    # fallback: 如果 agent_name 不包含已知 domain，检查 tracer
    from code_checker.tracer import _current_tracer
    if _current_tracer and _current_tracer._current_node:
        node = _current_tracer._current_node
        for domain in ("cpp", "qt", "sqlite", "git"):
            if domain in node:
                return domain
    return "unknown"

_thread_local = threading.local()
"""线程局部存储，每个 chunk 线程独立维护自己的 allowed_indices。"""


def set_agent_name(name: str) -> None:
    """设置当前线程的 agent 名称，供 wiki 日志追溯。"""
    _thread_local.agent_name = name


def _get_agent_name() -> str:
    """获取当前线程的 agent 名称。

    优先级:
      1. thread_local（由 set_agent_name 显式设置）
      2. 当前活跃 tracer span 的 node_name（由 _traced 自动设置）
      3. "unknown"
    """
    name = getattr(_thread_local, "agent_name", "")
    if name:
        return name
    # 回退：从 tracer 的当前 span 推断
    from code_checker.tracer import _current_tracer
    if _current_tracer and _current_tracer._current_node:
        return _current_tracer._current_node
    return "unknown"


def _lookup_violation_id(idx: int) -> str:
    """从 merged_violations 中查找指定 idx 的 violation_id。"""
    if _state_ref is None:
        return ""
    violations = _state_ref.get("merged_violations") or []
    if 0 <= idx < len(violations):
        v = violations[idx]
        if v is not None:
            return v.get("violation_id", "")
    return ""

# ── 修复遥测（per-idx 工具调用追踪）──
_fix_telemetry: dict[int, dict] = {}
"""idx → {called_get_detail, called_propose, propose_tool, propose_result}"""
_telemetry_lock = threading.Lock()
"""保护 _fix_telemetry 的锁。"""

# ── 跨 idx 重复检测（防止模型将同一修复套用到不相关违规）──
_fix_content_tracker: dict[int, str] = {}
"""idx → content_signature，追踪本轮已提交的修复内容"""
_fix_content_lock = threading.Lock()
"""保护 _fix_content_tracker 的锁。"""


# ── 规范矛盾候选累加器 ──
_contradiction_candidates: list[dict] = []
"""每次 run 中 review_agent 检测到的规范矛盾候选。"""
_contradiction_lock = threading.Lock()
"""保护 _contradiction_candidates 的锁。"""


def get_contradiction_candidates() -> list[dict]:
    """获取本次 run 中检测到的所有规范矛盾候选。"""
    with _contradiction_lock:
        return list(_contradiction_candidates)


def clear_contradiction_candidates() -> None:
    """清空矛盾候选累加器（每次 run 前调用）。"""
    global _contradiction_candidates
    with _contradiction_lock:
        _contradiction_candidates = []


def clear_fix_telemetry() -> None:
    """清空修复遥测 + 跨 idx 重复检测器（每次 fix_agent 运行前调用）。"""
    global _fix_telemetry, _fix_content_tracker
    with _telemetry_lock:
        _fix_telemetry = {}
    with _fix_content_lock:
        _fix_content_tracker = {}


def get_fix_telemetry() -> dict[int, dict]:
    """获取修复遥测快照。"""
    with _telemetry_lock:
        return dict(_fix_telemetry)


def _record_telemetry(idx: int, field: str, value) -> None:
    """线程安全地记录单条遥测。"""
    with _telemetry_lock:
        if idx not in _fix_telemetry:
            _fix_telemetry[idx] = {
                "called_get_detail": False,
                "called_propose": False,
                "propose_tool": None,
                "propose_result": None,
            }
        _fix_telemetry[idx][field] = value


def _make_fix_signature(fix_before: str = "", fix_after: str = "",
                        changes: list[dict] | None = None) -> str:
    """生成修复内容签名，用于跨 idx 重复检测。

    对 propose_fix：基于 (before, after) 的归一化哈希
    对 propose_patchset：基于 (文件列表, 操作列表) 的归一化哈希
    """
    import hashlib
    if changes:
        # PatchSet: 签名 = 文件列表 + 操作类型 + 首条 before/after 摘要
        parts = []
        for ch in changes[:8]:  # 最多取前 8 条 change
            f = os.path.basename(ch.get("file", "") or "")
            op = ch.get("operation", "") or ""
            b = (ch.get("before") or "")[:200].strip()
            a = (ch.get("after") or ch.get("code") or "")[:200].strip()
            parts.append(f"{f}|{op}|{b}|{a}")
        raw = "||".join(parts)
    else:
        b = (fix_before or "")[:500].strip()
        a = (fix_after or "")[:500].strip()
        raw = f"{b}|||{a}"
    return hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()[:32]


def _check_cross_idx_duplicate(idx: int, fix_before: str = "", fix_after: str = "",
                                changes: list[dict] | None = None) -> str | None:
    """检测同一修复是否被错误复用到不同违规类型上。

    如果为 idx=X 提交的修复与 idx=Y 完全一致，但违规 X 和 Y 的规则不同且文件不同，
    则拒绝提交（模型在复制作弊）。
    """
    violations = (_state_ref or {}).get("merged_violations") or []
    current_rule = ""
    current_file = ""
    if 0 <= idx < len(violations):
        current_rule = (violations[idx].get("rule") or "").strip()
        current_file = (violations[idx].get("file") or "").strip()

    sig = _make_fix_signature(fix_before, fix_after, changes)

    with _fix_content_lock:
        for existing_idx, existing_sig in _fix_content_tracker.items():
            if existing_sig != sig or existing_idx == idx:
                continue
            # 相同签名 → 检查是否违规类型也不同
            existing_rule = ""
            existing_file = ""
            if 0 <= existing_idx < len(violations):
                existing_rule = (violations[existing_idx].get("rule") or "").strip()
                existing_file = (violations[existing_idx].get("file") or "").strip()

            # 规则不同 + 文件不同 → 几乎不可能是正确修复
            if current_rule and existing_rule and current_rule != existing_rule:
                if current_file != existing_file:
                    return (
                        f"❌ 跨 idx 重复检测：相同的修复内容已被提交给 "
                        f"idx={existing_idx}（规则: '{existing_rule}', "
                        f"文件: {os.path.basename(existing_file)}），"
                        f"但你正在为 idx={idx}（规则: '{current_rule}', "
                        f"文件: {os.path.basename(current_file)}）提交完全相同修复。\n"
                        f"这两个违规的规则和文件都不同，不可能用同一修复解决。\n"
                        f"请为 idx={idx} 生成针对 '{current_rule}' 规则的专门修复方案，"
                        f"不要复用 idx={existing_idx} 的修复内容。"
                    )
                # 规则不同但同一文件 → 警告但仍允许（可能跨规则修复）
                print(f"  [cross_idx] ⚠️ idx={idx} 与 idx={existing_idx} 修复相同"
                      f"（规则不同但同文件，放行）")

        # 记录本次签名
        _fix_content_tracker[idx] = sig

    return None


def set_allowed_indices(indices: set[int] | None) -> None:
    """设置当前线程允许操作的违规索引集合。

    每个 chunk 线程在启动时调用，工具函数据此硬编码拒绝越界操作。
    传入 None 清除限制（checker agent 不需要此限制）。
    """
    _thread_local.allowed_indices = indices


def _check_idx_allowed(idx: int) -> str | None:
    """校验 idx 是否在当前线程的允许范围内。返回 None 表示通过，否则返回错误消息。"""
    allowed = getattr(_thread_local, "allowed_indices", None)
    if allowed is not None and idx not in allowed:
        return (
            f"❌ 硬约束拒绝：idx={idx} 不在你的处理范围内。"
            f"你只能处理以下索引：{sorted(allowed)}"
        )
    return None


def set_state(state: dict) -> None:
    """节点函数在调用 agent 前设置当前状态引用。

    只清空当前 checker domain 的违规缓冲区，不影响其他并行 checker。
    """
    global _state_ref, _fix_plans_buffer
    domain = _get_checker_domain()
    with _buffer_lock:
        _state_ref = state
        _violations_buffers[domain] = []
        _fix_plans_buffer = []


def get_violations_buffer() -> list[dict]:
    """节点函数在 agent 运行后取出当前 checker domain 累积的违规。

    只返回当前 domain 的违规，不会混入其他并行 checker 的结果。
    """
    domain = _get_checker_domain()
    with _buffer_lock:
        return list(_violations_buffers.get(domain, []))


def get_fix_plans_buffer() -> list[dict]:
    """节点函数在 agent 运行后取出累积的修复方案（线程安全）。"""
    with _buffer_lock:
        return list(_fix_plans_buffer)


# ============================================================================
# 本地审查缓存（直接 JSON 读写，不做 pipeline）
# ============================================================================

_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache", "violations")


def _ensure_cache_dir() -> None:
    os.makedirs(_CACHE_DIR, exist_ok=True)


def _cache_path(index: int) -> str:
    return os.path.join(_CACHE_DIR, f"{index}.json")


def _read_review_cache(index: int) -> dict | None:
    """读单条违规的审查缓存。不存在或已通过返回 None。"""
    path = _cache_path(index)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
    if data.get("passed"):
        return None
    return data


def _write_review_cache(
    index: int, plan: dict, score: int, passed: bool,
    feedback: str, suggestion: str, rule_snippet: str, scoring_criteria: str,
) -> None:
    """写审查结果到本地 JSON。合并已有记录，追加本次尝试。"""
    _ensure_cache_dir()
    path = _cache_path(index)

    # 读已有缓存
    data = _read_review_cache(index)
    if data is None:
        # 新建
        violations = (_state_ref or {}).get("merged_violations") or []
        v = violations[index] if index < len(violations) else {}
        data = {
            "index": index,
            "file": v.get("file", ""),
            "line": v.get("line", 0),
            "rule_name": v.get("rule", ""),
            "severity": v.get("severity", ""),
            "current_code": v.get("current", ""),
            "expected": v.get("expected", ""),
            "reason": v.get("reason", ""),
            "rule_snippet": rule_snippet or "",
            "scoring_criteria": scoring_criteria or "",
            "attempts": [],
            "passed": False,
        }

    # 追加本次尝试
    attempt = {
        "iter": len(data["attempts"]) + 1,
        "fix_before": plan.get("fix_before", "")[:500],
        "fix_after": plan.get("fix_after", "")[:500],
        "score": score,
        "passed": passed,
        "feedback": feedback[:300],
        "suggestion": suggestion[:300],
    }
    data["attempts"].append(attempt)
    data["passed"] = passed

    # 首次有 scoring_criteria 就记录
    if scoring_criteria and not data.get("scoring_criteria"):
        data["scoring_criteria"] = scoring_criteria

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ============================================================================
# 通用工具（所有 agent 可用）
# ============================================================================


def _record_file_read(path: str, content: str) -> None:
    """记录一次文件读取到 per-agent ReadFileTracker。读取失败不记录。"""
    try:
        from code_checker.context_compaction import get_tracker
        agent_name = _get_agent_name()
        tracker = get_tracker(agent_name)
        if tracker:
            tracker.record_read(path, content)
    except Exception:
        pass  # tracker 记录失败不影响主流程


@tool
def read_file(file_path: str) -> str:
    """读取源文件内容。

    Args:
        file_path: 文件的绝对路径。如果只给文件名，会在 repo 中搜索。
    """
    if _state_ref is None:
        return "错误：状态未初始化"

    file_contents = _state_ref.get("file_contents") or {}
    # 尝试精确匹配
    if file_path in file_contents:
        content = file_contents[file_path]
        _record_file_read(file_path, content)
        return content

    # 尝试文件名匹配
    for fp in file_contents:
        if os.path.basename(fp) == file_path:
            content = file_contents[fp]
            _record_file_read(fp, content)
            return content
        if file_path in fp:
            content = file_contents[fp]
            _record_file_read(fp, content)
            return content

    return f"文件未找到: {file_path}\n可用文件: {list(file_contents.keys())[:20]}"


@tool
def search_in_file(file_path: str, pattern: str) -> list[dict]:
    """在文件中用正则表达式搜索，返回匹配行及行号。

    Args:
        file_path: 文件路径（绝对路径或文件名）
        pattern: 正则表达式模式（Python re 语法）
    """
    content = read_file.invoke({"file_path": file_path})
    if content.startswith("错误") or content.startswith("文件未找到"):
        return [{"error": content}]

    results = []
    try:
        pat = re.compile(pattern)
    except re.error as e:
        return [{"error": f"正则表达式错误: {e}"}]

    for i, line in enumerate(content.split("\n"), 1):
        if pat.search(line):
            results.append({
                "line": i,
                "content": line.rstrip("\r"),
            })

    return results


@tool
def list_files() -> list[str]:
    """列出项目中所有 C++ 源代码文件的绝对路径。"""
    if _state_ref is None:
        return []
    file_list = _state_ref.get("file_list") or []
    return file_list


@tool
def report_violation(
    file: str, line: int, rule: str, severity: str,
    current: str, expected: str, reason: str,
    rule_section: str = "",
    rule_excerpt: str = "",
    rule_page: str = "",
) -> str:
    """报告一条违规项。对每条发现的违规调用一次。

    Args:
        file: 文件路径
        line: 行号
        rule: 违规的规范条款名称（建议带 § 章节号，如 "§1.1 命名约定"）
        severity: critical / warning / suggestion / info
                 info = 仅用于报告展示，不进入 fix/review 流程（如 Git 提交格式问题）
        current: 违规的当前代码
        expected: 期望的正确代码
        reason: 为什么这是违规
        rule_section: 【重要】对应规范文件的章节标题，如 "## 7. 禁止模式" 或 "### 1.1 命名约定"。
                      从你读过的 get_rules_text 返回内容中精确复制。
        rule_excerpt: 【重要】规范文件中与该违规直接相关的条款原文摘录（2-5 句即可）。
                      从你读过的 get_rules_text 返回内容中精确复制，包含正确/错误示例更佳。
                      这会被 fix_agent 和 review_agent 直接使用，不再重复查规范。
        rule_page: 【Wiki 模式】LLM Wiki 页面路径，如 "cpp/naming-classes"、"qt/braces-knr"。
                   系统会从此页面确定性提取 rule_clause 条款原文，消除 LLM 摘录偏差。
    """
    if severity not in ("critical", "warning", "suggestion", "info"):
        return f"严重度 '{severity}' 无效，必须是 critical/warning/suggestion/info"

    violation = {
        "file": file,
        "line": line,
        "rule": rule,
        "severity": severity,
        "current": current,
        "expected": expected,
        "reason": reason,
        "source": "",  # 由调用方设置
        "rule_section": rule_section,
        "rule_excerpt": rule_excerpt,
        "rule_page": rule_page,
    }

    # 补充上下文
    if _state_ref:
        enrich_violation_context(violation, _state_ref.get("file_contents") or {})

    # ── 按 domain 隔离追加违规 ──
    domain = _get_checker_domain()
    with _buffer_lock:
        if domain not in _violations_buffers:
            _violations_buffers[domain] = []
        _violations_buffers[domain].append(violation)
        # idx 在锁内计算：防止两个线程同时 append 后读到相同的 len，
        # 生成重复或错误归属的追踪编号
        idx = len(_violations_buffers[domain]) - 1

    # ── 可观测性：记录违规发现事件 ──
    from code_checker.tracer import get_current_tracer
    tracer = get_current_tracer()
    if tracer:
        agent_name = _get_agent_name()
        violation["violation_id"] = tracer.record_violation(
            violation, agent_name, idx,
        )

    return f"违规已记录: [{severity}] {rule} @ {os.path.basename(file)}:{line}"


@tool
def get_rules_text(checker_name: str, phase: str = "checker") -> str:
    """获取指定规范文件的文本，支持按阶段裁剪。

    Args:
        checker_name: cpp / qt / sqlite
        phase: checker (默认, 自动裁剪非检查章节) /
               fix (返回完整规范——但 fix_agent 不应调用此工具) /
               review (返回完整规范——但 review_agent 不应调用此工具)

    注意：fix_agent 和 review_agent 不应使用此工具。
    它们通过 get_violation_detail / get_pending_fixes 获得精确规则注入。
    """
    rule_files = {
        "cpp": CPP_RULES_FILE,
        "qt": QT_RULES_FILE,
        "sqlite": SQLITE_RULES_FILE,
    }
    path = rule_files.get(checker_name, "")
    if not path:
        return f"未知规范: {checker_name}，可选: cpp/qt/sqlite"
    try:
        full_text = read_rules_file(path)
        return filter_rules_by_phase(full_text, checker_name, phase)
    except Exception:
        return f"无法读取规范文件: {path}"


# ============================================================================
# Wiki 检索工具（Agent 查阅 LLM Wiki 规则库）
# ============================================================================

@tool
def search_wiki(query: str, domain: str = "") -> str:
    """在 LLM Wiki 规则库中搜索规则页面。返回匹配页面的标题、摘要和相关度评分。

    Wiki 包含 199 条独立可检查的规则页面，涵盖 7 个域：
      cpp (72) / qt (51) / sqlite (5) / git (4)  ← 公司主规则
      tencent (49) / qt-wiki (8) / google (10)    ← 副规则对照

    使用场景：
    - 需要深入了解某条规则的具体条款、正确/错误示例、检查方法时
    - 需要查看副规则（Google/Qt Coding/腾讯安全）的冲突说明时
    - 需要找到某条违规的修复指南和审查清单时

    Args:
        query: 搜索关键词，如 "命名约定"、"camelCase"、"大括号 K&R"、"SQLite PRAGMA"
        domain: 限制域，如 "cpp"、"qt"、"tencent"；留空搜索全部
    """
    if not query.strip():
        return "错误：query 不能为空。请提供搜索关键词，如 '命名约定'、'include 顺序'、'大括号'"

    agent_name = _get_agent_name()

    result = search_wiki_pages(query, domain=domain, agent_name=agent_name, max_results=8)
    matches = result.get("matches", [])

    if not matches:
        domains_hint = ""
        if not domain:
            domains_hint = "。可用域: cpp, qt, sqlite, git, tencent, qt-wiki, google"
        return f"未找到与 '{query}' 匹配的 wiki 页面{domains_hint}。请尝试不同的关键词或更宽泛的查询。"

    lines = [f"搜索 '{query}'（{result['domain']}域）：找到 {result['total']} 个匹配，显示前 {len(matches)} 个：\n"]
    for i, m in enumerate(matches):
        lines.append(
            f"{i+1}. **{m['title']}** (`{m['slug']}`)\n"
            f"   域: {m['domain']} | 优先级: {m['priority']} | 检查: {m['check_method']}\n"
            f"   摘要: {m['snippet']}\n"
        )
    return "\n".join(lines)


@tool
def get_wiki_page(slug: str) -> str:
    """读取指定 LLM Wiki 页面的完整内容。

    页面包含：规则条款原文、正确/错误代码示例、检查方法（正则/LM）、
    修复指南、审查清单、关联页面链接、冲突说明（副规则页面）。

    Args:
        slug: 页面标识，如 "cpp/naming-classes"、"qt/braces-knr"、"tencent/no-oob-write"
              支持短名（如 "naming-classes"），系统会自动查找
    """
    if not slug.strip():
        return "错误：slug 不能为空。示例: 'cpp/naming-classes', 'qt/braces-knr'"

    agent_name = _get_agent_name()

    page = _get_wiki_page_raw(slug.strip(), agent_name=agent_name)
    if page is None:
        return (
            f"未找到页面 '{slug}'。\n"
            f"可用域: cpp, qt, sqlite, git, tencent, qt-wiki, google\n"
            f"请对照系统提示词中的规则索引找到正确的 slug 后重试。"
        )

    # 返回页面内容，如果过长则返回摘要+检查方法+审查清单
    content = page["content"]
    lines = [
        f"=== {page['title']} ===",
        f"域: {page['domain']} | 优先级: {page['priority']} | 检查方法: {page['check_method']}",
    ]
    if page.get("related_pages"):
        related = [f"[[{r}]]" for r in page["related_pages"][:10]]
        lines.append(f"关联页面: {', '.join(related)}")
    lines.append(f"\n{content}")
    return "\n".join(lines)


# ============================================================================
# Wiki 违规增强 — 从 wiki 页面确定性提取 rule_clause
# ============================================================================

def enrich_violations_from_wiki(violations: list[dict]) -> list[dict]:
    """对每条含 rule_page 的违规，从 wiki 页面确定性提取条款原文。

    读取规则条款（## 规则条款）、来源文件、来源章节，
    填充 rule_clause / source_file / source_section 字段。
    若 rule_excerpt 为空也自动填充，确保 fix/review agent 有规则可用。

    设计意图（SUB_RULE_INTEGRATION_DESIGN.md §4.3）：
      rule_clause 由确定性系统代码填充，不由 checker agent 摘录。
      Agent 可能改写、缩略或添加自己的理解——wiki 页面原文是权威来源。
    """
    import yaml

    wiki_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rules-wiki", "wiki")
    if not os.path.isdir(wiki_dir):
        return violations

    enriched = 0
    for v in violations:
        rule_page = v.get("rule_page", "").strip()
        if not rule_page:
            continue

        # 规范化路径
        page_path = rule_page.replace("\\", "/")
        if not page_path.endswith(".md"):
            page_path += ".md"
        full_path = os.path.join(wiki_dir, page_path)

        if not os.path.isfile(full_path):
            continue

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                raw = f.read()
        except Exception:
            continue

        # 解析 YAML frontmatter
        clause_text = ""
        source_file = ""
        source_section = ""
        if raw.startswith("---"):
            parts = raw.split("---", 2)
            if len(parts) >= 3:
                try:
                    fm = yaml.safe_load(parts[1])
                except Exception:
                    fm = {}
                source_file = fm.get("source_file", "")
                source_section = fm.get("source_section", "")
                body = parts[2]
        else:
            body = raw

        # 提取 "## 规则条款" 节
        clause_text = _extract_wiki_section(body, "规则条款")
        if not clause_text:
            # 回退：取页面第一段正文
            clause_text = body.strip().split("\n\n")[0] if body.strip() else ""

        # 填充字段
        if clause_text:
            v["rule_clause"] = clause_text.strip()
        if source_file and not v.get("source_file"):
            v["source_file"] = source_file
        if source_section and not v.get("rule_section"):
            v["rule_section"] = source_section
        # 若 LLM 未填 rule_excerpt，用 clause 回填（fix/review 工具依赖此字段）
        if not v.get("rule_excerpt") and clause_text:
            v["rule_excerpt"] = clause_text.strip()

        enriched += 1

    return violations


def _extract_wiki_section(body: str, section_name: str) -> str:
    """从 wiki 页面正文中提取指定 ## 标题下的内容。"""
    import re
    # 匹配 "## 规则条款" 或 "## 规则条款\n" 直到下一个同级或上级标题
    pattern = rf"^##\s+{re.escape(section_name)}\s*\n(.*?)(?=^##?\s|\Z)"
    m = re.search(pattern, body, re.MULTILINE | re.DOTALL)
    if m:
        return m.group(1).strip()
    return ""


# ============================================================================
# Mech Checker 专用工具（将 16 个正则规则包装为工具）
# ============================================================================


def _get_file_content(file_path: str) -> Optional[str]:
    """内部辅助：通过 read_file 获取文件内容。"""
    if _state_ref is None:
        return None
    file_contents = _state_ref.get("file_contents") or {}
    if file_path in file_contents:
        return file_contents[file_path]
    for fp in file_contents:
        if os.path.basename(fp) == file_path or file_path in fp:
            return file_contents[fp]
    return None


def _is_qt_file(file_path: str, content: str) -> bool:
    """判断文件是否包含 Qt 代码。"""
    ext = os.path.splitext(file_path)[1].lower()
    if ext in QT_SPECIAL_EXTENSIONS:
        return True
    if ext in CXX_EXTENSIONS:
        return bool(QT_MARKERS.search(content))
    return False


def _has_sqlite(content: str) -> bool:
    """判断文件是否涉及 SQLite。"""
    return bool(SQLITE_MARKERS.search(content))


# C++ 规则工具


@tool
def check_tab_indentation(file_path: str) -> list[dict]:
    """检测文件中的 Tab 缩进字符。禁止使用 Tab，应用 4 个空格缩进。

    Args:
        file_path: 要检查的文件路径
    """
    content = _get_file_content(file_path)
    if content is None:
        return [{"error": f"文件未找到: {file_path}"}]
    violations = []
    for i, line in enumerate(content.split("\n"), 1):
        if "\t" in line:
            violations.append({
                "line": i, "rule": "禁止 Tab 缩进", "severity": "critical",
                "current": line.strip()[:120],
                "expected": "将 Tab 替换为 4 个空格",
                "reason": f"第 {i} 行包含 Tab 字符",
            })
    return violations


@tool
def check_line_width(file_path: str, is_qt: bool = False) -> list[dict]:
    """检测文件中的超长行。C++ 限 100 字符，Qt 限 120 字符。

    Args:
        file_path: 要检查的文件路径
        is_qt: 是否包含 Qt 代码（True=120 字符限制，False=100 字符限制）
    """
    content = _get_file_content(file_path)
    if content is None:
        return [{"error": f"文件未找到: {file_path}"}]
    limit = 120 if is_qt else 100
    violations = []
    for i, line in enumerate(content.split("\n"), 1):
        stripped = line.rstrip("\r")
        if len(stripped) > limit:
            violations.append({
                "line": i, "rule": f"行宽 ≤ {limit} 字符", "severity": "warning",
                "current": stripped[:120],
                "expected": "将超长行拆分为多行",
                "reason": f"第 {i} 行宽度 {len(stripped)} 字符，超过 {limit} 限制",
            })
    return violations


@tool
def check_header_guard(file_path: str) -> list[dict]:
    """检测 .h/.hpp 文件的保护宏格式。
    要求: PROJECT_MODULE_FILENAME_H_ 全大写，至少 2 个下划线分段，_H_ 结尾。

    Args:
        file_path: 要检查的头文件路径
    """
    content = _get_file_content(file_path)
    if content is None:
        return [{"error": f"文件未找到: {file_path}"}]
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in (".h", ".hpp"):
        return []

    lines = content.split("\n")
    violations = []
    guard_re = re.compile(r"^#ifndef\s+([A-Z][A-Z0-9]*(?:_[A-Z][A-Z0-9]*)+_H_)\s*$")

    ifndef_line = -1
    ifndef_name = ""
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("//") or stripped.startswith("/*"):
            continue
        if stripped.startswith("#ifndef"):
            m = guard_re.match(stripped)
            if m:
                ifndef_name = m.group(1)  # 完整宏名，如 PROJECT_MODULE_FILE_H_
            else:
                violations.append({
                    "line": i + 1, "rule": "头文件保护宏格式", "severity": "critical",
                    "current": stripped,
                    "expected": "格式: #ifndef PROJECT_MODULE_FILENAME_H_",
                    "reason": "保护宏格式不正确",
                })
            ifndef_line = i
            break

    if ifndef_line >= 0:
        for i in range(ifndef_line + 1, min(ifndef_line + 4, len(lines))):
            stripped = lines[i].strip()
            if not stripped or stripped.startswith("//"):
                continue
            if stripped.startswith("#define"):
                parts = stripped.split()
                if len(parts) >= 2 and ifndef_name and parts[1] != ifndef_name:
                    violations.append({
                        "line": i + 1, "rule": "头文件保护宏格式", "severity": "critical",
                        "current": stripped,
                        "expected": f"#define {ifndef_name}",
                        "reason": f"#define 与 #ifndef '{ifndef_name}' 不匹配",
                    })
                break
    return violations


@tool
def check_using_namespace_in_header(file_path: str) -> list[dict]:
    """检测头文件中是否使用了 using namespace（会污染编译单元）。

    Args:
        file_path: 要检查的文件路径
    """
    content = _get_file_content(file_path)
    if content is None:
        return [{"error": f"文件未找到: {file_path}"}]
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in (".h", ".hpp"):
        return []

    violations = []
    for i, line in enumerate(content.split("\n"), 1):
        if re.search(r"using\s+namespace\s+\w+", line):
            violations.append({
                "line": i, "rule": "头文件禁止 using namespace", "severity": "critical",
                "current": line.strip(),
                "expected": "将 using namespace 移至 .cpp 文件",
                "reason": f"头文件第 {i} 行包含 using namespace",
            })
    return violations


@tool
def check_define_macro(file_path: str) -> list[dict]:
    """检测 #define 宏常量/函数（应使用 constexpr/const 替代）。排除头文件保护宏。

    Args:
        file_path: 要检查的文件路径
    """
    content = _get_file_content(file_path)
    if content is None:
        return [{"error": f"文件未找到: {file_path}"}]
    violations = []
    define_re = re.compile(r"^\s*#define\s+(\w+)\s+(.*)")
    prev_line = ""
    for i, line in enumerate(content.split("\n"), 1):
        m = define_re.match(line)
        if not m:
            prev_line = line
            continue
        if re.match(r"^\s*#ifndef\s+", prev_line):
            prev_line = line
            continue
        prev_line = line
        violations.append({
            "line": i, "rule": "禁止 #define 常量/函数", "severity": "warning",
            "current": line.strip(), "expected": "使用 constexpr/const 替代",
            "reason": f"第 {i} 行用 #define 定义 '{m.group(1)}'",
        })
    return violations


@tool
def check_c_style_array(file_path: str) -> list[dict]:
    """检测 C 风格数组声明（应使用 std::array / std::vector）。

    Args:
        file_path: 要检查的文件路径
    """
    content = _get_file_content(file_path)
    if content is None:
        return [{"error": f"文件未找到: {file_path}"}]
    violations = []
    c_array_re = re.compile(
        r"\b(char|int|float|double|long|short|bool|wchar_t|"
        r"unsigned|signed|size_t|uint\d+_t|int\d+_t)\s+"
        r"[\w*&:<>\s]+\s*\[[^\]]*\]\s*[;=]"
    )
    for i, line in enumerate(content.split("\n"), 1):
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("/*"):
            continue
        if "main(" in stripped and "argv" in stripped:
            continue
        if "std::array" in line or "operator[]" in line:
            continue
        if c_array_re.search(line):
            violations.append({
                "line": i, "rule": "禁止 C 风格数组", "severity": "warning",
                "current": stripped, "expected": "使用 std::array / std::vector",
                "reason": f"第 {i} 行使用了 C 风格数组声明",
            })
    return violations


@tool
def check_throw_spec(file_path: str) -> list[dict]:
    """检测 throw() 动态异常规范（C++11 起弃用，应用 noexcept）。

    Args:
        file_path: 要检查的文件路径
    """
    content = _get_file_content(file_path)
    if content is None:
        return [{"error": f"文件未找到: {file_path}"}]
    violations = []
    for i, line in enumerate(content.split("\n"), 1):
        if re.search(r"throw\s*\(\s*\)", line):
            violations.append({
                "line": i, "rule": "禁止 throw() 异常规范", "severity": "warning",
                "current": line.strip(), "expected": "使用 noexcept 替代",
                "reason": f"第 {i} 行使用了 throw() 动态异常规范",
            })
    return violations


@tool
def check_default_lambda_capture(file_path: str) -> list[dict]:
    """检测 lambda 默认捕获 [=] 或 [&]（必须显式列出捕获变量）。

    Args:
        file_path: 要检查的文件路径
    """
    content = _get_file_content(file_path)
    if content is None:
        return [{"error": f"文件未找到: {file_path}"}]
    violations = []
    default_cap_re = re.compile(r"\[\=\]|\[\&\]")
    for i, line in enumerate(content.split("\n"), 1):
        if default_cap_re.search(line):
            if re.search(r"\[\=\s*,\s*&?\w+\]", line) or re.search(r"\[\&\s*,\s*\w+\]", line):
                continue
            violations.append({
                "line": i, "rule": "禁止默认 lambda 捕获", "severity": "critical",
                "current": line.strip(), "expected": "显式列出每个捕获变量",
                "reason": f"第 {i} 行 lambda 使用默认捕获",
            })
    return violations


@tool
def check_reinterpret_cast(file_path: str) -> list[dict]:
    """检测 reinterpret_cast 使用（应用 static_cast 替代）。

    Args:
        file_path: 要检查的文件路径
    """
    content = _get_file_content(file_path)
    if content is None:
        return [{"error": f"文件未找到: {file_path}"}]
    violations = []
    for i, line in enumerate(content.split("\n"), 1):
        if re.search(r"\breinterpret_cast\b", line):
            violations.append({
                "line": i, "rule": "禁止 reinterpret_cast", "severity": "critical",
                "current": line.strip(), "expected": "使用 static_cast 或标记 NOLINT",
                "reason": f"第 {i} 行使用了 reinterpret_cast",
            })
    return violations


@tool
def check_virtual_override(file_path: str) -> list[dict]:
    """检测 virtual ... override 冗余（override 不应重复 virtual）。

    Args:
        file_path: 要检查的文件路径
    """
    content = _get_file_content(file_path)
    if content is None:
        return [{"error": f"文件未找到: {file_path}"}]
    violations = []
    for i, line in enumerate(content.split("\n"), 1):
        if re.search(r"\bvirtual\b.*\boverride\b", line):
            violations.append({
                "line": i, "rule": "override 不重复 virtual", "severity": "warning",
                "current": line.strip(), "expected": "删除 virtual，保留 override",
                "reason": f"第 {i} 行 override 重复写了 virtual",
            })
    return violations


@tool
def check_c_variadic(file_path: str) -> list[dict]:
    """检测 C 风格 ... 可变参数（应用模板参数包替代，排除 catch/template）。

    Args:
        file_path: 要检查的文件路径
    """
    content = _get_file_content(file_path)
    if content is None:
        return [{"error": f"文件未找到: {file_path}"}]
    violations = []
    c_variadic_re = re.compile(r"(?<=[,\(])\s*\.\.\.\s*(?=\))")
    for i, line in enumerate(content.split("\n"), 1):
        if "catch" in line or "template" in line:
            continue
        if c_variadic_re.search(line):
            violations.append({
                "line": i, "rule": "禁止 C 风格 ... 可变参数", "severity": "warning",
                "current": line.strip(), "expected": "使用模板参数包替代",
                "reason": f"第 {i} 行使用了 C 风格可变参数",
            })
    return violations


# Qt 规则工具


@tool
def check_qt_include_dot_h(file_path: str, is_qt: bool = True) -> list[dict]:
    """检测 Qt 头文件 include 带 .h 后缀（应为 #include <QWidget> 而非 <QWidget.h>）。

    Args:
        file_path: 要检查的文件路径
        is_qt: 是否包含 Qt 代码
    """
    if not is_qt:
        return []
    content = _get_file_content(file_path)
    if content is None:
        return [{"error": f"文件未找到: {file_path}"}]
    violations = []
    qt_include_re = re.compile(r'#include\s*<Q\w+\.h\s*>')
    for i, line in enumerate(content.split("\n"), 1):
        if qt_include_re.search(line):
            violations.append({
                "line": i, "rule": "Qt include 不加 .h", "severity": "warning",
                "current": line.strip(), "expected": "去掉 .h 后缀",
                "reason": f"第 {i} 行 Qt include 带了 .h 后缀",
            })
    return violations


@tool
def check_qt_signal_name(file_path: str, is_qt: bool = True) -> list[dict]:
    """检测 Qt 信号名是否包含 'signal' 字样。

    Args:
        file_path: 要检查的文件路径
        is_qt: 是否包含 Qt 代码
    """
    if not is_qt:
        return []
    content = _get_file_content(file_path)
    if content is None:
        return [{"error": f"文件未找到: {file_path}"}]
    violations = []
    signal_re = re.compile(r"\b\w*[Ss]ignal\w*\s*\(")
    in_signals = False
    for i, line in enumerate(content.split("\n"), 1):
        stripped = line.strip()
        if re.match(r"^\s*signals\s*:\s*$", line):
            in_signals = True
            continue
        if in_signals and re.match(r"^\s*(public|private|protected)\s+slots?\s*:\s*$", line):
            in_signals = False
            continue
        if in_signals and signal_re.search(stripped):
            violations.append({
                "line": i, "rule": "信号名禁含 signal", "severity": "warning",
                "current": stripped, "expected": "重命名，去掉 'signal' 字样",
                "reason": f"第 {i} 行信号名包含 'signal'",
            })
    return violations


@tool
def check_qt_slot_name(file_path: str, is_qt: bool = True) -> list[dict]:
    """检测 Qt 槽名是否包含 'slot' 字样。

    Args:
        file_path: 要检查的文件路径
        is_qt: 是否包含 Qt 代码
    """
    if not is_qt:
        return []
    content = _get_file_content(file_path)
    if content is None:
        return [{"error": f"文件未找到: {file_path}"}]
    violations = []
    slot_re = re.compile(r"\b\w*[Ss]lot\w*\s*\(")
    in_slots = False
    for i, line in enumerate(content.split("\n"), 1):
        stripped = line.strip()
        if re.match(r"^\s*(public|private|protected)\s+slots?\s*:\s*$", line):
            in_slots = True
            continue
        if in_slots and re.match(r"^\s*signals\s*:\s*$", line):
            in_slots = False
            continue
        if in_slots and slot_re.search(stripped):
            violations.append({
                "line": i, "rule": "槽名禁含 slot", "severity": "warning",
                "current": stripped, "expected": "重命名，去掉 'slot' 字样",
                "reason": f"第 {i} 行槽名包含 'slot'",
            })
    return violations


# SQLite 规则工具


@tool
def check_sqlite_pragma_key(file_path: str) -> list[dict]:
    """检测 SQLite 文件是否包含 PRAGMA key 加密设置。

    Args:
        file_path: 要检查的文件路径
    """
    content = _get_file_content(file_path)
    if content is None:
        return [{"error": f"文件未找到: {file_path}"}]
    if not _has_sqlite(content):
        return []
    if "PRAGMA key" not in content and "PRAGMA key =" not in content and "pragma key" not in content:
        return [{
            "line": 1, "rule": "SQLite 必须使用 SQLCipher 加密", "severity": "critical",
            "current": "（未找到 PRAGMA key 设置）",
            "expected": "执行 PRAGMA key = '...' 设置加密密钥",
            "reason": "文件中未找到 PRAGMA key 加密设置",
        }]
    return []


@tool
def check_sqlite_kdf(file_path: str) -> list[dict]:
    """检测 SQLite 文件的 KDF 迭代次数是否 ≥ 256000。

    Args:
        file_path: 要检查的文件路径
    """
    content = _get_file_content(file_path)
    if content is None:
        return [{"error": f"文件未找到: {file_path}"}]
    if not _has_sqlite(content):
        return []
    violations = []
    if "cipher_default_kdf_iter" not in content:
        violations.append({
            "line": 1, "rule": "SQLite KDF 迭代数 ≥ 256000", "severity": "critical",
            "current": "（未找到 cipher_default_kdf_iter）",
            "expected": "执行 PRAGMA cipher_default_kdf_iter = 256000",
            "reason": "未设置 KDF 迭代次数",
        })
    else:
        m = re.search(r"cipher_default_kdf_iter\s*=\s*(\d+)", content)
        if m and int(m.group(1)) < 256000:
            violations.append({
                "line": 1, "rule": "SQLite KDF 迭代数 ≥ 256000", "severity": "warning",
                "current": f"cipher_default_kdf_iter = {m.group(1)}",
                "expected": "cipher_default_kdf_iter = 256000",
                "reason": f"KDF 迭代数 {m.group(1)} 低于要求的 256000",
            })
    return violations


# Git 规则工具


@tool
def run_git_log(repo_path: str, count: int = 50) -> str:
    """运行 git log 获取最近的提交记录。

    Args:
        repo_path: Git 仓库路径
        count: 获取的提交数（默认 50）
    """
    rejection = assert_tool_allowed("run_git_log")
    if rejection:
        return rejection
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "log", f"--format=%H|||%s", f"-n{count}"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            return f"git log 失败: {result.stderr}"
        output = result.stdout.strip()
        if not output:
            return "git log 无输出（仓库可能无提交）"
        return output
    except FileNotFoundError:
        return "git 未安装"
    except subprocess.TimeoutExpired:
        return "git log 超时"


# ============================================================================
# Fix / Review agent 工具
# ============================================================================


@tool
def get_pending_violations() -> list[dict]:
    """获取所有待修复的违规项列表。返回每条违规的 idx、文件、行号、规则、严重度。"""
    if _state_ref is None:
        return []
    violations = _state_ref.get("merged_violations") or []
    # 检查 fix_plans，排除已通过、infra、unresolved 的
    fix_plans = _state_ref.get("fix_plans") or []
    skip_indices = set()
    for i, p in enumerate(fix_plans):
        if p is not None:
            fs = p.get("fix_status", "")
            if fs in ("passed", "infra", "unresolved", "refuted"):
                skip_indices.add(i)

    pending = []
    for i, v in enumerate(violations):
        if i not in skip_indices:
            pending.append({
                "idx": i,
                "file": v.get("file", ""),
                "line": v.get("line", 0),
                "rule": v.get("rule", ""),
                "severity": v.get("severity", ""),
                "current": v.get("current", "")[:200],
                "expected": v.get("expected", "")[:200],
                "reason": v.get("reason", "")[:200],
            })
    return pending


# ============================================================================
# L2: 规则精确注入 — 从规范文件提取 fix_guidance 和 review_checklist
# ============================================================================

# ── 规则名 → 章节关键词映射（三级回退的第 1 级）──
_RULE_KEYWORD_MAP: dict[str, dict[str, list[str]]] = {
    "cpp": {
        "命名": ["### 1.1 命名约定"],
        "类名": ["### 1.1 命名约定"],
        "PascalCase": ["### 1.1 命名约定"],
        "camelCase": ["### 1.1 命名约定"],
        "m_": ["### 1.1 命名约定"],
        "常量": ["### 1.1 命名约定"],
        "UPPER_CASE": ["### 1.1 命名约定"],
        "头文件": ["### 1.2 头文件规范"],
        "include": ["### 1.2 头文件规范"],
        "保护宏": ["### 1.2 头文件规范"],
        "前置声明": ["### 1.2 头文件规范"],
        "缩进": ["### 1.3 代码格式"],
        "行宽": ["### 1.3 代码格式"],
        "Tab": ["### 1.3 代码格式"],
        "大括号": ["### 1.3 代码格式"],
        "智能指针": ["### 2.1 智能指针使用规范"],
        "unique_ptr": ["### 2.1 智能指针使用规范"],
        "shared_ptr": ["### 2.1 智能指针使用规范"],
        "make_unique": ["### 2.1 智能指针使用规范"],
        "make_shared": ["### 2.1 智能指针使用规范"],
        "裸指针": ["### 2.1 智能指针使用规范"],
        "移动": ["### 2.2 移动语义规范"],
        "std::move": ["### 2.2 移动语义规范"],
        "NRVO": ["### 2.2 移动语义规范"],
        "lambda": ["### 2.3 Lambda表达式规范"],
        "Lambda": ["### 2.3 Lambda表达式规范"],
        "捕获": ["### 2.3 Lambda表达式规范"],
        "RAII": ["### 3.1 资源获取即初始化", "### 3.2 避免内存泄漏规范"],
        "内存泄漏": ["### 3.2 避免内存泄漏规范"],
        "new": ["### 2.1 智能指针使用规范", "### 3.2 避免内存泄漏规范"],
        "delete": ["### 2.1 智能指针使用规范", "### 3.2 避免内存泄漏规范"],
        "异常": ["### 4.1 异常使用规范", "### 4.2 异常安全保证"],
        "noexcept": ["### 4.1 异常使用规范"],
        "throw": ["### 4.1 异常使用规范"],
        "模板": ["### 5.1 模板使用规范"],
        "concept": ["### 5.2 概念(Concepts)使用"],
        "线程": ["### 6.1 线程安全规范"],
        "mutex": ["### 6.1 线程安全规范", "### 6.2 原子操作与锁"],
        "原子": ["### 6.2 原子操作与锁"],
        "死锁": ["### 6.1 线程安全规范"],
        "C风格": ["## 7. 禁止模式"],
        "reinterpret_cast": ["## 7. 禁止模式"],
        "using namespace": ["## 7. 禁止模式"],
        "#define": ["## 7. 禁止模式"],
        "宏": ["## 7. 禁止模式"],
        "类型转换": ["## 7. 禁止模式"],
        "cast": ["## 7. 禁止模式"],
        "可变参数": ["## 7. 禁止模式"],
    },
    "qt": {
        "缩进": ["### 2.1 缩进规则"],
        "Tab": ["### 2.1 缩进规则"],
        "变量": ["### 2.2 变量声明规范", "### 3.4 变量名命名规范"],
        "空白": ["### 2.3 空白字符规范"],
        "大括号": ["### 2.4 大括号使用规范"],
        "switch": ["### 2.6 Switch语句规范"],
        "断行": ["### 2.7 代码断行规范"],
        "virtual": ["### 2.8 继承与virtual关键字规范"],
        "文件命名": ["### 3.1 文件命名规范"],
        "类名": ["### 3.2 类名命名规范"],
        "Q开头": ["### 3.2 类名命名规范"],
        "信号": ["#### 3.3.2 信号命名规范"],
        "signal": ["#### 3.3.2 信号命名规范"],
        "槽": ["#### 3.3.3 槽函数命名规范"],
        "slot": ["#### 3.3.3 槽函数命名规范"],
        "控件": ["#### 3.4.1 UI控件类名缩写表"],
        "前缀": ["#### 3.4.1 UI控件类名缩写表"],
        "m_lbl": ["#### 3.4.1 UI控件类名缩写表"],
        "m_btn": ["#### 3.4.1 UI控件类名缩写表"],
        "m_edt": ["#### 3.4.1 UI控件类名缩写表"],
        "include": ["#### 4.2.1 头文件包含顺序", "### 4.3 Qt库引用规范"],
        "头文件": ["#### 4.2.1 头文件包含顺序"],
        ".h": ["### 4.3 Qt库引用规范"],
        "内存": ["### 4.4 内存管理规范"],
    },
    "sqlite": {
        "PRAGMA": ["# 加密原理"],
        "key": ["# 加密原理"],
        "KDF": ["# KDF 密钥派生机制"],
        "迭代": ["# KDF 密钥派生机制"],
        "salt": ["# Salt机制说明"],
        "Salt": ["# Salt机制说明"],
        "SQL": ["# 加密原理"],
        "注入": ["# 加密原理"],
        "参数化": ["# 加密原理"],
        "加密": ["# 概述", "# 技术组成", "# 加密原理"],
        "连接": ["# C# 数据库连接方式"],
        "密钥": ["# 加密原理", "# KDF 密钥派生机制"],
        "硬编码": ["# 加密原理"],
    },
}


def _get_rule_path(domain: str) -> str:
    return {
        "cpp": CPP_RULES_FILE,
        "qt": QT_RULES_FILE,
        "sqlite": SQLITE_RULES_FILE,
    }.get(domain, "")


def _split_into_sections(rules_text: str) -> list[tuple[str, str]]:
    """将规范文本按章节标题切分为 [(header, body), ...] 列表。"""
    # 匹配: ## N. / ### N.N / #### N.N.N / ## 一、/ # 验证方案
    # 支持多级编号: 1, 1.1, 3.3.2, 4.2.1
    # 注意: [^\n]* 确保捕获完整的标题行文本（如 "## 7. 禁止模式"），
    # 否则 keyword_map → section 匹配会失败。
    pattern = re.compile(
        r"^(#{1,4}\s+(?:\d+(?:[\.\、]\d+)*[\.\、]?"
        r"|[一二三四五六七八九十]+[、．])[^\n]*"
        r"|#\s+\S.*)",
        re.MULTILINE,
    )
    splits = list(pattern.finditer(rules_text))
    if not splits:
        return [("", rules_text)]

    sections = []
    for i, m in enumerate(splits):
        start = m.start()
        end = splits[i + 1].start() if i + 1 < len(splits) else len(rules_text)
        # 归一化: 将非断行空格 \xa0 替换为普通空格
        header = m.group(0).strip().replace("\xa0", " ")
        body = rules_text[start:end]
        sections.append((header, body))

    if splits[0].start() > 0:
        preamble = rules_text[:splits[0].start()].strip()
        if preamble:
            sections.insert(0, ("(前言)", preamble))

    return sections


def _extract_keywords(rule_name: str) -> list[str]:
    """从规则名中提取用于匹配的关键词列表。"""
    keywords = [rule_name]
    for sep in ["：", ":", "、", "，", ",", " ", "-"]:
        if sep in rule_name:
            keywords.extend(rule_name.split(sep))
    return [k.strip() for k in keywords if len(k.strip()) >= 1]


def _match_rule_section(domain: str, rule_name: str) -> str:
    """三级回退：从规范文件中找到与 rule_name 最相关的章节文本。"""
    path = _get_rule_path(domain)
    if not path:
        return ""
    try:
        rules_text = read_rules_file(path)
    except Exception:
        return ""

    keyword_map = _RULE_KEYWORD_MAP.get(domain, {})
    sections = _split_into_sections(rules_text)

    # ── Level 1: 关键词 → 章节标题匹配 ──
    # 1a: 精确匹配 map key
    keywords = _extract_keywords(rule_name)
    for kw in keywords:
        if kw in keyword_map:
            target_headers = keyword_map[kw]
            for header, body in sections:
                for th in target_headers:
                    if th in header:
                        return _expand_with_subsections(header, body, sections)
    # 1b: map key 是 rule_name 的子串（如 "信号" ⊂ "信号命名规范"）
    for map_key, target_headers in keyword_map.items():
        if len(map_key) >= 2 and map_key in rule_name:
            for header, body in sections:
                for th in target_headers:
                    if th in header:
                        return _expand_with_subsections(header, body, sections)
    # 1c: 直接匹配章节标题
    for kw in keywords:
        kw_clean = kw.strip("#* ")
        for header, body in sections:
            header_clean = re.sub(r"^#+\s*", "", header)
            if kw_clean in header_clean:
                return _expand_with_subsections(header, body, sections)

    # ── Level 2: rule_name 在正文中 substring 匹配 ──
    name_short = rule_name[:20] if len(rule_name) > 20 else rule_name
    for header, body in sections:
        if name_short in body:
            return _expand_with_subsections(header, body, sections)

    # ── Level 3: 默认 — 返回 "禁止模式" 或 "示例代码" 章节 ──
    for header, body in sections:
        if "禁止" in header or "示例代码" in header or "示例" in header:
            return _expand_with_subsections(header, body, sections)

    return rules_text


def _expand_with_subsections(
    header: str, body: str, sections: list[tuple[str, str]],
) -> str:
    """如果匹配的章节是高层标题（# / ##），自动合并后续 ### 子章节。

    例如 SQLite 中 # 加密原理 后跟 ### 1. 文件级加密模型 / ### 2. 解密流程，
    这些子章节的内容属于加密原理章节，应一并返回。
    """
    # 计算当前标题级别
    level = 0
    for ch in header:
        if ch == "#":
            level += 1
        else:
            break
    if level >= 3:
        return body  # ### 级别不需要扩展

    # 找到此章节在 sections 中的位置
    matched_idx = None
    for i, (h, b) in enumerate(sections):
        if h == header and b == body:
            matched_idx = i
            break
    if matched_idx is None:
        return body

    # 合并后续更低级别的子章节
    result = body
    for i in range(matched_idx + 1, len(sections)):
        sub_h, sub_b = sections[i]
        sub_level = 0
        for ch in sub_h:
            if ch == "#":
                sub_level += 1
            else:
                break
        if sub_level > level:
            result += "\n" + sub_b
        else:
            break  # 遇到同级或更高级标题，停止

    return result


def _extract_fix_guidance(domain: str, rule_name: str) -> str:
    """从规范文件中提取修复指南：正确示例 + 错误示例 + 理由。

    支持多域来源（如 "cpp|qt|sqlite"），尝试每个域，返回最佳匹配。
    优先选择 keyword_map 中有匹配的域，退而求其次选最长的结果。
    """
    candidates: list[tuple[bool, int, str]] = []  # (has_kw_match, length, section)
    for d in domain.split("|"):
        d = d.strip()
        section = _match_rule_section(d, rule_name)
        if not section:
            continue
        # 检查该域是否通过关键词精准匹配（非 Level-3 fallback）
        has_kw = any(
            kw in _RULE_KEYWORD_MAP.get(d, {})
            for kw in _extract_keywords(rule_name)
        ) or any(
            len(mk) >= 2 and mk in rule_name
            for mk in _RULE_KEYWORD_MAP.get(d, {})
        )
        candidates.append((has_kw, len(section), section))
    if not candidates:
        return ""
    # 优先关键词匹配，其次长度（从最短的默认 fallback 中脱颖而出）
    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    best_section = candidates[0][2]

    parts = []
    max_len = 3000

    correct_m = re.search(
        r"(?:\*{0,2}正确示例\*{0,2}|Correct).*?\n(.*?)"
        r"(?=\*{0,2}错误示例\*{0,2}|\*{0,2}检查方法\*{0,2}|###|$)",
        section, re.DOTALL,
    )
    if correct_m:
        parts.append(f"=== 正确示例 ===\n{correct_m.group(0).strip()[:max_len]}")

    incorrect_m = re.search(
        r"(?:\*{0,2}错误示例\*{0,2}|Wrong).*?\n(.*?)"
        r"(?=\*{0,2}检查方法\*{0,2}|###|$)",
        section, re.DOTALL,
    )
    if incorrect_m:
        parts.append(f"=== 错误示例 ===\n{incorrect_m.group(0).strip()[:max_len]}")

    reason_m = re.search(
        r"\*{0,2}理由\*{0,2}[：:]\s*\n(.*?)"
        r"(?=\*{0,2}(?:正确|错误|检查|规则)\*{0,2}|###|$)",
        section, re.DOTALL,
    )
    if reason_m:
        parts.append(f"=== 理由 ===\n{reason_m.group(0).strip()[:max_len]}")

    rule_m = re.search(
        r"\*{0,2}规则\*{0,2}[：:]\s*\n(.*?)"
        r"(?=\*{0,2}(?:正确|错误|检查|理由)\*{0,2}|###|$)",
        section, re.DOTALL,
    )
    if rule_m:
        parts.insert(0, f"=== 规则 ===\n{rule_m.group(0).strip()[:max_len]}")

    # ── Fallback: 无结构化模式匹配时，返回章节原文摘要 ──
    if not parts:
        clean = re.sub(r"\n{3,}", "\n\n", section)
        parts.append(f"=== 相关规范原文 ===\n{clean[:max_len]}")

    return "\n\n".join(parts)


def _extract_review_checklist(domain: str, rule_name: str) -> str:
    """从规范文件中提取审查标准：检查方法 + 检查清单项。

    支持多域来源（如 "cpp|qt|sqlite"），尝试每个域，返回最佳匹配。
    优先选择 keyword_map 中有匹配的域。
    """
    candidates: list[tuple[bool, int, str]] = []
    for d in domain.split("|"):
        d = d.strip()
        section = _match_rule_section(d, rule_name)
        if not section:
            continue
        has_kw = any(
            kw in _RULE_KEYWORD_MAP.get(d, {})
            for kw in _extract_keywords(rule_name)
        ) or any(
            len(mk) >= 2 and mk in rule_name
            for mk in _RULE_KEYWORD_MAP.get(d, {})
        )
        candidates.append((has_kw, len(section), section))
    if not candidates:
        return ""
    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    section = candidates[0][2]

    parts = []
    max_len = 2000

    check_m = re.search(
        r"\*{0,2}检查方法\*{0,2}[：:]\s*\n(.*?)"
        r"(?=###|\*{0,2}(?:正确|错误|规则|理由)\*{0,2}|$)",
        section, re.DOTALL,
    )
    if check_m:
        parts.append(check_m.group(0).strip()[:max_len])

    checklist_items = re.findall(
        r"(?:(?:\d+\.\s*\[.\])|(?:-\s*\[.\])).*",
        section,
    )
    if checklist_items:
        items_text = "\n".join(checklist_items[:10])
        parts.append(f"=== 检查清单 ===\n{items_text[:max_len]}")

    # ── Fallback: 无结构化模式时返回章节原文 ──
    if not parts:
        clean = re.sub(r"\n{3,}", "\n\n", section)
        parts.append(f"=== 相关规范原文 ===\n{clean[:max_len]}")

    return "=== 审查标准 ===\n" + "\n\n".join(parts)


@tool
def get_violation_detail(violation_idx: int) -> dict:
    """获取单条违规的完整详细信息，包括历史修改记录、审查标准、最新建议。

    Args:
        violation_idx: 违规在 merged_violations 中的索引
    """
    if _state_ref is None:
        return {"error": "状态未初始化"}

    # 硬编码校验：只允许访问分配给当前 agent 的违规
    rejection = _check_idx_allowed(violation_idx)
    if rejection:
        return {"error": rejection}

    violations = _state_ref.get("merged_violations") or []
    if violation_idx < 0 or violation_idx >= len(violations):
        return {"error": f"违规索引 {violation_idx} 超出范围 (0-{len(violations)-1})"}

    # ── 遥测：记录 get_violation_detail 调用 ──
    _record_telemetry(violation_idx, "called_get_detail", True)

    v = violations[violation_idx]
    detail = {
        "idx": violation_idx,
        "file": v.get("file", ""),
        "line": v.get("line", 0),
        "rule": v.get("rule", ""),
        "severity": v.get("severity", ""),
        "current": v.get("current", ""),
        "expected": v.get("expected", ""),
        "reason": v.get("reason", ""),
        "surrounding": v.get("surrounding", ""),
    }

    # ── FixContextBundle: 为跨文件修复提供相关文件信息 ──
    detail["related_files"] = _build_related_files(v, violation_idx)

    # 从本地缓存加载历史审查记录
    cached = _read_review_cache(violation_idx)
    if cached:
        detail["history"] = cached.get("attempts", [])
        detail["scoring_criteria"] = cached.get("scoring_criteria", "")
        detail["rule_snippet"] = cached.get("rule_snippet", "")
        attempts = cached.get("attempts", [])
        if attempts:
            last = attempts[-1]
            if last.get("suggestion"):
                detail["latest_suggestion"] = last["suggestion"]

    # ── L2: fix_guidance — 优先复用 checker 传下来的 rule_excerpt ──
    if not detail.get("fix_guidance"):
        # 路径 A（主路径）：checker agent 报告违规时已附带规范原文
        excerpt = v.get("rule_excerpt", "")
        section = v.get("rule_section", "")
        if excerpt:
            parts = [f"=== 来源: {section} ==="] if section else []
            parts.append(excerpt)
            detail["fix_guidance"] = "\n".join(parts)
        else:
            # 路径 B（fallback）：关键词映射表 + 规范文件提取（兼容历史数据）
            domain = v.get("source", "")
            rule_name = v.get("rule", "")
            if domain and rule_name:
                guidance = _extract_fix_guidance(domain, rule_name)
                if guidance:
                    detail["fix_guidance"] = guidance

    return detail


def _build_related_files(violation: dict, idx: int) -> list[dict]:
    """为违规构建相关文件列表（FixContextBundle 的一部分）。

    根据违规类型推断修复可能需要涉及的相关文件：
      - SQL 注入 → database.h, database.cpp
      - 密钥硬编码 → 调用 derivedKey() 的文件
      - 头文件违规 → 对应的 .cpp 文件

    Returns:
        [{"path": str, "reason": str}, ...]
    """
    if _state_ref is None:
        return []

    file_list = _state_ref.get("file_list") or []
    file_contents = _state_ref.get("file_contents") or {}
    v_file = violation.get("file", "")
    v_rule = violation.get("rule", "")
    v_dir = os.path.dirname(v_file)
    related: list[dict] = []

    # ── 根据规则类型推断相关文件 ──
    rule_lower = v_rule.lower()

    if "sql" in rule_lower or "参数化" in rule_lower or "注入" in rule_lower:
        # SQL 注入修复可能需要修改 Database 类声明和实现
        for fp in file_list:
            basename = os.path.basename(fp).lower()
            if basename in ("database.h", "database.hpp", "database.cpp"):
                if fp != v_file:
                    related.append({"path": fp, "reason": "Database 类声明/实现"})

    elif "密钥" in rule_lower or "key" in rule_lower or "硬编码" in rule_lower:
        # 密钥修复可能需要修改所有调用 deriveKey 的文件
        for fp in file_list:
            if fp == v_file:
                continue
            content = file_contents.get(fp, "")
            if "deriveKey" in content or "kObfuscatedKey" in content:
                related.append({"path": fp, "reason": "调用密钥派生函数的文件"})

    elif "include" in rule_lower or "头文件" in rule_lower:
        # Include 顺序问题可能需要看相关头文件
        for fp in file_list:
            if fp == v_file:
                continue
            basename = os.path.basename(fp)
            v_basename = os.path.basename(v_file)
            # 同名不同扩展名
            if os.path.splitext(basename)[0] == os.path.splitext(v_basename)[0]:
                related.append({"path": fp, "reason": f"{v_basename} 的对应文件"})

    # ── 同目录默认相关文件（限 3 个）──
    if v_dir:
        count = 0
        for fp in file_list:
            if fp == v_file:
                continue
            if any(r["path"] == fp for r in related):
                continue
            if os.path.dirname(fp) == v_dir:
                basename = os.path.basename(fp)
                related.append({"path": fp, "reason": f"同目录文件: {basename}"})
                count += 1
                if count >= 3:
                    break

    return related[:8]  # 最多返回 8 个相关文件


# ── fix_status 枚举 ──
FIX_STATUS = {
    "pending": "未开始",
    "proposed": "已提交修复方案",
    "passed": "审查通过",
    "failed": "审查不通过",
    "refuted": "🚨 幻觉驳回 — 原始违规声称的代码结构在源文件中不存在",
    "unresolved": "无法自动修复（需人工处理）",
    "infra": "基础设施问题（非代码编辑工具能修）",
}


@tool
def propose_fix(
    idx: int, file: str, line: int,
    fix_before: str, fix_after: str, reason: str,
) -> str:
    """提交一条代码修复方案（单文件、单片段修改）。

    注意：此工具适合局部修改（include 顺序、命名、noexcept 等）。
    对于需要跨文件改动的修复（SQL 参数化、API 变更），请使用 propose_patchset。

    Args:
        idx: 违规索引（对应 get_pending_violations 中的 idx）
        file: 文件路径
        line: 行号
        fix_before: 原始代码（必须从文件中精确复制）
        fix_after: 修复后的代码（必须与 fix_before 有实质不同）
        reason: 修改理由
    """
    rejection = assert_tool_allowed("propose_fix")
    if rejection:
        return rejection
    # ── 硬编码校验：只允许操作分配给当前 agent 的 idx ──
    rejection = _check_idx_allowed(idx)
    if rejection:
        _record_telemetry(idx, "called_propose", True)
        _record_telemetry(idx, "propose_tool", "propose_fix")
        _record_telemetry(idx, "propose_result", "schema_error")
        return rejection

    # ── 硬性 no-op 检查 ──
    before_norm = fix_before.strip().replace(" ", "").replace("\t", "").replace("\n", "")
    after_norm = fix_after.strip().replace(" ", "").replace("\t", "").replace("\n", "")
    if before_norm == after_norm:
        _record_telemetry(idx, "called_propose", True)
        _record_telemetry(idx, "propose_tool", "propose_fix")
        _record_telemetry(idx, "propose_result", "no_op")
        return (
            "❌ 错误：fix_before 与 fix_after 实质相同（no-op），禁止提交。\n"
            "请确保修复代码与原始代码有实质不同：\n"
            "- 不只是改变空格/缩进\n"
            "- 不只是添加/删除注释\n"
            "- 必须修改代码逻辑或语法\n"
            "请重新生成修复方案。如果确实无法产生有效修复，请明确返回 '无法修复' 并说明原因。"
        )
    # ── 检查是否仅添加了注释 ──
    before_lines = [l for l in fix_before.split("\n") if l.strip() and not l.strip().startswith("//")]
    after_lines = [l for l in fix_after.split("\n") if l.strip() and not l.strip().startswith("//")]
    before_joined = "".join(l.replace(" ", "").replace("\t", "") for l in before_lines)
    after_joined = "".join(l.replace(" ", "").replace("\t", "") for l in after_lines)
    if before_joined == after_joined:
        _record_telemetry(idx, "called_propose", True)
        _record_telemetry(idx, "propose_tool", "propose_fix")
        _record_telemetry(idx, "propose_result", "no_op")
        return (
            "❌ 错误：修复方案仅修改了注释，代码逻辑未变（no-op）。\n"
            "请对代码进行实质性修改，不要只改注释。"
        )

    # ── 跨 idx 重复检测：防止模型将同一修复套用到不相关违规 ──
    dup_check = _check_cross_idx_duplicate(idx, fix_before, fix_after, changes=None)
    if dup_check:
        _record_telemetry(idx, "called_propose", True)
        _record_telemetry(idx, "propose_tool", "propose_fix")
        _record_telemetry(idx, "propose_result", "cross_idx_duplicate")
        return dup_check

    plan = {
        "idx": idx,
        "file": file,
        "line": line,
        "fix_before": fix_before,
        "fix_after": fix_after,
        "changes": None,  # 单片段修复不使用 PatchSet
        "reason": reason,
        "fix_status": "proposed",  # 新状态枚举
        "status": 0,               # 兼容旧字段
        "score": 0,
        "feedback": "",
        "suggestion": "",
        "rule_snippet": "",
        "violation_id": _lookup_violation_id(idx),
    }
    _fix_plans_buffer.append(plan)

    # ── 遥测：记录 propose_fix 调用 ──
    _record_telemetry(idx, "called_propose", True)
    _record_telemetry(idx, "propose_tool", "propose_fix")
    _record_telemetry(idx, "propose_result", "success")

    return f"修复方案已提交: #{idx} @ {os.path.basename(file)}:{line}"


@tool
def propose_patchset(
    idx: int,
    changes: list[dict],
    reason: str,
    risk: str = "",
) -> str:
    """提交跨文件修复方案包（PatchSet）。适合需要修改多个文件的修复。

    与 propose_fix 的区别：
      - propose_fix: 单文件、单片段（局部修改）
      - propose_patchset: 多文件、多操作（跨文件重构、API 变更）

    每个 change 的结构：
      {
        "file": str,        # 文件路径
        "operation": str,   # "replace" | "insert_after" | "insert_before" | "delete"
        "anchor": str,      # 锚点代码（定位修改位置），replace 时可为空
        "before": str,      # 原始代码（operation="replace" 时必填）
        "after": str,       # 修改后代码（operation="replace" 时必填）
        "code": str,        # 要插入的代码（operation="insert_*" 时必填）
      }

    Args:
        idx: 违规索引
        changes: 修改列表（至少 1 条），每条是一个文件操作
        reason: 整体修复理由
        risk: 风险评估（可选，建议填写）
    """
    rejection = assert_tool_allowed("propose_patchset")
    if rejection:
        return rejection
    rejection = _check_idx_allowed(idx)
    if rejection:
        _record_telemetry(idx, "called_propose", True)
        _record_telemetry(idx, "propose_tool", "propose_patchset")
        _record_telemetry(idx, "propose_result", "schema_error")
        return rejection

    # ── 验证 ──
    if not changes or not isinstance(changes, list):
        _record_telemetry(idx, "called_propose", True)
        _record_telemetry(idx, "propose_tool", "propose_patchset")
        _record_telemetry(idx, "propose_result", "schema_error")
        return "❌ 错误：changes 必须是非空列表"
    if len(changes) == 0:
        _record_telemetry(idx, "called_propose", True)
        _record_telemetry(idx, "propose_tool", "propose_patchset")
        _record_telemetry(idx, "propose_result", "schema_error")
        return "❌ 错误：changes 不能为空"

    # ── 检查每条 change 是否都是 no-op ──
    all_noop = True
    for i, ch in enumerate(changes):
        op = ch.get("operation", "")
        if op == "replace":
            b = (ch.get("before") or "").strip().replace(" ", "").replace("\t", "").replace("\n", "")
            a = (ch.get("after") or "").strip().replace(" ", "").replace("\t", "").replace("\n", "")
            if b != a and a:
                all_noop = False
                break
        elif op in ("insert_after", "insert_before"):
            code = (ch.get("code") or "").strip()
            if code:
                all_noop = False
                break
        elif op == "delete":
            b = (ch.get("before") or "").strip()
            if b:
                all_noop = False
                break

    if all_noop:
        _record_telemetry(idx, "called_propose", True)
        _record_telemetry(idx, "propose_tool", "propose_patchset")
        _record_telemetry(idx, "propose_result", "no_op")
        return (
            "❌ 错误：PatchSet 中所有 change 都是 no-op（修改前后相同或插入为空）。\n"
            "请确保至少一条 change 产生实质性代码变更。\n"
            "如果确实无法产生有效修复，请明确返回 '无法修复' 并说明原因。"
        )

    # ── 跨 idx 重复检测：防止模型将同一 PatchSet 套用到不相关违规 ──
    dup_check = _check_cross_idx_duplicate(idx, fix_before="", fix_after="", changes=changes)
    if dup_check:
        _record_telemetry(idx, "called_propose", True)
        _record_telemetry(idx, "propose_tool", "propose_patchset")
        _record_telemetry(idx, "propose_result", "cross_idx_duplicate")
        return dup_check

    plan = {
        "idx": idx,
        "file": changes[0]["file"],   # 主文件
        "line": 0,                     # PatchSet 无单一行号
        "fix_before": "",              # 不使用单片段字段
        "fix_after": "",
        "changes": changes,            # 跨文件修改列表
        "reason": reason,
        "risk": risk,
        "fix_status": "proposed",
        "status": 0,                   # 兼容旧字段
        "score": 0,
        "feedback": "",
        "suggestion": "",
        "rule_snippet": "",
        "violation_id": _lookup_violation_id(idx),
    }
    _fix_plans_buffer.append(plan)

    # ── 遥测：记录 propose_patchset 调用 ──
    _record_telemetry(idx, "called_propose", True)
    _record_telemetry(idx, "propose_tool", "propose_patchset")
    _record_telemetry(idx, "propose_result", "success")

    files = set(ch.get("file", "") for ch in changes)
    return f"PatchSet 已提交: #{idx}, 涉及 {len(files)} 个文件, {len(changes)} 处修改"


@tool
def get_pending_fixes() -> list[dict]:
    """获取当前 agent 允许范围内的待审查修复方案。

    仅返回 fix_status 为 "proposed" 或 "failed" 的方案（需要审查的）。
    已通过（passed）、基础设施（infra）、无法修复（unresolved）的不返回。
    每条自动附带 review_checklist（从规范文件精确提取的审查标准）。
    """
    fix_plans = _state_ref.get("fix_plans") or []
    violations = _state_ref.get("merged_violations") or []
    if not fix_plans:
        return []
    allowed = getattr(_thread_local, "allowed_indices", None)
    pending = []
    for i, p in enumerate(fix_plans):
        if p is None:
            continue
        fs = p.get("fix_status", "")
        if fs not in ("proposed", "failed"):
            continue
        if allowed is not None and i not in allowed:
            continue
        raw_changes = p.get("changes")
        truncated_changes = None
        if raw_changes and isinstance(raw_changes, list):
            truncated_changes = []
            for ch in raw_changes[:12]:
                tc = dict(ch)
                for key in ("before", "after", "code"):
                    val = tc.get(key)
                    if isinstance(val, str) and len(val) > 500:
                        tc[key] = val[:500] + "\n... [截断，原文过长]"
                truncated_changes.append(tc)

        entry = {
            "idx": i,
            "file": p.get("file", ""),
            "line": p.get("line", 0),
            "fix_before": p.get("fix_before", "")[:1200],
            "fix_after": p.get("fix_after", "")[:1200],
            "changes": truncated_changes,
            "reason": p.get("reason", "")[:500],
            "risk": p.get("risk", ""),
            "fix_status": fs,
            "score": p.get("score", 0),
            "feedback": p.get("feedback", "")[:300],
            "suggestion": p.get("suggestion", "")[:500],
        }

        # ── 原始违规数据（供 review_agent 反幻觉事实核查）──
        if i < len(violations):
            v = violations[i]
            if v is not None:
                entry["violation"] = {
                    "current": v.get("current", "")[:800],
                    "expected": v.get("expected", "")[:800],
                    "reason": v.get("reason", "")[:500],
                    "rule": v.get("rule", ""),
                    "severity": v.get("severity", ""),
                    "source": v.get("source", ""),
                    "surrounding": v.get("surrounding", "")[:1500],
                }

        # ── L2: review_checklist — 优先复用 checker 传下来的 rule_excerpt ──
        if i < len(violations):
            v = violations[i]
            # 路径 A（主路径）：checker agent 报告违规时已附带规范原文
            excerpt = v.get("rule_excerpt", "")
            section = v.get("rule_section", "")
            if excerpt:
                parts = [f"=== 来源: {section} ==="] if section else []
                parts.append(excerpt)
                entry["review_checklist"] = "=== 审查标准 ===\n" + "\n".join(parts)
            else:
                # 路径 B（fallback）：关键词映射表 + 规范文件提取（兼容历史数据）
                domain = v.get("source", "")
                rule_name = v.get("rule", "")
                if domain and rule_name:
                    checklist = _extract_review_checklist(domain, rule_name)
                    if checklist:
                        entry["review_checklist"] = checklist

        pending.append(entry)
    return pending


@tool
def submit_review(
    idx: int, score: int, passed: bool,
    feedback: str, suggestion: str, rule_snippet: str,
    scoring_criteria: str = "",
) -> str:
    """提交对一条修复方案的审查结果。

    Args:
        idx: 修复方案在 fix_plans 中的索引
        score: 评分 0-10
        passed: 是否通过（score >= 6 应为 True）
        feedback: 审查意见（2-3 句，具体说明为什么给这个分数）
        suggestion: 若未通过，给出具体可执行的修改指令（如"将第X行Y改为Z"），禁止模糊词
        rule_snippet: 相关规范原文摘录
        scoring_criteria: 首次审查必须输出（1-3 条具体可验证条件），后续审查沿用历史标准
    """
    rejection = assert_tool_allowed("submit_review")
    if rejection:
        return rejection
    if _state_ref is None:
        print("  [submit_review] 错误: _state_ref 为 None")
        return "错误：状态未初始化"

    # 硬编码校验：只允许审查分配给当前 agent 的 idx
    rejection = _check_idx_allowed(idx)
    if rejection:
        print(f"  [submit_review] {rejection}")
        return rejection

    fix_plans = _state_ref.get("fix_plans") or []
    if idx < 0 or idx >= len(fix_plans):
        print(f"  [submit_review] 错误: idx={idx} 超出范围 (0-{len(fix_plans)-1})")
        return f"错误：索引 {idx} 超出范围"

    plan = fix_plans[idx]
    if plan is None:
        print(f"  [submit_review] 错误: fix_plans[{idx}] 为 None")
        return f"错误：修复方案 #{idx} 不存在"

    print(f"  [submit_review] idx={idx} score={score} passed={passed} file={plan.get('file','?')[-40:]}")

    plan["score"] = score
    plan["passed"] = passed

    # ── 矛盾候选检测：feedback 中包含 [CONTRADICTION-CANDIDATE] 标记 ──
    cc_match = re.search(
        r'\[CONTRADICTION-CANDIDATE\]\s*(.+?)(?:\n|$)',
        feedback, re.DOTALL,
    )
    if cc_match:
        description = cc_match.group(1).strip()
        with _contradiction_lock:
            violations = (_state_ref or {}).get("merged_violations") or []
            v_info = {}
            if 0 <= idx < len(violations) and violations[idx] is not None:
                v_info = {
                    "rule": violations[idx].get("rule", ""),
                    "severity": violations[idx].get("severity", ""),
                    "current": violations[idx].get("current", "")[:300],
                    "reason": violations[idx].get("reason", "")[:300],
                }
            _contradiction_candidates.append({
                "idx": idx,
                "file": plan.get("file", ""),
                "line": plan.get("line", 0),
                "description": description,
                "violation": v_info,
                "feedback": feedback[:600],
                "fix_after": plan.get("fix_after", "")[:300],
            })
        print(f"  [submit_review] 📋 矛盾候选 #{idx}: {description[:120]}")

    # ── 幻觉检测：feedback 以 🚨 HALLUCINATION DETECTED 开头 → refuted ──
    is_refuted = (
        feedback.startswith("🚨 HALLUCINATION DETECTED")
        or feedback.startswith("HALLUCINATION DETECTED")
    )
    if is_refuted:
        plan["fix_status"] = "refuted"
        plan["passed"] = False
        plan["score"] = 0
        print(f"  [submit_review] 🚨 idx={idx} 被驳回为幻觉（refuted）")
    else:
        plan["fix_status"] = "passed" if passed else "failed"
    plan["status"] = 1 if passed else 0  # 兼容旧字段
    plan["feedback"] = feedback
    plan["suggestion"] = suggestion
    plan["rule_snippet"] = rule_snippet

    # 写本地缓存：直接读写 JSON，不经过 knowledge_cache 复杂 pipeline
    _write_review_cache(idx, plan, score, passed, feedback, suggestion,
                        rule_snippet, scoring_criteria)

    # ── 可观测性：记录违规修复/审查事件 ──
    from code_checker.tracer import get_current_tracer
    tracer = get_current_tracer()
    if tracer:
        iteration = (_state_ref or {}).get("fix_iteration", 0)
        # 优先从 fix_plan 自身取 violation_id（最可靠），回退到 merged_violations
        vid = plan.get("violation_id", "")
        if not vid:
            violations = (_state_ref or {}).get("merged_violations") or []
            if idx < len(violations):
                vid = violations[idx].get("violation_id", "")
        tracer.record_fix(
            violation_id=vid,
            fix_status="passed" if passed else "failed",
            score=score,
            iteration=iteration,
        )

    status = "通过" if passed else "未通过"
    return f"审查 #{idx}: {status} (score={score})"


# ============================================================================
# Mech checker 所有工具列表
# ============================================================================

MECH_TOOLS = [
    read_file,
    search_in_file,
    report_violation,
    list_files,
    check_tab_indentation,
    check_line_width,
    check_header_guard,
    check_using_namespace_in_header,
    check_define_macro,
    check_c_style_array,
    check_throw_spec,
    check_default_lambda_capture,
    check_reinterpret_cast,
    check_virtual_override,
    check_c_variadic,
    check_qt_include_dot_h,
    check_qt_signal_name,
    check_qt_slot_name,
    check_sqlite_pragma_key,
    check_sqlite_kdf,
]

# LLM checker 工具（只读 + 报告 + wiki 查阅）
# 注意: get_rules_text 已从默认列表移除，Agent 优先使用 wiki 索引+拉取模式。
#       函数保留作为回退，单个 agent 可按需添加。
CHECKER_TOOLS = [
    read_file,
    search_in_file,
    report_violation,
    list_files,
    get_wiki_page,
]

# Git agent 工具
GIT_TOOLS = [
    run_git_log,
    read_file,
    report_violation,
    get_wiki_page,
]

# Fix agent 工具
FIX_TOOLS = [
    read_file,
    list_files,
    search_in_file,
    get_rules_text,
    get_pending_violations,
    get_violation_detail,
    propose_fix,
    propose_patchset,
    search_wiki,
    get_wiki_page,
]

# Review agent 工具
REVIEW_TOOLS = [
    read_file,
    list_files,
    search_in_file,
    get_rules_text,
    get_pending_fixes,
    submit_review,
    search_wiki,
    get_wiki_page,
]
