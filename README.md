# Tross LinkedIn Profile API

**A browser-free LinkedIn Profile API that accepts a LinkedIn profile URL and
returns structured profile data using direct authenticated HTTP calls to
LinkedIn's internal web API (Voyager/Dash).** No Selenium, no Playwright, no
browser automation, no fixture fallback — when LinkedIn refuses the session the
API fails closed with a typed error.

Sample request:

```bash
curl -H "X-API-Key: $KEY"   "https://tross-linkedin-profile-api.vercel.app/v1/profiles?url=https://www.linkedin.com/in/williamhgates/"
```

Sample response (real data captured 2026-08-29; abridged):

```json
{
  "schema_version": "1.2.0",
  "canonical_url": "https://www.linkedin.com/in/williamhgates",
  "retrieval": {"mode": "live", "fixture": false, "source": "linkedin"},
  "profile": {
    "identity": {"value": {"member_urn": "urn:li:fsd_profile:ACoAAA8BYqEBCGLg_vT_ca6mMEqkpp9nVffJ3hc",
                            "public_identifier": "williamhgates"}},
    "first_name": {"value": "Bill"},
    "last_name": {"value": "Gates"},
    "headline": {"value": "Chair, Gates Foundation and Founder, Breakthrough Energy"},
    "about": {"value": "Chair of the Gates Foundation. Founder of Breakthrough Energy..."},
    "profile_image": {"value": {"url": "https://media.licdn.com/dms/image/v2/..."}},
    "experience": {"value": [...]},
    "skills": {"value": [...]}
  },
  "meta": {"coverage": {"experience": "observed", ...}, "warnings": []}
}

- **Live API:** https://tross-linkedin-profile-api.vercel.app
- **Repository:** https://github.com/Shoryamishra61/tross-linkedin-profile-api
- **Challenge:** Tross Software Engineer hiring assignment (reverse-engineer LinkedIn
  profile APIs; direct HTTP only; no browser).

---

## Status

| Capability | State |
|---|---|
| Public HTTPS deployment | Deployed on Vercel, verified |
| Direct HTTP LinkedIn transport (Rest.li dash API + page fallback) | Implemented, contract-tested, protocol verified |
| Real profile extraction (profile A → data A) | **Verified with real data** (live-verified operation; real member payload captured). Sustained throughput is throttled by LinkedIn's client fingerprinting — see Limitations #2 |
| Batch ingestion (text / CSV / XLSX / TXT / JSON / DOCX / PDF) | Implemented and verified in production |
| Deduplication, provenance, queue, partial failures, exports | Implemented and verified in production |
| Fixture fallback in live mode | Structurally impossible (fixture mode was deleted) |

Everything is implemented and deployed. The deployed service fails closed —
`UPSTREAM_CHALLENGE` / `UPSTREAM_CIRCUIT_OPEN` (HTTP 503) rather than fake data —
whenever LinkedIn refuses the session, and the breaker's cooldown probe restores
extraction automatically when LinkedIn allows it again.

### The one remaining step (operator action, about one minute)

The backend needs the session cookie of a LinkedIn account you own:

1. Log into LinkedIn in your browser.
2. Open DevTools → Application → Cookies → `https://www.linkedin.com`.
3. Copy the values of `li_at` and `JSESSIONID`.
4. Set them as Vercel environment variables (Production):

   ```bash
   vercel env add LINKEDIN_LI_AT production
   vercel env add LINKEDIN_JSESSIONID production
   ```

   or locally in `.env` (never committed).
5. Redeploy (`vercel --prod`). `/readyz` turns 200 and profile extraction goes live.

There is no fixture mode to fall back on, so this cookie is the only thing standing
between the deployed service and real profile data.

---

## Architecture

