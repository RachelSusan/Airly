"""AI What-If Pollution Simulator endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends

from app.ai.client import ClaudeClient
from app.ai.simulator import explain
from app.api.deps import get_ai, get_air_service, rate_limit
from app.engine.impact import (
    Mode,
    ScenarioId,
    ScenarioResult,
    avoid_peak_hours,
    community_trees,
    commute_switch,
    families_reduce_driving,
    petrol_to_public,
)
from app.models.api import (
    AvoidPeakRequest,
    CustomSwitchRequest,
    FamiliesRequest,
    PetrolToPublicRequest,
    ScenarioInfo,
    ScenarioNumbers,
    ScenariosResponse,
    SimulateRequest,
    SimulateResponse,
    TreesRequest,
)
from app.services.air_quality import AirQualityService

router = APIRouter(prefix="/api", tags=["simulator"])

SCENARIOS: list[ScenarioInfo] = [
    ScenarioInfo(
        scenario_id=ScenarioId.PETROL_TO_PUBLIC,
        title="Switch from petrol car to public transport",
        description="Swap a regular petrol-car commute for metro, bus, cycling or walking.",
        defaults={"distance_km": 12, "days_per_week": 5, "to_mode": "metro"},
    ),
    ScenarioInfo(
        scenario_id=ScenarioId.AVOID_PEAK_HOURS,
        title="Avoid peak traffic hours",
        description="Travel outside rush hour: less fuel in free-flowing traffic, and "
        "cleaner air on the way when the forecast is lower.",
        defaults={
            "mode": "petrol_car",
            "distance_km": 12,
            "days_per_week": 5,
            "peak_hour": 9,
            "off_peak_hour": 11,
        },
    ),
    ScenarioInfo(
        scenario_id=ScenarioId.FAMILIES_REDUCE_DRIVING,
        title="1,000 families drive less",
        description="Many households replace some car km with walking, cycling or transit.",
        defaults={
            "families": 1000,
            "km_per_day_reduced": 5,
            "days_per_week": 5,
            "substitute": "walk",
        },
    ),
    ScenarioInfo(
        scenario_id=ScenarioId.COMMUNITY_TREES,
        title="Our community plants trees",
        description="CO2 absorbed by newly planted trees as they grow.",
        defaults={"trees": 500, "years": 5},
    ),
    ScenarioInfo(
        scenario_id=ScenarioId.CUSTOM_COMMUTE_SWITCH,
        title="Compare any two ways to travel",
        description="Pick your current and new mode of travel.",
        defaults={
            "from_mode": "petrol_2w",
            "to_mode": "ev_2w",
            "distance_km": 8,
            "days_per_week": 6,
        },
    ),
]


@router.get("/scenarios", dependencies=[Depends(rate_limit("read"))])
async def scenarios() -> ScenariosResponse:
    """List the preset What-If scenarios and travel modes."""
    return ScenariosResponse(scenarios=SCENARIOS, modes=list(Mode))


@router.post("/simulate", dependencies=[Depends(rate_limit("ai"))])
async def simulate(
    body: Annotated[SimulateRequest, Body()],
    service: Annotated[AirQualityService, Depends(get_air_service)],
    ai: Annotated[ClaudeClient | None, Depends(get_ai)],
) -> SimulateResponse:
    """Compute a scenario's emission changes and explain them in plain language."""
    result = await _compute(body, service)
    explanation, next_step, source = await explain(result, ai)
    return SimulateResponse(
        source=source,
        scenario_id=result.scenario_id,
        result=ScenarioNumbers(
            period=result.period,
            co2_kg=result.co2_kg,
            pm25_g=result.pm25_g,
            nox_g=result.nox_g,
            exposure_change_pct=result.exposure_change_pct,
        ),
        explanation=explanation,
        next_step=next_step,
        assumptions=list(result.assumptions),
        sources=list(result.sources),
        disclaimer=result.disclaimer,
    )


async def _compute(body: SimulateRequest, service: AirQualityService) -> ScenarioResult:
    match body:
        case PetrolToPublicRequest(inputs=i):
            return petrol_to_public(Mode(i.to_mode), i.distance_km, i.days_per_week)
        case CustomSwitchRequest(inputs=i):
            return commute_switch(i.from_mode, i.to_mode, i.distance_km, i.days_per_week)
        case FamiliesRequest(inputs=i):
            return families_reduce_driving(
                i.families, i.km_per_day_reduced, i.days_per_week, i.substitute
            )
        case TreesRequest(inputs=i):
            return community_trees(i.trees, i.years)
        case AvoidPeakRequest(inputs=i, location=loc):
            peak = off_peak = None
            if loc is not None:
                data, _ = await service.get_air_data(loc.lat, loc.lon)
                by_hour = {r.time.hour: r.pollutants.pm2_5 for r in data.forecast}
                peak, off_peak = by_hour.get(i.peak_hour), by_hour.get(i.off_peak_hour)
            return avoid_peak_hours(
                i.mode, i.distance_km, i.days_per_week, peak_pm25=peak, off_peak_pm25=off_peak
            )
    raise AssertionError("unreachable")  # pragma: no cover
