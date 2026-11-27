"""Rule-based daily protection checklist for each family member."""

from __future__ import annotations

from dataclasses import dataclass

from app.engine.aqi import AqiCategory
from app.engine.risk import Sensitivity, sensitivity_for
from app.models.family import AgeGroup, Condition, Member


@dataclass(frozen=True, slots=True)
class ChecklistItem:
    """One protective action with the reason it applies."""

    id: str
    text: str
    reason: str


def checklist_for(
    member: Member, category: AqiCategory, *, has_purifier: bool = False
) -> list[ChecklistItem]:
    """Return today's checklist for one member, most important first."""
    return [
        *_health_items(member, category),
        *_activity_items(member, category),
        *_home_items(category, has_purifier=has_purifier),
        ChecklistItem(
            "check_aqi", "Check the AQI before going out", "Air quality changes through the day"
        ),
    ]


def _health_items(member: Member, category: AqiCategory) -> list[ChecklistItem]:
    """Items driven by the member's health conditions."""
    conditions = set(member.conditions)
    moderate_or_worse = category.level >= AqiCategory.MODERATE.level
    label = category.label
    items: list[ChecklistItem] = []
    if conditions & {Condition.ASTHMA, Condition.COPD} and moderate_or_worse:
        items.append(
            ChecklistItem(
                "carry_inhaler", "Carry your reliever inhaler", f"Breathing condition + {label} air"
            )
        )
    if Condition.HEART in conditions and moderate_or_worse:
        items.append(
            ChecklistItem(
                "watch_symptoms",
                "Avoid exertion; watch for chest pain or breathlessness",
                f"Heart condition + {label} air",
            )
        )
    return items


def _activity_items(member: Member, category: AqiCategory) -> list[ChecklistItem]:
    """Items about being outdoors: masks, exercise, play and time outside."""
    sensitive = sensitivity_for(member.age_group, member.conditions) is Sensitivity.HIGH
    level = category.level
    poor_or_worse = level >= AqiCategory.POOR.level
    label = category.label
    items: list[ChecklistItem] = []
    if poor_or_worse or (sensitive and level >= AqiCategory.MODERATE.level):
        items.append(
            ChecklistItem("n95_outdoors", "Wear a well-fitted N95 mask outdoors", f"{label} air")
        )
    if level >= AqiCategory.VERY_POOR.level:
        items.append(
            ChecklistItem("exercise_indoors", "Move exercise indoors today", f"{label} air")
        )
    if member.age_group in (AgeGroup.INFANT, AgeGroup.CHILD) and poor_or_worse:
        items.append(
            ChecklistItem(
                "indoor_play", "Plan indoor play", f"Children breathe more air per kg; {label} air"
            )
        )
    if Condition.PREGNANCY in member.conditions and poor_or_worse:
        items.append(
            ChecklistItem(
                "limit_outdoor_time", "Keep time outdoors short", f"Pregnancy + {label} air"
            )
        )
    return items


def _home_items(category: AqiCategory, *, has_purifier: bool) -> list[ChecklistItem]:
    """Items about keeping indoor air clean."""
    level = category.level
    poor_or_worse = level >= AqiCategory.POOR.level
    label = category.label
    items: list[ChecklistItem] = []
    if poor_or_worse:
        items.append(
            ChecklistItem(
                "windows_closed", "Keep windows closed during the worst hours", f"{label} air"
            )
        )
    if has_purifier and level >= AqiCategory.MODERATE.level:
        items.append(
            ChecklistItem(
                "run_purifier", "Run the air purifier in the room you use most", f"{label} air"
            )
        )
    elif not has_purifier and poor_or_worse:
        items.append(
            ChecklistItem(
                "clean_air_room",
                "Pick one room as a clean-air room (doors and windows shut)",
                f"{label} air and no purifier",
            )
        )
    return items
