"""
context_compaction — LangGraph ReAct Agent 上下文压缩管线。

参考 learn-claude-code s08 的四层压缩策略，适配到 LangGraph 的
create_react_agent 框架中，通过 pre_model_hook 在每次 LLM 调用前执行。

管线（按执行顺序）：
  L3: tool_result_persist — 超大 ToolMessage 落盘，LLM 可 read_file 恢复
  L1: snip_compact        — 消息数超阈值时裁剪中间消息（边界保护）
  L2: micro_compact       — 旧 ToolMessage 替换为占位符，关键工具白名单保护
  L4: compact_history     — token 超阈值时 LLM 摘要压缩（领域特化 8 段模板）
  guard: critical_guard   — 估算字符数超硬限时激进裁剪，防 prompt_too_long

遥测系统：
  每次压缩操作的结构化决策记录写入 JSONL 日志，包含：
  - 压缩前后指标（消息数、估算字符数、ToolMessage 数）
  - 每一层的触发情况和效果
  - agent/chunk 标识，方便按维度分析

设计哲学："Cheap first, expensive last." — L1-L3 为 0 API 调用，L4 为付费 LLM 调用。
"""

import os
import json
import time
import threading
from datetime import datetime
from typing import Optional, Callable

from langchain_core.messages import (
    BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage,
    RemoveMessage,
)

# ============================================================================
# Per-agent ReadFileTracker 注册表
# ============================================================================

_tracker_registry: dict[str, 'ReadFileTracker'] = {}
"""agent_name → ReadFileTracker 的注册表。每个 agent 拥有独立 tracker。"""
_registry_lock = threading.Lock()


def register_tracker(agent_name: str, tracker: 'ReadFileTracker') -> None:
    """将 ReadFileTracker 注册到全局注册表（agent 初始化时调用）。"""
    with _registry_lock:
        _tracker_registry[agent_name] = tracker


def unregister_tracker(agent_name: str) -> None:
    """从注册表移除 tracker（agent 结束时调用）。"""
    with _registry_lock:
        _tracker_registry.pop(agent_name, None)


def get_tracker(agent_name: str) -> 'ReadFileTracker | None':
    """通过 agent_name 查找对应的 ReadFileTracker。

    支持前缀匹配：如 "cpp_agent/file1" 匹配 "cpp_agent"。
    """
    with _registry_lock:
        if agent_name in _tracker_registry:
            return _tracker_registry[agent_name]
        for name, tracker in _tracker_registry.items():
            if agent_name.startswith(name):
                return tracker
    return None


# ============================================================================
# L4CircuitBreaker 注册表 — 跨函数调用的 breaker 持久化
# ============================================================================

_breaker_registry: dict[str, 'L4CircuitBreaker'] = {}
"""agent_name → L4CircuitBreaker 的注册表。breaker 生命周期脱离 CompactionHookFactory，
跨 review_agent() 等循环调用存活。"""
_breaker_registry_lock = threading.Lock()


def register_breaker(agent_name: str, breaker: 'L4CircuitBreaker') -> None:
    """将 L4CircuitBreaker 注册到全局注册表（agent 初始化时调用）。"""
    with _breaker_registry_lock:
        _breaker_registry[agent_name] = breaker


def get_breaker(agent_name: str) -> 'L4CircuitBreaker | None':
    """通过 agent_name 查找对应的 L4CircuitBreaker。"""
    with _breaker_registry_lock:
        return _breaker_registry.get(agent_name)


# ============================================================================
# ReadFileTracker — 跟踪 agent 读取的文件，支持 post-compact 恢复
# ============================================================================

class _FileEntry:
    """单条文件读取记录。"""
    __slots__ = ('path', 'content', 'timestamp', 'access_count')

    def __init__(self, path: str, content: str, timestamp: float, access_count: int):
        self.path = path
        self.content = content
        self.timestamp = timestamp
        self.access_count = access_count


class ReadFileTracker:
    """每个 agent 独立的文件读取追踪器。

    记录 agent 通过 read_file 工具读取的文件内容和时间戳。
    L4 compact 后通过 get_recent() 恢复最近读取的文件。

    设计要点:
      - 线程安全：内部有锁，支持 ThreadPoolExecutor 多线程并发
      - LRU 淘汰：超过 max_files 时淘汰最旧的文件
      - 内容截断：单文件最多保留 MAX_CONTENT_CHARS 字符
      - 防御性注释：当前所有 subagent 的 task_msg 只含文件路径不含内容，
        subagent 必须调 read_file。若未来 task_msg 包含文件内容，
        此 tracker 将漏记录，需同步修改 task_msg 构建处和此处理逻辑。
    """

    MAX_CONTENT_CHARS = 10000       # 单文件最大存储字符数

    def __init__(self, max_files: int = 20):
        self._max_files = max_files
        self._files: dict[str, _FileEntry] = {}
        self._order: list[str] = []  # LRU 队列，尾部最新
        self._lock = threading.Lock()

    def record_read(self, path: str, content: str) -> None:
        """记录一次文件读取。已存在的文件会更新内容和时间戳并移到 LRU 尾部。

        注意：当前所有 subagent 的 task_msg 只含文件路径不含文件内容，
        subagent 必须调用 read_file 获取代码。若未来 task_msg 变为包含
        文件内容，此 tracker 将漏记录那些直接注入的文件——届时需同步修改。
        """
        with self._lock:
            truncated = content[:self.MAX_CONTENT_CHARS]
            if len(content) > self.MAX_CONTENT_CHARS:
                truncated += (
                    f"\n... [截断 {len(content) - self.MAX_CONTENT_CHARS} 字符]"
                )

            if path in self._files:
                entry = self._files[path]
                entry.content = truncated
                entry.timestamp = time.time()
                entry.access_count += 1
                self._order.remove(path)
                self._order.append(path)
            else:
                self._files[path] = _FileEntry(
                    path=path, content=truncated,
                    timestamp=time.time(), access_count=1,
                )
                self._order.append(path)
                while len(self._order) > self._max_files:
                    old = self._order.pop(0)
                    del self._files[old]

    def get_recent(
        self,
        n: int = 5,
        max_chars_per_file: int = 5000,
        total_budget_chars: int = 50000,
    ) -> list[tuple[str, str]]:
        """获取最近 N 个文件的内容，遵守预算约束。

        Args:
            n: 最多返回文件数
            max_chars_per_file: 单文件最多返回字符数
            total_budget_chars: 总字符预算（所有文件合计）

        Returns:
            [(文件路径, 文件内容), ...] 按最近使用排序（最新在前）
        """
        with self._lock:
            recent_paths = list(reversed(self._order))[:n]
            result: list[tuple[str, str]] = []
            used_chars = 0
            for path in recent_paths:
                entry = self._files.get(path)
                if entry is None:
                    continue
                content = entry.content[:max_chars_per_file]
                content_chars = len(content)
                if used_chars + content_chars > total_budget_chars:
                    remaining = total_budget_chars - used_chars
                    if remaining > 200:
                        content = content[:remaining] + "\n... [超出预算截断]"
                    else:
                        break
                result.append((path, content))
                used_chars += len(content)
            return result

    def clear(self) -> None:
        """清空所有记录（新 run 开始时调用）。"""
        with self._lock:
            self._files.clear()
            self._order.clear()


