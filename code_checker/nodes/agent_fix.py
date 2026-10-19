"""
agent_fix — 代码修复 Agent（Flash 模型，单条全并行）。

每条违规独立调用，全部并行执行。
取消 chunk 机制：flash 模型在 chunk 内会产生锚定效应，
将第一条违规的修复模板复制到后续违规，导致跨 idx 复用。
"""

import os
from concurrent.futures import as_completed

from code_checker.rate_limiter import RateLimitedExecutor

from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

from code_checker.state import AgentState
from code_checker.config import (
    llm, llm_flash, INFRA_RULES, MAX_CONCURRENCY,
)
from code_checker.context_compaction import CompactionHookFactory
from code_checker.utils import invoke_with_retry
from code_checker.tools import (
    set_state, set_allowed_indices, get_fix_plans_buffer,
    read_file, list_files, search_in_file,
    get_violation_detail, propose_fix, propose_patchset,
    clear_fix_telemetry, get_fix_telemetry,
    search_wiki, get_wiki_page,
    set_agent_name,
)

FIX_SYSTEM_PROMPT = """你是 C++ 代码修复专家。为分配给你的每条违规提出精确的代码修复方案。

=== 工作流程 ===
你会收到一个违规索引列表。对列表中的每条违规依次处理：
  a. 用 get_violation_detail(idx) 获取完整信息（包含 fix_guidance:
     从公司规范文件中精确提取的修复指南——正确示例、错误示例、理由）。
     注意: 无需再调用 get_rules_text，此工具已移除，修复所需规则已自动注入。
  b. 用 read_file 读取违规所在文件，确认周围代码
  c. 【跨文件检查】在构思修复前，判断修复是否会涉及其他文件：
     - 修复调用了某个方法？→ read_file 对应的 .h 文件，确认该方法是否存在
     - 修复改变了类型/签名？→ read_file 对应的 .h 和所有 .cpp，评估影响范围
     - 不确定有哪些相关文件？→ 检查 get_violation_detail 返回的 related_files
     - 不确定符号在哪里定义？→ 用 search_in_file 搜索
  d. 基于跨文件阅读的结果，构思一个在当前代码库 API 范围内可编译的修复方案
  e. 提交修复方案：
     - 单文件局部修改 → 用 propose_fix 提交
     - 跨文件修改（SQL 参数化、API 变更等）→ 用 propose_patchset 提交
全部违规处理完后说明"修复完成"。

=== 强制规则 ===

【规则 1 - 禁止 no-op】fix_after 必须与 fix_before 有实质不同。
   完全相同 = 直接 0 分。propose_patchset 的 changes 也必须有实质变更。

【规则 2 - 必须执行建议】出现 latest_suggestion 时，必须按建议方向执行修改。

【规则 3 - 禁止重复失败路径】history 中标记 [score<6] 的每条修改方向已被驳回，不得重复。

【规则 4 - 满足审查标准】scoring_criteria 中的 checklist 必须逐一满足。

【规则 5 - 精确复制原文】fix_before 必须从文件 surrounding 上下文的 "→" 标记行一字不差复制。

【规则 6 - 先读后写，确认 API 存在】调用任何方法/类之前，必须 read_file 对应的头文件确认其存在。
   禁止假设一个不存在的方法"后面会有人实现"。如果你发现修复需要的 API 不存在：
   a. 换一种当前 API 支持的实现方式
   b. 如果确实无法在当前 API 范围内完成，明确说明需要哪些前置改动，不要提交半成品

【规则 7 - 逐条处理】一次只处理一条违规，提交后再处理下一条。

【规则 8 - 选择正确的工具】
   - 单文件、单行修改（include 顺序、命名、noexcept）→ propose_fix
   - 跨文件修改（SQL 参数化、添加 API、改变调用链）→ propose_patchset
   - 如果拿不准，优先使用 propose_patchset（更灵活）

【规则 9 - 重试时查阅修复模式库】如果这是重试（history 中有 score<6 的驳回记录），
   先调用 search_wiki("违规关键词", domain="fix-patterns") 查找是否有
   历史沉淀的修复模式可以参考。fix-patterns 域包含从过往 run 中积累的
   成功修复案例（代码特征 → 修复步骤），可以帮你一次修对。
   找到相关 pattern 后用 get_wiki_page 读完整内容。"""

