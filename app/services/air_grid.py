"""Current pollution at many points in one request: the grid around a location (for the
smooth map overlay) and arbitrary points such as other cities.

One Open-Meteo request returns all points. The air-quality model has a resolution of
roughly 10-40 km, so the grid shows regional patterns, not street-level differences.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.models.air import GridPoint
from app.services.air_quality import (
    AIR_QUALITY_URL,
    AIR_VARIABLES,
    parse_pollutants,
    round_coord,
)
from app.services.cache import TTLCache
from app.services.errors import UpstreamError

GRID_SIZE = 7  # 7 x 7 points (~66 km square)
MAX_POINTS = 80
GRID_STEP_DEG = 0.1  # ~11 km, close to the model's native spacing


def grid_coordinates(lat: float, lon: float, size: int = GRID_SIZE) -> list[tuple[float, float]]:
    """Centre-out square grid of coordinates, clipped to valid latitudes."""
    half = size // 2
    coords = []
    for row in range(-half, half + 1):
        for col in range(-half, half + 1):
            point_lat = round(lat + row * GRID_STEP_DEG, 2)
            point_lon = round(((lon + col * GRID_STEP_DEG + 180) % 360) - 180, 2)
            if -90 <= point_lat <= 90:
                coords.append((point_lat, point_lon))
    return coords


class AirGridService:
    """Fetches and caches current pollution for a grid or a list of points."""

    def __init__(self, http: httpx.AsyncClient, cache: TTLCache[list[GridPoint]]) -> None:
        self._http = http
        self._cache = cache

    async def get_grid(self, lat: float, lon: float) -> tuple[list[GridPoint], bool]:
        """Return ``(points, is_stale)`` around the rounded location.

        Raises:
            UpstreamError: if the provider fails and nothing is cached.
        """
        lat, lon = round_coord(lat), round_coord(lon)
        coords = grid_coordinates(lat, lon)
        return await self._cache.get_or_load(f"grid:{lat}:{lon}", lambda: self._fetch(coords))

    async def get_points(self, points: list[tuple[float, float]]) -> tuple[list[GridPoint], bool]:
        """Return ``(points, is_stale)`` for up to ``MAX_POINTS`` coordinates, in order.

        Raises:
            ValueError: if no points or too many are given.
            UpstreamError: if the provider fails and nothing is cached.
        """
        if not 1 <= len(points) <= MAX_POINTS:
            raise ValueError(f"between 1 and {MAX_POINTS} points are required")
        coords = [(round_coord(lat), round_coord(lon)) for lat, lon in points]
        key = "points:" + ";".join(f"{lat},{lon}" for lat, lon in coords)
        return await self._cache.get_or_load(key, lambda: self._fetch(coords))

    async def _fetch(self, coords: list[tuple[float, float]]) -> list[GridPoint]:
        params = {
            "latitude": ",".join(str(c[0]) for c in coords),
            "longitude": ",".join(str(c[1]) for c in coords),
            "current": ",".join(AIR_VARIABLES),
            "timezone": "auto",
        }
        try:
            response = await self._http.get(AIR_QUALITY_URL, params=params)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise UpstreamError("Grid request failed") from exc
        try:
            return parse_grid(coords, payload)
        except (KeyError, TypeError, ValueError) as exc:
            raise UpstreamError("Unexpected grid response format") from exc


def parse_grid(coords: list[tuple[float, float]], payload: Any) -> list[GridPoint]:
    """Pair requested coordinates with the provider's per-point results."""
    rows = payload if isinstance(payload, list) else [payload]
    if len(rows) != len(coords):
        raise ValueError("grid size mismatch")
    return [
        GridPoint(
            lat=lat,
            lon=lon,
            pollutants=parse_pollutants({k: row["current"].get(k) for k in AIR_VARIABLES}),
        )
        for (lat, lon), row in zip(coords, rows, strict=True)
    ]
