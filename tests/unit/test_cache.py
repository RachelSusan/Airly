import asyncio

import pytest

from app.services.cache import TTLCache
from app.services.errors import UpstreamError


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_get_returns_fresh_value_then_expires() -> None:
    clock = FakeClock()
    cache: TTLCache[str] = TTLCache(ttl=10, max_entries=5, clock=clock)
    cache.set("k", "v")
    assert cache.get("k") == "v"
    clock.now = 11
    assert cache.get("k") is None


def test_lru_eviction() -> None:
    cache: TTLCache[int] = TTLCache(ttl=10, max_entries=2)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.get("a")  # a becomes most recently used
    cache.set("c", 3)
    assert cache.get("b") is None
    assert cache.get("a") == 1
    assert len(cache) == 2


def test_invalid_configuration() -> None:
    with pytest.raises(ValueError):
        TTLCache(ttl=0, max_entries=1)


async def test_get_or_load_loads_once_for_concurrent_callers() -> None:
    cache: TTLCache[int] = TTLCache(ttl=10, max_entries=5)
    calls = 0

    async def loader() -> int:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0)
        return 42

    results = await asyncio.gather(*(cache.get_or_load("k", loader) for _ in range(5)))
    assert all(r == (42, False) for r in results)
    assert calls == 1


async def test_get_or_load_serves_stale_on_upstream_error() -> None:
    clock = FakeClock()
    cache: TTLCache[str] = TTLCache(ttl=10, max_entries=5, stale_ttl=100, clock=clock)
    cache.set("k", "old")
    clock.now = 20

    async def failing() -> str:
        raise UpstreamError("down")

    assert await cache.get_or_load("k", failing) == ("old", True)


async def test_get_or_load_raises_when_no_stale_value() -> None:
    clock = FakeClock()
    cache: TTLCache[str] = TTLCache(ttl=10, max_entries=5, stale_ttl=5, clock=clock)
    cache.set("k", "old")
    clock.now = 100

    async def failing() -> str:
        raise UpstreamError("down")

    with pytest.raises(UpstreamError):
        await cache.get_or_load("k", failing)
