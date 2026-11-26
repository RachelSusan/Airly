import pytest

from app.engine.aqi import AqiCategory
from app.engine.risk import (
    Advice,
    Intensity,
    RiskLevel,
    Sensitivity,
    assess_member,
    child_outdoor_alert,
    outdoor_guidance,
    risk_level,
    sensitivity_for,
)
from app.models.family import AgeGroup, Condition, Member


@pytest.mark.parametrize(
    ("age_group", "conditions", "expected"),
    [
        (AgeGroup.ADULT, (), Sensitivity.STANDARD),
        (AgeGroup.TEEN, (), Sensitivity.STANDARD),
        (AgeGroup.CHILD, (), Sensitivity.ELEVATED),
        (AgeGroup.SENIOR, (), Sensitivity.ELEVATED),
        (AgeGroup.ADULT, (Condition.ALLERGY,), Sensitivity.ELEVATED),
        (AgeGroup.INFANT, (), Sensitivity.HIGH),
        (AgeGroup.ADULT, (Condition.ASTHMA,), Sensitivity.HIGH),
        (AgeGroup.ADULT, (Condition.PREGNANCY,), Sensitivity.HIGH),
        (AgeGroup.SENIOR, (Condition.ALLERGY,), Sensitivity.HIGH),
        (AgeGroup.CHILD, (Condition.ALLERGY, Condition.HEART), Sensitivity.HIGH),
    ],
)
def test_sensitivity_for(
    age_group: AgeGroup, conditions: tuple[Condition, ...], expected: Sensitivity
) -> None:
    assert sensitivity_for(age_group, conditions) is expected


def test_same_air_is_riskier_for_sensitive_people() -> None:
    adult = risk_level(AqiCategory.MODERATE, Sensitivity.STANDARD)
    asthmatic = risk_level(AqiCategory.MODERATE, Sensitivity.HIGH)
    assert adult is RiskLevel.MODERATE
    assert asthmatic is RiskLevel.HIGH


@pytest.mark.parametrize(
    ("category", "sensitivity", "expected"),
    [
        (AqiCategory.GOOD, Sensitivity.HIGH, RiskLevel.LOW),
        (AqiCategory.SATISFACTORY, Sensitivity.STANDARD, RiskLevel.LOW),
        (AqiCategory.VERY_POOR, Sensitivity.STANDARD, RiskLevel.HIGH),
        (AqiCategory.SEVERE, Sensitivity.STANDARD, RiskLevel.VERY_HIGH),
    ],
)
def test_risk_level_table(
    category: AqiCategory, sensitivity: Sensitivity, expected: RiskLevel
) -> None:
    assert risk_level(category, sensitivity) is expected


def test_outdoor_guidance_strenuous_vs_light() -> None:
    strenuous = outdoor_guidance(AqiCategory.POOR, Sensitivity.ELEVATED)
    light = outdoor_guidance(AqiCategory.POOR, Sensitivity.ELEVATED, Intensity.LIGHT)
    assert strenuous.advice is Advice.AVOID
    assert light.advice is Advice.CAUTION


def test_outdoor_guidance_light_on_good_day_stays_safe() -> None:
    assert (
        outdoor_guidance(AqiCategory.GOOD, Sensitivity.HIGH, Intensity.LIGHT).advice is Advice.SAFE
    )


def test_every_category_and_sensitivity_has_guidance() -> None:
    for category in AqiCategory:
        for sensitivity in Sensitivity:
            assert outdoor_guidance(category, sensitivity).text


@pytest.mark.parametrize(
    ("age_group", "sensitivity", "category", "alerted"),
    [
        (AgeGroup.CHILD, Sensitivity.HIGH, AqiCategory.MODERATE, True),
        (AgeGroup.CHILD, Sensitivity.ELEVATED, AqiCategory.MODERATE, False),
        (AgeGroup.CHILD, Sensitivity.ELEVATED, AqiCategory.POOR, True),
        (AgeGroup.INFANT, Sensitivity.HIGH, AqiCategory.SATISFACTORY, False),
        (AgeGroup.ADULT, Sensitivity.HIGH, AqiCategory.SEVERE, False),
    ],
)
def test_child_outdoor_alert_thresholds(
    age_group: AgeGroup, sensitivity: Sensitivity, category: AqiCategory, alerted: bool
) -> None:
    assert (child_outdoor_alert(age_group, sensitivity, category) is not None) is alerted


def test_child_alert_says_no_outdoor_play_when_very_poor() -> None:
    alert = child_outdoor_alert(AgeGroup.CHILD, Sensitivity.ELEVATED, AqiCategory.VERY_POOR)
    assert alert is not None
    assert "indoor play" in alert


def test_assess_member_asthmatic_child() -> None:
    member = Member(id="m_1", age_group=AgeGroup.CHILD, conditions=(Condition.ASTHMA,))
    risk = assess_member(member, AqiCategory.VERY_POOR)
    assert risk.member_id == "m_1"
    assert risk.sensitivity is Sensitivity.HIGH
    assert risk.risk_level is RiskLevel.VERY_HIGH
    assert risk.guidance.advice is Advice.AVOID
    assert len(risk.alerts) == 2


def test_assess_member_healthy_adult_good_day_has_no_alerts() -> None:
    member = Member(id="m_2", age_group=AgeGroup.ADULT)
    risk = assess_member(member, AqiCategory.GOOD)
    assert risk.alerts == ()
    assert risk.guidance.advice is Advice.SAFE
