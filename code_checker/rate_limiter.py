"""
LLM API 流控模块 — 解决高并发下 DeepSeek 503 的三种机制。

1. SubmissionPacer   — 提交间隔控制，消灭瞬时尖刺
2. CircuitBreaker    — 真三态熔断器（Closed → Open → HalfOpen → Closed）
3. RateLimitedExecutor — 包装 ThreadPoolExecutor，集成上述机制

所有 agent 共享同一个熔断器实例（进程级单例），因为它们都打同一个 API。
"""

import time
import threading
from concurrent.futures import ThreadPoolExecutor


# ---------------------------------------------------------------------------
# 提交节奏器 — 确保两次 submit 之间有最小间隔
# ---------------------------------------------------------------------------

class SubmissionPacer:
    """控制任务提交速率，防止 ThreadPoolExecutor 在微秒级全量提交。

    每次 submit 前调用 wait()，如距上次提交不足 min_interval 则 sleep 补齐。
    """

    def __init__(self, min_interval_ms: int = 50):
        self._min_interval = min_interval_ms / 1000.0
        self._last_submit = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        """阻塞直到距上次提交已过 min_interval。"""
        with self._lock:
            now = time.time()
            gap = self._last_submit + self._min_interval - now
            if gap > 0:
                time.sleep(gap)
            self._last_submit = time.time()


# ---------------------------------------------------------------------------
# 熔断器 — 真三态：Closed → Open → HalfOpen → Closed
# ---------------------------------------------------------------------------

class CircuitBreakerOpenError(Exception):
    """熔断器断开时抛出的异常，调用方捕获后做降级处理。"""
    pass


class CircuitBreaker:
    """三态熔断器，带半开探测（一次只放一个请求）。

    状态转换:
      Closed  ──连续 N 次失败──→ Open
      Open    ──冷却期满────→ HalfOpen
      HalfOpen ──探测成功──→ Closed（重置计数）
      HalfOpen ──探测失败──→ Open（重新冷却）

    进程级单例：所有 agent 共享，因为打的是同一个 DeepSeek API。

    半开探测所有权：通过一次性探测凭证（probe token）实现。
    before_request() 在 half_open 状态下放行时返回一个唯一 token，
    后续 on_success() / on_failure() 必须携带此 token 才能结算探测。
    迟到的旧请求（无 token 或 token 不匹配）无法改变当前状态。
    同一探测的 retry 循环中，将 token 传回 before_request() 即可识别重试。
    """

    def __init__(self, failure_threshold: int = 5, cooldown_seconds: float = 30.0):
        self._threshold = failure_threshold
        self._cooldown = cooldown_seconds
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._state = "closed"          # closed | open | half_open
        self._probe_in_flight = False   # half_open 时只允许一个探测
        self._probe_token: object | None = None  # 一次性探测凭证
        self._lock = threading.Lock()

    # ── 查询（供外部日志/监控使用）──

    @property
    def state(self) -> str:
        with self._lock:
            return self._state

    @property
    def failure_count(self) -> int:
        with self._lock:
            return self._failure_count

    # ── 核心 API ──

    def before_request(self, probe_token: object = None) -> object | None:
        """每次 LLM 请求前必须调用。熔断中抛 CircuitBreakerOpenError。

        半开探测所有权：通过一次性 token 实现。
        - 首次调用（probe_token=None）：若处于 half_open 且无探测进行中，
          生成新 token 并返回。调用方须保存此 token。
        - 重试调用（probe_token=上次返回的 token）：识别为同一探测的重试，
          允许通过。
        - 返回 None 表示当前不在半开探测中（closed 状态正常放行）。

        Returns:
            None — 正常放行（closed 状态），无需 token。
            object — 半开探测 token，调用方须传给 on_success/on_failure。
        """
        with self._lock:
            # 检查是否可以从 open → half_open
            if self._state == "open":
                if time.time() - self._last_failure_time >= self._cooldown:
                    self._state = "half_open"
                    self._probe_in_flight = False
                    self._probe_token = None
                    print("  [熔断器] 冷却结束，进入半开状态（允许一次探测）")

            if self._state == "closed":
                return None

            if self._state == "half_open":
                # 同一探测的 retry：token 匹配 → 允许通过
                if probe_token is not None and probe_token is self._probe_token:
                    return self._probe_token
                # 新探测：无探测进行中 → 生成 token
                if not self._probe_in_flight:
                    self._probe_in_flight = True
                    token = object()  # 唯一的一次性凭证
                    self._probe_token = token
                    return token
                # 已有其他探测在进行中，拒绝
                remaining = self._cooldown - (time.time() - self._last_failure_time)
                raise CircuitBreakerOpenError(
                    f"熔断器半开：等待探测结果，"
                    f"约 {remaining:.0f}s"
                )

            # self._state == "open"
            remaining = self._cooldown - (time.time() - self._last_failure_time)
            raise CircuitBreakerOpenError(
                f"熔断器断开：连续 {self._threshold} 次失败，"
                f"需等待 {remaining:.0f}s"
            )

    def on_success(self, probe_token: object = None) -> None:
        """请求成功后调用。携带 probe_token 结算半开探测。

        仅在 token 匹配当前探测凭证时才关闭熔断器。
        迟到的旧请求（无 token 或 token 过期）无法改变状态。
        """
        with self._lock:
            # 半开状态：只有探测所有者才能关闭
            if self._state == "half_open":
                if probe_token is not self._probe_token:
                    # 迟到请求或非探测请求 — 忽略，不改变状态
                    return
                print("  [熔断器] 探测成功，熔断器关闭")
            # 只在 half_open 或 closed 时重置；open 状态不应出现（before_request 会拒绝）
            if self._state != "open":
                self._state = "closed"
                self._failure_count = 0
            self._probe_in_flight = False
            self._probe_token = None

    def on_failure(self, probe_token: object = None) -> None:
        """请求失败后调用。携带 probe_token 结算半开探测。

        仅在 token 匹配当前探测凭证时才将失败归因于此探测。
        迟到的旧请求的失败不计入当前探测。
        """
        with self._lock:
            # 半开状态：只有探测所有者才能结算失败
            if self._state == "half_open":
                if probe_token is not self._probe_token:
                    # 迟到请求 — 忽略，不计入失败
                    return
                self._failure_count += 1
                self._last_failure_time = time.time()
                print(f"  [熔断器] 探测失败，重新熔断 {self._cooldown:.0f}s")
                self._state = "open"
                self._probe_in_flight = False
                self._probe_token = None
                return

            # closed 状态：正常累计失败
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._failure_count >= self._threshold and self._state == "closed":
                self._state = "open"
                print(f"  [熔断器] 连续 {self._failure_count} 次失败，"
                      f"熔断 {self._cooldown:.0f}s")

    def reset(self) -> None:
        """手动重置熔断器（阶段切换时使用）。

        每次进入新的流水线阶段（fix → review → wiki）时调用，
        防止上一阶段的失败计数污染下一阶段。
        """
        with self._lock:
            was_open = self._state in ("open", "half_open")
            self._state = "closed"
            self._failure_count = 0
            self._probe_in_flight = False
            self._probe_token = None
            if was_open:
                print("  [熔断器] 手动重置（阶段切换）")


