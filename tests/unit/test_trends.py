import httpx
import pytest
import respx

from app.engine.aqi import AqiCategory
from app.engine.trends import daily_summaries, summarise
from app.models.air import HourlyReading
from app.services.air_history import AirHistoryService
from app.services.air_quality import AIR_QUALITY_URL
from app.services.cache import TTLCache
from app.services.errors import UpstreamError
from tests.api.conftest import history_readings


def _with_pm(reading: HourlyReading, pm: float | None) -> HourlyReading:
    return reading.model_copy(
        update={"pollutants": reading.pollutants.model_copy(update={"pm2_5": pm})}
    )


def test_daily_aqi_uses_daily_average_concentration() -> None:
    readings = history_readings([30, 60])
    # Day 2 alternates 90 / 30 within the day: its mean is still 60
    readings[24:] = [_with_pm(r, 30.0 if i % 2 else 90.0) for i, r in enumerate(readings[24:])]
    days = daily_summaries(readings)
    assert [(d.day.day, d.aqi) for d in days] == [(25, 50), (26, 100)]
    assert days[1].pm2_5 == 60.0


def test_days_without_particulates_are_skipped() -> None:
    assert daily_summaries([_with_pm(r, None) for r in history_readings([40])]) == []


def test_summarise_counts_and_extremes() -> None:
    stats = summarise(daily_summaries(history_readings([20, 200, 100])))
    assert stats.days == 3
    assert stats.by_category[AqiCategory.GOOD] == 1
    assert stats.best is not None and stats.best.aqi == 33
    assert stats.worst is not None and stats.worst.aqi == 362
    assert stats.average_aqi == round((33 + 362 + 233) / 3)


def test_summarise_empty() -> None:
    stats = summarise([])
    assert stats.best is None
    assert stats.average_aqi is None


def _service(client: httpx.AsyncClient) -> AirHistoryService:
    return AirHistoryService(client, TTLCache[list[HourlyReading]](ttl=60, max_entries=5))


@respx.mock
async def test_history_service_requests_past_days_and_parses() -> None:
    payload = {
        "hourly": {
            "time": ["2026-11-25T00:00", "2026-11-25T01:00"],
            "pm2_5": [50.0, 70.0],
            "pm10": [None, None],
            "nitrogen_dioxide": [10.0, 10.0],
            "ozone": [5.0, 5.0],
            "carbon_monoxide": [500.0, 500.0],
            "sulphur_dioxide": [3.0, 3.0],
        }
    }
    route = respx.get(AIR_QUALITY_URL).mock(return_value=httpx.Response(200, json=payload))
    async with httpx.AsyncClient() as client:
        readings, stale = await _service(client).get_history(28.613, 77.209, 30)
    assert len(readings) == 2
    assert stale is False
    assert readings[0].pollutants.co == 0.5
    params = route.calls.last.request.url.params
    assert params["past_days"] == "29"
    assert params["latitude"] == "28.61"


@respx.mock
async def test_history_service_errors() -> None:
    respx.get(AIR_QUALITY_URL).mock(return_value=httpx.Response(200, json={"oops": 1}))
    async with httpx.AsyncClient() as client:
        with pytest.raises(UpstreamError):
            await _service(client).get_history(1, 1, 7)
        with pytest.raises(ValueError, match="days"):
            await _service(client).get_history(1, 1, 90)
