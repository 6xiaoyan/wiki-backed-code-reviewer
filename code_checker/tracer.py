"""
PipelineTracer — 全流程可观测性追踪模块。

为每次流水线运行提供：
  - run_id 贯穿全流程，关联所有事件
  - Span 上下文管理器，自动记录每个节点的耗时和产出
  - 违规生命周期追踪（发现 → 修复 → 审查 → 解决）
  - 结构化 JSONL 事件日志 + 人类可读时间线摘要

设计原则：
  - 零外部依赖（仅 Python stdlib）
  - 线程安全（支持 LangGraph Send 并行扇出）
  - fire-and-forget（trace 写入不抛异常，不阻断主流程）
  - 与现有 wiki_access.log JSONL 模式一致

用法：
    from code_checker.tracer import PipelineTracer, set_current_tracer

    tracer = PipelineTracer(run_id, output_dir)
    set_current_tracer(tracer)

    with tracer.span("repo_scanner"):
        ...

    tracer.finish(state)
    print(tracer.timeline_summary())
"""

import json
import os
import time
import threading
import datetime
from typing import Optional
from contextlib import contextmanager


# ============================================================================
# 模块级 tracer 引用（全局单例，供所有节点访问）
# ============================================================================

_current_tracer: Optional["PipelineTracer"] = None
_tracer_lock = threading.Lock()


def set_current_tracer(tracer: Optional["PipelineTracer"]) -> None:
    """设置当前活跃的追踪器。main.py 在每次 run() 开始时调用。"""
    global _current_tracer
    with _tracer_lock:
        _current_tracer = tracer


def get_current_tracer() -> Optional["PipelineTracer"]:
    """获取当前活跃的追踪器。各节点通过此函数获取 tracer 引用。"""
    with _tracer_lock:
        return _current_tracer


# ============================================================================
# Span 上下文管理器
# ============================================================================


class SpanContext:
    """节点执行的追踪区间。

    作为上下文管理器使用，进入时写 span_start 事件，退出时写 span_end 事件。
    即使节点抛出异常，也能正确记录 end 事件（含错误信息）。

    属性:
        node_name:   节点名称（如 "repo_scanner"）
        start_time:  进入时的 perf_counter 值
        output:      节点返回的 dict（退出时由 wrapper 填充）
        error:       异常信息（如有）
        span_id:     唯一区间标识
    """

    __slots__ = ("node_name", "start_time", "output", "error", "span_id", "duration_ms")

    def __init__(self, node_name: str) -> None:
        self.node_name = node_name
        self.start_time = 0.0
        self.output: Optional[dict] = None
        self.error: Optional[str] = None
        self.span_id = ""
        self.duration_ms: float = 0.0


# ============================================================================
# PipelineTracer
# ============================================================================


