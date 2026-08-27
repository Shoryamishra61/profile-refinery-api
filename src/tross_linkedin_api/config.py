from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Annotated

from pydantic import BeforeValidator, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class AppMode(StrEnum):
    FIXTURE = "fixture"
    LIVE = "live"


def _split_keys(value: object) -> object:
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return value


ApiKeys = Annotated[list[SecretStr], NoDecode, BeforeValidator(_split_keys)]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
        case_sensitive=False,
    )

    app_api_keys: ApiKeys = Field(min_length=1)
    app_mode: AppMode = AppMode.FIXTURE
    app_rate_limit_requests: int = Field(default=30, ge=1, le=10_000)
    app_rate_limit_window_seconds: int = Field(default=60, ge=1, le=3_600)
    app_schema_path: Path = Path("schemas/profile-response.schema.json")
    app_operation_registry_path: Path = Path("config/operation_registry.yaml")
    app_fixture_root: Path = Path("tests/fixtures/raw")
    app_upstream_timeout_seconds: float = Field(default=12.0, gt=0, le=60)
    app_upstream_max_bytes: int = Field(default=5_000_000, ge=1024, le=20_000_000)
    app_upstream_retries: int = Field(default=1, ge=0, le=2)
    linkedin_li_at: SecretStr | None = None
    linkedin_jsessionid: SecretStr | None = None

    @model_validator(mode="after")
    def validate_mode_requirements(self) -> Settings:
        if self.app_mode is AppMode.LIVE:
            missing = []
            if not self.linkedin_li_at or not self.linkedin_li_at.get_secret_value():
                missing.append("LINKEDIN_LI_AT")
            if not self.linkedin_jsessionid or not self.linkedin_jsessionid.get_secret_value():
                missing.append("LINKEDIN_JSESSIONID")
            if missing:
                raise ValueError(f"live mode requires runtime secrets: {', '.join(missing)}")
        return self

    @property
    def api_key_values(self) -> tuple[str, ...]:
        return tuple(key.get_secret_value() for key in self.app_api_keys)
