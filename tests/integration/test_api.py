from __future__ import annotations

import httpx
import pytest


@pytest.mark.asyncio
async def test_health_and_readiness_are_public(client: httpx.AsyncClient) -> None:
    assert (await client.get("/healthz")).json() == {"status": "ok"}
    response = await client.get("/readyz")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


@pytest.mark.asyncio
async def test_fixture_demo_never_embeds_the_caller_api_key(client: httpx.AsyncClient) -> None:
    response = await client.get("/demo")
    assert response.status_code == 200
    assert "Verified Fixture Demo" in response.text
    assert "test-api-key" not in response.text
    assert "Bearer token" not in response.text


@pytest.mark.asyncio
async def test_missing_and_invalid_api_keys_are_401(client: httpx.AsyncClient) -> None:
    params = {"url": "https://www.linkedin.com/in/synthetic-profile"}
    missing = await client.get("/v1/profiles", params=params)
    invalid = await client.get("/v1/profiles", params=params, headers={"X-API-Key": "wrong"})
    for response in (missing, invalid):
        assert response.status_code == 401
        assert response.headers["content-type"].startswith("application/problem+json")
        assert response.json()["code"] == "UNAUTHORIZED_CALLER"
        assert "API" not in response.json()["detail"] or "valid" in response.json()["detail"]


@pytest.mark.asyncio
async def test_fixture_profile_contract_and_instrumentation(client: httpx.AsyncClient) -> None:
    response = await client.get(
        "/v1/profiles",
        params={"url": "https://linkedin.com/in/synthetic-profile?trk=example"},
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["canonical_url"] == "https://www.linkedin.com/in/synthetic-profile"
    assert body["retrieval"] == {
        "mode": "fixture",
        "source": "synthetic_fixture",
        "fixture": True,
        "requested_url": "https://linkedin.com/in/synthetic-profile?trk=example",
        "canonical_url": "https://www.linkedin.com/in/synthetic-profile",
        "observed_at": body["observed_at"],
        "partial": False,
    }
    assert body["profile"]["name"]["value"] == "Avery Raman"
    assert len(body["profile"]["experience"]["value"]) == 2
    assert body["profile"]["background_image"]["status"] == "not_provided"
    assert body["partial"] is False
    assert body["meta"]["upstream_calls"] == 6
    assert len(body["meta"]["operations_succeeded"]) == 6
    assert body["meta"]["viewer_context"] == "synthetic_fixture"


@pytest.mark.asyncio
async def test_invalid_url_never_reaches_transport(client: httpx.AsyncClient) -> None:
    response = await client.get(
        "/v1/profiles",
        params={"url": "https://linkedin.com.evil.test/in/admin"},
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_PROFILE_URL"


@pytest.mark.asyncio
async def test_openapi_is_31_and_documents_required_header(client: httpx.AsyncClient) -> None:
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    document = response.json()
    assert document["openapi"].startswith("3.1")
    operation = document["paths"]["/v1/profiles"]["get"]
    assert operation["security"]
    schemes = document["components"]["securitySchemes"]
    assert any(item.get("name") == "X-API-Key" for item in schemes.values())
