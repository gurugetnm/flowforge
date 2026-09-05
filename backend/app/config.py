"""Application configuration loaded from the environment."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings.

    Values are read from the process environment, falling back to a local
    ``.env`` file so developers do not need to export anything by hand.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["development", "test", "production"] = "development"
    debug: bool = False

    database_url: str = "postgresql+psycopg://flowforge:flowforge@localhost:5432/flowforge"

    # Comma separated list of origins allowed to call the API from a browser.
    cors_origins: str = "http://localhost:3000"

    secret_key: str = Field(
        default="dev-secret-change-me",
        min_length=8,
        description="Signs session tokens. Must be overridden outside development.",
    )
    access_token_ttl_minutes: int = 60 * 12
    cookie_secure: bool = False
    cookie_name: str = "flowforge_session"

    @field_validator("database_url")
    @classmethod
    def _require_psycopg_driver(cls, value: str) -> str:
        if value.startswith("postgresql://"):
            # Normalise to the psycopg 3 driver used across the project.
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """Return the process wide settings singleton."""
    return Settings()
