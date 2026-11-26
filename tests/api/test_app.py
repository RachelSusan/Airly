from fastapi.testclient import TestClient

from app import __version__
from app.config import Settings
from app.main import create_app
from app.security.headers import CONTENT_SECURITY_POLICY


def _client(**overrides: object) -> TestClient:
    return TestClient(create_app(Settings(**overrides)))


def test_health_ok() -> None:
    response = _client().get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__}


def test_security_headers_present() -> None:
    response = _client().get("/api/health")
    assert response.headers["Content-Security-Policy"] == CONTENT_SECURITY_POLICY
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "Strict-Transport-Security" not in response.headers


def test_production_adds_hsts_and_hides_docs() -> None:
    client = _client(app_env="production")
    assert "Strict-Transport-Security" in client.get("/api/health").headers
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_development_exposes_docs() -> None:
    assert _client().get("/docs").status_code == 200


def test_settings_ai_enabled_flag() -> None:
    assert Settings(anthropic_api_key="abc").ai_enabled is True
    assert Settings(anthropic_api_key="").ai_enabled is False


def test_api_key_is_not_revealed_in_repr() -> None:
    settings = Settings(anthropic_api_key="super-secret")
    assert "super-secret" not in repr(settings)
