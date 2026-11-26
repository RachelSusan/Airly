"""FastAPI application factory."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.ai.client import build_ai_client
from app.api import air, chat, health, plan, simulate
from app.api.deps import build_limiters
from app.api.errors import register_error_handlers
from app.config import Settings, get_settings
from app.models.air import AirData, GridPoint, HourlyReading, Place
from app.security.body_limit import add_body_limit
from app.security.headers import add_security_headers
from app.services.air_grid import AirGridService
from app.services.air_history import AirHistoryService
from app.services.air_quality import AirQualityService
from app.services.cache import TTLCache
from app.services.geocoding import GeocodingService

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
UPSTREAM_TIMEOUT_SECONDS = 8.0
STALE_AIR_SECONDS = 2 * 60 * 60
GEO_CACHE_SECONDS = 24 * 60 * 60
HISTORY_CACHE_SECONDS = 60 * 60

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the application with middleware, routers and static files.

    Services are created at startup unless already set on ``app.state`` (tests inject fakes).
    """
    settings = settings or get_settings()
    logging.basicConfig(level=settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT_SECONDS) as http:
            state = app.state
            if not hasattr(state, "air_service"):
                state.air_service = AirQualityService(
                    http,
                    TTLCache[AirData](
                        ttl=settings.air_cache_ttl_seconds,
                        max_entries=500,
                        stale_ttl=STALE_AIR_SECONDS,
                    ),
                )
            if not hasattr(state, "grid_service"):
                state.grid_service = AirGridService(
                    http,
                    TTLCache[list[GridPoint]](
                        ttl=settings.air_cache_ttl_seconds,
                        max_entries=200,
                        stale_ttl=STALE_AIR_SECONDS,
                    ),
                )
            if not hasattr(state, "history_service"):
                state.history_service = AirHistoryService(
                    http,
                    TTLCache[list[HourlyReading]](
                        ttl=HISTORY_CACHE_SECONDS, max_entries=200, stale_ttl=STALE_AIR_SECONDS
                    ),
                )
            if not hasattr(state, "geocoding_service"):
                state.geocoding_service = GeocodingService(
                    http, TTLCache[list[Place]](ttl=GEO_CACHE_SECONDS, max_entries=1000)
                )
            if not hasattr(state, "ai"):
                state.ai = build_ai_client(settings)
            logger.info("startup ai_enabled=%s", state.ai is not None)
            yield

    app = FastAPI(
        title="Airly API",
        version=__version__,
        lifespan=lifespan,
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
        openapi_url=None if settings.is_production else "/openapi.json",
    )
    app.state.settings = settings
    app.state.limiters = build_limiters()

    register_error_handlers(app)
    add_body_limit(app)
    add_security_headers(app, production=settings.is_production)
    for router in (health.router, air.router, plan.router, chat.router, simulate.router):
        app.include_router(router)

    if STATIC_DIR.is_dir():
        app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

    return app


app = create_app()
