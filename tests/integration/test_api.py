from __future__ import annotations

import httpx
import pytest
from conftest import FULL_PROFILE_FIXTURE

import tross_linkedin_api.api as api_module
from tross_linkedin_api.errors import (
    ProfileNotFound,
    UpstreamChallenge,
    UpstreamOperationDrift,
    UpstreamTimeout,
)
from tross_linkedin_api.runtime import Runtime as RealRuntime

REQUEST_LI_AT_SENTINEL = "request-only-" + "li-at-sentinel-value"
REQUEST_JSESSION_SENTINEL = "ajax:" + "request-only-jsession"


@pytest.mark.asyncio
async def test_healthz_is_public_and_readyz_reflects_session(client: httpx.AsyncClient) -> None:
    assert (await client.get("/healthz")).json() == {"status": "ok"}
    response = await client.get("/readyz")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["extraction_capability"]["state"] == "UNVERIFIED"
    assert "governor" in body["extraction_capability"]


@pytest.mark.asyncio
async def test_missing_and_invalid_api_keys_are_401(client: httpx.AsyncClient) -> None:
    params = {"url": "https://www.linkedin.com/in/test-integration-profile"}
    missing = await client.get("/v1/profiles", params=params)
    invalid = await client.get("/v1/profiles", params=params, headers={"X-API-Key": "wrong"})
    for response in (missing, invalid):
        assert response.status_code == 401
        assert response.headers["content-type"].startswith("application/problem+json")
        assert response.json()["code"] == "UNAUTHORIZED_CALLER"


