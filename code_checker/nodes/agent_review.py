"""
agent_review — 修复方案审查 Agent（Pro 模型，每条独立并行）。

使用 deepseek-v4-flash 审查修复方案。
每条违规独立调 LLM，全量并行（不切 chunk）。
端到端时延 = max(单条审查耗时)，而非 batch 累加。
"""

import os
from concurrent.futures import as_completed

from code_checker.rate_limiter import RateLimitedExecutor

from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

from code_checker.state import AgentState
from code_checker.config import (
    llm, MAX_CONCURRENCY, is_complex_fix_plan,
)
from code_checker.context_compaction import CompactionHookFactory

from code_checker.utils import invoke_with_retry
from code_checker.tools import (
    set_state, set_allowed_indices,
    read_file, get_pending_fixes, submit_review,
    set_agent_name,
)

PASS_THRESHOLD = 6

REVIEW_SYSTEM_PROMPT = f"""你是 C++ 代码审查专家。审查分配给你的每条修复方案是否正确有效。

=== 🚨 反幻觉 Gate（Step 0 — 最高优先级，必须首先执行）===

在你对修复方案评分之前，必须**先验证原始违规是否真实存在于源代码中**。
上一个 checker agent 可能产生幻觉——声称了不存在的代码结构、虚构的类成员、
凭空生成的数值。你的第一职责是拦截这些幻觉，不让它们流入报告。

对每条待审查的违规，执行以下事实核查：

  a. 用 get_pending_fixes 获取方案详情。
     注意返回结果中新增的 violation 字段（包含原始违规的 current, expected,
     reason, rule, line, surrounding——这些是 checker agent 声称发现的问题）
  b. 用 read_file 读取违规所在文件
  c. 定位到违规声称的行号，逐项比对：
     - violation.current 中的代码是否与文件中对应行号的代码匹配？
     - violation 声称存在的语法结构（#include、类成员、常量、类型转换、
       throw() 规范、(=]/[&] 默认捕获等）在源文件中是否真实存在？
     - violation 声称的数值（如 "1e12"、"256000"）是否与源文件一致？
     - 违规行号是否指向有效代码行（非空行、非纯注释行）？
  d. 若任一项不匹配 → 判定为 🚨 HALLUCINATION：
     - submit_review: score=0, passed=false
     - feedback 必须以 "🚨 HALLUCINATION DETECTED:" 开头，后面说明：
       (1) 原始违规声称了什么（引用 violation.current 和 violation.reason）
       (2) 源代码中实际是什么（引用 read_file 看到的真实代码）
       (3) 具体哪一项事实不匹配
     - suggestion 中给出证据对比（"声称: ..." vs "实际: ..."）
     - ⛔ 停止！不进入后续的修复方案评分流程。不要给修复方案打分。
  e. 仅当 Step 0 全部通过（违规确实存在），才进入下面的正常评分流程

=== 常见幻觉模式（Step 0 重点识别）===
1. "缺少 #include <XXX>" — 但该头文件在第 N 行已是前置声明 class XXX; 而非 include
2. "static constexpr 成员与匿名命名空间常量同名冲突" — 但类中查无此静态成员
3. "值冲突（如 1e12 vs 1e15）" — 但声称的冲突值在代码仓库中不存在
4. "应使用 XXX 替代 YYY" — 但 YYY（声称的"当前代码"）在该行并不存在
5. 违规行号指向空行、注释行、或根本不包含声称的语法结构
6. violation.current 与文件中对应行明显不同（可能是 checker agent 摘录错误或虚构）

=== 工作流程（Step 0 通过后）===
你会收到一个修复方案索引列表。对列表中的每条逐一审查：
  a. 先用 read_file 读取对应文件，确认 fix_before 是否与文件中代码一致
  b. 用 get_pending_fixes 获取方案详情（包含 review_checklist:
     从公司规范文件中精确提取的审查标准和检查清单）。
     注意: 无需再调用 get_rules_text，此工具已移除，审查标准已自动注入。
  c. 逐条对照以下维度评分
  d. 用 submit_review 提交审查结果

=== 评分维度（0-10）===
1. 正确性 — 是否真正解决违规（对照规范逐条检查）
2. 完整性 — 是否覆盖所有相关代码
3. 无副作用 — 是否引入新问题（内存泄漏、逻辑错误、编译错误）
4. 风格一致 — 是否遵循项目风格

=== 评分规则 ===
- fix_before == fix_after（完全相同）→ 直接 0 分，feedback "no-op：修复前后代码完全相同"
- 修复方向与违规规则无关 → 0-2 分，feedback 明确指出方向错误
- 修复方向正确但不完整 → 3-5 分，suggestion 给出补全步骤
- 修复正确但有轻微风格问题 → 6-7 分
- 修复完全正确 → 8-10 分
- score ≥ {PASS_THRESHOLD} 视为通过（passed=true）

=== 规范矛盾检测 ===

当你发现两条规范之间存在不可调和的矛盾时，标记为矛盾候选，
让系统记录并反馈到规范文档中。

触发条件（满足任一即标记）：
1. 修复方案技术上正确（按规范A应该这样修），但修后违反另一条规范B
2. 违规根因是规范本身冲突（如 Allman vs K&R），无论如何修都得罪一方
3. 同一条规范内部不同章节自相矛盾（如 §1.1 要求 camelCase
   但 §11.2 示例用 snake_case），修复只能择一而从

常见场景：
- C++ 裸 new 禁令 vs Qt 父子模型 new QWidget(this)
- C++ Allman 大括号 vs Qt K&R 大括号
- C++ §1.1 camelCase vs §11.2 测试命名 snake_case

标记方式 — 在 feedback 末尾追加一行:
[CONTRADICTION-CANDIDATE] <规范A条款> vs <规范B条款>: <一句话描述>

示例 feedback 结尾:
修复方案正确，但存在规范间矛盾。
[CONTRADICTION-CANDIDATE] C++ §7 禁止裸new vs Qt §4.4 父子模型: Qt 控件构造 new QLabel(this) 是标准实践，无法用智能指针替代，两条规范不可调和

⚠️ 矛盾候选 ≠ 幻觉。违规真实存在，只是规范本身冲突。
  正常完成评分流程（按你的判断给出裁决），同时在 feedback 末尾加标记即可。

=== submit_review 参数说明 ===
- idx: 修复方案索引
- score: 0-10 整数评分
- passed: score >= {PASS_THRESHOLD} 时填 true；幻觉驳回时填 false
- feedback: 2-3 句具体评价。幻觉驳回时必须以 "🚨 HALLUCINATION DETECTED:" 开头
- suggestion: 未通过时必须给出具体可执行修改指令，禁止模糊词。通过可为空。
  幻觉驳回时给出证据对比（"声称: ..." vs "实际: ..."）
- rule_snippet: 从规范原文中摘录最相关条款
- scoring_criteria: 首次审查必须输出 1-3 条具体可验证条件，后续审查沿用

=== 重要 ===
- Step 0 反幻觉核查不可跳过 — 这是你最重要的职责
- 一次只审查一条
- 首次审查必须给出 scoring_criteria
- suggestion 必须可执行，拒绝"请确认"/"请核实"/"检查"等模糊词"""

