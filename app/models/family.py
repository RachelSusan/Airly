"""Family profile models (stored client-side; validated server-side per request)."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.engine.impact import Mode
from app.engine.ventilation import CookingFuel


class AgeGroup(StrEnum):
    """Age bands used for sensitivity rules."""

    INFANT = "infant"  # 0-1
    CHILD = "child"  # 2-12
    TEEN = "teen"  # 13-17
    ADULT = "adult"  # 18-64
    SENIOR = "senior"  # 65+


class Condition(StrEnum):
    """Health conditions that raise sensitivity to air pollution."""

    ASTHMA = "asthma"
    COPD = "copd"
    HEART = "heart"
    PREGNANCY = "pregnancy"
    ALLERGY = "allergy"


class Member(BaseModel):
    """One household member."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")
    name: str | None = Field(default=None, max_length=40)
    age_group: AgeGroup
    conditions: tuple[Condition, ...] = Field(default=(), max_length=5)
    outdoor_activities: tuple[
        Annotated[str, StringConstraints(max_length=20, pattern=r"^[a-z_]+$")], ...
    ] = Field(default=(), max_length=10)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Commute(_Strict):
    """Regular commute. ``distance_km`` is one way."""

    mode: Mode
    distance_km: float = Field(gt=0, le=200)
    days_per_week: int = Field(ge=1, le=7)
    depart_hour: int = Field(default=9, ge=0, le=23)


class School(_Strict):
    """School hours (local time)."""

    start_hour: int = Field(ge=5, le=12)
    end_hour: int = Field(ge=10, le=20)


class Home(_Strict):
    """Home setup that changes indoor-air advice."""

    has_purifier: bool = False
    cooking_fuel: CookingFuel = CookingFuel.LPG
    smoker_at_home: bool = False


class Household(_Strict):
    """Household lifestyle details (all optional)."""

    commute: Commute | None = None
    school: School | None = None
    home: Home = Home()