# ============================================================================
# L4CircuitBreaker — L4 摘要熔断器，防止连续负节省率浪费 API 调用
# ============================================================================

class L4CircuitBreaker:
    """L4 compact 熔断器（两态：closed → open）。

    连续 N 次 compact 后 token 反而增加超过阈值 → 熔断 → 后续 L4 全部跳过。
    同一 session 内不自动恢复。参考 rate_limiter.CircuitBreaker 但简化为两态。

    阈值设计：savings_pct < -10%（非 ≤ 0），容忍 _estimate_tokens()
    在 C++ 代码上 ~15% 的估算误差。
    """

    def __init__(self, failure_threshold: int = 3,
                 min_savings_pct: float = -0.10):
        self._threshold = failure_threshold
        self._min_savings_pct = min_savings_pct
        self._consecutive_failures = 0
        self._state = "closed"  # closed | open
        self._lock = threading.Lock()

    def record_result(self, pre_tokens: int, post_tokens: int) -> None:
        """记录一次 L4 compact 的结果。

        仅在 L4 实际触发（triggered=True）后调用。LLM 调用失败时
        compact_history 返回 triggered=False，不会进入此方法。

        负节省率超过阈值 → 累计失败；正节省 → 重置计数。
        """
        with self._lock:
            if self._state == "open":
                return
            if pre_tokens > 0:
                savings_pct = (1 - post_tokens / pre_tokens)
            else:
                savings_pct = 0.0
            if savings_pct < self._min_savings_pct:
                self._consecutive_failures += 1
                if self._consecutive_failures >= self._threshold:
                    self._state = "open"
                    print(
                        f"  [L4熔断器] 连续 {self._consecutive_failures} 次负节省率 "
                        f"（{savings_pct:.1%}），L4 已熔断，本 session 不再触发"
                    )
            else:
                self._consecutive_failures = 0

    @property
    def is_open(self) -> bool:
        return self._state == "open"

    @property
    def state(self) -> str:
        return self._state

    @property
    def failure_count(self) -> int:
        return self._consecutive_failures

    def reset(self) -> None:
        """手动重置熔断器（新 run 开始时调用）。"""
        with self._lock:
            self._state = "closed"
            self._consecutive_failures = 0


# ============================================================================
# 默认参数（可通过 create_compaction_hook 覆盖）
# ============================================================================

DEFAULTS = {
    "max_messages": 30,               # L1 snip_compact: 消息数阈值（CC 原版 50，我们更激进）
    "keep_head": 3,                   # L1 snip_compact: 保留头部消息数
    "keep_tail": 27,                  # L1 snip_compact: 保留尾部消息数
    "keep_recent_tool_results": 8,    # L2 micro_compact: 保留最近 N 条完整 ToolMessage（v2: 5→8）
    "persist_threshold": 3000,        # L3: 单个 ToolMessage 落盘阈值（字符数，P90=2834→拦截 top 8%）
    "max_chars_per_turn": 200000,     # L3: 单轮工具结果最大字符数（参考 CC max_bytes）
    "chars_per_token": 4,             # 字符/Token 估算比率（参考 CC s06）
    "critical_char_limit": 80000,     # guard: 硬限字符数，超过则激进裁剪
    # ── L4 LLM 摘要（默认启用，阈值 75% × 128K = 96K tokens）──
    "l4_token_threshold": 96000,      # L4: token 阈值，超此值触发 LLM 摘要（75% 上下文窗口）
    "l4_keep_recent": 15,            # L4: 摘要后保留的近期消息数
    "l4_tool_result_cap": 2000,      # L4: 送给摘要 LLM 的 ToolResult 截断字符数（Pi 模式）
    "l4_model": None,                 # L4: 摘要模型（必须由 agent 传入，否则跳过）
    # ── guard 硬限阈值提升（L4 启用后 guard 退居二线安全网）──
    "critical_char_limit_l4": 160000, # guard 硬限（当 L4 启用时提升，因摘要后上下文大幅缩减）
}

# ============================================================================
# 遥测系统
# ============================================================================

_TELEMETRY_DIR: Optional[str] = None


