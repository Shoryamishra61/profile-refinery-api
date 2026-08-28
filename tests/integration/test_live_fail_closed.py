from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from tross_linkedin_api.canonicalizer import canonicalize_profile_url
from tross_linkedin_api.config import AppMode, Settings
from tross_linkedin_api.errors import LiveFixtureLeakDetected
from tross_linkedin_api.main import create_app
from tross_linkedin_api.operation_registry import OperationRegistry
from tross_linkedin_api.orchestrator import ProfileOrchestrator
from tross_linkedin_api.transport import FixtureTransport
from tross_linkedin_api.validation import SchemaValidator


@pytest.mark.asyncio
async def test_live_mode_without_verified_operation_returns_explicit_503() -> None:
    settings = Settings(
        app_api_keys=["live-test-key"],
        app_mode="live",
        app_operation_registry_path="config/operation_registry.yaml",
    )
    app = create_app(settings)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        readiness = await client.get("/readyz")
        assert readiness.status_code == 503
        response = await client.get(
            "/v1/profiles",
            params={"url": "https://www.linkedin.com/in/shoryakumar-mishra/"},
            headers={"X-API-Key": "live-test-key"},
        )

    assert response.status_code == 503
    assert response.json()["code"] == "UPSTREAM_OPERATION_UNAVAILABLE"
    assert "SYNTHETIC-001" not in response.text


@pytest.mark.asyncio
async def test_live_response_rejects_fixture_sentinels() -> None:
    registry = OperationRegistry.load(
        Path("config/operation_registry.yaml"), AppMode.FIXTURE
    )
    orchestrator = ProfileOrchestrator(
        registry,
        FixtureTransport(registry, Path("tests/fixtures/raw")),
        SchemaValidator(Path("schemas/profile-response.schema.json")),
        AppMode.LIVE,
    )

    with pytest.raises(LiveFixtureLeakDetected):
        await orchestrator.fetch(
            canonicalize_profile_url("https://www.linkedin.com/in/real-profile"),
            "fixture-leak-regression",
        )
