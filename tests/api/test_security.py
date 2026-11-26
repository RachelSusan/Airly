from collections.abc import Callable

from fastapi.testclient import TestClient

from app.security.rate_limit import SlidingWindowLimiter

MakeClient = Callable[..., TestClient]


def test_rate_limit_returns_429_with_retry_after(make_client: MakeClient) -> None:
    client = make_client()
    client.app.state.limiters["read"] = SlidingWindowLimiter(limit=2)
    for _ in range(2):
        assert client.get("/api/scenarios").status_code == 200
    response = client.get("/api/scenarios")
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "rate_limited"
    assert int(response.headers["Retry-After"]) >= 1
    assert "Content-Security-Policy" in response.headers


def test_rate_limit_can_be_disabled(make_client: MakeClient) -> None:
    client = make_client(rate_limit_enabled=False)
    client.app.state.limiters["read"] = SlidingWindowLimiter(limit=1)
    assert all(client.get("/api/scenarios").status_code == 200 for _ in range(3))


def test_oversized_body_rejected(make_client: MakeClient) -> None:
    response = make_client().post(
        "/api/chat", content=b"x" * 40_000, headers={"content-type": "application/json"}
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"


def test_malformed_json_is_validation_error(make_client: MakeClient) -> None:
    response = make_client().post(
        "/api/plan", content=b"{not json", headers={"content-type": "application/json"}
    )
    assert response.status_code == 422


def test_unknown_route_uses_error_format(make_client: MakeClient) -> None:
    response = make_client().get("/api/nope")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_errors_do_not_leak_internals(make_client: MakeClient) -> None:
    client = make_client()
    client.app.state.geocoding_service = None  # force an unexpected server error
    response = client.get("/api/geocode", params={"q": "Delhi"})
    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "internal_error", "message": "Something went wrong. Please try again."}
    }


def test_limiter_window_resets() -> None:
    now = [0.0]
    limiter = SlidingWindowLimiter(limit=1, window=10, clock=lambda: now[0])
    assert limiter.hit("a") is None
    assert limiter.hit("a") == 10
    assert limiter.hit("b") is None
    now[0] = 10.5
    assert limiter.hit("a") is None
