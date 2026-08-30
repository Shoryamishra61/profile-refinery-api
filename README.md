# Profile Refinery

Profile Refinery accepts a LinkedIn member URL and attempts to return a normalized profile
using authenticated direct HTTP requests. It uses no browser automation and has
no fixture or replay fallback in `APP_MODE=live`.

- API: <https://profile-refinery-api.vercel.app>
- Repository: <https://github.com/Shoryamishra61/profile-refinery-api>

## Problem and design boundary

The assignment requires semantic profile data, not rendered page markup. Profile Refinery
therefore sends bounded requests to registered LinkedIn operations, decodes
Rest.li JSON or React Flight records, establishes target ownership, and validates
the normalized result before returning it. Direct HTTP keeps the acquisition
contract deterministic and auditable. It does not make upstream access
guaranteed: challenges, expired sessions, unknown shapes, and unavailable
operations are typed failures and never trigger browser, fixture, or replay
fallbacks.

## Current production status

Production is now **live-verified for one deployed profile request**. Request
`deployed-live-20260830` returned HTTP 200 from the public HTTPS API with
`retrieval.mode=live`, `fixture=false`, real identity, 5 Experience, 1 Education,
3 Skills, 5 Certifications, 0 Languages, and a profile image. The primary
`profile_view` and all required section operations succeeded; no page fallback,
fixture, replay, or cache was used. `/readyz` returned 200 after that successful
extraction. Sanitized evidence is stored in
`artifacts/live_profile_A_deployed.json`.

An earlier production trace (`final-p0-acceptance-2`) remains useful drift
evidence: its identity-less RSC response correctly fell back to the authenticated
profile page and stopped on a 302 challenge. The new success proves that this
failure was not a fabricated profile or a permanent parser fallback.

Evidence labels have these exact meanings:

- `LIVE`: observed through a current direct authenticated LinkedIn request.
- `REAL_HAR_REPLAY`: deterministically parsed from a real captured response.
- `SYNTHETIC_UNIT`: produced only by synthetic test input.

Only `LIVE` evidence can establish production extraction success. Passing tests
and `REAL_HAR_REPLAY` prove contracts and parsing, not current upstream behavior.

## Verified local live evidence

On 2026-08-30, two controlled direct-HTTP extractions succeeded from the local
environment with retries disabled. No browser runtime, fixture, replay, or cache
was used:

| Profile | Core | Experience | Education | Skills | Certifications | Languages | Image |
|---|---:|---:|---:|---:|---:|---:|---:|
| Shorya Mishra | present | 5 | 1 | 3 | 5 | 0 | present |
| Bill Gates | present | 3 | 2 | 0 | 0 | 0 | present |

For both calls, `profile_view` and the required section operations succeeded and
`retrieval.mode` was `live` with `fixture=false`. The names, canonical URLs, and
resolved identities differed. Sanitized evidence is stored in
`artifacts/live_profile_A.json` and `artifacts/live_profile_B.json`. Empty
Languages is an observed result, not evidence of a parser failure.

The supplied real HAR independently replayed as Experience 5, Education 1,
Skills 3, Certifications 5, and Languages 0 (`REAL_HAR_REPLAY`). The HAR itself
is excluded from Git because it contains private profile/session context.

## Active extraction protocol

The deployed primary protocol is LinkedIn SDUI over React Flight:

1. `POST /flagship-web/rsc-action/actions/component` with the
   `profileCardsActivity` component and vanity-name payload.
2. Resolve the target-owned `prioritizedProfileId` and semantic name, headline,
   and image SetState values from the Flight model records.
3. If core parsing drifts, try the authenticated direct-HTTP `profile_page`
   fallback and parse embedded semantic profile data. Challenges remain terminal.
4. Request the enabled Experience, Education, Skills, Certifications, and
   Languages profile-card components using that target identity.
5. Parse semantic entities and normalize them against the public schema.

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
        +-- usable identity ----------------------+
        |                                         |
        +-- parser drift -> authenticated page ---+
                                                  |
                                                  v
                                        target identity resolver
        |
        v
section RSC requests -> semantic Flight parser -> schema 1.2.0
```

## API

The deployment root is an extraction desk for request-scoped sessions. A caller
submits up to 10 profile URLs, their current `li_at` and `JSESSIONID` cookie
values, optional companion cookies, User-Agent, and Accept-Language. These
values live only in the request's isolated runtime: they are not written to the
job store, logged, cached, returned, or retained after the transport closes.
The response carries `Cache-Control: no-store`, and the page clears all secret
inputs immediately after submission. This is an alternative to configuring a
shared LinkedIn session in the backend. No Profile Refinery account or product
API key is required for this request-scoped route.

```text
POST /v1/session-extractions

{
  "urls": ["https://www.linkedin.com/in/example/"],
  "session": {
    "li_at": "<request-scoped value>",
    "jsessionid": "<request-scoped value>",
    "companion_cookies": "bcookie=...; bscookie=...; liap=true",
    "user_agent": "<the session's browser User-Agent>",
    "accept_language": "en-US,en;q=0.9"
  }
}
```

Profiles are processed sequentially. An upstream challenge or open circuit
stops the remaining list; skipped entries are explicit and no alternate account,
proxy rotation, browser, fixture, or replay is attempted. The web interface can
download the returned normalized records as JSON or a safe flattened CSV.
Fields outside the current direct-HTTP contract—such as professional email,
company industry, follower counts, and connection degree—remain unavailable
rather than being inferred.

The operator-only server-configured single-profile endpoint remains available
for existing integrations and retains its generic `X-API-Key` protection:

```bash
curl -H "X-API-Key: $KEY" \
  "https://profile-refinery-api.vercel.app/v1/profiles?url=https://www.linkedin.com/in/example/"
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

