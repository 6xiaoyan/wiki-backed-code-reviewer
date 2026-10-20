"""结果渲染：完整 Markdown 报告 + PR 汇总评论。

安全要求（PRD §9）：
  * 评论带隐藏标记，便于只更新机器人自己的那条；
  * 模型/仓库文本中的 @提醒、HTML 注释、反引号会被中和，不能产生副作用；
  * 评论长度受控，优先展示严重问题，省略数量明确写出；
  * 始终写明被审查的 head SHA，不写“最新代码已通过”。
"""

from __future__ import annotations

import re

from code_checker.pr_review.models import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_INCOMPLETE,
    STATUS_SKIPPED,
    STATUS_SUPERSEDED,
    Finding,
    ReviewResult,
)

SUMMARY_MARKER = "<!-- wiki-backed-code-reviewer:summary:v1 -->"
COMMENT_MAX_CHARS = 60000
COMMENT_MAX_FINDINGS = 20

_MENTION_RE = re.compile(r"(?<![\w`])@([A-Za-z0-9][A-Za-z0-9_-]{0,38})")

_STATUS_LABELS = {
    STATUS_COMPLETED: "审查完成",
    STATUS_SKIPPED: "已跳过",
    STATUS_INCOMPLETE: "审查未完成",
    STATUS_FAILED: "审查失败",
    STATUS_SUPERSEDED: "结果已过时",
}

_SEVERITY_LABELS = {
    "critical": "critical",
    "warning": "warning",
    "suggestion": "suggestion",
    "info": "info",
}


def sanitize_inline(text: str, limit: int = 420) -> str:
    """中和可能产生副作用的 Markdown/HTML 结构。"""
    text = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("<!--", "&lt;!--").replace("-->", "--&gt;")
    # 用反斜杠转义 @提醒；GitHub 不会把它渲染成 mention
    text = _MENTION_RE.sub(lambda m: f"\\@{m.group(1)}", text)
    # 去掉反引号，避免破坏外层行内代码/代码块结构
    text = text.replace("`", "'")
    text = " ".join(text.split())
    if len(text) > limit:
        text = text[:limit] + "…"
    return text


def _status_line(result: ReviewResult) -> str:
    label = _STATUS_LABELS.get(result.status, result.status)
    return f"**状态**：{label}（`{result.status}`）"


def _request_shas(result: ReviewResult) -> str:
    req = result.request
    return (
        f"- 代码版本（head）：`{req.head_sha}`\n"
        f"- 目标分支版本（base）：`{req.base_sha}`\n"
        f"- 共同祖先（merge-base）：`{req.merge_base_sha}`"
    )


def _run_links(result: ReviewResult) -> str:
    req = result.request
    lines = []
    if req.run_url:
        lines.append(f"- 运行记录：{req.run_url}")
    artifacts = result.artifacts or {}
    if artifacts.get("artifact_url"):
        lines.append(f"- 完整报告与 JSON：{artifacts['artifact_url']}")
    elif artifacts.get("artifact_name"):
        lines.append(
            f"- 完整报告与 JSON：Actions 运行页 → Artifacts → "
            f"`{artifacts['artifact_name']}`"
        )
    if artifacts.get("report_path") and not artifacts.get("artifact_url"):
        lines.append(f"- 本地完整报告：`{artifacts['report_path']}`")
    return "\n".join(lines)


