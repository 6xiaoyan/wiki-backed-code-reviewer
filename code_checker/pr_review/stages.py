"""PR 审查流水线的阶段实现（LangGraph 节点与直接调用共用）。

每个 stage 接收并原地更新一个 ``AnalysisContext``，返回:
  "ok"       继续下一阶段
  "skipped"  按策略跳过（草稿/无适用改动），后续只导出结果
  "failed"   失败，后续只导出结果

阶段划分与 PRD §7 一致：prepare → deterministic → agents → verify → merge → export。
"""

from __future__ import annotations

import datetime as _dt
import json
import os
from dataclasses import dataclass, field
from typing import Any

from code_checker.pr_review import agents, evidence, report
from code_checker.pr_review.budget import BudgetExceeded, ReviewBudget
from code_checker.pr_review.config import (
    PRConfig,
    compute_config_digest,
    compute_prompts_digest,
    compute_rules_digest,
)
from code_checker.pr_review.context import ContextBuilder, build_file_context
from code_checker.pr_review.deterministic_pr import (
    filter_deterministic_violations,
    run_deterministic_checks,
)
from code_checker.pr_review.diff_parser import DiffParseError, parse_diff
from code_checker.pr_review.merge import merge_findings, severity_counts
from code_checker.pr_review.models import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_INCOMPLETE,
    STATUS_SKIPPED,
    ChangedFile,
    Finding,
    ReviewRequest,
    ReviewResult,
    make_review_key,
    stable_finding_id,
)
from code_checker.pr_review.scope import build_scope, domain_of
from code_checker.pr_review.snapshot import Snapshot, SnapshotError

SCHEMA_VERSION = 1


def utcnow() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class AnalysisContext:
    snapshot: Snapshot
    request: ReviewRequest
    config: PRConfig
    budget: ReviewBudget
    offline: bool
    artifact_dir: str | None = None
    registry: dict[str, dict] | None = None
    llm: Any = None

    result: ReviewResult = field(init=False)
    changed_files: list[ChangedFile] = field(default_factory=list)
    commits: list[dict] = field(default_factory=list)
    decision: Any = None
    head_contents: dict[str, str] = field(default_factory=dict)
    base_contents: dict[str, str] = field(default_factory=dict)
    raw_det: list[dict] = field(default_factory=list)
    det: dict = field(default_factory=dict)
    review: dict | None = None
    confirmed: list[Finding] = field(default_factory=list)
    uncertain: list[dict] = field(default_factory=list)
    filtered: list[dict] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    force_incomplete: bool = False
    fatal: str = ""

    def __post_init__(self) -> None:
        self.request.rules_digest = self.request.rules_digest or compute_rules_digest()
        self.request.prompts_digest = self.request.prompts_digest or compute_prompts_digest()
        self.request.config_digest = (
            self.request.config_digest or compute_config_digest(self.config)
        )
        self.request.model_id = self.request.model_id or self.config.model_id
        self.result = ReviewResult(
            schema_version=SCHEMA_VERSION,
            status=STATUS_FAILED,
            status_reason="",
            review_key=make_review_key(self.request),
            generated_at=utcnow(),
            request=self.request,
        )

    def degrade(self, stage: str, status: str, reason: str, impact: str) -> None:
        self.result.degradation.append({
            "stage": stage, "status": status, "reason": reason, "impact": impact,
        })

    def stop_skipped(self, reason: str, stage: str = "prepare") -> str:
        self.result.status = STATUS_SKIPPED
        self.result.status_reason = reason
        self.degrade(stage, "skipped", reason, "未执行模型审查")
        return "skipped"

    def stop_failed(self, reason: str, stage: str) -> str:
        self.result.status = STATUS_FAILED
        self.result.status_reason = reason
        self.result.errors.append(reason)
        self.degrade(stage, "failed", reason, "无法完成审查")
        self.fatal = reason
        return "failed"


