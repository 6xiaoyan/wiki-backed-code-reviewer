"""PR 审查流水线入口（顺序执行版本）。

真正的阶段实现在 ``stages.py``；LangGraph 版本在 ``graph_pr.py``，两者
调用同一组 stage 函数，因此行为一致。此处的顺序版本便于在没有 LangGraph
的环境中运行确定性测试。
"""

from __future__ import annotations

from typing import Callable

from code_checker.pr_review import stages
from code_checker.pr_review.budget import ReviewBudget
from code_checker.pr_review.config import PRConfig
from code_checker.pr_review.models import ReviewRequest, ReviewResult
from code_checker.pr_review.snapshot import Snapshot
from code_checker.pr_review.stages import (
    AnalysisContext,
    build_context,
    load_result,
    stage_agents,
    stage_deterministic,
    stage_export,
    stage_merge,
    stage_prepare,
    stage_verify,
    write_artifacts,
)

#: 阶段顺序与 PRD §7 一致。
STAGE_SEQUENCE: tuple[Callable[[AnalysisContext], str], ...] = (
    stage_prepare,
    stage_deterministic,
    stage_agents,
    stage_verify,
    stage_merge,
)


def run_analysis(
    snapshot: Snapshot,
    request: ReviewRequest,
    *,
    config: PRConfig | None = None,
    llm=None,
    registry: dict[str, dict] | None = None,
    offline: bool | None = None,
    artifact_dir: str | None = None,
    budget: ReviewBudget | None = None,
) -> ReviewResult:
    """顺序执行全部阶段并返回结果（不写 GitHub）。"""
    ctx = build_context(
        snapshot, request, config=config, llm=llm, registry=registry,
        offline=offline, artifact_dir=artifact_dir, budget=budget,
    )
    for stage in STAGE_SEQUENCE:
        status = stage(ctx)
        if status != "ok":
            break
    stage_export(ctx)
    return ctx.result


__all__ = [
    "STAGE_SEQUENCE",
    "AnalysisContext",
    "build_context",
    "load_result",
    "run_analysis",
    "write_artifacts",
]
