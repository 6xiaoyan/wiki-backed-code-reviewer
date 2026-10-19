"""
report_exporter — 生成合规审查报告 + 修复指南接口。

产出两份文档：
  1. compliance_report.md — 人类阅读的完整流程报告
  2. fix_guide.md         — 给 Claude 的结构化修复执行指南（当前为桩，待后续完善）
"""

import os
from code_checker.state import AgentState
from code_checker.config import OUTPUT_REPORT_FILENAME

_SEVERITY_ICONS: dict[str, str] = {
    "critical": "[CRIT]",
    "warning": "[WARN]",
    "suggestion": "[SUGG]",
    "info": "[INFO]",
}


def report_exporter(state: AgentState) -> dict:
    print("[报告导出] 启动...")

    violations: list[dict] = state.get("merged_violations") or []
    fix_plans: list[dict] = state.get("fix_plans") or []
    format_fix_log: list[dict] = state.get("format_fix_log") or []
    iteration: int = state.get("fix_iteration", 1)
    degradation_log: list[dict] = state.get("degradation_log") or []
    offline_mode: bool = state.get("offline_mode", False)

    # ── 统计 ──
    crit = sum(1 for v in violations if v.get("severity") == "critical")
    warn = sum(1 for v in violations if v.get("severity") == "warning")
    sugg = sum(1 for v in violations if v.get("severity") == "suggestion")
    info_cnt = sum(1 for v in violations if v.get("severity") == "info")
    fmt_count = len(format_fix_log)

    # 按 fix_status 统计
    passed = sum(1 for p in fix_plans if p is not None and p.get("fix_status") == "passed")
    unresolved = sum(1 for p in fix_plans if p is not None and p.get("fix_status") == "unresolved")
    infra = sum(1 for p in fix_plans if p is not None and p.get("fix_status") == "infra")
    failed = sum(1 for p in fix_plans if p is not None and p.get("fix_status") == "failed")
    unreviewed = sum(1 for p in fix_plans if p is not None and p.get("fix_status") == "unreviewed")
    degraded = sum(1 for p in fix_plans if p is not None and p.get("fix_status") == "degraded")
    proposed = sum(1 for p in fix_plans if p is not None and p.get("fix_status") == "proposed")
    null_plans = sum(1 for p in fix_plans if p is None)
    # 兼容旧 status
    if not any(p is not None and p.get("fix_status") for p in fix_plans):
        passed = sum(1 for p in fix_plans if p is not None and p.get("status") == 1)
        unresolved = 0
        infra = 0
    total = len(fix_plans)

    # ── 完整性门禁：由 report_exporter 节点计算并返回，LangGraph 才会提交到最终状态 ──
    # routing 函数中无法写入 state（条件边不合并 state 变更）
    run_incomplete = bool(unreviewed or proposed or null_plans or (
        not fix_plans and violations  # 有违规但无修复方案 = fix 阶段整体故障
    ))

    # ── 事实核验统计（在修复概览表中引用）──
    # 使用显式 _fact_check_status 字段计数，而非减法推断。
    # 每条 violation 在 _fact_check_violations() 中已被标记为:
    #   "verified" | "unverified" | "skipped" | "refuted"
    refuted_violations: list[dict] = state.get("refuted_violations") or []
    refuted_count = len(refuted_violations)
    unverified_count = sum(
        1 for v in violations
        if v.get("_fact_check_status") == "unverified"
    )
    verified_count = sum(
        1 for v in violations
        if v.get("_fact_check_status") == "verified"
    )
    skipped_fact_check_count = sum(
        1 for v in violations
        if v.get("_fact_check_status") == "skipped"
    )

    # ── 覆盖率统计 ──
    coverage_ledger = state.get("coverage_ledger") or {}
    cov_total = len(coverage_ledger.get("required_checks", []))
    cov_completed = len(coverage_ledger.get("completed_checks", []))
    cov_complete = coverage_ledger.get("coverage_complete", False)
    pipeline_errors = state.get("pipeline_errors") or []

    # ── 计算综合可信度 ──
    has_degradation = any(
        e.get("status") in ("degraded", "skipped", "failed")
        for e in degradation_log
    )
    is_offline_run = offline_mode
    all_llm_failed = all(
        e.get("status") in ("skipped", "failed")
        for e in degradation_log
        if e.get("stage") not in ("deterministic_checker", "format_fixer", "report_exporter")
    ) if degradation_log else False

    if is_offline_run or all_llm_failed:
        confidence_level = "🔴 LOW — 仅确定性检查可用，LLM 语义审查和修复方案审查均未执行"
    elif run_incomplete:
        confidence_level = (
            "🔴 LOW — 运行不完整：存在未经审查、审查未执行或无修复方案的违规，"
            "报告结果不可声称'已通过'"
        )
    elif has_degradation:
        confidence_level = "🟡 MEDIUM — 部分 LLM 阶段降级，详见下方运行状态"
    elif unverified_count > 0:
        confidence_level = (
            "🟡 MEDIUM — 存在无法核验的违规（缺少可核验的代码证据），"
            "不排除为幻觉，需人工确认后方可声称'已通过'"
        )
    else:
        confidence_level = "🟢 HIGH — 所有阶段正常运行"

    # ═══════════════════════════════════════════════════════════
    #  1. compliance_report.md（人类阅读）
    # ═══════════════════════════════════════════════════════════
    lines: list[str] = [
        "# 代码规范审查报告",
        "",
        f"**仓库**: {state['repo_path']}",
        f"**规范**: C++ / Qt / Git / SQLite",
        f"**迭代**: {iteration}次",
        f"**严重度**: 🔴 Critical {crit} | 🟡 Warning {warn} | 🔵 Suggestion {sugg} | ⚪ Info {info_cnt}",
        f"**综合可信度**: {confidence_level}",
        "",
    ]

    # ── 降级横幅 ──
    if degradation_log:
        lines += [
            "## ⚠️ 运行状态",
            "",
        ]
        if is_offline_run:
            lines.append("**运行模式**: 🔒 离线模式（零 API 调用）")
            lines.append("")
        lines += [
            "| 阶段 | 状态 | 说明 |",
            "|------|------|------|",
        ]
        # 定义所有已知阶段的顺序
        known_stages = [
            "deterministic_checker", "cpp_agent", "qt_agent",
            "git_agent", "sqlite_agent", "report_merger",
            "format_fixer", "fix_agent", "review_agent",
            "report_exporter",
        ]
        logged_stages = {e["stage"]: e for e in degradation_log}
        for stage in known_stages:
            if stage in logged_stages:
                e = logged_stages[stage]
                icon = {"ok": "✅", "degraded": "⚠️", "skipped": "⏭️", "failed": "❌"}.get(
                    e.get("status", ""), "❓")
                lines.append(f"| {stage} | {icon} {e.get('status', '?')} | {e.get('reason', '?')} |")
            else:
                lines.append(f"| {stage} | ✅ 正常 | - |")
        lines.append("")
        lines.append(f"**综合可信度**: {confidence_level}")
        lines.append("")

    lines += [
        "## 覆盖率",
        "",
        f"| 指标 | 数量 |",
        f"|------|------|",
        f"| 必检项 | {cov_total} |",
        f"| 已完成 | {cov_completed} |",
        f"| 覆盖率 | {_pct(cov_completed, cov_total)} |",
        f"| 状态 | {'✅ 达标' if cov_complete else '❌ 未达标'} |",
        "",
        "## 修复概览",
        "",
        f"| 指标 | 数量 |",
        f"|------|------|",
        f"| 总违规 | {len(violations)} |",
        f"| 自动修复 (format_fixer) | {fmt_count} |",
        f"| 修复方案总数 | {total} |",
        f"| 已通过 | {passed} |",
    ]
    if unresolved:
        lines.append(f"| 无法自动修复（需人工） | {unresolved} |")
    if infra:
        lines.append(f"| 基础设施问题 | {infra} |")
    if failed:
        lines.append(f"| 审查不通过 | {failed} |")
    if unreviewed:
        lines.append(f"| ⚠️ 未经审查（API 降级） | {unreviewed} |")
    if degraded:
        lines.append(f"| ⚠️ 修复降级（API 不可用） | {degraded} |")
    if offline_mode:
        lines.append(f"| 运行模式 | 🔒 离线 |")
    # 事实核验概览
    if refuted_count > 0:
        lines.append(f"| 🚨 事实核验驳回 | {refuted_count} |")
    if unverified_count > 0:
        lines.append(f"| ⚪ 未验证违规 | {unverified_count} |")

    lines += [
        f"| 通过率 | {_pct(passed, total)} |",
        "",
    ]

    if unresolved > 0:
        lines.append(
            f"⚠️ **有 {unresolved} 条违规无法自动修复，需要人工审查。**"
            f"请查看下方标记为 '🔶 需人工处理' 的条目。"
        )
        lines.append("")

    if pipeline_errors:
        lines.append("## ⚠️ 管道警告")
        lines.append("")
        for err in pipeline_errors:
            lines.append(f"- {err}")
        lines.append("")

    # ── 事实核验结果（在违规详情之前）──
    if refuted_count > 0 or unverified_count > 0:
        lines += [
            "## 🔍 事实核验结果",
            "",
            "合并前对每条 LLM 发现的违规执行了三项确定性核验：",
            "1. 文件是否存在于仓库中",
            "2. 行号是否指向有效代码行",
            "3. 声称的当前代码是否与源文件匹配",
            "",
            "| 核验结果 | 数量 | 说明 |",
            "|----------|------|------|",
            f"| ✅ 已核验 | {verified_count} | 代码位置和证据匹配，通过三项核验 |",
        ]
        if skipped_fact_check_count > 0:
            lines.append(
                f"| ⏭️ 跳过 | {skipped_fact_check_count} | "
                f"确定性检查或 Git 违规，不适用代码级事实核验 |"
            )
        if unverified_count > 0:
            lines.append(
                f"| ⚪ 未验证 | {unverified_count} | "
                f"缺少可核验的代码证据（如违规描述为'缺少 PRAGMA key'等规则级违规），"
                f"不排除为幻觉 |"
            )
        if refuted_count > 0:
            lines.append(
                f"| 🚨 已驳回 | {refuted_count} | "
                f"文件、行号或代码不匹配——声称的代码在源文件中不存在 |"
            )
        lines.append("")
        # ── 驳回详情：逐条列出文件、行号、规则和驳回原因 ──
        if refuted_count > 0:
            lines.append("### 驳回详情")
            lines.append("")
            lines.append("| 文件 | 行号 | 规则 | 驳回原因 |")
            lines.append("|------|------|------|----------|")
            for rv in refuted_violations:
                rv_file = os.path.basename(rv.get("file", "?"))
                rv_line = str(rv.get("line", "?"))
                rv_rule = rv.get("rule", "?")[:50]
                rv_reason = (rv.get("_fact_check_reason") or "?")[:100]
                lines.append(
                    f"| {rv_file} | {rv_line} | {rv_rule} | {rv_reason} |"
                )
            lines.append("")
        lines.append(
            "⚠️ **重要**：'已核验'仅表示违规声称的代码片段在源文件对应位置附近存在，"
            "不证明该规则确实被违反。审查 agent 仍需独立判断违规结论的正确性。"
        )
        lines.append("")

    lines += [
        "---",
        "",
    ]

    for idx, v in enumerate(violations):
        icon = _SEVERITY_ICONS.get(v.get("severity", ""), "⚪")
        lines.append(
            f"### {icon} [{v.get('rule', '?')}] "
            f"{v.get('file', '?')}:{v.get('line', '?')}"
        )
        lines.append("")
        lines.append(f"- **来源**: {v.get('source', '?')}")
        lines.append(f"- **严重度**: {v.get('severity', '?')}")
        lines.append(f"- **当前**: `{v.get('current', '?')}`")
        lines.append(f"- **应为**: `{v.get('expected', '?')}`")
        lines.append(f"- **原因**: {v.get('reason', '?')}")
        lines.append("")

        # 关联修复方案：fix_plans[idx] 与 violations[idx] 一一对应
        matched_plan = _find_plan(fix_plans, idx, v.get("file"), v.get("line"))
        if matched_plan:
            method = matched_plan.get("fix_method", "")
            fs = matched_plan.get("fix_status", "")
            changes = matched_plan.get("changes")

            # ── 渲染 fix_before/fix_after 或 PatchSet ──
            if changes:
                method_tag = " 📦 PatchSet"
                lines.append(f"  **修复**{method_tag}:")
                for ch in changes:
                    ch_file = os.path.basename(ch.get("file", "?"))
                    op = ch.get("operation", "?")
                    if op == "replace":
                        lines.append(f"  - `{ch_file}`: 替换")
                        lines.append(f"    ```diff\n    - {ch.get('before', '?')}\n    + {ch.get('after', '?')}\n    ```")
                    elif op in ("insert_after", "insert_before"):
                        lines.append(f"  - `{ch_file}`: {op} (锚点: `{ch.get('anchor', '?')[:60]}`)")
                        lines.append(f"    ```cpp\n    {ch.get('code', '?')}\n    ```")
                    elif op == "delete":
                        lines.append(f"  - `{ch_file}`: 删除 `{ch.get('before', '?')[:80]}`")
                risk = matched_plan.get("risk")
                if risk:
                    lines.append(f"  - ⚠️ 风险: {risk}")
            elif method == "format_fixer":
                method_tag = " 🤖 format_fixer"
                lines.append(f"  **修复**{method_tag}:")
                lines.append(
                    f"  ```diff\n"
                    f"  - {matched_plan.get('fix_before', '?')}\n"
                    f"  + {matched_plan.get('fix_after', '?')}\n"
                    f"  ```"
                )
            else:
                lines.append(f"  **修复**:")
                fb_code = matched_plan.get("fix_before", "")
                fa_code = matched_plan.get("fix_after", "")
                if fb_code or fa_code:
                    lines.append(
                        f"  ```diff\n"
                        f"  - {fb_code}\n"
                        f"  + {fa_code}\n"
                        f"  ```"
                    )

            # ── 状态渲染（基于 fix_status）──
            if method == "format_fixer":
                lines.append(f"  **状态**: ✅ 自动通过（确定性修复）")
            elif fs == "passed":
                lines.append(
                    f"  **审查**: ✅ 通过 "
                    f"(评分 {matched_plan.get('score', '?')}/10)"
                )
            elif fs == "unresolved":
                lines.append(
                    f"  **审查**: 🔶 需人工处理 "
                    f"(评分 {matched_plan.get('score', '?')}/10)"
                )
            elif fs == "infra":
                lines.append(f"  **审查**: ⚙️ 基础设施问题（非代码修复范围）")
            elif fs == "unreviewed":
                lines.append(
                    f"  **审查**: ⚠️ 未经审查（API 降级）"
                )
            elif fs == "degraded":
                lines.append(
                    f"  **审查**: ⚠️ 修复降级（API 不可用，未生成修复方案）"
                )
            elif fs == "failed":
                lines.append(
                    f"  **审查**: ❌ 未通过 "
                    f"(评分 {matched_plan.get('score', '?')}/10)"
                )
            else:
                # 兼容旧 status
                status_label = "✅ 通过" if matched_plan.get("status") else "❌ 未通过"
                lines.append(
                    f"  **审查**: {status_label} "
                    f"(评分 {matched_plan.get('score', '?')}/10)"
                )

            fb = matched_plan.get("feedback")
            if fb:
                lines.append(f"  > 评价: {fb}")
            sg = matched_plan.get("suggestion")
            if sg:
                lines.append(f"  > 建议: {sg}")
            rs = matched_plan.get("rule_snippet")
            if rs:
                lines.append(f"  > 规范: {rs}")

            # ── 可观测性：违规生命周期追踪链 ──
            chain = _build_lifecycle_chain(v, matched_plan, idx, iteration)
            if chain:
                lines.append(f"  **追踪链**: {chain}")

        lines.append("")

    lines.append("---")
    lines.append("*LangGraph Code Compliance Reviewer*")

    report = "\n".join(lines)
    output_path = os.path.join(os.getcwd(), OUTPUT_REPORT_FILENAME)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"  [报告导出] {output_path}")

    # ═══════════════════════════════════════════════════════════
    #  2. fix_guide.md（给 Claude 的修复指南 — 接口桩）
    # ═══════════════════════════════════════════════════════════
    _export_fix_guide_stub(state, fix_plans, format_fix_log, violations, iteration)

    return {"final_report": report, "run_incomplete": run_incomplete}


