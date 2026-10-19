"""GitHub REST 客户端：分页、重试、鉴权与令牌不泄露。"""

import json

import pytest

from code_checker.pr_review.github_client import (
    GitHubAuthError,
    GitHubClient,
    GitHubError,
    GitHubNotFound,
)


class Transport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def __call__(self, method, url, headers, data, timeout):
        self.requests.append({
            "method": method, "url": url, "headers": dict(headers),
            "data": json.loads(data.decode()) if data else None,
        })
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def _client(responses, **kwargs):
    transport = Transport(responses)
    return GitHubClient("secret-token-value", transport=transport,
                        sleep=lambda s: None, **kwargs), transport


def test_headers_and_token_redaction():
    client, transport = _client([(200, {}, b'{"login": "bot"}')])
    assert client.get_authenticated_user() == "bot"
    req = transport.requests[0]
    assert req["headers"]["Authorization"] == "Bearer secret-token-value"
    assert req["headers"]["X-GitHub-Api-Version"] == "2022-11-28"
    assert "secret-token-value" not in repr(client)


def test_comment_pagination():
    first = [{"id": i, "body": "x", "user": {"login": "u"}} for i in range(100)]
    second = [{"id": 100, "body": "y", "user": {"login": "u"}}]
    client, transport = _client([
        (200, {}, json.dumps(first).encode()),
        (200, {}, json.dumps(second).encode()),
    ])
    comments = client.list_issue_comments("owner/repo", 7)
    assert len(comments) == 101
    assert len(transport.requests) == 2
    assert "page=2" in transport.requests[1]["url"]


def test_rate_limit_retry():
    client, transport = _client([
        (429, {"Retry-After": "0"}, b"rate limit"),
        (200, {}, b'{"number": 7, "state": "open", "head": {"sha": "abc"}}'),
    ])
    pull = client.get_pull("owner/repo", 7)
    assert pull["number"] == 7
    assert len(transport.requests) == 2


def test_auth_error_not_retried():
    client, transport = _client([(401, {}, b"bad credentials")])
    with pytest.raises(GitHubAuthError):
        client.get_pull("owner/repo", 7)
    assert len(transport.requests) == 1


def test_not_found():
    client, _ = _client([(404, {}, b"not found")])
    with pytest.raises(GitHubNotFound):
        client.get_commit("owner/repo", "deadbeef")
    client, _ = _client([(404, {}, b"not found")])
    assert client._request("GET", "/x", allow_404=True)[0] is None


def test_network_error_is_retried_then_reported():
    client, transport = _client([OSError("boom"), OSError("boom"), OSError("boom")])
    with pytest.raises(GitHubError) as exc:
        client.get_pull("owner/repo", 7)
    assert "网络请求失败" in str(exc.value)
    assert len(transport.requests) == 3
    assert "secret-token-value" not in str(exc.value)


def test_create_and_update_comment_payloads():
    client, transport = _client([
        (201, {}, b'{"id": 1, "body": "hi", "user": {"login": "bot"}}'),
        (200, {}, b'{"id": 1, "body": "hi2", "user": {"login": "bot"}}'),
    ])
    client.create_issue_comment("owner/repo", 7, "hi")
    client.update_issue_comment("owner/repo", 1, "hi2")
    assert transport.requests[0]["method"] == "POST"
    assert transport.requests[0]["data"] == {"body": "hi"}
    assert transport.requests[1]["method"] == "PATCH"
    assert transport.requests[1]["url"].endswith("/issues/comments/1")