def _finding_block(f: Finding, index: int, *, detailed: bool) -> str:
    sev = _SEVERITY_LABELS.get(f.severity, f.severity)
    loc = f"{sanitize_inline(f.file, limit=200)}:{f.line}" if f.line else sanitize_inline(f.file, limit=200)
    lines = [f"#### {index}. [{sev}] `{loc}`", ""]
    lines.append(f"- **问题**：{sanitize_inline(f.message, limit=700)}")
    if f.code_evidence:
        lines.append(f"- **本次改动证据**：`{sanitize_inline(f.code_evidence, limit=300)}`")
    rule = f"`{sanitize_inline(f.rule_id, limit=120)}`"
    if f.rule_title and f.rule_title != f.rule_id:
        rule += f" — {sanitize_inline(f.rule_title, limit=160)}"
    lines.append(f"- **依据**：{rule}")
    basis = f.rule_quote or f.rule_basis
    if basis:
        source = ""
        if f.rule_source:
            source = f"（可信 Wiki 原文，来源：{sanitize_inline(f.rule_source, limit=200)}）"
        else:
            source = "（可信 Wiki 原文）"
        lines.append(f"- **规则正文**：{sanitize_inline(basis, limit=600)}{source}")
    elif f.rule_page:
        lines.append("- **规则正文**：未能从可信 Wiki 提取对应条款（见运行记录）")
    else:
        lines.append("- **规则正文**：该检查由确定性代码执行，未映射到 Wiki 页面")
    if f.suggestion:
        lines.append(f"- **建议**：{sanitize_inline(f.suggestion, limit=500)}")
    if detailed and f.source:
        lines.append(f"- **来源**：`{sanitize_inline(f.source, limit=80)}`")
    lines.append("")
    return "\n".join(lines)


def _coverage_block(result: ReviewResult, *, compact: bool) -> str:
    summary = result.summary
    reviewed = summary.get("files_reviewed", 0)
    changed = summary.get("files_changed", 0)
    excluded = summary.get("files_excluded", 0)
    lines_budget = summary.get("changed_lines", 0)
    parts = [f"已审查 {reviewed}/{changed} 个变更文件，{lines_budget} 行改动"]
    if excluded:
        parts.append(f"排除 {excluded} 个文件")
    rules_injected = int(summary.get("rules_injected") or 0)
    rules_not_injected = int(summary.get("rules_not_injected") or 0)
    if rules_injected or rules_not_injected:
        text_rules = f"规则正文注入 {rules_injected} 条"
        if rules_not_injected:
            text_rules += f"，{rules_not_injected} 条未注入"
        parts.append(text_rules)
    text = "；".join(parts)
    if result.not_covered:
        text += f"；{len(result.not_covered)} 个文件因预算未覆盖"
    if compact:
        return text
    lines = [text, ""]
    if result.excluded_files:
        lines.append("**排除文件**（不发送给模型）：")
        for item in result.excluded_files[:30]:
            lines.append(f"- `{sanitize_inline(item.get('path', ''), 200)}` — "
                         f"{sanitize_inline(item.get('reason', ''), 200)}")
        if len(result.excluded_files) > 30:
            lines.append(f"- …其余 {len(result.excluded_files) - 30} 个见完整报告")
        lines.append("")
    if result.not_covered:
        lines.append("**未覆盖范围**（预算或读取失败）：")
        for item in result.not_covered[:30]:
            lines.append(f"- `{sanitize_inline(item.get('path', ''), 200)}` — "
                         f"{sanitize_inline(item.get('reason', ''), 200)}")
        lines.append("")
    return "\n".join(lines)


def _issues_block(result: ReviewResult, *, compact: bool,
                  findings: list[Finding] | None = None) -> str:
    findings = findings if findings is not None else result.findings
    if not findings:
        if result.status == STATUS_COMPLETED:
            return (
                "**未发现与本次改动相关的已确认问题。**\n\n"
                "> 这不等于“整个仓库安全”：审查范围仅限本次 diff 涉及的改动，"
                "未覆盖部分见下方说明。\n"
            )
        return ""
    limit = COMMENT_MAX_FINDINGS if compact else len(findings)
    shown = findings[:limit]
    lines = [f"### 已确认问题（{len(findings)}）", ""]
    for i, f in enumerate(shown, 1):
        lines.append(_finding_block(f, i, detailed=not compact))
    if len(findings) > len(shown):
        lines.append(
            f"> 评论仅显示前 {len(shown)} 条（按严重度排序），"
            f"其余 {len(findings) - len(shown)} 条见完整报告。\n"
        )
    return "\n".join(lines)


