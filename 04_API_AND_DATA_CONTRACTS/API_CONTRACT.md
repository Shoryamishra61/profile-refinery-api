# Public API Contract

## Endpoint

`GET /v1/profiles?url={linkedin_profile_url}`

Header: `X-API-Key` required in deployed service.

## Success envelope

```json
{
  "schema_version": "1.0.0",
  "input_url": "https://www.linkedin.com/in/example",
  "canonical_url": "https://www.linkedin.com/in/example",
  "observed_at": "2026-08-27T13:00:00Z",
  "partial": false,
  "profile": {
    "identity": {"value": {"vanity_slug": "example", "member_urn": "urn:li:..."}, "status": "present", "provenance": {}},
    "name": {"value": "Example Person", "status": "present", "provenance": {}},
    "headline": {"value": "...", "status": "present", "provenance": {}},
    "location": {"value": "...", "status": "present", "provenance": {}},
    "about": {"value": "...", "status": "present", "provenance": {}},
    "experience": {"value": [], "status": "present", "provenance": {}},
    "education": {"value": [], "status": "present", "provenance": {}},
    "skills": {"value": [], "status": "present", "provenance": {}},
    "certifications": {"value": [], "status": "present", "provenance": {}},
    "languages": {"value": [], "status": "present", "provenance": {}},
    "profile_image": {"value": null, "status": "not_provided", "provenance": {}}
  },
  "meta": {"viewer_context": "authenticated_backend_member", "operations_attempted": [], "operations_succeeded": [], "warnings": []}
}
```

## Status semantics

`present`, `not_provided`, `not_visible_to_viewer`, `not_available_from_endpoint`, `upstream_failed`, `parser_failed`, `stale_or_expired`, `unknown`.

`not_visible_to_viewer` requires evidence; missing key alone is insufficient.

## Partial

Return 200 + `partial=true` when core succeeds but optional sections fail.

## Error Problem Details

Codes: `INVALID_PROFILE_URL`, `UNAUTHORIZED_CALLER`, `PROFILE_NOT_FOUND`, `CALLER_RATE_LIMITED`, `UPSTREAM_AUTH_EXPIRED`, `UPSTREAM_CHALLENGE`, `UPSTREAM_RATE_LIMITED`, `UPSTREAM_OPERATION_DRIFT`, `UPSTREAM_TIMEOUT`, `INTERNAL_CONTRACT_FAILURE`.