class PipelineTracer:
    """流水线追踪器。每次 pipeline run 创建一个实例。

    线程安全：JSONL 写入用锁保护，内存中的 span 列表同理。
    """

    def __init__(self, run_id: str, output_dir: str) -> None:
        """初始化追踪器。

        Args:
            run_id:     本次运行的唯一标识（由 main.py 生成）
            output_dir: traces 输出目录
        """
        self.run_id = run_id
        self._start_time = time.perf_counter()
        self._output_dir = output_dir
        self._jsonl_path = os.path.join(output_dir, f"{run_id}.jsonl")
        # agent 级 ReAct 轨迹独立文件（归因数据源），不污染主时间线
        self._agent_jsonl_path = os.path.join(output_dir, f"{run_id}-agent.jsonl")

        # 线程安全
        self._write_lock = threading.Lock()
        self._span_lock = threading.Lock()

        # 累积数据（供 finish() 和时间线摘要使用）
        self._spans: list[SpanContext] = []
        self._violation_events: list[dict] = []   # violation_found 事件
        self._fix_events: list[dict] = []           # violation_fix 事件
        self._llm_events: list[dict] = []           # llm_call 事件
        self._current_node: str = ""                # 当前正在执行的节点名（供 _get_agent_name 回退）

        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)

        # 记录 run_start 事件
        self._write_event({
            "event": "run_start",
            "run_id": run_id,
            "timestamp": _now_iso(),
        })

    # ── 公开 API ────────────────────────────────────────────────

    @contextmanager
    def span(self, node_name: str):
        """节点执行的追踪区间（上下文管理器）。

        用法:
            with tracer.span("repo_scanner") as ctx:
                result = repo_scanner(state)
                ctx.output = result
        """
        ctx = SpanContext(node_name)
        ctx.span_id = f"{node_name}-{len(self._spans)+1:03d}"
        ctx.start_time = time.perf_counter()

        # 设置当前节点名（供 _get_agent_name 回退）
        prev_node = self._current_node
        self._current_node = node_name

        # 写 span_start
        self._write_event({
            "event": "span_start",
            "run_id": self.run_id,
            "timestamp": _now_iso(),
            "span_id": ctx.span_id,
            "node": node_name,
        })

        try:
            yield ctx
        except Exception as e:
            ctx.error = f"{type(e).__name__}: {e}"
            raise
        finally:
            # 无论如何都写 span_end
            ctx.duration_ms = round((time.perf_counter() - ctx.start_time) * 1000, 1)
            duration_ms = ctx.duration_ms
            end_event: dict = {
                "event": "span_end",
                "run_id": self.run_id,
                "timestamp": _now_iso(),
                "span_id": ctx.span_id,
                "node": node_name,
                "duration_ms": duration_ms,
            }
            if ctx.error:
                end_event["error"] = ctx.error
            if ctx.output is not None:
                end_event["output_summary"] = _summarize_output(ctx.output)
            self._write_event(end_event)

            # 保存 span 到内存（供时间线摘要）
            with self._span_lock:
                self._spans.append(ctx)

            # 恢复前一个节点名
            self._current_node = prev_node

    def record_violation(
        self, violation: dict, source_node: str, index: int,
    ) -> str:
        """记录一条违规被发现的事件。

        Args:
            violation:    违规 dict（含 file, line, rule, severity 等）
            source_node:  来源节点名（如 "deterministic_checker", "cpp_agent"）
            index:        违规在当前批次中的序号

        Returns:
            violation_id 字符串，调用方应将其写入 violation["violation_id"]
        """
        vid = self._make_violation_id(source_node, index)
        event = {
            "event": "violation_found",
            "run_id": self.run_id,
            "timestamp": _now_iso(),
            "violation_id": vid,
            "file": _basename(violation.get("file", "")),
            "line": violation.get("line", 0),
            "rule": violation.get("rule", ""),
            "severity": violation.get("severity", ""),
            "source_node": source_node,
            "source_kind": violation.get("source_kind", ""),
        }
        self._write_event(event)
        with self._span_lock:
            self._violation_events.append(event)
        return vid

    def record_fix(
        self, violation_id: str, fix_status: str,
        score: int = 0, iteration: int = 0,
        feedback: str = "", suggestion: str = "",
    ) -> None:
        """记录一条违规的修复/审查结果事件。

        Args:
            violation_id: 违规 ID（与 record_violation 返回的一致）
            fix_status:   修复状态（passed / failed / unresolved / infra）
            score:        审查评分（0-10）
            iteration:    当前 fix-review 迭代次数
            feedback:     审查意见（为什么给这个分数）
            suggestion:   修改建议（如未通过）
        """
        event = {
            "event": "violation_fix",
            "run_id": self.run_id,
            "timestamp": _now_iso(),
            "violation_id": violation_id,
            "fix_status": fix_status,
            "score": score,
            "iteration": iteration,
        }
        if feedback:
            event["feedback"] = feedback[:200]
        if suggestion:
            event["suggestion"] = suggestion[:200]
        self._write_event(event)
        with self._span_lock:
            self._fix_events.append(event)

    def record_llm_call(
        self, agent_name: str, model: str,
        duration_ms: float = 0.0, tokens: int = 0,
    ) -> None:
        """记录一次 LLM 调用。

        Args:
            agent_name:  调用 LLM 的 agent 名称
            model:       LLM 模型名
            duration_ms: 调用耗时（毫秒）
            tokens:      消耗的 token 数（如能获取）
        """
        event = {
            "event": "llm_call",
            "run_id": self.run_id,
            "timestamp": _now_iso(),
            "agent": agent_name,
            "model": model,
            "duration_ms": duration_ms,
        }
        if tokens > 0:
            event["tokens"] = tokens
        self._write_event(event)
        with self._span_lock:
            self._llm_events.append(event)

    def record_agent_trace(self, agent_name: str, messages: list) -> None:
        """落盘某个 agent 的 ReAct 轨迹（归因数据源），写独立 -agent.jsonl。

        不污染主时间线——归因只需要「它读了哪个文件、翻了哪个 wiki 页、
        报了/漏了什么」，这些是 agent 级推理链，与管道级事件分开存。

        Args:
            agent_name: 轨迹所属 agent（如 "cpp/file3"）。
            messages:   已序列化的消息列表（由 utils.serialize_messages 转换）。
                        本模块不 import langchain，维持零外部依赖。
        """
        event = {
            "event": "agent_trace",
            "run_id": self.run_id,
            "timestamp": _now_iso(),
            "agent": agent_name,
            "messages": messages,
        }
        try:
            line = json.dumps(event, ensure_ascii=False) + "\n"
            with self._write_lock:
                with open(self._agent_jsonl_path, "a", encoding="utf-8") as f:
                    f.write(line)
        except Exception:
            pass  # fire-and-forget

    def finish(self, state: dict) -> None:
        """流水线结束。写 run_end 事件，关闭 JSONL 文件。

        Args:
            state: 最终的 AgentState（用于提取汇总统计）
        """
        total_ms = round((time.perf_counter() - self._start_time) * 1000, 1)

        violations = state.get("merged_violations") or []
        fix_plans = state.get("fix_plans") or []

        passed = sum(1 for p in fix_plans if p is not None and p.get("fix_status") == "passed")
        failed = sum(1 for p in fix_plans if p is not None and p.get("fix_status") == "failed")
        unresolved = sum(1 for p in fix_plans if p is not None and p.get("fix_status") == "unresolved")
        infra = sum(1 for p in fix_plans if p is not None and p.get("fix_status") == "infra")
        iteration = state.get("fix_iteration", 0)

        self._write_event({
            "event": "run_end",
            "run_id": self.run_id,
            "timestamp": _now_iso(),
            "total_duration_ms": total_ms,
            "total_violations": len(violations),
            "total_fix_plans": len(fix_plans),
            "passed": passed,
            "failed": failed,
            "unresolved": unresolved,
            "infra": infra,
            "fix_iterations": iteration,
        })

        # 在内存中保存汇总数据供 timeline_summary 使用
        self._total_ms = total_ms
        self._final_state = state

    def timeline_summary(self) -> str:
        """生成人类可读的流水线时间线文本。"""
        total_ms = getattr(self, "_total_ms", 0.0)
        state = getattr(self, "_final_state", {})
        violations = state.get("merged_violations") or []
        fix_plans = state.get("fix_plans") or []

        lines: list[str] = [
            "",
            "=" * 60,
            "  流水线时间线",
            "=" * 60,
            f"  run_id: {self.run_id}",
            f"  总耗时: {_format_duration(total_ms)}",
            f"  事件日志: {self._jsonl_path}",
            "",
        ]

        # ── 节点耗时表 ──
        with self._span_lock:
            spans = list(self._spans)
        if spans:
            lines.append("  节点耗时:")
            for s in spans:
                dur_str = _format_duration(s.duration_ms) if s.duration_ms else "?"
                summary = ""
                if s.output:
                    summary = _describe_span_output(s.node_name, s.output)
                error_flag = " ❌" if s.error else ""
                lines.append(f"    {s.node_name:<24s} {dur_str:>8s}  {summary}{error_flag}")

        # ── 违规生命周期统计 ──
        lines.append("")
        lines.append("  违规生命周期:")
        with self._span_lock:
            found_count = len(self._violation_events)
        fmt_fixed = sum(
            1 for p in fix_plans
            if p is not None and p.get("fix_method") == "format_fixer"
        )
        passed = sum(1 for p in fix_plans if p is not None and p.get("fix_status") == "passed")
        failed = sum(1 for p in fix_plans if p is not None and p.get("fix_status") == "failed")
        unresolved = sum(1 for p in fix_plans if p is not None and p.get("fix_status") == "unresolved")

        parts = [f"发现 {found_count} 条"]
        if fmt_fixed:
            parts.append(f"{fmt_fixed} 条格式自动修复")
        remaining = len(fix_plans) - fmt_fixed
        if remaining > 0:
            parts.append(f"{remaining} 条进入 fix-review")
        lines.append(f"    {' → '.join(parts)}")

        if fix_plans:
            result_parts = []
            if passed:
                result_parts.append(f"{passed} 条通过")
            if failed:
                result_parts.append(f"{failed} 条未通过(达上限)")
            if unresolved:
                result_parts.append(f"{unresolved} 条需人工处理")
            lines.append(f"    → {' / '.join(result_parts)}")

        # ── LLM 调用统计 ──
        with self._span_lock:
            llm_events = list(self._llm_events)
        if llm_events:
            lines.append("")
            lines.append("  LLM 调用统计:")
            for e in llm_events:
                agent = e.get("agent", "?")
                model = e.get("model", "?")
                dur = _format_duration(e.get("duration_ms", 0))
                lines.append(f"    {agent}: {model} {dur}")

        lines.append("")
        lines.append("=" * 60)
        return "\n".join(lines)

    # ── 内部方法 ────────────────────────────────────────────────

    def _make_violation_id(self, source_node: str, index: int) -> str:
        """生成违规唯一标识。

        格式: {run_id 末 8 位}-{source_node 缩写}-{序号:04d}
        例: a1b2c3d4-detc-0003
        """
        short_run = self.run_id[-8:] if len(self.run_id) >= 8 else self.run_id
        # source_node 缩写映射
        abbrev_map = {
            "deterministic_checker": "detc",
            "cpp_agent": "cpp",
            "qt_agent": "qt",
            "git_agent": "git",
            "sqlite_agent": "sqlt",
            "report_merger": "merg",
        }
        abbrev = abbrev_map.get(source_node, source_node[:4])
        return f"{short_run}-{abbrev}-{index:04d}"

    def _write_event(self, event: dict) -> None:
        """线程安全地追加一条事件到 JSONL 文件。

        fire-and-forget: 任何写入异常都被静默捕获，绝不抛到主流程。
        """
        try:
            line = json.dumps(event, ensure_ascii=False) + "\n"
            with self._write_lock:
                with open(self._jsonl_path, "a", encoding="utf-8") as f:
                    f.write(line)
        except Exception:
            pass  # fire-and-forget


