"""Shared fixtures. Tests never touch the network or the real Claude API."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from app.engine.aqi import AqiPoint, Pollutant, category_for

FIXTURES = Path(__file__).parent / "fixtures"
BASE_TIME = datetime(2026, 11, 26, 0, 0)


@pytest.fixture(autouse=True)
def _test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("APP_ENV", "development")


@pytest.fixture
def load_fixture() -> Callable[[str], dict[str, Any]]:
    def _load(name: str) -> dict[str, Any]:
        return json.loads((FIXTURES / name).read_text(encoding="utf-8"))

    return _load


@pytest.fixture
def make_points() -> Callable[..., list[AqiPoint]]:
    """Build hourly AQI points from a list of AQI values starting at ``start_hour``."""

    def _make(values: list[int], start_hour: int = 0) -> list[AqiPoint]:
        start = BASE_TIME + timedelta(hours=start_hour)
        return [
            AqiPoint(
                time=start + timedelta(hours=i),
                aqi=value,
                category=category_for(value),
                dominant=Pollutant.PM2_5,
                pm2_5=None,
            )
            for i, value in enumerate(values)
        ]

    return _make
