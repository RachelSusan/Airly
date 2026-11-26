"""HTTP security headers applied to every response (see docs/security.md, section 5)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

# Leaflet (map library) is loaded from unpkg pinned to one version with Subresource Integrity;
# map tiles come from OpenStreetMap. Nothing else outside our origin is allowed.
MAP_LIBRARY_ORIGIN = "https://unpkg.com"
MAP_TILE_ORIGIN = "https://tile.openstreetmap.org"

CONTENT_SECURITY_POLICY = "; ".join(
    (
        "default-src 'self'",
        f"script-src 'self' {MAP_LIBRARY_ORIGIN}",
        f"style-src 'self' {MAP_LIBRARY_ORIGIN}",
        f"img-src 'self' data: {MAP_TILE_ORIGIN} {MAP_LIBRARY_ORIGIN}",
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

# Swagger UI (development only; disabled in production) loads its assets from a CDN and
# uses an inline script, so it gets a looser policy limited to those exact sources.
DOCS_PATHS = frozenset({"/docs", "/docs/oauth2-redirect"})
DOCS_CONTENT_SECURITY_POLICY = "; ".join(
    (
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
        "style-src 'self' https://cdn.jsdelivr.net",
        "img-src 'self' data: https://fastapi.tiangolo.com",
        "connect-src 'self'",
        "object-src 'none'",
        "frame-ancestors 'none'",
    )
)


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
        if not production and request.url.path in DOCS_PATHS:
            response.headers["Content-Security-Policy"] = DOCS_CONTENT_SECURITY_POLICY
        for name, value in headers.items():
            response.headers.setdefault(name, value)
        return response
