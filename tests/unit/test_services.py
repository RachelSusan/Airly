from collections.abc import Callable
from typing import Any

import httpx
import pytest
import respx

from app.models.air import AirData, Place
from app.services.air_quality import (
    AIR_QUALITY_URL,
    MET_USER_AGENT,
    MET_WEATHER_URL,
    WEATHER_URL,
    AirQualityService,
)
from app.services.cache import TTLCache
from app.services.errors import UpstreamError
from app.services.geocoding import GEOCODING_URL, GeocodingService

Loader = Callable[[str], dict[str, Any]]


def _air_service(client: httpx.AsyncClient) -> AirQualityService:
    return AirQualityService(client, TTLCache[AirData](ttl=900, max_entries=10, stale_ttl=7200))


@respx.mock
async def test_air_quality_parses_and_combines(load_fixture: Loader) -> None:
    air_route = respx.get(AIR_QUALITY_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("air_quality.json"))
    )
    respx.get(WEATHER_URL).mock(return_value=httpx.Response(200, json=load_fixture("weather.json")))

    async with httpx.AsyncClient() as client:
        data, stale = await _air_service(client).get_air_data(28.6139, 77.2090)

    assert stale is False
    assert (data.lat, data.lon) == (28.61, 77.21)
    assert data.timezone == "Asia/Kolkata"
    assert data.current.pollutants.pm2_5 == 186.0
    assert data.current.pollutants.co == 2.1  # µg/m³ -> mg/m³
    assert data.current.weather.wind_kmh == 4.1
    # Forecast starts at the current hour (08:00 is dropped)
    assert [r.time.hour for r in data.forecast] == [9, 10, 11]
    assert data.forecast[1].weather.temperature_c == 16.0
    assert data.forecast[2].pollutants.pm2_5 is None
    assert data.forecast[2].pollutants.so2 is None  # negative reading discarded
    assert air_route.calls.last.request.url.params["latitude"] == "28.61"


@respx.mock
async def test_air_quality_uses_cache(load_fixture: Loader) -> None:
    air_route = respx.get(AIR_QUALITY_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("air_quality.json"))
    )
    respx.get(WEATHER_URL).mock(return_value=httpx.Response(200, json=load_fixture("weather.json")))
    async with httpx.AsyncClient() as client:
        service = _air_service(client)
        await service.get_air_data(28.61, 77.21)
        await service.get_air_data(28.611, 77.209)  # rounds to the same key
    assert air_route.call_count == 1


@respx.mock
async def test_air_quality_works_without_weather(load_fixture: Loader) -> None:
    respx.get(AIR_QUALITY_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("air_quality.json"))
    )
    respx.get(WEATHER_URL).mock(return_value=httpx.Response(429, text="Too many requests"))
    respx.get(MET_WEATHER_URL).mock(side_effect=httpx.ConnectError("offline"))
    async with httpx.AsyncClient() as client:
        data, _ = await _air_service(client).get_air_data(28.61, 77.21)
    assert data.current.pollutants.pm2_5 == 186.0
    assert data.current.weather.wind_kmh is None
    assert data.forecast[0].weather.temperature_c is None


def _met_entry(utc_time: str, temp: float, wind_ms: float) -> dict[str, Any]:
    return {
        "time": utc_time,
        "data": {
            "instant": {
                "details": {
                    "air_temperature": temp,
                    "relative_humidity": 60.0,
                    "wind_speed": wind_ms,
                }
            },
            "next_1_hours": {"details": {"precipitation_amount": 0.2}},
        },
    }


