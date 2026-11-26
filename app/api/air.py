"""City search and live air-quality dashboard data (no AI involved)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_air_service, get_geocoding_service, get_grid_service, rate_limit
from app.engine.aqi import InsufficientDataError, aqi_series, compute_aqi
from app.engine.facts import NoAirDataError, current_point
from app.engine.risk import Sensitivity, outdoor_guidance
from app.engine.windows import Activity, TimeWindow, best_window
from app.models.api import (
    AirGridResponse,
    AirResponse,
    CurrentConditions,
    ForecastHour,
    GeocodeResponse,
    GridCell,
    Location,
    WindowOut,
)
from app.services.air_grid import GRID_STEP_DEG, AirGridService
from app.services.air_quality import AirQualityService, round_coord
from app.services.geocoding import GeocodingService

router = APIRouter(prefix="/api", tags=["air"], dependencies=[Depends(rate_limit("read"))])

QUERY_PATTERN = r"^[\w\s,.'\-]+$"
GRID_NOTE = (
    "Modelled regional air quality (about 10-40 km resolution). It shows broad patterns "
    "around you, not differences between individual streets."
)
DASHBOARD_ACTIVITIES = (Activity.WALK, Activity.JOG, Activity.PLAY, Activity.COMMUTE)


@router.get("/geocode")
async def geocode(
    q: Annotated[str, Query(min_length=2, max_length=80, pattern=QUERY_PATTERN)],
    service: Annotated[GeocodingService, Depends(get_geocoding_service)],
    country: Annotated[str | None, Query(pattern=r"^[A-Z]{2}$")] = None,
) -> GeocodeResponse:
    """Search for a city by name, optionally limited to one country (e.g. ``IN``)."""
    return GeocodeResponse(results=await service.search(q, country))


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
    guidance = outdoor_guidance(now.category, Sensitivity.STANDARD)

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


@router.get("/air/grid")
async def air_grid(
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
    service: Annotated[AirGridService, Depends(get_grid_service)],
) -> AirGridResponse:
    """Current AQI on a grid around the location, for the neighbourhood map."""
    points, stale = await service.get_grid(lat, lon)
    cells = []
    for point in points:
        try:
            result = compute_aqi(point.pollutants.as_mapping())
        except InsufficientDataError:
            continue
        cells.append(
            GridCell(
                lat=point.lat,
                lon=point.lon,
                aqi=result.aqi,
                category=result.category,
                label=result.category.label,
                dominant=result.dominant,
                pm2_5=point.pollutants.pm2_5,
            )
        )
    if not cells:
        raise NoAirDataError("No grid data")
    return AirGridResponse(
        center=Location(lat=round_coord(lat), lon=round_coord(lon)),
        step_deg=GRID_STEP_DEG,
        cells=cells,
        stale=stale,
        note=GRID_NOTE,
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
