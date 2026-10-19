"""
工具函数：JSON 提取、文件读取、进度条等。
"""

import json
import os
import re
import sys
import time
import random
import threading
from typing import Optional


# ── 真实请求并发门禁 ──
# SubmissionPacer 只控制"任务进入线程池"的速度，不控制 agent.invoke()
# 内部实际发出的 HTTP 请求数。此信号量限制同时在飞的 LLM API 调用数，
# 防止线程池中 20 个 worker 同时打 API 造成 503 尖刺。
from code_checker.config import MAX_CONCURRENCY
_in_flight_semaphore = threading.Semaphore(MAX_CONCURRENCY)


def invoke_with_retry(agent, task_msg: str, label: str, config: dict = None,
                      max_retries: int = 4):
    """带去相关抖动的 LLM invoke，处理 503，集成熔断器 + 请求并发门禁。

    每次 LLM 调用前先过熔断器检查（before_request），熔断中直接拒绝。
    通过后在信号量保护下执行实际 API 调用，确保同时在飞请求数 ≤ MAX_CONCURRENCY。
    重试间隔: 去相关抖动（AWS 方案）——每次延迟 = min(30s, random(1s, 上次延迟×3))。
    同一批次中每个请求的延迟序列完全不同，天然错开，不形成二次尖刺。

    重要: on_failure 只在所有重试耗尽后才调用一次，防止重试放大失败计数。
    SDK 级 max_retries=0，重试仅由此函数管理（单层重试）。

    半开探测令牌：before_request() 在 half_open 状态返回一次性 token，
    后续 on_success/on_failure 必须携带此 token 结算。非 503 异常也会结算探测，
    防止熔断器永久卡在 half_open。
    """
    if config is None:
        config = {"recursion_limit": 120}
    prev_delay = 1.0  # 初始基准

    from code_checker.rate_limiter import get_circuit_breaker, CircuitBreakerOpenError
    breaker = get_circuit_breaker()
    probe_token: object | None = None  # 半开探测凭证

    for attempt in range(max_retries):
        # ── 第一道：快速熔断检查（无锁竞争时可以快速拒绝）──
        # 重试时传入上次的 probe_token，让 breaker 识别同一探测
        try:
            breaker.before_request(probe_token)
        except CircuitBreakerOpenError:
            raise  # 熔断中，直接拒绝，不重试

        # ── 获取真实请求槽位 ──
        _in_flight_semaphore.acquire()
        semaphore_held = True
        try:
            # ── 第二道：排队后重新检查（防止排队期间熔断器状态变更）──
            # 场景：通过第一道检查时 breaker 是 CLOSED，但在信号量排队期间
            # 其他请求失败导致 breaker → OPEN。此时必须拒绝，不能执行。
            # 半开探测的 token 在此处获取/更新。
            try:
                probe_token = breaker.before_request(probe_token)
            except CircuitBreakerOpenError:
                raise  # 排队期间熔断，拒绝执行

            from langchain_core.messages import HumanMessage
            result = agent.invoke(
                {"messages": [HumanMessage(content=task_msg)]},
                config=config,
            )
            breaker.on_success(probe_token)
            return result
        except Exception as e:
            err = str(e)
            if "503" in err or "busy" in err.lower() or "service_unavailable" in err:
                if attempt < max_retries - 1:
                    delay = min(30.0, random.uniform(1.0, prev_delay * 3))
                    print(f"  [retry] {label} 503 过载，{delay:.1f}s 后重试"
                          f" ({attempt + 1}/{max_retries})")
                    # ── 释放槽位再等待，不占着槽位 sleep ──
                    _in_flight_semaphore.release()
                    semaphore_held = False
                    time.sleep(delay)
                    prev_delay = delay
                    continue
                # 所有重试耗尽 → 计一次失败，结算探测
                breaker.on_failure(probe_token)
            else:
                # ── 非 503 异常：同样结算探测，防止永久卡在 half_open ──
                breaker.on_failure(probe_token)
            raise
        finally:
            if semaphore_held:
                _in_flight_semaphore.release()


# ── 消息序列化（agent 轨迹落盘用）────────────────────────
def _clip(text: str, limit: int) -> str:
    """截断长文本，超限时加省略标记。"""
    if text is None:
        return ""
    text = str(text)
    if len(text) <= limit:
        return text
    return text[:limit] + f"...[截断,共{len(text)}字符]"


