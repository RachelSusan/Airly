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
