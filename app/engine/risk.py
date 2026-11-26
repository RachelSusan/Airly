"""Per-member sensitivity, risk level and outdoor-activity advice.

Based on CPCB health statements per AQI category, simplified to three advice states.
See docs/impact_methodology.md, section 2.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.engine.aqi import AqiCategory
from app.models.family import AgeGroup, Condition, Member


class Sensitivity(StrEnum):
    """How strongly a person is affected by polluted air."""

    STANDARD = "standard"
    ELEVATED = "elevated"
    HIGH = "high"

    @property
    def level(self) -> int:
        """0 (standard) to 2 (high)."""
        return list(Sensitivity).index(self)


class Advice(StrEnum):
    """Advice state shown in the UI."""

    SAFE = "safe"
    CAUTION = "caution"
    AVOID = "avoid"


class Intensity(StrEnum):
    """Activity intensity. Light activity tolerates one category worse air."""

    LIGHT = "light"
    STRENUOUS = "strenuous"


class RiskLevel(StrEnum):
    """Overall risk for a person today."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


_RESPIRATORY_OR_CARDIAC = frozenset(
    {Condition.ASTHMA, Condition.COPD, Condition.HEART, Condition.PREGNANCY}
)

_C, _S = AqiCategory, Sensitivity
_A = Advice
# ADVICE[category][sensitivity] -> (advice, guidance)
ADVICE_TABLE: dict[AqiCategory, dict[Sensitivity, tuple[Advice, str]]] = {
    _C.GOOD: {
        _S.STANDARD: (_A.SAFE, "Enjoy outdoor activities."),
        _S.ELEVATED: (_A.SAFE, "Enjoy outdoor activities."),
        _S.HIGH: (_A.SAFE, "Enjoy outdoor activities."),
    },
    _C.SATISFACTORY: {
        _S.STANDARD: (_A.SAFE, "Outdoor activities are fine."),
        _S.ELEVATED: (_A.SAFE, "Outdoor activities are fine."),
        _S.HIGH: (_A.CAUTION, "Fine for most activities; take breaks during long exertion."),
    },
    _C.MODERATE: {
        _S.STANDARD: (_A.CAUTION, "Limit long or intense outdoor exertion."),
        _S.ELEVATED: (_A.CAUTION, "Keep outdoor exertion short and take breaks."),
        _S.HIGH: (_A.CAUTION, "Only short, light outdoor activity; avoid strenuous exercise."),
    },
    _C.POOR: {
        _S.STANDARD: (_A.CAUTION, "Keep outdoor activity light and short."),
        _S.ELEVATED: (_A.AVOID, "Avoid prolonged outdoor activity."),
        _S.HIGH: (_A.AVOID, "Avoid outdoor activity; stay in cleaner indoor air."),
    },
    _C.VERY_POOR: {
        _S.STANDARD: (_A.AVOID, "Avoid strenuous outdoor activity; keep trips short."),
        _S.ELEVATED: (_A.AVOID, "Avoid outdoor activity."),
        _S.HIGH: (_A.AVOID, "Stay indoors in a clean-air room."),
    },
    _C.SEVERE: {
        _S.STANDARD: (_A.AVOID, "Avoid outdoor activity."),
        _S.ELEVATED: (_A.AVOID, "Stay indoors."),
        _S.HIGH: (_A.AVOID, "Stay indoors in a clean-air room."),
    },
}


@dataclass(frozen=True, slots=True)
class Guidance:
    """Advice state plus a one-line explanation."""

    advice: Advice
    text: str


@dataclass(frozen=True, slots=True)
class MemberRisk:
    """Risk assessment for one household member."""

    member_id: str
    sensitivity: Sensitivity
    risk_level: RiskLevel
    guidance: Guidance
    alerts: tuple[str, ...]


def sensitivity_for(age_group: AgeGroup, conditions: tuple[Condition, ...] = ()) -> Sensitivity:
    """Return the sensitivity tier for an age group and set of conditions."""
    condition_set = set(conditions)
    if (
        age_group is AgeGroup.INFANT
        or condition_set & _RESPIRATORY_OR_CARDIAC
        or (age_group is AgeGroup.SENIOR and condition_set)
    ):
        return Sensitivity.HIGH
    if age_group in (AgeGroup.CHILD, AgeGroup.SENIOR) or Condition.ALLERGY in condition_set:
        return Sensitivity.ELEVATED
    return Sensitivity.STANDARD


def outdoor_guidance(
    category: AqiCategory,
    sensitivity: Sensitivity,
    intensity: Intensity = Intensity.STRENUOUS,
) -> Guidance:
    """Return outdoor-activity guidance for a category, sensitivity and intensity.

    Light activity is assessed one category less severe (never below Good).
    """
    if intensity is Intensity.LIGHT and category is not AqiCategory.GOOD:
        category = list(AqiCategory)[category.level - 1]
    advice, text = ADVICE_TABLE[category][sensitivity]
    return Guidance(advice=advice, text=text)


def risk_level(category: AqiCategory, sensitivity: Sensitivity) -> RiskLevel:
    """Combine air quality and sensitivity into an overall risk level."""
    if category is AqiCategory.GOOD:
        return RiskLevel.LOW
    score = category.level + sensitivity.level
    if score <= 1:
        return RiskLevel.LOW
    if score <= 3:
        return RiskLevel.MODERATE
    if score == 4:
        return RiskLevel.HIGH
    return RiskLevel.VERY_HIGH


def child_outdoor_alert(
    age_group: AgeGroup, sensitivity: Sensitivity, category: AqiCategory
) -> str | None:
    """Return a children's outdoor alert, or ``None`` if not needed.

    Sensitive children are alerted from Moderate; other children from Poor.
    """
    if age_group not in (AgeGroup.INFANT, AgeGroup.CHILD):
        return None
    threshold = AqiCategory.MODERATE if sensitivity is Sensitivity.HIGH else AqiCategory.POOR
    if category.level < threshold.level:
        return None
    if category.level >= AqiCategory.VERY_POOR.level:
        return "Keep outdoor play off today; plan indoor play."
    return "Limit outdoor play to short, light sessions in the cleanest hours."


def assess_member(member: Member, category: AqiCategory) -> MemberRisk:
    """Assess one member's risk and alerts for the given air-quality category."""
    sensitivity = sensitivity_for(member.age_group, member.conditions)
    alerts: list[str] = []
    child_alert = child_outdoor_alert(member.age_group, sensitivity, category)
    if child_alert:
        alerts.append(child_alert)
    if {Condition.ASTHMA, Condition.COPD} & set(
        member.conditions
    ) and category.level >= AqiCategory.MODERATE.level:
        alerts.append("Keep the reliever inhaler close and follow the action plan.")
    return MemberRisk(
        member_id=member.id,
        sensitivity=sensitivity,
        risk_level=risk_level(category, sensitivity),
        guidance=outdoor_guidance(category, sensitivity),
        alerts=tuple(alerts),
    )
