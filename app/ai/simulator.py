"""Plain-language explanation of a computed What-If result."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from typing import Literal

from app.ai import fallback
from app.ai.client import AIUnavailableError, GeminiClient
from app.ai.prompts import SIMULATOR_SYSTEM
from app.ai.schemas import SIMULATION_SCHEMA
from app.engine.impact import ScenarioResult

logger = logging.getLogger(__name__)

SIM_MAX_TOKENS = 4096

Source = Literal["ai", "rules"]


async def explain(result: ScenarioResult, ai: GeminiClient | None) -> tuple[str, str, Source]:
    """Return ``(explanation, next_step, source)``."""
    if ai is not None:
        try:
            data = await ai.generate_json(
                system=SIMULATOR_SYSTEM,
                prompt="RESULT:\n" + json.dumps(asdict(result)),
                schema=SIMULATION_SCHEMA,
                max_tokens=SIM_MAX_TOKENS,
            )
            explanation, next_step = data.get("explanation"), data.get("next_step")
            if isinstance(explanation, str) and isinstance(next_step, str) and explanation:
                return explanation, next_step, "ai"
        except AIUnavailableError as exc:
            logger.warning("simulator_fallback reason=%s", exc)
    explanation, next_step = fallback.simulation_text(result)
    return explanation, next_step, "rules"