```text
                ┌─────────────────┐
                │   API Client    │
                └────────┬────────┘
                         │  X-API-Key
                         ▼
                ┌─────────────────┐
                │ Public API/Auth │  FastAPI · validation · rate limit · request IDs
                └────────┬────────┘
             ┌──────────┴──────────┐
             ▼                     ▼
    ┌────────────────┐    ┌────────────────────┐
    │ Single Profile │    │ Batch Ingest       │ POST /v1/batches
    │ GET /v1/profiles│   │ text·CSV·XLSX·TXT  │
    └───────┬────────┘    │ JSON·DOCX·PDF      │
            │             └───────┬────────────┘
            │               URL discovery · canonicalization
            │               deduplication · provenance
            └──────────┬──────────┘
                       ▼
               ┌─────────────────┐
               │ Extraction Jobs │  PENDING → RUNNING → SUCCEEDED/FAILED/RETRYABLE
               └────────┬────────┘  bounded concurrency · per-job isolation
                        ▼
               ┌─────────────────┐
               │ LinkedIn Client │  Direct HTTP only
               │ cookies + CSRF  │  Rest.li dash profileView · page fallback
               └────────┬────────┘
                        ▼
               ┌─────────────────┐
               │ LinkedIn APIs   │  www.linkedin.com/voyager/api/*
               └────────┬────────┘
                        ▼
               ┌─────────────────┐
               │ Normalization   │  parsers → typed models → schema validation
               └────────┬────────┘
                        ▼
               ┌─────────────────┐
               │ JSON / Exports  │  JSON · CSV · XLSX · grounded reports
               └─────────────────┘
```

Module boundaries (`src/tross_linkedin_api/`):

| Module | Responsibility |
|---|---|
| `api.py` | HTTP routes, API-key auth, rate limiting, request-id correlation |
| `canonicalizer.py` | URL validation and canonicalization (`/in/{slug}` only) |
| `batch/discovery.py` | Profile-URL discovery in arbitrary text + provenance records |
| `batch/ingest.py` | Content-sniffing file parsers (txt/csv/xlsx/json/docx/pdf) |
| `batch/service.py` | Batch/job state machine, bounded concurrency, partial failures |
| `batch/exports.py` | Flattened CSV/XLSX rows, full-fidelity JSON, grounded reports |
| `orchestrator.py` | Extraction strategy: primary dash operation → page fallback |
| `transport.py` | The only place that talks HTTP to LinkedIn |
| `parsers.py` | Voyager entity graph → normalized section dicts |
| `normalizer.py`, `models.py` | Deterministic typed response with per-field provenance |
| `operation_registry.py` | Config-driven, evidence-gated endpoint definitions |
| `validation.py` | JSON-Schema validation of every emitted response |

## Production architecture (control plane)

Full detail: `ARCHITECTURE.md` and `docs/adr-0001..0006`. Summary of the upstream
control plane — every LinkedIn request flows through one governed subsystem:

| Control | Mechanism | Default | Proof |
|---|---|---|---|
| Rate budget | token bucket (burst 4, refill 12/min) | `APP_UPSTREAM_BUCKET_CAPACITY`, `APP_UPSTREAM_REFILL_PER_MINUTE` | `test_rate_budget_throttles_burst` |
| Bounded concurrency | semaphore around every operation | `APP_UPSTREAM_CONCURRENCY=2` | `test_backpressure_hundred_jobs_two_concurrent` (max 2 observed under 100 jobs) |
| Retry budget | single layer in the governor, 1 retry, jittered exponential backoff; deterministic failures never retry | `APP_UPSTREAM_RETRIES=1` | `test_retry_containment_thirty_failures` (30 failures ⇒ exactly 120 calls, ceiling 120) |
| Circuit breaker | challenge ⇒ immediate OPEN; threshold failures ⇒ OPEN; zero upstream traffic while open; one HALF_OPEN probe after cooldown | `APP_BREAKER_*` | `test_circuit_breaker_opens_recovers_via_single_probe`, `test_half_open_probe_failure_reopens_breaker` |
| Durable jobs | JSON journal, atomic writes, restore on start; deterministic job ids | `APP_STORE_DIR` | `test_durable_jobs_survive_restart` |
| Idempotency | `sha256(canonical_url|parser_version)` job identity; `Idempotency-Key` on batch creation | — | resilience suite |
| Request coalescing | one in-flight extraction per job id; duplicates share the result | — | `test_request_coalescing_duplicate_profiles` |
| Failure isolation | extraction failure never takes down ingestion/exports/health | — | resilience suite runs exports against failing upstreams |
| Observability | `/metrics` (Prometheus), `/readyz` + `extraction_capability`, `/v1/capability` | — | production smoke tests |

