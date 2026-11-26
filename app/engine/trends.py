"""Daily AQI for the past week or month, from hourly modelled concentrations.

Each day's AQI uses the day's **average** concentration of each pollutant, which is closer
to the official 24-hour NAQI method than averaging hourly index values.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from statistics import fmean

from app.engine.aqi import AqiCategory, InsufficientDataError, Pollutant, compute_aqi
from app.models.air import HourlyReading

MIN_HOURS_FOR_FULL_DAY = 18


@dataclass(frozen=True, slots=True)
class DaySummary:
    """One day's air quality."""

    day: date
    aqi: int
    category: AqiCategory
    dominant: Pollutant
    pm2_5: float | None
    hours: int

    @property
    def complete(self) -> bool:
        """False when the day has too few hours of data to be representative."""
        return self.hours >= MIN_HOURS_FOR_FULL_DAY


@dataclass(frozen=True, slots=True)
class TrendSummary:
    """Counts and extremes across the period."""

    days: int
    by_category: dict[AqiCategory, int]
    best: DaySummary | None
    worst: DaySummary | None
    average_aqi: int | None


def daily_summaries(readings: Sequence[HourlyReading]) -> list[DaySummary]:
    """Group hourly readings by local date and compute each day's AQI, oldest first."""
    by_day: dict[date, list[HourlyReading]] = defaultdict(list)
    for reading in readings:
        by_day[reading.time.date()].append(reading)

    days: list[DaySummary] = []
    for day in sorted(by_day):
        hours = by_day[day]
        means: dict[str, float | None] = {}
        for pollutant in Pollutant:
            values = [
                v for r in hours if (v := r.pollutants.as_mapping().get(pollutant)) is not None
            ]
            means[pollutant.value] = fmean(values) if values else None
        try:
            result = compute_aqi(means)
        except InsufficientDataError:
            continue
        pm = means[Pollutant.PM2_5.value]
        days.append(
            DaySummary(
                day=day,
                aqi=result.aqi,
                category=result.category,
                dominant=result.dominant,
                pm2_5=round(pm, 1) if pm is not None else None,
                hours=sum(
                    1
                    for r in hours
                    if r.pollutants.pm2_5 is not None or r.pollutants.pm10 is not None
                ),
            )
        )
    return days


def summarise(days: Sequence[DaySummary]) -> TrendSummary:
    """Count days per category and find the cleanest and most polluted complete days."""
    complete = [d for d in days if d.complete]
    counts = {category: 0 for category in AqiCategory}
    for d in complete:
        counts[d.category] += 1
    return TrendSummary(
        days=len(complete),
        by_category=counts,
        best=min(complete, key=lambda d: d.aqi, default=None),
        worst=max(complete, key=lambda d: d.aqi, default=None),
        average_aqi=round(fmean(d.aqi for d in complete)) if complete else None,
    )
