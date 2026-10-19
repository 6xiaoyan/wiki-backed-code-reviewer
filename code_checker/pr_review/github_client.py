"""最小 GitHub REST 客户端（仅标准库）。

约束：
  * 只提供 PR 审查需要的只读接口 + 汇总评论读写接口。
  * 令牌只保存在内存中，不写入日志/异常消息。
  * 不提供执行任意 API 请求的公共方法，发布阶段也只用固定接口。
  * transport 可注入，便于离线测试分页、限流与错误处理。
"""

from __future__ import annotations

import json
import random
import time
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_API_URL = "https://api.github.com"
API_VERSION = "2022-11-28"
USER_AGENT = "wiki-backed-code-reviewer/1.0"


class GitHubError(RuntimeError):
    def __init__(self, status: int, message: str, *, url: str = "", retryable: bool = False):
        super().__init__(f"GitHub API 错误 ({status}): {message}")
        self.status = status
        self.message = message
        self.url = url
        self.retryable = retryable


class GitHubAuthError(GitHubError):
    pass


class GitHubNotFound(GitHubError):
    pass


def _default_transport(method: str, url: str, headers: dict, data: bytes | None,
                       timeout: float) -> tuple[int, dict, bytes]:
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as exc:
        body = b""
        try:
            body = exc.read()
        except Exception:
            pass
        return exc.code, dict(exc.headers or {}), body


class GitHubClient:
    """仅暴露固定接口的 GitHub 客户端。"""

    def __init__(self, token: str = "", *, api_url: str = DEFAULT_API_URL,
                 timeout: float = 30.0, transport=None, sleep=time.sleep,
                 max_retries: int = 3, user_agent: str = USER_AGENT):
        self._token = token or ""
        self.api_url = api_url.rstrip("/")
        self.timeout = timeout
        self._transport = transport or _default_transport
        self._sleep = sleep
        self.max_retries = max_retries
        self.user_agent = user_agent

    # ── 内部请求 ──
    def __repr__(self) -> str:  # 防止令牌进入日志
        return f"GitHubClient(api_url={self.api_url!r}, authenticated={bool(self._token)})"

    def _headers(self, accept: str) -> dict:
        headers = {
            "Accept": accept,
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": self.user_agent,
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def _request(self, method: str, path: str, *, accept: str = "application/vnd.github+json",
                 data: dict | None = None, allow_404: bool = False,
                 raw: bool = False) -> tuple[object, dict]:
        url = path if path.startswith("http") else f"{self.api_url}{path}"
        body = json.dumps(data).encode("utf-8") if data is not None else None
        headers = self._headers(accept)
        if body is not None:
            headers["Content-Type"] = "application/json"

        last_exc: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                status, resp_headers, resp_body = self._transport(
                    method, url, headers, body, self.timeout,
                )
            except Exception as exc:  # 网络层异常
                last_exc = exc
                if attempt + 1 < self.max_retries:
                    self._sleep(self._backoff(attempt))
                    continue
                raise GitHubError(0, f"网络请求失败: {exc}", url=url, retryable=True) from exc

            if status in (200, 201, 204):
                if raw:
                    return resp_body, resp_headers
                if not resp_body:
                    return None, resp_headers
                return json.loads(resp_body.decode("utf-8")), resp_headers

            text = ""
            try:
                text = resp_body.decode("utf-8", errors="replace")[:500]
            except Exception:
                pass

            if status == 404:
                if allow_404:
                    return None, resp_headers
                raise GitHubNotFound(404, text or "资源不存在", url=url)
            if status in (401, 403):
                # 403 也可能是限流；检查是否可重试
                if status == 403 and ("rate limit" in text.lower()
                                      or resp_headers.get("X-RateLimit-Remaining") == "0"):
                    last_exc = GitHubError(403, text, url=url, retryable=True)
                    if attempt + 1 < self.max_retries:
                        self._sleep(self._backoff(attempt, resp_headers))
                        continue
                    raise last_exc
                raise GitHubAuthError(status, text or "鉴权失败", url=url)
            if status in (429, 500, 502, 503, 504):
                last_exc = GitHubError(status, text or "服务端错误", url=url, retryable=True)
                if attempt + 1 < self.max_retries:
                    self._sleep(self._backoff(attempt, resp_headers))
                    continue
                raise last_exc
            raise GitHubError(status, text or "请求失败", url=url)

        raise last_exc or GitHubError(0, "未知请求失败", url=url)

    def _backoff(self, attempt: int, headers: dict | None = None) -> float:
        if headers:
            retry_after = headers.get("Retry-After") or headers.get("retry-after")
            if retry_after:
                try:
                    return min(60.0, max(0.0, float(retry_after)))
                except ValueError:
                    pass
        return min(30.0, (2 ** attempt) + random.uniform(0.0, 1.0))

    # ── 只读接口 ──
    def get_authenticated_user(self) -> str:
        data, _ = self._request("GET", "/user")
        return str((data or {}).get("login") or "")

    def get_pull(self, repo: str, pr_number: int) -> dict:
        data, _ = self._request("GET", f"/repos/{repo}/pulls/{int(pr_number)}")
        return data or {}

    def compare(self, repo: str, base_sha: str, head_sha: str) -> dict:
        path = f"/repos/{repo}/compare/{urllib.parse.quote(base_sha)}...{urllib.parse.quote(head_sha)}"
        data, _ = self._request("GET", path)
        return data or {}

    def get_commit(self, repo: str, sha: str) -> dict:
        data, _ = self._request("GET", f"/repos/{repo}/commits/{urllib.parse.quote(sha)}")
        return data or {}

    def get_tree(self, repo: str, sha: str, recursive: bool = True) -> dict:
        suffix = "?recursive=1" if recursive else ""
        data, _ = self._request("GET", f"/repos/{repo}/git/trees/{urllib.parse.quote(sha)}{suffix}")
        return data or {}

    def get_blob(self, repo: str, blob_sha: str) -> dict:
        data, _ = self._request("GET", f"/repos/{repo}/git/blobs/{urllib.parse.quote(blob_sha)}")
        return data or {}

    def list_issue_comments(self, repo: str, pr_number: int, *,
                            max_pages: int = 10, per_page: int = 100) -> list[dict]:
        comments: list[dict] = []
        for page in range(1, max_pages + 1):
            data, _ = self._request(
                "GET",
                f"/repos/{repo}/issues/{int(pr_number)}/comments"
                f"?per_page={per_page}&page={page}",
            )
            batch = data or []
            if not isinstance(batch, list):
                raise GitHubError(0, "评论接口返回了非列表数据")
            comments.extend(batch)
            if len(batch) < per_page:
                break
        return comments

    def list_run_artifacts(self, repo: str, run_id: int) -> list[dict]:
        """列出本次 Actions 运行的 artifact（用于在评论中给出下载入口）。"""
        data, _ = self._request(
            "GET", f"/repos/{repo}/actions/runs/{int(run_id)}/artifacts",
        )
        return list((data or {}).get("artifacts") or [])

    # ── 写接口（publish job 专用）──
    def create_issue_comment(self, repo: str, pr_number: int, body: str) -> dict:
        data, _ = self._request(
            "POST", f"/repos/{repo}/issues/{int(pr_number)}/comments", data={"body": body},
        )
        return data or {}

    def update_issue_comment(self, repo: str, comment_id: int, body: str) -> dict:
        data, _ = self._request(
            "PATCH", f"/repos/{repo}/issues/comments/{int(comment_id)}", data={"body": body},
        )
        return data or {}
