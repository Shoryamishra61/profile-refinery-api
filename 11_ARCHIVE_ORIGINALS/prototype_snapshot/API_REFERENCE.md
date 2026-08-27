# API Reference Manual (v1)

This manual provides the technical specifications of our public HTTPS profile extraction gateway.

## Request Endpoint
`GET /v1/profiles`

### Request Headers
* `X-API-Key` (Required): String token representing the caller credentials.
* `Accept` (Optional): `application/json`

### Request Parameters
| Name | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `url` | String | Yes | Legitimate, public LinkedIn profile URL (e.g., `https://www.linkedin.com/in/jane-doe`). |
| `mock` | Boolean | No | Defaults to `true`. Enables offline mock mode to return deterministic, validated fixture schemas for testing. |
| `viewer_state` | String | No | Defaults to `V1`. Selects connection degree mapping: `V1` (1st degree), `V2` (2nd degree), `V3` (3rd degree/private out-of-network). |

---

## Response Schema
All successful responses return `HTTP 200 OK` with a JSON payload complying with `PROFILE_SCHEMA.json`.

### Successful Response Format (Partial Example)
```json
{
  "identity": {
    "value": {
      "vanity_slug": "jane-doe-engineering-leader",
      "member_urn": "urn:li:fsd_profile:ACoAAAtp-4U",
      "profile_id": "ACoAAAtp-4U"
    },
    "status": "present",
    "provenance": {
      "source_operation": "POST /voyager/api/graphql",
      "observation_time": "2026-08-27T06:29:07Z",
      "raw_entity_reference": "urn:li:fsd_profile:ACoAAAtp-4U",
      "normalization_performed": "Slug-to-URN key binding",
      "schema_version": "1.0.0"
    }
  },
  "headline": {
    "value": "Engineering Director & Protocol Researcher",
    "status": "present",
    "provenance": {
      "source_operation": "POST /voyager/api/graphql",
      "observation_time": "2026-08-27T06:29:07Z",
      "raw_entity_reference": "urn:li:fsd_profile:ACoAAAtp-4U",
      "normalization_performed": "Localized text extraction",
      "schema_version": "1.0.0"
    }
  }
}
```

---

## Error Handling Specifications
The API uses strict **RFC 9457 Problem Details** for HTTP APIs as its default error response format.

### Error Response Format (Example)
```json
{
  "type": "https://api.tross-profile-challenge.com/errors/invalid-profile-slug",
  "title": "Invalid Profile Slug",
  "status": 400,
  "detail": "The provided profile URL could not be canonicalized. Expected pattern: /in/vanity-name",
  "instance": "/v1/profiles"
}
```

### Documented Error Types
* **`invalid-profile-slug` (HTTP 400):** Provided URL is malformed or violates security boundaries (SSRF hosts).
* **`unauthorized` (HTTP 401):** Revoked or missing `X-API-Key` headers.
* **`rate-limit-exceeded` (HTTP 429):** Client has exceeded the safety threshold of 10 requests per minute.
* **`profile-not-found` (HTTP 404):** Target profile does not exist or has been deleted.
* **`upstream-schema-drift` (HTTP 502):** Upstream response has drifted, failing Draft-07 validation.
