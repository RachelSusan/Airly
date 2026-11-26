from collections.abc import Callable

from app.engine.aqi import AqiPoint
from app.engine.ventilation import CookingFuel, ventilation_advice

Points = Callable[..., list[AqiPoint]]


def test_clean_air_means_open_windows(make_points: Points) -> None:
    points = make_points([45, 60, 80], start_hour=10)
    advice = ventilation_advice(points[0], points, wind_kmh=12)
    assert advice.open_windows is True
    assert advice.airing_hour is None
    assert "Good" in advice.reason
    assert advice.tips == ()


def test_still_air_suggests_cross_breeze(make_points: Points) -> None:
    points = make_points([45], start_hour=10)
    advice = ventilation_advice(points[0], points, wind_kmh=2)
    assert any("cross-breeze" in tip for tip in advice.tips)


def test_poor_air_keeps_windows_closed_with_airing_hour(make_points: Points) -> None:
    points = make_points([320, 280, 150, 260], start_hour=9)
    advice = ventilation_advice(points[0], points)
    assert advice.open_windows is False
    assert advice.airing_hour is not None
    assert advice.airing_hour.time.hour == 11
    assert any("11:00" in tip for tip in advice.tips)
    assert any("exhaust fan" in tip for tip in advice.tips)


def test_no_clean_hour_means_keep_shut(make_points: Points) -> None:
    points = make_points([420, 410, 405], start_hour=9)
    advice = ventilation_advice(points[0], points)
    assert advice.open_windows is False
    assert any("Keep windows shut" in tip for tip in advice.tips)


def test_solid_fuel_cooking_gets_extra_ventilation_tip(make_points: Points) -> None:
    points = make_points([350], start_hour=9)
    advice = ventilation_advice(points[0], points, cooking_fuel=CookingFuel.BIOMASS)
    assert any("chimney" in tip for tip in advice.tips)
