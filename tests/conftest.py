from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest

os.environ.setdefault("APP_API_KEYS", "test-api-key")

from profile_refinery_api.config import Settings  # noqa: E402
from profile_refinery_api.errors import ProblemError, UpstreamOperationDrift  # noqa: E402
from profile_refinery_api.main import create_app  # noqa: E402
from profile_refinery_api.models import OperationResult  # noqa: E402
from profile_refinery_api.runtime import Runtime  # noqa: E402

FULL_PROFILE_FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "raw" / "full_profile.json").read_text(encoding="utf-8")
)


class StubTransport:
    """Scriptable in-process transport standing in for the LinkedIn HTTP client."""

    def __init__(self) -> None:
        self.call_count = 0
        self.script: dict[str, list[Any]] = {}
        self.slug_script: dict[tuple[str, str], list[Any]] = {}
        self.seen: list[tuple[str, str]] = []

    def set(self, semantic_name: str, outcomes: list[Any]) -> None:
        self.script[semantic_name] = list(outcomes)

    def set_for_slug(self, semantic_name: str, slug: str, outcomes: list[Any]) -> None:
        self.slug_script[(semantic_name, slug)] = list(outcomes)

    async def execute(
        self, semantic_name: str, slug: str, request_id: str, resource_id: str | None = None
    ) -> OperationResult:
        self.call_count += 1
        self.seen.append((semantic_name, slug))
        queue = self.slug_script.get((semantic_name, slug))
        if queue is None:
            queue = self.script.get(semantic_name)
        if queue is None:
            payload = json.loads(json.dumps(FULL_PROFILE_FIXTURE))
        else:
            if not queue:
                raise UpstreamOperationDrift(semantic_name, "Scripted upstream queue exhausted.")
            outcome = queue.pop(0)
            if isinstance(outcome, Exception):
                raise outcome
            payload = outcome
        return OperationResult(
            operation=semantic_name, payload=payload, duration_ms=5.0, status_code=200
        )

    async def aclose(self) -> None:
        return None


@pytest.fixture
def stub_transport() -> StubTransport:
    return StubTransport()


@pytest.fixture
def settings() -> Settings:
    return Settings(
        app_api_keys=["test-api-key"],
        app_mode="live",
        app_rate_limit_requests=1000,
        app_schema_path="schemas/profile-response.schema.json",
        app_operation_registry_path="config/operation_registry.yaml",
        linkedin_li_at="test-session",
        linkedin_jsessionid='"ajax:fixture-test"',
        # High breaker threshold: request-mapping tests assert error typing,
        # not breaker transitions (those have dedicated tests).
        app_breaker_failure_threshold=50,
        app_store_dir="./.profile_refinery_store_test",
    )


@pytest.fixture
async def runtime(settings: Settings, stub_transport: StubTransport) -> AsyncIterator[Runtime]:
    active_runtime = Runtime(settings, transport=stub_transport)
    yield active_runtime
    await active_runtime.aclose()


@pytest.fixture
async def client(runtime: Runtime) -> AsyncIterator[httpx.AsyncClient]:
    application = create_app(runtime=runtime)
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"X-API-Key": "test-api-key"}


__all__ = ["StubTransport", "ProblemError", "FULL_PROFILE_FIXTURE"]
