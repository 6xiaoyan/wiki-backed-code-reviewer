"""运行预算：模型请求数、上下文读取量、阶段时限（PRD §10）。

所有计数集中在一个对象里，四个领域 Agent 与重试共用同一份额度，
避免“每个并行 Agent 各拿完整额度”。预算超限抛 BudgetExceeded，
由上层标记 ``incomplete``——绝不静默截断后声称审查完成。
"""

from __future__ import annotations

import threading
import time
from contextlib import contextmanager

from code_checker.pr_review.models import BudgetConfig


class BudgetExceeded(RuntimeError):
    """预算耗尽。``kind`` 用于区分模型请求 / 上下文 / 时间。"""

    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind


class ReviewBudget:
    """线程安全的预算计数器。"""

    def __init__(self, config: BudgetConfig | None = None, clock=time.monotonic):
        self.config = config or BudgetConfig()
        self._clock = clock
        self._lock = threading.Lock()
        self._started = clock()
        self._model_requests = 0
        self._model_retries = 0
        self._failed_requests = 0
        self._prompt_tokens = 0
        self._completion_tokens = 0
        self._tokens_unknown = False
        self._context_bytes = 0
        self._context_keys: set[tuple] = set()
        self._phases: dict[str, float] = {}
        self._open_phases: dict[str, float] = {}

    # ── 模型请求 ──
    def reserve_model_request(self, label: str = "") -> int:
        self.check_deadline()
        with self._lock:
            if self._model_requests >= self.config.max_model_requests:
                raise BudgetExceeded(
                    "model_requests",
                    f"模型请求预算耗尽（上限 {self.config.max_model_requests} 次）"
                    f"{'，最后一次调用: ' + label if label else ''}",
                )
            self._model_requests += 1
            return self._model_requests

    def record_retry(self) -> None:
        with self._lock:
            self._model_retries += 1

    def record_failed_request(self) -> None:
        with self._lock:
            self._failed_requests += 1

    def record_tokens(self, prompt_tokens: int | None, completion_tokens: int | None) -> None:
        with self._lock:
            if prompt_tokens is None and completion_tokens is None:
                self._tokens_unknown = True
                return
            self._prompt_tokens += int(prompt_tokens or 0)
            self._completion_tokens += int(completion_tokens or 0)

    @property
    def model_requests(self) -> int:
        return self._model_requests

    @property
    def remaining_model_requests(self) -> int:
        return max(0, self.config.max_model_requests - self._model_requests)

    # ── 上下文读取 ──
    def add_context(self, path: str, sha: str, start: int, end: int, nbytes: int) -> int:
        """记录一次额外上下文读取；同一 (路径, 版本, 范围) 只计量一次。

        Returns:
            本次实际计入的字节数（重复读取返回 0）。

        Raises:
            BudgetExceeded: 累计上下文超过上限。
        """
        key = (path, sha, int(start), int(end))
        with self._lock:
            if key in self._context_keys:
                return 0
            if self._context_bytes + nbytes > self.config.max_extra_context_bytes:
                raise BudgetExceeded(
                    "extra_context",
                    f"额外上下文读取超限（上限 {self.config.max_extra_context_bytes} 字节）",
                )
            self._context_keys.add(key)
            self._context_bytes += nbytes
            return nbytes

    @property
    def context_bytes(self) -> int:
        return self._context_bytes

    # ── 时限 ──
    def elapsed(self) -> float:
        return self._clock() - self._started

    def check_deadline(self) -> None:
        if self.elapsed() > self.config.review_timeout_seconds:
            raise BudgetExceeded(
                "timeout",
                f"审查阶段超时（上限 {self.config.review_timeout_seconds} 秒）",
            )

    # ── 阶段耗时 ──
    @contextmanager
    def phase(self, name: str):
        t0 = self._clock()
        try:
            yield
        finally:
            self._phases[name] = round(self._phases.get(name, 0.0) + (self._clock() - t0), 3)

    def usage(self) -> dict:
        with self._lock:
            return {
                "model_requests": self._model_requests,
                "model_requests_limit": self.config.max_model_requests,
                "model_retries": self._model_retries,
                "failed_requests": self._failed_requests,
                "prompt_tokens": self._prompt_tokens,
                "completion_tokens": self._completion_tokens,
                "tokens_unknown": self._tokens_unknown,
                "context_bytes": self._context_bytes,
                "context_bytes_limit": self.config.max_extra_context_bytes,
                "elapsed_seconds": round(self.elapsed(), 1),
                "timeout_seconds": self.config.review_timeout_seconds,
                "phase_seconds": dict(sorted(self._phases.items())),
            }
