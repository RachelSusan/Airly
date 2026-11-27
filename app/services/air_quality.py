"""Open-Meteo client for air quality and weather (free, no API key).

Docs: https://open-meteo.com/en/docs/air-quality-api and https://open-meteo.com/en/docs
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

import httpx

from app.models.air import AirData, HourlyReading, Pollutants, Weather
from app.services.cache import TTLCache
from app.services.errors import UpstreamError

logger = logging.getLogger(__name__)

AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
# Backup weather source (MET Norway, free, no key). Its terms ask for an identifying User-Agent.
MET_WEATHER_URL = "https://api.met.no/weatherapi/locationforecast/2.0/compact"
MET_USER_AGENT = "Airly/1.0 (+https://github.com/RachelSusan/Airly)"
MS_TO_KMH = 3.6
FORECAST_HOURS = 24
COORD_DECIMALS = 2  # ~1 km: better cache hits and privacy
UG_PER_MG = 1000.0

# Open-Meteo variable name -> our pollutant field
AIR_VARIABLES: dict[str, str] = {
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
            "hourly": ",".join(AIR_VARIABLES),
            "current": ",".join(AIR_VARIABLES),
        }
        weather_params = {
            **base,
            "hourly": ",".join(_WEATHER_VARIABLES),
            "current": ",".join(_WEATHER_VARIABLES),
        }
        air_result, weather_result = await asyncio.gather(
            self._get_json(AIR_QUALITY_URL, air_params),
            self._get_json(WEATHER_URL, weather_params),
            return_exceptions=True,
        )
        if isinstance(air_result, BaseException):
            raise air_result  # air quality is essential
        air_json = air_result
        # Weather only adds context (temperature, wind); never fail the dashboard without it.
        weather_json: dict[str, Any] | None = None
        if isinstance(weather_result, BaseException):
            logger.warning("weather_primary_unavailable detail=%s", weather_result)
            weather_json = await self._backup_weather(lat, lon, air_json)
        else:
            weather_json = weather_result
        try:
            return parse_air_data(lat, lon, air_json, weather_json)
        except (KeyError, TypeError, ValueError) as exc:
            raise UpstreamError("Unexpected air-quality response format") from exc

    async def _backup_weather(
        self, lat: float, lon: float, air_json: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Weather from MET Norway, reshaped like Open-Meteo's; ``None`` if it fails too."""
        try:
            met_json = await self._get_json(
                MET_WEATHER_URL,
                {"lat": lat, "lon": lon},
                headers={"User-Agent": MET_USER_AGENT},
            )
            return met_to_open_meteo(met_json, air_json)
        except (UpstreamError, KeyError, TypeError, ValueError) as exc:
            logger.warning("weather_unavailable detail=%s", exc)
            return None

    async def _get_json(
        self, url: str, params: dict[str, Any], headers: dict[str, str] | None = None
    ) -> dict[str, Any]:
        host = httpx.URL(url).host
        try:
            response = await self._http.get(url, params=params, headers=headers)
        except httpx.HTTPError as exc:
            raise UpstreamError(f"{host}: {type(exc).__name__}") from exc
        if response.status_code >= 400:
            raise UpstreamError(f"{host}: HTTP {response.status_code} {response.text[:120]}")
        try:
            return response.json()
        except ValueError as exc:
            raise UpstreamError(f"{host}: invalid JSON") from exc


def parse_air_data(
    lat: float, lon: float, air_json: dict[str, Any], weather_json: dict[str, Any] | None
) -> AirData:
    """Combine Open-Meteo air-quality and (optional) weather responses into ``AirData``.

    The forecast starts at the current hour and covers ``FORECAST_HOURS`` hours. Without
    weather data, weather fields are left empty.
    """
    weather_by_time = _weather_by_time(weather_json["hourly"]) if weather_json else {}
    weather_now = (weather_json or {}).get("current") or {}
    air_hourly = air_json["hourly"]
    current_time = _parse_time(air_json["current"]["time"])

    readings: list[HourlyReading] = []
    for index, raw_time in enumerate(air_hourly["time"]):
        time = _parse_time(raw_time)
        if time < current_time.replace(minute=0):
            continue
        pollutants = parse_pollutants({k: air_hourly[k][index] for k in AIR_VARIABLES})
        readings.append(
            HourlyReading(
                time=time, pollutants=pollutants, weather=weather_by_time.get(time, Weather())
            )
        )
        if len(readings) == FORECAST_HOURS:
            break

    current = HourlyReading(
        time=current_time,
        pollutants=parse_pollutants({k: air_json["current"].get(k) for k in AIR_VARIABLES}),
        weather=_weather({k: weather_now.get(k) for k in _WEATHER_VARIABLES}),
    )
    return AirData(
        lat=lat,
        lon=lon,
        timezone=air_json.get("timezone", "UTC"),
        current=current,
        forecast=readings,
    )


def met_to_open_meteo(met_json: dict[str, Any], air_json: dict[str, Any]) -> dict[str, Any]:
    """Convert a MET Norway forecast to the Open-Meteo weather shape used by ``parse_air_data``.

    MET Norway reports whole UTC hours and wind in m/s; Open-Meteo uses local hours (from
    the air-quality response's UTC offset) and km/h. In half-hour zones such as India each
    MET hour is snapped to the local hour it falls in.
    """
    offset = timedelta(seconds=int(air_json.get("utc_offset_seconds", 0)))
    hourly: dict[str, list[Any]] = {"time": [], **{k: [] for k in _WEATHER_VARIABLES}}
    for entry in met_json["properties"]["timeseries"]:
        utc = datetime.fromisoformat(entry["time"].replace("Z", "+00:00"))
        details = entry["data"]["instant"]["details"]
        wind = details.get("wind_speed")
        next_hour = (entry["data"].get("next_1_hours") or {}).get("details") or {}
        # Snap to the local hour it falls in (e.g. 05:00 UTC = 10:30 IST -> 10:00).
        local = (utc + offset).replace(tzinfo=None, minute=0)
        hourly["time"].append(local.isoformat(timespec="minutes"))
        hourly["temperature_2m"].append(details.get("air_temperature"))
        hourly["relative_humidity_2m"].append(details.get("relative_humidity"))
        hourly["wind_speed_10m"].append(round(wind * MS_TO_KMH, 1) if wind is not None else None)
        hourly["precipitation"].append(next_hour.get("precipitation_amount"))

    now_hour = _parse_time(air_json["current"]["time"]).replace(minute=0)
    current: dict[str, Any] = {}
    for index, raw_time in enumerate(hourly["time"]):
        if _parse_time(raw_time) == now_hour:
            current = {k: hourly[k][index] for k in _WEATHER_VARIABLES}
            break
    return {"hourly": hourly, "current": current}


def _weather_by_time(hourly: dict[str, list[Any]]) -> dict[datetime, Weather]:
    result: dict[datetime, Weather] = {}
    for index, raw_time in enumerate(hourly["time"]):
        values = {k: hourly[k][index] for k in _WEATHER_VARIABLES}
        result[_parse_time(raw_time)] = _weather(values)
    return result


def parse_pollutants(raw: dict[str, Any]) -> Pollutants:
    values = {AIR_VARIABLES[k]: _number(v) for k, v in raw.items()}
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