REVIEW_AGENT_TOOLS = [
    read_file, get_pending_fixes, submit_review,
]
# 注意: get_rules_text 已移除。审查标准通过 get_pending_fixes 的 review_checklist 字段提供。


def _run_single_review(
    idx: int, idx_pos: int, total_count: int,
    compaction_factory: CompactionHookFactory = None,
    is_patchset: bool = False,
) -> int:
    """在单个线程中运行一个 subagent，审查单条修复方案。"""
    set_allowed_indices({idx})
    set_agent_name("review_agent")

    if compaction_factory:
        label = f"ps{idx_pos}" if is_patchset else f"{idx_pos}/{total_count}"
        compaction_factory.set_chunk(label)
    agent = create_react_agent(
        model=llm,
        tools=REVIEW_AGENT_TOOLS,
        prompt=REVIEW_SYSTEM_PROMPT,
        pre_model_hook=compaction_factory.hook if compaction_factory else None,
    )

    if is_patchset:
        task_msg = (
            f"🔍 跨文件 PatchSet 审查（#{idx_pos}/{total_count}）。"
            f"审查违规 #{idx} 的跨文件修复方案：\n\n"
            f"  1. 用 get_pending_fixes 获取方案（注意 changes 字段中每条 change 的 before/after）\n"
            f"  2. 对 PatchSet 涉及的所有文件都 read_file 确认上下文\n"
            f"  3. 检查跨文件一致性：新增的 API 是否在头文件中声明，调用点是否都更新\n"
            f"  4. 对照 get_pending_fixes 返回的 review_checklist（已自动注入），"
            f"最后 submit_review 提交\n\n"
            f"⚠️ 跨文件修改经常遗漏头文件更新或调用点适配，请重点检查这些。"
        )
    else:
        task_msg = (
            f"审查修复方案 #{idx}（{idx_pos}/{total_count}）。\n\n"
            f"先用 get_pending_fixes 获取方案的 fix_before/fix_after，"
            f"再用 read_file 读对应文件确认代码上下文，"
            f"最后 submit_review 提交审查结果。"
        )

    result = invoke_with_retry(agent, task_msg, f"review #{idx}",
                               config={"recursion_limit": 120})
    return len(result.get("messages", []))


