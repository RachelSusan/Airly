"""Consistent JSON error responses: ``{"error": {"code", "message", "details?"}}``."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.engine.facts import NoAirDataError
from app.services.errors import UpstreamError

logger = logging.getLogger(__name__)

UPSTREAM_MESSAGE = "Air quality data is temporarily unavailable. Please try again shortly."
_STATUS_CODES = {
    400: "bad_request",
    404: "not_found",
    405: "method_not_allowed",
    413: "payload_too_large",
    429: "rate_limited",
}


class AppError(Exception):
    """An error with a safe, user-facing message."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.headers = headers


def error_response(
    status_code: int,
    code: str,
    message: str,
    *,
    details: list[dict[str, str]] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Build the standard error body."""
    body: dict[str, object] = {"code": code, "message": message}
    if details:
        body["details"] = details
    return JSONResponse({"error": body}, status_code=status_code, headers=headers)


def register_error_handlers(app: FastAPI) -> None:
    """Attach handlers so every error uses the same shape and leaks no internals."""

    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return error_response(exc.status_code, exc.code, exc.message, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {
                "field": ".".join(str(part) for part in err.get("loc", ())[1:]),
                "message": str(err.get("msg", "Invalid value")),
            }
            for err in exc.errors()
        ]
        return error_response(422, "validation_error", "Some fields are invalid.", details=details)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _STATUS_CODES.get(exc.status_code, "http_error")
        return error_response(exc.status_code, code, str(exc.detail))

    @app.exception_handler(UpstreamError)
    async def _upstream(_: Request, exc: UpstreamError) -> JSONResponse:
        logger.warning("upstream_error detail=%s", exc)
        return error_response(503, "upstream_unavailable", UPSTREAM_MESSAGE)

    @app.exception_handler(NoAirDataError)
    async def _no_data(_: Request, exc: NoAirDataError) -> JSONResponse:
        logger.warning("no_air_data detail=%s", exc)
        return error_response(503, "upstream_unavailable", UPSTREAM_MESSAGE)

    @app.exception_handler(Exception)
    async def _unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unexpected_error type=%s", type(exc).__name__)
        return error_response(500, "internal_error", "Something went wrong. Please try again.")
