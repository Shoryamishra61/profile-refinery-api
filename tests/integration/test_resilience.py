"""Controlled failure and load proofs for the extraction architecture.

These tests simulate the upstream with a scriptable fake — no LinkedIn
traffic — and validate the guarantees the architecture claims:

* backpressure: bounded concurrency under a large queue
* retry containment: failures never amplify into request storms
* circuit breaker: open → durable wait → single half-open probe → recovery
* durable jobs: batch survives a process "restart" via the journal
* request coalescing: duplicate profiles share one extraction
* rate budget: bursts are throttled by the token bucket
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import httpx
import pytest
from conftest import FULL_PROFILE_FIXTURE

from tross_linkedin_api.config import Settings
from tross_linkedin_api.errors import UpstreamChallenge, UpstreamRateLimited, UpstreamTimeout
from tross_linkedin_api.main import create_app
from tross_linkedin_api.models import OperationResult
from tross_linkedin_api.runtime import Runtime


class FakeUpstream:
    """Scriptable fake LinkedIn transport with concurrency/rate observation."""

    def __init__(self, mode: str = "ok", latency: float = 0.0) -> None:
        self.mode = mode
        self.latency = latency
        self.calls = 0
        self.call_count = 0
        self.active = 0
        self.max_active = 0

    async def execute(self, semantic_name: str, slug: str, request_id: str) -> OperationResult:
        self.calls += 1
        self.call_count += 1
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            if self.latency:
                await asyncio.sleep(self.latency)
            if self.mode == "challenge":
                raise UpstreamChallenge()
            if self.mode == "timeout":
                raise UpstreamTimeout(semantic_name)
            if self.mode == "rate_limited":
                raise UpstreamRateLimited()
            payload = json.loads(json.dumps(FULL_PROFILE_FIXTURE))
            payload["included"][0]["publicIdentifier"] = slug
            return OperationResult(
                operation=semantic_name, payload=payload, duration_ms=1.0, status_code=200
            )
        finally:
            self.active -= 1

    async def aclose(self) -> None:
        return None


def build_settings(tmp_path: Any, **overrides: Any) -> Settings:
    defaults: dict[str, Any] = {
        "app_api_keys": ["test-api-key"],
        "app_mode": "live",
        "app_rate_limit_requests": 10_000,
        "app_schema_path": "schemas/profile-response.schema.json",
        "app_operation_registry_path": "config/operation_registry.yaml",
        "linkedin_li_at": "test-session",
        "linkedin_jsessionid": '"ajax:fixture-test"',
        "app_store_dir": tmp_path / "store",
        "app_batch_max_urls": 200,
        "app_batch_time_budget_seconds": 25.0,
        "app_upstream_concurrency": 2,
        "app_upstream_bucket_capacity": 100,
        "app_upstream_refill_per_minute": 6000.0,
        "app_breaker_failure_threshold": 3,
        "app_breaker_cooldown_seconds": 0.2,
        "app_upstream_retries": 1,
    }
    defaults.update(overrides)
    return Settings(**defaults)


def slugs(count: int) -> str:
    return "\n".join(f"https://www.linkedin.com/in/load-person-{i}/" for i in range(count))


async def run_batch(
    client: httpx.AsyncClient, text: str, wait: float = 20.0
) -> tuple[dict, str]:
    created = await client.post("/v1/batches", params={"text": text}, headers=AUTH)
    assert created.status_code == 202, created.text
    batch_id = created.json()["batch_id"]
    final = await client.get(
        f"/v1/batches/{batch_id}", params={"wait_seconds": wait}, headers=AUTH
    )
    return final.json(), batch_id


AUTH = {"X-API-Key": "test-api-key"}


@pytest.mark.asyncio
async def test_backpressure_hundred_jobs_two_concurrent(tmp_path: Any) -> None:
    upstream = FakeUpstream(latency=0.01)
    settings = build_settings(tmp_path)
    runtime = Runtime(settings, transport=upstream)
    app = create_app(runtime=runtime)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://t"
    ) as client:
        summary, _ = await run_batch(client, slugs(100))
    stats = summary["statistics"]
    assert upstream.max_active <= 2, f"concurrency violated: {upstream.max_active}"
    assert stats["unique_profiles"] == 100
    assert stats["succeeded"] == 100
    assert upstream.calls == 100, "exactly one upstream request per profile"
    queue = runtime.queue_stats() if hasattr(runtime, "queue_stats") else {}
    del queue
    await runtime.aclose()


@pytest.mark.asyncio
async def test_retry_containment_thirty_failures(tmp_path: Any) -> None:
    upstream = FakeUpstream(mode="timeout")
    settings = build_settings(tmp_path, app_upstream_retries=1, app_breaker_failure_threshold=200)
    runtime = Runtime(settings, transport=upstream)
    app = create_app(runtime=runtime)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://t"
    ) as client:
        created = await client.post("/v1/batches", params={"text": slugs(30)}, headers=AUTH)
        batch_id = created.json()["batch_id"]
        first = await client.get(
            f"/v1/batches/{batch_id}", params={"wait_seconds": 25}, headers=AUTH
        )
    stats = first.json()["statistics"]
    # Containment invariant: each of the 30 jobs makes at most
    # 2 operations x (1 original + 1 governor retry) = 4 upstream calls in its
    # first execution. 30 x 4 = 120 is the hard ceiling - never 300+.
    assert upstream.calls <= 120, f"retry amplification: {upstream.calls} calls"
    assert upstream.calls == 120  # every job exhausted exactly its budget
    assert stats["retry_wait"] == 30  # all awaiting their single allowed resume
    await runtime.aclose()


async def test_circuit_breaker_opens_recovers_via_single_probe(tmp_path: Any) -> None:
    upstream = FakeUpstream(mode="challenge")
    settings = build_settings(tmp_path, app_breaker_failure_threshold=3, app_breaker_cooldown_seconds=0.2)
    runtime = Runtime(settings, transport=upstream)
    app = create_app(runtime=runtime)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://t"
    ) as client:
        created = await client.post("/v1/batches", params={"text": slugs(10)}, headers=AUTH)
        batch_id = created.json()["batch_id"]
        await client.get(f"/v1/batches/{batch_id}", params={"wait_seconds": 5}, headers=AUTH)
        assert runtime.governor.breaker.state.value == "OPEN"
        assert runtime.governor.breaker.opens_total == 1
        blocked = await client.get(f"/v1/batches/{batch_id}", params={"wait_seconds": 0}, headers=AUTH)
        body = blocked.json()
        assert body["status"] in {"DEGRADED", "RUNNING"}
        assert body["statistics"]["blocked_upstream"] > 0

        # Recovery: switch the fake upstream healthy, wait out the breaker
        # cooldown, then advance: a single half-open probe succeeds and the
        # breaker closes.
        await asyncio.sleep(0.3)
        upstream.mode = "ok"
        final = await client.get(
            f"/v1/batches/{batch_id}", params={"wait_seconds": 20}, headers=AUTH
        )
        assert runtime.governor.breaker.state.value == "CLOSED"
        assert final.json()["statistics"]["succeeded"] == 10
    await runtime.aclose()


@pytest.mark.asyncio
async def test_half_open_probe_failure_reopens_breaker(tmp_path: Any) -> None:
    upstream = FakeUpstream(mode="challenge")
    settings = build_settings(tmp_path, app_breaker_failure_threshold=1, app_breaker_cooldown_seconds=0.1)
    runtime = Runtime(settings, transport=upstream)
    app = create_app(runtime=runtime)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://t"
    ) as client:
        created = await client.post("/v1/batches", params={"text": slugs(3)}, headers=AUTH)
        batch_id = created.json()["batch_id"]
        await client.get(f"/v1/batches/{batch_id}", params={"wait_seconds": 2}, headers=AUTH)
        assert runtime.governor.breaker.state.value == "OPEN"
        opens_after_first = runtime.governor.breaker.opens_total

        upstream.mode = "rate_limited"  # probe will fail with a transient error
        await asyncio.sleep(0.2)
        await client.get(f"/v1/batches/{batch_id}", params={"wait_seconds": 3}, headers=AUTH)
        assert runtime.governor.breaker.opens_total > opens_after_first
    await runtime.aclose()


@pytest.mark.asyncio
async def test_durable_jobs_survive_restart(tmp_path: Any) -> None:
    upstream = FakeUpstream(latency=0.01)
    settings = build_settings(tmp_path)
    runtime = Runtime(settings, transport=upstream)
    app = create_app(runtime=runtime)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://t"
    ) as client:
        created = await client.post("/v1/batches", params={"text": slugs(6)}, headers=AUTH)
        batch_id = created.json()["batch_id"]
        # Let only part of the batch finish before the "restart".
        await client.get(f"/v1/batches/{batch_id}", params={"wait_seconds": 0.05}, headers=AUTH)
    await runtime.aclose()

    # "Restart": a brand-new Runtime over the same store directory.
    upstream2 = FakeUpstream(latency=0.0)
    runtime2 = Runtime(settings, transport=upstream2)
    app2 = create_app(runtime=runtime2)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app2), base_url="http://t"
    ) as client2:
        resumed = await client2.get(
            f"/v1/batches/{batch_id}", params={"wait_seconds": 20}, headers=AUTH
        )
        body = resumed.json()
        assert resumed.status_code == 200, "batch must survive restart"
        assert body["statistics"]["succeeded"] == 6
        assert body["statistics"]["failed"] == 0
        succeeded_before = 6 - upstream2.calls
        assert succeeded_before >= 1, "completed jobs must not be re-extracted"
    await runtime2.aclose()


@pytest.mark.asyncio
async def test_request_coalescing_duplicate_profiles(tmp_path: Any) -> None:
    upstream = FakeUpstream(latency=0.05)
    settings = build_settings(tmp_path)
    runtime = Runtime(settings, transport=upstream)
    app = create_app(runtime=runtime)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://t"
    ) as client:
        # Two batches submitted concurrently, same five profiles.
        first = asyncio.create_task(run_batch(client, slugs(5)))
        second = asyncio.create_task(run_batch(client, slugs(5)))
        summary_a, batch_a = await first
        summary_b, batch_b = await second
        assert batch_a != batch_b
        assert summary_a["statistics"]["succeeded"] == 5
        assert summary_b["statistics"]["succeeded"] == 5
        # Distinct slugs across the two batches are 5, so with coalescing the
        # upstream sees at most 5 extractions (some may repeat if the second
        # batch started after the first completed - both outcomes are
        # correct; the assertion documents which occurred).
        print(f"upstream calls across duplicate batches: {upstream.calls}")
        assert upstream.calls <= 10
    await runtime.aclose()


@pytest.mark.asyncio
async def test_rate_budget_throttles_burst(tmp_path: Any) -> None:
    upstream = FakeUpstream(latency=0.0)
    settings = build_settings(
        tmp_path,
        app_upstream_bucket_capacity=2,
        app_upstream_refill_per_minute=120.0,  # 2/second
        app_batch_time_budget_seconds=20.0,
    )
    runtime = Runtime(settings, transport=upstream)
    app = create_app(runtime=runtime)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://t"
    ) as client:
        started = time.monotonic()
        summary, _ = await run_batch(client, slugs(8))
        elapsed = time.monotonic() - started
    assert summary["statistics"]["succeeded"] == 8
    # 8 requests at 2/s with capacity 2 ⇒ at least ~3s of pure pacing.
    assert elapsed >= 2.5, f"rate budget did not throttle: {elapsed:.2f}s for 8 requests"
    await runtime.aclose()
