"""Health check endpoint used by hosting platforms."""

from __future__ import annotations

from fastapi import APIRouter

from app import __version__

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Report that the service is running."""
    return {"status": "ok", "version": __version__}
