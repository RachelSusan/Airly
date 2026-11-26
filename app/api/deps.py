"""Shared request dependencies: services, AI client and rate limits."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Request

from app.ai.client import ClaudeClient
from app.api.errors import AppError
from app.config import Settings
from app.security.rate_limit import SlidingWindowLimiter
from app.services.air_quality import AirQualityService
from app.services.geocoding import GeocodingService

RATE_LIMITS: dict[str, int] = {"read": 60, "ai": 10, "chat": 20}  # requests per minute


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_air_service(request: Request) -> AirQualityService:
    return request.app.state.air_service


def get_geocoding_service(request: Request) -> GeocodingService:
    return request.app.state.geocoding_service


def get_ai(request: Request) -> ClaudeClient | None:
    return request.app.state.ai


def build_limiters() -> dict[str, SlidingWindowLimiter]:
    """One limiter per endpoint group."""
    return {group: SlidingWindowLimiter(limit) for group, limit in RATE_LIMITS.items()}


def rate_limit(group: str) -> Callable[[Request], Awaitable[None]]:
    """Dependency that enforces the per-IP limit for ``group``."""

    async def _check(request: Request) -> None:
        if not request.app.state.settings.rate_limit_enabled:
            return
        client = request.client.host if request.client else "unknown"
        retry_after = request.app.state.limiters[group].hit(client)
        if retry_after is not None:
            raise AppError(
                429,
                "rate_limited",
                "Too many requests. Please wait a moment and try again.",
                headers={"Retry-After": str(retry_after)},
            )

    return _check