@respx.mock
async def test_air_quality_uses_backup_weather(load_fixture: Loader) -> None:
    respx.get(AIR_QUALITY_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("air_quality.json"))
    )
    respx.get(WEATHER_URL).mock(return_value=httpx.Response(429, text="Too many requests"))
    met = {
        "properties": {
            "timeseries": [
                # 04:00 UTC = 09:30 IST -> the fixture's current hour (09:00); 05:00 UTC -> 10:00
                _met_entry("2026-11-26T04:00:00Z", 21.0, 1.0),
                _met_entry("2026-11-26T05:00:00Z", 23.5, 2.0),
            ]
        }
    }
    met_route = respx.get(MET_WEATHER_URL).mock(return_value=httpx.Response(200, json=met))
    async with httpx.AsyncClient() as client:
        data, _ = await _air_service(client).get_air_data(28.61, 77.21)
    assert met_route.calls.last.request.headers["User-Agent"] == MET_USER_AGENT
    assert data.current.weather.temperature_c == 21.0
    assert data.current.weather.wind_kmh == 3.6
    assert data.current.weather.precip_mm == 0.2
    ten_am = next(r for r in data.forecast if r.time.hour == 10)
    assert ten_am.weather.temperature_c == 23.5
    assert ten_am.weather.wind_kmh == 7.2


@respx.mock
async def test_air_quality_http_error_raises_upstream_error() -> None:
    respx.get(AIR_QUALITY_URL).mock(return_value=httpx.Response(503))
    respx.get(WEATHER_URL).mock(return_value=httpx.Response(200, json={}))
    async with httpx.AsyncClient() as client:
        with pytest.raises(UpstreamError):
            await _air_service(client).get_air_data(28.61, 77.21)


@respx.mock
async def test_air_quality_bad_format_raises_upstream_error() -> None:
    respx.get(AIR_QUALITY_URL).mock(return_value=httpx.Response(200, json={"unexpected": 1}))
    respx.get(WEATHER_URL).mock(return_value=httpx.Response(200, json={"unexpected": 1}))
    async with httpx.AsyncClient() as client:
        with pytest.raises(UpstreamError):
            await _air_service(client).get_air_data(28.61, 77.21)


def _geo_service(client: httpx.AsyncClient) -> GeocodingService:
    return GeocodingService(client, TTLCache[list[Place]](ttl=86400, max_entries=10))


@respx.mock
async def test_geocoding_parses_results_and_skips_bad_rows(load_fixture: Loader) -> None:
    route = respx.get(GEOCODING_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("geocoding.json"))
    )
    async with httpx.AsyncClient() as client:
        places = await _geo_service(client).search("  New   Delhi ")
    assert places == [
        Place(
            name="New Delhi",
            admin="Delhi",
            country="India",
            lat=28.64,
            lon=77.22,
            timezone="Asia/Kolkata",
        )
    ]
    assert route.calls.last.request.url.params["name"] == "new delhi"


@respx.mock
async def test_geocoding_country_filter_sent_and_cached_separately(load_fixture: Loader) -> None:
    route = respx.get(GEOCODING_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("geocoding.json"))
    )
    async with httpx.AsyncClient() as client:
        service = _geo_service(client)
        await service.search("Delhi", "IN")
        await service.search("Delhi")
    assert route.call_count == 2
    assert route.calls[0].request.url.params["countryCode"] == "IN"
    assert "countryCode" not in route.calls[1].request.url.params


@respx.mock
async def test_geocoding_empty_query_makes_no_request() -> None:
    route = respx.get(GEOCODING_URL)
    async with httpx.AsyncClient() as client:
        assert await _geo_service(client).search("   ") == []
    assert route.call_count == 0


@respx.mock
async def test_geocoding_no_results() -> None:
    respx.get(GEOCODING_URL).mock(return_value=httpx.Response(200, json={}))
    async with httpx.AsyncClient() as client:
        assert await _geo_service(client).search("zzzz") == []


@respx.mock
async def test_geocoding_error_raises_upstream_error() -> None:
    respx.get(GEOCODING_URL).mock(side_effect=httpx.ConnectError("offline"))
    async with httpx.AsyncClient() as client:
        with pytest.raises(UpstreamError):
            await _geo_service(client).search("Delhi")
