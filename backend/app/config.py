from __future__ import annotations

import secrets
import warnings
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "test", "production"]

# Placeholder secrets that must never be used outside local development.
_INSECURE_SECRETS = {
    "",
    "change-me",
    "dev-secret-key-for-local-testing-only",
    "secret",
    "changeme",
}


class Settings(BaseSettings):
    app_env: Environment = Field("development", alias="APP_ENV")

    # SQLite works out of the box for local dev/tests; Postgres for real deploys.
    database_url: str = Field(
        "sqlite+aiosqlite:///./patentgate.db", alias="DATABASE_URL"
    )

    jwt_secret: str = Field("", alias="JWT_SECRET")
    jwt_algorithm: str = Field("HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(14, alias="REFRESH_TOKEN_EXPIRE_DAYS")

    # Comma-separated list of allowed browser origins.
    cors_origins: str = Field("http://localhost:3000", alias="CORS_ORIGINS")

    # Kept for backwards compatibility with the earlier single-origin variable.
    frontend_origin: str | None = Field(None, alias="FRONTEND_ORIGIN")

    # Standalone Agent 1 server, used only when IN_PROCESS_AGENTS is false.
    agent1_server_url: str = Field("http://localhost:8001", alias="AGENT1_SERVER_URL")
    in_process_agents: bool = Field(True, alias="IN_PROCESS_AGENTS")

    log_level: str = Field("INFO", alias="LOG_LEVEL")
    log_json: bool = Field(True, alias="LOG_JSON")

    # Max JSON request body accepted by the API, in bytes (1 MiB default).
    max_request_bytes: int = Field(1_048_576, alias="MAX_REQUEST_BYTES")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def allowed_origins(self) -> list[str]:
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        if self.frontend_origin and self.frontend_origin not in origins:
            origins.append(self.frontend_origin)
        return origins

    @field_validator("jwt_algorithm")
    @classmethod
    def _known_algorithm(cls, value: str) -> str:
        allowed = {"HS256", "HS384", "HS512"}
        if value not in allowed:
            raise ValueError(f"JWT_ALGORITHM must be one of {sorted(allowed)}")
        return value

    @model_validator(mode="after")
    def _enforce_secret_policy(self) -> Settings:
        weak = self.jwt_secret.strip() in _INSECURE_SECRETS or len(self.jwt_secret) < 32
        if weak:
            if self.is_production:
                raise ValueError(
                    "JWT_SECRET must be set to a strong (>=32 char) random value "
                    "in production. Generate one with: python -c "
                    "\"import secrets; print(secrets.token_urlsafe(48))\""
                )
            # Development / test: fall back to an ephemeral secret so the app
            # still boots, but make it loud - tokens will not survive a restart.
            object.__setattr__(self, "jwt_secret", secrets.token_urlsafe(48))
            warnings.warn(
                "JWT_SECRET is unset or weak; using a random ephemeral secret for "
                "this process. Set JWT_SECRET in backend/.env for stable sessions.",
                stacklevel=2,
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