def _uncertain_block(result: ReviewResult, *, compact: bool) -> str:
    if not result.uncertain_findings:
        return ""
    n = len(result.uncertain_findings)
    if compact:
        return (
            f"### 不确定候选（{n}）\n\n"
            "> 证据不足，未计入已确认问题，不作为合并阻断依据。"
            "详见完整报告 `uncertain_findings`。\n"
        )
    lines = [f"### 不确定候选（{n}）", ""]
    for item in result.uncertain_findings[:40]:
        lines.append(
            f"- `{sanitize_inline(item.get('file', '?'), 200)}:"
            f"{item.get('line', '?')}` — {sanitize_inline(item.get('reason', ''), 240)}"
        )
    if n > 40:
        lines.append(f"- …其余 {n - 40} 条见完整报告")
    lines.append("")
    return "\n".join(lines)


def _runtime_block(result: ReviewResult, *, compact: bool) -> str:
    lines: list[str] = []
    problems = [
        e for e in result.degradation
        if e.get("status") in ("failed", "degraded", "skipped")
    ]
    if problems:
        lines.append("### 运行异常与降级")
        lines.append("")
        for e in problems[:20]:
            lines.append(
                f"- `{sanitize_inline(e.get('stage', '?'), 80)}` "
                f"{e.get('status')}：{sanitize_inline(e.get('reason', ''), 300)}"
            )
        lines.append("")
    usage = result.budget_usage or {}
    if usage:
        token_text = "未知（接口未返回）" if usage.get("tokens_unknown") else (
            f"{usage.get('prompt_tokens', 0)} / {usage.get('completion_tokens', 0)}"
        )
        lines.append(
            f"**运行用量**：模型请求 {usage.get('model_requests', 0)}/"
            f"{usage.get('model_requests_limit', '?')} 次；"
            f"重试 {usage.get('model_retries', 0)} 次；"
            f"上下文 {usage.get('context_bytes', 0)} 字节；"
            f"耗时 {usage.get('elapsed_seconds', 0)} 秒；"
            f"token（输入/输出）{token_text}"
        )
        lines.append("")
    if result.errors:
        lines.append("### 错误")
        lines.append("")
        for err in result.errors[:10]:
            lines.append(f"- {sanitize_inline(err, 400)}")
        lines.append("")
    return "\n".join(lines)


def render_comment(result: ReviewResult) -> str:
    """渲染 PR 汇总评论（单条，可更新）。"""
    req = result.request
    head7 = req.head_sha[:7]
    label = _STATUS_LABELS.get(result.status, result.status)
    summary = result.summary or {}
    counts = summary.get("by_severity") or {}
    ordered = sorted(
        result.findings,
        key=lambda f: (
            {"critical": 0, "warning": 1, "suggestion": 2, "info": 3}.get(f.severity, 9),
            f.file, f.line,
        ),
    )
    count_text = "，".join(
        f"{k} {counts[k]}" for k in ("critical", "warning", "suggestion") if counts.get(k)
    ) or "0"

    lines = [
        SUMMARY_MARKER,
        f"## PR 审查：{label}",
        "",
        _status_line(result),
        f"- 代码版本（head）：`{head7}`（完整：`{req.head_sha}`）",
        f"- 审查范围：`{req.merge_base_sha[:7]}` → `{req.head_sha[:7]}`"
        f"（{summary.get('commits', 0)} 个提交）",
        f"- 生成时间：{result.generated_at}",
        "",
        f"**结论**：已确认问题 {len(result.findings)} 条（{count_text}）；"
        f"不确定候选 {len(result.uncertain_findings)} 条。",
        "",
        _coverage_block(result, compact=True),
        "",
    ]
    if result.status != STATUS_COMPLETED and result.status_reason:
        lines += [f"> **{label}**：{sanitize_inline(result.status_reason, 600)}", ""]

    issues = _issues_block(result, compact=True, findings=ordered)
    if issues:
        lines += [issues, ""]
    uncertain = _uncertain_block(result, compact=True)
    if uncertain:
        lines += [uncertain, ""]
    runtime = _runtime_block(result, compact=True)
    if runtime:
        lines += [runtime, ""]

    lines += [
        "---",
        "### 版本与追溯",
        "",
        _request_shas(result),
        f"- 规则/skill 摘要：`{req.rules_digest or '未记录'}`；"
        f"提示词摘要：`{req.prompts_digest or '未记录'}`；"
        f"配置摘要：`{req.config_digest or '未记录'}`",
        f"- 审查程序版本：`{req.program_sha or '未记录'}`；"
        f"模型：`{req.model_provider}/{req.model_id or '未记录'}`",
        f"- review_key：`{result.review_key}`",
        "",
        _run_links(result),
        "",
        "> 修复建议均为建议，系统未执行、未验证；本评论不代表代码已修复或构建测试已通过。",
        "",
        "*由 wiki-backed-code-reviewer 自动生成*",
    ]
    text = "\n".join(line for line in lines if line is not None)

    if len(text) > COMMENT_MAX_CHARS:
        cut = text[:COMMENT_MAX_CHARS - 300]
        text = (
            cut
            + "\n\n---\n> 评论超长已截断，完整内容见 Actions artifact 中的完整报告。\n"
        )
    return text


