# Profile Refinery

Profile Refinery is a browserless LinkedIn profile-normalization system built around authenticated direct HTTP protocols. It resolves semantic identity before accepting data, decodes LinkedIn SDUI/React Flight records, and returns a versioned profile model with field-level availability and provenance.

**Public application:** <https://profile-refinery-api.vercel.app>

**OpenAPI:** <https://profile-refinery-api.vercel.app/docs>

## Why this system exists

Rendered pages are a poor extraction contract: layout changes, virtualization, and presentation state obscure the entities a data pipeline needs. Profile Refinery instead treats upstream behavior as a protocol-research problem:

- request contracts are registered and evidence-labeled;
- target ownership is established before entity parsing;
- React Flight actions are decoded as semantic records, not DOM nodes;
- unknown structures become typed drift errors rather than guessed data;
- live, real-capture replay, and synthetic-unit evidence remain distinct;
- live mode has no fixture, replay, or stale-response escape hatch.

The current protocol uses the `profileCardsActivity` SDUI component for core identity, then identity-scoped profile-card components for Experience, Education, Skills, Certifications, and Languages. An authenticated profile-page operation is available as a core fallback and bounded location-enrichment path.

## Requirement coverage

| Requirement | Implementation |
|---|---|
| Public HTTPS API | Deployed at `https://profile-refinery-api.vercel.app` |
| Accept a LinkedIn profile URL | `GET /v1/profiles?url=…` and request-scoped `POST /v1/session-extractions` |
| Return profile details | Strict schema covers name, headline, location, about, experience, education, skills, certifications, languages, profile image, and background image when available |
| Backend credentials allowed | Operator-owned session can be supplied through deployment secrets; the public desk alternatively accepts an authorized request-scoped session |
| Public complete source | `https://github.com/Shoryamishra61/profile-refinery-api` |
| Setup, API, approach, limitations | This README plus `API_REFERENCE.md`, `ARCHITECTURE.md`, `REVERSE_ENGINEERING_METHOD.md`, and `LIMITATIONS.md` |
| Secrets excluded | `.env`, cookies, HAR files, raw captures, and generated live results are ignored; release gates and `scripts/security_audit.py` scan tracked source |

Fields are returned **when available to the authenticated viewer**. Absence, upstream failure, and parser drift are represented explicitly; the service never invents missing profile values.

## System shape

```text
LinkedIn URL / uploaded files
            │
            ▼
 validation · discovery · canonicalization · deduplication
            │
            ▼
 request-scoped or operator-owned authenticated HTTP transport
            │
            ▼
 rate budget · bounded retries · circuit breaker · size/type checks
            │
            ▼
 Flight decoder · target identity resolver · semantic section parsers
            │
            ▼
 schema validation · field provenance · JSON / CSV / XLSX / HTML card
```

No browser automation, automated login, CAPTCHA solving, account/proxy rotation, challenge-token generation, or fingerprint spoofing is present.

## Public extraction desk

The deployment root provides a mobile-friendly extraction workflow. A caller supplies an authorized LinkedIn session for that request only, then pastes profile URLs or uploads TXT, CSV, JSON, XLSX, DOCX, or PDF files. The service discovers up to 200 unique profile URLs with occurrence provenance and processes sequential API groups of at most 10.

Credentials are isolated in a transient runtime, never written to the job store, never returned, and never included in application logs. Responses use `Cache-Control: no-store`; the web client clears secret inputs after submission.

```http
POST /v1/session-extractions
Content-Type: application/json

{
  "urls": ["https://www.linkedin.com/in/example/"],
  "session": {
    "li_at": "<request-scoped value>",
    "jsessionid": "<request-scoped value>",
    "companion_cookies": "<optional cookie pairs>",
    "user_agent": "<session user agent>",
    "accept_language": "en-US,en;q=0.9"
  }
}
```

Each submitted URL receives an explicit `succeeded`, `partial`, `failed`, or `skipped` result. A challenge stops later requests for that session. Invalid URLs are rejected before transport execution.

### What each session value means

| Input | Significance | Input format |
|---|---|---|
| `li_at` | LinkedIn's primary signed-in session token. It authorizes authenticated profile requests and is the most sensitive input. | Value only, without `li_at=` |
| `JSESSIONID` | Session identifier used by LinkedIn's CSRF contract. The transport derives the `csrf-token` header from this same cookie value. It must come from the same session as `li_at`. | Value only; surrounding quotes are accepted |
| `bcookie` | Optional browser identifier that provides ordinary companion context. It does not authenticate the account and cannot replace `li_at`. | The web form accepts only the value after `bcookie=` |
| User-Agent | Identifies the client software associated with the authorized session. The web form fills the current browser value automatically. | Complete User-Agent string |
| Accept-Language | Preserves the request locale, which can affect localized profile text. | Standard header value such as `en-US,en;q=0.9` |

The web interface deliberately asks for only one companion value, `bcookie`, instead of a congested raw-cookie field. Backend API clients may optionally send additional ordinary companion cookies through `companion_cookies` using Cookie-header syntax:

