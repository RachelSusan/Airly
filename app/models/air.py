"""Air-quality and weather data models (see docs/database.md, section 3)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Pollutants(_Frozen):
    """Pollutant concentrations. µg/m³ for all except CO, which is mg/m³."""

    pm2_5: float | None = None
    pm10: float | None = None
    no2: float | None = None
    o3: float | None = None
    co: float | None = Field(default=None, description="Carbon monoxide in mg/m³")
    so2: float | None = None

    def as_mapping(self) -> dict[str, float | None]:
        """Return concentrations keyed by pollutant code (matches ``engine.aqi.Pollutant``)."""
        return self.model_dump()


class Weather(_Frozen):
    """Weather conditions relevant to air quality and ventilation."""

    temperature_c: float | None = None
    humidity_pct: float | None = None
    wind_kmh: float | None = None
    precip_mm: float | None = None


class HourlyReading(_Frozen):
    """Pollutants and weather for one hour (local time of the location)."""

    time: datetime
    pollutants: Pollutants
    weather: Weather


class Place(_Frozen):
    """A geocoded place."""

    name: str
    admin: str | None = None
    country: str | None = None
    lat: float
    lon: float
    timezone: str | None = None


class AirData(_Frozen):
    """Current conditions plus the hourly forecast for one location."""

    lat: float
    lon: float
    timezone: str
    current: HourlyReading
    forecast: list[HourlyReading]