def _get_telemetry_path() -> str:
    """获取遥测日志文件路径，自动创建目录。"""
    global _TELEMETRY_DIR
    if _TELEMETRY_DIR is None:
        _TELEMETRY_DIR = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), ".cache", "compaction_telemetry"
        )
    os.makedirs(_TELEMETRY_DIR, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    return os.path.join(_TELEMETRY_DIR, f"compaction_{date_str}.jsonl")


def _record_telemetry(record: dict) -> None:
    """追加一条遥测记录到 JSONL 文件。写入失败不抛异常。"""
    try:
        path = _get_telemetry_path()
        line = json.dumps(record, ensure_ascii=False, default=str)
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass  # 遥测失败不阻塞主流程


# ============================================================================
# 辅助函数
# ============================================================================


def _estimate_chars(messages: list) -> int:
    """估算消息列表序列化后的字符数（参考 CC s08 的 estimate_size）。"""
    total = 0
    for m in messages:
        if hasattr(m, "content") and isinstance(m.content, str):
            total += len(m.content)
        elif hasattr(m, "content") and isinstance(m.content, list):
            total += len(json.dumps(m.content, default=str))
        if isinstance(m, AIMessage) and getattr(m, "tool_calls", None):
            total += len(json.dumps(m.tool_calls, default=str))
    return total


def _estimate_tokens(messages: list) -> int:
    """基于字符数估算 token 数。"""
    return max(1, _estimate_chars(messages) // DEFAULTS["chars_per_token"])


def _count_tool_results(messages: list) -> tuple[int, int]:
    """返回 (ToolMessage 总数, ToolMessage 总字符数)。"""
    count = 0
    total_chars = 0
    for m in messages:
        if isinstance(m, ToolMessage):
            count += 1
            if isinstance(m.content, str):
                total_chars += len(m.content)
            elif isinstance(m.content, list):
                total_chars += len(json.dumps(m.content, default=str))
    return count, total_chars


def _extract_user_goal(messages: list) -> str | None:
    """从消息历史中提取当前 subagent 的任务目标。

    策略：找到第一条 HumanMessage 并返回其内容（截断到 2000 字符）。
    所有 subagent（cpp/fix/review）的第一条 HumanMessage 都是
    chunk 级任务指令，行为一致，不需要按 agent 类型做差异化解析。

    Returns:
        第一条 HumanMessage 内容（截断），或 None（如果不存在）。
    """
    for m in messages:
        if isinstance(m, HumanMessage):
            content = m.content
            if isinstance(content, str):
                if not content:  # 跳过空字符串
                    continue
                if len(content) > 2000:
                    return content[:2000] + "\n... [任务描述已截断]"
                return content
            return str(content) if content else None
    return None


def _collect_metrics(messages: list) -> dict:
    """收集压缩前的消息指标。"""
    tool_count, tool_chars = _count_tool_results(messages)
    return {
        "message_count": len(messages),
        "estimated_chars": _estimate_chars(messages),
        "estimated_tokens": _estimate_tokens(messages),
        "tool_result_count": tool_count,
        "tool_result_chars": tool_chars,
    }


def _validate_no_orphans(messages: list) -> list:
    """兜底校验：确保消息历史中不存在孤立的 tool_call 或 ToolMessage。

    双向检查：
      1. AIMessage(tool_calls) 缺少对应的 ToolMessage → 替换为占位 HumanMessage
      2. ToolMessage 缺少对应的 AIMessage(tool_calls) → 替换为占位 HumanMessage

    ⚠️ 绝不原地修改消息对象（避免污染状态中的原始消息），
       需要修改时创建新对象。

    Returns:
        修复后的消息列表（全新对象，不修改原消息）
    """
    # 收集所有存在的 tool_call_id → ToolMessage 位置
    tool_result_ids: dict[str, int] = {}
    for i, m in enumerate(messages):
        if isinstance(m, ToolMessage):
            tool_result_ids[m.tool_call_id] = i

    # 收集所有 AIMessage(tool_calls) 声称的 tool_call_id
    tool_call_ids: dict[str, int] = {}  # tool_call_id → AIMessage 位置
    for i, m in enumerate(messages):
        if isinstance(m, AIMessage) and getattr(m, "tool_calls", None):
            for tc in m.tool_calls:
                if tc.get("id"):
                    tool_call_ids[tc["id"]] = i

    # ── 正向：AIMessage 的 tool_call 是否都有 ToolMessage ──
    # ── 反向：ToolMessage 是否都有对应的 AIMessage ──
    orphan_positions: set[int] = set()

    for i, m in enumerate(messages):
        if isinstance(m, AIMessage) and getattr(m, "tool_calls", None):
            tool_calls = m.tool_calls
            orphan_ids = [tc["id"] for tc in tool_calls if tc["id"] not in tool_result_ids]

            if orphan_ids:
                if len(orphan_ids) == len(tool_calls):
                    # 全部孤儿：整个 AIMessage 替换为占位消息
                    orphan_positions.add(i)
                else:
                    # 部分孤儿：创建新 AIMessage（只含有效 tool_calls）
                    # 不修改原消息对象！
                    orphan_positions.add(i)  # 标记需要替换

        elif isinstance(m, ToolMessage):
            tc_id = m.tool_call_id
            if tc_id not in tool_call_ids:
                # 孤立的 ToolMessage：没有对应的 AIMessage(tool_calls)
                orphan_positions.add(i)

    if not orphan_positions:
        return list(messages)  # 无孤儿，返回副本

    # ── 重建消息列表 ──
    fixed = []
    for i, m in enumerate(messages):
        if i in orphan_positions:
            if isinstance(m, AIMessage) and getattr(m, "tool_calls", None):
                tool_calls = m.tool_calls
                valid_calls = [tc for tc in tool_calls if tc["id"] in tool_result_ids]
                if valid_calls:
                    # 部分孤儿：创建新 AIMessage，只保留有效的 tool_calls
                    fixed.append(AIMessage(
                        content=m.content,
                        tool_calls=valid_calls,
                    ))
                else:
                    # 全部孤儿：替换为占位消息
                    fixed.append(HumanMessage(
                        content=f"[校验修复] 省略了 {len(tool_calls)} 个工具调用（缺少结果）。"
                    ))
            elif isinstance(m, ToolMessage):
                # 孤立的 ToolMessage：替换为占位消息
                fixed.append(HumanMessage(
                    content=f"[校验修复] 省略了孤立的工具结果（{getattr(m, 'name', 'unknown')}）。"
                ))
            else:
                # 不应到达这里
                fixed.append(HumanMessage(content="[校验修复] 省略了异常消息。"))
        else:
            fixed.append(m)

    return fixed


# ============================================================================
# L3: Tool Result 持久化（参考 CC s08 tool_result_budget + persist_large_output）
# ============================================================================

_PERSIST_DIR: Optional[str] = None


def _get_persist_dir() -> str:
    """获取工具结果持久化目录，自动创建。"""
    global _PERSIST_DIR
    if _PERSIST_DIR is None:
        _PERSIST_DIR = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            ".cache", "tool_results",
        )
    os.makedirs(_PERSIST_DIR, exist_ok=True)
    return _PERSIST_DIR


def _persist_large_output(tool_call_id: str, content: str) -> str:
    """将超大工具结果写入磁盘，返回 <persisted-output> 标记。

    CC 原版策略：完整内容落盘，上下文只保留路径 + 前 2000 字符预览。
    LLM 需要完整结果时通过 read_file 读取磁盘文件。
    """
    persist_dir = _get_persist_dir()
    path = os.path.join(persist_dir, f"{tool_call_id}.json")
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    preview = content[:2000]
    return (
        f"<persisted-output>\n"
        f"Full output: {path}\n"
        f"Preview ({len(content)} chars total):\n"
        f"{preview}\n"
        f"</persisted-output>"
    )


def tool_result_persist(
    messages: list,
    persist_threshold: int = None,
    critical_tool_names: set = None,
) -> tuple[list, dict]:
    """超大 ToolMessage 落盘持久化，替换为路径 + 预览标记。

    CC 原版 tool_result_budget 只处理最后一条 user 消息（Anthropic API
    将多个 tool_result 打包在一条消息中）。我们适配到 LangGraph v2 的
    独立 ToolMessage 格式：扫描每一条 ToolMessage，超阈值即落盘。

    Returns:
        (modified_messages, action_record)
    """
    persist_threshold = persist_threshold or DEFAULTS["persist_threshold"]
    critical_tool_names = critical_tool_names or set()

    action = {"triggered": False, "results_persisted": 0, "chars_saved": 0}

    modified = []
    for m in messages:
        if isinstance(m, ToolMessage) and isinstance(m.content, str):
            tool_name = getattr(m, "name", None)
            if tool_name in critical_tool_names:
                modified.append(m)
                continue
            if len(m.content) > persist_threshold:
                saved = len(m.content) - 2000  # 只保留 2000 字符预览
                persisted = _persist_large_output(m.tool_call_id, m.content)
                modified.append(ToolMessage(
                    content=persisted,
                    tool_call_id=m.tool_call_id,
                    name=getattr(m, "name", None),
                ))
                action["triggered"] = True
                action["results_persisted"] += 1
                action["chars_saved"] += saved
            else:
                modified.append(m)
        elif isinstance(m, ToolMessage) and isinstance(m.content, list):
            # 结构化内容先序列化再判断
            content_str = json.dumps(m.content, default=str)
            tool_name = getattr(m, "name", None)
            if tool_name in critical_tool_names:
                modified.append(m)
                continue
            if len(content_str) > persist_threshold:
                saved = len(content_str) - 2000
                persisted = _persist_large_output(m.tool_call_id, content_str)
                modified.append(ToolMessage(
                    content=persisted,
                    tool_call_id=m.tool_call_id,
                    name=getattr(m, "name", None),
                ))
                action["triggered"] = True
                action["results_persisted"] += 1
                action["chars_saved"] += saved
            else:
                modified.append(m)
        else:
            modified.append(m)

    return modified, action


# ============================================================================
# L1: Snip Compact（消息数裁剪）
# ============================================================================


def _has_tool_calls(msg) -> bool:
    """消息是否包含 tool_calls。"""
    return isinstance(msg, AIMessage) and bool(getattr(msg, "tool_calls", None))


def _is_tool_result(msg) -> bool:
    """消息是否为 ToolMessage。"""
    return isinstance(msg, ToolMessage)


def _get_safe_boundaries(messages: list) -> list[int]:
    """找出消息列表中所有安全的切割位置。

    安全切割点 = 可以放在 messages[i-1] 和 messages[i] 之间的位置。
    不安全 = 在 AIMessage(tool_calls) 和其 ToolMessage 之间，
    或在同一个 AIMessage 的多个 ToolMessage 之间。

    Returns:
        安全切割索引列表（i 表示在 messages[i] 之前切割，0 和 len(messages) 总是安全）
    """
    boundaries = [0]  # 开头总是安全
    for i in range(1, len(messages) + 1):
        if i == len(messages):
            boundaries.append(i)  # 末尾总是安全
        else:
            prev = messages[i - 1]
            curr = messages[i]
            # 不安全：prev 是 AIMessage(tool_calls)，curr 是其 ToolMessage
            if _has_tool_calls(prev) and _is_tool_result(curr):
                continue
            # 不安全：两个连续的 ToolMessage（属于同一个 AIMessage）
            if _is_tool_result(prev) and _is_tool_result(curr):
                continue
            boundaries.append(i)
    return boundaries


def _nearest_boundary(boundaries: list[int], target: int, direction: str = "down") -> int:
    """找到最接近 target 的安全边界。

    Args:
        boundaries: 安全边界列表（升序）
        target: 目标位置
        direction: "down" = 找 <= target 的最近边界, "up" = 找 >= target 的最近边界
    """
    if direction == "down":
        best = 0
        for b in boundaries:
            if b <= target:
                best = b
            else:
                break
        return best
    else:
        for b in boundaries:
            if b >= target:
                return b
        return boundaries[-1]  # 末尾


def _find_aimessage_for_tool(messages: list, tool_pos: int) -> int:
    """给定 ToolMessage 的位置，找到调用它的 AIMessage 的位置。

    从 tool_pos 向前扫描，找到包含匹配 tool_call_id 的 AIMessage。
    如果找不到（理论上不应该），返回 tool_pos。
    """
    tool_msg = messages[tool_pos]
    if not isinstance(tool_msg, ToolMessage):
        return tool_pos
    tc_id = tool_msg.tool_call_id
    for i in range(tool_pos - 1, -1, -1):
        m = messages[i]
        if isinstance(m, AIMessage) and getattr(m, "tool_calls", None):
            for tc in m.tool_calls:
                if tc.get("id") == tc_id:
                    return i
    return tool_pos


def _expand_to_include_block(messages: list, start: int, end: int) -> tuple[int, int]:
    """将区间 [start, end) 扩展到包含完整的 AIMessage+ToolMessages 原子块。

    确保不会在 AIMessage(tool_calls) 和它的 ToolMessage 之间切割，
    也不会在同一个 AIMessage 的多个 ToolMessage 之间切割。
    """
    # 向前扩展：如果 start 位置是 ToolMessage，找到它的 AIMessage
    if start < len(messages) and isinstance(messages[start], ToolMessage):
        aimsg_pos = _find_aimessage_for_tool(messages, start)
        if aimsg_pos < start:
            start = aimsg_pos

    # 向后扩展：如果 end-1 位置是 AIMessage(tool_calls)，找到它所有 ToolMessage
    if end > 0 and isinstance(messages[end - 1], AIMessage) and getattr(messages[end - 1], "tool_calls", None):
        aim_msg = messages[end - 1]
        for tc in aim_msg.tool_calls:
            tc_id = tc.get("id")
            # 找到对应的 ToolMessage
            for j in range(end, len(messages)):
                if isinstance(messages[j], ToolMessage) and messages[j].tool_call_id == tc_id:
                    end = j + 1
                else:
                    break

    return start, end


def snip_compact(
    messages: list,
    max_messages: int = None,
    keep_head: int = None,
    keep_tail: int = None,
    critical_tool_names: set = None,
) -> tuple[list, dict]:
    """消息数超过阈值时，裁剪中间消息。

    保留头部约 keep_head 条 + 尾部约 keep_tail 条，中间替换为占位消息。
    边界保护：通过安全切割点分析，绝不拆散 tool_use/tool_result 配对。
    关键工具保护：critical_tool_names 中的工具结果不会被裁剪。
    实际保留数量可能因边界对齐而有小幅偏差。

    Returns:
        (modified_messages, action_record)
    """
    max_messages = max_messages or DEFAULTS["max_messages"]
    keep_head = keep_head or DEFAULTS["keep_head"]
    keep_tail = keep_tail or DEFAULTS["keep_tail"]
    critical_tool_names = critical_tool_names or set()

    action = {
        "triggered": False,
        "messages_snipped": 0,
        "head_kept": keep_head,
        "tail_kept": keep_tail,
    }

    total = len(messages)
    if total <= max_messages:
        return messages, action

    # ── 计算安全边界 ──
    boundaries = _get_safe_boundaries(messages)
    desired_head_end = keep_head
    desired_tail_start = total - keep_tail

    head_end = _nearest_boundary(boundaries, desired_head_end, "down")
    tail_start = _nearest_boundary(boundaries, desired_tail_start, "up")

    # 确保 head 和 tail 不重叠
    if tail_start <= head_end:
        mid = (head_end + tail_start) // 2
        head_end = _nearest_boundary(boundaries, mid, "down")
        tail_start = _nearest_boundary(boundaries, mid + 1, "up")
        if tail_start <= head_end:
            return messages, action

    # ── 用户目标保护：确保第一条 HumanMessage 不被裁剪 ──
    # 所有 subagent（cpp/fix/review）的第一条 HumanMessage 都是 chunk 级
    # 任务指令（"审查单个 C++ 文件（1/5）：path"），丢失后 agent 不知自己要做什么。
    # 在 _expand_to_include_block 内部保证 head_end 至少覆盖第一条 HumanMessage，
    # 而非事后补救——事后已无法找回被裁掉的消息。
    first_hm_idx = None
    for i in range(total):
        if isinstance(messages[i], HumanMessage):
            first_hm_idx = i
            break
    if first_hm_idx is not None and first_hm_idx >= head_end:
        # 第一条 HumanMessage 在裁剪区内或被裁剪边界切掉
        # 扩展 head_end 到包含它（+1 因为 head_end 是 exclusive bound）
        head_end = _nearest_boundary(
            boundaries, max(head_end, first_hm_idx + 1), "up"
        )
        # 重新计算 tail_start，确保不重叠
        if tail_start <= head_end:
            tail_start = _nearest_boundary(boundaries, head_end + 1, "up")
            if tail_start <= head_end:
                return messages, action

    # ── 关键工具保护：扫描裁剪区，确保关键 ToolMessage 不被裁掉 ──
    if critical_tool_names:
        snipped_region = messages[head_end:tail_start]
        critical_positions = []
        for i, m in enumerate(snipped_region):
            if isinstance(m, ToolMessage) and getattr(m, "name", None) in critical_tool_names:
                critical_positions.append(head_end + i)

        if critical_positions:
            # 对于每个关键 ToolMessage，找到它的 AIMessage，
            # 然后扩展 head 使其包含整个原子块
            for pos in critical_positions:
                aim_pos = _find_aimessage_for_tool(messages, pos)
                head_end = max(head_end, pos + 1)  # 至少包含到该 ToolMessage 之后
                # 也确保 AIMessage 被包含
                if aim_pos < head_end:
                    head_end = max(head_end, aim_pos)

            # 重新计算 tail_start，确保不重叠
            tail_start = _nearest_boundary(boundaries, max(tail_start, head_end + 1), "up")
            if tail_start <= head_end:
                return messages, action  # 无法安全裁剪，放弃

    snipped_count = tail_start - head_end
    snipped = messages[head_end:tail_start]

    # 生成占位消息
    snippet = (
        f"[上下文裁剪] 中间 {snipped_count} 条消息已省略。\n"
        f"包含 {sum(1 for m in snipped if isinstance(m, ToolMessage))} 个工具结果。\n"
        f"如需之前的文件内容或规范文本，请重新调用相关工具获取。"
    )
    placeholder = HumanMessage(content=snippet)

    result = messages[:head_end] + [placeholder] + messages[tail_start:]

    action["triggered"] = True
    action["messages_snipped"] = snipped_count
    action["head_kept"] = head_end
    action["tail_kept"] = total - tail_start

    return result, action


# ============================================================================
# L2: Micro Compact（ToolMessage 占位符化）
# ============================================================================


def micro_compact(
    messages: list, keep_recent: int = None,
    critical_tool_names: set = None,
) -> tuple[list, dict]:
    """将旧的 ToolMessage 内容替换为占位符，保留最近 N 条完整内容。

    这是成本最低的压缩：0 API 调用，仅操作消息内容。
    CC 原版对所有 tool_result 做统一压缩；如果后续需要文件内容，LLM 会重新调用工具。
    critical_tool_names 中的工具结果永不压缩。

    Returns:
        (modified_messages, action_record)
    """
    keep_recent = keep_recent or DEFAULTS["keep_recent_tool_results"]
    critical_tool_names = critical_tool_names or set()

    action = {
        "triggered": False,
        "results_compacted": 0,
        "results_kept": keep_recent,
    }

    # 找到所有 ToolMessage 的位置
    tool_indices = [
        i for i, m in enumerate(messages) if isinstance(m, ToolMessage)
    ]

    if len(tool_indices) <= keep_recent:
        return messages, action

    # 需要压缩的 ToolMessage 索引（除了最近 keep_recent 条）
    to_compact = set(tool_indices[:-keep_recent])

    modified = []
    for i, m in enumerate(messages):
        if i in to_compact and isinstance(m, ToolMessage):
            tool_name = getattr(m, "name", None)
            if tool_name in critical_tool_names:
                modified.append(m)  # 关键工具结果不压缩
                continue
            content = m.content
            content_len = len(content) if isinstance(content, str) else len(
                json.dumps(content, default=str)
            )

            if isinstance(content, str) and content_len > 120:
                tool_name = getattr(m, "name", "unknown")
                placeholder = (
                    f"[已压缩] {tool_name} 返回 {content_len} 字符结果已省略。"
                    f"如需使用，请重新调用该工具。"
                )
                modified.append(ToolMessage(
                    content=placeholder,
                    tool_call_id=m.tool_call_id,
                    name=getattr(m, "name", None),
                ))
                action["triggered"] = True
                action["results_compacted"] += 1
            else:
                modified.append(m)
        else:
            modified.append(m)

    return modified, action


# ============================================================================
# Guard: 硬限保护（参考 CC reactive_compact，适配为 pre_model_hook 预检）
# ============================================================================


def critical_guard(
    messages: list,
    critical_char_limit: int = None,
) -> tuple[list, dict]:
    """估算字符数超过硬限时激进裁剪，防止 API 返回 prompt_too_long。

    CC 的 reactive_compact 在 API 报错后触发，保留尾部 5 条消息。
    我们适配为 proactive：在 pre_model_hook 中预估，超过硬限则
    保留 SystemMessage + 尾部消息，中间替换为诚实的占位符。

    仅在极端情况下触发（例如修复前的 report_merger 死循环），
    正常 agent 运行不应到达此阈值。

    Returns:
        (modified_messages, action_record)
    """
    critical_char_limit = critical_char_limit or DEFAULTS["critical_char_limit"]

    action = {"triggered": False, "messages_cut": 0}

    if _estimate_chars(messages) <= critical_char_limit:
        return messages, action

    # 分离 SystemMessage 和正文
    system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
    body_msgs = [m for m in messages if not isinstance(m, SystemMessage)]

    keep_tail = min(20, len(body_msgs))
    head_msgs = body_msgs[:DEFAULTS["keep_head"]]
    tail_msgs = body_msgs[-keep_tail:] if keep_tail > 0 else []

    cut_count = len(body_msgs) - len(head_msgs) - len(tail_msgs)
    if cut_count <= 0:
        return messages, action

    placeholder = HumanMessage(content=(
        f"[紧急裁剪] 上下文过大（{_estimate_chars(messages)} 字符），"
        f"中间 {cut_count} 条消息已省略。"
        f"如需之前的文件内容或规范文本，请重新调用相关工具获取。"
    ))

    result = system_msgs + head_msgs + [placeholder] + tail_msgs
    result = _validate_no_orphans(result)

    action["triggered"] = True
    action["messages_cut"] = cut_count

    return result, action


# ============================================================================
# L4: LLM 摘要压缩（领域特化，参考 CC 9段 FULL + Pi Agent 领域模板）
# ============================================================================

# ── L4 domain-specific summary prompts ──
_COMPACTION_SUMMARY_SYSTEM = """\
You are a conversation summarizer for a Code Compliance Reviewer agent system.
Your task is to create a structured summary of the agent's ReAct conversation
so that it can maintain dialogue continuity in a future context window.

CRITICAL — Your summary is for CONVERSATION CONTINUITY ONLY. It is NOT the
authoritative source of system facts. The following are stored externally in
ledgers/state and MUST be reloaded from tools, never assumed from your summary:

  - Coverage completeness (stored in coverage_ledger, reload via get_pending_violations)
  - Deterministic violations (must_keep=True, stored in merged_violations)
  - File lists and which files exist (reload via list_files)
  - Fix/review status (reload via get_pending_fixes / get_violation_detail)
  - Rule texts (reload via get_rules_text)

Your summary should cover:
  - What the agent was doing before the summary
  - Which conversation patterns and decisions emerged
  - What needs to happen next (at the task level, not fact level)

DO NOT:
  - List specific violations as fact (they may be stale)
  - Decide which files/checks are completed (coverage ledger owns this)
  - State "N violations found" as a final count (reload from state)
  - Include any information that would prevent the agent from re-checking

Output format:
1. First, wrap your analysis of each message in <analysis>...</analysis> tags.
2. Then, output the structured summary in <summary>...</summary> tags."""

_COMPACTION_SUMMARY_USER = """\
Below is the conversation history of a Code Compliance Reviewer agent.
Create a structured summary for conversation continuity only.

<conversation>
{conversation_text}
</conversation>

## Required Summary Sections

### 1. Current Phase & Goal
- Which pipeline phase: [checking / merging / format-fixing / fixing / reviewing]
- Target project and what standards are being checked (C++/Qt/Git/SQLite)

### 2. Conversation Narrative
- What has happened so far in the dialogue (narrative, not a fact ledger)
- Which patterns of interaction emerged
- Which files were discussed (but ALWAYS re-read them, don't trust this list)
- Which approaches were tried and why they worked or didn't

### 3. Key Decisions & Rationale
- Important choices made and their rationale
- Approaches tried that did not work

### 4. User Constraints & Preferences
- ALL explicit user requirements, style preferences, or constraints

### 5. Current State
- Precisely what was being worked on immediately before this summary
- Which specific task was in progress (NOT which violations — reload those from tools)

### 6. Next Steps
- What to do next, at the task level
- Priority order if multiple steps remain

## IMPORTANT — What NOT to include
DO NOT list violations as "facts" — these are stored in the external Violation Ledger
and must be reloaded via get_pending_violations/get_violation_detail.
DO NOT decide coverage is complete — Coverage Ledger owns this.
DO NOT mark fixes as done — fix_status is in the state, reload via get_pending_fixes.

The summary only helps conversation flow. For authoritative data, always reload from tools.

Wrap your summary in <summary>...</summary> tags."""


def compact_history(
    messages: list, model=None,
    keep_recent: int = 15,
    tool_result_cap: int = 2000,
) -> tuple[list, dict]:
    """使用 LLM 将对话历史摘要压缩（L4 层）。

    参考 Claude Code 的 9 段 FULL prompt + Pi Agent 的领域模板，
    适配为 Code Compliance Reviewer 的 8 段结构。

    流程（参考 CC SDK + Pi Agent）：
      1. 序列化对话历史，ToolResult 截断到 tool_result_cap 字符（Pi 模式）
      2. LLM 生成 <analysis> + <summary> 结构化摘要（CC 模式）
      3. 摘要替换历史，保留 SystemMessage + summary + 最后 keep_recent 条消息

    Args:
        messages: 当前消息列表
        model: LLM 客户端（必须传入，否则跳过）
        keep_recent: 摘要后保留的近期消息数（默认 15，参考 Pi 的 20K tokens 逻辑）
        tool_result_cap: 送给摘要 LLM 的 ToolResult 截断字符数（Pi 模式 = 2000）

    Returns:
        (modified_messages, action_record)
    """
    action = {"triggered": False, "summary_tokens": 0, "pre_tokens": 0}

    if model is None:
        return messages, action

    # ── 分离 SystemMessage 和正文 ──
    system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
    body_msgs = [m for m in messages if not isinstance(m, SystemMessage)]

    if len(body_msgs) < 10:
        return messages, action  # 太少不值得压缩

    # ── 序列化对话（Pi 模式：ToolResult 截断到 tool_result_cap 字符）──
    body_text = ""
    for m in body_msgs:
        if isinstance(m, HumanMessage):
            body_text += f"[USER] {m.content}\n"
        elif isinstance(m, AIMessage):
            if getattr(m, "tool_calls", None):
                tools = [tc.get("name", "?") for tc in m.tool_calls]
                body_text += f"[ASSISTANT] 调用工具: {', '.join(tools)}\n"
            if m.content:
                body_text += f"[ASSISTANT] {str(m.content)[:500]}\n"
        elif isinstance(m, ToolMessage):
            tool_name = getattr(m, "name", "unknown")
            if isinstance(m.content, str):
                if len(m.content) > tool_result_cap:
                    body_text += (
                        f"[TOOL_RESULT] {tool_name}: "
                        f"{m.content[:tool_result_cap]}... "
                        f"[截断 {len(m.content) - tool_result_cap} 字符]\n"
                    )
                else:
                    body_text += f"[TOOL_RESULT] {tool_name}: {m.content}\n"
            else:
                content_str = json.dumps(m.content, default=str)
                if len(content_str) > tool_result_cap:
                    body_text += (
                        f"[TOOL_RESULT] {tool_name}: "
                        f"{content_str[:tool_result_cap]}... "
                        f"[截断 {len(content_str) - tool_result_cap} 字符]\n"
                    )
                else:
                    body_text += f"[TOOL_RESULT] {tool_name}: {content_str}\n"

    # 只取最后 80000 字符（防止摘要 prompt 本身过大）
    body_text = body_text[-80000:]

    action["pre_tokens"] = _estimate_tokens(messages)

    # ── LLM 摘要 ──
    try:
        summary_response = model.invoke([
            SystemMessage(content=_COMPACTION_SUMMARY_SYSTEM),
            HumanMessage(content=_COMPACTION_SUMMARY_USER.format(
                conversation_text=body_text
            )),
        ])
        summary = summary_response.content
        action["triggered"] = True
        action["summary_tokens"] = _estimate_tokens([HumanMessage(content=summary)])
    except Exception:
        return messages, action  # 摘要失败，退化为不压缩

    # ── 构建新的消息列表（CC 模式：SystemMessage + 摘要 + 近期消息）──
    summary_msg = HumanMessage(content=(
        f"[对话摘要] 以下为此前对话的压缩摘要（仅供对话连续性）。\n"
        f"⚠️ 此摘要仅用于帮助你回忆上下文。\n"
        f"所有系统事实（覆盖率、违规列表、文件清单、修复状态）已存储在外部账本中。\n"
        f"请通过工具重新加载：get_pending_violations, list_files, get_rules_text 等。\n"
        f"不要假设摘要中的数字为准确——始终从工具重新获取。\n\n"
        f"{summary}\n\n"
        f"[摘要结束] 以上为压缩摘要。继续执行任务，并通过工具重新加载事实状态。"
    ))
    # 保留 SystemMessage + 摘要 + 最后 keep_recent 条消息
    # ⚠️ 关键：必须确保不拆散 AIMessage(tool_calls)/ToolMessage 配对
    if len(body_msgs) >= keep_recent:
        cut_pos = len(body_msgs) - keep_recent
        # ── 向后扩展：确保 cut_pos 不在 AIMessage(tool_calls) 和其 ToolMessage 之间 ──
        # 扫描 cut_pos 附近，如果 cut_pos 落在配对中间，向前找到 AIMessage
        while cut_pos > 0:
            curr = body_msgs[cut_pos]
            prev = body_msgs[cut_pos - 1]
            # 不安全：prev 是 AIMessage(tool_calls)，curr 是其 ToolMessage
            if (isinstance(prev, AIMessage) and getattr(prev, "tool_calls", None)
                    and isinstance(curr, ToolMessage)):
                cut_pos -= 1  # 向前移动，包含这个 AIMessage
            # 不安全：两个连续的 ToolMessage（属于同一个 AIMessage）
            elif isinstance(prev, ToolMessage) and isinstance(curr, ToolMessage):
                cut_pos -= 1
            else:
                break
        # ── 向前扩展：如果 recent 中有 ToolMessage 但其 AIMessage 不在 recent ──
        # 找到 recent 中所有 ToolMessage 的 tool_call_id
        recent_tool_ids: set[str] = set()
        for m in body_msgs[cut_pos:]:
            if isinstance(m, ToolMessage):
                recent_tool_ids.add(m.tool_call_id)
        # 找到这些 tool_call_id 对应的 AIMessage 位置
        aim_positions: set[int] = set()
        for i in range(cut_pos):
            m = body_msgs[i]
            if isinstance(m, AIMessage) and getattr(m, "tool_calls", None):
                for tc in m.tool_calls:
                    if tc.get("id") in recent_tool_ids:
                        aim_positions.add(i)
        # 如果 AIMessage 在 cut_pos 之前，需要向前扩展
        if aim_positions:
            cut_pos = min(cut_pos, min(aim_positions))
        recent = body_msgs[cut_pos:]
    else:
        recent = body_msgs

    result = system_msgs + [summary_msg] + recent

    # ── 最终校验：确保 L4 产出无孤立的 tool_call/tool_result ──
    result = _validate_no_orphans(result)

    return result, action


# ============================================================================
# Post-Compact 恢复（v2 核心修复）
# ============================================================================

POST_COMPACT_TOKEN_BUDGET = 20000       # 恢复内容总预算（字符数），v2: 50K→20K
POST_COMPACT_MAX_FILES = 3              # 最多恢复文件数，v2: 5→3
POST_COMPACT_MAX_CHARS_PER_FILE = 5000  # 每个文件最多恢复字符数

# Compaction Boundary Marker — 分隔摘要/恢复内容与完整保真消息
_BOUNDARY_MARKER = (
    "━━━━━━ 上下文分界 ━━━━━━\n"
    "以上为压缩摘要和恢复的关键上下文。以下为压缩前保留的完整保真消息。\n"
    "如对以上恢复内容有疑问，请通过工具重新加载：\n"
    "  - read_file 重新读取文件\n"
    "  - get_violation_detail 重新加载违规详情\n"
    "  - get_pending_fixes 重新加载修复状态\n"
    "  - get_wiki_page / get_rules_text 重新获取规范文本\n"
    "不要假设摘要或恢复内容中的任何数字或代码片段为准确——始终从工具重新获取。"
)


def post_compact_restore(
    compacted: list,
    original: list,
    agent_name: str = "",
) -> list:
    """在 L4 compact 之后恢复关键上下文，防止 agent "失忆"。

    恢复顺序（参考真实 CC 的 buildPostCompactMessages）：
      1. 用户任务目标（来自原始消息的第一条 HumanMessage）
      2. 最近读取的文件内容（来自 ReadFileTracker，预算控制）
      3. Compaction Boundary Marker（分隔摘要与完整保真区域）

    不恢复系统事实状态（违规列表、覆盖率、修复状态）——
    这些由 agent 通过 get_violation_detail / get_pending_fixes 等工具重新加载。

    恢复提示使用中文（与 checker agent 的中文 system prompt 一致）。

    Args:
        compacted: compact_history 输出的消息列表
        original: compact 前的原始消息列表（用于提取用户目标）
        agent_name: agent 标识（用于查找对应的 ReadFileTracker）

    Returns:
        恢复后的消息列表
    """
    # ── 1. 提取用户任务目标 ──
    goal = _extract_user_goal(original)
    goal_msgs: list = []
    if goal:
        goal_msgs.append(HumanMessage(content=(
            f"[任务目标] 以下为你正在执行的任务，上下文压缩后请继续：\n\n"
            f"{goal}\n\n"
            f"[任务目标结束]"
        )))

    # ── 2. 恢复最近读取的文件 ──
    file_msgs: list = []
    if agent_name:
        tracker = get_tracker(agent_name)
        if tracker:
            recent_files = tracker.get_recent(
                n=POST_COMPACT_MAX_FILES,
                max_chars_per_file=POST_COMPACT_MAX_CHARS_PER_FILE,
                total_budget_chars=POST_COMPACT_TOKEN_BUDGET,
            )
            for path, content in recent_files:
                basename = os.path.basename(path)
                file_msgs.append(HumanMessage(content=(
                    f"[恢复文件] {basename}\n"
                    f"路径: {path}\n"
                    f"---\n"
                    f"{content}\n"
                    f"---\n"
                    f"[文件结束] 如需完整内容请用 read_file(\"{path}\") 重新读取。"
                )))

    # ── 3. 分离 compacted 消息中的 SystemMessage 和正文 ──
    system_msgs = [m for m in compacted if isinstance(m, SystemMessage)]
    body_msgs = [m for m in compacted if not isinstance(m, SystemMessage)]

    # ── 4. 找到摘要消息的位置 ──
    # compact_history 的摘要消息以 "[对话摘要]" 开头
    summary_idx = None
    for i, m in enumerate(body_msgs):
        if isinstance(m, HumanMessage) and "[对话摘要]" in str(getattr(m, "content", "")):
            summary_idx = i
            break

    if summary_idx is None:
        # 没有摘要消息，恢复内容放在最前面
        boundary_marker = SystemMessage(content=_BOUNDARY_MARKER)
        return system_msgs + goal_msgs + file_msgs + [boundary_marker] + body_msgs

    # ── 5. 组装：摘要 → 恢复内容 → Boundary Marker → 近期消息 ──
    before_summary = body_msgs[:summary_idx + 1]  # 包含摘要消息
    after_summary = body_msgs[summary_idx + 1:]    # 近期完整保真消息

    boundary_marker = SystemMessage(content=_BOUNDARY_MARKER)

    return (
        system_msgs
        + before_summary
        + goal_msgs
        + file_msgs
        + [boundary_marker]
        + after_summary
    )


# ============================================================================
# 五层压缩管线
# ============================================================================


def run_compaction_pipeline(
    messages: list,
    agent_name: str = "unknown",
    chunk_label: str = "",
    telemetry: bool = True,
    critical_tool_names: set = None,
    **kwargs,
) -> list:
    """执行完整上下文压缩管线（L3 → L1 → L2 → [L4] → guard）。

    这是 pre_model_hook 调用的核心函数。
    管线顺序：L3(免费) → L1(免费) → L2(免费) → [L4(付费摘要)] → guard(免费安全网)

    "Cheap first, expensive last." — 免费层先过滤，L4 只处理残留的超标上下文。

    Args:
        messages: 当前 ReAct agent 的全部消息
        agent_name: agent 标识（用于遥测）
        chunk_label: chunk 标识（如 "2/5"）
        telemetry: 是否记录遥测
        critical_tool_names: 关键工具名集合，这些工具的结果 L1/L2/L3 均跳过
        **kwargs: 覆盖 DEFAULTS 中的参数

    Returns:
        压缩后的消息列表
    """
    # 合并参数
    params = {**DEFAULTS, **kwargs}
    critical_tool_names = critical_tool_names or set()

    # ── 遥测：压缩前指标 ──
    pre_metrics = _collect_metrics(messages) if telemetry else None
    layer_actions = {}

    working = list(messages)

    # ── L3: Tool Result 持久化（免费）──
    working, l3_action = tool_result_persist(
        working,
        persist_threshold=params["persist_threshold"],
        critical_tool_names=critical_tool_names,
    )
    layer_actions["L3_tool_result_persist"] = l3_action

    # ── L1: Snip Compact（免费）──
    working, l1_action = snip_compact(
        working,
        max_messages=params["max_messages"],
        keep_head=params["keep_head"],
        keep_tail=params["keep_tail"],
        critical_tool_names=critical_tool_names,
    )
    layer_actions["L1_snip_compact"] = l1_action

    # ── L2: Micro Compact（免费）──
    working, l2_action = micro_compact(
        working,
        keep_recent=params["keep_recent_tool_results"],
        critical_tool_names=critical_tool_names,
    )
    layer_actions["L2_micro_compact"] = l2_action

    # ── 兜底校验：确保无孤立的 tool_call/tool_result ──
    working = _validate_no_orphans(working)

    # ── L4: LLM 摘要压缩（付费，token 超阈值时触发）──
    # 位置：L1+L2 之后、guard 之前 — 先免费过滤，再用付费 LLM 处理残留
    l4_action = {"triggered": False, "summary_tokens": 0}
    l4_threshold = params.get("l4_token_threshold")
    l4_model = params.get("l4_model")
    # 从 kwargs 获取 per-agent 的 L4 熔断器（由 CompactionHookFactory 注入）
    l4_breaker = kwargs.get("_l4_breaker")
    if l4_threshold is not None and l4_model is not None:
        # ── 检查 L4 熔断器 ──
        if l4_breaker is not None and l4_breaker.is_open:
            l4_action = {"triggered": False, "skipped": "circuit_breaker_open"}
        else:
            current_tokens = _estimate_tokens(working)
            if current_tokens > l4_threshold:
                pre_l4_tokens = current_tokens
                working, l4_action = compact_history(
                    working,
                    model=l4_model,
                    keep_recent=params.get("l4_keep_recent", 15),
                    tool_result_cap=params.get("l4_tool_result_cap", 2000),
                )
                # ── v2: post-compact 恢复关键上下文 ──
                if l4_action.get("triggered"):
                    working = post_compact_restore(
                        working, messages, agent_name,
                    )
                    # 纵深防御：恢复后再次校验配对完整性
                    working = _validate_no_orphans(working)
                # ── v2: 记录 L4 结果到熔断器 ──
                if l4_breaker is not None and l4_action.get("triggered"):
                    post_l4_tokens = _estimate_tokens(working)
                    l4_breaker.record_result(pre_l4_tokens, post_l4_tokens)
    layer_actions["L4_compact_history"] = l4_action

    # ── Guard: 硬限保护（最终安全网）──
    # 正常路径：L4@96K 触发后上下文已大幅缩减，guard 使用高位阈值（几乎不触发）
    # 熔断路径：breaker open → L4 跳过 → guard 降级为原阈值，用粗暴截断兜底
    guard_char_limit = (
        params["critical_char_limit"]
        if (l4_breaker is not None and l4_breaker.is_open)
        else params.get("critical_char_limit_l4", 160000)
    )
    working, guard_action = critical_guard(
        working,
        critical_char_limit=guard_char_limit,
    )
    layer_actions["guard_critical"] = guard_action

    # ── 遥测：压缩后指标 + 写入 ──
    if telemetry:
        post_metrics = _collect_metrics(working)
        savings_pct = (
            (1 - post_metrics["estimated_tokens"] / max(1, pre_metrics["estimated_tokens"])) * 100
            if pre_metrics["estimated_tokens"] > 0
            else 0
        )
        record = {
            "ts": datetime.now().isoformat(),
            "agent": agent_name,
            "chunk": chunk_label,
            "pre": pre_metrics,
            "layers": layer_actions,
            "post": post_metrics,
            "savings_pct": round(savings_pct, 1),
        }
        _record_telemetry(record)

    return working


# ============================================================================
# pre_model_hook 工厂函数
# ============================================================================


def create_compaction_hook(
    agent_name: str = "unknown",
    telemetry: bool = True,
    **param_overrides,
) -> Callable[[dict], dict]:
    """创建 pre_model_hook 函数，供 create_react_agent 使用。

    Args:
        agent_name: agent 标识（用于遥测）
        telemetry: 是否启用遥测记录
        **param_overrides: 覆盖 DEFAULTS 中的压缩参数

    Returns:
        签名为 (state: dict) -> dict 的 hook 函数

    Usage:
        agent = create_react_agent(
            model=llm,
            tools=tools,
            prompt=system_prompt,
            pre_model_hook=create_compaction_hook("cpp_agent", max_messages=60),
        )
    """
    params = param_overrides  # 捕获覆盖参数

    def hook(state: dict) -> dict:
        messages = state.get("messages", [])

        if not messages:
            return {}

        compacted = run_compaction_pipeline(
            messages,
            agent_name=agent_name,
            chunk_label="",  # 由调用方在 agent 节点中无法动态传入，使用默认
            telemetry=telemetry,
            **params,
        )

        # 使用 llm_input_messages：仅影响本次 LLM 调用，
        # 不修改持久化的 messages 历史（便于调试和后续分析）
        return {"llm_input_messages": compacted}

    return hook


# ============================================================================
# 辅助：带 chunk 标签的压缩 hook（用于 ThreadPoolExecutor 场景）
# ============================================================================


class CompactionHookFactory:
    """可动态设置 chunk 标签的 hook 工厂。

    ThreadPoolExecutor 中每个 chunk 在不同线程中运行，
    需要在 _run_chunk 内部设置 chunk_label 后再执行 ReAct 循环。
    但 pre_model_hook 无法在线程间传递动态参数，因此提供这个类：

    Usage:
        factory = CompactionHookFactory("cpp_agent")
        # 在每个 _run_chunk 中：
        factory.set_chunk(f"2/5")
        agent = create_react_agent(..., pre_model_hook=factory.hook)
    """

    def __init__(self, agent_name: str, telemetry: bool = True,
                 critical_tool_names: set = None, **params):
        self.agent_name = agent_name
        self.telemetry = telemetry
        self.params = {**DEFAULTS, **params}
        self._local = threading.local()
        self._local.chunk = ""

        # ── v2: per-agent ReadFileTracker ──
        self.read_tracker = ReadFileTracker()
        register_tracker(agent_name, self.read_tracker)

        # ── v2: per-agent L4 熔断器（模块级持久化，跨函数调用存活）──
        existing = get_breaker(agent_name)
        if existing is not None:
            self.l4_breaker = existing
        else:
            self.l4_breaker = L4CircuitBreaker()
            register_breaker(agent_name, self.l4_breaker)

        # 存储 critical_tool_names 供 hook 使用
        self.critical_tool_names = critical_tool_names or set()

    def set_chunk(self, label: str) -> None:
        """设置当前 chunk 标签（在 _run_chunk 中调用，线程安全）。"""
        self._local.chunk = label

    def hook(self, state: dict) -> dict:
        """pre_model_hook 兼容的函数签名。"""
        messages = state.get("messages", [])
        if not messages:
            return {}

        compacted = run_compaction_pipeline(
            messages,
            agent_name=self.agent_name,
            chunk_label=getattr(self._local, "chunk", ""),
            telemetry=self.telemetry,
            critical_tool_names=self.critical_tool_names,
            _l4_breaker=self.l4_breaker,
            **self.params,
        )
        return {"llm_input_messages": compacted}
