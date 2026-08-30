# Architecture

## Design principles

Profile Refinery separates acquisition, semantic interpretation, normalization, and presentation. The upstream is undocumented and mutable, so a transport-level HTTP success is insufficient: an operation succeeds only when its parser establishes usable target-owned data.

The design follows five invariants:

1. live mode fails closed and cannot silently load fixture, replay, or cached profile data;
2. URLs never control the outbound host or arbitrary path;
3. target identity is resolved before section entities are accepted;
4. challenges stop the session and open the circuit breaker;
5. missing values remain missing with explicit status and provenance.

## Components

```text
FastAPI boundary
  ├─ canonicalizer and request validation
  ├─ request-scoped extraction runtime
  ├─ operator single-profile API
  ├─ file discovery and batch service
  └─ JSON/CSV/XLSX/HTML presentation
             │
             ▼
ProfileOrchestrator
  ├─ core plan: profile_view → parser-aware profile_page fallback
  ├─ bounded location enrichment
  ├─ identity-scoped section plan
  └─ normalization and schema validation
             │
             ▼
UpstreamGovernor
  ├─ semaphore
  ├─ token bucket
  └─ circuit breaker
             │
             ▼
LinkedInTransport
  ├─ operation registry
  ├─ session/CSRF construction
  ├─ HTTP/2 client with redirects disabled
  └─ status, content-type, and size classification
             │
             ▼
RSC decoder and deterministic semantic parsers
```

## Protocol registry

`config/operation_registry.yaml` is the control plane for upstream requests. Each entry names the semantic operation, evidence status, HTTP method and fixed path, transport family, parser, component identifier, and observation reference. Code never accepts an arbitrary upstream URL from a caller.

The active core operation posts a vanity-scoped JSON structure to LinkedIn's SDUI component action endpoint. The Flight decoder reconstructs model records and SetState actions, then the identity resolver requires target-owned semantic markers. If the response is syntactically valid but identity-less, `UpstreamOperationDrift` advances the core plan to the authenticated profile-page fallback. Authentication failures, challenges, circuit-open, and confident not-found outcomes remain terminal.

After core identity succeeds, section operations use the resolved profile identity. Each optional section is isolated: transport or parser failure is recorded as coverage/warning metadata and makes the normalized response partial. No failed section is represented as a successful empty section.

## Data model

The public response is a strict Pydantic model validated again against `schemas/profile-response.schema.json`. Every field carries:

- a typed value or `null`;
- an availability status;
- source operation and observation time;
- parser version and optional entity reference/normalization note.

Retrieval metadata fixes mode to `live`, source to `linkedin`, and fixture to `false`. Response metadata records operations attempted/succeeded, request-local upstream call count and latency, transport strategy, warnings, and section coverage.

## Reliability and state

The governor controls every LinkedIn operation. A semaphore bounds concurrency; a token bucket limits burst and sustained rate; the breaker transitions `CLOSED → OPEN → HALF_OPEN` and permits one recovery probe. Network and eligible 5xx retries occur only in the transport layer, preventing multiplicative retry storms.

Readiness is intentionally stronger than liveness. `/healthz` reports process health. `/readyz` requires valid configuration, a usable session, a closed breaker, and a normalized live success observed by the current runtime. Serverless cold starts can therefore return conservative `UNVERIFIED` readiness.

There is no live profile response cache. Concurrent batch jobs for the same canonical URL may share one in-flight task, but followers receive the owner's real terminal result; completed responses are not reused across later requests. The batch journal persists job state through its storage abstraction. Crash-restored running jobs return to pending because no worker lease survives process death.

## Batch and discovery

Discovery is a local, transport-independent pipeline:

```text
bytes → content sniffing → bounded decoder → URL occurrences
      → strict canonicalization → deduplication + provenance
```

Supported inputs are TXT, CSV, JSON, XLSX, DOCX, and PDF. OOXML member count and expanded-size limits defend against archive bombs; PDF and spreadsheet dimensions are bounded. LinkedIn post URLs are retained but not mapped to authors without a verified protocol.

Batch execution has deterministic IDs, idempotency, bounded concurrency, explicit state transitions, partial failure, and JSON/CSV/XLSX exports. Failed export rows preserve the submitted LinkedIn URL. Spreadsheet formulas are neutralized. Export responses are non-cacheable.

## Security boundaries

- strict HTTPS host/path canonicalization prevents SSRF;
- fixed registry paths prevent caller-controlled upstream routing;
- credentials stay in environment configuration or request-local memory;
- logs use an allowlist and exclude URLs, headers, cookies, payloads, and keys;
- redirects are exposed for classification rather than followed;
- media proxying allowlists LinkedIn media hosts and streams with a hard byte ceiling;
- all problems use stable typed codes and non-secret details.

See [SECURITY.md](SECURITY.md) for the full control set and [PRIVACY_AND_PLATFORM_NOTES.md](PRIVACY_AND_PLATFORM_NOTES.md) for deployment responsibilities.

## Deployment topology

`vercel.json` exposes the public FastAPI application on Vercel. `Dockerfile` and `render.yaml` support a persistent-process deployment. Vercel is suitable for the stateless request-scoped surface, but its ephemeral filesystem and process-local readiness/breaker state are explicit constraints. A horizontally scaled deployment should supply shared rate limiting, breaker coordination, and persistent `JournalStore` semantics.

Architecture decisions are recorded in [docs](docs/). Upstream evidence and safe protocol shapes are recorded separately so operational code remains small and deterministic.
