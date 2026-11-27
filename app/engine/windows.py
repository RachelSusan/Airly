"""Find the cleanest time windows for activities from an hourly AQI forecast.

See docs/impact_methodology.md, section 3.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from itertools import pairwise

from app.engine.aqi import AqiCategory, AqiPoint, category_for
from app.engine.risk import Advice, Intensity, Sensitivity, outdoor_guidance

ONE_HOUR = timedelta(hours=1)
MAX_DURATION_HOURS = 4
HOURS_PER_DAY = 24


class Activity(StrEnum):
    """Activities the planner can schedule."""

    WALK = "walk"
    JOG = "jog"
    CYCLE = "cycle"
    PLAY = "play"
    COMMUTE = "commute"


@dataclass(frozen=True, slots=True)
class ActivityProfile:
    """Intensity and allowed local hours (``earliest`` <= start, end <= ``latest``)."""

    intensity: Intensity
    earliest: int
    latest: int


ACTIVITY_PROFILES: dict[Activity, ActivityProfile] = {
    Activity.WALK: ActivityProfile(Intensity.LIGHT, earliest=6, latest=21),
    Activity.JOG: ActivityProfile(Intensity.STRENUOUS, earliest=5, latest=21),
    Activity.CYCLE: ActivityProfile(Intensity.STRENUOUS, earliest=6, latest=20),
    Activity.PLAY: ActivityProfile(Intensity.STRENUOUS, earliest=7, latest=18),
    Activity.COMMUTE: ActivityProfile(Intensity.LIGHT, earliest=5, latest=23),
}


@dataclass(frozen=True, slots=True)
class TimeWindow:
    """A recommended (or least-bad) window for an activity."""

    activity: Activity
    start: datetime
    end: datetime
    avg_aqi: int
    category: AqiCategory
    advice: Advice
    guidance: str


def best_window(
    points: Sequence[AqiPoint],
    activity: Activity,
    *,
    duration_hours: int = 1,
    sensitivity: Sensitivity = Sensitivity.STANDARD,
    hours: tuple[int, int] | None = None,
) -> TimeWindow | None:
    """Return the lowest-AQI contiguous window for an activity.

    Args:
        points: Hourly AQI points in time order.
        activity: Activity to schedule.
        duration_hours: Window length, 1-4 hours.
        sensitivity: Sensitivity of the most sensitive participant.
        hours: Optional ``(earliest, latest)`` local hours overriding the activity default,
            e.g. school hours.

    Returns:
        The best window (earliest wins ties), or ``None`` if no window fits.

    Raises:
        ValueError: for an invalid duration or hour range.
    """
    if not 1 <= duration_hours <= MAX_DURATION_HOURS:
        raise ValueError(f"duration_hours must be 1-{MAX_DURATION_HOURS}")
    profile = ACTIVITY_PROFILES[activity]
    earliest, latest = hours if hours is not None else (profile.earliest, profile.latest)
    if not 0 <= earliest < latest <= HOURS_PER_DAY:
        raise ValueError("hours must satisfy 0 <= earliest < latest <= 24")

    best: tuple[float, int] | None = None
    for start in range(len(points) - duration_hours + 1):
        window = points[start : start + duration_hours]
        if not _is_contiguous(window) or not _within_hours(window, earliest, latest):
            continue
        mean = sum(p.aqi for p in window) / duration_hours
        if best is None or mean < best[0]:
            best = (mean, start)

    if best is None:
        return None
    mean, start = best
    window = points[start : start + duration_hours]
    avg_aqi = int(mean + 0.5)
    category = category_for(avg_aqi)
    guidance = outdoor_guidance(category, sensitivity, profile.intensity)
    return TimeWindow(
        activity=activity,
        start=window[0].time,
        end=window[-1].time + ONE_HOUR,
        avg_aqi=avg_aqi,
        category=category,
        advice=guidance.advice,
        guidance=guidance.text,
    )


def hourly_advice(
    points: Sequence[AqiPoint],
    sensitivity: Sensitivity = Sensitivity.STANDARD,
    intensity: Intensity = Intensity.STRENUOUS,
) -> list[tuple[datetime, Advice]]:
    """Label every forecast hour as safe, caution or avoid."""
    return [(p.time, outdoor_guidance(p.category, sensitivity, intensity).advice) for p in points]


def worst_hours(points: Sequence[AqiPoint], count: int = 3) -> list[AqiPoint]:
    """Return the ``count`` most polluted hours, worst first."""
    return sorted(points, key=lambda p: p.aqi, reverse=True)[:count]


def _is_contiguous(window: Sequence[AqiPoint]) -> bool:
    return all(b.time - a.time == ONE_HOUR for a, b in pairwise(window))


def _within_hours(window: Sequence[AqiPoint], earliest: int, latest: int) -> bool:
    start_hour = window[0].time.hour
    end_hour = start_hour + len(window)
    return start_hour >= earliest and end_hour <= latest
