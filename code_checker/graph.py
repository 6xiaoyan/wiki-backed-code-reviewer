"""
Agent 图构建 — 组装基于 Agent 的 LangGraph StateGraph。

拓扑结构（双层检查架构）:

    START
      │
  repo_scanner
      │
  deterministic_checker  ← 确定性正则检查（Python 强制执行，不经 LLM）
      │
      ├─ Send ─→ cpp_agent    (LLM 语义审查, Flash)
      ├─ Send ─→ qt_agent     (LLM 语义审查, Flash)
      ├─ Send ─→ git_agent    (Git 规范, Flash)
      └─ Send ─→ sqlite_agent (LLM 语义审查, Flash)
      │           (四路并行)
      ▼
  report_merger (Agent, Flash — must_keep 保护)
      │
      ▼
  format_fixer (确定性正则修复 — 格式类违规)
      │
      ▼
  fix_agent (Flash, PatchSet 跨文件修复) ◄──────────┐
      │                                                │
      ▼                                                │
  review_agent (Pro) ──(未通过 & iter<3)──────────────┘
      │
      │ (通过 / 达上限)
      ▼
  report_exporter (双文档输出: 含 unresolved/manual_review)
      │
     END

模型分层:
  Flash:              cpp_agent, qt_agent, sqlite_agent, review_agent, git_agent, report_merger, fix_agent
  确定性引擎:          deterministic_checker (零 token), format_fixer (零 token)

架构变更（vs 旧版）:
  1. deterministic_checker: 所有正则规则脱离 LLM，改由 Python 强制执行
  2. coverage_ledger: 确保每个文件必须执行的检查不会遗漏
  3. report_merger: must_keep=True 的违规不可被 LLM 删除
  4. fix_agent: 状态机 fix_status (非二值 status)，no-op 不再伪通过
  5. L4: 只压缩 ReAct 对话历史，不承载系统事实状态
"""

from langgraph.graph import StateGraph, START, END

from code_checker.state import AgentState
from code_checker.nodes import (
    repo_scanner,
    github_scanner,
    deterministic_checker,
    report_merger,
    report_exporter,
)
from code_checker.nodes.agent_cpp import cpp_agent
from code_checker.nodes.agent_qt import qt_agent
from code_checker.nodes.agent_git import git_agent
from code_checker.nodes.agent_sqlite import sqlite_agent
from code_checker.nodes.agent_fix import fix_agent
from code_checker.nodes.agent_review import review_agent
from code_checker.nodes.format_fixer import format_fixer
from code_checker.config import is_github_url, get_degradation_mode
from code_checker.routing import fanout_to_checkers_v2, route_after_critique_v2


def _traced(node_fn, node_name: str):
    """返回一个带追踪的节点包装函数。

    当 tracer 已初始化时，用 PipelineTracer.span() 包裹节点执行，
    自动记录 span_start / span_end 事件和耗时。
    tracer 未初始化时（测试环境等）降级为直接调用，不影响功能。
    """
    def wrapped(state: AgentState):
        from code_checker.tracer import get_current_tracer
        from code_checker.tools import set_agent_name
        set_agent_name(node_name)  # 设置线程 agent 名，供 report_violation 追溯
        tracer = get_current_tracer()
        if tracer:
            with tracer.span(node_name) as ctx:
                result = node_fn(state)
                ctx.output = result
                return result
        else:
            return node_fn(state)
    wrapped.__name__ = node_fn.__name__
    return wrapped


def _log_degradation(state: AgentState, stage: str, status: str,
                     reason: str, impact: str) -> None:
    """向 state 的 degradation_log 追加一条降级事件。"""
    log = list(state.get("degradation_log") or [])
    log.append({
        "stage": stage,
        "status": status,
        "reason": reason,
        "impact": impact,
    })
    state["degradation_log"] = log


def _degradable(node_fn, node_name: str, fallback_result: dict):
    """返回一个带降级保护的节点包装函数。

    在 _traced 之外再包裹一层 try/except：
    - offline 模式：跳过 LLM 调用，直接返回 fallback_result
    - 正常执行：异常时记录降级事件，返回 fallback_result
    - strict 模式：异常时重新抛出（不降级）

    降级事件写入 state["degradation_log"]，供 report_exporter 展示。

    重要：LangGraph 只提交节点 return dict 中的字段，不提交对 state 的
    就地修改。因此本包装器在返回前始终将 state["degradation_log"] 合并到
    return dict 中——无论节点函数内部是否已经修改了它。
    """
    traced_fn = _traced(node_fn, node_name)

    def wrapped(state: AgentState):
        # ── 记录运行前的日志长度，用于提取本节点增量事件 ──
        log_before = list(state.get("degradation_log") or [])

        # ── offline 模式：跳过 LLM 调用 ──
        if get_degradation_mode() == "offline":
            print(f"  [{node_name}] offline 模式，跳过")
            _log_degradation(
                state, node_name, "skipped",
                "DEGRADATION_MODE=offline，跳过 LLM 调用",
                "该阶段未执行，相关违规/修复/审查缺失",
            )
            log_after = state.get("degradation_log") or []
            new_events = log_after[len(log_before):]
            result = dict(fallback_result)
            result["degradation_log"] = new_events
            return result

        try:
            result = traced_fn(state)
            # 只返回本节点新增的降级事件（增量），不是全量日志。
            # degradation_log 使用 Annotated reducer 合并并行分支的产出。
            log_after = state.get("degradation_log") or []
            new_events = log_after[len(log_before):]
            if isinstance(result, dict):
                result["degradation_log"] = new_events
            return result
        except Exception as e:
            print(f"  [{node_name}] 降级: {e}")
            _log_degradation(
                state, node_name, "degraded",
                f"API 调用失败: {e}",
                "该阶段部分或全部功能不可用，详见报告",
            )
            if get_degradation_mode() == "strict":
                raise
            log_after = state.get("degradation_log") or []
            new_events = log_after[len(log_before):]
            result = dict(fallback_result)
            result["degradation_log"] = new_events
            return result

    wrapped.__name__ = node_fn.__name__
    return wrapped


