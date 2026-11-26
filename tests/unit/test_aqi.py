from datetime import datetime

import pytest

from app.engine.aqi import (
    AqiCategory,
    InsufficientDataError,
    Pollutant,
    aqi_series,
    category_for,
    compute_aqi,
    sub_index,
)
from app.models.air import HourlyReading, Pollutants, Weather


@pytest.mark.parametrize(
    ("concentration", "expected"),
    [(0, 0), (15, 25), (30, 50), (60, 100), (90, 200), (120, 300), (250, 400), (380, 500)],
)
def test_sub_index_pm25_breakpoints(concentration: float, expected: int) -> None:
    assert sub_index(Pollutant.PM2_5, concentration) == expected


def test_sub_index_pm25_interpolates_within_band() -> None:
    # Very Poor band: 120-250 µg/m³ -> 300-400. 186 -> 300 + 66 * 100 / 130 = 350.8
    assert sub_index(Pollutant.PM2_5, 186) == 351


def test_sub_index_caps_at_500() -> None:
    assert sub_index(Pollutant.PM10, 2000) == 500


@pytest.mark.parametrize(
    ("pollutant", "concentration", "expected"),
    [
        (Pollutant.PM10, 100, 100),
        (Pollutant.NO2, 180, 200),
        (Pollutant.O3, 168, 200),
        (Pollutant.CO, 2.0, 100),
        (Pollutant.SO2, 800, 300),
    ],
)
def test_sub_index_other_pollutants(
    pollutant: Pollutant, concentration: float, expected: int
) -> None:
    assert sub_index(pollutant, concentration) == expected


def test_sub_index_rejects_negative() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        sub_index(Pollutant.PM2_5, -1)


@pytest.mark.parametrize(
    ("aqi", "category"),
    [
        (0, AqiCategory.GOOD),
        (50, AqiCategory.GOOD),
        (51, AqiCategory.SATISFACTORY),
        (100, AqiCategory.SATISFACTORY),
        (200, AqiCategory.MODERATE),
        (300, AqiCategory.POOR),
        (301, AqiCategory.VERY_POOR),
        (400, AqiCategory.VERY_POOR),
        (401, AqiCategory.SEVERE),
        (500, AqiCategory.SEVERE),
    ],
)
def test_category_for_boundaries(aqi: int, category: AqiCategory) -> None:
    assert category_for(aqi) is category


def test_compute_aqi_uses_highest_sub_index() -> None:
    result = compute_aqi({"pm2_5": 186.0, "pm10": 298.0, "no2": 64.0, "co": None})
    assert result.aqi == 351
    assert result.dominant is Pollutant.PM2_5
    assert result.category is AqiCategory.VERY_POOR
    assert Pollutant.CO not in result.sub_indices


def test_compute_aqi_requires_particulates() -> None:
    with pytest.raises(InsufficientDataError):
        compute_aqi({"no2": 50.0, "o3": 20.0})


def test_compute_aqi_accepts_pm10_only() -> None:
    assert compute_aqi({"pm10": 50.0}).aqi == 50


def test_category_label_and_level() -> None:
    assert AqiCategory.VERY_POOR.label == "Very Poor"
    assert AqiCategory.GOOD.level == 0
    assert AqiCategory.SEVERE.level == 5


def test_aqi_series_skips_hours_without_particulates() -> None:
    readings = [
        HourlyReading(
            time=datetime(2026, 11, 26, 9),
            pollutants=Pollutants(pm2_5=45.0),
            weather=Weather(),
        ),
        HourlyReading(
            time=datetime(2026, 11, 26, 10),
            pollutants=Pollutants(no2=40.0),
            weather=Weather(),
        ),
    ]
    points = aqi_series(readings)
    assert len(points) == 1
    assert points[0].aqi == 75
    assert points[0].pm2_5 == 45.0
