# API Reference

## `GET /v1/profiles`

Query parameter `url` is required and must be an HTTPS `linkedin.com/in/{slug}` or `www.linkedin.com/in/{slug}` URL. Tracking query parameters are discarded. Header `X-API-Key` is required.

Success is HTTP 200 with schema version, input/canonical URLs, observation time, `partial`, required profile fields, per-field availability/provenance, and request metadata. Every profile key exists even when its value is unavailable.

Availability values are `present`, `not_provided`, `not_visible_to_viewer`, `not_available_from_endpoint`, `upstream_failed`, `parser_failed`, `stale_or_expired`, and `unknown`. The implementation does not emit `not_visible_to_viewer` without affirmative evidence.

`meta.upstream_calls` and `meta.upstream_latency_ms` are measured by the transport path. In fixture mode these are fixture-operation count and local file/parse timing, not LinkedIn calls or live latency.

## Partial success

If core succeeds but an optional section fails, the API returns 200, `partial=true`, preserves successful fields, sets the affected field value to `null`, and records a typed warning. A disabled operation is `not_available_from_endpoint`, not an upstream failure.

## Problem Details

Errors use `application/problem+json` with RFC 9457-compatible `type`, `title`, `status`, `detail`, `instance`, and stable `code` fields.

| HTTP | Code | Meaning |
|---:|---|---|
| 400 | `INVALID_PROFILE_URL` | URL failed the strict profile boundary |
| 401 | `UNAUTHORIZED_CALLER` | API key missing or invalid |
| 404 | `PROFILE_NOT_FOUND` | Upstream confidently returned not found |
| 429 | `CALLER_RATE_LIMITED` | Local sliding-window limit exceeded |
| 502 | `UPSTREAM_OPERATION_DRIFT` | Registered operation/shape/content contract changed |
| 503 | `UPSTREAM_AUTH_EXPIRED` | Owned session requires renewal |
| 503 | `UPSTREAM_CHALLENGE` | Checkpoint detected; session stopped |
| 503 | `UPSTREAM_RATE_LIMITED` | LinkedIn rate limited the operation |
| 504 | `UPSTREAM_TIMEOUT` | Bounded transport budget exhausted |
| 500 | `INTERNAL_CONTRACT_FAILURE` | Service refused invalid normalized output |

## Operations endpoints

- `GET /healthz`: process liveness.
- `GET /readyz`: schema, registry, core operation, and session readiness.
- `GET /openapi.json`: OpenAPI 3.1 contract.
- `GET /docs`: Swagger UI for the API contract; this is documentation only, not an acquisition browser.
