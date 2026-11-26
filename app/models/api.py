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
    results: list[Place]


class CurrentConditions(BaseModel):
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
    time: datetime
    aqi: int
    category: AqiCategory
    label: str
    advice: Advice


class WindowOut(BaseModel):
    activity: str
    start: datetime
    end: datetime
    avg_aqi: int
    category: AqiCategory
    label: str
    advice: Advice
    guidance: str


class AirResponse(BaseModel):
    location: Location
    timezone: str
    current: CurrentConditions
    forecast: list[ForecastHour]
    best_windows: dict[str, WindowOut | None]
    stale: bool


# ---------------------------------------------------------------- plan


class PlanRequest(_Strict):
    location: Location
    members: list[Member] = Field(min_length=1, max_length=MAX_MEMBERS)
    household: Household = Household()

    @model_validator(mode="after")
    def _check_members(self) -> PlanRequest:
        _unique_member_ids(self.members)
        return self


class RoutineItem(BaseModel):
    activity: str
    start: str
    end: str
    advice: Advice
    why: str
    impact: str


class CommutePlan(BaseModel):
    recommended_departure: str
    why: str
    alternative_mode: str
    alternative_impact: str


class SchoolSlot(BaseModel):
    slot: str
    advice: Advice
    alternative: str


class Tip(BaseModel):
    tip: str
    why: str
    impact: str


class ChecklistOut(BaseModel):
    id: str
    text: str
    reason: str


class MemberPlan(BaseModel):
    member_id: str
    risk_level: RiskLevel
    alerts: list[str]
    checklist: list[ChecklistOut]


class PlanContent(BaseModel):
    """The plan body. Also the JSON schema Claude must follow."""

    summary: str
    routine: list[RoutineItem]
    commute: CommutePlan | None
    school: list[SchoolSlot]
    indoor_tips: list[Tip]
    sustainable_choices: list[Tip]
    members: list[MemberPlan]


class PlanResponse(PlanContent):
    source: Literal["ai", "rules"]
    current: dict[str, object]
    generated_at: datetime


# ---------------------------------------------------------------- chat


class ChatMessage(_Strict):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=MAX_CHAT_CHARS)


class ChatContext(_Strict):
    location: Location
    members: list[Member] = Field(default_factory=list, max_length=MAX_MEMBERS)
    household: Household = Household()

    @model_validator(mode="after")
    def _check_members(self) -> ChatContext:
        _unique_member_ids(self.members)
        return self


class ChatRequest(_Strict):
    messages: list[ChatMessage] = Field(min_length=1, max_length=MAX_CHAT_MESSAGES)
    context: ChatContext

    @model_validator(mode="after")
    def _check_turns(self) -> ChatRequest:
        if self.messages[0].role != "user" or self.messages[-1].role != "user":
            raise ValueError("conversation must start and end with a user message")
        return self


class ChatResponse(BaseModel):
    source: Literal["ai", "rules"]
    reply: str
    tools_used: list[str]


# ---------------------------------------------------------------- simulator

PublicMode = Literal[tuple(sorted(m.value for m in PUBLIC_OR_ACTIVE_MODES))]  # type: ignore[valid-type]


class CommuteInputs(_Strict):
    distance_km: float = Field(gt=0, le=200)
    days_per_week: int = Field(ge=1, le=7)


class PeakInputs(CommuteInputs):
    mode: Mode
    peak_hour: int = Field(default=9, ge=0, le=23)
    off_peak_hour: int = Field(default=11, ge=0, le=23)


class FamiliesInputs(_Strict):
    families: int = Field(ge=1, le=1_000_000)
    km_per_day_reduced: float = Field(gt=0, le=200)
    days_per_week: int = Field(ge=1, le=7)
    substitute: Mode = Mode.WALK


class TreesInputs(_Strict):
    trees: int = Field(ge=1, le=100_000)
    years: int = Field(default=1, ge=1, le=20)


class PetrolToPublicInputs(CommuteInputs):
    to_mode: PublicMode  # type: ignore[valid-type]


class CustomSwitchInputs(CommuteInputs):
    from_mode: Mode
    to_mode: Mode


class AvoidPeakRequest(_Strict):
    scenario_id: Literal[ScenarioId.AVOID_PEAK_HOURS]
    inputs: PeakInputs
    location: Location | None = None


class FamiliesRequest(_Strict):
    scenario_id: Literal[ScenarioId.FAMILIES_REDUCE_DRIVING]
    inputs: FamiliesInputs


class TreesRequest(_Strict):
    scenario_id: Literal[ScenarioId.COMMUNITY_TREES]
    inputs: TreesInputs


class PetrolToPublicRequest(_Strict):
    scenario_id: Literal[ScenarioId.PETROL_TO_PUBLIC]
    inputs: PetrolToPublicInputs


class CustomSwitchRequest(_Strict):
    scenario_id: Literal[ScenarioId.CUSTOM_COMMUTE_SWITCH]
    inputs: CustomSwitchInputs


SimulateRequest = Annotated[
    AvoidPeakRequest | FamiliesRequest | TreesRequest | PetrolToPublicRequest | CustomSwitchRequest,
    Field(discriminator="scenario_id"),
]


class ScenarioNumbers(BaseModel):
    period: str
    co2_kg: float
    pm25_g: float | None
    nox_g: float | None
    exposure_change_pct: float | None


class SimulateResponse(BaseModel):
    source: Literal["ai", "rules"]
    scenario_id: ScenarioId
    result: ScenarioNumbers
    explanation: str
    next_step: str
    assumptions: list[str]
    sources: list[str]
    disclaimer: str


class ScenarioInfo(BaseModel):
    scenario_id: ScenarioId
    title: str
    description: str
    defaults: dict[str, object]


class ScenariosResponse(BaseModel):
    scenarios: list[ScenarioInfo]
    modes: list[Mode]
