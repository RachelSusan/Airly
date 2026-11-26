"""AI Air Quality Assistant chat endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.ai.assistant import answer
from app.ai.client import GeminiClient
from app.api.deps import get_ai, get_air_service, rate_limit
from app.engine.facts import build_facts
from app.models.api import ChatRequest, ChatResponse
from app.services.air_quality import AirQualityService

router = APIRouter(prefix="/api", tags=["chat"], dependencies=[Depends(rate_limit("chat"))])


@router.post("/chat")
async def chat(
    body: ChatRequest,
    service: Annotated[AirQualityService, Depends(get_air_service)],
    ai: Annotated[GeminiClient | None, Depends(get_ai)],
) -> ChatResponse:
    """Answer a question about the air, grounded in live data for the user's location."""
    ctx = body.context
    data, _ = await service.get_air_data(ctx.location.lat, ctx.location.lon)
    facts = build_facts(data, ctx.members, ctx.household, ctx.location.name)
    reply, tools_used, source = await answer(body.messages, facts, ai)
    return ChatResponse(source=source, reply=reply, tools_used=tools_used)
