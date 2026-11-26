"""Fakes for API tests: no network, no real Gemini calls."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from google.genai import errors as genai_errors
from google.genai import types

from app.ai.client import GeminiClient
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

    async def get_points(self, points: list[tuple[float, float]]) -> tuple[list[GridPoint], bool]:
        if self.points is None:
            raise UpstreamError("down")
        return [
            GridPoint(lat=lat, lon=lon, pollutants=self.points[i % len(self.points)].pollutants)
            for i, (lat, lon) in enumerate(points)
        ], False


DEFAULT_GRID = [
    GridPoint(lat=28.61, lon=77.21, pollutants=Pollutants(pm2_5=186.0)),
    GridPoint(lat=28.71, lon=77.21, pollutants=Pollutants(pm2_5=40.0)),
    GridPoint(lat=28.51, lon=77.21, pollutants=Pollutants(no2=20.0)),  # no particulates
]


class FakeAPIError(genai_errors.APIError):
    def __init__(self) -> None:  # skip SDK constructor (needs a real response)
        Exception.__init__(self, "boom")
        self.code = 400  # a request error that switching models would not fix


def _candidate(parts: list[Any], finish: str) -> SimpleNamespace:
    return SimpleNamespace(
        content=SimpleNamespace(role="model", parts=parts),
        finish_reason=types.FinishReason(finish),
    )


def text_response(text: str, finish: str = "STOP") -> SimpleNamespace:
    """A Gemini-shaped response with one text part."""
    part = SimpleNamespace(text=text, thought=None, function_call=None)
    return SimpleNamespace(candidates=[_candidate([part], finish)], function_calls=None)


def tool_response(*calls: tuple[str, str, dict[str, Any]]) -> SimpleNamespace:
    """A Gemini-shaped response asking to call tools: ``(id, name, args)`` each."""
    fcs = [SimpleNamespace(id=i, name=n, args=a) for i, n, a in calls]
    parts = [SimpleNamespace(text=None, thought=None, function_call=fc) for fc in fcs]
    return SimpleNamespace(candidates=[_candidate(parts, "STOP")], function_calls=fcs)


class FakeModels:
    """Stands in for ``genai.Client().aio.models``: returns queued responses (or raises
    queued exceptions) and records each request."""

    def __init__(self, *responses: Any) -> None:
        self.responses = list(responses)
        self.requests: list[dict[str, Any]] = []

    async def generate_content(self, *, model: str, contents: Any, config: Any) -> Any:
        snapshot = list(contents) if isinstance(contents, list) else contents
        self.requests.append({"model": model, "contents": snapshot, "config": config})
        item = self.responses.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


def tool_results(request: dict[str, Any]) -> list[Any]:
    """Function responses the app sent back in a recorded request."""
    return [part.function_response for part in request["contents"][-1].parts]


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
        models: FakeModels | None = None,
        air: FakeAirService | None = None,
        grid: FakeGrid | None = None,
        **settings: Any,
    ) -> TestClient:
        app = create_app(Settings(gemini_api_key=None, **settings))
        app.state.air_service = air or FakeAirService(air_data)
        app.state.grid_service = grid or FakeGrid(DEFAULT_GRID)
        app.state.geocoding_service = FakeGeocoding()
        app.state.ai = GeminiClient(models, "gemini-test") if models else None
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
