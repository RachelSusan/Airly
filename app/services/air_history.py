"""Past days of hourly air quality from Open-Meteo (for the week / month trend view)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from app.models.air import HourlyReading, Weather
from app.services.air_quality import AIR_QUALITY_URL, AIR_VARIABLES, parse_pollutants, round_coord
from app.services.cache import TTLCache
from app.services.errors import UpstreamError

ALLOWED_DAYS = (7, 30)


class AirHistoryService:
    """Fetches and caches the past ``days`` of hourly readings (today included)."""

    def __init__(self, http: httpx.AsyncClient, cache: TTLCache[list[HourlyReading]]) -> None:
        self._http = http
        self._cache = cache

    async def get_history(
        self, lat: float, lon: float, days: int
    ) -> tuple[list[HourlyReading], bool]:
        """Return ``(readings, is_stale)``.

        Raises:
            ValueError: if ``days`` is not one of ``ALLOWED_DAYS``.
            UpstreamError: if the provider fails and nothing is cached.
        """
        if days not in ALLOWED_DAYS:
            raise ValueError(f"days must be one of {ALLOWED_DAYS}")
        lat, lon = round_coord(lat), round_coord(lon)
        return await self._cache.get_or_load(
            f"history:{days}:{lat}:{lon}", lambda: self._fetch(lat, lon, days)
        )

    async def _fetch(self, lat: float, lon: float, days: int) -> list[HourlyReading]:
        params: dict[str, str | int | float] = {
            "latitude": lat,
            "longitude": lon,
            "hourly": ",".join(AIR_VARIABLES),
            "timezone": "auto",
            "past_days": days - 1,  # plus today
            "forecast_days": 1,
        }
        try:
            response = await self._http.get(AIR_QUALITY_URL, params=params)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise UpstreamError("History request failed") from exc
        try:
            return parse_history(payload)
        except (KeyError, TypeError, ValueError) as exc:
            raise UpstreamError("Unexpected history response format") from exc


def parse_history(payload: dict[str, Any]) -> list[HourlyReading]:
    """Hourly readings from an Open-Meteo air-quality response."""
    hourly = payload["hourly"]
    return [
        HourlyReading(
            time=datetime.fromisoformat(raw_time),
            pollutants=parse_pollutants({k: hourly[k][i] for k in AIR_VARIABLES}),
            weather=Weather(),
        )
        for i, raw_time in enumerate(hourly["time"])
    ]
