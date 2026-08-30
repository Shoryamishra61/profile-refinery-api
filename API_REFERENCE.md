# API Reference

## `POST /v1/session-extractions`

The public extraction-desk route accepts 1–10 LinkedIn profile URLs plus an
authorized request-scoped LinkedIn session. It does not require a Profile
Refinery account or product API key. Session fields are used only by an isolated
in-memory runtime, the response is marked `Cache-Control: no-store`, and raw
credentials never appear in response or validation-error bodies.

Profiles run sequentially. A challenge or open circuit stops the remaining
items and marks them explicitly as skipped.

Request body:

```json
{
  "urls": ["https://www.linkedin.com/in/example/"],
  "session": {
    "li_at": "<authorized session value>",
    "jsessionid": "<authorized session value>",
    "companion_cookies": "<optional cookie-name/value pairs>",
    "user_agent": "<the same browser session User-Agent>",
    "accept_language": "en-US,en;q=0.9"
  }
}
```

The normal response is an HTTP 200 envelope so every submitted URL has its own
outcome:

```json
{
  "request_id": "caller-supplied-or-generated-id",
  "credential_handling": "request_memory_only",
  "results": [
    {
      "input_url": "https://www.linkedin.com/in/example/",
      "status": "succeeded",
      "profile": {"schema_version": "1.2.0", "profile": {}},
      "error": null
    }
  ]
}
```

`status` is `succeeded`, `partial`, `failed`, or `skipped`. A syntactically
valid request containing an invalid member URL still returns the HTTP 200
envelope, but that item is `failed` with `error.code=INVALID_PROFILE_URL`. URL
validation occurs before transport execution, so LinkedIn is not called for
that item. A malformed request body (missing session fields, invalid field
types, or more than 10 URLs) returns HTTP 422.

Backend callers should keep all session values in environment variables or a
secret manager, send a unique `X-Request-ID`, use a bounded timeout, and inspect
both the HTTP status and each item status. Never embed session material in
frontend JavaScript, URLs, logs, or source control. Live examples are also
available in `/docs` and the machine-readable contract is `/openapi.json`.

## `GET /v1/profiles`

This legacy operator route uses a backend-configured LinkedIn session. Query
parameter `url` is required and must be an HTTPS `linkedin.com/in/{slug}` or
`www.linkedin.com/in/{slug}` URL. Tracking query parameters are discarded. A
generic operator `X-API-Key` is required.

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