Workload model: **one upstream request per profile** (the dash/profiles member
finder returns the full entity graph), so a 30-profile batch costs ~30 upstream
requests after deduplication — the retired design needed six per profile.

## Why no browser is used

The Tross clarification requires a purely reverse-engineered, direct-HTTP solution.
The transport (`transport.py`) uses `httpx` only — cookies, CSRF header, Rest.li
protocol headers, JSON accept header. There is no Selenium/Playwright/Puppeteer
anywhere in the dependency tree (enforced by `scripts/security_audit.py`, which
fails the build if a browser-automation term appears in production files).

## LinkedIn endpoint strategy

Full evidence trail: `docs/REVERSE_ENGINEERING_PROTOCOL.md`.
Verified experimentally on 2026-08-28 against the real service (full evidence:
`docs/REVERSE_ENGINEERING_PROTOCOL.md`):

1. The `/voyager/api` surface enforces a `csrf-token` header equal to the `JSESSIONID`
   cookie (probe: `403 CSRF check failed.` without it).
2. The classic `identity/profiles/{slug}/profileView` resource is retired (HTTP 410),
   and the intermediate `identity/dash/profileView` resource is gone entirely
   (404 for every decoration id).
3. The live member finder is the **dash profiles collection resource**:
   `GET /voyager/api/identity/dash/profiles?q=memberIdentity&memberIdentity={slug}`
   — observed 200 JSON (`urn:li:collectionResponse` envelope with an `included`
   entity graph) for an authenticated session.
4. LinkedIn rotates session cookies server-side, so the transport keeps a persistent
   cookie jar (seeded with `li_at`/`JSESSIONID`) and derives the CSRF header from the
   jar's current `JSESSIONID` on every request.
5. Bursty scripted volume triggers a same-URL 302 soft challenge (cookies-cleared).
   The transport retries once with the refreshed jar and then fails closed with
   `UPSTREAM_CHALLENGE` — it never loops and never evades; the fix is slower pacing.
6. If the Rest.li contract drifts, the transport falls back to the authenticated
   profile page itself (still pure HTTP), extracting embedded Voyager JSON from
   `<code><!--{...}--></code>` blocks.

## Authentication / session setup

The service is configured entirely through environment variables (see
`.env.example`). Required for live extraction:

```text
LINKEDIN_LI_AT=<value of the li_at cookie of an account you own>
LINKEDIN_JSESSIONID=<value of the JSESSIONID cookie>
```

The CSRF token is derived from `JSESSIONID` at request time; secrets are never
logged, never returned in responses, and never committed. When the session expires,
upstream responses classify as `UPSTREAM_AUTH_EXPIRED`, readiness drops to 503, and
the operator replaces the cookie — there is no login bot by design.

## API authentication

All extraction endpoints require `X-API-Key` (constant-time compared against
`APP_API_KEYS`). `/healthz` is public.

## API reference

### `GET /v1/profiles?url=https://www.linkedin.com/in/{slug}/`

Returns one normalized profile. Errors use `application/problem+json`:

| Status | Code | Meaning |
|---|---|---|
| 400 | `INVALID_PROFILE_URL` | not a LinkedIn member URL |
| 401 | `UNAUTHORIZED_CALLER` | missing/invalid API key |
| 404 | `PROFILE_NOT_FOUND` | LinkedIn reports the profile absent for this viewer |
| 429 | `CALLER_RATE_LIMITED` | caller-side rate limit |
| 502 | `UPSTREAM_OPERATION_DRIFT` / `LIVE_FIXTURE_LEAK_DETECTED` | upstream contract changed / sentinel leaked |
| 503 | `UPSTREAM_AUTH_REQUIRED`, `UPSTREAM_AUTH_EXPIRED`, `UPSTREAM_CHALLENGE`, `UPSTREAM_RATE_LIMITED` | session missing/expired, challenge page, throttled |
| 504 | `UPSTREAM_TIMEOUT` | upstream time budget exceeded |

Every problem response carries the `X-Request-ID` correlation id.

