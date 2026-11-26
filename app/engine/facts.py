"""Assemble the verified FACTS object for one household.

Everything here is deterministic. The AI layer receives this object (or tool results drawn
from it) and only phrases it; the rules fallback renders it directly.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from app.engine.aqi import AqiPoint, InsufficientDataError, aqi_point, aqi_series
from app.engine.checklist import checklist_for
from app.engine.exposure import BreathingActivity, exposure_change_pct, inhaled_dose_ug
from app.engine.impact import Mode, ScenarioResult, commute_switch
from app.engine.risk import Sensitivity, assess_member, sensitivity_for
from app.engine.ventilation import ventilation_advice
from app.engine.windows import Activity, TimeWindow, best_window, worst_hours
from app.models.air import AirData
from app.models.family import AgeGroup, Commute, Household, Member, School

COMMUTE_FLEX_HOURS = 2
ACTIVE_MODE_MAX_KM = 5.0
PRIVATE_MOTOR_MODES = frozenset(
    {Mode.PETROL_CAR, Mode.DIESEL_CAR, Mode.CNG_CAR, Mode.PETROL_2W, Mode.AUTO_CNG}
)
DAYTIME = (7, 19)
CHILD_AGES = frozenset({AgeGroup.INFANT, AgeGroup.CHILD})
ACTIVITY_ALIASES: dict[str, Activity] = {
    "walking": Activity.WALK,
    "walk": Activity.WALK,
    "jogging": Activity.JOG,
    "running": Activity.JOG,
    "jog": Activity.JOG,
    "cycling": Activity.CYCLE,
    "cycle": Activity.CYCLE,
    "play": Activity.PLAY,
    "sports": Activity.PLAY,
}


class NoAirDataError(ValueError):
    """Raised when the forecast has no usable hours."""


@dataclass(frozen=True, slots=True)
class HouseholdFacts:
    """Computed facts plus the AQI series used to make them."""

    current: AqiPoint
    series: list[AqiPoint]
    data: dict[str, Any]


def current_point(air: AirData, series: Sequence[AqiPoint]) -> AqiPoint:
    """AQI for now, falling back to the first forecast hour when current data is partial.

    Raises:
        NoAirDataError: if no hour has particulate data.
    """
    try:
        return aqi_point(air.current)
    except InsufficientDataError:
        if series:
            return series[0]
        raise NoAirDataError("No usable air-quality data for this location") from None


def household_sensitivity(members: Sequence[Member], *, children_only: bool = False) -> Sensitivity:
    """Highest sensitivity in the household (or among children only)."""
    pool = [
        m
        for m in members
        if not children_only or m.age_group in (AgeGroup.INFANT, AgeGroup.CHILD, AgeGroup.TEEN)
    ]
    if not pool:
        return Sensitivity.STANDARD
    return max((sensitivity_for(m.age_group, m.conditions) for m in pool), key=lambda s: s.level)


def build_facts(air: AirData, members: Sequence[Member], household: Household) -> HouseholdFacts:
    """Compute every number the planner and assistant may use.

    Raises:
        NoAirDataError: if there is no usable air-quality data.
    """
    series = aqi_series(air.forecast)
    current = current_point(air, series)
    if not series:
        series = [current]
    sensitivity = household_sensitivity(members)
    child_sensitivity = household_sensitivity(members, children_only=True)

    windows = {
        activity.value: _window(best_window(series, activity, sensitivity=sensitivity))
        for activity in (Activity.WALK, Activity.JOG, Activity.CYCLE)
    }
    windows[Activity.PLAY.value] = _window(
        best_window(series, Activity.PLAY, sensitivity=child_sensitivity)
    )

    data: dict[str, Any] = {
        "location": {"lat": air.lat, "lon": air.lon, "timezone": air.timezone},
        "now": _point(current),
        "weather_now": air.current.weather.model_dump(),
        "forecast_summary": {
            "hours": len(series),
            "cleanest": [_point(p) for p in sorted(series, key=lambda p: p.aqi)[:3]],
            "worst": [_point(p) for p in worst_hours(series)],
        },
        "household_sensitivity": sensitivity.value,
        "best_windows": windows,
        "jog_exposure": _jog_exposure(series, windows.get(Activity.JOG.value)),
        "ventilation": _ventilation(current, series, air, household),
        "members": [_member(m, current, series, household) for m in members],
        "commute": _commute(series, household.commute, sensitivity),
        "school": _school(series, household.school, child_sensitivity),
    }
    return HouseholdFacts(current=current, series=series, data=data)


def _point(point: AqiPoint) -> dict[str, Any]:
    return {
        "time": point.time.strftime("%H:%M"),
        "date": point.time.date().isoformat(),
        "aqi": point.aqi,
        "category": point.category.label,
        "dominant": point.dominant.value,
        "pm2_5": point.pm2_5,
    }


def _window(window: TimeWindow | None) -> dict[str, Any] | None:
    if window is None:
        return None
    return {
        "activity": window.activity.value,
        "start": window.start.strftime("%H:%M"),
        "end": window.end.strftime("%H:%M"),
        "avg_aqi": window.avg_aqi,
        "category": window.category.label,
        "advice": window.advice.value,
        "guidance": window.guidance,
    }


def _member(
    member: Member, current: AqiPoint, series: Sequence[AqiPoint], household: Household
) -> dict[str, Any]:
    risk = assess_member(member, current.category)
    checklist = checklist_for(member, current.category, has_purifier=household.home.has_purifier)
    activities = _member_activities(member)
    return {
        "member_id": member.id,
        "name": member.name,
        "relationship": member.relationship.value,
        "age_group": member.age_group.value,
        "conditions": [c.value for c in member.conditions],
        "sensitivity": risk.sensitivity.value,
        "risk_level": risk.risk_level.value,
        "outdoor_advice": risk.guidance.advice.value,
        "guidance": risk.guidance.text,
        "alerts": list(risk.alerts),
        "checklist": [{"id": i.id, "text": i.text, "reason": i.reason} for i in checklist],
        "activity_windows": {
            a.value: _window(best_window(series, a, sensitivity=risk.sensitivity))
            for a in activities
        },
        "commute": _commute(series, member.commute, risk.sensitivity),
        "school": _school(series, member.school, risk.sensitivity),
    }


def _member_activities(member: Member) -> list[Activity]:
    """Map a member's listed outdoor activities to plannable activities (walk by default)."""
    found: list[Activity] = []
    for name in member.outdoor_activities:
        activity = ACTIVITY_ALIASES.get(name)
        if activity and activity not in found:
            found.append(activity)
    if not found:
        found.append(Activity.PLAY if member.age_group in CHILD_AGES else Activity.WALK)
    return found