def _export_fix_guide_stub(
    state: AgentState,
    fix_plans: list[dict],
    format_fix_log: list[dict],
    violations: list[dict],
    iteration: int,
) -> None:
    """fix_guide.md 接口桩 — 后续完善为完整 Claude 修复指南。"""
    fmt_count = len(format_fix_log)
    llm_count = sum(1 for p in fix_plans if p is not None and p.get("fix_method") != "format_fixer")
    lines = [
        "# 🤖 代码修复指南 — 给 Claude 的执行指令",
        "",
        f"> 仓库: {state['repo_path']}",
        f"> 迭代: {iteration}次",
        f"> 自动修复: {fmt_count} | AI 修复: {llm_count}",
        "",
        "---",
        "",
        "## TODO: 完善修复指南",
        "",
        "此文件是修复指南的接口桩。后续完善应包含：",
        "- 每条违规的精确 diff（可直接 apply）",
        "- 按文件分组（方便批量操作）",
        "- 修复优先级排序",
        "- 审查历史与建议摘要",
        "",
        "当前请参考 `compliance_report.md` 获取完整信息。",
        "",
        "---",
        "*Generated by LangGraph Code Compliance Reviewer*",
    ]
    guide_path = os.path.join(os.getcwd(), "fix_guide.md")
    with open(guide_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  [报告导出] {guide_path} (桩)")


def _find_plan(plans: list[dict], idx: int, file_path: str = "", line: int = 0) -> dict | None:
    """查找与违规匹配的修复方案。

    fix_plans[i] 与 violations[i] 一一对应，直接用索引获取。
    仅当直接索引不可用时才回退到 (file, line) 模糊匹配。
    """
    # ── 主路径：索引直接对应 ──
    if 0 <= idx < len(plans):
        p = plans[idx]
        if p is not None:
            return p

    # ── 回退：精确 (file, line) 匹配 ──
    if file_path:
        for p in plans:
            if p is None:
                continue
            if p.get("file") == file_path and p.get("line") == line:
                return p
            # PatchSet: 检查 changes 中是否包含该文件
            changes = p.get("changes")
            if changes:
                for ch in changes:
                    if ch.get("file") == file_path:
                        return p
    return None


def _build_lifecycle_chain(
    violation: dict, plan: dict, idx: int, iteration: int,
) -> str:
    """构建一条违规的完整生命周期追踪链。

    从违规发现来源、修复方案状态、审查评分等信息，
    生成一行可读的追踪链："发现 → 分析 → 修复 → 审查结果"。
    """
    parts: list[str] = []

    # 发现来源
    source_kind = violation.get("source_kind", "")
    source = violation.get("source", "unknown")
    if source_kind == "deterministic":
        parts.append(f"发现(deterministic_checker)")
    else:
        parts.append(f"发现({source}_agent)")

    # 修复状态
    method = plan.get("fix_method", "")
    fs = plan.get("fix_status", "")
    score = plan.get("score", 0)

    if method == "format_fixer":
        parts.append("自动修复(format_fixer)")
        parts.append("✅ 自动通过")
    elif fs == "passed":
        parts.append(f"修复(fix_agent, iter={iteration})")
        parts.append(f"✅ 通过(score={score}/10)")
    elif fs == "failed":
        parts.append(f"修复(fix_agent, iter={iteration})")
        parts.append(f"❌ 未通过(score={score}/10, iter={iteration}/3)")
    elif fs == "unresolved":
        parts.append(f"修复(fix_agent, iter={iteration})")
        parts.append(f"🔶 需人工处理")
    elif fs == "unreviewed":
        parts.append(f"修复(fix_agent, iter={iteration})")
        parts.append("⚠️ 未经审查(API 降级)")
    elif fs == "degraded":
        parts.append("⚠️ 修复降级(API 不可用)")
    elif fs == "infra":
        parts.append("跳过(基础设施问题)")
    elif fs == "proposed":
        parts.append(f"修复已提交(fix_agent)")
        parts.append("⏳ 待审查")

    # 审查反馈摘要
    feedback = plan.get("feedback", "")
    if feedback and fs in ("failed", "unresolved"):
        short_fb = feedback[:80] + ("..." if len(feedback) > 80 else "")
        parts.append(f'→ "{short_fb}"')

    return " → ".join(parts) if parts else ""


def _pct(n: int, total: int) -> str:
    if total == 0:
        return "0%"
    return f"{n / total * 100:.0f}%"
