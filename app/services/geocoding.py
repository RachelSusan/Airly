"""City search via the Open-Meteo Geocoding API (free, no API key)."""

from __future__ import annotations

from typing import Any

import httpx

from app.models.air import Place
from app.services.cache import TTLCache
from app.services.errors import UpstreamError

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
MAX_RESULTS = 5


class GeocodingService:
    """Looks up places by name, with caching."""

    def __init__(self, http: httpx.AsyncClient, cache: TTLCache[list[Place]]) -> None:
        self._http = http
        self._cache = cache

    async def search(self, query: str) -> list[Place]:
        """Return up to ``MAX_RESULTS`` places matching ``query``.

        Raises:
            UpstreamError: if the provider fails and nothing is cached.
        """
        normalised = " ".join(query.split()).lower()
        if not normalised:
            return []
        places, _ = await self._cache.get_or_load(
            f"geo:{normalised}", lambda: self._fetch(normalised)
        )
        return places

    async def _fetch(self, query: str) -> list[Place]:
        params = {"name": query, "count": MAX_RESULTS, "language": "en", "format": "json"}
        try:
            response = await self._http.get(GEOCODING_URL, params=params)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise UpstreamError("Geocoding request failed") from exc
        return parse_places(payload)


def parse_places(payload: dict[str, Any]) -> list[Place]:
    """Convert a geocoding response into ``Place`` models, skipping malformed rows."""
    places: list[Place] = []
    for row in payload.get("results") or []:
        try:
            places.append(
                Place(
                    name=row["name"],
                    admin=row.get("admin1"),
                    country=row.get("country"),
                    lat=round(float(row["latitude"]), 2),
                    lon=round(float(row["longitude"]), 2),
                    timezone=row.get("timezone"),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return places