FIX_AGENT_TOOLS = [
    read_file, list_files, search_in_file,
    get_violation_detail, propose_fix, propose_patchset,
    search_wiki, get_wiki_page,
]
# 注意: get_rules_text 已移除。修复指南通过 get_violation_detail 的 fix_guidance 字段提供。



def _run_single(
    idx: int, idx_pos: int, total_count: int,
    compaction_factory: CompactionHookFactory = None,
    is_retry: bool = False,
) -> int:
    """修复单条违规（独立调用，无交叉污染）。"""
    set_allowed_indices({idx})
    set_agent_name("fix_agent")

    if compaction_factory:
        compaction_factory.set_chunk(f"{idx_pos}/{total_count}")
    agent = create_react_agent(
        model=llm_flash,
        tools=FIX_AGENT_TOOLS,
        prompt=FIX_SYSTEM_PROMPT,
        pre_model_hook=compaction_factory.hook if compaction_factory else None,
    )

    if is_retry:
        task_msg = (
            f"⚠️ 补跑轮次 — 违规 #{idx} 在上一轮被遗漏，这次必须处理。\n\n"
            f"  1. 调用 get_violation_detail({idx}) 获取详情\n"
            f"  2. 单文件局部修改 → 调用 propose_fix 提交\n"
            f"  3. 跨文件修改 → 调用 propose_patchset 提交\n\n"
            f"禁止提交 no-op（fix_before == fix_after 会被拒绝）。"
        )
    else:
        task_msg = (
            f"修复违规 #{idx}（{idx_pos}/{total_count}）。\n\n"
            f"  1. 用 get_violation_detail({idx}) 获取详情（包含 fix_guidance）\n"
            f"  2. read_file 读取违规所在文件，确认周围代码\n"
            f"  3. 单文件修改 → propose_fix；跨文件修改 → propose_patchset\n\n"
            f"⚠️ 如果提交返回错误（no-op），必须重新生成一个实质不同的修复方案。"
        )

    result = invoke_with_retry(agent, task_msg, f"fix #{idx}")
    return len(result.get("messages", []))


