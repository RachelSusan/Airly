import httpx
import pytest
import respx

from app.models.air import GridPoint
from app.services.air_grid import GRID_SIZE, AirGridService, grid_coordinates, parse_grid
from app.services.air_quality import AIR_QUALITY_URL
from app.services.cache import TTLCache
from app.services.errors import UpstreamError


def test_grid_coordinates_square_around_centre() -> None:
    coords = grid_coordinates(28.61, 77.21)
    assert len(coords) == GRID_SIZE * GRID_SIZE
    assert (28.61, 77.21) in coords
    assert min(c[0] for c in coords) == 28.31
    assert max(c[1] for c in coords) == 77.51


def test_grid_coordinates_wrap_longitude_and_clip_poles() -> None:
    coords = grid_coordinates(89.95, 179.95)
    assert all(-90 <= lat <= 90 for lat, _ in coords)
    assert all(-180 <= lon < 180 for _, lon in coords)
    assert len(coords) < GRID_SIZE * GRID_SIZE


def test_parse_grid_rejects_size_mismatch() -> None:
    with pytest.raises(ValueError, match="mismatch"):
        parse_grid([(1.0, 1.0), (2.0, 2.0)], [{"current": {}}])


def _service(client: httpx.AsyncClient) -> AirGridService:
    return AirGridService(client, TTLCache[list[GridPoint]](ttl=900, max_entries=5))


def _row(pm: float) -> dict:
    return {"current": {"pm2_5": pm, "pm10": None, "carbon_monoxide": 1000.0}}


@respx.mock
async def test_get_grid_single_request_and_parse() -> None:
    route = respx.get(AIR_QUALITY_URL).mock(
        return_value=httpx.Response(200, json=[_row(10.0 + i) for i in range(49)])
    )
    async with httpx.AsyncClient() as client:
        points, stale = await _service(client).get_grid(28.613, 77.209)
    assert route.call_count == 1
    assert stale is False
    assert len(points) == 49
    assert points[0].pollutants.pm2_5 == 10.0
    assert points[0].pollutants.co == 1.0
    assert len(route.calls.last.request.url.params["latitude"].split(",")) == 49


@respx.mock
async def test_get_grid_errors_become_upstream_error() -> None:
    respx.get(AIR_QUALITY_URL).mock(return_value=httpx.Response(200, json=[_row(1.0)]))
    async with httpx.AsyncClient() as client:
        with pytest.raises(UpstreamError):
            await _service(client).get_grid(10, 10)


@respx.mock
async def test_get_grid_http_error() -> None:
    respx.get(AIR_QUALITY_URL).mock(return_value=httpx.Response(500))
    async with httpx.AsyncClient() as client:
        with pytest.raises(UpstreamError):
            await _service(client).get_grid(10, 10)


@respx.mock
async def test_get_points_keeps_order_and_caches() -> None:
    route = respx.get(AIR_QUALITY_URL).mock(
        return_value=httpx.Response(200, json=[_row(5.0), _row(50.0)])
    )
    async with httpx.AsyncClient() as client:
        service = _service(client)
        points, _ = await service.get_points([(19.076, 72.877), (28.61, 77.21)])
        await service.get_points([(19.076, 72.877), (28.61, 77.21)])
    assert [(p.lat, p.pollutants.pm2_5) for p in points] == [(19.08, 5.0), (28.61, 50.0)]
    assert route.call_count == 1


@pytest.mark.parametrize("count", [0, 81])
async def test_get_points_rejects_bad_count(count: int) -> None:
    async with httpx.AsyncClient() as client:
        with pytest.raises(ValueError, match="points"):
            await _service(client).get_points([(1.0, 1.0)] * count)