def serialize_messages(messages: list) -> list[dict]:
    """把 langchain 消息列表序列化成紧凑 dict，供 agent 轨迹落盘。

    只记角色 + 工具名 + 工具参数 + 截断预览，不落全量内容——
    完整文件 / wiki 原文在磁盘上，归因时按参数路径回读即可。
    """
    from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

    out: list[dict] = []
    for m in messages:
        if isinstance(m, HumanMessage):
            out.append({"role": "human", "text": _clip(str(m.content), 2000)})
        elif isinstance(m, AIMessage):
            calls = [
                {"name": tc.get("name", ""),
                 "args": _clip(json.dumps(tc.get("args", {}), ensure_ascii=False,
                                          default=str), 500)}
                for tc in (getattr(m, "tool_calls", None) or [])
            ]
            out.append({"role": "ai", "text": _clip(str(m.content or ""), 1000),
                        "tool_calls": calls})
        elif isinstance(m, ToolMessage):
            out.append({"role": "tool", "name": getattr(m, "name", ""),
                        "preview": _clip(str(m.content), 4000)})
        else:
            out.append({"role": type(m).__name__,
                        "text": _clip(str(getattr(m, "content", "")), 1000)})
    return out


# ── 进度条 ──────────────────────────────────────────────
_ENABLE_PROGRESS = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
_BAR_WIDTH = 16

if _ENABLE_PROGRESS:
    import threading
    _multi_lock = threading.Lock()
    _multi_rows = 4          # C++ / Qt / Git / SQLite
    _multi_bars = [""] * _multi_rows
    _multi_inited = False


def _make_bar(pct: float) -> str:
    if not _ENABLE_PROGRESS:
        return ""
    filled = int(_BAR_WIDTH * pct)
    return "█" * filled + "░" * (_BAR_WIDTH - filled)


def _render_multi_row(row: int, text: str):
    """刷新第 row 行（0=顶, 3=底），其余行保持不变，光标回到底部。"""
    if not _ENABLE_PROGRESS:
        return
    global _multi_inited
    with _multi_lock:
        if not _multi_inited:
            # 首次：打印 4 行占位
            for _ in range(_multi_rows):
                sys.stdout.write("\n")
            sys.stdout.flush()
            _multi_inited = True

        _multi_bars[row] = text

        # 光标上移到第 row 行，覆盖写入
        up = _multi_rows - row
        sys.stdout.write(f"\033[{up}A\r\033[K{_multi_bars[row]}")
        # 逐行下移，刷新后续行
        for r in range(row + 1, _multi_rows):
            sys.stdout.write(f"\n\033[K{_multi_bars[r]}")
        # 光标回到底部
        sys.stdout.write(f"\n\033[K")
        sys.stdout.flush()


def _finish_multi_row(row: int, text: str):
    """完成某行，写入最终文本后不再更新。"""
    if not _ENABLE_PROGRESS:
        return
    global _multi_inited
    with _multi_lock:
        if not _multi_inited:
            print(text)
            return
        _multi_bars[row] = text
        up = _multi_rows - row
        sys.stdout.write(f"\033[{up}A\r\033[K{text}")
        for r in range(row + 1, _multi_rows):
            sys.stdout.write(f"\n\033[K{_multi_bars[r]}")
        sys.stdout.write(f"\n\033[K")
        sys.stdout.flush()


class Progress:
    """单行进度条，用于串行阶段（fix_planner / self_critique）。"""

    def __init__(self, label: str, total: int):
        self.label = label
        self.total = max(total, 1)
        self._last_len = 0

    def update(self, current: int, extra: str = ""):
        if not _ENABLE_PROGRESS:
            return
        bar = _make_bar(min(current / self.total, 1.0))
        line = f"  [{self.label}] |{bar}| {current}/{self.total} {extra}"
        pad = self._last_len - len(line)
        if pad > 0:
            line += " " * pad
        sys.stdout.write("\r" + line)
        sys.stdout.flush()
        self._last_len = len(line)

    def done(self):
        if not _ENABLE_PROGRESS:
            return
        sys.stdout.write("\n")
        sys.stdout.flush()