def _ventilation(
    current: AqiPoint, series: Sequence[AqiPoint], air: AirData, household: Household
) -> dict[str, Any]:
    advice = ventilation_advice(
        current,
        series,
        wind_kmh=air.current.weather.wind_kmh,
        cooking_fuel=household.home.cooking_fuel,
    )
    return {
        "open_windows_now": advice.open_windows,
        "airing_time": advice.airing_hour.time.strftime("%H:%M") if advice.airing_hour else None,
        "reason": advice.reason,
        "tips": list(advice.tips),
    }


def _jog_exposure(series: Sequence[AqiPoint], best: dict[str, Any] | None) -> dict[str, Any] | None:
    """Compare a 1-hour jog in the worst daytime hour with the best window."""
    daytime = [p for p in series if DAYTIME[0] <= p.time.hour < DAYTIME[1] and p.pm2_5]
    if not best or not daytime:
        return None
    worst = max(daytime, key=lambda p: p.pm2_5 or 0)
    best_point = next((p for p in series if p.time.strftime("%H:%M") == best["start"]), None)
    if best_point is None or not best_point.pm2_5 or not worst.pm2_5:
        return None
    old = inhaled_dose_ug(worst.pm2_5, BreathingActivity.JOG, 1)
    new = inhaled_dose_ug(best_point.pm2_5, BreathingActivity.JOG, 1)
    return {
        "worst_time": worst.time.strftime("%H:%M"),
        "worst_pm2_5": worst.pm2_5,
        "best_time": best["start"],
        "best_pm2_5": best_point.pm2_5,
        "change_pct": exposure_change_pct(old, new),
    }


def _commute(
    series: Sequence[AqiPoint], commute: Commute | None, sensitivity: Sensitivity
) -> dict[str, Any] | None:
    if commute is None:
        return None
    earliest = max(0, commute.depart_hour - COMMUTE_FLEX_HOURS)
    latest = min(24, commute.depart_hour + COMMUTE_FLEX_HOURS + 1)
    window = best_window(
        series, Activity.COMMUTE, sensitivity=sensitivity, hours=(earliest, latest)
    )
    alternatives = [
        _alternative(
            to, commute_switch(commute.mode, to, commute.distance_km, commute.days_per_week)
        )
        for to in _alternative_modes(commute.mode, commute.distance_km)
    ]
    return {
        "mode": commute.mode.value,
        "distance_km": commute.distance_km,
        "days_per_week": commute.days_per_week,
        "usual_departure": f"{commute.depart_hour:02d}:00",
        "best_departure_window": _window(window),
        "alternatives": alternatives,
    }


def _alternative_modes(mode: Mode, distance_km: float) -> list[Mode]:
    if mode not in PRIVATE_MOTOR_MODES:
        return []
    options = [Mode.METRO, Mode.BUS]
    if distance_km <= ACTIVE_MODE_MAX_KM:
        options.append(Mode.CYCLE)
    if mode is not Mode.PETROL_2W:
        options.append(Mode.EV_2W)
    return options


def _alternative(to_mode: Mode, result: ScenarioResult) -> dict[str, Any]:
    return {
        "to_mode": to_mode.value,
        "co2_kg_per_year": result.co2_kg,
        "pm25_g_per_year": result.pm25_g,
        "nox_g_per_year": result.nox_g,
    }


def _school(
    series: Sequence[AqiPoint], school: School | None, sensitivity: Sensitivity
) -> dict[str, Any] | None:
    if school is None or school.end_hour <= school.start_hour:
        return None
    window = best_window(
        series, Activity.PLAY, sensitivity=sensitivity, hours=(school.start_hour, school.end_hour)
    )
    return {
        "hours": f"{school.start_hour:02d}:00-{school.end_hour:02d}:00",
        "best_outdoor_slot": _window(window),
    }
