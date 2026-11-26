import dataclasses

import pytest

from app.engine.impact import (
    DISCLAIMER,
    EMISSION_FACTORS,
    Mode,
    ScenarioId,
    annual_commute_km,
    avoid_peak_hours,
    community_trees,
    commute_switch,
    families_reduce_driving,
    petrol_to_public,
)


def test_annual_commute_km_is_round_trip() -> None:
    assert annual_commute_km(12, 5) == 6240


def test_petrol_to_metro_matches_documented_example() -> None:
    result = petrol_to_public(Mode.METRO, distance_km=12, days_per_week=5)
    assert result.scenario_id is ScenarioId.PETROL_TO_PUBLIC
    assert result.co2_kg == -686.4
    assert result.pm25_g == -68.6
    assert result.nox_g == -374.4
    assert result.period == "year"
    assert result.baseline_co2_kg == 873.6  # 0.140 kg/km x 6,240 km before the switch


def test_petrol_to_public_rejects_private_modes() -> None:
    with pytest.raises(ValueError, match="to_mode"):
        petrol_to_public(Mode.DIESEL_CAR, 10, 5)


def test_custom_switch_can_increase_emissions() -> None:
    result = commute_switch(Mode.METRO, Mode.PETROL_CAR, 10, 5)
    assert result.co2_kg > 0


def test_families_scenario_scales_linearly() -> None:
    one = families_reduce_driving(1, 5, 5)
    thousand = families_reduce_driving(1000, 5, 5)
    assert thousand.co2_kg == pytest.approx(one.co2_kg * 1000, rel=1e-3)
    assert one.co2_kg == pytest.approx(-0.140 * 5 * 5 * 52, abs=0.1)


def test_trees_report_co2_only() -> None:
    result = community_trees(100, years=5)
    assert result.co2_kg == -10500.0
    assert result.pm25_g is None
    assert result.period == "5 years"


def test_avoid_peak_hours_with_exposure() -> None:
    result = avoid_peak_hours(Mode.PETROL_CAR, 10, 5, peak_pm25=200, off_peak_pm25=150)
    assert result.co2_kg == pytest.approx(-0.15 * 0.140 * 5200, abs=0.1)
    assert result.exposure_change_pct == -25.0


def test_avoid_peak_hours_without_forecast_has_no_exposure() -> None:
    assert avoid_peak_hours(Mode.BUS, 10, 5).exposure_change_pct is None


@pytest.mark.parametrize(
    "call",
    [
        lambda: annual_commute_km(0, 5),
        lambda: annual_commute_km(10, 8),
        lambda: families_reduce_driving(0, 5, 5),
        lambda: community_trees(200_000),
        lambda: community_trees(10, years=50),
    ],
)
def test_inputs_are_bounded(call) -> None:
    with pytest.raises(ValueError):
        call()


def test_results_never_claim_aqi_change_and_carry_disclaimer() -> None:
    results = [
        petrol_to_public(Mode.BUS, 8, 5),
        families_reduce_driving(1000, 4, 5),
        community_trees(50),
        avoid_peak_hours(Mode.PETROL_2W, 6, 6),
    ]
    for result in results:
        fields = {f.name for f in dataclasses.fields(result)}
        assert not any("aqi" in name for name in fields)
        assert result.disclaimer == DISCLAIMER
        assert result.assumptions
        assert result.sources


def test_every_mode_has_a_factor() -> None:
    assert set(EMISSION_FACTORS) == set(Mode)
