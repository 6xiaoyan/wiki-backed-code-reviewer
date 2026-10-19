"""发布：校验分析产物并把汇总评论写回 PR（PRD §5、§8、§9）。

publish job 不持有模型凭据，只做：
  1. 校验 JSON schema/大小/仓库/PR/head/run 一致性，并拒绝含疑似凭据的产物；
  2. 重新读取 PR：head 变化或 PR 已关闭 → superseded，不写评论；
  3. 查找“作者为机器人 + 含隐藏标记”的唯一汇总评论，更新或创建；
  4. 不执行产物中的任何代码。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from code_checker.pr_review.models import (
    ALL_STATUSES,
    STATUS_SUPERSEDED,
    ReviewResult,
    make_review_key,
)
from code_checker.pr_review.report import (
    SUMMARY_MARKER,
    render_comment,
)

SCHEMA_VERSION = 1
MAX_PAYLOAD_BYTES = 4 * 1024 * 1024
MAX_COMMENT_BYTES = 65000  # GitHub 上限 65536，留出安全余量
DEFAULT_BOT_LOGIN = "github-actions[bot]"

_SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)


class PublishError(RuntimeError):
    """产物不合法或发布前置条件不满足。"""


@dataclass
class PublishDecision:
    action: str  # created | updated | skipped | superseded | dry_run
    reason: str = ""
    comment_id: int | None = None
    comment_url: str = ""
    body: str = ""
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "reason": self.reason,
            "comment_id": self.comment_id,
            "comment_url": self.comment_url,
            "comment_length": len(self.body),
            "details": self.details,
        }


def contains_secret(text: str) -> str:
    """返回命中的凭据类型；未命中返回空串。"""
    for rx in _SECRET_PATTERNS:
        if rx.search(text):
            return rx.pattern
    return ""


def validate_result_payload(payload: dict, *, expected_repo: str, expected_pr: int,
                            expected_head_sha: str = "", expected_run_id: str = "",
                            ) -> ReviewResult:
    """校验分析产物。任何不一致都拒绝发布，避免旧结果覆盖新结果。"""
    if not isinstance(payload, dict):
        raise PublishError("产物不是 JSON 对象")
    raw = json.dumps(payload, ensure_ascii=False)
    if len(raw.encode("utf-8")) > MAX_PAYLOAD_BYTES:
        raise PublishError(f"产物超过大小上限（{MAX_PAYLOAD_BYTES} 字节）")
    hit = contains_secret(raw)
    if hit:
        raise PublishError(f"产物包含疑似凭据（模式 {hit}），拒绝发布")

    if int(payload.get("schema_version") or 0) != SCHEMA_VERSION:
        raise PublishError(f"schema_version 不支持: {payload.get('schema_version')!r}")
    if str(payload.get("status") or "") not in ALL_STATUSES:
        raise PublishError(f"非法状态: {payload.get('status')!r}")

    result = ReviewResult.from_dict(payload)
    req = result.request
    if req.repo != expected_repo:
        raise PublishError(f"仓库不一致: 产物 {req.repo!r} vs 期望 {expected_repo!r}")
    if int(req.pr_number) != int(expected_pr):
        raise PublishError(f"PR 编号不一致: {req.pr_number} vs {expected_pr}")
    if expected_head_sha and req.head_sha != expected_head_sha:
        raise PublishError(
            f"head SHA 不一致: 产物 {req.head_sha} vs 期望 {expected_head_sha}"
        )
    if expected_run_id and str(req.run_id) != str(expected_run_id):
        raise PublishError(f"run_id 不一致: 产物 {req.run_id} vs 期望 {expected_run_id}")

    recomputed = make_review_key(req)
    if result.review_key and result.review_key != recomputed:
        raise PublishError("review_key 与请求内容不一致，产物可能被篡改")

    if len(result.findings) > 500 or len(result.uncertain_findings) > 500:
        raise PublishError("问题数量异常，拒绝发布")
    for f in result.findings:
        if f.severity not in ("critical", "warning", "suggestion", "info"):
            raise PublishError(f"非法严重度: {f.severity!r}")
        if f.line < 0:
            raise PublishError(f"非法行号: {f.line}")
        if not f.file or len(f.file) > 400:
            raise PublishError(f"非法文件路径: {f.file!r}")
    return result


class Publisher:
    def __init__(self, client, *, bot_login: str = "", dry_run: bool = False):
        self.client = client
        self.bot_login = bot_login or DEFAULT_BOT_LOGIN
        self.dry_run = dry_run

    # ── 评论查找 ──
    def find_summary_comment(self, repo: str, pr_number: int) -> dict | None:
        """只接受“机器人作者 + 隐藏标记”的评论，忽略用户伪造标记。"""
        comments = self.client.list_issue_comments(repo, pr_number)
        candidates = [
            c for c in comments
            if str((c.get("user") or {}).get("login") or "") == self.bot_login
            and SUMMARY_MARKER in str(c.get("body") or "")
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda c: int(c.get("id") or 0))
        return candidates[0]

    # ── 发布 ──
    def publish(self, result: ReviewResult, *, expected_repo: str, expected_pr: int,
                expected_run_id: str = "", artifact_url: str = "") -> PublishDecision:
        if artifact_url:
            result.artifacts = dict(result.artifacts or {})
            result.artifacts["artifact_url"] = artifact_url

        # ── 写前再次读取 PR，防止旧结果覆盖新结果 ──
        try:
            pr = self.client.get_pull(expected_repo, expected_pr)
        except Exception as exc:
            raise PublishError(f"发布前读取 PR 失败: {exc}") from exc
        state = str(pr.get("state") or "")
        latest_head = str(((pr.get("head") or {}).get("sha")) or "")
        if state != "open":
            result.status = STATUS_SUPERSEDED
            result.status_reason = f"PR 状态为 {state}，不发布旧结论"
            return PublishDecision("superseded", result.status_reason)
        if latest_head and latest_head != result.request.head_sha:
            result.status = STATUS_SUPERSEDED
            result.status_reason = (
                f"发布前发现新的 head {latest_head[:7]}，"
                f"本次结果对应 {result.request.head_sha[:7]}，不更新评论"
            )
            return PublishDecision("superseded", result.status_reason)

        body = render_comment(result)
        if SUMMARY_MARKER not in body:
            raise PublishError("评论缺少隐藏标记")
        if body.count(SUMMARY_MARKER) != 1:
            raise PublishError("评论包含多个隐藏标记")
        if len(body.encode("utf-8")) > MAX_COMMENT_BYTES:
            raise PublishError(f"评论超过长度上限（{len(body)} 字符）")
        if contains_secret(body):
            raise PublishError("评论包含疑似凭据，拒绝发布")

        existing = self.find_summary_comment(expected_repo, expected_pr)
        if self.dry_run:
            return PublishDecision(
                "dry_run", "dry-run 模式未写入 GitHub",
                comment_id=int(existing["id"]) if existing else None,
                body=body,
            )
        if existing:
            comment = self.client.update_issue_comment(
                expected_repo, int(existing["id"]), body,
            )
            return PublishDecision(
                "updated", "更新已有机器人汇总评论",
                comment_id=int(comment.get("id") or existing["id"]),
                comment_url=str(comment.get("html_url") or ""), body=body,
            )
        comment = self.client.create_issue_comment(expected_repo, expected_pr, body)
        return PublishDecision(
            "created", "创建机器人汇总评论",
            comment_id=int(comment.get("id") or 0) or None,
            comment_url=str(comment.get("html_url") or ""), body=body,
        )


def artifact_url_for_run(client, repo: str, run_id: str, artifact_name: str) -> str:
    """在运行已上传的 artifact 中查找下载入口（只读接口）。"""
    if not run_id or not artifact_name:
        return ""
    try:
        artifacts = client.list_run_artifacts(repo, int(run_id))
    except Exception:
        return ""
    for art in artifacts:
        if str(art.get("name") or "") == artifact_name:
            return str(art.get("html_url") or "")
    return ""