def fix_agent(state: AgentState) -> dict:
    """修复 agent 节点（Flash 模型，单条全并行）。

    每条违规独立调用，全部并行执行（无 chunk 分组）。
    取消 chunk 的原因：flash 模型会将第一条的修复模板锚定到后续违规。
    端到端时延 = max(单条修复耗时)，而非 batch 累加。
    保证：每个待修复违规都有方案（LLM 遗漏的自动补跑，最多 3 轮）。
    """
    iteration = state.get("fix_iteration", 0) + 1
    violations = state.get("merged_violations") or []
    existing_plans = state.get("fix_plans") or []

    # 注意：不重置熔断器。如果 DeepSeek 在 checker 阶段已经连续 503，
    # 进入 fix 阶段不应该清除故障状态——那会让下游重新冲击已确认不可用的服务。
    # 熔断器跨阶段持续跟踪，冷却期满后自动进入半开探测。

    if not violations:
        print("[fix_agent ] 无违规，跳过")
        return {"fix_iteration": iteration, "fix_plans": []}

    # ── 确定待修复索引 ──
    if not existing_plans:
        pending_indices = list(range(len(violations)))
        print(f"[fix_agent ] 首次全量修复（{len(pending_indices)} 条）...")
    else:
        # 只修复 fix_status == "failed"（审查未通过）
        review_failed = [
            i for i, p in enumerate(existing_plans)
            if i < len(violations)
            and p is not None and p.get("fix_status") == "failed"
        ]
        # 从未产出方案的补跑
        never_tried = [
            i for i, p in enumerate(existing_plans)
            if i < len(violations) and p is None
        ]
        if never_tried:
            print(f"[fix_agent ] ⚠️ {len(never_tried)} 条从未产出方案，将补跑")
        pending_indices = never_tried + review_failed

        if not pending_indices:
            # 统计各状态数量
            status_counts: dict[str, int] = {}
            for p in existing_plans:
                if p is not None:
                    fs = p.get("fix_status", "?")
                    status_counts[fs] = status_counts.get(fs, 0) + 1
            summary = ", ".join(f"{k}={v}" for k, v in sorted(status_counts.items()))
            print(f"[fix_agent ] 全部已修复，跳过（{summary}）")
            return {"fix_iteration": iteration, "fix_plans": existing_plans}

        # ── 状态守卫：只允许 failed 和 None 进入 ──
        illegal = [
            i for i in pending_indices
            if existing_plans[i] is not None
            and existing_plans[i].get("fix_status") not in ("failed",)
        ]
        if illegal:
            illegal_statuses = [(i, existing_plans[i].get("fix_status")) for i in illegal]
            print(f"[fix_agent ] ⚠️ 状态机异常：{len(illegal)} 条非 failed 进入 retry: "
                  f"{illegal_statuses}，已过滤")
            pending_indices = [i for i in pending_indices if i not in set(illegal)]

        print(f"[fix_agent ] 重改 {len(pending_indices)} 条"
              f"（审查未过 {len(review_failed)}, 补跑 {len(never_tried)}）"
              f" 第{iteration}次迭代...")

    # ── 初始化 fix_plans ──
    if not existing_plans:
        all_plans: list = [None] * len(violations)
    else:
        all_plans = list(existing_plans)

    # ── 基础设施类违规 / informational 违规：不进入 fix/review ──
    infra_skipped = 0
    for i, v in enumerate(violations):
        rule = v.get("rule", "")
        severity = v.get("severity", "")
        if rule in INFRA_RULES or severity == "info":
            skip_reason = ("[infra] 基础设施类违规，需人工处理"
                          if rule in INFRA_RULES
                          else "[info] Git/流程类违规，fix agent 无法自动修复")
            all_plans[i] = {
                "idx": i,
                "file": v.get("file", ""),
                "line": v.get("line", 0),
                "fix_before": v.get("current", ""),
                "fix_after": v.get("current", ""),
                "changes": None,
                "reason": skip_reason,
                "fix_status": "infra",
                "status": 1,
                "score": 0,
                "feedback": f"跳过：规则 '{rule}' 不属于可自动修复的源代码问题",
                "suggestion": "",
            }
            infra_skipped += 1
    if infra_skipped:
        print(f"[fix_agent ] {infra_skipped} 条非源代码违规已标记 infra（不进入 fix/review）")
        pending_indices = [i for i in pending_indices
                          if violations[i].get("rule", "") not in INFRA_RULES
                          and violations[i].get("severity", "") != "info"]

    # ── 每条违规独立处理，全部并行（无 chunk，无复杂度分拣）──
    MAX_PROPOSAL_RETRIES = 3
    retry_round = 0
    total_new = 0

    while pending_indices and retry_round < MAX_PROPOSAL_RETRIES:
        retry_round += 1
        if retry_round > 1:
            print(f"[fix_agent ] 补跑轮次 {retry_round}/{MAX_PROPOSAL_RETRIES}: "
                  f"{len(pending_indices)} 条仍未产出方案")

        total_count = len(pending_indices)
        if retry_round == 1:
            print(f"[fix_agent ] {total_count} 条违规 → {total_count} 路并行修复")

        # ── 标记已有方案 & 清空遥测 ──
        state["fix_plans"] = all_plans
        set_state(state)
        clear_fix_telemetry()

        max_workers = min(total_count, MAX_CONCURRENCY)  # 全并行，时延 = max(单条耗时)
        compaction_factory = CompactionHookFactory(
            "fix_agent",
            critical_tool_names={"get_violation_detail", "propose_fix",
                                 "propose_patchset"},
            l4_model=llm,
        )
        with RateLimitedExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(
                    _run_single, idx, pos + 1, total_count, compaction_factory,
                    is_retry=(retry_round > 1),
                )
                for pos, idx in enumerate(pending_indices)
            ]
            for f in as_completed(futures):
                try:
                    f.result()
                except Exception as e:
                    print(f"  [fix_agent ] 修复异常: {e}")

        # ── 收集结果 ──
        allowed = set(pending_indices)
        new_plans = get_fix_plans_buffer()
        for p in new_plans:
            target_idx = p.pop("idx", None)
            if not (isinstance(target_idx, int) and 0 <= target_idx < len(all_plans)):
                continue
            if target_idx not in allowed:
                print(f"  [fix_agent ] ⚠️ 拒绝越界方案 idx={target_idx}")
                continue
            p.setdefault("fix_status", "proposed")
            p.setdefault("status", 0)
            p.setdefault("score", 0)
            p.setdefault("feedback", "")
            p.setdefault("suggestion", "")
            p.setdefault("rule_snippet", "")
            p.setdefault("changes", None)
            if all_plans[target_idx] is None:
                total_new += 1
            all_plans[target_idx] = p

        # ── 遥测报告 ──
        telemetry = get_fix_telemetry()
        _print_telemetry_report(pending_indices, telemetry, violations)

        # ── 检查遗漏 ──
        pending_indices = [i for i in pending_indices if all_plans[i] is None]

    # ── 兜底：标记仍无方案的为 unresolved ──
    if pending_indices:
        print(f"[fix_agent ] ⚠️ {len(pending_indices)} 条经 "
              f"{MAX_PROPOSAL_RETRIES} 轮补跑仍无方案，标记 unresolved: {pending_indices}")
        for i in pending_indices:
            v = violations[i]
            all_plans[i] = {
                "idx": i,
                "file": v.get("file", ""),
                "line": v.get("line", 0),
                "fix_before": v.get("current", ""),
                "fix_after": v.get("current", ""),
                "reason": "[fix_agent] LLM 无法生成修复方案",
                "fix_status": "unresolved",
                "status": 0,
                "score": 0,
                "feedback": "LLM 经 3 轮补跑仍无法为此违规生成修复方案。需人工审查。",
                "suggestion": "",
                "changes": None,
            }

    total_count = sum(1 for p in all_plans if p is not None)
    print(f"[fix_agent ] 完成: {total_count}/{len(all_plans)} 条方案"
          f"（本轮新增 {total_new}）")
    return {"fix_plans": all_plans, "fix_iteration": iteration}


