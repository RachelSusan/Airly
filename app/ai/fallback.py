"""Rule-based responses used when Claude is unavailable. Same facts, plainer wording."""

from __future__ import annotations

from typing import Any

from app.engine.impact import ScenarioResult
from app.models.api import (
    ChecklistOut,
    CommutePlan,
    MemberPlan,
    PlanContent,
    RoutineItem,
    SchoolSlot,
    Tip,
)

_ACTIVITY_LABELS = {
    "walk": "Walk",
    "jog": "Jog or run",
    "cycle": "Cycle",
    "play": "Outdoor play",
    "commute": "Commute",
}
_MODE_LABELS = {
    "metro": "metro",
    "bus": "bus",
    "cycle": "cycling",
    "walk": "walking",
    "ev_2w": "an electric scooter",
}


def plan(facts: dict[str, Any]) -> PlanContent:
    """Build a complete plan directly from the facts."""
    now = facts["now"]
    routine = _routine(facts["best_windows"])
    jog = facts.get("jog_exposure")
    if jog and routine:
        for item in routine:
            if item.activity == _ACTIVITY_LABELS["jog"]:
                change = jog["change_pct"]
                verb = "cuts" if change < 0 else "raises"
                item.impact = (
                    f"{item.impact} Jogging at {jog['best_time']} instead of "
                    f"{jog['worst_time']} {verb} the PM2.5 you breathe in by about "
                    f"{abs(change):.0f}%."
                )

    return PlanContent(
        summary=(
            f"The air now is {now['category']} (AQI {now['aqi']}), mainly from "
            f"{now['dominant'].upper().replace('_', '.')}. "
            "Plan outdoor time for the cleanest hours."
        ),
        routine=routine,
        commute=_commute(facts.get("commute")),
        school=_school(facts.get("school")),
        indoor_tips=_indoor_tips(facts["ventilation"]),
        sustainable_choices=_sustainable(facts.get("commute"), facts["members"]),
        members=[
            MemberPlan(
                member_id=m["member_id"],
                risk_level=m["risk_level"],
                alerts=m["alerts"],
                routine=_routine(m.get("activity_windows") or {}),
                commute=_commute(m.get("commute")),
                school=_school(m.get("school")),
                checklist=[ChecklistOut(**item) for item in m["checklist"]],
            )
            for m in facts["members"]
        ],
    )


def _routine(windows: dict[str, Any]) -> list[RoutineItem]:
    return [
        RoutineItem(
            activity=_ACTIVITY_LABELS.get(name, name),
            start=w["start"],
            end=w["end"],
            advice=w["advice"],
            why=f"Cleanest hour for this: AQI {w['avg_aqi']} ({w['category']}).",
            impact=w["guidance"],
        )
        for name, w in windows.items()
        if w is not None
    ]


def _commute(commute: dict[str, Any] | None) -> CommutePlan | None:
    if not commute:
        return None
    window = commute.get("best_departure_window")
    best = _best_alternative(commute)
    return CommutePlan(
        recommended_departure=window["start"] if window else commute["usual_departure"],
        why=(
            f"Air along your route is cleanest around then (AQI {window['avg_aqi']})."
            if window
            else "No cleaner time near your usual departure."
        ),
        alternative_mode=_MODE_LABELS.get(best["to_mode"], best["to_mode"]) if best else "",
        alternative_impact=(
            f"Saves about {abs(best['co2_kg_per_year']):,.0f} kg CO2 a year (estimate)."
            if best
            else ""
        ),
    )


def _best_alternative(commute: dict[str, Any]) -> dict[str, Any] | None:
    options = commute.get("alternatives") or []
    return min(options, key=lambda a: a["co2_kg_per_year"], default=None)


def _school(school: dict[str, Any] | None) -> list[SchoolSlot]:
    if not school or not school.get("best_outdoor_slot"):
        return []
    slot = school["best_outdoor_slot"]
    return [
        SchoolSlot(
            slot=f"Outdoor time {slot['start']}-{slot['end']}",
            advice=slot["advice"],
            alternative="Indoor games or yoga in a closed hall" if slot["advice"] != "safe" else "",
        )
    ]


def _indoor_tips(ventilation: dict[str, Any]) -> list[Tip]:
    tips = [
        Tip(
            tip="Open the windows now"
            if ventilation["open_windows_now"]
            else "Keep windows closed",
            why=ventilation["reason"],
            impact="Keeps indoor air cleaner than outdoor air.",
        )
    ]
    tips.extend(
        Tip(tip=t, why="Based on today's air and your home.", impact="")
        for t in ventilation["tips"]
    )
    return tips


