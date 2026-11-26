"""Indian National Air Quality Index (CPCB NAQI) calculation.

Each pollutant's sub-index is linearly interpolated between concentration breakpoints;
the overall AQI is the highest sub-index. See docs/impact_methodology.md, section 1.
"""

from __future__ import annotations

from bisect import bisect_left
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from app.models.air import HourlyReading

MAX_AQI = 500


class Pollutant(StrEnum):
    """Pollutant codes (match the field names of ``app.models.air.Pollutants``)."""

    PM2_5 = "pm2_5"
    PM10 = "pm10"
    NO2 = "no2"
    O3 = "o3"
    CO = "co"
    SO2 = "so2"


class AqiCategory(StrEnum):
    """NAQI categories, in increasing order of severity."""

    GOOD = "good"
    SATISFACTORY = "satisfactory"
    MODERATE = "moderate"
    POOR = "poor"
    VERY_POOR = "very_poor"
    SEVERE = "severe"

    @property
    def level(self) -> int:
        """0 (Good) to 5 (Severe), for comparisons."""
        return list(AqiCategory).index(self)

    @property
    def label(self) -> str:
        """Human-readable name, e.g. ``Very Poor``."""
        return self.value.replace("_", " ").title()


# Index values at each breakpoint: Good | Satisfactory | Moderate | Poor | Very Poor | Severe
INDEX_BREAKPOINTS: tuple[int, ...] = (0, 50, 100, 200, 300, 400, 500)

# Concentrations at the same breakpoints (CPCB). The final value extends the Severe band
# by the width of the Very Poor band, the convention used by the CPCB calculator.
CONCENTRATION_BREAKPOINTS: dict[Pollutant, tuple[float, ...]] = {
    Pollutant.PM2_5: (0, 30, 60, 90, 120, 250, 380),
    Pollutant.PM10: (0, 50, 100, 250, 350, 430, 510),
    Pollutant.NO2: (0, 40, 80, 180, 280, 400, 520),
    Pollutant.O3: (0, 50, 100, 168, 208, 748, 1288),
    Pollutant.CO: (0, 1.0, 2.0, 10, 17, 34, 51),  # mg/m³
    Pollutant.SO2: (0, 40, 80, 380, 800, 1600, 2400),
}

_CATEGORY_UPPER_BOUNDS: tuple[tuple[int, AqiCategory], ...] = (
    (50, AqiCategory.GOOD),
    (100, AqiCategory.SATISFACTORY),
    (200, AqiCategory.MODERATE),
    (300, AqiCategory.POOR),
    (400, AqiCategory.VERY_POOR),
)

PARTICULATES = (Pollutant.PM2_5, Pollutant.PM10)


class InsufficientDataError(ValueError):
    """Raised when there is not enough pollutant data to compute an AQI."""


@dataclass(frozen=True, slots=True)
class AqiResult:
    """Overall AQI with its category, dominant pollutant and each sub-index."""

    aqi: int
    category: AqiCategory
    dominant: Pollutant
    sub_indices: Mapping[Pollutant, int]


@dataclass(frozen=True, slots=True)
class AqiPoint:
    """AQI for one hour, used by the planning rules."""

    time: datetime
    aqi: int
    category: AqiCategory
    dominant: Pollutant
    pm2_5: float | None


def sub_index(pollutant: Pollutant, concentration: float) -> int:
    """Return the NAQI sub-index (0-500) for one pollutant concentration.

    Args:
        pollutant: Pollutant code.
        concentration: µg/m³ (mg/m³ for CO). Must be non-negative.

    Raises:
        ValueError: if ``concentration`` is negative.
    """
    if concentration < 0:
        raise ValueError("concentration must be non-negative")
    breaks = CONCENTRATION_BREAKPOINTS[pollutant]
    if concentration >= breaks[-1]:
        return MAX_AQI
    upper = max(1, bisect_left(breaks, concentration))
    c_lo, c_hi = breaks[upper - 1], breaks[upper]
    i_lo, i_hi = INDEX_BREAKPOINTS[upper - 1], INDEX_BREAKPOINTS[upper]
    value = i_lo + (i_hi - i_lo) * (concentration - c_lo) / (c_hi - c_lo)
    return int(value + 0.5)  # round half up


def category_for(aqi: int) -> AqiCategory:
    """Map an AQI value to its NAQI category."""
    for upper, category in _CATEGORY_UPPER_BOUNDS:
        if aqi <= upper:
            return category
    return AqiCategory.SEVERE


def compute_aqi(concentrations: Mapping[str, float | None]) -> AqiResult:
    """Compute the overall AQI from available pollutant concentrations.

    At least one particulate (PM2.5 or PM10) is required, because particulates drive
    winter smog and the CPCB method requires one.

    Raises:
        InsufficientDataError: if neither PM2.5 nor PM10 is available.
    """
    indices: dict[Pollutant, int] = {}
    for pollutant in Pollutant:
        value = concentrations.get(pollutant)
        if value is not None:
            indices[pollutant] = sub_index(pollutant, value)

    if not any(p in indices for p in PARTICULATES):
        raise InsufficientDataError("PM2.5 or PM10 is required to compute AQI")

    dominant = max(indices, key=lambda p: indices[p])
    aqi = indices[dominant]
    return AqiResult(aqi=aqi, category=category_for(aqi), dominant=dominant, sub_indices=indices)


def aqi_point(reading: HourlyReading) -> AqiPoint:
    """Compute the AQI point for one hourly reading.

    Raises:
        InsufficientDataError: if the reading lacks particulate data.
    """
    result = compute_aqi(reading.pollutants.as_mapping())
    return AqiPoint(
        time=reading.time,
        aqi=result.aqi,
        category=result.category,
        dominant=result.dominant,
        pm2_5=reading.pollutants.pm2_5,
    )


def aqi_series(readings: Sequence[HourlyReading]) -> list[AqiPoint]:
    """Compute AQI points for a forecast, skipping hours without particulate data."""
    points: list[AqiPoint] = []
    for reading in readings:
        try:
            points.append(aqi_point(reading))
        except InsufficientDataError:
            continue
    return points
