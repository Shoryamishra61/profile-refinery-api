from __future__ import annotations

import tempfile
from enum import StrEnum
from pathlib import Path
from typing import Annotated

from pydantic import BeforeValidator, Field, SecretStr
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class AppMode(StrEnum):
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

    # Optional keys protect operator-only endpoints. The public request-scoped
    # extraction desk does not invent or require a product-specific API key.
    app_api_keys: ApiKeys = Field(default_factory=list)
    # Optional additive key used for controlled deployment verification and
    # rotation without invalidating existing callers.
    app_validation_api_key: SecretStr | None = None
    app_mode: AppMode = AppMode.LIVE
    app_rate_limit_requests: int = Field(default=30, ge=1, le=10_000)
    app_rate_limit_window_seconds: int = Field(default=60, ge=1, le=3_600)
    app_schema_path: Path = Path("schemas/profile-response.schema.json")
    app_operation_registry_path: Path = Path("config/operation_registry.yaml")
    app_upstream_timeout_seconds: float = Field(default=12.0, gt=0, le=60)
    # Activity Flight currently carries the target identity resolver in a
    # 5-7 MB stream. Eight MB is a measured protocol ceiling, not an open-ended
    # download allowance; the transport still aborts while streaming.
    app_upstream_max_bytes: int = Field(default=8_000_000, ge=1024, le=20_000_000)
    app_upstream_retries: int = Field(default=1, ge=0, le=3)
    # Upstream governor: the single control plane for all LinkedIn traffic.
    app_upstream_concurrency: int = Field(default=2, ge=1, le=10)
    app_upstream_bucket_capacity: int = Field(default=4, ge=1, le=500)
    app_upstream_refill_per_minute: float = Field(default=12.0, gt=0, le=6000)
    app_breaker_failure_threshold: int = Field(default=3, ge=1, le=200)
    app_breaker_cooldown_seconds: float = Field(default=300.0, gt=0, le=3600)
    # Durable job journal directory (survives warm process restarts).
    # Serverless deployment filesystems are read-only outside their temporary
    # directory. Callers that need durable batch storage must override this.
    app_store_dir: Path = Path(tempfile.gettempdir()) / "profile_refinery_store"
    app_batch_max_urls: int = Field(default=200, ge=1, le=5_000)
    app_batch_max_file_bytes: int = Field(default=5_242_880, ge=1024, le=52_428_800)
    app_batch_concurrency: int = Field(default=3, ge=1, le=10)
    app_batch_time_budget_seconds: float = Field(default=8.0, gt=0, le=60)
    linkedin_li_at: SecretStr | None = None
    linkedin_jsessionid: SecretStr | None = None
    # Optional full session context in raw `Cookie:` header form
    # ("name=value; name=value"). Supplements li_at/JSESSIONID with the
    # companion cookies a real browser session carries.
    linkedin_cookie: SecretStr | None = None
    # Optional single, operator-managed egress proxy. This is deliberately one
    # static endpoint: the service never rotates proxies or selects identities.
    linkedin_egress_proxy: SecretStr | None = None
    linkedin_user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )
    linkedin_accept_language: str = "en-US,en;q=0.9,hi;q=0.8,en-IN;q=0.7"

    @property
    def api_key_values(self) -> tuple[str, ...]:
        values = [key.get_secret_value() for key in self.app_api_keys]
        if self.app_validation_api_key:
            values.append(self.app_validation_api_key.get_secret_value())
        return tuple(values)
