import pytest

from app.engine.exposure import (
    BreathingActivity,
    Protection,
    exposure_change_pct,
    inhaled_dose_ug,
)


def test_jogging_later_cuts_exposure() -> None:
    # Documented example: 7 AM PM2.5 180 vs 2 PM PM2.5 95, one-hour jog.
    morning = inhaled_dose_ug(180, BreathingActivity.JOG, 1)
    afternoon = inhaled_dose_ug(95, BreathingActivity.JOG, 1)
    assert morning == 540
    assert exposure_change_pct(morning, afternoon) == -47.2


def test_n95_reduces_dose() -> None:
    dose = inhaled_dose_ug(100, BreathingActivity.WALK, 2, Protection.N95)
    assert dose == pytest.approx(100 * 1.2 * 2 * 0.2)


@pytest.mark.parametrize(("pm", "hours"), [(-1, 1), (10, 0)])
def test_inhaled_dose_rejects_invalid(pm: float, hours: float) -> None:
    with pytest.raises(ValueError):
        inhaled_dose_ug(pm, BreathingActivity.REST, hours)


def test_exposure_change_requires_positive_baseline() -> None:
    with pytest.raises(ValueError):
        exposure_change_pct(0, 10)