```text
bcookie=v=2&…; bscookie=v=1&…; liap=true
```

Do **not** repeat `li_at` or `JSESSIONID` inside `companion_cookies`. They already have authoritative dedicated fields. Duplicating them can create conflicting cookie values and, for `JSESSIONID`, desynchronize the cookie from the derived CSRF header. Request-scoped validation rejects those duplicates; the server-configured transport also excludes them when importing companion cookies.

## API surface

| Endpoint | Purpose | Authentication |
|---|---|---|
| `GET /` | Extraction desk and profile-card viewer | Public |
| `POST /v1/link-discovery` | Discover canonical member/post URLs from text and files | Public |
| `POST /v1/session-extractions` | Request-scoped direct extraction, 1–10 profiles | Request session |
| `POST /v1/session-exports/xlsx` | Convert normalized results to a workbook | Public |
| `GET /v1/profiles?url=…` | Single profile using the server-configured session | `X-API-Key` |
| `POST /v1/batches` and `/v1/batches/{id}/*` | Persistent operator batch workflow and exports | `X-API-Key` |
| `GET /healthz` | Process liveness | Public |
| `GET /readyz` | Current live-extraction capability | Public |
| `GET /v1/capability` | Governor, breaker, and queue state | `X-API-Key` when configured |

See [API_REFERENCE.md](API_REFERENCE.md) for contracts and [schemas/profile-response.schema.json](schemas/profile-response.schema.json) for the normalized response.

## Normalized output

Every required field is present in the response envelope, even when unavailable:

- identity, first name, last name, full name, headline, location, and about;
- experience and education with structured dates and organization identifiers;
- skills, certifications, and languages;
- profile and background images;
- canonical URL, member URN, observation time, availability, and provenance;
- operations attempted/succeeded, upstream calls/latency, coverage, and warnings.

An empty array is data, not proof of parser completeness. `partial=true`, coverage, warnings, and field statuses distinguish absence from parser or upstream failure. Exports include JSON, flattened CSV, multi-sheet XLSX, and a self-contained responsive HTML profile card. Formula-like spreadsheet cells are escaped.

## Reliability model

All upstream calls pass through a shared governor with bounded concurrency, token-bucket pacing, one retry layer, and a challenge-aware circuit breaker. Redirects are not followed automatically. Status, content type, response size, and semantic identity are validated before an operation succeeds.

Core fallback is parser-aware: an HTTP 200 identity-less Flight stream is operation drift and permits the registered authenticated-page fallback; an upstream challenge remains terminal. Optional section drift produces an explicit partial response without fabricating values. `/readyz` requires configured session material, a closed breaker, and a successful normalized live observation in the current process.

Batch jobs use deterministic identifiers, idempotency, bounded workers, concurrent-request coalescing, partial-failure isolation, and a journal abstraction. Vercel storage is ephemeral; use a persistent `JournalStore` implementation for durable multi-instance operation.

## Local development

```bash
uv sync --extra dev --locked
cp .env.example .env
uv run uvicorn profile_refinery_api.main:app --host 127.0.0.1 --port 8000
```

Operator extraction needs an owned session in environment variables. The public request-scoped route does not require `APP_API_KEYS`; protected operator and batch routes do.

```text
APP_API_KEYS
APP_VALIDATION_API_KEY
LINKEDIN_LI_AT
LINKEDIN_JSESSIONID
LINKEDIN_COOKIE
LINKEDIN_EGRESS_PROXY
LINKEDIN_USER_AGENT
LINKEDIN_ACCEPT_LANGUAGE
```

All supported controls and safe defaults are documented in [.env.example](.env.example). Never commit `.env`, cookies, HAR files, or raw upstream responses.

## Verification

```bash
uv run ruff check src tests config scripts
uv run mypy src/profile_refinery_api
uv run pytest
uv run python scripts/security_audit.py
uv run pip-audit
```

Automated release gates perform only deterministic offline verification. Test success and capture replay do not establish current LinkedIn availability. Production verification must be a controlled authorized call and must report only safe field counts and provenance.

## Research and operations documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) — runtime boundaries and failure semantics
- [REVERSE_ENGINEERING_METHOD.md](REVERSE_ENGINEERING_METHOD.md) — evidence workflow
- [docs/REVERSE_ENGINEERING_PROTOCOL.md](docs/REVERSE_ENGINEERING_PROTOCOL.md) — redacted protocol contracts
- [SECURITY.md](SECURITY.md) — controls and incident history
- [PRIVACY_AND_PLATFORM_NOTES.md](PRIVACY_AND_PLATFORM_NOTES.md) — operator responsibilities
- [LIMITATIONS.md](LIMITATIONS.md) — explicit non-claims
- [docs](docs/) — architecture decision records

## Evidence policy

`LIVE` means a current authorized direct HTTP observation. `REAL_HAR_REPLAY` means deterministic parsing of a real redacted capture. `SYNTHETIC_UNIT` means authored test input. These labels are never interchangeable, and the system never uses an LLM to extract or fill profile fields.

## License

MIT. See [LICENSE](LICENSE).
