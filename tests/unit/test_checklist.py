from app.engine.aqi import AqiCategory
from app.engine.checklist import checklist_for
from app.models.family import AgeGroup, Condition, Member


def _ids(member: Member, category: AqiCategory, **kwargs: bool) -> list[str]:
    return [item.id for item in checklist_for(member, category, **kwargs)]


def test_healthy_adult_good_day_only_checks_aqi() -> None:
    assert _ids(Member(id="a", age_group=AgeGroup.ADULT), AqiCategory.GOOD) == ["check_aqi"]


def test_asthmatic_child_very_poor_day() -> None:
    member = Member(id="c", age_group=AgeGroup.CHILD, conditions=(Condition.ASTHMA,))
    ids = _ids(member, AqiCategory.VERY_POOR, has_purifier=True)
    assert ids[0] == "carry_inhaler"
    for expected in ("n95_outdoors", "exercise_indoors", "indoor_play", "run_purifier"):
        assert expected in ids
    assert "clean_air_room" not in ids


def test_sensitive_person_gets_mask_from_moderate() -> None:
    member = Member(id="s", age_group=AgeGroup.ADULT, conditions=(Condition.HEART,))
    ids = _ids(member, AqiCategory.MODERATE)
    assert "n95_outdoors" in ids
    assert "watch_symptoms" in ids


def test_no_purifier_suggests_clean_air_room() -> None:
    member = Member(id="p", age_group=AgeGroup.ADULT, conditions=(Condition.PREGNANCY,))
    ids = _ids(member, AqiCategory.POOR, has_purifier=False)
    assert "clean_air_room" in ids
    assert "limit_outdoor_time" in ids


def test_every_item_has_a_reason() -> None:
    member = Member(id="x", age_group=AgeGroup.SENIOR, conditions=(Condition.COPD,))
    assert all(item.reason for item in checklist_for(member, AqiCategory.SEVERE))
