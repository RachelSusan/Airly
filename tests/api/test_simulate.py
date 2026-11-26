import json
from collections.abc import Callable

from fastapi.testclient import TestClient

from tests.api.conftest import LOCATION, FakeModels, text_response

MakeClient = Callable[..., TestClient]


def test_scenarios_lists_presets(make_client: MakeClient) -> None:
    data = make_client().get("/api/scenarios").json()
    ids = {s["scenario_id"] for s in data["scenarios"]}
    assert ids == {
        "avoid_peak_hours",
        "families_reduce_driving",
        "community_trees",
        "petrol_to_public",
        "custom_commute_switch",
    }
    assert "metro" in data["modes"]


def test_petrol_to_public_rules(make_client: MakeClient) -> None:
    body = {
        "scenario_id": "petrol_to_public",
        "inputs": {"distance_km": 12, "days_per_week": 5, "to_mode": "metro"},
    }
    data = make_client().post("/api/simulate", json=body).json()
    assert data["source"] == "rules"
    assert data["result"]["co2_kg"] == -873.6
    assert "not a forecast" in data["explanation"]
    assert data["disclaimer"]
    assert data["assumptions"]


def test_simulate_ai_explanation(make_client: MakeClient) -> None:
    reply = json.dumps({"explanation": "You save CO2.", "next_step": "Try it Monday."})
    models = FakeModels(text_response(reply))
    body = {"scenario_id": "community_trees", "inputs": {"trees": 100, "years": 2}}
    data = make_client(models=models).post("/api/simulate", json=body).json()
    assert data["source"] == "ai"
    assert data["explanation"] == "You save CO2."
    assert data["result"]["co2_kg"] == -4200.0
    assert data["result"]["pm25_g"] is None


def test_simulate_ai_invalid_json_falls_back(make_client: MakeClient) -> None:
    models = FakeModels(text_response("not json"))
    body = {"scenario_id": "community_trees", "inputs": {"trees": 10}}
    assert make_client(models=models).post("/api/simulate", json=body).json()["source"] == "rules"


def test_families_and_custom_switch(make_client: MakeClient) -> None:
    client = make_client()
    families = {
        "scenario_id": "families_reduce_driving",
        "inputs": {"families": 1000, "km_per_day_reduced": 5, "days_per_week": 5},
    }
    custom = {
        "scenario_id": "custom_commute_switch",
        "inputs": {
            "from_mode": "petrol_2w",
            "to_mode": "ev_2w",
            "distance_km": 8,
            "days_per_week": 6,
        },
    }
    assert client.post("/api/simulate", json=families).json()["result"]["co2_kg"] < 0
    assert client.post("/api/simulate", json=custom).json()["result"]["co2_kg"] < 0


def test_avoid_peak_uses_forecast_for_exposure(make_client: MakeClient) -> None:
    body = {
        "scenario_id": "avoid_peak_hours",
        "inputs": {
            "mode": "petrol_car",
            "distance_km": 10,
            "days_per_week": 5,
            "peak_hour": 9,
            "off_peak_hour": 10,
        },
        "location": LOCATION,
    }
    data = make_client().post("/api/simulate", json=body).json()
    # Fixture PM2.5: 186 at 09:00, 150 at 10:00 -> -19.4%
    assert data["result"]["exposure_change_pct"] == -19.4


def test_simulate_rejects_unknown_scenario(make_client: MakeClient) -> None:
    body = {"scenario_id": "lower_city_aqi", "inputs": {}}
    assert make_client().post("/api/simulate", json=body).status_code == 422


def test_simulate_rejects_out_of_range(make_client: MakeClient) -> None:
    body = {"scenario_id": "community_trees", "inputs": {"trees": 1_000_000}}
    assert make_client().post("/api/simulate", json=body).status_code == 422


def test_petrol_to_public_rejects_private_target(make_client: MakeClient) -> None:
    body = {
        "scenario_id": "petrol_to_public",
        "inputs": {"distance_km": 5, "days_per_week": 5, "to_mode": "diesel_car"},
    }
    assert make_client().post("/api/simulate", json=body).status_code == 422
