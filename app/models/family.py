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


class Relationship(StrEnum):
    """How a member relates to the person using the app."""

    SELF = "self"
    SPOUSE = "spouse"
    CHILD = "child"
    PARENT = "parent"
    GRANDPARENT = "grandparent"
    SIBLING = "sibling"
    OTHER = "other"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Commute(_Strict):
    """Regular trip to work or college. ``distance_km`` is one way."""

    mode: Mode
    distance_km: float = Field(gt=0, le=200)
    days_per_week: int = Field(ge=1, le=7)
    depart_hour: int = Field(default=9, ge=0, le=23)


class School(_Strict):
    """School or college hours (local time)."""

    start_hour: int = Field(ge=5, le=12)
    end_hour: int = Field(ge=10, le=20)


Activity = Annotated[str, StringConstraints(max_length=20, pattern=r"^[a-z_]+$")]


class Member(_Strict):
    """One family member, with their own travel and school routine."""

    id: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")
    name: str | None = Field(default=None, max_length=40)
    relationship: Relationship = Relationship.OTHER
    age_group: AgeGroup
    conditions: tuple[Condition, ...] = Field(default=(), max_length=5)
    outdoor_activities: tuple[Activity, ...] = Field(default=(), max_length=10)
    commute: Commute | None = None
    school: School | None = None


class Home(_Strict):
    """Home setup shared by the family; changes indoor-air advice."""

    has_purifier: bool = False
    cooking_fuel: CookingFuel = CookingFuel.LPG
    smoker_at_home: bool = False


class Household(_Strict):
    """Shared home details. ``commute`` and ``school`` are kept for older clients;
    per-member travel lives on each ``Member``."""

    commute: Commute | None = None
    school: School | None = None
    home: Home = Home()
