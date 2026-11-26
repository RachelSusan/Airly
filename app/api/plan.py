"""Personalised daily plan (Smart Daily Routine Planner + Family Protection Profiles)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends

from app.ai.client import GeminiClient
from app.ai.planner import generate_plan
from app.api.deps import get_ai, get_air_service, rate_limit
from app.engine.facts import build_facts
from app.models.api import PlanRequest, PlanResponse
from app.services.air_quality import AirQualityService

router = APIRouter(prefix="/api", tags=["plan"], dependencies=[Depends(rate_limit("ai"))])


@router.post("/plan")
async def plan(
    body: PlanRequest,
    service: Annotated[AirQualityService, Depends(get_air_service)],
    ai: Annotated[GeminiClient | None, Depends(get_ai)],
) -> PlanResponse:
    """Build today's plan for the household from live data."""
    data, _ = await service.get_air_data(body.location.lat, body.location.lon)
    facts = build_facts(data, body.members, body.household, body.location.name)
    content, source = await generate_plan(facts.data, ai)
    return PlanResponse(
        **content.model_dump(),
        source=source,
        current=facts.data["now"],
        generated_at=datetime.now(UTC),
    )
