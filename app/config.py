"""Application settings, loaded from environment variables (and a local ``.env`` file)."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. Secrets never have defaults and are never logged."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    anthropic_api_key: SecretStr | None = None
    claude_model: str = "claude-opus-5-5"
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
        """True when an Anthropic API key is configured."""
        return bool(self.anthropic_api_key and self.anthropic_api_key.get_secret_value())


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings instance."""
    return Settings()
