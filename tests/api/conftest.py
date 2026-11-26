"""Fakes for API tests: no network, no real Claude calls."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from types import SimpleNamespace
from typing import Any

import anthropic
import pytest
from fastapi.testclient import TestClient

from app.ai.client import ClaudeClient
from app.config import Settings
from app.main import create_app
from app.models.air import AirData, GridPoint, Place, Pollutants
from app.services.air_quality import parse_air_data
from app.services.errors import UpstreamError


class FakeAirService:
    def __init__(self, data: AirData | None, *, stale: bool = False) -> None:
        self.data = data
        self.stale = stale
        self.calls: list[tuple[float, float]] = []

    async def get_air_data(self, lat: float, lon: float) -> tuple[AirData, bool]:
        self.calls.append((lat, lon))
        if self.data is None:
            raise UpstreamError("down")
        return self.data, self.stale


class FakeGeocoding:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []

    async def search(self, query: str, country: str | None = None) -> list[Place]:
        self.calls.append((query, country))
        return [Place(name="New Delhi", country="India", lat=28.64, lon=77.22)]


class FakeGrid:
    def __init__(self, points: list[GridPoint] | None = None) -> None:
        self.points = points

    async def get_grid(self, lat: float, lon: float) -> tuple[list[GridPoint], bool]:
        if self.points is None:
            raise UpstreamError("down")
        return self.points, False


DEFAULT_GRID = [
    GridPoint(lat=28.61, lon=77.21, pollutants=Pollutants(pm2_5=186.0)),
    GridPoint(lat=28.71, lon=77.21, pollutants=Pollutants(pm2_5=40.0)),
    GridPoint(lat=28.51, lon=77.21, pollutants=Pollutants(no2=20.0)),  # no particulates
]


class FakeAPIError(anthropic.APIError):
    def __init__(self) -> None:  # skip SDK constructor (needs a real request)
        Exception.__init__(self, "boom")


def text_response(text: str, stop_reason: str = "end_turn") -> SimpleNamespace:
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)], stop_reason=stop_reason
    )


def tool_response(*calls: tuple[str, str, dict[str, Any]]) -> SimpleNamespace:
    blocks = [SimpleNamespace(type="tool_use", id=i, name=n, input=a) for i, n, a in calls]
    return SimpleNamespace(content=blocks, stop_reason="tool_use")


class FakeMessages:
    """Returns queued responses (or raises queued exceptions) and records requests."""

    def __init__(self, *responses: Any) -> None:
        self.responses = list(responses)
        self.requests: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> Any:
        self.requests.append(kwargs)
        item = self.responses.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


@pytest.fixture
def air_data(load_fixture: Callable[[str], dict[str, Any]]) -> AirData:
    return parse_air_data(
        28.61, 77.21, load_fixture("air_quality.json"), load_fixture("weather.json")
    )


@pytest.fixture
def make_client(air_data: AirData) -> Iterator[Callable[..., TestClient]]:
    clients: list[TestClient] = []

    def _make(
        *,
        messages: FakeMessages | None = None,
        air: FakeAirService | None = None,
        grid: FakeGrid | None = None,
        **settings: Any,
    ) -> TestClient:
        app = create_app(Settings(anthropic_api_key=None, **settings))
        app.state.air_service = air or FakeAirService(air_data)
        app.state.grid_service = grid or FakeGrid(DEFAULT_GRID)
        app.state.geocoding_service = FakeGeocoding()
        app.state.ai = ClaudeClient(messages, "claude-opus-5-5") if messages else None
        client = TestClient(app, raise_server_exceptions=False)
        client.__enter__()
        clients.append(client)
        return client

    yield _make
    for client in clients:
        client.__exit__(None, None, None)


FAMILY = [
    {"id": "m_1", "name": "Aarav", "age_group": "child", "conditions": ["asthma"]},
    {"id": "m_2", "age_group": "adult", "outdoor_activities": ["jogging"]},
]
LOCATION = {"lat": 28.61, "lon": 77.21}
HOUSEHOLD = {
    "commute": {"mode": "petrol_car", "distance_km": 12, "days_per_week": 5, "depart_hour": 9},
    "school": {"start_hour": 8, "end_hour": 14},
    "home": {"has_purifier": True, "cooking_fuel": "lpg"},
}


def dumps(obj: Any) -> str:
    return json.dumps(obj)
