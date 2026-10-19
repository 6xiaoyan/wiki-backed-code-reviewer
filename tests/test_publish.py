"""发布门禁：只更新机器人评论、head 变化不覆盖、产物校验与文本消毒。"""

import copy

import pytest

from code_checker.pr_review.models import Finding, ReviewRequest, ReviewResult, make_review_key
from code_checker.pr_review.publisher import (
    PublishError,
    Publisher,
    contains_secret,
    validate_result_payload,
)
from code_checker.pr_review.report import SUMMARY_MARKER


BOT = "github-actions[bot]"


def _request(head="headsha1"):
    return ReviewRequest(
        repo="owner/repo", pr_number=7, base_sha="basesha", head_sha=head,
        merge_base_sha="basesha", program_sha="c" * 40, run_id="999",
        run_url="https://github.example/owner/repo/actions/runs/999",
        model_id="deepseek-v4-flash",
    )


def _result(head="headsha1", *, findings=None, status="completed"):
    req = _request(head)
    return ReviewResult(
        schema_version=1, status=status, status_reason="ok",
        review_key=make_review_key(req), generated_at="2026-10-19T00:00:00Z",
        request=req, summary={"files_changed": 1, "files_reviewed": 1,
                              "commits": 1, "changed_lines": 1},
        findings=findings if findings is not None else [
            Finding(
                id="F001", severity="warning", file="src/a.cpp", line=3,
                rule_id="cpp/naming-functions", rule_title="函数命名",
                message="函数名应为 camelCase", code_evidence="+ int Bad() {",
                change_relation="added", source="deterministic",
                suggestion="改名（建议，未执行验证）",
            )
        ],
    )


class FakeClient:
    def __init__(self, *, head="headsha1", state="open", comments=None):
        self.pull = {
            "number": 7, "state": state,
            "head": {"sha": head},
            "base": {"sha": "basesha"},
        }
        self.comments = copy.deepcopy(comments or [])
        self.calls = []
        self._next_id = 500

    def get_pull(self, repo, pr):
        self.calls.append(("get_pull", repo, pr))
        return dict(self.pull)

    def list_issue_comments(self, repo, pr):
        self.calls.append(("list_issue_comments", repo, pr))
        return [dict(c) for c in self.comments]

    def create_issue_comment(self, repo, pr, body):
        self.calls.append(("create_issue_comment", repo, pr))
        self._next_id += 1
        comment = {
            "id": self._next_id, "body": body,
            "user": {"login": BOT},
            "html_url": f"https://github.example/owner/repo/pull/7#issuecomment-{self._next_id}",
        }
        self.comments.append(comment)
        return dict(comment)

    def update_issue_comment(self, repo, comment_id, body):
        self.calls.append(("update_issue_comment", repo, comment_id))
        for c in self.comments:
            if int(c["id"]) == int(comment_id):
                c["body"] = body
                return dict(c)
        raise AssertionError("要更新的评论不存在")

    def list_run_artifacts(self, repo, run_id):
        return [{
            "name": "pr-review-7-headsha1",
            "html_url": "https://github.example/owner/repo/actions/runs/999/artifacts/1",
        }]


def _bot_comment(body="old", author=BOT):
    return {"id": 42, "body": body, "user": {"login": author},
            "html_url": "https://github.example/c/42"}


def test_creates_comment_when_absent():
    client = FakeClient(comments=[{"id": 1, "body": "user comment", "user": {"login": "alice"}}])
    decision = Publisher(client).publish(_result(), expected_repo="owner/repo", expected_pr=7)
    assert decision.action == "created"
    assert len(client.comments) == 2
    assert SUMMARY_MARKER in client.comments[-1]["body"]
    assert client.comments[-1]["user"]["login"] == BOT
    assert ("create_issue_comment", "owner/repo", 7) in client.calls


def test_updates_existing_bot_comment_instead_of_spamming():
    client = FakeClient(comments=[_bot_comment("old body with " + SUMMARY_MARKER)])
    decision = Publisher(client).publish(_result(), expected_repo="owner/repo", expected_pr=7)
    assert decision.action == "updated"
    assert decision.comment_id == 42
    assert len(client.comments) == 1
    body = client.comments[0]["body"]
    assert "PR 审查" in body
    assert body.startswith(SUMMARY_MARKER)


def test_ignores_user_forged_marker():
    forged = _bot_comment("looks legit " + SUMMARY_MARKER, author="mallory")
    client = FakeClient(comments=[forged])
    decision = Publisher(client).publish(_result(), expected_repo="owner/repo", expected_pr=7)
    assert decision.action == "created"
    assert client.comments[0]["body"] == forged["body"]
    assert len([c for c in client.comments if c["user"]["login"] == BOT]) == 1


