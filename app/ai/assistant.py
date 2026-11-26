"""Chat assistant: Claude answers using read-only tools backed by the engine."""

from __future__ import annotations

import json
import logging
from typing import Any, Literal

from app.ai import fallback
from app.ai.client import AIUnavailableError, ClaudeClient, text_of
from app.ai.prompts import ASSISTANT_SYSTEM
from app.ai.tools import MAX_TOOL_ROUNDS, TOOLS, ToolError, run_tool
from app.engine.facts import HouseholdFacts
from app.models.api import ChatMessage

logger = logging.getLogger(__name__)

CHAT_MAX_TOKENS = 2000

Source = Literal["ai", "rules"]


async def answer(
    messages: list[ChatMessage], facts: HouseholdFacts, ai: ClaudeClient | None
) -> tuple[str, list[str], Source]:
    """Return ``(reply, tools_used, source)``."""
    if ai is not None:
        try:
            reply, used = await _run_with_tools(messages, facts, ai)
            if reply:
                return reply, used, "ai"
        except AIUnavailableError as exc:
            logger.warning("chat_fallback reason=%s", exc)
    return fallback.chat_reply(messages[-1].content, facts.data), [], "rules"


async def _run_with_tools(
    messages: list[ChatMessage], facts: HouseholdFacts, ai: ClaudeClient
) -> tuple[str, list[str]]:
    convo: list[dict[str, Any]] = [{"role": m.role, "content": m.content} for m in messages]
    used: list[str] = []
    for _ in range(MAX_TOOL_ROUNDS + 1):
        response = await ai.create(
            system=ASSISTANT_SYSTEM,
            messages=convo,
            max_tokens=CHAT_MAX_TOKENS,
            effort="low",
            tools=TOOLS,
        )
        tool_calls = [b for b in response.content if b.type == "tool_use"]
        if response.stop_reason != "tool_use" or not tool_calls:
            return text_of(response), used
        # Pass the assistant turn back unchanged (thinking blocks included).
        convo.append({"role": "assistant", "content": response.content})
        convo.append(
            {"role": "user", "content": [_execute(call, facts, used) for call in tool_calls]}
        )
    raise AIUnavailableError("Too many tool rounds")


def _execute(call: Any, facts: HouseholdFacts, used: list[str]) -> dict[str, Any]:
    try:
        result = run_tool(call.name, call.input, facts)
    except ToolError as exc:
        return {
            "type": "tool_result",
            "tool_use_id": call.id,
            "content": str(exc),
            "is_error": True,
        }
    if call.name not in used:
        used.append(call.name)
    return {"type": "tool_result", "tool_use_id": call.id, "content": json.dumps(result)}
