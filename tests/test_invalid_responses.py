"""无效模型响应不得被当成“没有发现问题”（问题 2）。"""

import pytest

from code_checker.pr_review.agents import _parse_response
from code_checker.pr_review.config import PRConfig
from code_checker.pr_review.pipeline import run_analysis
from code_checker.pr_review.report import render_comment
from code_checker.pr_review.snapshot import LocalGitSnapshot

BASE = """#include <iostream>

int main() {
    return 0;
}
"""

HEAD = """#include <iostream>

int helper() {
    return 1;
}

int main() {
    return 0;
}
"""

NAME_QUOTE = "函数和方法必须使用camelCase（首字母小写，后续每个单词的首字母大写）"
FINDING = (
    '[{"file": "src/main.cpp", "line": 3, "rule_id": "cpp/naming-functions", '
    '"severity": "warning", "message": "函数命名", "code": "int helper() {", '
    f'"rule_quote": "{NAME_QUOTE}", "suggestion": "改名"}}]'
)


def _run(repo, request, llm):
    return run_analysis(
        LocalGitSnapshot(repo.path), request,
        config=PRConfig(), llm=llm, offline=False,
    )


@pytest.mark.parametrize("text", [
    "[]",
    '[{"file": "src/a.cpp"}]',
    '{"findings": [{"file": "src/a.cpp"}]}',
    '```json\n[]\n```',
])
def test_valid_responses(text):
    findings, error = _parse_response(text)
    assert error == ""
    assert isinstance(findings, list)


@pytest.mark.parametrize("text", [
    "",
    "   \n\t ",
    "not json",
    '{"foo": 1}',
    "[1, 2]",
    "null",
    "{}",
    '[{"file": "src/a.cpp"}, 3]',
    "```json\n\n```",
])
def test_invalid_responses_are_rejected(text):
    findings, error = _parse_response(text)
    assert findings is None
    assert error


def test_empty_response_retries_then_marks_incomplete(make_repo, request_for, fake_llm):
    repo = make_repo({"src/main.cpp": BASE}, {"src/main.cpp": HEAD})
    llm = fake_llm([""])
    result = _run(repo, request_for(repo), llm)

    assert llm.calls == 3  # 首次 + 2 次重试
    assert result.status == "incomplete"
    assert "模型响应无效" in result.status_reason
    assert "空响应" in result.status_reason
    assert result.findings == []
    assert result.budget_usage["model_requests"] == 3
    assert result.budget_usage["model_retries"] == 2
    assert "审查未完成" in render_comment(result)


def test_malformed_json_marks_incomplete(make_repo, request_for, fake_llm):
    repo = make_repo({"src/main.cpp": BASE}, {"src/main.cpp": HEAD})
    llm = fake_llm(['{"findings": [oops'])
    result = _run(repo, request_for(repo), llm)

    assert llm.calls == 3
    assert result.status == "incomplete"
    assert "JSON 解析失败" in result.status_reason
    assert result.findings == []


def test_wrong_json_type_marks_incomplete(make_repo, request_for, fake_llm):
    repo = make_repo({"src/main.cpp": BASE}, {"src/main.cpp": HEAD})
    llm = fake_llm(["[1, 2, 3]"])
    result = _run(repo, request_for(repo), llm)

    assert llm.calls == 3
    assert result.status == "incomplete"
    assert "非对象元素" in result.status_reason


def test_legitimate_empty_array_is_completed(make_repo, request_for, fake_llm):
    repo = make_repo({"src/main.cpp": BASE}, {"src/main.cpp": HEAD})
    llm = fake_llm(["[]"])
    result = _run(repo, request_for(repo), llm)

    assert llm.calls == 1
    assert result.status == "completed"
    assert result.findings == []
    assert result.status_reason == "所有必要阶段完成"
    assert "未发现与本次改动相关的已确认问题" in render_comment(result)


def test_valid_findings_array_is_accepted(make_repo, request_for, fake_llm):
    repo = make_repo({"src/main.cpp": BASE}, {"src/main.cpp": HEAD})
    llm = fake_llm([FINDING])
    result = _run(repo, request_for(repo), llm)

    assert llm.calls == 1
    assert result.status == "completed"
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.rule_id == "cpp/naming-functions"
    assert finding.rule_quote == NAME_QUOTE
    assert "camelCase" in finding.rule_basis


def test_invalid_then_valid_retry_succeeds(make_repo, request_for, fake_llm):
    repo = make_repo({"src/main.cpp": BASE}, {"src/main.cpp": HEAD})
    llm = fake_llm(["not json", "[]"])
    result = _run(repo, request_for(repo), llm)

    assert llm.calls == 2
    assert result.status == "completed"
    assert result.budget_usage["model_retries"] == 1


def test_retry_exhaustion_never_becomes_zero_problem_completed(
    make_repo, request_for, fake_llm,
):
    repo = make_repo({"src/main.cpp": BASE}, {"src/main.cpp": HEAD})
    llm = fake_llm(['{"findings": "none"}'])
    result = _run(repo, request_for(repo), llm)

    assert result.status == "incomplete"
    assert result.status != "completed"
    assert "审查未完成" in render_comment(result)
    assert result.summary.get("confirmed_findings") == 0
