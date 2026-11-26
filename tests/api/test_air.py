from collections.abc import Callable

from fastapi.testclient import TestClient

from tests.api.conftest import FakeAirService

MakeClient = Callable[..., TestClient]


def test_geocode_returns_results(make_client: MakeClient) -> None:
    response = make_client().get("/api/geocode", params={"q": "Delhi"})
    assert response.status_code == 200
    assert response.json()["results"][0]["name"] == "New Delhi"


def test_geocode_passes_country_filter(make_client: MakeClient) -> None:
    client = make_client()
    assert client.get("/api/geocode", params={"q": "Pune", "country": "IN"}).status_code == 200
    assert client.app.state.geocoding_service.calls[-1] == ("Pune", "IN")


def test_geocode_rejects_bad_country(make_client: MakeClient) -> None:
    response = make_client().get("/api/geocode", params={"q": "Pune", "country": "india"})
    assert response.status_code == 422


def test_geocode_rejects_bad_query(make_client: MakeClient) -> None:
    response = make_client().get("/api/geocode", params={"q": "<script>"})
    assert response.status_code == 422
    body = response.json()["error"]
    assert body["code"] == "validation_error"
    assert body["details"][0]["field"] == "q"


def test_air_returns_dashboard(make_client: MakeClient) -> None:
    response = make_client().get("/api/air", params={"lat": 28.61, "lon": 77.21})
    assert response.status_code == 200
    data = response.json()
    assert data["current"]["aqi"] == 351
    assert data["current"]["label"] == "Very Poor"
    assert data["current"]["dominant"] == "pm2_5"
    assert data["current"]["pollutants"]["co"] == 2.1
    assert len(data["forecast"]) == 2  # 11:00 has no particulate data
    assert set(data["best_windows"]) == {"walk", "jog", "play", "commute"}
    assert data["best_windows"]["walk"]["start"].endswith("10:00:00")
    assert data["stale"] is False


def test_air_passes_stale_flag(make_client: MakeClient, air_data) -> None:
    client = make_client(air=FakeAirService(air_data, stale=True))
    assert client.get("/api/air", params={"lat": 1, "lon": 1}).json()["stale"] is True


def test_air_rejects_out_of_range_coordinates(make_client: MakeClient) -> None:
    response = make_client().get("/api/air", params={"lat": 120, "lon": 77})
    assert response.status_code == 422


def test_air_upstream_failure_is_503(make_client: MakeClient) -> None:
    client = make_client(air=FakeAirService(None))
    response = client.get("/api/air", params={"lat": 28.61, "lon": 77.21})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "upstream_unavailable"
