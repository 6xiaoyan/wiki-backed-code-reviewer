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
import re
from dataclasses import dataclass, field
from typing import Any

from code_checker.pr_review import agents, evidence, report, rules
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

#: 匹配 C/C++ include 指令，用于从固定版本树定位关联头文件。
_INCLUDE_RE = re.compile(r'#\s*include\s*([<"])([^>"]+)[>"]')


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

    def stop_incomplete(self, reason: str, stage: str = "prepare") -> str:
        """停止流水线但保留 incomplete 语义（不能降级成普通 skipped）。"""
        self.result.status = STATUS_INCOMPLETE
        self.result.status_reason = reason
        self.degrade(stage, "degraded", reason, "审查未完成，已有结论不完整")
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
        reason = "；".join(decision.reasons) or "没有适用的代码改动"
        if decision.status_override == "incomplete":
            # 有适用代码改动但全部未读取（例如唯一文件超过大小上限）
            return ctx.stop_incomplete(reason, "scope")
        return ctx.stop_skipped(reason, "scope")
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
    ctx.result.artifacts["rule_coverage"] = ctx.review.get("rule_coverage", [])
    ctx.result.artifacts["header_context_missing"] = ctx.review.get("header_missing", [])
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
    basis = rules.rule_clause(rule_id)
    return Finding(
        id=stable_finding_id(item.get("file", ""), 1, rule_id, 0),
        severity=str(item.get("severity") or "suggestion"),
        file=str(item.get("file") or ""),
        line=0,
        rule_id=rule_id,
        rule_title=str(meta.get("title") or rule_id),
        rule_quote="",
        rule_basis=basis,
        rule_source=rules.rule_source(rule_id),
        message=str(item.get("message") or ""),
        code_evidence=str(item.get("code") or ""),
        change_relation="added",
        suggestion=str(item.get("suggestion") or ""),
        source="git",
    )


def _run_agent_reviews(ctx: AnalysisContext) -> dict:
    by_domain: dict[str, list] = {}
    for cf in ctx.decision.included:
        dom = domain_of(cf.path, ctx.head_contents.get(cf.path, ""))
        by_domain.setdefault(dom, []).append(cf)

    out = {"raw": [], "agent_failed": False, "reasons": [],
           "degradation": [], "context_reads": [], "rule_coverage": [],
           "header_missing": [], "rule_texts": {}}

    # ── 每个领域注入本领域的可信规则正文（受可信预算限制）──
    corpora = {}
    for domain in sorted(by_domain):
        corpus = rules.build_domain_rules(
            domain,
            limit_bytes=ctx.config.budget.max_rule_context_bytes,
            max_page_bytes=ctx.config.budget.max_rule_page_bytes,
        )
        corpora[domain] = corpus
        out["rule_coverage"].append(corpus.to_dict())
        out["rule_texts"][domain] = dict(corpus.injected_text)
        if corpus.empty:
            out["agent_failed"] = True
            out["reasons"].append(
                f"{domain} 领域没有可注入的可信规则正文，未执行模型审查"
            )
            out["degradation"].append({
                "stage": f"rules/{domain}", "status": "failed",
                "reason": "没有可用的规则正文",
                "impact": f"{domain} 领域文件未经模型审查",
            })
        elif corpus.excluded:
            # 超限规则绝不静默丢弃：记录未注入原因，结果标为 incomplete
            out["agent_failed"] = True
            out["reasons"].append(
                f"{domain} 领域有 {len(corpus.excluded)} 条规则正文"
                f"因输入上限未注入，审查依据不完整"
            )
            out["degradation"].append({
                "stage": f"rules/{domain}", "status": "degraded",
                "reason": (
                    f"{len(corpus.included)} 条规则已注入，"
                    f"{len(corpus.excluded)} 条未注入（详见运行记录 rule_coverage）"
                ),
                "impact": "模型只能依据已注入规则审查，结果不完整",
            })

    reviewer = agents.DomainReviewer(
        ctx.llm, ctx.budget, ctx.registry or {}, corpora,
    )
    ctx_builder = ContextBuilder(ctx.snapshot, ctx.budget)
    for domain, domain_files in sorted(by_domain.items()):
        if corpora[domain].empty:
            continue  # 没有规则正文时不调用模型，已标记 incomplete
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

            # 关联头文件从固定 head_sha 的仓库树中查找（不仅是本次变更文件）
            headers, missing, header_error = _related_header_paths(cf, ctx)
            if header_error:
                out["agent_failed"] = True
                out["reasons"].append(header_error)
                out["degradation"].append({
                    "stage": "context", "status": "failed",
                    "reason": header_error,
                    "impact": f"{cf.path} 无法确定关联头文件",
                })
            for item in missing:
                path = item["path"]
                out["header_missing"].append({"path": path, "quoted": item["quoted"],
                                              "file": cf.path})
                if item["quoted"]:
                    message = f"{path}: 引用的项目头文件不在固定版本树中"
                    out["agent_failed"] = True
                    out["reasons"].append(message)
                    out["degradation"].append({
                        "stage": "context", "status": "failed",
                        "reason": message,
                        "impact": f"{cf.path} 缺少必要头文件上下文，审查依据不完整",
                    })
                else:
                    out["degradation"].append({
                        "stage": "context", "status": "degraded",
                        "reason": f"{path}: 引用的头文件不在固定版本树中",
                        "impact": f"{cf.path} 未读取该头文件上下文",
                    })
            for header in headers:
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
            # 服务端标记发现所属领域，覆盖模型可能伪造的同名字段；
            # 证据核验只接受该领域本轮实际注入的规则与正文。
            for item in raws:
                if not isinstance(item, dict):
                    continue
                tagged = dict(item)
                tagged.pop("_agent_domain", None)
                tagged["_agent_domain"] = domain
                out["raw"].append(tagged)
    out["context_reads"] = ctx_builder.reads_dict()
    return out


