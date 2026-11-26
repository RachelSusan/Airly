"""Rules for "Should I open my windows?"."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from app.engine.aqi import AqiCategory, AqiPoint
from app.engine.timefmt import clock

STILL_AIR_KMH = 5.0  # below this, air exchange through one window is slow
AIRING_MINUTES = 15


class CookingFuel(StrEnum):
    """Household cooking fuel."""

    LPG = "lpg"
    PNG = "png"
    ELECTRIC = "electric"
    BIOMASS = "biomass"
    KEROSENE = "kerosene"


SOLID_OR_KEROSENE = frozenset({CookingFuel.BIOMASS, CookingFuel.KEROSENE})


@dataclass(frozen=True, slots=True)
class VentilationAdvice:
    """Whether to open windows now, when to air the home, and why."""

    open_windows: bool
    airing_hour: AqiPoint | None
    reason: str
    tips: tuple[str, ...]


def ventilation_advice(
    current: AqiPoint,
    forecast: Sequence[AqiPoint],
    *,
    wind_kmh: float | None = None,
    cooking_fuel: CookingFuel | None = None,
) -> VentilationAdvice:
    """Decide whether to ventilate now and suggest the cleanest airing hour."""
    tips: list[str] = []
    cleanest = min(forecast, key=lambda p: p.aqi, default=None)

    if current.category.level <= AqiCategory.SATISFACTORY.level:
        open_now = True
        reason = f"Outdoor air is {current.category.label} (AQI {current.aqi}), so airing helps."
        if wind_kmh is not None and wind_kmh < STILL_AIR_KMH:
            tips.append("The air is still. Open windows on opposite sides for a cross-breeze.")
        airing = None
    else:
        open_now = False
        reason = (
            f"Outdoor air is {current.category.label} (AQI {current.aqi}). "
            "Opening windows would let more pollution in."
        )
        airing = cleanest if cleanest and cleanest.aqi < current.aqi else None
        if airing is not None and airing.category.level <= AqiCategory.MODERATE.level:
            tips.append(
                f"Air out for about {AIRING_MINUTES} minutes around "
                f"{clock(airing.time)}, when the air is cleanest."
            )
        else:
            tips.append("Keep windows shut today and run a purifier if you have one.")

    if cooking_fuel in SOLID_OR_KEROSENE:
        tips.append(
            "Cooking with wood, dung or kerosene makes indoor smoke. Use a chimney or exhaust "
            "fan, and open the kitchen window while cooking, even on bad days."
        )
    elif not open_now:
        tips.append("Use the kitchen exhaust fan while cooking.")

    return VentilationAdvice(
        open_windows=open_now, airing_hour=airing, reason=reason, tips=tuple(tips)
    )