def _print_telemetry_report(
    pending_indices: list[int],
    telemetry: dict[int, dict],
    violations: list[dict],
) -> None:
    """打印 per-chunk 修复遥测：每个 idx 的工具调用和失败原因。"""
    if not telemetry:
        print("  [遥测] 无工具调用记录（所有 idx 均未被 LLM 接触）")
        return

    no_call = []
    no_op = []
    schema_err = []
    cross_idx_dup = []  # 跨 idx 重复套用
    success = []
    detail_only = []  # 调了 get_violation_detail 但没调 propose

    for idx in sorted(pending_indices):
        t = telemetry.get(idx, {})
        called_detail = t.get("called_get_detail", False)
        called_propose = t.get("called_propose", False)
        result = t.get("propose_result", "")

        if not called_detail and not called_propose:
            no_call.append(idx)
        elif called_detail and not called_propose:
            detail_only.append(idx)
        elif called_propose:
            if result == "no_op":
                no_op.append(idx)
            elif result == "cross_idx_duplicate":
                cross_idx_dup.append(idx)
            elif result == "schema_error":
                schema_err.append(idx)
            elif result == "success":
                success.append(idx)

    # 只打印有问题的
    if no_call:
        rules = [violations[i].get("rule", "?") for i in no_call]
        print(f"  [遥测] 未接触: {len(no_call)} 条 — LLM 从未调用工具: "
              f"{list(zip(no_call, rules))}")
    if detail_only:
        rules = [violations[i].get("rule", "?") for i in detail_only]
        print(f"  [遥测] 只读未修: {len(detail_only)} 条 — 调了 get_detail 但未提交修复: "
              f"{list(zip(detail_only, rules))}")
    if no_op:
        rules = [violations[i].get("rule", "?") for i in no_op]
        print(f"  [遥测] no-op: {len(no_op)} 条 — 提交了但被拒绝（修改前后相同）: "
              f"{list(zip(no_op, rules))}")
    if schema_err:
        rules = [violations[i].get("rule", "?") for i in schema_err]
        print(f"  [遥测] schema 错误: {len(schema_err)} 条: "
              f"{list(zip(schema_err, rules))}")
    if cross_idx_dup:
        rules = [violations[i].get("rule", "?") for i in cross_idx_dup]
        print(f"  [遥测] 跨idx复用: {len(cross_idx_dup)} 条 — 相同修复套用到不同违规: "
              f"{list(zip(cross_idx_dup, rules))}")

    if success:
        tools_used = {}
        for idx in success:
            t = telemetry.get(idx, {})
            tool_name = t.get("propose_tool", "?")
            tools_used[tool_name] = tools_used.get(tool_name, 0) + 1
        tools_str = ", ".join(f"{k}={v}" for k, v in tools_used.items())
        print(f"  [遥测] 成功: {len(success)} 条 ({tools_str})")
