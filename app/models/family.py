"""Family profile models (stored client-side; validated server-side per request)."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


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
    conditions: tuple[Condition, ...] = ()
    outdoor_activities: tuple[str, ...] = Field(default=(), max_length=10)
