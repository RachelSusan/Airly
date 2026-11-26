"""Per-client sliding-window rate limiting (in memory, per process)."""

from __future__ import annotations

import math
import time
from collections import deque
from collections.abc import Callable

MAX_TRACKED_CLIENTS = 10_000


class SlidingWindowLimiter:
    """Allow at most ``limit`` requests per ``window`` seconds for each key."""

    def __init__(
        self, limit: int, window: float = 60.0, clock: Callable[[], float] = time.monotonic
    ) -> None:
        if limit <= 0 or window <= 0:
            raise ValueError("limit and window must be positive")
        self.limit = limit
        self.window = window
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}

    def hit(self, key: str) -> int | None:
        """Record a request. Return ``None`` if allowed, else seconds to wait."""
        now = self._clock()
        hits = self._hits.setdefault(key, deque())
        while hits and now - hits[0] >= self.window:
            hits.popleft()
        if len(hits) >= self.limit:
            return max(1, math.ceil(self.window - (now - hits[0])))
        hits.append(now)
        if len(self._hits) > MAX_TRACKED_CLIENTS:
            self._prune(now)
        return None

    def _prune(self, now: float) -> None:
        stale = [k for k, v in self._hits.items() if not v or now - v[-1] >= self.window]
        for key in stale:
            del self._hits[key]
