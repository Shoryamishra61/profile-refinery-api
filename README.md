# Tross LinkedIn Profile API

Tross accepts a LinkedIn member URL and attempts to return a normalized profile
using authenticated direct HTTP requests. It uses no browser automation and has
no fixture or replay fallback in `APP_MODE=live`.

- API: <https://tross-linkedin-profile-api.vercel.app>
- Repository: <https://github.com/Shoryamishra61/tross-linkedin-profile-api>

## Current production status

Production is **not live-verified**. The authenticated RSC `profile_view` request
reaches LinkedIn, but the currently observed Vercel response is a 135-byte React
Flight stream with one model record and no `prioritizedProfileId`, target identity,
or profile SetState values. The API therefore fails closed with
`UPSTREAM_OPERATION_DRIFT`; it does not emit fixture, replay, or inferred data.

Evidence labels have these exact meanings:

- `LIVE`: observed through a current direct authenticated LinkedIn request.
- `REAL_HAR_REPLAY`: deterministically parsed from a real captured response.
- `SYNTHETIC_UNIT`: produced only by synthetic test input.

Only `LIVE` evidence can establish production extraction success. Passing tests
and `REAL_HAR_REPLAY` prove contracts and parsing, not current upstream behavior.

## Active extraction protocol

The deployed primary protocol is LinkedIn SDUI over React Flight:

1. `POST /flagship-web/rsc-action/actions/component` with the
   `profileCardsActivity` component and vanity-name payload.
2. Resolve the target-owned `prioritizedProfileId` and semantic name, headline,
   and image SetState values from the Flight model records.
3. Request the enabled Experience, Education, Skills, Certifications, and
   Languages profile-card components using that target identity.
4. Parse semantic Flight entities and normalize them against the public schema.

The request uses JSON, `csrf-token`, `x-li-anchor-page-key`, and
`x-li-rsc-stream`. Dynamic trace, page-instance, and parent-span telemetry is not
required by the known-good captured contract replay and is not synthesized.
Historical Rest.li and authenticated-page operations remain evidence references;
they are not described as the active successful production path.

```text
GET /v1/profiles
        |
        v
canonical URL + API-key validation
        |
        v
profileCardsActivity RSC request
        |
        v
target identity resolver
        |
        v
section RSC requests -> semantic Flight parser -> schema 1.2.0
```

## API

```bash
curl -H "X-API-Key: $KEY" \
  "https://tross-linkedin-profile-api.vercel.app/v1/profiles?url=https://www.linkedin.com/in/example/"
```

The following is an illustrative **schema shape**, not a live-success example:

```json
{
  "schema_version": "1.2.0",
  "canonical_url": "https://www.linkedin.com/in/example",
  "retrieval": {"mode": "live", "fixture": false, "source": "linkedin"},
  "profile": {
    "name": {"value": null, "status": "not_provided"},
    "experience": {"value": [], "status": "not_provided"},
    "education": {"value": [], "status": "not_provided"},
    "skills": {"value": [], "status": "not_provided"},
    "certifications": {"value": [], "status": "not_provided"},
    "languages": {"value": [], "status": "not_provided"}
  }
}
```

Actual successful responses are validated against
`schemas/profile-response.schema.json`. Empty arrays do not prove section
extraction, and synthetic values are never reported as live evidence.

### Error taxonomy

| HTTP | Code | Meaning |
|---:|---|---|
| 400 | `INVALID_PROFILE_URL` | Invalid LinkedIn member URL |
| 401 | `UNAUTHORIZED_CALLER` | Missing or invalid API key |
| 404 | `PROFILE_NOT_FOUND` | Profile absent for the authenticated viewer |
| 429 | `CALLER_RATE_LIMITED` | Public API caller limit |
| 502 | `UPSTREAM_OPERATION_DRIFT` | HTTP succeeded but the semantic contract did not |
| 503 | `UPSTREAM_AUTH_REQUIRED` / `UPSTREAM_AUTH_EXPIRED` | Session missing or expired |
| 503 | `UPSTREAM_FORBIDDEN` | LinkedIn returned generic HTTP 403 |
| 503 | `UPSTREAM_UNAVAILABLE` | LinkedIn returned HTTP 5xx |
| 503 | `UPSTREAM_CHALLENGE` / `UPSTREAM_RATE_LIMITED` | Explicit challenge or upstream throttling |
| 504 | `UPSTREAM_TIMEOUT` | Network operation exceeded its time budget |

`/healthz` proves that the API process responds. `/readyz` is stricter: it returns
503 with `UNAVAILABLE`, `UNVERIFIED`, or `UNUSABLE` until that process observes a
successful normalized live profile. A configured cookie alone is not readiness.

## Authentication

Set `APP_API_KEYS` for API callers. Live extraction additionally requires session
material for an account the operator owns:

```text
LINKEDIN_LI_AT=<li_at value>
LINKEDIN_JSESSIONID=<JSESSIONID value>
LINKEDIN_COOKIE=<optional additional cookie header>
```

Cookie values, CSRF values, and API keys must never be logged, committed, or
included in comparison reports. Live mode fails closed when session material or
semantic identity is unavailable.

## Local verification

```bash
uv sync --extra dev
uv run pytest
uv run ruff check src tests scripts
uv run mypy
uv run python scripts/security_audit.py
```

Current acceptance-suite count: `126` tests. This count is updated
from the full `pytest` run; it is not evidence of live LinkedIn extraction.

## Safety boundary

The project does not solve CAPTCHAs, rotate accounts or proxies, generate
challenge tokens, spoof browser fingerprints, automate login, or circumvent
access controls. When LinkedIn refuses or changes the response, the API returns a
typed failure and preserves the distinction among `LIVE`, `REAL_HAR_REPLAY`, and
`SYNTHETIC_UNIT` evidence.
