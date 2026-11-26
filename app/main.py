"""FastAPI application factory."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api import health
from app.config import Settings, get_settings
from app.security.headers import add_security_headers

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the application with middleware, routers and static files."""
    settings = settings or get_settings()
    logging.basicConfig(level=settings.log_level)

    app = FastAPI(
        title="BreatheWise API",
        version=__version__,
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
        openapi_url=None if settings.is_production else "/openapi.json",
    )
    add_security_headers(app, production=settings.is_production)
    app.include_router(health.router)

    if STATIC_DIR.is_dir():
        app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

    return app


app = create_app()
