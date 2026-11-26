from collections.abc import Callable

from fastapi.testclient import TestClient

from tests.api.conftest import FakeHistory, history_readings

MakeClient = Callable[..., TestClient]


def test_history_week_returns_daily_aqi(make_client: MakeClient) -> None:
    response = make_client().get("/api/air/history", params={"lat": 28.61, "lon": 77.21})
    assert response.status_code == 200
    data = response.json()
    assert data["period_days"] == 7
    labels = [d["label"] for d in data["days"]]
    assert labels == ["Mon 23 Nov", "Tue 24 Nov", "Wed 25 Nov", "Thu 26 Nov"]
    assert [d["aqi"] for d in data["days"]] == [33, 75, 233, 362]
    assert data["days"][-1]["is_today"] is True
    summary = data["summary"]
    assert summary["best"]["label"] == "Mon 23 Nov"
    assert summary["worst"]["category"] == "very_poor"
    assert summary["by_category"]["good"] == 1
    assert summary["average_aqi"] == 176


def test_history_month_passes_days(make_client: MakeClient) -> None:
    history = FakeHistory(history_readings([50] * 30))
    client = make_client(history=history)
    response = client.get("/api/air/history", params={"lat": 1, "lon": 1, "days": 30})
    assert response.status_code == 200
    assert history.calls == [30]


def test_history_rejects_other_periods(make_client: MakeClient) -> None:
    response = make_client().get("/api/air/history", params={"lat": 1, "lon": 1, "days": 365})
    assert response.status_code == 422


def test_history_upstream_failure_is_503(make_client: MakeClient) -> None:
    client = make_client(history=FakeHistory(None))
    assert client.get("/api/air/history", params={"lat": 1, "lon": 1}).status_code == 503


def test_partial_today_is_not_counted_as_best_or_worst(make_client: MakeClient) -> None:
    history = FakeHistory(history_readings([100, 100, 10], hours_last_day=6))
    data = make_client(history=history).get("/api/air/history", params={"lat": 1, "lon": 1})
    body = data.json()
    assert body["days"][-1]["complete"] is False
    assert body["summary"]["days"] == 2
    assert body["summary"]["best"]["aqi"] == 233
