"""Request and response models for the HTTP API (see docs/api.md)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.engine.aqi import AqiCategory, Pollutant
from app.engine.impact import PUBLIC_OR_ACTIVE_MODES, Mode, ScenarioId
from app.engine.risk import Advice, RiskLevel
from app.models.air import Place, Pollutants, Weather
from app.models.family import Household, Member

MAX_MEMBERS = 10
MAX_CHAT_MESSAGES = 20
MAX_CHAT_CHARS = 1000


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Location(_Strict):
    """A point on the map; rounded to 2 decimals server-side."""

    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    name: str | None = Field(default=None, max_length=120)


def _unique_member_ids(members: list[Member]) -> list[Member]:
    ids = [m.id for m in members]
    if len(ids) != len(set(ids)):
        raise ValueError("member ids must be unique")
    return members


# ---------------------------------------------------------------- air / geocode


class GeocodeResponse(BaseModel):
    """City search results."""

    results: list[Place]


class CurrentConditions(BaseModel):
    """AQI, pollutants, weather and advice for the current hour."""

    time: datetime
    aqi: int
    category: AqiCategory
    label: str
    dominant: Pollutant
    advice: Advice
    guidance: str
    pollutants: Pollutants
    weather: Weather


class ForecastHour(BaseModel):
    """AQI and outdoor advice for one forecast hour."""

    time: datetime
    aqi: int
    category: AqiCategory
    label: str
    advice: Advice


class WindowOut(BaseModel):
    """The best time window for an activity."""

    activity: str
    start: datetime
    end: datetime
    avg_aqi: int
    category: AqiCategory
    label: str
    advice: Advice
    guidance: str


class AirResponse(BaseModel):
    """Response of ``GET /api/air``: current conditions, forecast and best windows."""

    location: Location
    timezone: str
    current: CurrentConditions
    forecast: list[ForecastHour]
    best_windows: dict[str, WindowOut | None]
    stale: bool


class GridCell(BaseModel):
    """Current AQI at one point on the map."""

    lat: float
    lon: float
    aqi: int
    category: AqiCategory
    label: str
    dominant: Pollutant
    pm2_5: float | None


class HistoryDay(BaseModel):
    """Daily AQI for one day of the trend."""

    date: str  # ISO date
    label: str  # e.g. "Thu 26 Nov"
    aqi: int
    category: AqiCategory
    category_label: str
    dominant: Pollutant
    pm2_5: float | None
    complete: bool
    is_today: bool


class HistorySummary(BaseModel):
    """Totals for the trend period: average, best, worst and days per category."""

    days: int
    by_category: dict[str, int]
    average_aqi: int | None
    best: HistoryDay | None
    worst: HistoryDay | None


class HistoryResponse(BaseModel):
    """Response of ``GET /api/air/history``: daily AQI for a week or month."""

    period_days: int
    days: list[HistoryDay]
    summary: HistorySummary
    stale: bool
    note: str


class Point(_Strict):
    """A coordinate to look up on the map."""

    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class PointsRequest(_Strict):
    """Body of ``POST /api/air/points``."""

    points: list[Point] = Field(min_length=1, max_length=80)


class PointsResponse(BaseModel):
    """Current AQI per requested point, in request order (``None`` if no data)."""

    cells: list[GridCell | None]
    stale: bool


class AirGridResponse(BaseModel):
    """Response of ``GET /api/air/grid``: AQI on a grid around the location."""

    center: Location
    step_deg: float
    cells: list[GridCell]
    stale: bool
    note: str


# ---------------------------------------------------------------- plan


class PlanRequest(_Strict):
    """Body of ``POST /api/plan``: location, household and family members."""

    location: Location
    members: list[Member] = Field(min_length=1, max_length=MAX_MEMBERS)
    household: Household = Household()

    @model_validator(mode="after")
    def _check_members(self) -> PlanRequest:
        _unique_member_ids(self.members)
        return self


class RoutineItem(BaseModel):
    """One activity slot in the day plan."""

    activity: str
    start: str
    end: str
    advice: Advice
    why: str
    impact: str


class CommutePlan(BaseModel):
    """Best departure time and advice for a commute."""

    recommended_departure: str
    why: str
    alternative_mode: str
    alternative_impact: str


class SchoolSlot(BaseModel):
    """Outdoor-time advice for a school or college slot."""

    slot: str
    advice: Advice
    alternative: str


class Tip(BaseModel):
    """An indoor or sustainable tip with its reason and impact."""

    tip: str
    why: str
    impact: str


class ChecklistOut(BaseModel):
    """One protective action on a member's checklist."""

    id: str
    text: str
    reason: str


class MemberPlan(BaseModel):
    """Everything planned for one family member."""

    member_id: str
    risk_level: RiskLevel
    alerts: list[str]
    routine: list[RoutineItem]
    commute: CommutePlan | None
    school: list[SchoolSlot]
    checklist: list[ChecklistOut]


class PlanContent(BaseModel):
    """The plan body. Also the JSON schema the AI model must follow."""

    summary: str
    routine: list[RoutineItem]
    commute: CommutePlan | None
    school: list[SchoolSlot]
    indoor_tips: list[Tip]
    sustainable_choices: list[Tip]
    members: list[MemberPlan]


