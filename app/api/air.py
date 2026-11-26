"""City search and live air-quality dashboard data (no AI involved)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_air_service, get_geocoding_service, rate_limit
from app.engine.aqi import aqi_series
from app.engine.facts import current_point
from app.engine.risk import Intensity, Sensitivity, outdoor_guidance
from app.engine.windows import Activity, TimeWindow, best_window
from app.models.api import (
    AirResponse,
    CurrentConditions,
    ForecastHour,
    GeocodeResponse,
    Location,
    WindowOut,
)
from app.services.air_quality import AirQualityService
from app.services.geocoding import GeocodingService

router = APIRouter(prefix="/api", tags=["air"], dependencies=[Depends(rate_limit("read"))])

QUERY_PATTERN = r"^[\w\s,.'\-]+$"
DASHBOARD_ACTIVITIES = (Activity.WALK, Activity.JOG, Activity.PLAY, Activity.COMMUTE)


@router.get("/geocode")
async def geocode(
    q: Annotated[str, Query(min_length=2, max_length=80, pattern=QUERY_PATTERN)],
    service: Annotated[GeocodingService, Depends(get_geocoding_service)],
) -> GeocodeResponse:
    """Search for a city by name."""
    return GeocodeResponse(results=await service.search(q))


@router.get("/air")
async def air(
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
    service: Annotated[AirQualityService, Depends(get_air_service)],
) -> AirResponse:
    """Current AQI, 24-hour forecast and best activity windows for a location."""
    data, stale = await service.get_air_data(lat, lon)
    series = aqi_series(data.forecast)
    now = current_point(data, series)
    guidance = outdoor_guidance(now.category, Sensitivity.STANDARD, Intensity.LIGHT)

    return AirResponse(
        location=Location(lat=data.lat, lon=data.lon),
        timezone=data.timezone,
        current=CurrentConditions(
            time=data.current.time,
            aqi=now.aqi,
            category=now.category,
            label=now.category.label,
            dominant=now.dominant,
            advice=guidance.advice,
            guidance=guidance.text,
            pollutants=data.current.pollutants,
            weather=data.current.weather,
        ),
        forecast=[
            ForecastHour(
                time=p.time,
                aqi=p.aqi,
                category=p.category,
                label=p.category.label,
                advice=outdoor_guidance(p.category, Sensitivity.STANDARD).advice,
            )
            for p in series
        ],
        best_windows={a.value: _window_out(best_window(series, a)) for a in DASHBOARD_ACTIVITIES},
        stale=stale,
    )


def _window_out(window: TimeWindow | None) -> WindowOut | None:
    if window is None:
        return None
    return WindowOut(
        activity=window.activity.value,
        start=window.start,
        end=window.end,
        avg_aqi=window.avg_aqi,
        category=window.category,
        label=window.category.label,
        advice=window.advice,
        guidance=window.guidance,
    )
