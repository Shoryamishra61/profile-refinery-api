from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest
import respx
from httpx import Response

from tross_linkedin_api.config import Settings
from tross_linkedin_api.errors import (
    ProfileNotFound,
    UpstreamAuthExpired,
    UpstreamChallenge,
    UpstreamForbidden,
    UpstreamOperationDrift,
    UpstreamRateLimited,
    UpstreamTimeout,
    UpstreamUnavailable,
)
from tross_linkedin_api.operation_registry import OperationRegistry, RegistryDocument
from tross_linkedin_api.session import SessionProvider
from tross_linkedin_api.transport import LinkedInTransport

DASH_PATH = "/voyager/api/identity/dash/profiles"
RSC_PATH = "/flagship-web/rsc-action/actions/component"


def live_components(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Settings, OperationRegistry, SessionProvider, LinkedInTransport]:
    monkeypatch.setenv("APP_API_KEYS", "caller")
    settings = Settings(
        app_api_keys=["caller"],
        app_mode="live",
        linkedin_li_at="test-li-at-value",
        linkedin_jsessionid='"ajax:test-session"',
        app_upstream_retries=0,
    )
    registry = OperationRegistry(
        RegistryDocument.model_validate(
            {
                "version": 2,
                "operations": [
                    {
                        "semantic_name": "profile_view",
                        "enabled": True,
                        "evidence_status": "historical",
                        "kind": "restli",
                        "method": "GET",
                        "path": DASH_PATH,
                        "transport_family": "restli",
                        "parser": "full_profile_v1",
                        "observed_at": "2026-08-28T00:00:00Z",
                        "evidence_reference": "test",
                    },
                    {
                        "semantic_name": "profile_experience",
                        "enabled": True,
                        "evidence_status": "live_verified",
                        "kind": "rsc",
                        "method": "POST",
                        "path": RSC_PATH,
                        "transport_family": "react_flight",
                        "parser": "linkedin_sdui_flight_v1",
                        "component_id": (
                            "com.linkedin.sdui.generated.profile.dsl.impl."
                            "profileCardsExperienceOnly"
                        ),
                        "observed_at": "2026-08-29T00:00:00Z",
                        "evidence_reference": "test",
                    },
                    {
                        "semantic_name": "profile_page",
                        "enabled": True,
                        "evidence_status": "historical",
                        "kind": "html",
                        "method": "GET",
                        "path": "/in/{slug}/",
                        "transport_family": "web",
                        "parser": "full_profile_v1",
                        "observed_at": "2026-08-28T00:00:00Z",
                        "evidence_reference": "test",
                    },
                ],
            }
        )
    )
    session = SessionProvider(settings)
    transport = LinkedInTransport(settings, registry, session)
    return settings, registry, session, transport


def registry_with_decoration(tmp_path: Path, decorations: list[str]) -> OperationRegistry:
    registry_path = tmp_path / "registry.yaml"
    decoration_lines = "".join(f"      - {item}\n" for item in decorations)
    registry_path.write_text(
        "version: 2\n"
        "operations:\n"
        "  - semantic_name: profile_view\n"
        "    enabled: true\n"
        "    evidence_status: historical\n"
        "    kind: restli\n"
        "    method: GET\n"
        "    path: /voyager/api/identity/dash/profiles\n"
        "    transport_family: restli\n"
        "    parser: full_profile_v1\n"
        "    decoration_ids:\n"
        f"{decoration_lines}"
        "    observed_at: 2026-08-28T00:00:00Z\n"
        "    evidence_reference: test\n",
        encoding="utf-8",
    )
    return OperationRegistry.load(registry_path)


def valid_payload() -> dict[str, object]:
    return {
        "data": {"profileView": {"entityUrn": "urn:li:fsd_profile:1"}},
        "included": [
            {
                "$type": "com.linkedin.voyager.dash.identity.profile.Profile",
                "entityUrn": "urn:li:fsd_profile:1",
                "firstName": {"localized": {"en_US": "Real"}},
                "lastName": {"localized": {"en_US": "Person"}},
            }
        ],
    }


@respx.mock
async def test_restli_request_carries_csrf_and_session_cookies(monkeypatch) -> None:
    _, _, _, transport = live_components(monkeypatch)
    route = respx.get(f"https://www.linkedin.com{DASH_PATH}").mock(
        return_value=Response(200, json=valid_payload())
    )
    result = await transport.execute("profile_view", "some-person", "req-1")
    await transport.aclose()

    assert route.called
    request = route.calls.last.request
    assert request.headers["csrf-token"] == "ajax:test-session"
    cookie_header = request.headers.get("cookie", "")
    assert "li_at=test-li-at-value" in cookie_header
    assert "ajax%3Atest-session" in cookie_header or "ajax:test-session" in cookie_header
    assert '""ajax' not in cookie_header
    assert request.headers["x-restli-protocol-version"] == "2.0.0"
    assert "memberIdentity=some-person" in str(request.url)
    assert "decorationId" not in str(request.url)
    assert result.payload == valid_payload()