# ---------------------------------------------------------------------------
# prepare：固定版本、diff、审查范围
# ---------------------------------------------------------------------------
def stage_prepare(ctx: AnalysisContext) -> str:
    if ctx.request.draft:
        return ctx.stop_skipped("草稿 PR：按策略跳过审查，不调用模型")
    if ctx.request.pr_state and ctx.request.pr_state != "open":
        return ctx.stop_skipped(
            f"PR 状态为 {ctx.request.pr_state}，新任务不调用模型"
        )

    try:
        with ctx.budget.phase("diff"):
            diff_text = ctx.snapshot.diff(
                ctx.request.merge_base_sha, ctx.request.head_sha,
            )
            ctx.changed_files = parse_diff(diff_text)
            ctx.commits = ctx.snapshot.commit_subjects(
                ctx.request.merge_base_sha, ctx.request.head_sha,
            )
    except (SnapshotError, DiffParseError) as exc:
        return ctx.stop_failed(f"无法准备 diff: {exc}", "diff")

    if not ctx.changed_files:
        return ctx.stop_skipped("PR 没有文件改动", "diff")

    try:
        with ctx.budget.phase("scope"):
            decision, head_contents = build_scope(
                ctx.changed_files, ctx.snapshot, ctx.request, ctx.config.budget,
            )
            base_contents: dict[str, str] = {}
            for cf in decision.included:
                if cf.status == "added":
                    continue
                try:
                    blob = ctx.snapshot.read_text(
                        cf.path, ctx.request.merge_base_sha,
                        max_bytes=ctx.config.budget.max_file_bytes,
                    )
                    base_contents[cf.path] = blob.text
                except SnapshotError as exc:
                    ctx.force_incomplete = True
                    ctx.reasons.append(f"{cf.path}: 无法读取改动前版本（{exc}）")
                    ctx.degrade("scope", "failed",
                                f"读取 {cf.path} 的改动前版本失败: {exc}",
                                "历史问题对比与删除行证据不可用")
    except SnapshotError as exc:
        return ctx.stop_failed(f"构建审查范围失败: {exc}", "scope")

    ctx.decision = decision
    ctx.head_contents = head_contents
    ctx.base_contents = base_contents
    ctx.result.excluded_files = decision.excluded
    ctx.result.not_covered = decision.not_covered
    ctx.result.summary["scope_reasons"] = decision.reasons
    if decision.status_override == "incomplete":
        ctx.force_incomplete = True
        ctx.reasons.extend(decision.reasons)
    if not decision.included:
        return ctx.stop_skipped(
            "；".join(decision.reasons) or "没有适用的代码改动", "scope",
        )
    return "ok"


# ---------------------------------------------------------------------------
# deterministic：复用现有确定性规则并过滤历史问题
# ---------------------------------------------------------------------------
def stage_deterministic(ctx: AnalysisContext) -> str:
    try:
        with ctx.budget.phase("deterministic"):
            ctx.raw_det = run_deterministic_checks(
                ctx.decision.included, ctx.head_contents,
            )
            ctx.det = filter_deterministic_violations(
                ctx.raw_det, ctx.decision.included,
                ctx.head_contents, ctx.base_contents,
            )
    except Exception as exc:  # 确定性规则执行异常 → 不可声称审查完成
        ctx.force_incomplete = True
        ctx.reasons.append(f"确定性检查失败: {exc}")
        ctx.degrade("deterministic_checker", "failed", str(exc),
                    "部分确定性规则未执行")
        ctx.det = {"confirmed": [], "uncertain": [], "filtered": []}
    ctx.confirmed = list(ctx.det["confirmed"])
    ctx.uncertain = list(ctx.det["uncertain"])
    ctx.filtered = list(ctx.det["filtered"])
    return "ok"


# ---------------------------------------------------------------------------
# agents：领域模型审查 + Git 确定性规则
# ---------------------------------------------------------------------------
def stage_agents(ctx: AnalysisContext) -> str:
    if ctx.offline:
        ctx.force_incomplete = True
        ctx.reasons.append("离线模式：只执行确定性检查，未执行完整 LLM 审查")
        ctx.degrade("llm_review", "skipped",
                    "离线模式（没有执行模型语义审查）",
                    "只能依赖确定性规则；不得声称已完成 LLM 审查")
        _append_git_findings(ctx)
        return "ok"

    if ctx.llm is None:
        try:
            from code_checker.config import has_llm_credentials
            from code_checker.config import llm as default_llm

            if not has_llm_credentials():
                return ctx.stop_failed(
                    "缺少模型凭据：请配置 DEEPSEEK_API_KEY（GitHub Secrets）",
                    "llm_review",
                )
            ctx.llm = default_llm
        except Exception as exc:
            return ctx.stop_failed(f"初始化模型客户端失败: {exc}", "llm_review")

    if ctx.registry is None:
        ctx.registry = evidence.default_rule_registry()

    try:
        ctx.review = _run_agent_reviews(ctx)
    except BudgetExceeded as exc:
        ctx.review = {
            "raw": [], "agent_failed": True, "reasons": [str(exc)],
            "degradation": [{
                "stage": "llm_review", "status": "failed",
                "reason": str(exc), "impact": "模型审查提前中止，结果不完整",
            }],
            "context_reads": [],
        }
    except Exception as exc:  # 领域 Agent 崩溃不能当作“未发现问题”
        ctx.review = {
            "raw": [], "agent_failed": True,
            "reasons": [f"领域 Agent 执行异常: {exc}"],
            "degradation": [{
                "stage": "llm_review", "status": "failed", "reason": str(exc),
                "impact": "模型审查未完成，结果不完整",
            }],
            "context_reads": [],
        }

    ctx.result.degradation.extend(ctx.review["degradation"])
    ctx.result.artifacts["context_reads"] = ctx.review["context_reads"]
    if ctx.review["agent_failed"]:
        ctx.force_incomplete = True
        ctx.reasons.extend(ctx.review["reasons"])

    _append_git_findings(ctx)
    return "ok"