class PlanResponse(PlanContent):
    """Response of ``POST /api/plan``: the plan plus where it came from."""

    source: Literal["ai", "rules"]
    current: dict[str, object]
    generated_at: datetime


# ---------------------------------------------------------------- chat


class ChatMessage(_Strict):
    """One message in the chat history."""

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=MAX_CHAT_CHARS)


class ChatContext(_Strict):
    """Location and family details sent with a chat question."""

    location: Location
    members: list[Member] = Field(default_factory=list, max_length=MAX_MEMBERS)
    household: Household = Household()

    @model_validator(mode="after")
    def _check_members(self) -> ChatContext:
        _unique_member_ids(self.members)
        return self


class ChatRequest(_Strict):
    """Body of ``POST /api/chat``."""

    messages: list[ChatMessage] = Field(min_length=1, max_length=MAX_CHAT_MESSAGES)
    context: ChatContext

    @model_validator(mode="after")
    def _check_turns(self) -> ChatRequest:
        if self.messages[0].role != "user" or self.messages[-1].role != "user":
            raise ValueError("conversation must start and end with a user message")
        return self


class ChatResponse(BaseModel):
    """Response of ``POST /api/chat``: the answer and the tools it used."""

    source: Literal["ai", "rules"]
    reply: str
    tools_used: list[str]


# ---------------------------------------------------------------- simulator

PublicMode = Literal[tuple(sorted(m.value for m in PUBLIC_OR_ACTIVE_MODES))]  # type: ignore[valid-type]


class CommuteInputs(_Strict):
    """Distance and frequency of a regular trip."""

    distance_km: float = Field(gt=0, le=200)
    days_per_week: int = Field(ge=1, le=7)


class PeakInputs(CommuteInputs):
    """Inputs for moving a trip from peak to off-peak hours."""

    mode: Mode
    peak_hour: int = Field(default=9, ge=0, le=23)
    off_peak_hour: int = Field(default=11, ge=0, le=23)


class FamiliesInputs(_Strict):
    """Inputs for many families driving less."""

    families: int = Field(ge=1, le=1_000_000)
    km_per_day_reduced: float = Field(gt=0, le=200)
    days_per_week: int = Field(ge=1, le=7)
    substitute: Mode = Mode.WALK


class TreesInputs(_Strict):
    """Inputs for a community tree-planting scenario."""

    trees: int = Field(ge=1, le=100_000)
    years: int = Field(default=1, ge=1, le=20)


class PetrolToPublicInputs(CommuteInputs):
    """Inputs for switching a petrol-car commute to public or active travel."""

    to_mode: PublicMode  # type: ignore[valid-type]


class CustomSwitchInputs(CommuteInputs):
    """Inputs for switching between any two travel modes."""

    from_mode: Mode
    to_mode: Mode


class AvoidPeakRequest(_Strict):
    """Simulate travelling outside peak pollution hours."""

    scenario_id: Literal[ScenarioId.AVOID_PEAK_HOURS]
    inputs: PeakInputs
    location: Location | None = None


class FamiliesRequest(_Strict):
    """Simulate many families reducing driving."""

    scenario_id: Literal[ScenarioId.FAMILIES_REDUCE_DRIVING]
    inputs: FamiliesInputs


class TreesRequest(_Strict):
    """Simulate planting trees in the community."""

    scenario_id: Literal[ScenarioId.COMMUNITY_TREES]
    inputs: TreesInputs


class PetrolToPublicRequest(_Strict):
    """Simulate switching from a petrol car to public transport."""

    scenario_id: Literal[ScenarioId.PETROL_TO_PUBLIC]
    inputs: PetrolToPublicInputs


class CustomSwitchRequest(_Strict):
    """Simulate any commute mode switch."""

    scenario_id: Literal[ScenarioId.CUSTOM_COMMUTE_SWITCH]
    inputs: CustomSwitchInputs


SimulateRequest = Annotated[
    AvoidPeakRequest | FamiliesRequest | TreesRequest | PetrolToPublicRequest | CustomSwitchRequest,
    Field(discriminator="scenario_id"),
]


class ScenarioNumbers(BaseModel):
    """Calculated emission and exposure changes for a scenario."""

    period: str
    co2_kg: float
    pm25_g: float | None
    nox_g: float | None
    exposure_change_pct: float | None
    baseline_co2_kg: float | None


class SimulateResponse(BaseModel):
    """Response of ``POST /api/simulate``: numbers plus a plain-language explanation."""

    source: Literal["ai", "rules"]
    scenario_id: ScenarioId
    result: ScenarioNumbers
    explanation: str
    next_step: str
    assumptions: list[str]
    sources: list[str]
    disclaimer: str


class ScenarioInfo(BaseModel):
    """A scenario the simulator offers, with its description."""

    scenario_id: ScenarioId
    title: str
    description: str
    defaults: dict[str, object]


class ScenariosResponse(BaseModel):
    """Response of ``GET /api/simulate/scenarios``."""

    scenarios: list[ScenarioInfo]
    modes: list[Mode]
