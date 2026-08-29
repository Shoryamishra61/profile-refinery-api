from __future__ import annotations

import httpx
import pytest

from tross_linkedin_api.errors import ProfileNotFound, UpstreamOperationDrift, UpstreamTimeout


@pytest.mark.asyncio
async def test_healthz_is_public_and_readyz_reflects_session(client: httpx.AsyncClient) -> None:
    assert (await client.get("/healthz")).json() == {"status": "ok"}
    response = await client.get("/readyz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["extraction_capability"]["state"] == "CLOSED"
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
async def test_fallback_strategy_used_when_primary_drifts(
    client: httpx.AsyncClient, stub_transport: object
) -> None:
    stub_transport.set("profile_view", [])
    response = await client.get(
        "/v1/profiles",
        params={"url": "https://www.linkedin.com/in/test-integration-profile/"},
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 200
    assert response.json()["meta"]["transport_strategy"] == "profile_page"


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