def render_report(result: ReviewResult) -> str:
    """渲染完整 Markdown 报告（写入 artifact）。"""
    req = result.request
    summary = result.summary or {}
    counts = summary.get("by_severity") or {}
    lines = [
        "# PR 审查完整报告",
        "",
        f"- 状态：`{result.status}` — {result.status_reason or '无' }",
        f"- 仓库：`{req.repo}`，PR #{req.pr_number}",
        f"- 触发方式：{req.trigger or '未知'}；运行：{req.run_url or '未知'}",
        f"- 生成时间：{result.generated_at}",
        f"- review_key：`{result.review_key}`",
        "",
        "## 版本记录",
        "",
        "| 项目 | 值 |",
        "|---|---|",
        f"| 被审查代码 head | `{req.head_sha}` |",
        f"| 目标分支 base | `{req.base_sha}` |",
        f"| 共同祖先 merge-base | `{req.merge_base_sha}` |",
        f"| 审查程序提交 | `{req.program_sha or '未记录'}` |",
        f"| 规则/skill 摘要 | `{req.rules_digest or '未记录'}` |",
        f"| 提示词摘要 | `{req.prompts_digest or '未记录'}` |",
        f"| 配置摘要 | `{req.config_digest or '未记录'}` |",
        f"| 模型 | `{req.model_provider}/{req.model_id or '未记录'}` |",
        f"| Actions run | `{req.run_id}` attempt {req.run_attempt} |",
        "",
        "## 审查范围",
        "",
        _coverage_block(result, compact=False),
        "",
        f"- 已审查文件：{summary.get('files_reviewed', 0)}",
        f"- 变更行数：{summary.get('changed_lines', 0)}",
        f"- PR 提交数：{summary.get('commits', 0)}",
        f"- 已确认问题：{len(result.findings)}"
        f"（critical {counts.get('critical', 0)} / warning {counts.get('warning', 0)}"
        f" / suggestion {counts.get('suggestion', 0)} / info {counts.get('info', 0)}）",
        f"- 不确定候选：{len(result.uncertain_findings)}",
        f"- 过滤的历史/无关候选：{len(result.filtered_findings)}",
        "",
        "### 已审查文件明细",
        "",
    ]
    for item in result.reviewed_files:
        lines.append(
            f"- `{item.get('path')}`（{item.get('status')}，域 {item.get('domain')}，"
            f"+{item.get('additions', 0)}/-{item.get('deletions', 0)}）"
        )
    lines.append("")

    rule_coverage = result.artifacts.get("rule_coverage") or []
    if rule_coverage:
        lines += ["## 规则正文注入范围", ""]
        lines += [
            "| 领域 | 已注入 | 未注入 | 已用字节 | 上限字节 |",
            "|---|---|---|---|---|",
        ]
        for item in rule_coverage:
            lines.append(
                f"| {sanitize_inline(item.get('domain', '?'), 40)} "
                f"| {item.get('rules_injected', 0)} "
                f"| {item.get('rules_not_injected', 0)} "
                f"| {item.get('used_bytes', 0)} "
                f"| {item.get('limit_bytes', 0)} |"
            )
        lines.append("")
        excluded_rules = [
            (item.get("domain", "?"), rule)
            for item in rule_coverage
            for rule in (item.get("excluded") or [])
        ]
        if excluded_rules:
            lines += [
                "**未注入的规则正文**（审查依据不完整，结果因此标为未完成）：",
                "",
            ]
            for domain, rule in excluded_rules[:100]:
                lines.append(
                    f"- `{sanitize_inline(rule.get('rule_id', '?'), 120)}`"
                    f"（{sanitize_inline(str(domain), 40)}）— "
                    f"{sanitize_inline(rule.get('reason', ''), 240)}"
                )
            if len(excluded_rules) > 100:
                lines.append(f"- …其余 {len(excluded_rules) - 100} 条")
            lines.append("")

    lines += ["## 已确认问题", ""]
    if not result.findings:
        lines.append(
            "未发现与本次改动相关的已确认问题。该结论仅覆盖上面列出的审查范围，"
            "不代表整个仓库安全。"
        )
        lines.append("")
    for i, f in enumerate(sorted(
            result.findings,
            key=lambda x: ({"critical": 0, "warning": 1, "suggestion": 2,
                            "info": 3}.get(x.severity, 9), x.file, x.line),
            ), 1):
        lines.append(_finding_block(f, i, detailed=True))

    if result.uncertain_findings:
        lines += ["## 不确定候选", "", _uncertain_block(result, compact=False)]

    if result.filtered_findings:
        lines += ["## 已过滤候选（历史问题或证据不足）", ""]
        for item in result.filtered_findings[:100]:
            lines.append(
                f"- `{item.get('file', '?')}:{item.get('line', '?')}` "
                f"{item.get('rule', item.get('rule_id', '?'))} — "
                f"{item.get('reason', '')}"
            )
        if len(result.filtered_findings) > 100:
            lines.append(f"- …其余 {len(result.filtered_findings) - 100} 条")
        lines.append("")

    context_reads = result.artifacts.get("context_reads") or []
    if context_reads:
        lines += ["## 额外上下文读取记录", ""]
        for r in context_reads:
            lines.append(
                f"- `{r.get('path')}` @ `{str(r.get('sha'))[:8]}` "
                f"行 {r.get('start')}-{r.get('end')}：{r.get('purpose')} "
                f"（{r.get('bytes')} 字节）"
            )
        lines.append("")

    header_missing = result.artifacts.get("header_context_missing") or []
    if header_missing:
        lines += ["## 未读取的关联头文件", ""]
        for item in header_missing[:50]:
            kind = "项目头文件（必要上下文）" if item.get("quoted") else "外部/角括号头文件"
            lines.append(
                f"- `{sanitize_inline(item.get('path', '?'), 200)}` "
                f"（{kind}，引用自 `{sanitize_inline(item.get('file', '?'), 200)}`）"
            )
        lines.append("")

    runtime = _runtime_block(result, compact=False)
    if runtime:
        lines += ["## 运行状态与用量", "", runtime]

    lines += [
        "## 已知限制",
        "",
        "- 本阶段只审查 PR diff 覆盖的改动，不做完整跨文件数据流分析。",
        "- 文档/二进制/生成/第三方文件被排除，不发送给模型。",
        "- 修复建议未执行验证；系统不会自动修改、提交或合并代码。",
        "- 模型输出经过证据核验，但语义判断仍可能不完整。",
        "",
        "---",
        "*wiki-backed-code-reviewer · 第一阶段*",
    ]
    return "\n".join(lines)


def comment_preview(result: ReviewResult, limit: int = 500) -> str:
    """测试/日志用：截断后的评论预览。"""
    return render_comment(result)[:limit]