def _related_header_paths(cf, ctx: AnalysisContext) -> tuple[list[str], list[dict], str]:
    """从固定 head_sha 的仓库树查找被 include 的同名头文件。

    Returns:
        (可读取的头文件, 缺失的候选头文件, 错误信息)。
        候选基于 ``#include`` 指令，不依赖本次变更文件集合。
    """
    if not cf.path.endswith((".cpp", ".cc")):
        return [], [], ""
    import posixpath

    base_dir = posixpath.dirname(cf.path)
    name = posixpath.basename(cf.path).rsplit(".", 1)[0]
    expected = {
        posixpath.join(base_dir, name + ext)
        for ext in (".h", ".hpp", ".hxx")
    }
    text = ctx.head_contents.get(cf.path, "")
    includes: list[tuple[str, bool]] = []
    for match in _INCLUDE_RE.finditer(text or ""):
        raw_target = match.group(2).strip().replace("\\", "/")
        quoted = match.group(1) == '"'
        target = posixpath.normpath(posixpath.join(base_dir, raw_target))
        if target in expected:
            includes.append((target, quoted))

    try:
        tree = ctx.snapshot.list_tree(ctx.request.head_sha)
    except SnapshotError as exc:
        return [], [], f"读取 head={ctx.request.head_sha[:8]} 文件树失败: {exc}"

    headers: list[str] = []
    missing: list[dict] = []
    for target, quoted in includes:
        if target in tree:
            if target not in headers:
                headers.append(target)
        else:
            missing.append({"path": target, "quoted": quoted})
    return headers, missing, ""


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
        # 只允许该领域本轮实际注入的规则与正文；缺失时按空表失败关闭
        domain_rule_texts=ctx.review.get("rule_texts") or {},
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
    rule_coverage = ctx.result.artifacts.get("rule_coverage") or []
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
        "rules_injected": sum(int(r.get("rules_injected", 0)) for r in rule_coverage),
        "rules_not_injected": sum(
            int(r.get("rules_not_injected", 0)) for r in rule_coverage
        ),
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