# ============================================================================
# 辅助函数
# ============================================================================


def _now_iso() -> str:
    """返回 ISO 8601 格式的当前时间字符串。"""
    return datetime.datetime.now().isoformat(timespec="seconds")


def _basename(path: str) -> str:
    """返回路径的文件名部分（跨平台）。"""
    return os.path.basename(path.replace("\\", "/"))


def _format_duration(ms: float) -> str:
    """格式化毫秒为人类可读的时长字符串。"""
    if ms <= 0:
        return "0ms"
    if ms < 1000:
        return f"{ms:.0f}ms"
    if ms < 60000:
        return f"{ms/1000:.1f}s"
    minutes = int(ms // 60000)
    seconds = (ms % 60000) / 1000
    return f"{minutes}m{seconds:.0f}s"


def _summarize_output(output: dict) -> dict:
    """提取节点返回 dict 的关键摘要字段。

    不记录完整内容（文件内容可能很大），只记录统计数字。
    """
    summary: dict = {}
    for key, value in output.items():
        if value is None:
            continue
        if isinstance(value, list):
            summary[key] = f"list[{len(value)}]"
        elif isinstance(value, dict):
            summary[key] = f"dict[{len(value)} keys]"
        elif isinstance(value, str):
            if len(value) > 100:
                summary[key] = f"str[{len(value)} chars]"
            else:
                summary[key] = value
        elif isinstance(value, bool):
            summary[key] = value
        elif isinstance(value, (int, float)):
            summary[key] = value
    return summary


def _describe_span_output(node_name: str, output: dict) -> str:
    """为 span 生成一行人类可读的产出描述。"""
    parts: list[str] = []

    # 文件扫描节点
    if "file_list" in output:
        fl = output.get("file_list")
        if isinstance(fl, list):
            parts.append(f"({len(fl)} files)")

    # 违规产出节点
    for field in ("deterministic_violations", "cpp_violations",
                  "qt_violations", "git_violations", "sqlite_violations",
                  "merged_violations"):
        val = output.get(field)
        if isinstance(val, list):
            parts.append(f"({len(val)} violations)")

    # 修复方案节点
    if "fix_plans" in output:
        fp = output.get("fix_plans")
        if isinstance(fp, list):
            passed = sum(1 for p in fp if p is not None and p.get("fix_status") == "passed")
            failed = sum(1 for p in fp if p is not None and p.get("fix_status") == "failed")
            parts.append(f"({len(fp)} plans, {passed} passed, {failed} failed)")

    # 覆盖率
    if "coverage_ledger" in output:
        cl = output.get("coverage_ledger")
        if isinstance(cl, dict) and "coverage_complete" in cl:
            parts.append(f"(coverage {'OK' if cl['coverage_complete'] else 'INCOMPLETE'})")

    return ", ".join(parts) if parts else ""
