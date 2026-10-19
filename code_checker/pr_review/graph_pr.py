"""PR 审查 LangGraph。

    START → prepare → deterministic → agents → verify → merge → export → END

prepare 按策略跳过（草稿/无适用改动）或失败时直接进入 export，
保证即使失败也会导出可追查的结果。节点函数与顺序版本共用 ``stages.py``。

注意：PR 模式不接入 fix/review 循环、Wiki 写入、skill 自动积累与旧缓存，
因此这里没有这些节点。
"""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from code_checker.pr_review import stages
from code_checker.pr_review.budget import ReviewBudget
from code_checker.pr_review.config import PRConfig
from code_checker.pr_review.models import ReviewRequest, ReviewResult
from code_checker.pr_review.snapshot import Snapshot
from code_checker.pr_review.stages import AnalysisContext, build_context


class PRGraphState(TypedDict, total=False):
    ctx: Any
    stage_result: str


def _node(fn):
    def run(state: PRGraphState) -> dict:
        ctx: AnalysisContext = state["ctx"]
        status = fn(ctx)
        return {"ctx": ctx, "stage_result": status or "ok"}

    run.__name__ = fn.__name__
    return run


def _route(state: PRGraphState) -> str:
    return state.get("stage_result") or "ok"


def build_pr_graph():
    graph = StateGraph(PRGraphState)
    graph.add_node("prepare", _node(stages.stage_prepare))
    graph.add_node("deterministic", _node(stages.stage_deterministic))
    graph.add_node("agents", _node(stages.stage_agents))
    graph.add_node("verify", _node(stages.stage_verify))
    graph.add_node("merge", _node(stages.stage_merge))
    graph.add_node("export", _node(stages.stage_export))

    graph.add_edge(START, "prepare")
    graph.add_conditional_edges(
        "prepare",
        _route,
        {"ok": "deterministic", "skipped": "export", "failed": "export"},
    )
    graph.add_edge("deterministic", "agents")
    graph.add_conditional_edges(
        "agents",
        _route,
        {"ok": "verify", "skipped": "export", "failed": "export"},
    )
    graph.add_edge("verify", "merge")
    graph.add_edge("merge", "export")
    graph.add_edge("export", END)
    return graph.compile()


def run_analysis_graph(
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
    """通过 LangGraph 执行 PR 审查。"""
    ctx = build_context(
        snapshot, request, config=config, llm=llm, registry=registry,
        offline=offline, artifact_dir=artifact_dir, budget=budget,
    )
    app = build_pr_graph()
    final = app.invoke({"ctx": ctx, "stage_result": ""})
    return final["ctx"].result


__all__ = ["PRGraphState", "build_pr_graph", "run_analysis_graph"]