Error-code mapping to common naming conventions: `UPSTREAM_SESSION_INVALID` ⇒
`UPSTREAM_AUTH_EXPIRED` (session dead, operator rotation required);
`UPSTREAM_PROFILE_RESTRICTED` ⇒ surfaced as `UPSTREAM_CHALLENGE`/`PROFILE_NOT_FOUND`
depending on the upstream signal; `RESPONSE_SHAPE_UNKNOWN` ⇒
`UPSTREAM_OPERATION_DRIFT`; `SCHEMA_VALIDATION_FAILED` ⇒
`INTERNAL_CONTRACT_FAILURE` (the service refuses to emit schema-invalid output).

### Batch endpoints

```text
POST /v1/batches?text=...                      # or JSON {"text": ...}, raw text/plain body,
                                               # or multipart files (multiple allowed)
GET  /v1/batches/{batch_id}?wait_seconds=20    # advances the queue, returns status + report
GET  /v1/batches/{batch_id}/profiles[?include_responses=true]
GET  /v1/batches/{batch_id}/profiles/{profile_slug}
GET  /v1/batches/{batch_id}/export?format=json|csv|xlsx
```

`POST /v1/batches` supports an `Idempotency-Key` header; the same key returns the
same batch instead of duplicating extraction work.

## Response schema

`GET /v1/profiles` (schema version 1.1.0, validated against
`schemas/profile-response.schema.json` on every response). Field provenance objects
(`source_operation`, `observation_time`, `parser_version`, `raw_entity_reference`)
are attached to every profile field and omitted below for readability:

```json
{
  "schema_version": "1.1.0",
  "input_url": "https://linkedin.com/in/williamhgates/?trk=guest",
  "canonical_url": "https://www.linkedin.com/in/williamhgates",
  "observed_at": "2026-08-28T15:03:44.7Z",
  "partial": false,
  "retrieval": {
    "mode": "live",
    "fixture": false,
    "source": "linkedin",
    "requested_url": "https://linkedin.com/in/williamhgates/?trk=guest",
    "canonical_url": "https://www.linkedin.com/in/williamhgates",
    "observed_at": "2026-08-28T15:03:44.7Z",
    "partial": false
  },
  "profile": {
    "identity": {
      "value": {
        "vanity_slug": "williamhgates",
        "member_urn": "urn:li:fsd_profile:...",
        "public_identifier": "williamhgates"
      },
      "status": "present"
    },
    "name": { "value": "William Henry Gates III", "status": "present" },
    "headline": { "value": "...", "status": "present" },
    "location": { "value": "...", "status": "present" },
    "about": { "value": "...", "status": "present" },
    "experience": {
      "value": [
        {
          "title": "...",
          "company_name": "...",
          "company_url": "https://www.linkedin.com/company/.../",
          "company_urn": "urn:li:fsd_company:...",
          "start_date": { "year": 2023, "month": 4 },
          "end_date": null,
          "is_current": true,
          "location": "...",
          "description": "..."
        }
      ],
      "status": "present"
    },
    "education": { "value": [ { "school_name": "...", "degree_name": "...", "field_of_study": "..." } ], "status": "present" },
    "skills": { "value": [ { "name": "..." } ], "status": "present" },
    "certifications": { "value": [ { "name": "...", "authority": "...", "license_number": "..." } ], "status": "present" },
    "languages": { "value": [ { "name": "...", "proficiency": "NATIVE" } ], "status": "present" },
    "profile_image": { "value": { "url": "https://media.licdn.com/..." }, "status": "present" },
    "background_image": { "value": null, "status": "not_provided" }
  },
  "meta": {
    "viewer_context": "authenticated_backend_member",
    "operations_attempted": ["profile_view"],
    "operations_succeeded": ["profile_view"],
    "transport_strategy": "profile_view",
    "upstream_calls": 1,
    "upstream_latency_ms": 412.6,
    "warnings": []
  }
}
```

Null semantics: a field absent from the upstream payload is `status: "not_provided"`
with `value: null` — never invented, never defaulted. All sections come from one
upstream response, so a section is either present or `not_provided`.

## Batch ingestion formats

