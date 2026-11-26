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
    sensitivity = sensitivity_for(member.age_group, member.conditions)
    conditions = set(member.conditions)
    level = category.level
    label = category.label
    items: list[ChecklistItem] = []

    def add(item_id: str, text: str, reason: str) -> None:
        items.append(ChecklistItem(id=item_id, text=text, reason=reason))

    if conditions & {Condition.ASTHMA, Condition.COPD} and level >= AqiCategory.MODERATE.level:
        add("carry_inhaler", "Carry your reliever inhaler", f"Breathing condition + {label} air")
    if Condition.HEART in conditions and level >= AqiCategory.MODERATE.level:
        add(
            "watch_symptoms",
            "Avoid exertion; watch for chest pain or breathlessness",
            f"Heart condition + {label} air",
        )
    if level >= AqiCategory.POOR.level or (
        sensitivity is Sensitivity.HIGH and level >= AqiCategory.MODERATE.level
    ):
        add("n95_outdoors", "Wear a well-fitted N95 mask outdoors", f"{label} air")
    if level >= AqiCategory.VERY_POOR.level:
        add("exercise_indoors", "Move exercise indoors today", f"{label} air")
    if member.age_group in (AgeGroup.INFANT, AgeGroup.CHILD) and level >= AqiCategory.POOR.level:
        add("indoor_play", "Plan indoor play", f"Children breathe more air per kg; {label} air")
    if Condition.PREGNANCY in conditions and level >= AqiCategory.POOR.level:
        add("limit_outdoor_time", "Keep time outdoors short", f"Pregnancy + {label} air")
    if level >= AqiCategory.POOR.level:
        add("windows_closed", "Keep windows closed during the worst hours", f"{label} air")
    if has_purifier and level >= AqiCategory.MODERATE.level:
        add("run_purifier", "Run the air purifier in the room you use most", f"{label} air")
    elif not has_purifier and level >= AqiCategory.POOR.level:
        add(
            "clean_air_room",
            "Pick one room as a clean-air room (doors and windows shut)",
            f"{label} air and no purifier",
        )
    add("check_aqi", "Check the AQI before going out", "Air quality changes through the day")
    return items
