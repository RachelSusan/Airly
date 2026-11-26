from collections.abc import Callable
from datetime import datetime
from typing import Any

import pytest

from app.engine.facts import NoAirDataError, build_facts
from app.models.air import AirData, HourlyReading, Pollutants, Weather
from app.models.family import Commute, Household, Member, School
from app.services.air_quality import parse_air_data

Loader = Callable[[str], dict[str, Any]]


@pytest.fixture
def air(load_fixture: Loader) -> AirData:
    return parse_air_data(
        28.61, 77.21, load_fixture("air_quality.json"), load_fixture("weather.json")
    )


def test_build_facts_full_household(air: AirData) -> None:
    members = [
        Member(id="kid", age_group="child", conditions=("asthma",)),
        Member(id="mum", age_group="adult"),
    ]
    household = Household(
        commute=Commute(mode="petrol_car", distance_km=12, days_per_week=5, depart_hour=9),
        school=School(start_hour=8, end_hour=14),
    )
    facts = build_facts(air, members, household)
    data = facts.data

    assert data["now"]["aqi"] == 351
    assert data["household_sensitivity"] == "high"
    assert data["best_windows"]["walk"]["start"] == "10:00 AM"
    assert data["best_windows"]["walk"]["day"] == "Thu 26 Nov"
    assert data["today"] == "Thu 26 Nov"
    assert data["ventilation"]["open_windows_now"] is False
    assert [m["member_id"] for m in data["members"]] == ["kid", "mum"]
    alternatives = {a["to_mode"]: a for a in data["commute"]["alternatives"]}
    assert alternatives["metro"]["co2_kg_per_year"] == -686.4
    assert "cycle" not in alternatives  # 12 km is too far for the cycling suggestion
    assert data["school"]["best_outdoor_slot"]["start"] == "10:00 AM"
    assert data["school"]["hours"] == "8:00 AM-2:00 PM"
    assert data["jog_exposure"]["change_pct"] < 0


def test_build_facts_without_household_details(air: AirData) -> None:
    data = build_facts(air, [], Household()).data
    assert data["commute"] is None
    assert data["school"] is None
    assert data["members"] == []
    assert data["household_sensitivity"] == "standard"


def test_current_falls_back_to_forecast_when_partial(air: AirData) -> None:
    partial = air.model_copy(
        update={
            "current": HourlyReading(
                time=datetime(2026, 11, 26, 9), pollutants=Pollutants(no2=10), weather=Weather()
            )
        }
    )
    assert build_facts(partial, [], Household()).current.aqi == 351


def test_no_usable_data_raises() -> None:
    empty = AirData(
        lat=0,
        lon=0,
        timezone="UTC",
        current=HourlyReading(
            time=datetime(2026, 1, 1), pollutants=Pollutants(), weather=Weather()
        ),
        forecast=[],
    )
    with pytest.raises(NoAirDataError):
        build_facts(empty, [], Household())
