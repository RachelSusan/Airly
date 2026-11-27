"""Read-only tools the AI model can call in chat. Every result comes from the engine."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.engine.facts import HouseholdFacts
from app.engine.impact import Mode, commute_switch
from app.engine.risk import Sensitivity
from app.engine.timefmt import clock, day_label
from app.engine.windows import Activity, best_window

MAX_TOOL_ROUNDS = 4

_NO_INPUT = {"type": "object", "properties": {}, "required": [], "additionalProperties": False}

TOOLS: list[dict[str, Any]] = [
    {
        "name": "get_current_conditions",
        "description": "The user's location (place name and coordinates), current AQI, "
        "category, dominant pollutant and weather, plus the cleanest and worst hours in the "
        "next 24 hours.",
        "parameters": _NO_INPUT,
    },
    {
        "name": "get_forecast_windows",
        "description": "Best time window in the next 24 hours for an activity, with advice "
        "for the most sensitive household member.",
        "parameters": {
            "type": "object",
            "properties": {
                "activity": {"type": "string", "enum": [a.value for a in Activity]},
                "duration_hours": {"type": "integer", "enum": [1, 2, 3, 4]},
            },
            "required": ["activity", "duration_hours"],
            "additionalProperties": False,
        },
    },
    {
        "name": "assess_family_risk",
        "description": "Risk level, outdoor advice, alerts and checklist for each family member.",
        "parameters": _NO_INPUT,
    },
    {
        "name": "check_ventilation",
        "description": "Whether to open windows now, the best airing time, and why.",
        "parameters": _NO_INPUT,
    },
    {
        "name": "estimate_commute_switch",
        "description": "Estimated yearly change in CO2, PM2.5 and NOx emissions from switching "
        "a regular commute between travel modes. Distance is one way.",
        "parameters": {
            "type": "object",
            "properties": {
                "from_mode": {"type": "string", "enum": [m.value for m in Mode]},
                "to_mode": {"type": "string", "enum": [m.value for m in Mode]},
                "distance_km": {"type": "number"},
                "days_per_week": {"type": "integer", "enum": [1, 2, 3, 4, 5, 6, 7]},
            },
            "required": ["from_mode", "to_mode", "distance_km", "days_per_week"],
            "additionalProperties": False,
        },
    },
]


class _WindowArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    activity: Activity
    duration_hours: int = Field(ge=1, le=4)


class _SwitchArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    from_mode: Mode
    to_mode: Mode
    distance_km: float = Field(gt=0, le=200)
    days_per_week: int = Field(ge=1, le=7)


class ToolError(Exception):
    """A tool call had invalid input or an unknown name."""


ToolHandler = Callable[[Any, HouseholdFacts], dict[str, Any]]


def _current_conditions(_raw: Any, facts: HouseholdFacts) -> dict[str, Any]:
    data = facts.data
    return {
        "location": data["location"],
        "now": data["now"],
        "weather_now": data["weather_now"],
        "forecast_summary": data["forecast_summary"],
    }


def _forecast_windows(raw: Any, facts: HouseholdFacts) -> dict[str, Any]:
    args = _WindowArgs.model_validate(raw)
    data = facts.data
    window = best_window(
        facts.series,
        args.activity,
        duration_hours=args.duration_hours,
        sensitivity=Sensitivity(data["household_sensitivity"]),
    )
    if window is None:
        return {"window": None, "note": "No suitable window in the next 24 hours."}
    return {
        "window": {
            "activity": window.activity.value,
            "day": day_label(window.start),
            "start": clock(window.start),
            "end": clock(window.end),
            "avg_aqi": window.avg_aqi,
            "category": window.category.label,
            "advice": window.advice.value,
            "guidance": window.guidance,
        },
        "jog_exposure": data["jog_exposure"] if args.activity is Activity.JOG else None,
    }


def _family_risk(_raw: Any, facts: HouseholdFacts) -> dict[str, Any]:
    return {
        "members": facts.data["members"],
        "household_sensitivity": facts.data["household_sensitivity"],
    }


def _ventilation(_raw: Any, facts: HouseholdFacts) -> dict[str, Any]:
    ventilation: dict[str, Any] = facts.data["ventilation"]
    return ventilation


def _commute_switch(raw: Any, _facts: HouseholdFacts) -> dict[str, Any]:
    args = _SwitchArgs.model_validate(raw)
    result = commute_switch(args.from_mode, args.to_mode, args.distance_km, args.days_per_week)
    return {
        "period": result.period,
        "co2_kg": result.co2_kg,
        "pm25_g": result.pm25_g,
        "nox_g": result.nox_g,
        "assumptions": list(result.assumptions),
        "disclaimer": result.disclaimer,
    }


_HANDLERS: dict[str, ToolHandler] = {
    "get_current_conditions": _current_conditions,
    "get_forecast_windows": _forecast_windows,
    "assess_family_risk": _family_risk,
    "check_ventilation": _ventilation,
    "estimate_commute_switch": _commute_switch,
}


def run_tool(name: str, raw_input: Any, facts: HouseholdFacts) -> dict[str, Any]:
    """Execute a tool against precomputed facts. Inputs are validated again here.

    Raises:
        ToolError: for an unknown tool or invalid input.
    """
    handler = _HANDLERS.get(name)
    if handler is None:
        raise ToolError(f"Unknown tool: {name}")
    try:
        return handler(raw_input, facts)
    except (ValidationError, ValueError) as exc:
        raise ToolError(f"Invalid input for {name}") from exc
