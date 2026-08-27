from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx
from httpx import Response

from tross_linkedin_api.config import AppMode, Settings
from tross_linkedin_api.errors import (
    ProfileNotFound,
    UpstreamAuthExpired,
    UpstreamChallenge,
    UpstreamOperationDrift,
    UpstreamRateLimited,
    UpstreamTimeout,
)
from tross_linkedin_api.operation_registry import OperationRegistry
from tross_linkedin_api.session import SessionProvider
from tross_linkedin_api.transport import LinkedInTransport


def live_components(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Settings, OperationRegistry, SessionProvider]:
    registry_path = tmp_path / "registry.yaml"
    registry_path.write_text(
        """version: 1
operations:
  - semantic_name: profile_core
    enabled: true
    evidence_status: live_verified
    method: POST
    path: /voyager/api/graphql
    transport_family: graphql
    query_id_env: TEST_QUERY_ID
    input_variables: [member_identity]
    parser: profile_core_v1
    observed_at: 2026-08-27T12:00:00Z
    viewer_context: owned_account
    fixture: tests/fixtures/raw/profile_core.json
    evidence_reference: controlled-test
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("TEST_QUERY_ID", "test-query-id")
    settings = Settings(
        app_api_keys=["caller"],
        app_mode="live",
        linkedin_li_at="fixture",
        linkedin_jsessionid='"ajax:synthetic"',
        app_operation_registry_path=registry_path,
        app_upstream_retries=0,
        app_upstream_max_bytes=1024,
    )
    registry = OperationRegistry.load(registry_path, AppMode.LIVE)
    session = SessionProvider(settings)
    return settings, registry, session


@pytest.mark.asyncio
@respx.mock
async def test_direct_transport_uses_fixed_host_and_registered_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings, registry, session = live_components(tmp_path, monkeypatch)
    route = respx.post("https://www.linkedin.com/voyager/api/graphql").mock(
        return_value=Response(
            200, json={"included": []}, headers={"content-type": "application/json"}
        )
    )
    transport = LinkedInTransport(settings, registry, session)
    try:
        result = await transport.execute("profile_core", "safe-slug", "request-1")
    finally:
        await transport.aclose()
    assert result.status_code == 200
    assert route.called
    request = route.calls[0].request
    assert request.url.host == "www.linkedin.com"
    assert request.url.path == "/voyager/api/graphql"
    assert request.read()
    assert b"test-query-id" in request.content
    assert b"safe-slug" in request.content


@pytest.mark.asyncio
@respx.mock
async def test_challenge_fails_session_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings, registry, session = live_components(tmp_path, monkeypatch)
    respx.post("https://www.linkedin.com/voyager/api/graphql").mock(
        return_value=Response(403, text="checkpoint")
    )
    transport = LinkedInTransport(settings, registry, session)
    try:
        with pytest.raises(UpstreamChallenge):
            await transport.execute("profile_core", "safe-slug", "request-2")
    finally:
        await transport.aclose()
    assert session.available is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "headers", "content"),
    [
        (302, {"location": "https://evil.test"}, b""),
        (200, {"content-type": "text/html"}, b"<html>unexpected</html>"),
        (200, {"content-type": "application/json"}, b"not-json"),
        (410, {"content-type": "application/json"}, b"{}"),
    ],
)
@respx.mock
async def test_malformed_responses_are_controlled_drift(
    status: int,
    headers: dict[str, str],
    content: bytes,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings, registry, session = live_components(tmp_path, monkeypatch)
    respx.post("https://www.linkedin.com/voyager/api/graphql").mock(
        return_value=Response(status, headers=headers, content=content)
    )
    transport = LinkedInTransport(settings, registry, session)
    try:
        with pytest.raises(UpstreamOperationDrift):
            await transport.execute("profile_core", "safe-slug", "request-3")
    finally:
        await transport.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (401, UpstreamAuthExpired),
        (404, ProfileNotFound),
        (429, UpstreamRateLimited),
        (500, UpstreamTimeout),
    ],
)
@respx.mock
async def test_upstream_status_mapping(
    status: int,
    expected: type[Exception],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings, registry, session = live_components(tmp_path, monkeypatch)
    respx.post("https://www.linkedin.com/voyager/api/graphql").mock(
        return_value=Response(status, json={})
    )
    transport = LinkedInTransport(settings, registry, session)
    try:
        with pytest.raises(expected):
            await transport.execute("profile_core", "safe-slug", "request-status")
    finally:
        await transport.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [httpx.ReadTimeout("timeout"), httpx.ConnectError("reset")])
@respx.mock
async def test_network_failures_are_bounded_timeouts(
    failure: Exception,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings, registry, session = live_components(tmp_path, monkeypatch)
    respx.post("https://www.linkedin.com/voyager/api/graphql").mock(side_effect=failure)
    transport = LinkedInTransport(settings, registry, session)
    try:
        with pytest.raises(UpstreamTimeout):
            await transport.execute("profile_core", "safe-slug", "request-timeout")
    finally:
        await transport.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_checkpoint_html_and_oversized_payload_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings, registry, session = live_components(tmp_path, monkeypatch)
    route = respx.post("https://www.linkedin.com/voyager/api/graphql")
    route.mock(
        return_value=Response(
            200, content=b"<html>security challenge</html>", headers={"content-type": "text/html"}
        )
    )
    transport = LinkedInTransport(settings, registry, session)
    try:
        with pytest.raises(UpstreamChallenge):
            await transport.execute("profile_core", "safe-slug", "request-checkpoint")
    finally:
        await transport.aclose()
    assert session.available is False

    settings, registry, session = live_components(tmp_path, monkeypatch)
    route.mock(
        return_value=Response(
            200, content=b"{" + b" " * 2048 + b"}", headers={"content-type": "application/json"}
        )
    )
    transport = LinkedInTransport(settings, registry, session)
    try:
        with pytest.raises(UpstreamOperationDrift, match="size limit"):
            await transport.execute("profile_core", "safe-slug", "request-size")
    finally:
        await transport.aclose()