def _append_git_findings(ctx: AnalysisContext) -> None:
    for item in agents.review_commits_deterministic(ctx.commits):
        ctx.confirmed.append(_git_finding(item, ctx.registry or {}))


def _git_finding(item: dict, registry: dict[str, dict]) -> Finding:
    rule_id = str(item.get("rule_id") or "git/commit-format")
    meta = registry.get(rule_id) or {}
    return Finding(
        id=stable_finding_id(item.get("file", ""), 1, rule_id, 0),
        severity=str(item.get("severity") or "suggestion"),
        file=str(item.get("file") or ""),
        line=0,
        rule_id=rule_id,
        rule_title=str(meta.get("title") or rule_id),
        message=str(item.get("message") or ""),
        code_evidence=str(item.get("code") or ""),
        change_relation="added",
        suggestion=str(item.get("suggestion") or ""),
        source="git",
    )


def _run_agent_reviews(ctx: AnalysisContext) -> dict:
    reviewer = agents.DomainReviewer(ctx.llm, ctx.budget, ctx.registry or {})
    ctx_builder = ContextBuilder(ctx.snapshot, ctx.budget)
    by_domain: dict[str, list] = {}
    for cf in ctx.decision.included:
        dom = domain_of(cf.path, ctx.head_contents.get(cf.path, ""))
        by_domain.setdefault(dom, []).append(cf)

    out = {"raw": [], "agent_failed": False, "reasons": [],
           "degradation": [], "context_reads": []}
    for domain, domain_files in sorted(by_domain.items()):
        for cf in domain_files:
            try:
                ctx.budget.check_deadline()
            except BudgetExceeded as exc:
                out["agent_failed"] = True
                out["reasons"].append(str(exc))
                out["degradation"].append({
                    "stage": f"{domain}_agent", "status": "failed",
                    "reason": str(exc), "impact": "审查提前中止，结果不完整",
                })
                out["context_reads"] = ctx_builder.reads_dict()
                return out

            hints = [v for v in ctx.raw_det if v.get("file") == cf.path]
            context = build_file_context(cf, ctx.head_contents.get(cf.path, ""))
            for header in _referenced_headers(cf, ctx.head_contents):
                try:
                    snippet = ctx_builder.read_range(
                        header, ctx.request.head_sha, 1, 120,
                        f"被 {cf.path} include 的直接相关头文件",
                    )
                    context += f"\n\n直接相关头文件 {header}（前 120 行）：\n{snippet}"
                except (SnapshotError, BudgetExceeded) as exc:
                    out["agent_failed"] = True
                    out["reasons"].append(f"{header}: 读取关联头文件失败（{exc}）")
                    out["degradation"].append({
                        "stage": "context", "status": "failed",
                        "reason": str(exc),
                        "impact": f"{cf.path} 缺少关联头文件上下文",
                    })
                    break
            try:
                raws, deg = reviewer.review_file(domain, cf, context, hints)
            except BudgetExceeded as exc:
                out["agent_failed"] = True
                out["reasons"].append(str(exc))
                out["degradation"].append({
                    "stage": f"{domain}_agent", "status": "failed",
                    "reason": str(exc), "impact": "审查提前中止，结果不完整",
                })
                out["context_reads"] = ctx_builder.reads_dict()
                return out
            if deg.get("status") != "ok":
                out["degradation"].append(deg)
            if deg.get("status") == "failed":
                out["agent_failed"] = True
                out["reasons"].append(
                    f"{domain} Agent 未完成: {deg.get('reason')}"
                )
            out["raw"].extend(raws)
    out["context_reads"] = ctx_builder.reads_dict()
    return out


def _referenced_headers(cf, head_contents: dict[str, str]) -> list[str]:
    from code_checker.pr_review.context import related_header_candidates

    if not cf.path.endswith((".cpp", ".cc")):
        return []
    candidates = related_header_candidates(cf.path, set(head_contents))
    if not candidates:
        return []
    text = head_contents.get(cf.path, "")
    return [h for h in candidates if h.rsplit("/", 1)[-1] in text]