## Offline batch, file, and export subsystem

The batch subsystem is independently verified with mocked/replay extractor data;
this is `SYNTHETIC_UNIT`/non-live evidence and does not imply LinkedIn availability.

- Inputs: pasted text, TXT, CSV, JSON, XLSX, DOCX, and PDF.
- Discovery: member URLs only, canonicalization, cross-file deduplication, and
  occurrence provenance (offset, line/paragraph/page, CSV column, JSON path,
  XLSX sheet/cell).
- Safety/limits: content-based type detection, malformed and unsupported input
  handling, encrypted-PDF rejection, 2,000-page PDF cap, 20-sheet/10,000-row
  XLSX caps, upload and URL limits.
- Batch behavior: idempotency, deterministic job IDs/states, bounded concurrency,
  partial-failure isolation, queue control, and journal restart recovery.
- Exports: complete JSON records, deterministic flattened CSV, and XLSX sheets
  `profiles`, `experience`, `education`, `skills`, `certifications`, `languages`,
  `provenance`, and `failures`. CSV/XLSX formula-like cells are stored as text.

Endpoints:

```text
POST /v1/batches
GET  /v1/batches/{batch_id}
GET  /v1/batches/{batch_id}/profiles
GET  /v1/batches/{batch_id}/profiles/{profile_id}
GET  /v1/batches/{batch_id}/report
GET  /v1/batches/{batch_id}/export?format=json|csv|xlsx
```

PDF is supported as input. PDF output is not required and is not implemented.

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

`APP_API_KEYS` is optional and applies only to protected operator/batch routes.
The public request-scoped desk does not use it. Backend-session extraction
additionally requires session material for an account the operator owns:

```text
LINKEDIN_LI_AT=<li_at value>
LINKEDIN_JSESSIONID=<JSESSIONID value>
LINKEDIN_COOKIE=<optional additional cookie header>
LINKEDIN_EGRESS_PROXY=<optional single static HTTP(S) proxy URL>
LINKEDIN_USER_AGENT=<exact user agent associated with the owned session>
LINKEDIN_ACCEPT_LANGUAGE=<language header associated with that session>
```

Cookie values, CSRF values, and API keys must never be logged, committed, or
included in comparison reports. Live mode fails closed when session material or
semantic identity is unavailable. `LINKEDIN_EGRESS_PROXY` is optional and is
passed to HTTPX as one operator-managed endpoint; Profile Refinery does not rotate proxies.
When it is absent, HTTPX may use the standard `HTTPS_PROXY`/`ALL_PROXY`
environment configuration. The transport enables HTTP/2 and never follows
redirects automatically.

Other supported environment names are documented in `.env.example`: caller
rate limits, upstream timeout/size/retry limits, governor and breaker settings,
schema/registry paths, and the local store path. Values belong only in local or
deployment secrets.

## Local setup

```bash
uv sync --extra dev
cp .env.example .env
uv run uvicorn profile_refinery_api.main:app --host 127.0.0.1 --port 8000
```

Populate only the owned-session and caller-key values needed for the run. With
no LinkedIn session configured, `/healthz` remains healthy while `/readyz` and
profile extraction fail closed.

## Production deployment

`vercel.json` deploys the FastAPI public surface to Vercel. `Dockerfile` and
`render.yaml` provide a persistent-process alternative. Set secret values in the
host's environment and never commit `.env`.

The production trace above proves that Vercel reached LinkedIn and received a
302 on the authenticated page fallback. It does **not** prove why LinkedIn chose
that response or that changing egress will fix it. A single static egress proxy
can be configured with `LINKEDIN_EGRESS_PROXY` for a controlled environment
comparison; it is not a success guarantee and must not be used as a rotating or
access-control-circumvention mechanism.

There is no profile-response cache in live mode. Consequently, a live response
cannot be served stale, from replay, or from a fixture.

## Local verification

```bash
uv sync --extra dev
uv run pytest
uv run ruff check src tests config scripts
uv run mypy src/profile_refinery_api
uv run python scripts/security_audit.py
uv run pip-audit
```

Current acceptance-suite count: `148` tests. This count is updated
from the full `pytest` run; it is not evidence of live LinkedIn extraction.

## Known limitations

- Public extraction depends on a short-lived owned LinkedIn session and upstream
  behavior; a later challenge or schema change must still fail closed.
- Certifications now has non-empty `LIVE` and `REAL_HAR_REPLAY` evidence.
  Languages was reached and parsed successfully but was empty on both live
  profiles and the real HAR; a non-empty real Languages case remains unverified.
- The configured static proxy and alternative persistent host are deployment
  options only. Neither has been verified to change LinkedIn's response.
- Profile completeness is viewer- and upstream-contract-dependent. Legitimately
  absent data remains null or empty; unknown data is never inferred.
- `/readyz` records observed success in process memory. On a serverless host, a
  cold instance can conservatively return `UNVERIFIED` until that instance
  completes a live profile request.

## Safety boundary

The project does not solve CAPTCHAs, rotate accounts or proxies, generate
challenge tokens, spoof browser fingerprints, automate login, or circumvent
access controls. When LinkedIn refuses or changes the response, the API returns a
typed failure and preserves the distinction among `LIVE`, `REAL_HAR_REPLAY`, and
`SYNTHETIC_UNIT` evidence.
