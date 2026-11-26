"""Emission factors and What-If scenario calculations.

Reports **estimated emission changes** (and exposure changes where live data allows).
It never predicts changes in local AQI. See docs/impact_methodology.md, sections 5-7.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

WEEKS_PER_YEAR = 52
ROUND_TRIP = 2
TREE_CO2_KG_PER_YEAR = 21.0
OFF_PEAK_FUEL_SAVING = 0.15
AUTO_OCCUPANCY = 1.5

DISCLAIMER = (
    "These are estimated emission changes. They do not predict changes in your local AQI, "
    "which depends on weather and many other sources."
)


class Mode(StrEnum):
    """Ways of travelling."""

    WALK = "walk"
    CYCLE = "cycle"
    PETROL_CAR = "petrol_car"
    DIESEL_CAR = "diesel_car"
    CNG_CAR = "cng_car"
    EV_CAR = "ev_car"
    PETROL_2W = "petrol_2w"
    EV_2W = "ev_2w"
    AUTO_CNG = "auto_cng"
    BUS = "bus"
    METRO = "metro"
    WFH = "wfh"


class ScenarioId(StrEnum):
    """Preset What-If scenarios."""

    AVOID_PEAK_HOURS = "avoid_peak_hours"
    FAMILIES_REDUCE_DRIVING = "families_reduce_driving"
    COMMUNITY_TREES = "community_trees"
    PETROL_TO_PUBLIC = "petrol_to_public"
    CUSTOM_COMMUTE_SWITCH = "custom_commute_switch"


@dataclass(frozen=True, slots=True)
class EmissionFactor:
    """Emissions per person-km travelled."""

    co2_kg: float
    pm25_g: float
    nox_g: float
    basis: str


GRID_KG_CO2_PER_KWH = 0.79  # CEA CO2 Baseline Database, Indian grid weighted average (FY 2019-20)

# CO2 per km, checked November 2026 (details and confidence in docs/impact_methodology.md):
# - Combustion cars, two-wheelers and autos: India GHG Program (2015) factors where confirmed,
#   otherwise fuel CO2 content from the same report (petrol 2.27 kg/L, diesel 2.64 kg/L,
#   CNG 2.69 kg/kg) divided by typical real-world fuel economy.
# - Bus: TERI (29.5 g CO2 per passenger-km). Metro and electric vehicles: estimates from the
#   grid factor above. PM2.5 and NOx: BS-VI type-approval limits plus non-exhaust estimates.
EMISSION_FACTORS: dict[Mode, EmissionFactor] = {
    Mode.PETROL_CAR: EmissionFactor(0.140, 0.012, 0.060, "petrol car, single occupant"),
    Mode.DIESEL_CAR: EmissionFactor(0.150, 0.015, 0.080, "diesel car, single occupant"),
    Mode.CNG_CAR: EmissionFactor(0.120, 0.010, 0.050, "CNG car, single occupant"),
    Mode.EV_CAR: EmissionFactor(
        round(0.15 * GRID_KG_CO2_PER_KWH, 3), 0.008, 0.0, "electric car, grid electricity"
    ),
    Mode.PETROL_2W: EmissionFactor(0.036, 0.006, 0.060, "petrol two-wheeler"),
    Mode.EV_2W: EmissionFactor(
        round(0.03 * GRID_KG_CO2_PER_KWH, 3), 0.003, 0.0, "electric two-wheeler, grid electricity"
    ),
    Mode.AUTO_CNG: EmissionFactor(
        round(0.100 / AUTO_OCCUPANCY, 4),
        round(0.008 / AUTO_OCCUPANCY, 4),
        round(0.050 / AUTO_OCCUPANCY, 4),
        f"CNG auto-rickshaw shared by {AUTO_OCCUPANCY} passengers",
    ),
    Mode.BUS: EmissionFactor(0.030, 0.002, 0.050, "bus, per passenger"),
    Mode.METRO: EmissionFactor(0.030, 0.001, 0.0, "metro, per passenger, grid electricity"),
    Mode.WALK: EmissionFactor(0.0, 0.0, 0.0, "walking"),
    Mode.CYCLE: EmissionFactor(0.0, 0.0, 0.0, "cycling"),
    Mode.WFH: EmissionFactor(0.0, 0.0, 0.0, "no trip (work from home)"),
}

PUBLIC_OR_ACTIVE_MODES = frozenset({Mode.BUS, Mode.METRO, Mode.CYCLE, Mode.WALK, Mode.EV_2W})

SOURCES: tuple[str, ...] = (
    "India GHG Program / WRI: India Specific Road Transport Emission Factors (2015)",
    "Central Electricity Authority: CO2 Baseline Database for the Indian Power Sector",
    "TERI: per-passenger emissions by mode in Delhi; BS-VI type-approval limits (MoRTH)",
)
TREE_SOURCE = "Common estimate of ~21 kg CO2 absorbed per mature tree per year"


@dataclass(frozen=True, slots=True)
class ScenarioResult:
    """Outcome of a What-If scenario over one year. Negative values are reductions."""

    scenario_id: ScenarioId
    co2_kg: float
    pm25_g: float | None
    nox_g: float | None
    exposure_change_pct: float | None = None
    baseline_co2_kg: float | None = None  # emissions before the change, for comparison charts
    period: str = "year"
    assumptions: tuple[str, ...] = ()
    sources: tuple[str, ...] = field(default=SOURCES)
    disclaimer: str = DISCLAIMER


def _check_range(name: str, value: float, low: float, high: float) -> None:
    if not low <= value <= high:
        raise ValueError(f"{name} must be between {low} and {high}")


def annual_commute_km(distance_km: float, days_per_week: int) -> float:
    """Yearly round-trip distance for a one-way commute distance."""
    _check_range("distance_km", distance_km, 0.1, 200)
    _check_range("days_per_week", days_per_week, 1, 7)
    return distance_km * ROUND_TRIP * days_per_week * WEEKS_PER_YEAR


def _factor_line(mode: Mode) -> str:
    f = EMISSION_FACTORS[mode]
    return f"{f.basis}: {f.co2_kg} kg CO2, {f.pm25_g} g PM2.5, {f.nox_g} g NOx per km"


def commute_switch(
    from_mode: Mode,
    to_mode: Mode,
    distance_km: float,
    days_per_week: int,
    scenario_id: ScenarioId = ScenarioId.CUSTOM_COMMUTE_SWITCH,
) -> ScenarioResult:
    """Change in yearly emissions from switching a regular commute between modes."""
    km = annual_commute_km(distance_km, days_per_week)
    old, new = EMISSION_FACTORS[from_mode], EMISSION_FACTORS[to_mode]
    return ScenarioResult(
        scenario_id=scenario_id,
        co2_kg=round((new.co2_kg - old.co2_kg) * km, 1),
        pm25_g=round((new.pm25_g - old.pm25_g) * km, 1),
        nox_g=round((new.nox_g - old.nox_g) * km, 1),
        baseline_co2_kg=round(old.co2_kg * km, 1),
        assumptions=(
            f"{distance_km} km each way, {days_per_week} days a week, "
            f"{WEEKS_PER_YEAR} weeks a year ({km:,.0f} km)",
            _factor_line(from_mode),
            _factor_line(to_mode),
        ),
    )


def petrol_to_public(to_mode: Mode, distance_km: float, days_per_week: int) -> ScenarioResult:
    """Switch a petrol-car commute to public transport, cycling, walking or an EV scooter.

    Raises:
        ValueError: if ``to_mode`` is not a public or active mode.
    """
    if to_mode not in PUBLIC_OR_ACTIVE_MODES:
        raise ValueError(f"to_mode must be one of {sorted(PUBLIC_OR_ACTIVE_MODES)}")
    return commute_switch(
        Mode.PETROL_CAR, to_mode, distance_km, days_per_week, ScenarioId.PETROL_TO_PUBLIC
    )


def families_reduce_driving(
    families: int,
    km_per_day_reduced: float,
    days_per_week: int,
    substitute: Mode = Mode.WALK,
) -> ScenarioResult:
    """Yearly change if many families replace some petrol-car km with another mode."""
    _check_range("families", families, 1, 1_000_000)
    _check_range("km_per_day_reduced", km_per_day_reduced, 0.1, 200)
    _check_range("days_per_week", days_per_week, 1, 7)
    km = families * km_per_day_reduced * days_per_week * WEEKS_PER_YEAR
    old, new = EMISSION_FACTORS[Mode.PETROL_CAR], EMISSION_FACTORS[substitute]
    return ScenarioResult(
        scenario_id=ScenarioId.FAMILIES_REDUCE_DRIVING,
        co2_kg=round((new.co2_kg - old.co2_kg) * km, 1),
        pm25_g=round((new.pm25_g - old.pm25_g) * km, 1),
        nox_g=round((new.nox_g - old.nox_g) * km, 1),
        baseline_co2_kg=round(old.co2_kg * km, 1),
        assumptions=(
            f"{families:,} families each drive {km_per_day_reduced} km less a day, "
            f"{days_per_week} days a week ({km:,.0f} km a year in total)",
            _factor_line(Mode.PETROL_CAR),
            _factor_line(substitute),
        ),
    )


def community_trees(trees: int, years: int = 1) -> ScenarioResult:
    """CO2 absorbed by planted trees. PM2.5 removal is too variable to quantify."""
    _check_range("trees", trees, 1, 100_000)
    _check_range("years", years, 1, 20)
    return ScenarioResult(
        scenario_id=ScenarioId.COMMUNITY_TREES,
        co2_kg=round(-trees * TREE_CO2_KG_PER_YEAR * years, 1),
        pm25_g=None,
        nox_g=None,
        period=f"{years} year{'s' if years > 1 else ''}",
        assumptions=(
            f"{TREE_CO2_KG_PER_YEAR} kg CO2 per mature tree per year; young trees absorb less",
            "Trees also trap some dust and particles, but the amount varies too much with "
            "species and placement to give a number",
        ),
        sources=(TREE_SOURCE,),
    )


def avoid_peak_hours(
    mode: Mode,
    distance_km: float,
    days_per_week: int,
    *,
    peak_pm25: float | None = None,
    off_peak_pm25: float | None = None,
) -> ScenarioResult:
    """Emission and exposure change from commuting outside peak traffic.

    Exposure change is computed only when forecast PM2.5 for both times is supplied.
    """
    km = annual_commute_km(distance_km, days_per_week)
    factor = EMISSION_FACTORS[mode]
    exposure: float | None = None
    assumptions = [
        f"About {OFF_PEAK_FUEL_SAVING:.0%} less fuel used in free-flowing traffic",
        f"{distance_km} km each way, {days_per_week} days a week ({km:,.0f} km a year)",
        _factor_line(mode),
    ]
    if peak_pm25 is not None and off_peak_pm25 is not None and peak_pm25 > 0:
        exposure = round((off_peak_pm25 - peak_pm25) / peak_pm25 * 100, 1)
        assumptions.append(
            f"Forecast PM2.5: {peak_pm25:g} µg/m³ at peak vs {off_peak_pm25:g} µg/m³ off-peak"
        )
    return ScenarioResult(
        scenario_id=ScenarioId.AVOID_PEAK_HOURS,
        co2_kg=round(-OFF_PEAK_FUEL_SAVING * factor.co2_kg * km, 1),
        pm25_g=round(-OFF_PEAK_FUEL_SAVING * factor.pm25_g * km, 1),
        nox_g=round(-OFF_PEAK_FUEL_SAVING * factor.nox_g * km, 1),
        exposure_change_pct=exposure,
        baseline_co2_kg=round(factor.co2_kg * km, 1),
        assumptions=tuple(assumptions),
    )
