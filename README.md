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

## Approach and system design

The implementation treats LinkedIn as a versioned, evidence-gated protocol rather than a page to scrape. Fixed operation contracts acquire semantic React Flight records, a target-identity resolver proves which member owns the returned entities, deterministic parsers normalize only known structures, and schema validation rejects internally inconsistent output. Browser/UI structure is never the production extraction contract.

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

## API documentation

The research-oriented interactive documentation is available at [profile-refinery-api.vercel.app/docs](https://profile-refinery-api.vercel.app/docs). It includes authentication guidance, quickstarts, protocol flow, response semantics, failure taxonomy, operational readiness, evidence classes, and a searchable explorer generated from the current OpenAPI 3.1 document. The raw machine contract is [profile-refinery-api.vercel.app/openapi.json](https://profile-refinery-api.vercel.app/openapi.json).

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

## Setup instructions

### Prerequisites

- Python 3.12
- [`uv`](https://docs.astral.sh/uv/) for locked dependency installation
- an authorized LinkedIn session only when performing a controlled live request

### Install and run

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

### How to obtain your authorized session values with DevTools

Use only a LinkedIn account and session you own or are explicitly authorized to use. Never provide a LinkedIn password to Profile Refinery, a browser extension, a third party, or this repository.

#### Chrome, Edge, Brave, and other Chromium browsers

1. Sign in to LinkedIn manually at `https://www.linkedin.com` in your normal browser.
2. Open a LinkedIn page, press `F12` (or `Ctrl+Shift+I`), and select **Application**.
3. In the left sidebar, open **Storage → Cookies → https://www.linkedin.com**.
4. Find the cookie named `li_at`. Copy only its **Value** column. Do not copy `li_at=` and do not include surrounding whitespace.
5. Find `JSESSIONID`. Copy its **Value** from the same browser session. LinkedIn commonly displays a quoted value such as `"ajax:…"`; Profile Refinery accepts it with or without those surrounding quotes.
6. Optionally find `bcookie` and copy only its value. The public form asks for this one companion value and constructs `bcookie=<value>` itself.
7. Switch to **Network**, reload the LinkedIn page, and select an ordinary request to `www.linkedin.com`.
8. Under **Request Headers**, copy the complete `User-Agent` and `Accept-Language` values. The extraction desk fills the current browser User-Agent automatically, but verify it when the session came from a different browser or machine.
9. Close DevTools when finished. Avoid screenshots, screen sharing, clipboard-history synchronization, or pasting these values into chat or issue trackers.

#### Firefox

1. Sign in manually, press `F12`, and open **Storage → Cookies → https://www.linkedin.com**.
2. Copy the value columns for `li_at`, `JSESSIONID`, and optionally `bcookie` exactly as described above.
3. Use **Network → Headers** on a reloaded LinkedIn request to obtain `User-Agent` and `Accept-Language`.

#### Where each value goes

| DevTools value | Public extraction desk | Backend environment |
|---|---|---|
| `li_at` value | **li_at cookie value** | `LINKEDIN_LI_AT` |
| `JSESSIONID` value | **JSESSIONID cookie value** | `LINKEDIN_JSESSIONID` |
| optional `bcookie` value | **bcookie companion** | `LINKEDIN_COOKIE=bcookie=<value>` |
| `User-Agent` header | **Request fingerprint → User-Agent** | `LINKEDIN_USER_AGENT` |
| `Accept-Language` header | **Request fingerprint → Accept-Language** | `LINKEDIN_ACCEPT_LANGUAGE` |

Do not place `li_at` or `JSESSIONID` inside `LINKEDIN_COOKIE`. Their dedicated settings are authoritative, and `JSESSIONID` must remain synchronized with the derived CSRF header. Additional backend companion cookies, when genuinely needed, use normal Cookie-header syntax such as `bcookie=<value>; bscookie=<value>; liap=true`.

Treat all copied values as secrets. Store them in Vercel/host environment secrets or a local ignored `.env`, rotate them after accidental exposure, and never commit them—even temporarily.

## Verification

```bash
uv run ruff check src tests config scripts
uv run mypy src/profile_refinery_api
uv run pytest
uv run python scripts/security_audit.py
uv run pip-audit
```

Automated release gates perform only deterministic offline verification. Test success and capture replay do not establish current LinkedIn availability. Production verification must be a controlled authorized call and must report only safe field counts and provenance.

## Known limitations

- LinkedIn is an undocumented and mutable upstream. Challenges, authentication expiry, and semantic drift can interrupt extraction without notice.
- Completeness depends on the authenticated viewer. Hidden or absent values remain missing and are never inferred.
- A successful Languages operation has been observed, but the retained real evidence set does not contain a non-empty Languages example.
- Pagination is implemented only where a captured contract establishes cursor and termination semantics; universal full-history completeness is not claimed.
- Request-scoped extraction accepts 10 profiles per API call. The web desk coordinates larger discovered sets in sequential groups up to its configured 200-profile limit.
- Vercel has an ephemeral filesystem and process-local readiness/circuit state. Durable, horizontally scaled batch operation needs a persistent `JournalStore` and shared control-plane implementations.
- LinkedIn post URLs can be discovered, but author-profile resolution remains unavailable until a captured semantic contract proves that mapping.
- PDF is supported as an input format, not an export format.
- This project does not imply LinkedIn endorsement or establish a lawful basis for a specific operator. See [PRIVACY_AND_PLATFORM_NOTES.md](PRIVACY_AND_PLATFORM_NOTES.md).

The maintained limitation register is [LIMITATIONS.md](LIMITATIONS.md).

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