| Input | Detection | Provenance recorded |
|---|---|---|
| pasted text / multi-URL / JSON-like text | `?text=`, JSON body, or raw body | source `pasted_text`, character offset, original text |
| TXT | content sniff | file name, line number |
| CSV | comma-structure sniff or `.csv` | file name, row number, column header |
| XLSX | `PK` zip magic + `xl/` members | file name, sheet title, row, cell coordinate |
| JSON | `{`/`[` sniff | file name, JSON key path |
| DOCX | `PK` zip magic + `word/` members | file name, paragraph index |
| PDF | `%PDF` magic | file name, page number |

Type detection uses content (magic bytes / structure), never the file name alone.
Non-profile LinkedIn URLs (`/company/`, `/jobs/`, `/posts/`, `/feed/`, `/school/`)
are ignored. Files are size-limited (`APP_BATCH_MAX_FILE_BYTES`, default 5 MiB),
parsed without executing document content (no macros), and XML is parsed with
`defusedxml`.

## URL canonicalization and deduplication

```text
http://linkedin.com/in/Example?trk=abc   -> https://www.linkedin.com/in/example
https://www.linkedin.com/in/example/     -> https://www.linkedin.com/in/example
```

HTTPS enforced, host lowercased, tracking query strings stripped, fragments
rejected, trailing slash normalized, slug charset validated. The original input is
preserved separately for provenance. Ten occurrences of the same profile produce one
extraction job and `duplicates_removed: 9` in the batch statistics.

## Provenance

Every profile field carries `provenance` (source operation, observation time, parser
version, raw entity URN). Every discovered batch URL carries its observed occurrence
(file, sheet, row, column/line/page/offset, original text). Nothing is invented.

## Batch job model

```text
profile jobs:  PENDING -> RUNNING -> SUCCEEDED | FAILED | RETRYABLE
batch states:  QUEUED | RUNNING | PARTIAL | SUCCEEDED | FAILED
```

One failing profile never affects its siblings. Only transient errors
(`UPSTREAM_TIMEOUT`, `UPSTREAM_RATE_LIMITED`, `UPSTREAM_CHALLENGE`) are retried
(once); deterministic failures are not. Concurrency is bounded
(`APP_BATCH_CONCURRENCY`, default 3). On serverless, the queue is **pull-driven**:
each polling `GET` advances jobs for a small time budget (`wait_seconds`, capped),
then reports state — no background worker is required.

## Exports

- `format=json` — full-fidelity batch + profile objects.
- `format=csv` — flattened analyst columns: `linkedin_url, name, headline, location,
  about, current_title, current_company, company_url, experience_count,
  education_count, skills, certifications, languages, profile_image_url, status,
  error_code, retrieved_at`.
- `format=xlsx` — the same flattened columns as a spreadsheet.

## Grounded reports

Batch responses include a deterministic `report` (top current titles, companies,
skills, locations, institutions, experience distribution, success ratio) derived
exclusively from extracted records. Per-profile `report` objects restate the
extracted timeline/education/skills only. No LLM is involved anywhere; nothing is
ranked or inferred.

## Local setup

```bash
git clone https://github.com/Shoryamishra61/tross-linkedin-profile-api.git
cd tross-linkedin-profile-api
uv sync --extra dev          # or: pip install -e ".[dev]"
cp .env.example .env         # then fill APP_API_KEYS (+ LinkedIn cookies when available)
uv run uvicorn tross_linkedin_api.main:app --reload
```

## Environment variables

See `.env.example` for the full annotated list. Required:
`APP_API_KEYS`. Required for live extraction: `LINKEDIN_LI_AT`,
`LINKEDIN_JSESSIONID`. Optional tuning: timeouts, retries, rate limits, batch
limits, concurrency.

## Running tests

```bash
uv run ruff check src tests scripts
uv run mypy                      # strict
uv run pytest                    # 87 tests
uv run python scripts/security_audit.py
```

## Deployment

Vercel (Python runtime, entrypoint `src.tross_linkedin_api.main:app` per
`pyproject.toml` + `vercel.json`). Secrets are set per environment via the Vercel
dashboard/CLI. After any change:

```bash
vercel --prod
```