@respx.mock
async def test_rsc_request_uses_minimal_semantic_contract_without_telemetry(monkeypatch) -> None:
    _, _, _, transport = live_components(monkeypatch)
    route = respx.post(f"https://www.linkedin.com{RSC_PATH}").mock(
        return_value=Response(
            200,
            content=b'0:{"children":["captured"]}\n',
            headers={"content-type": "application/octet-stream"},
        )
    )
    result = await transport.execute(
        "profile_experience", "some-person", "req-rsc", "ACoSANITIZED"
    )
    await transport.aclose()

    request = route.calls.last.request
    query = str(request.url)
    assert "componentId=" in query and "sduiid=" in query
    assert "parentSpanId" not in query
    assert request.headers["csrf-token"] == "ajax:test-session"
    assert request.headers["x-li-anchor-page-key"] == "d_flagship3_profile_view_base"
    assert request.headers["x-li-rsc-stream"] == "true"
    assert request.headers["accept-language"] == "en-US,en;q=0.9,hi;q=0.8,en-IN;q=0.7"
    assert "x-li-page-instance" not in request.headers
    assert "x-li-traceparent" not in request.headers
    body = json.loads(request.content)
    payload = body["clientArguments"]["payload"]
    assert payload["vanityName"] == "some-person"
    assert payload["replaceableSectionArgs"]["vieweeProfileId"] == "ACoSANITIZED"
    assert result.payload["flight"].startswith("0:")


@respx.mock
async def test_profile_view_matches_known_good_stable_rsc_contract(monkeypatch) -> None:
    settings, _, session, _ = live_components(monkeypatch)
    registry = OperationRegistry(
        RegistryDocument.model_validate(
            {
                "version": 2,
                "operations": [
                    {
                        "semantic_name": "profile_view",
                        "enabled": True,
                        "evidence_status": "live_verified",
                        "kind": "rsc",
                        "method": "POST",
                        "path": RSC_PATH,
                        "transport_family": "react_flight",
                        "parser": "linkedin_sdui_flight_v1",
                        "component_id": (
                            "com.linkedin.sdui.generated.profile.dsl.impl."
                            "profileCardsActivity"
                        ),
                        "request_variant": "profile_activity",
                        "observed_at": "2026-08-29T00:00:00Z",
                        "evidence_reference": "known-good-har",
                    }
                ],
            }
        )
    )
    transport = LinkedInTransport(settings, registry, session)
    route = respx.post(f"https://www.linkedin.com{RSC_PATH}").mock(
        return_value=Response(
            200,
            content=b'0:{"children":["captured"]}\n',
            headers={"content-type": "application/octet-stream"},
        )
    )

    await transport.execute("profile_view", "some-person", "req-profile-view")
    await transport.aclose()

    request = route.calls.last.request
    assert request.method == "POST"
    assert request.url.host == "www.linkedin.com"
    assert request.url.path == RSC_PATH
    assert set(parse_qs(request.url.query.decode())) == {"componentId", "sduiid"}
    component = "com.linkedin.sdui.generated.profile.dsl.impl.profileCardsActivity"
    assert request.url.params["componentId"] == component
    assert request.url.params["sduiid"] == component
    assert request.headers["content-type"] == "application/json"
    assert request.headers["accept"] == "*/*"
    assert request.headers["accept-language"] == "en-US,en;q=0.9,hi;q=0.8,en-IN;q=0.7"
    assert request.headers["csrf-token"] == "ajax:test-session"
    assert request.headers["x-li-anchor-page-key"] == "d_flagship3_profile_view_base"
    assert request.headers["x-li-rsc-stream"] == "true"
    assert not {"x-li-page-instance", "x-li-traceparent"} & set(request.headers)
    assert json.loads(request.content) == {
        "clientArguments": {
            "payload": {"isSelfView": False, "vanityName": "some-person"},
            "states": [],
            "requestMetadata": {"$type": "proto.sdui.common.RequestMetadata"},
            "screenId": "com.linkedin.sdui.flagshipnav.home.Home",
            "knownTemplateIds": [],
        }
    }


@respx.mock
async def test_retired_decoration_html_404_falls_through_to_next(
    monkeypatch, tmp_path: Path
) -> None:
    _, _, _, transport = live_components(monkeypatch)
    transport._registry = registry_with_decoration(
        tmp_path,
        [
            "com.linkedin.voyager.dash.deco.identity.profile.WebTopCardCoreProfile-18",
            "com.linkedin.voyager.dash.deco.identity.profile.WebTopCardCoreProfile-19",
        ],
    )
    route = respx.get(f"https://www.linkedin.com{DASH_PATH}").mock(
        side_effect=[
            Response(404, text="<html>error page</html>"),
            Response(200, json=valid_payload()),
        ]
    )
    result = await transport.execute("profile_view", "some-person", "req-1")
    await transport.aclose()

    assert route.call_count == 2
    assert result.payload == valid_payload()


@respx.mock
async def test_json_404_maps_to_profile_not_found(monkeypatch) -> None:
    _, _, _, transport = live_components(monkeypatch)
    respx.get(f"https://www.linkedin.com{DASH_PATH}").mock(
        return_value=Response(404, json={"data": {"status": 404}, "included": []})
    )
    with pytest.raises(ProfileNotFound):
        await transport.execute("profile_view", "ghost", "req-1")
    await transport.aclose()


