from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
import pytest
from conftest import StubTransport

from tross_linkedin_api.canonicalizer import canonicalize_profile_url
from tross_linkedin_api.config import Settings
from tross_linkedin_api.errors import LiveFixtureLeakDetected
from tross_linkedin_api.main import create_app
from tross_linkedin_api.operation_registry import OperationRegistry
from tross_linkedin_api.orchestrator import ProfileOrchestrator
from tross_linkedin_api.runtime import Runtime
from tross_linkedin_api.validation import SchemaValidator


def test_live_mode_without_session_fails_closed() -> None:
    settings = Settings(
        app_api_keys=["live-test-key"],
        app_mode="live",
        app_operation_registry_path="config/operation_registry.yaml",
        app_schema_path="schemas/profile-response.schema.json",
    )
    app = create_app(settings)

    async def scenario() -> tuple[httpx.Response, httpx.Response]:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            readiness = await client.get("/readyz")
            response = await client.get(
                "/v1/profiles",
                params={"url": "https://www.linkedin.com/in/some-real-person/"},
                headers={"X-API-Key": "live-test-key"},
            )
            return readiness, response

    readiness, response = asyncio.run(scenario())
    assert readiness.status_code == 503
    assert response.status_code == 503
    assert response.json()["code"] == "UPSTREAM_AUTH_REQUIRED"
    assert "SYNTHETIC-001" not in response.text


def test_readiness_turns_green_with_configured_session() -> None:
    settings = Settings(
        app_api_keys=["live-test-key"],
        app_mode="live",
        app_operation_registry_path="config/operation_registry.yaml",
        app_schema_path="schemas/profile-response.schema.json",
        linkedin_li_at="configured",
        linkedin_jsessionid='"ajax:configured"',
    )
    runtime = Runtime(settings, transport=StubTransport())
    assert runtime.ready is True


def test_live_response_rejects_fixture_sentinels() -> None:
    registry = OperationRegistry.load(Path("config/operation_registry.yaml"))
    orchestrator = ProfileOrchestrator(
        registry,
        _SentinelTransport(),
        SchemaValidator(Path("schemas/profile-response.schema.json")),
    )
    with pytest.raises(LiveFixtureLeakDetected):
        asyncio.run(
            orchestrator.fetch(
                canonicalize_profile_url("https://www.linkedin.com/in/real-profile"),
                "fixture-leak-regression",
            )
        )


class _SentinelTransport:
    call_count = 1

    async def execute(
        self, semantic_name: str, slug: str, request_id: str, resource_id: str | None = None
    ) -> object:
        from tross_linkedin_api.models import OperationResult

        payload = {
            "data": {"*elements": ["urn:li:fsd_profile:SYNTHETIC-001"]},
            "included": [
                {
                    "$type": "com.linkedin.voyager.dash.identity.profile.Profile",
                    "entityUrn": "urn:li:fsd_profile:SYNTHETIC-001",
                    "firstName": {"localized": {"en_US": "Synthetic"}},
                    "lastName": {"localized": {"en_US": "Sentinel"}},
                }
            ],
        }
        return OperationResult(
            operation=semantic_name, payload=payload, duration_ms=1.0, status_code=200
        )

    async def aclose(self) -> None:
        return None