# 进程级共享单例
_shared_breaker = CircuitBreaker(failure_threshold=5, cooldown_seconds=30.0)
_shared_pacer = SubmissionPacer(min_interval_ms=50)


def get_circuit_breaker() -> CircuitBreaker:
    """获取进程级熔断器单例。"""
    return _shared_breaker


def reset_circuit_breaker() -> None:
    """重置进程级熔断器（阶段切换时调用）。"""
    _shared_breaker.reset()


# ---------------------------------------------------------------------------
# 限流执行器 — 包装 ThreadPoolExecutor
# ---------------------------------------------------------------------------

class RateLimitedExecutor:
    """带提交节奏控制和熔断保护的 ThreadPoolExecutor。

    Usage:
        with RateLimitedExecutor(max_workers=20) as executor:
            futures = [executor.submit(fn, arg) for arg in args]
            for f in as_completed(futures):
                ...
    """

    def __init__(self, max_workers: int, min_submit_interval_ms: int = 50):
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._pacer = _shared_pacer
        self._breaker = _shared_breaker

    def submit(self, fn, *args, **kwargs):
        """提交任务。

        注意：熔断器检查不在 submit 层执行，而在 invoke_with_retry 中
        （实际 LLM 调用前）。这避免了半开探测自拒绝问题：
        submit 标记 probe_in_flight → 工作线程 invoke_with_retry
        再次检查发现已有探测 → 拒绝自己。

        熔断期间任务仍会提交到线程池，但在 invoke_with_retry 的
        before_request() 中立即失败，线程池槽位占用极短。

        Returns:
            一个 Future 对象。
        """
        self._pacer.wait()
        return self._executor.submit(fn, *args, **kwargs)

    def shutdown(self, wait: bool = True):
        self._executor.shutdown(wait=wait)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._executor.shutdown(wait=True)
        return False