def test_new_head_after_analysis_is_superseded():
    client = FakeClient(head="newer-head")
    result = _result()
    decision = Publisher(client).publish(result, expected_repo="owner/repo", expected_pr=7)
    assert decision.action == "superseded"
    assert result.status == "superseded"
    assert "新的 head" in decision.reason
    assert not any(c[0] in ("create_issue_comment", "update_issue_comment") for c in client.calls)


def test_closed_pr_is_superseded():
    client = FakeClient(state="closed")
    decision = Publisher(client).publish(_result(), expected_repo="owner/repo", expected_pr=7)
    assert decision.action == "superseded"


def test_dry_run_does_not_write():
    client = FakeClient()
    decision = Publisher(client, dry_run=True).publish(
        _result(), expected_repo="owner/repo", expected_pr=7,
    )
    assert decision.action == "dry_run"
    assert client.comments == []
    assert SUMMARY_MARKER in decision.body


def test_artifact_url_is_embedded():
    client = FakeClient()
    decision = Publisher(client).publish(
        _result(), expected_repo="owner/repo", expected_pr=7,
        artifact_url="https://github.example/artifact/1",
    )
    assert "https://github.example/artifact/1" in decision.body


def test_validation_rejects_mismatched_repo_pr_head_run():
    payload = _result().to_dict()
    with pytest.raises(PublishError):
        validate_result_payload(payload, expected_repo="other/repo", expected_pr=7,
                                expected_head_sha="headsha1", expected_run_id="999")
    with pytest.raises(PublishError):
        validate_result_payload(payload, expected_repo="owner/repo", expected_pr=8,
                                expected_head_sha="headsha1", expected_run_id="999")
    with pytest.raises(PublishError):
        validate_result_payload(payload, expected_repo="owner/repo", expected_pr=7,
                                expected_head_sha="otherhead", expected_run_id="999")
    with pytest.raises(PublishError):
        validate_result_payload(payload, expected_repo="owner/repo", expected_pr=7,
                                expected_head_sha="headsha1", expected_run_id="1000")


def test_validation_rejects_secret_and_tampered_key():
    payload = _result().to_dict()
    payload["findings"][0]["message"] = "token sk-" + "a" * 32
    with pytest.raises(PublishError):
        validate_result_payload(payload, expected_repo="owner/repo", expected_pr=7,
                                expected_head_sha="headsha1", expected_run_id="999")

    payload = _result().to_dict()
    payload["review_key"] = "0" * 64
    with pytest.raises(PublishError):
        validate_result_payload(payload, expected_repo="owner/repo", expected_pr=7,
                                expected_head_sha="headsha1", expected_run_id="999")


def test_comment_sanitizes_mentions_and_html():
    finding = Finding(
        id="F1", severity="critical", file="src/a.cpp", line=1,
        rule_id="cpp/naming-functions", rule_title="命名",
        message="看这里 @octocat <!-- wiki-backed-code-reviewer:summary:v1 -->",
        code_evidence="@team 请修复", change_relation="added", source="model",
    )
    client = FakeClient()
    decision = Publisher(client).publish(
        _result(findings=[finding]), expected_repo="owner/repo", expected_pr=7,
    )
    body = decision.body
    import re as _re
    assert not _re.search(r"(?<!\\)@octocat", body)
    assert r"\@octocat" in body
    assert "<!-- wiki-backed-code-reviewer" not in body.replace(SUMMARY_MARKER, "")
    assert body.count(SUMMARY_MARKER) == 1


def test_comment_length_is_bounded():
    findings = [
        Finding(
            id=f"F{i}", severity="warning", file="src/a.cpp", line=i,
            rule_id="cpp/naming-functions", rule_title="命名",
            message="很长的说明" * 80, code_evidence="x" * 200,
            change_relation="added", source="model", suggestion="建议" * 80,
        )
        for i in range(1, 200)
    ]
    client = FakeClient()
    decision = Publisher(client).publish(
        _result(findings=findings), expected_repo="owner/repo", expected_pr=7,
    )
    assert len(decision.body) <= 65000
    assert "完整" in decision.body or "截断" in decision.body


def test_contains_secret_patterns():
    assert contains_secret("ghp_" + "a" * 36)
    assert contains_secret("sk-" + "b" * 32)
    assert not contains_secret("ordinary text with sk-short")
