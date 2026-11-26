from collections.abc import Callable

from fastapi.testclient import TestClient

from app.models.air import GridPoint, Pollutants
from tests.api.conftest import FakeGrid

MakeClient = Callable[..., TestClient]


def test_grid_returns_cells_with_aqi(make_client: MakeClient) -> None:
    response = make_client().get("/api/air/grid", params={"lat": 28.613, "lon": 77.209})
    assert response.status_code == 200
    data = response.json()
    assert data["center"] == {"lat": 28.61, "lon": 77.21, "name": None}
    assert data["step_deg"] == 0.1
    assert [c["aqi"] for c in data["cells"]] == [351, 67]  # cell without PM is skipped
    assert data["cells"][0]["label"] == "Very Poor"
    assert "not differences between individual streets" in data["note"]


def test_grid_without_any_usable_cell_is_503(make_client: MakeClient) -> None:
    grid = FakeGrid([GridPoint(lat=1, lon=1, pollutants=Pollutants(o3=10))])
    response = make_client(grid=grid).get("/api/air/grid", params={"lat": 1, "lon": 1})
    assert response.status_code == 503


def test_grid_upstream_failure_is_503(make_client: MakeClient) -> None:
    response = make_client(grid=FakeGrid(None)).get("/api/air/grid", params={"lat": 1, "lon": 1})
    assert response.status_code == 503


def test_grid_validates_coordinates(make_client: MakeClient) -> None:
    assert make_client().get("/api/air/grid", params={"lat": 1, "lon": 500}).status_code == 422


def test_points_returns_aqi_in_order_with_nulls(make_client: MakeClient) -> None:
    body = {
        "points": [{"lat": 28.61, "lon": 77.21}, {"lat": 19.08, "lon": 72.88}, {"lat": 1, "lon": 1}]
    }
    response = make_client().post("/api/air/points", json=body)
    assert response.status_code == 200
    cells = response.json()["cells"]
    assert [c and c["aqi"] for c in cells] == [351, 67, None]  # third has no particulates
    assert cells[1]["lat"] == 19.08


def test_points_limits(make_client: MakeClient) -> None:
    client = make_client()
    assert client.post("/api/air/points", json={"points": []}).status_code == 422
    many = {"points": [{"lat": 1, "lon": 1}] * 81}
    assert client.post("/api/air/points", json=many).status_code == 422
    bad = {"points": [{"lat": 100, "lon": 1}]}
    assert client.post("/api/air/points", json=bad).status_code == 422


def test_points_upstream_failure_is_503(make_client: MakeClient) -> None:
    client = make_client(grid=FakeGrid(None))
    response = client.post("/api/air/points", json={"points": [{"lat": 1, "lon": 1}]})
    assert response.status_code == 503