def extract_json_array(raw_text: str, source_label: str = "") -> list[dict]:
    """
    从 LLM 返回的原始文本中提取 JSON 数组。

    具备多层容错：
      1. 去掉 ```json ... ``` 包裹
      2. 定位最外层 [ ... ] 或 { ... }
      3. 修复末尾多余逗号
      4. 整体解析失败时，逐对象正则提取回退

    Args:
        raw_text: LLM 的原始输出文本。
        source_label: 来源标识（文件路径等），仅用于日志。

    Returns:
        解析出的违规/方案字典列表；失败时返回空列表。
    """
    text = raw_text.strip()

    # ── 1. 去除 markdown 代码块包裹 ──
    m = re.search(r"```(?:json)?\s*\n(.*?)```", text, re.DOTALL)
    if m:
        text = m.group(1).strip()

    # ── 2. 定位 JSON 区域 ──
    s = text.find("[")
    e = text.rfind("]")

    if s == -1 or e == -1 or s >= e:
        # 尝试作为单个对象处理
        return _extract_json_object(text, source_label)

    text = text[s:e + 1]

    # ── 3. 修复尾部逗号 ──
    text = re.sub(r",\s*\]", "]", text)
    text = re.sub(r",\s*\}", "}", text)

    # ── 4. 整体解析 ──
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass

    # ── 5. 逐对象提取（回退策略） ──
    print(f"  [警告] {source_label}: 整体解析失败, 逐条提取...")
    items: list[dict] = []
    for match in re.finditer(r"\{[^{}]*\}", text):
        try:
            items.append(json.loads(match.group()))
        except json.JSONDecodeError:
            continue

    if items:
        print(f"  [恢复] 提取 {len(items)} 条")
    else:
        print(f"  [放弃] {source_label}")

    return items


def _extract_json_object(text: str, source_label: str) -> list[dict]:
    """从文本中提取单个 JSON 对象（LLM 可能返回对象而非数组时的回退）。"""
    s = text.find("{")
    e = text.rfind("}")
    if s == -1 or e == -1 or s >= e:
        print(f"  [警告] {source_label}: 找不到 JSON 结构")
        return []

    text = text[s:e + 1]
    text = re.sub(r",\s*\}", "}", text)

    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            # 兼容 {"violations": [...]} 结构
            violations = obj.get("violations")
            if isinstance(violations, list):
                return violations
            return [obj]
    except json.JSONDecodeError:
        print(f"  [警告] {source_label}: 对象解析失败")
    return []


def read_file_content(file_path: str) -> Optional[str]:
    """
    读取文件内容，优先 UTF-8，失败回退 GBK。

    Args:
        file_path: 文件绝对路径。

    Returns:
        文件文本内容；如果两种编码都失败则返回 None。
    """
    for encoding in ("utf-8", "gbk"):
        try:
            with open(file_path, "r", encoding=encoding) as fh:
                return fh.read()
        except (UnicodeDecodeError, FileNotFoundError):
            continue
    return None


def extract_surrounding_lines(
    content: str, line_number: int, context_lines: int = 3
) -> str:
    """
    从文件内容中提取指定行号前后 N 行的代码上下文。

    Args:
        content: 文件全文。
        line_number: 违规行号（1-indexed）。
        context_lines: 前后各取几行，默认 3。

    Returns:
        带行号标记的代码片段，违规行用 → 标注。例：
            118:     void foo() {
            119:         int x = 0;
          → 120:         char* buf = malloc(100);
            121:         free(buf);
            122:     }
    """
    if not content or line_number <= 0:
        return ""

    all_lines = content.split("\n")
    start = max(0, line_number - context_lines - 1)
    end = min(len(all_lines), line_number + context_lines)

    result: list[str] = []
    for i in range(start, end):
        ln = i + 1
        prefix = "  → " if ln == line_number else "    "
        result.append(f"{prefix}{ln:4d}: {all_lines[i]}")

    return "\n".join(result)


def enrich_violation_context(v: dict, file_contents: dict, context_lines: int = 3) -> None:
    """
    为一条违规记录补全文件路径和真实代码上下文。

    向 v 中写入:
      - surrounding: 违规行前后 N 行真实代码（带行号，违规行 → 标注）
      - 顶部带 "文件: <路径>" 头
    """
    file_path = v.get("file", "")
    content = file_contents.get(file_path, "")
    code_ctx = extract_surrounding_lines(content, v.get("line", 0), context_lines)
    if code_ctx:
        v.setdefault("surrounding", f"文件: {file_path}\n{code_ctx}")
    else:
        v.setdefault("surrounding", f"文件: {file_path}\n(无法提取上下文)")


def get_rule_file_path(source: str) -> str | None:
    """
    将 checker source 标签映射到对应的规则文件路径。

    Args:
        source: checker 来源名，如 "cpp", "qt", "sqlite", "git"。

    Returns:
        规则文件绝对路径，git 或未知来源返回 None。
    """
    from code_checker.config import CPP_RULES_FILE, QT_RULES_FILE, SQLITE_RULES_FILE

    _MAP: dict[str, str] = {
        "cpp":    CPP_RULES_FILE,
        "qt":     QT_RULES_FILE,
        "sqlite": SQLITE_RULES_FILE,
    }
    return _MAP.get(source)


def read_rules_file(file_path: str) -> str:
    """
    读取规范文件（UTF-8）。

    Args:
        file_path: 规范文件绝对路径。

    Returns:
        规范文件全文。
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()