@pytest.mark.asyncio
async def test_live_profile_contract_and_provenance(client: httpx.AsyncClient) -> None:
    response = await client.get(
        "/v1/profiles",
        params={"url": "https://linkedin.com/in/test-integration-profile?trk=example"},
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["schema_version"] == "1.2.0"
    assert body["canonical_url"] == "https://www.linkedin.com/in/test-integration-profile"
    retrieval = body["retrieval"]
    assert retrieval["mode"] == "live"
    assert retrieval["fixture"] is False
    assert retrieval["source"] == "linkedin"
    assert (
        retrieval["requested_url"] == "https://linkedin.com/in/test-integration-profile?trk=example"
    )
    profile = body["profile"]
    assert profile["first_name"]["value"] == "Integration"
    assert profile["last_name"]["value"] == "Check"
    assert profile["name"]["value"] == "Integration Check"
    assert body["meta"]["coverage"] == {
        "experience": "observed",
        "education": "observed",
        "skills": "observed",
        "certifications": "observed",
        "languages": "observed",
    }
    assert profile["headline"]["value"].startswith("Staff Engineer")
    assert len(profile["experience"]["value"]) == 2
    assert profile["experience"]["value"][0]["is_current"] is True
    assert profile["experience"]["value"][0]["company_url"] == (
        "https://www.linkedin.com/company/pipeline-validation-corp/"
    )
    assert [skill["name"] for skill in profile["skills"]["value"]] == [
        "HTTP protocol analysis",
        "Rest.li",
    ]
    assert profile["certifications"]["value"][0]["authority"] == "Open Verification Institute"
    assert profile["languages"]["value"][0]["proficiency"] == "NATIVE"
    assert profile["background_image"]["status"] == "not_provided"
    assert body["partial"] is False
    assert body["meta"]["transport_strategy"] == "profile_view"
    assert body["meta"]["viewer_context"] == "authenticated_backend_member"
    readiness = await client.get("/readyz")
    assert readiness.status_code == 200
    assert readiness.json()["extraction_capability"]["state"] == "CLOSED"


@pytest.mark.asyncio
async def test_error_responses_carry_request_id(client: httpx.AsyncClient) -> None:
    response = await client.get(
        "/v1/profiles",
        params={"url": "not-a-url"},
        headers={"X-API-Key": "test-api-key", "X-Request-ID": "corr-42"},
    )
    assert response.status_code == 400
    assert response.json()["request_id"] == "corr-42"
    # Regression: the enriched body must agree with its Content-Length header
    # (a mismatch crashes uvicorn with "content longer than Content-Length").
    assert int(response.headers["content-length"]) == len(response.content)


@pytest.mark.asyncio
async def test_upstream_failure_is_explicit_never_fixture(
    client: httpx.AsyncClient, stub_transport: object
) -> None:
    # Two failures per operation: the governor owns one bounded retry.
    stub_transport.set(
        "profile_view", [UpstreamTimeout("profile_view"), UpstreamTimeout("profile_view")]
    )
    stub_transport.set(
        "profile_page", [UpstreamTimeout("profile_page"), UpstreamTimeout("profile_page")]
    )
    response = await client.get(
        "/v1/profiles",
        params={"url": "https://www.linkedin.com/in/test-integration-profile/"},
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 504
    body = response.json()
    assert body["code"] == "UPSTREAM_TIMEOUT"
    assert "SYNTHETIC" not in response.text
    readiness = await client.get("/readyz")
    assert readiness.status_code == 503
    assert readiness.json()["extraction_capability"]["state"] == "UNUSABLE"


@pytest.mark.asyncio
async def test_profile_not_found_maps_to_404(
    client: httpx.AsyncClient, stub_transport: object
) -> None:
    stub_transport.set("profile_view", [ProfileNotFound()])
    response = await client.get(
        "/v1/profiles",
        params={"url": "https://www.linkedin.com/in/missing-person/"},
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 404
    assert response.json()["code"] == "PROFILE_NOT_FOUND"


@pytest.mark.asyncio
async def test_invalid_rsc_core_falls_back_to_valid_profile_page(
    client: httpx.AsyncClient, stub_transport: object
) -> None:
    stub_transport.set("profile_view", [{"flight": '0:{"children":[]}\n'}])
    stub_transport.set("profile_page", [FULL_PROFILE_FIXTURE])
    response = await client.get(
        "/v1/profiles",
        params={"url": "https://www.linkedin.com/in/test-integration-profile/"},
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 200
    meta = response.json()["meta"]
    assert meta["transport_strategy"] == "profile_page"
    assert meta["operations_attempted"][:2] == ["profile_view", "profile_page"]
    assert meta["operations_succeeded"][0] == "profile_page"


@pytest.mark.asyncio
async def test_valid_profile_view_core_does_not_call_profile_page(
    client: httpx.AsyncClient, stub_transport: object
) -> None:
    stub_transport.set("profile_view", [FULL_PROFILE_FIXTURE])
    response = await client.get(
        "/v1/profiles",
        params={"url": "https://www.linkedin.com/in/test-integration-profile/"},
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 200
    assert response.json()["meta"]["transport_strategy"] == "profile_view"
    assert [operation for operation, _ in stub_transport.seen] == ["profile_view"]


@pytest.mark.asyncio
async def test_profile_view_challenge_is_terminal_without_page_fallback(
    client: httpx.AsyncClient, stub_transport: object
) -> None:
    stub_transport.set("profile_view", [UpstreamChallenge()])
    response = await client.get(
        "/v1/profiles",
        params={"url": "https://www.linkedin.com/in/test-integration-profile/"},
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 503
    assert response.json()["code"] == "UPSTREAM_CHALLENGE"
    assert [operation for operation, _ in stub_transport.seen] == ["profile_view"]


@pytest.mark.asyncio
async def test_parser_drift_in_both_core_operations_is_typed_without_fake_profile(
    client: httpx.AsyncClient, stub_transport: object
) -> None:
    stub_transport.set("profile_view", [{"flight": '0:{"children":[]}\n'}])
    stub_transport.set("profile_page", [{"data": {}, "included": []}])
    response = await client.get(
        "/v1/profiles",
        params={"url": "https://www.linkedin.com/in/test-integration-profile/"},
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 502
    assert response.json()["code"] == "UPSTREAM_OPERATION_DRIFT"
    assert [operation for operation, _ in stub_transport.seen] == [
        "profile_view",
        "profile_page",
    ]
    assert "profile" not in response.json()
    assert "SYNTHETIC" not in response.text


@pytest.mark.asyncio
async def test_invalid_url_never_reaches_transport(
    client: httpx.AsyncClient, stub_transport: object
) -> None:
    response = await client.get(
        "/v1/profiles",
        params={"url": "https://linkedin.com.evil.test/in/admin"},
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_PROFILE_URL"
    assert stub_transport.call_count == 0


@pytest.mark.asyncio
async def test_openapi_documents_security(client: httpx.AsyncClient) -> None:
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    document = response.json()
    assert document["openapi"].startswith("3.1")
    operation = document["paths"]["/v1/profiles"]["get"]
    assert operation["security"]
    schemes = document["components"]["securitySchemes"]
    assert any(item.get("name") == "X-API-Key" for item in schemes.values())
    assert "/v1/batches" in document["paths"]
    assert "/v1/batches/{batch_id}/export" in document["paths"]
    assert document["paths"]["/v1/session-extractions"]["post"]["security"]


@pytest.mark.asyncio
async def test_extraction_desk_and_assets_are_public(client: httpx.AsyncClient) -> None:
    page = await client.get("/")
    stylesheet = await client.get("/assets/app.css")
    script = await client.get("/assets/app.js")
    assert page.status_code == 200
    assert "Tross Profile Refinery" in page.text
    assert "Request memory only" in page.text
    assert "localStorage" not in script.text
    assert stylesheet.status_code == 200
    assert script.status_code == 200


@pytest.mark.asyncio
async def test_request_scoped_session_extracts_without_echoing_secrets(
    client: httpx.AsyncClient,
    stub_transport: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_settings = []

    def transient_factory(settings: object) -> RealRuntime:
        captured_settings.append(settings)
        return RealRuntime(settings, transport=stub_transport)

    monkeypatch.setattr(api_module, "Runtime", transient_factory)
    sentinel_li_at = REQUEST_LI_AT_SENTINEL
    sentinel_jsession = REQUEST_JSESSION_SENTINEL
    sentinel_companions = "bcookie=request-only-bcookie; liap=true"
    response = await client.post(
        "/v1/session-extractions",
        headers={"X-API-Key": "test-api-key", "X-Request-ID": "desk-run"},
        json={
            "urls": ["https://www.linkedin.com/in/test-integration-profile/"],
            "session": {
                "li_at": sentinel_li_at,
                "jsessionid": sentinel_jsession,
                "companion_cookies": sentinel_companions,
                "user_agent": "Mozilla/5.0 request-scoped test browser",
                "accept_language": "en-US,en;q=0.9",
            },
        },
    )
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"].startswith("no-store")
    assert response.headers["x-credential-handling"] == "request-memory-only"
    body = response.json()
    assert body["credential_handling"] == "request_memory_only"
    assert body["results"][0]["status"] == "succeeded"
    assert body["results"][0]["profile"]["profile"]["name"]["value"] == "Integration Check"
    assert "request-only" not in response.text
    assert len(captured_settings) == 1
    assert captured_settings[0].linkedin_li_at.get_secret_value() == sentinel_li_at
    assert captured_settings[0].linkedin_jsessionid.get_secret_value() == sentinel_jsession


@pytest.mark.asyncio
async def test_request_scoped_extraction_stops_after_challenge(
    client: httpx.AsyncClient,
    stub_transport: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stub_transport.set("profile_view", [UpstreamChallenge()])
    monkeypatch.setattr(
        api_module,
        "Runtime",
        lambda settings: RealRuntime(settings, transport=stub_transport),
    )
    response = await client.post(
        "/v1/session-extractions",
        headers={"X-API-Key": "test-api-key"},
        json={
            "urls": [
                "https://www.linkedin.com/in/first-profile/",
                "https://www.linkedin.com/in/second-profile/",
            ],
            "session": {
                "li_at": REQUEST_LI_AT_SENTINEL,
                "jsessionid": REQUEST_JSESSION_SENTINEL,
                "user_agent": "Mozilla/5.0 request-scoped test browser",
            },
        },
    )
    assert response.status_code == 200
    results = response.json()["results"]
    assert results[0]["error"]["code"] == "UPSTREAM_CHALLENGE"
    assert results[1]["status"] == "skipped"
    assert results[1]["error"]["code"] == "SKIPPED_AFTER_CHALLENGE"
    assert stub_transport.call_count == 1


@pytest.mark.asyncio
async def test_request_scoped_extraction_requires_tross_api_key(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post(
        "/v1/session-extractions",
        json={
            "urls": ["https://www.linkedin.com/in/test-profile/"],
            "session": {
                "li_at": REQUEST_LI_AT_SENTINEL,
                "jsessionid": REQUEST_JSESSION_SENTINEL,
                "user_agent": "Mozilla/5.0 request-scoped test browser",
            },
        },
    )
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED_CALLER"


@pytest.mark.asyncio
async def test_request_validation_never_echoes_rejected_session_secret(
    client: httpx.AsyncClient,
) -> None:
    rejected_secret = "short-" + "secret-with-newline\nprivate-tail"
    response = await client.post(
        "/v1/session-extractions",
        headers={"X-API-Key": "test-api-key"},
        json={
            "urls": ["https://www.linkedin.com/in/test-profile/"],
            "session": {
                "li_at": rejected_secret,
                "jsessionid": REQUEST_JSESSION_SENTINEL,
                "user_agent": "Mozilla/5.0 request-scoped test browser",
            },
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] == "REQUEST_VALIDATION_ERROR"
    assert rejected_secret not in response.text
    assert "private-tail" not in response.text
    assert response.headers["cache-control"].startswith("no-store")


@pytest.mark.asyncio
async def test_core_only_payload_honestly_marks_sections_unavailable(
    client: httpx.AsyncClient, stub_transport: object
) -> None:
    """Section-operation failures remain unavailable, never empty-as-failure."""
    core_only = {
        "data": {"*elements": ["urn:li:fsd_profile:ACoAA-test"]},
        "included": [
            {
                "$type": "com.linkedin.voyager.dash.identity.profile.Profile",
                "entityUrn": "urn:li:fsd_profile:ACoAA-test",
                "publicIdentifier": "test-integration-profile",
                "firstName": {"localized": {"en_US": "Integration"}},
                "lastName": {"localized": {"en_US": "Check"}},
                "headline": {"localized": {"en_US": "Core-only projection"}},
            }
        ],
    }
    stub_transport.set("profile_view", [core_only])
    for section in ("experience", "education", "skills", "certifications", "languages"):
        stub_transport.set(
            f"profile_{section}",
            [UpstreamOperationDrift(f"profile_{section}", "scripted failure")],
        )
    response = await client.get(
        "/v1/profiles",
        params={"url": "https://www.linkedin.com/in/test-integration-profile/"},
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["partial"] is True
    assert body["status"] == "partial"
    assert body["profile"]["name"]["value"] == "Integration Check"
    experience = body["profile"]["experience"]
    assert experience["value"] is None
    assert experience["status"] == "upstream_failed"
    assert body["meta"]["coverage"]["experience"] == "unavailable"
    assert body["meta"]["coverage"]["languages"] == "unavailable"
    assert body["retrieval"]["mode"] == "live" and body["retrieval"]["fixture"] is False
