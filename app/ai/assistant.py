"""Chat assistant: Gemini answers using read-only tools backed by the engine."""

from __future__ import annotations

import logging
from typing import Any, Literal

from app.ai import fallback
from app.ai.client import AIUnavailableError, GeminiClient
from app.ai.prompts import ASSISTANT_SYSTEM
from app.ai.tools import MAX_TOOL_ROUNDS, TOOLS, ToolError, run_tool
from app.engine.facts import HouseholdFacts
from app.models.api import ChatMessage

logger = logging.getLogger(__name__)

CHAT_MAX_TOKENS = 4096

Source = Literal["ai", "rules"]


async def answer(
    messages: list[ChatMessage], facts: HouseholdFacts, ai: GeminiClient | None
) -> tuple[str, list[str], Source]:
    """Return ``(reply, tools_used, source)``."""
    if ai is not None:
        try:
            reply, used = await ai.chat(
                system=ASSISTANT_SYSTEM,
                messages=[(m.role, m.content) for m in messages],
                tools=TOOLS,
                run_tool=lambda name, args: _run(name, args, facts),
                max_rounds=MAX_TOOL_ROUNDS,
                max_tokens=CHAT_MAX_TOKENS,
            )
            if reply:
                return reply, used, "ai"
        except AIUnavailableError as exc:
            logger.warning("chat_fallback reason=%s", exc)
    return fallback.chat_reply(messages[-1].content, facts.data), [], "rules"


def _run(name: str, args: dict[str, Any], facts: HouseholdFacts) -> dict[str, Any]:
    """Run a tool; errors are returned to the model as data, never raised."""
    try:
        return run_tool(name, args, facts)
    except ToolError as exc:
        return {"error": str(exc)}
