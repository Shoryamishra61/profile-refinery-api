from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from tross_linkedin_api.config import Settings
from tross_linkedin_api.errors import UpstreamTimeout
from tross_linkedin_api.main import create_app
from tross_linkedin_api.models import OperationResult
from tross_linkedin_api.runtime import Runtime
from tross_linkedin_api.transport import FixtureTransport


class FailingSectionTransport(FixtureTransport):
    async def execute(self, semantic_name: str, slug: str, request_id: str) -> OperationResult:
        if semantic_name == "skills":
            raise UpstreamTimeout("skills")
        return await super().execute(semantic_name, slug, request_id)


@pytest.mark.asyncio
async def test_optional_failure_returns_200_partial(settings: Settings) -> None:
    base = Runtime(settings)
    transport = FailingSectionTransport(base.registry, Path("tests/fixtures/raw"))
    await base.aclose()
    runtime = Runtime(settings, transport=transport)
    app = create_app(runtime=runtime)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/v1/profiles",
            params={"url": "https://linkedin.com/in/synthetic-profile"},
            headers={"X-API-Key": "test-api-key"},
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["partial"] is True
    assert body["profile"]["skills"]["status"] == "upstream_failed"
    assert body["profile"]["skills"]["value"] is None
    assert body["profile"]["experience"]["status"] == "present"


@pytest.mark.asyncio
async def test_caller_rate_limit_is_429() -> None:
    settings = Settings(
        app_api_keys=["rate-key"],
        app_mode="fixture",
        app_rate_limit_requests=1,
        app_rate_limit_window_seconds=60,
    )
    app = create_app(settings)
    params = {"url": "https://linkedin.com/in/synthetic-profile"}
    headers = {"X-API-Key": "rate-key"}
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        assert (await client.get("/v1/profiles", params=params, headers=headers)).status_code == 200
        limited = await client.get("/v1/profiles", params=params, headers=headers)
    assert limited.status_code == 429
    assert limited.json()["code"] == "CALLER_RATE_LIMITED"
    assert int(limited.headers["retry-after"]) >= 1
