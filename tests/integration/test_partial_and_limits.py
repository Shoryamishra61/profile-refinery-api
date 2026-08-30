from __future__ import annotations

import httpx
import pytest
from conftest import StubTransport

from profile_refinery_api.config import Settings
from profile_refinery_api.main import create_app
from profile_refinery_api.runtime import Runtime


@pytest.mark.asyncio
async def test_caller_rate_limit_is_429() -> None:
    settings = Settings(
        app_api_keys=["rate-key"],
        app_mode="live",
        app_rate_limit_requests=1,
        app_rate_limit_window_seconds=60,
        linkedin_li_at="configured",
        linkedin_jsessionid='"ajax:configured"',
    )
    runtime = Runtime(settings, transport=StubTransport())
    app = create_app(runtime=runtime)
    params = {"url": "https://linkedin.com/in/rate-limited-person"}
    headers = {"X-API-Key": "rate-key"}
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        # The first call consumes the single allowed request slot; with the
        # stub-free runtime it fails closed on the absent real session, but
        # the rate limiter still counts it.
        await client.get("/v1/profiles", params=params, headers=headers)
        limited = await client.get("/v1/profiles", params=params, headers=headers)
    assert limited.status_code == 429
    assert limited.json()["code"] == "CALLER_RATE_LIMITED"
    assert int(limited.headers["retry-after"]) >= 1
    await runtime.aclose()
