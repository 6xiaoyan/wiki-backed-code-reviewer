"""报告与评论渲染：状态区分、省略说明、无虚假“通过”结论。"""

from code_checker.pr_review.models import Finding, ReviewRequest, ReviewResult, make_review_key
from code_checker.pr_review.report import (
    COMMENT_MAX_FINDINGS,
    SUMMARY_MARKER,
    render_comment,
    render_report,
    sanitize_inline,
)


def _result(status="completed", reason="所有必要阶段完成", findings=None, **summary):
    req = ReviewRequest(
        repo="owner/repo", pr_number=3, base_sha="a" * 40, head_sha="b" * 40,
        merge_base_sha="c" * 40, program_sha="d" * 40, run_id="1",
        run_url="https://github.example/run/1", model_id="deepseek-v4-flash",
    )
    base_summary = {"files_changed": 2, "files_reviewed": 2, "files_excluded": 1,
                    "changed_lines": 12, "commits": 1, "by_severity": {}}
    base_summary.update(summary)
    return ReviewResult(
        schema_version=1, status=status, status_reason=reason,
        review_key=make_review_key(req), generated_at="2026-10-19T00:00:00Z",
        request=req, summary=base_summary, findings=findings or [],
    )


def _finding(i=1, severity="warning", file="src/a.cpp"):
    return Finding(
        id=f"F{i}", severity=severity, file=file, line=i,
        rule_id="cpp/naming-functions", rule_title="函数命名",
        message="函数名应为 camelCase", code_evidence="+ int Bad() {",
        change_relation="added", source="deterministic",
        suggestion="改为 badName（建议，未执行验证）",
    )


def test_completed_with_zero_findings_does_not_claim_repo_is_safe():
    comment = render_comment(_result())
    assert "未发现与本次改动相关的已确认问题" in comment
    assert "整个仓库安全" in comment  # 明确说明不等于全仓安全
    assert "所有代码安全" not in comment
    assert "审查通过" not in comment
    assert "b" * 40 in comment


def test_incomplete_shows_reason_and_not_success():
    comment = render_comment(_result(status="incomplete", reason="预算耗尽"))
    assert "审查未完成" in comment
    assert "预算耗尽" in comment
    assert "审查完成" not in comment


def test_skipped_explains_reason():
    comment = render_comment(_result(status="skipped", reason="草稿 PR：跳过"))
    assert "已跳过" in comment
    assert "草稿 PR" in comment


def test_severity_ordering_and_truncation():
    findings = [_finding(i, "warning") for i in range(1, 6)]
    findings.append(_finding(99, "critical"))
    comment = render_comment(_result(findings=findings))
    assert comment.index("[critical]") < comment.index("[warning]")
    assert "已确认问题（6）" in comment
    assert COMMENT_MAX_FINDINGS == 20


def test_comment_limits_number_of_findings():
    findings = [_finding(i) for i in range(1, 30)]
    comment = render_comment(_result(findings=findings))
    assert "其余 9 条见完整报告" in comment


def test_unconfirmed_candidates_are_separate():
    result = _result()
    result.uncertain_findings = [{"file": "src/a.cpp", "line": 2,
                                  "reason": "无法证明由本次改动引入"}]
    comment = render_comment(result)
    assert "不确定候选（1）" in comment
    assert "未计入已确认问题" in comment


def test_report_contains_scope_versions_and_limits():
    result = _result(findings=[_finding()])
    result.not_covered = [{"path": "src/b.cpp", "reason": "超出预算"}]
    result.filtered_findings = [{"file": "src/c.cpp", "line": 9,
                                 "rule_id": "cpp/naming-functions",
                                 "reason": "历史问题"}]
    result.excluded_files = [{"path": "assets/x.png", "reason": "二进制文件"}]
    report = render_report(result)
    assert "版本记录" in report
    assert "c" * 40 in report
    assert "已过滤候选" in report
    assert "排除文件" in report
    assert "未覆盖范围" in report
    assert "已知限制" in report


def test_sanitize_inline_neutralizes_mentions_and_comments():
    out = sanitize_inline("@octocat <!-- marker --> `code`")
    assert "\\@octocat" in out
    assert "&lt;!--" in out
    assert "`" not in out


def test_marker_present_exactly_once():
    comment = render_comment(_result(findings=[_finding()]))
    assert comment.count(SUMMARY_MARKER) == 1
