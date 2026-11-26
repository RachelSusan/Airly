"""Read-only tools the AI model can call in chat. Every result comes from the engine."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.engine.facts import HouseholdFacts
from app.engine.impact import Mode, commute_switch
from app.engine.risk import Sensitivity
from app.engine.windows import Activity, best_window

MAX_TOOL_ROUNDS = 4

_NO_INPUT = {"type": "object", "properties": {}, "required": [], "additionalProperties": False}

TOOLS: list[dict[str, Any]] = [
    {
        "name": "get_current_conditions",
        "description": "Current AQI, category, dominant pollutant and weather at the user's "
        "location, plus the cleanest and worst hours in the next 24 hours.",
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


def run_tool(name: str, raw_input: Any, facts: HouseholdFacts) -> dict[str, Any]:
    """Execute a tool against precomputed facts. Inputs are validated again here.

    Raises:
        ToolError: for an unknown tool or invalid input.
    """
    data = facts.data
    try:
        if name == "get_current_conditions":
            return {
                "now": data["now"],
                "weather_now": data["weather_now"],
                "forecast_summary": data["forecast_summary"],
            }
        if name == "get_forecast_windows":
            args = _WindowArgs.model_validate(raw_input)
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
                    "start": window.start.strftime("%H:%M"),
                    "end": window.end.strftime("%H:%M"),
                    "avg_aqi": window.avg_aqi,
                    "category": window.category.label,
                    "advice": window.advice.value,
                    "guidance": window.guidance,
                },
                "jog_exposure": data["jog_exposure"] if args.activity is Activity.JOG else None,
            }
        if name == "assess_family_risk":
            return {
                "members": data["members"],
                "household_sensitivity": data["household_sensitivity"],
            }
        if name == "check_ventilation":
            return data["ventilation"]
        if name == "estimate_commute_switch":
            args = _SwitchArgs.model_validate(raw_input)
            result = commute_switch(
                args.from_mode, args.to_mode, args.distance_km, args.days_per_week
            )
            return {
                "period": result.period,
                "co2_kg": result.co2_kg,
                "pm25_g": result.pm25_g,
                "nox_g": result.nox_g,
                "assumptions": list(result.assumptions),
                "disclaimer": result.disclaimer,
            }
    except (ValidationError, ValueError) as exc:
        raise ToolError(f"Invalid input for {name}") from exc
    raise ToolError(f"Unknown tool: {name}")
