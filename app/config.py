"""Application settings, loaded from environment variables (and a local ``.env`` file)."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PLACEHOLDER_API_KEY = "your-gemini-api-key-here"  # value shipped in .env.example


class Settings(BaseSettings):
    """Runtime configuration. Secrets never have defaults and are never logged."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-2.5-flash"
    app_env: Literal["development", "production"] = "development"
    log_level: str = "INFO"
    air_cache_ttl_seconds: int = Field(default=900, ge=60, le=3600)
    rate_limit_enabled: bool = True

    @property
    def is_production(self) -> bool:
        """True when running in production (docs off, HSTS on)."""
        return self.app_env == "production"

    @property
    def ai_enabled(self) -> bool:
        """True when a real Gemini API key is configured (not blank, not the placeholder)."""
        if self.gemini_api_key is None:
            return False
        key = self.gemini_api_key.get_secret_value().strip()
        return bool(key) and key != PLACEHOLDER_API_KEY


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings instance."""
    return Settings()