def review_agent(state: AgentState) -> dict:
    """审查 agent 节点（Pro 模型，每条违规独立并行，不切 chunk）。

    端到端时延 = max(单条审查耗时)，而非 batch 累加。
    submit_review 直接写入 state 中对应索引的 fix_plan。
    """
    fix_plans = state.get("fix_plans") or []
    iteration = state.get("fix_iteration", 1)

    if not fix_plans:
        print("[review_agent] 无方案，跳过")
        return {}

    # ── 区分 fix_status：只审查 proposed 和 failed ──
    pending = [
        i for i, p in enumerate(fix_plans)
        if p is not None
        and p.get("fix_status", "") in ("proposed", "failed")
    ]

    # 统计跳过项
    status_counts: dict[str, int] = {}
    for p in fix_plans:
        if p is not None:
            fs = p.get("fix_status", "?")
            status_counts[fs] = status_counts.get(fs, 0) + 1
    skip_parts = [
        f"{k}={v}" for k, v in sorted(status_counts.items())
        if k not in ("proposed", "failed")
    ]
    skip_str = f", 跳过: {', '.join(skip_parts)}" if skip_parts else ""

    # 区分首次审查与重审
    first_review = [i for i in pending if not fix_plans[i].get("feedback")]
    re_review = [i for i in pending if i not in first_review]
    detail = f"首次 {len(first_review)}" if first_review else ""
    if re_review:
        detail = f"{detail}, 重审 {len(re_review)}" if detail else f"重审 {len(re_review)}"
    print(f"[review_agent] 待审查 {len(pending)}/{len(fix_plans)} 条（{detail}）{skip_str}")

    if not pending:
        print("[review_agent] 全部已审查，跳过")
        return {}

    # 注意：不重置熔断器。如果 DeepSeek 在 fix 阶段已经连续 503，
    # 进入 review 阶段不应该清除故障状态并立即再放出最多 20 个任务。
    # 熔断器跨阶段持续跟踪，冷却期满后自动进入半开探测。

    set_state(state)

    total_count = len(pending)
    max_workers = min(total_count, MAX_CONCURRENCY)
    print(f"[review_agent] {total_count} 条 → {total_count} 路并行"
          f"（并发上限 {max_workers}）")

    compaction_factory = CompactionHookFactory(
        "review_agent",
        critical_tool_names={"get_pending_fixes", "submit_review"},
        l4_model=llm,
    )
    failed_count = 0
    with RateLimitedExecutor(max_workers=max_workers) as executor:
        future_to_idx = {
            executor.submit(
                _run_single_review, idx, pos + 1, total_count, compaction_factory,
                is_patchset=is_complex_fix_plan(fix_plans[idx]),
            ): idx
            for pos, idx in enumerate(pending)
        }
        for f in as_completed(future_to_idx):
            idx = future_to_idx[f]
            try:
                f.result()
            except Exception as e:
                failed_count += 1
                print(f"  [review_agent] #{idx} 审查异常: {e}")
                # ── 安全门禁：失败的单条 plan 标记 unreviewed ──
                if 0 <= idx < len(fix_plans) and fix_plans[idx] is not None:
                    fs = fix_plans[idx].get("fix_status", "")
                    if fs in ("proposed", "failed"):
                        fix_plans[idx]["fix_status"] = "unreviewed"
                        fix_plans[idx]["score"] = 0
                        fix_plans[idx]["feedback"] = (
                            "⚠️ 审查不可用：review_agent 因 API 故障未能执行。"
                            "该修复方案未经审查，请人工验证。"
                        )

    # ── 记录降级 ──
    if failed_count > 0:
        log = list(state.get("degradation_log") or [])
        log.append({
            "stage": "review_agent",
            "status": "degraded" if failed_count < total_count else "failed",
            "reason": f"{failed_count}/{total_count} 条审查 API 调用失败",
            "impact": "失败的修复方案标记为 unreviewed，需人工审查",
        })
        state["degradation_log"] = log

    # submit_review 直接写入了 _state_ref["fix_plans"][idx]，无需搬运
    passed = sum(1 for p in fix_plans if p is not None and p.get("fix_status") == "passed")
    failed = sum(1 for p in fix_plans if p is not None and p.get("fix_status") == "failed")
    unresolved = sum(1 for p in fix_plans if p is not None and p.get("fix_status") == "unresolved")
    infra = sum(1 for p in fix_plans if p is not None and p.get("fix_status") == "infra")
    never_tried = sum(1 for p in fix_plans if p is None)
    summary = f"通过 {passed}, 未通过 {failed}"
    if unresolved:
        summary += f", 无法修复 {unresolved}"
    if infra:
        summary += f", 基础设施 {infra}"
    if never_tried:
        summary += f", 未产出方案 {never_tried}"
    print(f"[review_agent] 完成: {summary}")

    return {}