def _sustainable(commute: dict[str, Any] | None, members: list[dict[str, Any]]) -> list[Tip]:
    choices: list[Tip] = []
    trips = [("your", commute)] + [
        (f"{m.get('name') or 'This member'}'s", m.get("commute")) for m in members
    ]
    for owner, trip in trips:
        best = _best_alternative(trip) if trip else None
        if best:
            mode = _MODE_LABELS.get(best["to_mode"], best["to_mode"])
            choices.append(
                Tip(
                    tip=f"Try {mode} for {owner} commute",
                    why="Less fuel burned on the road.",
                    impact=(
                        f"About {abs(best['co2_kg_per_year']):,.0f} kg less CO2 a year (estimate)."
                    ),
                )
            )
    choices.append(
        Tip(
            tip="Combine errands into one trip and avoid idling",
            why="Short, stop-start trips burn the most fuel per km.",
            impact="Fewer exhaust emissions on your street.",
        )
    )
    choices.append(
        Tip(
            tip="Never burn leaves or rubbish",
            why="Open burning releases large amounts of smoke close to homes.",
            impact="Cleaner air for you and your neighbours.",
        )
    )
    return choices


def chat_reply(question: str, facts: dict[str, Any]) -> str:
    """Answer common questions from the facts using keyword matching."""
    q = question.lower()
    now = facts["now"]
    lead = f"The air now is {now['category']} (AQI {now['aqi']})."
    windows = facts["best_windows"]

    if any(word in q for word in ("window", "ventilat", "fresh air")):
        v = facts["ventilation"]
        answer = "Yes, open them." if v["open_windows_now"] else "Not right now."
        extra = f" Best time to air out: about {v['airing_time']}." if v["airing_time"] else ""
        return f"{answer} {v['reason']}{extra}"
    if any(word in q for word in ("kid", "child", "play", "school")):
        return f"{lead} {_window_sentence(windows.get('play'), 'outdoor play')}"
    if any(word in q for word in ("jog", "run", "exercise", "workout")):
        return f"{lead} {_window_sentence(windows.get('jog'), 'a jog')}"
    if any(word in q for word in ("walk", "outside", "outdoor")):
        return f"{lead} {_window_sentence(windows.get('walk'), 'a walk')}"
    if any(word in q for word in ("commute", "travel", "office", "drive")):
        commute = facts.get("commute")
        if commute and commute.get("best_departure_window"):
            w = commute["best_departure_window"]
            return f"{lead} The cleanest time to travel near your usual time is {w['start']}."
        return f"{lead} Add your commute in the profile for travel advice."
    if any(word in q for word in ("mask", "n95")):
        return (
            f"{lead} Outdoors, a well-fitted N95 mask filters far more fine particles "
            "than a cloth mask."
        )
    return (
        f"{lead} I can help with outdoor activities, children's play, windows, masks "
        "and commuting. Try asking one of those."
    )


def _window_sentence(window: dict[str, Any] | None, label: str) -> str:
    if window is None:
        return f"There's no suitable time for {label} in the next 24 hours; plan something indoors."
    advice = {
        "safe": "is a good time",
        "caution": "is the best time, with care",
        "avoid": "is the least bad time, but it's better to stay indoors",
    }
    return (
        f"For {label}, {window['start']}-{window['end']} {advice[window['advice']]} "
        f"(AQI {window['avg_aqi']}, {window['category']}). {window['guidance']}"
    )


def simulation_text(result: ScenarioResult) -> tuple[str, str]:
    """Template explanation and next step for a scenario result."""
    co2 = result.co2_kg
    direction = "avoids" if co2 < 0 else "adds"
    parts = [f"This change {direction} about {abs(co2):,.0f} kg of CO2 per {result.period}."]
    if result.pm25_g is not None and result.pm25_g != 0:
        trend = "fall" if result.pm25_g < 0 else "rise"
        parts.append(
            f"Fine-particle (PM2.5) emissions {trend} by about {abs(result.pm25_g):,.0f} g."
        )
    if result.exposure_change_pct is not None:
        parts.append(
            f"The PM2.5 you breathe on the way changes by about {result.exposure_change_pct}%."
        )
    parts.append("These are estimates of emissions, not a forecast of your local AQI.")
    return " ".join(parts), "Pick one day this week to try it and see how it fits your routine."