@respx.mock
async def test_all_decorations_refused_is_operation_drift(monkeypatch) -> None:
    _, _, _, transport = live_components(monkeypatch)
    respx.get(f"https://www.linkedin.com{DASH_PATH}").mock(
        return_value=Response(404, text="<html>error</html>")
    )
    with pytest.raises(UpstreamOperationDrift):
        await transport.execute("profile_view", "some-person", "req-1")
    await transport.aclose()


@respx.mock
async def test_401_fails_session_closed(monkeypatch) -> None:
    _, _, session, transport = live_components(monkeypatch)
    respx.get(f"https://www.linkedin.com{DASH_PATH}").mock(return_value=Response(401))
    with pytest.raises(UpstreamAuthExpired):
        await transport.execute("profile_view", "some-person", "req-1")
    assert session.available is False
    await transport.aclose()


@respx.mock
async def test_403_becomes_forbidden_without_invalidating_session(monkeypatch) -> None:
    _, _, session, transport = live_components(monkeypatch)
    respx.get(f"https://www.linkedin.com{DASH_PATH}").mock(return_value=Response(403))
    with pytest.raises(UpstreamForbidden):
        await transport.execute("profile_view", "some-person", "req-1")
    assert session.available is True
    await transport.aclose()


@respx.mock
async def test_5xx_becomes_upstream_unavailable(monkeypatch) -> None:
    _, _, _, transport = live_components(monkeypatch)
    respx.get(f"https://www.linkedin.com{DASH_PATH}").mock(return_value=Response(503))
    with pytest.raises(UpstreamUnavailable):
        await transport.execute("profile_view", "some-person", "req-1")
    await transport.aclose()


@respx.mock
async def test_429_becomes_rate_limited(monkeypatch) -> None:
    _, _, _, transport = live_components(monkeypatch)
    respx.get(f"https://www.linkedin.com{DASH_PATH}").mock(return_value=Response(429))
    with pytest.raises(UpstreamRateLimited):
        await transport.execute("profile_view", "some-person", "req-1")
    await transport.aclose()


@respx.mock
async def test_timeout_maps_to_upstream_timeout(monkeypatch) -> None:
    _, _, _, transport = live_components(monkeypatch)
    respx.get(f"https://www.linkedin.com{DASH_PATH}").mock(side_effect=httpx.ReadTimeout("x"))
    with pytest.raises(UpstreamTimeout):
        await transport.execute("profile_view", "some-person", "req-1")
    await transport.aclose()


@respx.mock
async def test_page_fallback_extracts_embedded_json(monkeypatch) -> None:
    _, _, _, transport = live_components(monkeypatch)
    embedded = (
        '<code style="display:none"><!--'
        + '{"included":[{"$type":"com.linkedin.voyager.dash.identity.profile.Profile",'
        + '"entityUrn":"urn:li:fsd_profile:9","firstName":{"localized":{"en_US":"Page"}}}]}'
        + "--></code>"
    )
    respx.get("https://www.linkedin.com/in/some-person/").mock(
        return_value=Response(
            200, text=f"<html>{embedded}</html>", headers={"content-type": "text/html"}
        )
    )
    result = await transport.execute("profile_page", "some-person", "req-1")
    await transport.aclose()
    assert result.payload["included"][0]["$type"].endswith(".Profile")


@respx.mock
async def test_page_bot_wall_999_is_challenge_session_survives(monkeypatch) -> None:
    _, _, session, transport = live_components(monkeypatch)
    respx.get("https://www.linkedin.com/in/some-person/").mock(return_value=Response(999))
    with pytest.raises(UpstreamChallenge):
        await transport.execute("profile_page", "some-person", "req-1")
    assert session.available is True
    await transport.aclose()


@respx.mock
async def test_authwall_redirect_is_session_expired(monkeypatch) -> None:
    _, _, session, transport = live_components(monkeypatch)
    respx.get(f"https://www.linkedin.com{DASH_PATH}").mock(
        return_value=Response(302, headers={"location": "https://www.linkedin.com/authwall"})
    )
    with pytest.raises(UpstreamAuthExpired):
        await transport.execute("profile_view", "some-person", "req-1")
    assert session.available is False
    await transport.aclose()


@respx.mock
async def test_same_url_redirect_is_challenge_session_survives(monkeypatch) -> None:
    _, _, session, transport = live_components(monkeypatch)
    route = respx.get(f"https://www.linkedin.com{DASH_PATH}").mock(
        return_value=Response(
            302, headers={"location": f"https://www.linkedin.com{DASH_PATH}?q=memberIdentity"}
        )
    )
    with pytest.raises(UpstreamChallenge):
        await transport.execute("profile_view", "some-person", "req-1")
    assert route.call_count == 1  # single attempt; retry policy lives in the governor
    # Transient challenges are breaker events: the session stays configured
    # so the cooldown probe can restore extraction automatically.
    assert session.available is True
    await transport.aclose()