def _route_entry(state: AgentState) -> str:
    """入口路由：GitHub URL → github_scanner，本地路径 → repo_scanner。"""
    repo_path = state.get("repo_path", "")
    if is_github_url(repo_path):
        print(f"[路由] 检测到 GitHub URL → github_scanner")
        return "github_scanner"
    print(f"[路由] 本地路径 → repo_scanner")
    return "repo_scanner"


def build_graph() -> StateGraph:
    """构建并返回编译后的 Agent 驱动 LangGraph 工作流。"""
    graph = StateGraph(AgentState)

    # ── 注册节点 ──
    # 确定性节点：纯本地，不降级（用 _traced 追踪但不捕获异常）
    graph.add_node("repo_scanner", _traced(repo_scanner, "repo_scanner"))
    graph.add_node("github_scanner", _traced(github_scanner, "github_scanner"))
    graph.add_node("deterministic_checker", _traced(deterministic_checker, "deterministic_checker"))
    graph.add_node("format_fixer", _traced(format_fixer, "format_fixer"))
    graph.add_node("report_exporter", _traced(report_exporter, "report_exporter"))

    # LLM 节点：可降级（用 _degradable 包裹，API 故障时返回空结果）
    graph.add_node("cpp_agent", _degradable(
        cpp_agent, "cpp_agent", {"cpp_violations": []},
    ))
    graph.add_node("qt_agent", _degradable(
        qt_agent, "qt_agent", {"qt_violations": []},
    ))
    graph.add_node("git_agent", _degradable(
        git_agent, "git_agent", {"git_violations": []},
    ))
    graph.add_node("sqlite_agent", _degradable(
        sqlite_agent, "sqlite_agent", {"sqlite_violations": []},
    ))
    graph.add_node("report_merger", _degradable(
        report_merger, "report_merger", {},
    ))
    graph.add_node("fix_agent", _degradable(
        fix_agent, "fix_agent", {},
    ))
    graph.add_node("review_agent", _degradable(
        review_agent, "review_agent", {},
    ))

    # ── 连接边 ──
    # 入口路由：根据 URL 类型选择扫描器
    graph.add_conditional_edges(
        START,
        _route_entry,
        path_map={
            "repo_scanner": "repo_scanner",
            "github_scanner": "github_scanner",
        },
    )

    # 两个扫描器都汇聚到 deterministic_checker（确定性正则，不经 LLM）
    graph.add_edge("repo_scanner", "deterministic_checker")
    graph.add_edge("github_scanner", "deterministic_checker")

    # deterministic_checker → 四路 LLM semantic agent 并行扇出
    graph.add_conditional_edges(
        "deterministic_checker",
        fanout_to_checkers_v2,
        path_map={
            "cpp_agent": "cpp_agent",
            "qt_agent": "qt_agent",
            "git_agent": "git_agent",
            "sqlite_agent": "sqlite_agent",
        },
    )

    # 四路 agent 汇聚到 report_merger
    graph.add_edge("cpp_agent", "report_merger")
    graph.add_edge("qt_agent", "report_merger")
    graph.add_edge("git_agent", "report_merger")
    graph.add_edge("sqlite_agent", "report_merger")

    # merge → format_fixer（格式拦截）→ fix → review → (loop or exit)
    graph.add_edge("report_merger", "format_fixer")
    graph.add_edge("format_fixer", "fix_agent")
    graph.add_edge("fix_agent", "review_agent")

    graph.add_conditional_edges(
        "review_agent",
        route_after_critique_v2,
        path_map={
            "fix_agent": "fix_agent",
            "report_exporter": "report_exporter",
        },
    )

    graph.add_edge("report_exporter", END)

    return graph.compile()


# ── 模块级单例 ──
app = build_graph()


def build_pr_review_graph():
    """构建 PR diff 审查图（第一阶段新增，独立于全仓审查图）。

    拓扑：
        START → prepare → deterministic → agents → verify → merge → export → END

    与全仓图共用确定性检查与领域规则，但不含 fix/review 循环、Wiki 写入
    与 skill 自动积累节点。实现见 ``code_checker.pr_review.graph_pr``。
    """
    from code_checker.pr_review.graph_pr import build_pr_graph

    return build_pr_graph()
