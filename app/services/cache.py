"""A small async TTL cache with LRU eviction and stale-on-error fallback."""

from __future__ import annotations

import asyncio
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from app.services.errors import UpstreamError


@dataclass(slots=True)
class _Entry[T]:
    value: T
    stored_at: float


class TTLCache[T]:
    """In-process cache.

    Entries are *fresh* for ``ttl`` seconds. After that they may still be served as
    *stale* for ``stale_ttl`` more seconds, but only when reloading fails.
    """

    def __init__(
        self,
        ttl: float,
        max_entries: int,
        stale_ttl: float = 0.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if ttl <= 0 or max_entries <= 0 or stale_ttl < 0:
            raise ValueError("ttl and max_entries must be positive; stale_ttl non-negative")
        self._ttl = ttl
        self._stale_ttl = stale_ttl
        self._max_entries = max_entries
        self._clock = clock
        self._data: OrderedDict[str, _Entry[T]] = OrderedDict()
        self._locks: dict[str, asyncio.Lock] = {}

    def __len__(self) -> int:
        return len(self._data)

    def get(self, key: str) -> T | None:
        """Return a fresh value, or ``None`` if missing or expired."""
        entry = self._data.get(key)
        if entry is None or self._age(entry) > self._ttl:
            return None
        self._data.move_to_end(key)
        return entry.value

    def get_stale(self, key: str) -> T | None:
        """Return an expired value still within the stale window, else ``None``."""
        entry = self._data.get(key)
        if entry is None or self._age(entry) > self._ttl + self._stale_ttl:
            return None
        return entry.value

    def set(self, key: str, value: T) -> None:
        """Store a value, evicting the least recently used entry when full."""
        self._data[key] = _Entry(value=value, stored_at=self._clock())
        self._data.move_to_end(key)
        while len(self._data) > self._max_entries:
            evicted, _ = self._data.popitem(last=False)
            self._locks.pop(evicted, None)

    async def get_or_load(self, key: str, loader: Callable[[], Awaitable[T]]) -> tuple[T, bool]:
        """Return ``(value, is_stale)``, loading at most once per key concurrently.

        Raises:
            UpstreamError: if loading fails and no stale value is available.
        """
        cached = self.get(key)
        if cached is not None:
            return cached, False

        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            cached = self.get(key)
            if cached is not None:
                return cached, False
            try:
                value = await loader()
            except UpstreamError:
                stale = self.get_stale(key)
                if stale is None:
                    raise
                return stale, True
            self.set(key, value)
            return value, False

    def _age(self, entry: _Entry[T]) -> float:
        return self._clock() - entry.stored_at
