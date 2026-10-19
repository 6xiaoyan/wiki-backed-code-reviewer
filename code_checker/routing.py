"""
路由逻辑：Send 扇出 + 条件边（Agent 架构）。

  fanout_to_checkers_v2  — 将 repo_scanner 产出并行分发给 4 个 checker agent
  route_after_critique_v2 — review_agent 后决定：回修 或 输出报告
"""

from langgraph.types import Send
from code_checker.state import AgentState
from code_checker.config import MAX_FIX_ITERATIONS


def fanout_to_checkers_v2(state: AgentState) -> list[Send]:
    """将扫描结果并行扇出到四个 checker agent（按规范域拆分）。

    每个 agent 接收完整 state（含 file_contents），
    独立运行自己的工具集：
      cpp:    C++ 正则 + LLM 审查
      qt:     Qt 正则 + LLM 审查
      git:    Git 提交规范审查
      sqlite: SQLite 正则 + LLM 安全审查
    """
    print("[路由] 四路 Agent Send 并行扇出...")

    payload = {
        "repo_path": state["repo_path"],
        "file_list": state.get("file_list"),
        "file_contents": state.get("file_contents"),
    }

    return [
        Send("cpp_agent", {**payload}),
        Send("qt_agent", {**payload}),
        Send("git_agent", {**payload}),
        Send("sqlite_agent", {**payload}),
    ]


def route_after_critique_v2(state: AgentState) -> str:
    """review_agent 后的条件路由。

    决策逻辑:
      1. 无修复方案 → 直接输出报告
      2. 全部通过 / unresolved / infra / unreviewed → 输出报告（不需要再改）
      3. 已达最大迭代次数 → 强制输出报告
      4. 仍有 failed（审查未通过）→ 返回 fix_agent 重改

    重要：LangGraph 条件边不合并 routing 函数中的 state 修改。
    因此 run_incomplete 标记由 report_exporter 节点从 fix_plans 数据计算，
    不在此处写入 state。
    """
    fix_plans = state.get("fix_plans") or []
    iteration = state.get("fix_iteration", 1)

    if not fix_plans:
        print("[路由] ⚠️ 无修复方案（fix 阶段整体故障？），运行不完整")
        return "report_exporter"

    # ── 统计所有终态 ──
    def count_status(status: str) -> int:
        return sum(1 for p in fix_plans if p is not None and p.get("fix_status") == status)

    failed = count_status("failed")
    unreviewed = count_status("unreviewed")
    proposed = count_status("proposed")
    null_count = sum(1 for p in fix_plans if p is None)

    # ── 异常状态告警（仅日志，不修改 state）──
    if proposed:
        print(f"[路由] ⚠️ {proposed} 条方案仍为 proposed（审查未执行），"
              f"运行不完整")
    if unreviewed:
        print(f"[路由] ⚠️ {unreviewed} 条审查不可用（API 故障），"
              f"这些方案需人工验证，运行不完整")
    if null_count:
        print(f"[路由] ⚠️ {null_count} 条从未产出修复方案（fix_agent 遗漏），"
              f"运行不完整")

    # ── 只有 fix_status="failed" 才返回重改 ──
    # unresolved/infra/passed/unreviewed/refuted 都不会进入 fix_agent
    if not failed:
        passed = count_status("passed")
        unresolved = count_status("unresolved")
        infra = count_status("infra")
        refuted = count_status("refuted")
        detail_parts = [f"通过 {passed}"]
        if failed:
            detail_parts.append(f"未通过 {failed}")
        if unresolved:
            detail_parts.append(f"需人工处理 {unresolved}")
        if infra:
            detail_parts.append(f"基础设施 {infra}")
        if refuted:
            detail_parts.append(f"🚨 幻觉驳回 {refuted}")
        is_incomplete = bool(unreviewed or proposed or null_count)
        if is_incomplete:
            detail_parts.append("⚠️ 运行不完整")
        print(f"[路由] {'/'.join(detail_parts)} → 生成报告")
        return "report_exporter"

    if iteration >= MAX_FIX_ITERATIONS:
        print(f"[路由] 已达上限({MAX_FIX_ITERATIONS}次), {failed}条仍未通过, 强制放行")
        if unreviewed or proposed or null_count:
            print(f"[路由] ⚠️ 运行不完整（"
                  f"未通过{failed}, 审查不可用{unreviewed}, "
                  f"未审查{proposed}, 无方案{null_count}）")
        return "report_exporter"

    print(f"[路由] {failed} 条未通过 → 返回 fix_agent 重改...")
    return "fix_agent"