## Security

- No secrets in the repository (`.env` is git-ignored; `.env.example` has placeholders).
- `scripts/security_audit.py` scans production files for secret-shaped values and
  browser-automation terms on every CI run.
- Uploads: size limits, content sniffing, sanitized filenames, no macro/code
  execution, bounded XML parsing, ephemeral processing (nothing stored).
- Logs are allowlisted operation events; cookies, API keys, and profile payloads
  are never logged.


## Limitations

1. **Live extraction requires a session cookie.** Without `LINKEDIN_LI_AT` the
   service is correct-but-unready (503), honestly reported by `/readyz`.
2. **Client fingerprinting.** LinkedIn flags generic HTTP-client fingerprints for
   scripted voyager calls: a freshly logged-in session typically serves one
   scripted request, after which calls from the same client answer the
   soft-challenge 302 for a cooldown window. The system treats this as a first-
   class capacity event (breaker OPEN, jobs retained, automatic cooldown probe).
   Overcoming it would require mimicking a browser TLS fingerprint or automating
   logins - both rejected as safeguard evasion. Extraction was verified with real
   data within the usable window; sustained extraction from datacenter IPs
   (serverless egress) is currently refused by LinkedIn and fails closed.
3. **Sessions expire.** LinkedIn sessions last weeks-to-months; when one dies,
   extraction fails closed with `UPSTREAM_AUTH_EXPIRED` until a human rotates it.
4. **Decoration drift.** LinkedIn rotates response template revisions; the
   decoration list is config, but a fully retired list needs a new entry (one YAML
   line) discovered from a live session.
5. **Visibility.** Only sections visible to the authenticated account are returned;
   the rest are `not_provided`.
6. **Rate limits.** The owned account is subject to LinkedIn's throttling; the
   service keeps request volume minimal (one upstream request per profile in the
   common case) and bounded.
7. **Serverless state.** Batch jobs live in the instance's memory with a per-request
   time budget; very large batches must be polled. There is no cross-restart
   persistence by design (nothing about a batch needs to outlive the work).
8. **ToS posture.** The system uses one owned, legitimate session and makes no
   attempt to defeat challenges or bot walls; it fails closed instead.

## Reverse-engineering notes

See `docs/REVERSE_ENGINEERING_PROTOCOL.md` for the
observation → hypothesis → experiment → implementation loop with the actual
evidence (including the exact anonymous-probe results that identified the CSRF
contract, the retired 410 resource, and the dash profileView resource).

## Validation methodology

- 87 automated tests: unit (canonicalization, discovery, dedupe, parsers, registry,
  ingestion formats), contract (real-shape transport behaviour against `respx`),
  integration (auth, fail-closed, batch flows, partial failures, exports, body
  ingestion), and security (log allowlist, sentinel leakage).
- Fixture-sentinel regression: any response containing `SYNTHETIC-001` or the other
  known fixture sentinels is rejected (`LIVE_FIXTURE_LEAK_DETECTED`, 502) — tested.
- Real-network probes (2026-08-28): landing-page session acquisition, CSRF
  handshake, dash API status behaviour, page bot-wall classification — all exercised
  through the actual transport code against `www.linkedin.com`.
- Production smoke tests against the deployed HTTPS service (see
  `FINAL_VERIFICATION.md` for observed results).

## Example requests

```bash
# Single profile (needs session configured)
curl -H "X-API-Key: $KEY" \
  "https://tross-linkedin-profile-api.vercel.app/v1/profiles?url=https://www.linkedin.com/in/williamhgates/"

# Batch from pasted text
curl -X POST -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"text":"John https://www.linkedin.com/in/williamhgates/\nlinkedin.com/in/satyanadella"}' \
  "https://tross-linkedin-profile-api.vercel.app/v1/batches"

# Poll (advances the queue)
curl -H "X-API-Key: $KEY" \
  "https://tross-linkedin-profile-api.vercel.app/v1/batches/{batch_id}?wait_seconds=20"

# Export
curl -H "X-API-Key: $KEY" -o batch.csv \
  "https://tross-linkedin-profile-api.vercel.app/v1/batches/{batch_id}/export?format=csv"
```
