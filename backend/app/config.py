"""Application configuration, loaded from environment / .env."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TRACKACTOR_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    db_url: str = "sqlite:///./trackactor.db"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # When true, every /api call (except health / docs / meta) needs a valid
    # X-API-Key, and writes need a key with the "write" scope. Off by default so
    # a fresh clone runs with no setup.
    require_key: bool = False

    # Guards the /api/keys and /api/webhooks management routes. When empty those
    # routes are open (fine for a local instance); set it once you expose them.
    admin_token: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
