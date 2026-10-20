"""状态机与失败/降级语义测试（PRD §9.1、§13）。"""

import pytest

from code_checker.pr_review.config import PRConfig
from code_checker.pr_review.models import STATUS_EXIT_CODES, BudgetConfig
from code_checker.pr_review.pipeline import run_analysis
from code_checker.pr_review.snapshot import LocalGitSnapshot


CLEAN_BASE = """#include <iostream>

int main() {
    return 0;
}
"""

CLEAN_HEAD = """#include <iostream>

int helper() {
    return 1;
}

int main() {
    return 0;
}
"""


@pytest.fixture
def clean_repo(make_repo):
    return make_repo({"src/main.cpp": CLEAN_BASE}, {"src/main.cpp": CLEAN_HEAD},
                     head_msg="feat: add helper")


def test_draft_pr_skips_without_calling_model(clean_repo, request_for, fake_llm):
    class ExplodingLLM:
        calls = 0

        def invoke(self, prompt):
            self.calls += 1
            raise AssertionError("草稿 PR 不应调用模型")

    llm = ExplodingLLM()
    result = run_analysis(
        LocalGitSnapshot(clean_repo.path),
        request_for(clean_repo, draft=True),
        config=PRConfig(), llm=llm, offline=False,
    )
    assert result.status == "skipped"
    assert "草稿" in result.status_reason
    assert llm.calls == 0
    assert STATUS_EXIT_CODES[result.status] == 0


def test_closed_pr_skips(clean_repo, request_for):
    result = run_analysis(
        LocalGitSnapshot(clean_repo.path),
        request_for(clean_repo, pr_state="closed"),
        config=PRConfig(offline=True), offline=True,
    )
    assert result.status == "skipped"
    assert "closed" in result.status_reason


def test_offline_never_reports_completed(clean_repo, request_for):
    result = run_analysis(
        LocalGitSnapshot(clean_repo.path), request_for(clean_repo),
        config=PRConfig(offline=True), offline=True,
    )
    assert result.status == "incomplete"
    assert "离线模式" in result.status_reason
    assert STATUS_EXIT_CODES[result.status] == 2


def test_completed_with_zero_findings(clean_repo, request_for, fake_llm):
    llm = fake_llm(["[]"])
    result = run_analysis(
        LocalGitSnapshot(clean_repo.path), request_for(clean_repo),
        config=PRConfig(), llm=llm, offline=False,
    )
    assert result.status == "completed"
    assert result.findings == []
    assert result.status_reason == "所有必要阶段完成"
    assert llm.calls >= 1


def test_completed_with_findings_still_succeeds(clean_repo, request_for, fake_llm):
    llm = fake_llm(['[{"file": "src/main.cpp", "line": 3, "rule_id": '
                    '"cpp/naming-functions", "severity": "warning", '
                    '"message": "函数命名", "code": "int helper() {", '
                    '"rule_quote": "函数和方法必须使用camelCase（首字母小写，'
                    '后续每个单词的首字母大写）", '
                    '"suggestion": "改名"}]'])
    result = run_analysis(
        LocalGitSnapshot(clean_repo.path), request_for(clean_repo),
        config=PRConfig(), llm=llm, offline=False,
    )
    assert result.status == "completed"
    assert len(result.findings) == 1
    assert result.findings[0].change_relation == "added"
    assert STATUS_EXIT_CODES[result.status] == 0


def test_missing_credentials_fails(clean_repo, request_for, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = run_analysis(
        LocalGitSnapshot(clean_repo.path), request_for(clean_repo),
        config=PRConfig(offline=False), llm=None, offline=False,
    )
    assert result.status == "failed"
    assert "缺少模型凭据" in result.status_reason
    assert STATUS_EXIT_CODES[result.status] == 1


def test_model_failure_marks_incomplete(clean_repo, request_for):
    class FailingLLM:
        def invoke(self, prompt):
            raise RuntimeError("503 service unavailable")

    result = run_analysis(
        LocalGitSnapshot(clean_repo.path), request_for(clean_repo),
        config=PRConfig(), llm=FailingLLM(), offline=False,
    )
    assert result.status == "incomplete"
    assert "Agent 未完成" in result.status_reason
    assert any(e["status"] == "failed" for e in result.degradation)
    assert STATUS_EXIT_CODES[result.status] == 2


def test_model_budget_exhaustion_marks_incomplete(clean_repo, request_for, fake_llm):
    result = run_analysis(
        LocalGitSnapshot(clean_repo.path), request_for(clean_repo),
        config=PRConfig(budget=BudgetConfig(max_model_requests=0)),
        llm=fake_llm(["[]"]), offline=False,
    )
    assert result.status == "incomplete"
    assert "预算" in result.status_reason


def test_no_applicable_change_skips(make_repo, request_for, fake_llm):
    repo = make_repo(
        {"README.md": "# demo\n", "src/main.cpp": CLEAN_BASE},
        {"README.md": "# demo updated\n"},
        head_msg="docs: update readme",
    )
    result = run_analysis(
        LocalGitSnapshot(repo.path), request_for(repo),
        config=PRConfig(), llm=fake_llm(["[]"]), offline=False,
    )
    assert result.status == "skipped"
    assert result.summary.get("scope_reasons")


def test_oversized_pr_marks_incomplete(make_repo, request_for, fake_llm):
    base = {"src/main.cpp": CLEAN_BASE}
    head = {f"src/file{i}.cpp": "int value = 0;\n" for i in range(5)}
    head["src/main.cpp"] = CLEAN_HEAD
    repo = make_repo(base, head, head_msg="feat: many files")
    result = run_analysis(
        LocalGitSnapshot(repo.path), request_for(repo),
        config=PRConfig(budget=BudgetConfig(max_files=3)),
        llm=fake_llm(["[]"]), offline=False,
    )
    assert result.status == "incomplete"
    assert result.summary["files_reviewed"] == 3
    assert result.not_covered
    assert "预算" in result.status_reason
