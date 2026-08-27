from __future__ import annotations

import os
from collections.abc import AsyncIterator

import httpx
import pytest

os.environ.setdefault("APP_API_KEYS", "test-api-key")
os.environ.setdefault("APP_MODE", "fixture")

from tross_linkedin_api.config import Settings  # noqa: E402
from tross_linkedin_api.main import create_app  # noqa: E402


@pytest.fixture
def settings() -> Settings:
    return Settings(
        app_api_keys=["test-api-key"],
        app_mode="fixture",
        app_rate_limit_requests=100,
        app_schema_path="schemas/profile-response.schema.json",
        app_operation_registry_path="config/operation_registry.yaml",
        app_fixture_root="tests/fixtures/raw",
    )


@pytest.fixture
async def client(settings: Settings) -> AsyncIterator[httpx.AsyncClient]:
    application = create_app(settings)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=application), base_url="http://test"
    ) as test_client:
        yield test_client
