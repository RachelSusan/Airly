"""Reject oversized request bodies early (see docs/security.md, section 3)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

from app.api.errors import error_response

MAX_BODY_BYTES = 32 * 1024


def add_body_limit(app: FastAPI, max_bytes: int = MAX_BODY_BYTES) -> None:
    """Return 413 when Content-Length exceeds ``max_bytes``; require a length on POST."""

    @app.middleware("http")
    async def _limit(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.method in {"POST", "PUT", "PATCH"}:
            length = request.headers.get("content-length")
            if length is None or not length.isdigit():
                return error_response(411, "length_required", "Content-Length is required.")
            if int(length) > max_bytes:
                return error_response(413, "payload_too_large", "Request body is too large.")
        return await call_next(request)
