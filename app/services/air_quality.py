"""Open-Meteo client for air quality and weather (free, no API key).

Docs: https://open-meteo.com/en/docs/air-quality-api and https://open-meteo.com/en/docs
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

import httpx

from app.models.air import AirData, HourlyReading, Pollutants, Weather
from app.services.cache import TTLCache
from app.services.errors import UpstreamError

AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
FORECAST_HOURS = 24
COORD_DECIMALS = 2  # ~1 km: better cache hits and privacy
UG_PER_MG = 1000.0

# Open-Meteo variable name -> our pollutant field
_AIR_VARIABLES: dict[str, str] = {
    "pm2_5": "pm2_5",
    "pm10": "pm10",
    "nitrogen_dioxide": "no2",
    "ozone": "o3",
    "carbon_monoxide": "co",
    "sulphur_dioxide": "so2",
}
_WEATHER_VARIABLES: dict[str, str] = {
    "temperature_2m": "temperature_c",
    "relative_humidity_2m": "humidity_pct",
    "wind_speed_10m": "wind_kmh",
    "precipitation": "precip_mm",
}


def round_coord(value: float) -> float:
    """Round a coordinate to the precision we use for caching and logging."""
    return round(value, COORD_DECIMALS)


class AirQualityService:
    """Fetches and caches combined air-quality and weather data."""

    def __init__(self, http: httpx.AsyncClient, cache: TTLCache[AirData]) -> None:
        self._http = http
        self._cache = cache

    async def get_air_data(self, lat: float, lon: float) -> tuple[AirData, bool]:
        """Return ``(data, is_stale)`` for the rounded coordinates.

        Raises:
            UpstreamError: if the provider fails and no stale data is cached.
        """
        lat, lon = round_coord(lat), round_coord(lon)
        key = f"air:{lat}:{lon}"
        return await self._cache.get_or_load(key, lambda: self._fetch(lat, lon))

    async def _fetch(self, lat: float, lon: float) -> AirData:
        base = {"latitude": lat, "longitude": lon, "timezone": "auto", "forecast_days": 2}
        air_params = {
            **base,
            "hourly": ",".join(_AIR_VARIABLES),
            "current": ",".join(_AIR_VARIABLES),
        }
        weather_params = {
            **base,
            "hourly": ",".join(_WEATHER_VARIABLES),
            "current": ",".join(_WEATHER_VARIABLES),
        }
        air_json, weather_json = await asyncio.gather(
            self._get_json(AIR_QUALITY_URL, air_params),
            self._get_json(WEATHER_URL, weather_params),
        )
        try:
            return parse_air_data(lat, lon, air_json, weather_json)
        except (KeyError, TypeError, ValueError) as exc:
            raise UpstreamError("Unexpected air-quality response format") from exc

    async def _get_json(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        try:
            response = await self._http.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise UpstreamError(f"Request to {httpx.URL(url).host} failed") from exc


def parse_air_data(
    lat: float, lon: float, air_json: dict[str, Any], weather_json: dict[str, Any]
) -> AirData:
    """Combine Open-Meteo air-quality and weather responses into ``AirData``.

    The forecast starts at the current hour and covers ``FORECAST_HOURS`` hours.
    """
    weather_by_time = _weather_by_time(weather_json["hourly"])
    air_hourly = air_json["hourly"]
    current_time = _parse_time(air_json["current"]["time"])

    readings: list[HourlyReading] = []
    for index, raw_time in enumerate(air_hourly["time"]):
        time = _parse_time(raw_time)
        if time < current_time.replace(minute=0):
            continue
        pollutants = _pollutants({k: air_hourly[k][index] for k in _AIR_VARIABLES})
        readings.append(
            HourlyReading(
                time=time, pollutants=pollutants, weather=weather_by_time.get(time, Weather())
            )
        )
        if len(readings) == FORECAST_HOURS:
            break

    current = HourlyReading(
        time=current_time,
        pollutants=_pollutants({k: air_json["current"].get(k) for k in _AIR_VARIABLES}),
        weather=_weather({k: weather_json["current"].get(k) for k in _WEATHER_VARIABLES}),
    )
    return AirData(
        lat=lat,
        lon=lon,
        timezone=air_json.get("timezone", "UTC"),
        current=current,
        forecast=readings,
    )


def _weather_by_time(hourly: dict[str, list[Any]]) -> dict[datetime, Weather]:
    result: dict[datetime, Weather] = {}
    for index, raw_time in enumerate(hourly["time"]):
        values = {k: hourly[k][index] for k in _WEATHER_VARIABLES}
        result[_parse_time(raw_time)] = _weather(values)
    return result


def _pollutants(raw: dict[str, Any]) -> Pollutants:
    values = {_AIR_VARIABLES[k]: _number(v) for k, v in raw.items()}
    if values["co"] is not None:
        values["co"] = round(values["co"] / UG_PER_MG, 3)  # µg/m³ -> mg/m³
    return Pollutants(**values)


def _weather(raw: dict[str, Any]) -> Weather:
    return Weather(**{_WEATHER_VARIABLES[k]: _number(v) for k, v in raw.items()})


def _number(value: Any) -> float | None:
    """Convert to float; missing or negative (invalid) readings become ``None``."""
    if value is None:
        return None
    number = float(value)
    return number if number >= 0 else None


def _parse_time(raw: str) -> datetime:
    return datetime.fromisoformat(raw)
