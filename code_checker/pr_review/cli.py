"""``python -m code_checker.pr_review`` 的命令行入口。

子命令：
  analyze  读取固定 PR 版本、执行审查、导出 JSON/Markdown（analyze job）
  publish  校验产物并把汇总评论写回 PR（publish job，无模型凭据）
  local    在本地 Git 仓库上按两个 ref 模拟一次 PR 审查（离线演示/测试）

退出码（analyze）：completed/skipped=0，incomplete=2，failed=1。
publish 的退出码：成功/过时=0，校验或接口失败=1。
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from code_checker.pr_review.config import PRConfig
from code_checker.pr_review.github_client import GitHubClient, GitHubError
from code_checker.pr_review.models import (
    STATUS_EXIT_CODES,
    STATUS_FAILED,
    STATUS_SKIPPED,
    STATUS_SUPERSEDED,
    ReviewRequest,
    ReviewResult,
    make_review_key,
)
from code_checker.pr_review.publisher import (
    PublishError,
    Publisher,
    artifact_url_for_run,
    validate_result_payload,
)
from code_checker.pr_review.snapshot import (
    GitHubApiSnapshot,
    LocalGitSnapshot,
    SnapshotError,
)

DEFAULT_OUTPUT_DIR = "review-artifacts"


class CliError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# 公共辅助
# ---------------------------------------------------------------------------
def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default) or default


def _load_event(path: str) -> dict:
    if not path or not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh) or {}
    except (json.JSONDecodeError, OSError):
        return {}


def _run_meta() -> dict:
    run_id = _env("GITHUB_RUN_ID")
    server = _env("GITHUB_SERVER_URL", "https://github.com")
    repo = _env("GITHUB_REPOSITORY")
    return {
        "run_id": run_id,
        "run_attempt": int(_env("GITHUB_RUN_ATTEMPT", "1") or 1),
        "run_url": (f"{server}/{repo}/actions/runs/{run_id}" if run_id and repo else ""),
        "program_sha": _env("GITHUB_SHA"),
    }


def _write_status(output_dir: str, result: ReviewResult) -> str:
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "review-status.json")
    payload = {
        "status": result.status,
        "status_reason": result.status_reason,
        "pr_number": result.request.pr_number,
        "head_sha": result.request.head_sha,
        "base_sha": result.request.base_sha,
        "review_key": result.review_key,
        "has_result": True,
        "artifact_name": (result.artifacts or {}).get("artifact_name", ""),
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    return path


def _print_summary(result: ReviewResult) -> None:
    print("=" * 68)
    print(f"PR 审查: {result.request.repo}#{result.request.pr_number} "
          f"head={result.request.head_sha[:8]}")
    print(f"状态: {result.status} — {result.status_reason}")
    print(f"已确认问题: {len(result.findings)}；"
          f"不确定候选: {len(result.uncertain_findings)}；"
          f"已审查文件: {result.summary.get('files_reviewed', 0)}/"
          f"{result.summary.get('files_changed', 0)}")
    for f in result.findings[:10]:
        print(f"  - [{f.severity}] {f.file}:{f.line} {f.rule_id} — {f.message[:100]}")
    usage = result.budget_usage or {}
    if usage:
        print(f"模型请求: {usage.get('model_requests', 0)}/"
              f"{usage.get('model_requests_limit', '?')}；"
              f"耗时: {usage.get('elapsed_seconds', 0)}s")
    print(f"JSON: {(result.artifacts or {}).get('json_path', '-')}")
    print("=" * 68)


# ---------------------------------------------------------------------------
# 请求构建
# ---------------------------------------------------------------------------
def _request_from_pull(pull: dict, repo: str, trigger: str) -> ReviewRequest:
    base = pull.get("base") or {}
    head = pull.get("head") or {}
    meta = _run_meta()
    return ReviewRequest(
        repo=repo,
        pr_number=int(pull.get("number") or 0),
        base_sha=str(base.get("sha") or ""),
        head_sha=str(head.get("sha") or ""),
        merge_base_sha="",  # 由 snapshot 解析
        program_sha=meta["program_sha"],
        run_id=meta["run_id"],
        run_attempt=meta["run_attempt"],
        run_url=meta["run_url"],
        trigger=trigger,
        draft=bool(pull.get("draft")),
        pr_state=str(pull.get("state") or "open"),
    )


def _request_from_file(path: str, args) -> tuple[ReviewRequest, object]:
    """从 JSON 文件（或 stdin 的 ``-``）读取审查请求。

    这让 PR 入口可以接收标准输入对象，而不是把 Actions 环境变量
    直接暴露给领域 Agent。
    """
    if path == "-":
        raw = sys.stdin.read()
    else:
        with open(path, "r", encoding="utf-8") as fh:
            raw = fh.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CliError(f"请求文件不是合法 JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise CliError("请求文件必须是 JSON 对象")
    request = ReviewRequest.from_dict(data)
    if not request.repo or "/" not in request.repo:
        raise CliError("请求缺少 repo（owner/repo）")
    if not request.base_sha or not request.head_sha:
        raise CliError("请求缺少 base_sha/head_sha")

    if args.repo_path:
        snapshot = LocalGitSnapshot(args.repo_path)
        try:
            snapshot.verify_commit(request.base_sha)
            snapshot.verify_commit(request.head_sha)
        except SnapshotError as exc:
            raise CliError(str(exc)) from exc
    else:
        snapshot = GitHubApiSnapshot(GitHubClient(_env("GITHUB_TOKEN")), request.repo)
    if not request.merge_base_sha:
        try:
            request.merge_base_sha = snapshot.resolve_merge_base(
                request.base_sha, request.head_sha,
            )
        except SnapshotError as exc:
            raise CliError(f"无法确定共同祖先: {exc}") from exc
    return request, snapshot


def _build_request(args, config: PRConfig) -> tuple[ReviewRequest, object]:
    """返回 (request, snapshot)。"""
    request_file = getattr(args, "request_file", "") or ""
    if args.command != "local" and request_file:
        return _request_from_file(request_file, args)

    if args.command == "local":
        if not args.repo_path:
            raise CliError("local 模式需要 --repo-path")
        snapshot = LocalGitSnapshot(args.repo_path)
        try:
            base_sha = snapshot.resolve_ref(args.base)
            head_sha = snapshot.resolve_ref(args.head)
            merge_base = snapshot.resolve_merge_base(base_sha, head_sha)
        except SnapshotError as exc:
            raise CliError(str(exc)) from exc
        meta = _run_meta()
        request = ReviewRequest(
            repo=args.repo or "local/repository",
            pr_number=int(args.pr or 0),
            base_sha=base_sha,
            head_sha=head_sha,
            merge_base_sha=merge_base,
            program_sha=meta["program_sha"],
            run_id=meta["run_id"],
            run_attempt=meta["run_attempt"],
            run_url=meta["run_url"],
            trigger="local",
        )
        return request, snapshot

    token = _env("GITHUB_TOKEN")
    repo = args.repo or _env("GITHUB_REPOSITORY")
    event = _load_event(args.event_path or _env("GITHUB_EVENT_PATH"))
    trigger = _env("GITHUB_EVENT_NAME")

    if event.get("pull_request"):
        pull = event["pull_request"]
        repo = repo or str((pull.get("base") or {}).get("repo", {}).get("full_name") or "")
        request = _request_from_pull(pull, repo, trigger or "pull_request_target")
        pr_number = request.pr_number
    else:
        pr_number = int(args.pr or 0)
        if not pr_number:
            raise CliError("无法确定 PR 编号：既没有事件负载，也没有 --pr")
        client = GitHubClient(token)
        try:
            pull = client.get_pull(repo, pr_number)
        except GitHubError as exc:
            raise CliError(f"读取 PR 失败: {exc}") from exc
        request = _request_from_pull(pull, repo, trigger or "workflow_dispatch")

    if not request.repo or "/" not in request.repo:
        raise CliError(f"无法确定仓库（当前: {request.repo!r}）")
    if not request.base_sha or not request.head_sha:
        raise CliError("PR 数据缺少 base/head SHA")
    if args.pr and int(args.pr) != request.pr_number:
        raise CliError(f"--pr {args.pr} 与事件中的 PR #{request.pr_number} 不一致")

    if args.repo_path:
        snapshot = LocalGitSnapshot(args.repo_path)
        try:
            snapshot.resolve_merge_base(request.base_sha, request.head_sha)
        except SnapshotError as exc:
            raise CliError(
                f"{exc}。工作流需先用 `git fetch origin +refs/pull/"
                f"{request.pr_number}/head:refs/remotes/pr/head` 获取 PR head"
                f"（不检出、不执行）"
            ) from exc
    else:
        snapshot = GitHubApiSnapshot(GitHubClient(token), request.repo)
    try:
        request.merge_base_sha = snapshot.resolve_merge_base(
            request.base_sha, request.head_sha,
        )
    except SnapshotError as exc:
        raise CliError(f"无法确定共同祖先: {exc}") from exc
    return request, snapshot


def _failed_result(args, config: PRConfig, message: str) -> ReviewResult:
    """即使无法构建正常请求，也导出一个可追查的失败结果。"""
    meta = _run_meta()
    pr = int(getattr(args, "pr", 0) or 0)
    repo = getattr(args, "repo", "") or _env("GITHUB_REPOSITORY") or "unknown/unknown"
    request = ReviewRequest(
        repo=repo, pr_number=pr, base_sha="", head_sha="", merge_base_sha="",
        program_sha=meta["program_sha"], run_id=meta["run_id"],
        run_attempt=meta["run_attempt"], run_url=meta["run_url"],
        trigger=_env("GITHUB_EVENT_NAME") or getattr(args, "command", ""),
        model_id=config.model_id,
    )
    return ReviewResult(
        schema_version=1, status=STATUS_FAILED, status_reason=message,
        review_key=make_review_key(request), generated_at="", request=request,
        errors=[message],
    )


# ---------------------------------------------------------------------------
# analyze
# ---------------------------------------------------------------------------
def cmd_analyze(args) -> int:
    config = PRConfig.from_env()
    out_dir = args.output_dir or _env("REVIEW_OUTPUT_DIR", DEFAULT_OUTPUT_DIR)
    offline = bool(args.offline) or config.offline

    # LangGraph 版本优先；不可用时退化为顺序版本（阶段实现相同）
    try:
        from code_checker.pr_review.graph_pr import run_analysis_graph as runner
    except Exception:
        from code_checker.pr_review.pipeline import run_analysis as runner

    try:
        request, snapshot = _build_request(args, config)
    except (CliError, SnapshotError) as exc:
        result = _failed_result(args, config, str(exc))
        from code_checker.pr_review.stages import write_artifacts

        result.artifacts.update(write_artifacts(result, out_dir))
        _write_status(out_dir, result)
        _print_summary(result)
        return 1

    try:
        result = runner(
            snapshot, request, config=config, offline=offline,
            artifact_dir=out_dir,
        )
    except Exception as exc:  # 崩溃也必须留下失败结果
        from code_checker.pr_review.stages import write_artifacts

        result = _failed_result(args, config, f"审查进程异常: {exc}")
        result.request = request
        result.review_key = make_review_key(request)
        result.artifacts.update(write_artifacts(result, out_dir))

    status_path = _write_status(out_dir, result)
    _print_summary(result)
    print(f"状态文件: {status_path}")
    return STATUS_EXIT_CODES.get(result.status, 1)


# ---------------------------------------------------------------------------
# publish
# ---------------------------------------------------------------------------
def cmd_publish(args) -> int:
    config = PRConfig.from_env()
    out_dir = args.output_dir or _env("REVIEW_OUTPUT_DIR", DEFAULT_OUTPUT_DIR)
    result_path = args.result or os.path.join(out_dir, "review-result.json")
    if not os.path.isfile(result_path):
        print(f"[publish] 找不到分析产物: {result_path}", file=sys.stderr)
        return 1
    try:
        with open(result_path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[publish] 读取产物失败: {exc}", file=sys.stderr)
        return 1

    repo = args.repo or _env("GITHUB_REPOSITORY")
    pr_number = int(args.pr or payload.get("request", {}).get("pr_number") or 0)
    if not repo or not pr_number:
        print("[publish] 缺少仓库或 PR 编号", file=sys.stderr)
        return 1

    token = _env("GITHUB_TOKEN")
    if not token and not args.dry_run:
        print("[publish] 缺少 GITHUB_TOKEN（publish job 需要 pull-requests: write）",
              file=sys.stderr)
        return 1

    try:
        result = validate_result_payload(
            payload,
            expected_repo=repo,
            expected_pr=pr_number,
            expected_head_sha=args.expected_head_sha or "",
            expected_run_id=args.expected_run_id or _env("GITHUB_RUN_ID"),
        )
    except PublishError as exc:
        print(f"[publish] 产物校验失败: {exc}", file=sys.stderr)
        return 1

    client = GitHubClient(token)
    artifact_url = ""
    if args.artifact_name:
        artifact_url = artifact_url_for_run(
            client, repo, _env("GITHUB_RUN_ID"), args.artifact_name,
        )
    publisher = Publisher(client, bot_login=args.bot_login or config.bot_login,
                          dry_run=args.dry_run)
    try:
        decision = publisher.publish(
            result, expected_repo=repo, expected_pr=pr_number,
            artifact_url=artifact_url,
        )
    except (PublishError, GitHubError) as exc:
        print(f"[publish] 发布失败: {exc}", file=sys.stderr)
        return 1

    os.makedirs(out_dir, exist_ok=True)
    decision_path = os.path.join(out_dir, "publish-decision.json")
    with open(decision_path, "w", encoding="utf-8") as fh:
        json.dump(decision.to_dict(), fh, ensure_ascii=False, indent=2)
    print(f"[publish] {decision.action}: {decision.reason}")
    if decision.comment_url:
        print(f"[publish] 评论: {decision.comment_url}")
    print(f"[publish] 决策记录: {decision_path}")
    if result.status == STATUS_SUPERSEDED:
        print("[publish] 结果已过时，未更新 PR 评论")
    return 0


# ---------------------------------------------------------------------------
# 参数解析
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m code_checker.pr_review",
        description="GitHub PR 代码审查（第一阶段）",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p):
        p.add_argument("--repo", default="", help="owner/repo（默认取 GITHUB_REPOSITORY）")
        p.add_argument("--pr", type=int, default=0, help="PR 编号")
        p.add_argument("--repo-path", default="", help="本地可信仓库检出路径")
        p.add_argument("--output-dir", default="", help="产物输出目录")
        p.add_argument("--offline", action="store_true",
                       help="离线：只跑确定性检查（结果标为 incomplete）")
        p.add_argument("--event-path", default="", help="GitHub 事件负载路径")

    analyze = sub.add_parser("analyze", help="执行审查并导出结果")
    common(analyze)
    analyze.add_argument("--request-file", default="", help="（可选）JSON 形式的请求")
    analyze.set_defaults(func=cmd_analyze)

    publish = sub.add_parser("publish", help="校验产物并写回 PR 评论")
    common(publish)
    publish.add_argument("--result", default="", help="review-result.json 路径")
    publish.add_argument("--expected-head-sha", default="",
                         help="来自 analyze 输出的 head SHA（校验一致性）")
    publish.add_argument("--expected-run-id", default="", help="校验产物来源 run")
    publish.add_argument("--artifact-name", default="", help="artifact 名称")
    publish.add_argument("--bot-login", default="", help="机器人账号登录名")
    publish.add_argument("--dry-run", action="store_true", help="只渲染不写入")
    publish.set_defaults(func=cmd_publish)

    local = sub.add_parser("local", help="本地模拟一次 PR 审查")
    common(local)
    local.add_argument("--base", default="main", help="基线 ref（默认 main）")
    local.add_argument("--head", default="HEAD", help="head ref（默认 HEAD）")
    local.set_defaults(func=cmd_analyze, command="local")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except CliError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