# ---------------------------------------------------------------------------
# verify：模型发现必须与固定版本和改动范围对得上
# ---------------------------------------------------------------------------
def stage_verify(ctx: AnalysisContext) -> str:
    if not ctx.review or not ctx.review.get("raw"):
        return "ok"
    if ctx.registry is None:
        ctx.registry = evidence.default_rule_registry()
    verified = evidence.verify_findings(
        ctx.review["raw"],
        files=ctx.decision.included,
        head_contents=ctx.head_contents,
        base_contents=ctx.base_contents,
        registry=ctx.registry,
        default_source="model",
    )
    ctx.confirmed.extend(verified["confirmed"])
    ctx.uncertain.extend(verified["uncertain"])
    ctx.filtered.extend(verified["filtered"])
    return "ok"


# ---------------------------------------------------------------------------
# merge：确定性去重、统计、状态判定
# ---------------------------------------------------------------------------
def stage_merge(ctx: AnalysisContext) -> str:
    merged = merge_findings(ctx.confirmed)
    counts = severity_counts(merged)
    ctx.result.findings = merged
    ctx.result.uncertain_findings = ctx.uncertain
    ctx.result.filtered_findings = ctx.filtered
    ctx.result.reviewed_files = [
        {
            "path": cf.path,
            "old_path": cf.old_path,
            "status": cf.status,
            "domain": domain_of(cf.path, ctx.head_contents.get(cf.path, "")),
            "additions": cf.additions,
            "deletions": cf.deletions,
        }
        for cf in ctx.decision.included
    ]
    ctx.result.summary.update({
        "files_changed": len(ctx.changed_files),
        "files_reviewed": len(ctx.decision.included),
        "files_excluded": len(ctx.decision.excluded),
        "files_not_covered": len(ctx.decision.not_covered),
        "changed_lines": ctx.decision.applicable_changed_lines,
        "commits": len(ctx.commits),
        "confirmed_findings": len(merged),
        "uncertain_findings": len(ctx.uncertain),
        "by_severity": counts,
    })
    if ctx.force_incomplete:
        ctx.result.status = STATUS_INCOMPLETE
        ctx.result.status_reason = (
            "；".join(dict.fromkeys(r for r in ctx.reasons if r)) or "审查未完成"
        )
    else:
        ctx.result.status = STATUS_COMPLETED
        ctx.result.status_reason = "所有必要阶段完成"
    return "ok"


# ---------------------------------------------------------------------------
# export：写 JSON / Markdown / 评论草稿
# ---------------------------------------------------------------------------
def stage_export(ctx: AnalysisContext) -> str:
    ctx.result.budget_usage = ctx.budget.usage()
    ctx.result.artifacts = dict(ctx.result.artifacts or {})
    if ctx.artifact_dir:
        ctx.result.artifacts.update(write_artifacts(ctx.result, ctx.artifact_dir))
    return "ok"


# ---------------------------------------------------------------------------
# 产物
# ---------------------------------------------------------------------------
def artifact_name(request: ReviewRequest) -> str:
    return f"pr-review-{request.pr_number}-{request.head_sha[:8]}"


def write_artifacts(result: ReviewResult, out_dir: str) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, "review-result.json")
    report_path = os.path.join(out_dir, "review-report.md")
    comment_path = os.path.join(out_dir, "pr-comment.md")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(result.to_dict(), fh, ensure_ascii=False, indent=2)
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write(report.render_report(result))
    with open(comment_path, "w", encoding="utf-8") as fh:
        fh.write(report.render_comment(result))
    return {
        "json_path": json_path,
        "report_path": report_path,
        "comment_path": comment_path,
        "artifact_name": artifact_name(result.request),
    }


def load_result(path: str) -> ReviewResult:
    with open(path, "r", encoding="utf-8") as fh:
        return ReviewResult.from_dict(json.load(fh))


def build_context(
    snapshot: Snapshot,
    request: ReviewRequest,
    *,
    config: PRConfig | None = None,
    llm=None,
    registry: dict[str, dict] | None = None,
    offline: bool | None = None,
    artifact_dir: str | None = None,
    budget: ReviewBudget | None = None,
) -> AnalysisContext:
    config = config or PRConfig.from_env()
    return AnalysisContext(
        snapshot=snapshot,
        request=request,
        config=config,
        budget=budget or ReviewBudget(config.budget),
        offline=config.offline if offline is None else offline,
        artifact_dir=artifact_dir,
        registry=registry,
        llm=llm,
    )
