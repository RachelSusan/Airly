from collections.abc import Callable
from datetime import timedelta

import pytest

from app.engine.aqi import AqiCategory, AqiPoint
from app.engine.risk import Advice, Sensitivity
from app.engine.windows import Activity, best_window, hourly_advice, worst_hours

Points = Callable[..., list[AqiPoint]]


def test_best_window_picks_lowest_hour(make_points: Points) -> None:
    # Hours 06..13
    points = make_points([350, 340, 320, 280, 220, 150, 140, 160], start_hour=6)
    window = best_window(points, Activity.JOG)
    assert window is not None
    assert window.start.hour == 12
    assert window.end.hour == 13
    assert window.avg_aqi == 140
    assert window.category is AqiCategory.MODERATE
    assert window.advice is Advice.CAUTION


def test_best_window_multi_hour_mean(make_points: Points) -> None:
    points = make_points([100, 300, 90, 95, 400], start_hour=8)
    window = best_window(points, Activity.WALK, duration_hours=2)
    assert window is not None
    assert (window.start.hour, window.end.hour) == (10, 12)
    assert window.avg_aqi == 93  # (90 + 95) / 2 = 92.5 -> 93


def test_best_window_ties_go_to_earliest(make_points: Points) -> None:
    points = make_points([80, 80, 80], start_hour=9)
    window = best_window(points, Activity.WALK)
    assert window is not None
    assert window.start.hour == 9


def test_best_window_respects_activity_hours(make_points: Points) -> None:
    # Cleanest air at 02:00-04:00, but play is only allowed 07:00-18:00
    values = [300, 300, 40, 40, 300, 300, 300, 250, 260]
    window = best_window(make_points(values, start_hour=0), Activity.PLAY)
    assert window is not None
    assert window.start.hour == 7


def test_best_window_custom_school_hours(make_points: Points) -> None:
    points = make_points([50] * 8 + [300] * 6 + [60] * 4, start_hour=0)
    window = best_window(points, Activity.PLAY, hours=(8, 14), sensitivity=Sensitivity.ELEVATED)
    assert window is not None
    assert 8 <= window.start.hour < 14
    assert window.advice is Advice.AVOID


def test_best_window_skips_gaps(make_points: Points) -> None:
    points = make_points([200, 60, 300], start_hour=9)
    gap = AqiPoint(
        time=points[1].time + timedelta(hours=5),
        aqi=55,
        category=AqiCategory.SATISFACTORY,
        dominant=points[1].dominant,
        pm2_5=None,
    )
    window = best_window([points[0], points[1], gap], Activity.WALK, duration_hours=2)
    assert window is not None
    assert window.start.hour == 9  # the only contiguous 2-hour block


def test_best_window_uses_sensitivity(make_points: Points) -> None:
    points = make_points([80], start_hour=10)
    standard = best_window(points, Activity.JOG)
    sensitive = best_window(points, Activity.JOG, sensitivity=Sensitivity.HIGH)
    assert standard is not None and sensitive is not None
    assert standard.advice is Advice.SAFE
    assert sensitive.advice is Advice.CAUTION


def test_best_window_none_when_nothing_fits(make_points: Points) -> None:
    assert best_window(make_points([100, 100], start_hour=0), Activity.PLAY) is None
    assert best_window([], Activity.WALK) is None


@pytest.mark.parametrize("duration", [0, 5])
def test_best_window_rejects_bad_duration(make_points: Points, duration: int) -> None:
    with pytest.raises(ValueError, match="duration_hours"):
        best_window(make_points([100], start_hour=10), Activity.WALK, duration_hours=duration)


def test_best_window_rejects_bad_hours(make_points: Points) -> None:
    with pytest.raises(ValueError, match="hours"):
        best_window(make_points([100], start_hour=10), Activity.WALK, hours=(14, 8))


def test_hourly_advice_labels_each_hour(make_points: Points) -> None:
    labels = [advice for _, advice in hourly_advice(make_points([40, 150, 450]))]
    assert labels == [Advice.SAFE, Advice.CAUTION, Advice.AVOID]


def test_worst_hours(make_points: Points) -> None:
    worst = worst_hours(make_points([100, 400, 250, 300]), count=2)
    assert [p.aqi for p in worst] == [400, 300]
