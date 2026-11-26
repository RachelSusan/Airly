"""HTTP security headers applied to every response (see docs/security.md, section 5)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

CONTENT_SECURITY_POLICY = "; ".join(
    (
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self'",
        "img-src 'self' data:",
        "connect-src 'self'",
        "font-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "frame-ancestors 'none'",
        "form-action 'self'",
    )
)

BASE_HEADERS: dict[str, str] = {
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(self), camera=(), microphone=()",
    "X-Frame-Options": "DENY",
}

HSTS_HEADER = ("Strict-Transport-Security", "max-age=31536000; includeSubDomains")


def security_headers(*, production: bool) -> dict[str, str]:
    """Return the headers to set, adding HSTS only in production (HTTPS)."""
    headers = dict(BASE_HEADERS)
    if production:
        headers[HSTS_HEADER[0]] = HSTS_HEADER[1]
    return headers


def add_security_headers(app: FastAPI, *, production: bool) -> None:
    """Register middleware that sets security headers on every response."""
    headers = security_headers(production=production)

    @app.middleware("http")
    async def _set_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        for name, value in headers.items():
            response.headers.setdefault(name, value)
        return response
