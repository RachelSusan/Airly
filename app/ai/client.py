"""Thin wrapper around the Anthropic SDK with BreatheWise's defaults and error mapping.

Every failure (network, rate limit, refusal, truncation, bad JSON) becomes
``AIUnavailableError`` so callers can switch to the rules fallback in one place.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from typing import Any, Literal, Protocol

import anthropic

from app.config import Settings

logger = logging.getLogger(__name__)

Effort = Literal["low", "medium", "high"]
FALLBACK_BETA = "server-side-fallback-2026-07-01"
REQUEST_TIMEOUT_SECONDS = 30.0
MAX_RETRIES = 2


class AIUnavailableError(Exception):
    """Claude could not produce a usable answer; use the rules fallback."""


class MessagesAPI(Protocol):
    """The part of ``AsyncAnthropic().beta.messages`` we use (lets tests inject a fake)."""

    async def create(self, **kwargs: Any) -> Any: ...


class ClaudeClient:
    """Calls Claude with consistent settings, prompt caching and refusal fallback."""

    def __init__(self, messages_api: MessagesAPI, model: str) -> None:
        self._api = messages_api
        self.model = model

    async def create(
        self,
        *,
        system: str,
        messages: Sequence[dict[str, Any]],
        max_tokens: int,
        effort: Effort,
        tools: Sequence[dict[str, Any]] | None = None,
        schema: dict[str, Any] | None = None,
    ) -> Any:
        """Send one request and return the SDK response.

        Raises:
            AIUnavailableError: on any API error, refusal or truncated output.
        """
        output_config: dict[str, Any] = {"effort": effort}
        if schema is not None:
            output_config["format"] = {"type": "json_schema", "schema": schema}
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            # Stable system prompt first, marked for caching; volatile data goes in messages.
            "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            "messages": list(messages),
            "output_config": output_config,
            "betas": [FALLBACK_BETA],
            "fallbacks": "default",
        }
        if tools:
            kwargs["tools"] = list(tools)
        try:
            response = await self._api.create(**kwargs)
        except anthropic.APIError as exc:
            logger.warning("claude_error type=%s", type(exc).__name__)
            raise AIUnavailableError("Claude request failed") from exc

        stop = getattr(response, "stop_reason", None)
        if stop == "refusal":
            raise AIUnavailableError("Claude declined this request")
        if stop == "max_tokens":
            raise AIUnavailableError("Claude response was cut off")
        return response

    async def create_json(self, **kwargs: Any) -> dict[str, Any]:
        """Like ``create`` with a JSON ``schema``; returns the parsed object.

        Raises:
            AIUnavailableError: if the call fails or the output is not a JSON object.
        """
        response = await self.create(**kwargs)
        try:
            data = json.loads(text_of(response))
        except (TypeError, ValueError) as exc:
            raise AIUnavailableError("Claude returned invalid JSON") from exc
        if not isinstance(data, dict):
            raise AIUnavailableError("Claude returned non-object JSON")
        return data


def text_of(response: Any) -> str:
    """Join the text blocks of a response (ignoring thinking and tool blocks)."""
    return "".join(
        block.text for block in getattr(response, "content", []) if block.type == "text"
    ).strip()


def build_claude_client(settings: Settings) -> ClaudeClient | None:
    """Create the client, or ``None`` when no API key is configured (rules-only mode)."""
    if not settings.ai_enabled or settings.anthropic_api_key is None:
        return None
    sdk = anthropic.AsyncAnthropic(
        api_key=settings.anthropic_api_key.get_secret_value(),
        timeout=REQUEST_TIMEOUT_SECONDS,
        max_retries=MAX_RETRIES,
    )
    return ClaudeClient(sdk.beta.messages, settings.claude_model)
