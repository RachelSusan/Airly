"""Thin wrapper around the Google Gen AI SDK (Gemini) with Airly's defaults.

Every failure (network, quota, safety block, truncation, bad JSON, too many tool rounds)
becomes ``AIUnavailableError`` so callers can switch to the rules fallback in one place.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Sequence
from typing import Any, Protocol

import httpx2
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from app.config import Settings

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_MS = 30_000
BLOCKED_REASONS = frozenset(
    {
        types.FinishReason.SAFETY,
        types.FinishReason.PROHIBITED_CONTENT,
        types.FinishReason.BLOCKLIST,
        types.FinishReason.SPII,
        types.FinishReason.RECITATION,
        types.FinishReason.MALFORMED_FUNCTION_CALL,
    }
)
# Function-calling loops are driven by our code, never automatically by the SDK.
_NO_AUTO_CALLS = types.AutomaticFunctionCallingConfig(disable=True)

ToolRunner = Callable[[str, dict[str, Any]], dict[str, Any]]


class AIUnavailableError(Exception):
    """The model could not produce a usable answer; use the rules fallback."""


class ModelsAPI(Protocol):
    """The part of ``genai.Client().aio.models`` we use (lets tests inject a fake)."""

    async def generate_content(self, *, model: str, contents: Any, config: Any) -> Any: ...


class GeminiClient:
    """Calls Gemini for structured JSON answers and for tool-using chat."""

    def __init__(self, models_api: ModelsAPI, model: str) -> None:
        self._api = models_api
        self.model = model

    async def generate_json(
        self, *, system: str, prompt: str, schema: dict[str, Any], max_tokens: int
    ) -> dict[str, Any]:
        """Return a JSON object that follows ``schema``.

        Raises:
            AIUnavailableError: if the call fails or the output is not a JSON object.
        """
        config = types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=max_tokens,
            response_mime_type="application/json",
            response_json_schema=schema,
            automatic_function_calling=_NO_AUTO_CALLS,
        )
        response = await self._call(prompt, config)
        try:
            data = json.loads(text_of(response))
        except (TypeError, ValueError) as exc:
            raise AIUnavailableError("Model returned invalid JSON") from exc
        if not isinstance(data, dict):
            raise AIUnavailableError("Model returned non-object JSON")
        return data

    async def chat(
        self,
        *,
        system: str,
        messages: Sequence[tuple[str, str]],
        tools: Sequence[dict[str, Any]],
        run_tool: ToolRunner,
        max_rounds: int,
        max_tokens: int,
    ) -> tuple[str, list[str]]:
        """Answer the last user message, letting the model call ``tools`` via ``run_tool``.

        Args:
            messages: ``(role, text)`` pairs; role is ``"user"`` or ``"assistant"``.
            tools: ``{"name", "description", "parameters"}`` (JSON Schema) definitions.
            run_tool: Executes a call; returns a result dict (``{"error": ...}`` on failure).

        Returns:
            ``(reply_text, names_of_tools_used_successfully)``.

        Raises:
            AIUnavailableError: on any failure or when tool rounds are exhausted.
        """
        contents: list[Any] = [
            types.Content(
                role="user" if role == "user" else "model",
                parts=[types.Part.from_text(text=text)],
            )
            for role, text in messages
        ]
        config = types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=max_tokens,
            tools=[types.Tool(function_declarations=[_declaration(t) for t in tools])],
            automatic_function_calling=_NO_AUTO_CALLS,
        )
        used: list[str] = []
        for _ in range(max_rounds + 1):
            response = await self._call(contents, config)
            calls = response.function_calls or []
            if not calls:
                return text_of(response), used
            # Keep the model's turn exactly as returned (it carries the call ids).
            contents.append(response.candidates[0].content)
            parts = []
            for call in calls:
                result = run_tool(call.name, dict(call.args or {}))
                if "error" not in result and call.name not in used:
                    used.append(call.name)
                parts.append(types.Part.from_function_response(name=call.name, response=result))
            contents.append(types.Content(role="user", parts=parts))
        raise AIUnavailableError("Too many tool rounds")

    async def _call(self, contents: Any, config: types.GenerateContentConfig) -> Any:
        try:
            response = await self._api.generate_content(
                model=self.model, contents=contents, config=config
            )
        except (genai_errors.APIError, httpx2.HTTPError, TimeoutError, OSError) as exc:
            logger.warning("gemini_error type=%s", type(exc).__name__)
            raise AIUnavailableError("Model request failed") from exc

        candidates = getattr(response, "candidates", None) or []
        if not candidates:
            raise AIUnavailableError("Model returned no answer (prompt blocked)")
        reason = candidates[0].finish_reason
        if reason in BLOCKED_REASONS:
            raise AIUnavailableError(f"Model declined ({reason})")
        if reason == types.FinishReason.MAX_TOKENS:
            raise AIUnavailableError("Model response was cut off")
        return response


def _declaration(tool: dict[str, Any]) -> types.FunctionDeclaration:
    return types.FunctionDeclaration(
        name=tool["name"],
        description=tool["description"],
        parameters_json_schema=tool["parameters"],
    )


def text_of(response: Any) -> str:
    """Join the visible text parts of the first candidate (skipping thoughts and calls)."""
    candidates = getattr(response, "candidates", None) or []
    if not candidates or candidates[0].content is None:
        return ""
    parts = candidates[0].content.parts or []
    return "".join(
        p.text for p in parts if getattr(p, "text", None) and not getattr(p, "thought", False)
    ).strip()


def build_ai_client(settings: Settings) -> GeminiClient | None:
    """Create the client, or ``None`` when no API key is configured (rules-only mode)."""
    if not settings.ai_enabled or settings.gemini_api_key is None:
        return None
    sdk = genai.Client(
        api_key=settings.gemini_api_key.get_secret_value(),
        http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MS),
    )
    return GeminiClient(sdk.aio.models, settings.gemini_model)
