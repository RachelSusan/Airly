"""Daily plan: Gemini phrases the verified facts; rules fallback renders them directly."""

from __future__ import annotations

import json
import logging
from typing import Literal

from pydantic import ValidationError

from app.ai import fallback
from app.ai.client import AIUnavailableError, GeminiClient
from app.ai.prompts import PLANNER_SYSTEM
from app.ai.schemas import PLAN_SCHEMA
from app.models.api import PlanContent

logger = logging.getLogger(__name__)

PLAN_MAX_TOKENS = 12_000

Source = Literal["ai", "rules"]


async def generate_plan(
    facts: dict[str, object], ai: GeminiClient | None
) -> tuple[PlanContent, Source]:
    """Return the plan and whether it came from the AI model or the rules."""
    if ai is not None:
        try:
            data = await ai.generate_json(
                system=PLANNER_SYSTEM,
                prompt="FACTS:\n" + json.dumps(facts),
                schema=PLAN_SCHEMA,
                max_tokens=PLAN_MAX_TOKENS,
            )
            plan = PlanContent.model_validate(data)
            _check_members(plan, facts)
            return plan, "ai"
        except (AIUnavailableError, ValidationError, ValueError) as exc:
            logger.warning("plan_fallback reason=%s", type(exc).__name__)
    return fallback.plan(facts), "rules"


def _check_members(plan: PlanContent, facts: dict[str, object]) -> None:
    """The model must return exactly the household's members (no invented people)."""
    members = facts.get("members")
    expected = {m["member_id"] for m in members} if isinstance(members, list) else set()
    if {m.member_id for m in plan.members} != expected:
        raise ValueError("plan members do not match the household")
