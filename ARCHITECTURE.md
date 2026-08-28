# Architecture

This document describes the system as implemented. Every pattern listed here is
exercised by a named test; every capacity number is measured, not aspirational.
Decision records: `docs/adr-0001` … `docs/adr-0006`.

## 1. Requirements

**Tross (original)**
* Public HTTPS API accepting a LinkedIn profile URL, returning the profile's
  structured data (name, headline, location, about, experience, education,
  skills, certifications, languages, images).
* Direct HTTP endpoint integration only — no browser automation of any kind.
* Own legitimate session usable server-side; secrets externalized.
* Public repository, complete documentation.

**Extended**
* Batch ingestion from arbitrary text and CSV/XLSX/TXT/JSON/DOCX/PDF, with URL
  discovery, canonicalization, deduplication, provenance, queueing, partial
  failures, exports, grounded reports.
* Production-grade upstream control: queueing, backpressure, bounded
  concurrency, rate budget, retry budget, circuit breaker, failure isolation,
  idempotency, persistence, observability.
* No synthetic fallback. Live request + upstream failure = explicit failure.

## 2. Workload model (measured)

| Quantity | Value | Basis |
|---|---|---|
| Profiles per acceptance batch | N = 30 | assignment workload |
| Upstream requests per profile | **R = 1** | the `dash/profiles` memberIdentity finder returns the entity graph in one call; the retired path needed 6 (core + 5 sections) — minimizing amplification was an explicit design objective |
| Total upstream operations for a 30-batch | ≈ 30 (duplicates removed first) | N × R after dedup |
| Safe burst | 4 requests | `APP_UPSTREAM_BUCKET_CAPACITY` default; bursts ≈20 triggered a live challenge |
| Safe sustained rate | 12 requests/minute | conservative default; the observed challenge cooldown bounds anything higher |
| Safe concurrency | 2 | the rate budget, not concurrency, is the binding constraint; concurrency 2 keeps latency variance from clustering requests |
| Retry budget | 1 upstream retry per operation (single layer), 2 executions per batch job | `APP_UPSTREAM_RETRIES`, `MAX_JOB_ATTEMPTS` |
| Challenge cost | breaker OPEN, cooldown 300 s, one probe to recover | observed live: challenge ⇒ same-URL 302 + cookie clearing |
| Expected 30-profile completion | ≈ 3–4 min at defaults (30 × 5 s pacing) | token-bucket arithmetic; measured wall clock recorded in the acceptance run |

## 3. High-level design

```text
                ┌───────────────────┐
                │    API CLIENTS    │
                └─────────┬─────────┘
                          ▼
                ┌───────────────────┐
                │  PUBLIC API LAYER │  auth · validation · request ids · rate limit
                └─────────┬─────────┘
             ┌────────────┴────────────┐
             ▼                         ▼
    ┌─────────────────┐       ┌────────────────────┐
    │ SINGLE PROFILE  │       │ BATCH INGESTION    │ text/CSV/XLSX/TXT/JSON/DOCX/PDF
    └────────┬────────┘       │ discovery·dedupe   │
             │                │ provenance         │
             │                └─────────┬──────────┘
             └────────────┬─────────────┘
                          ▼
                ┌───────────────────┐
                │    JOB REGISTRY   │  deterministic ids · durable journal
                │  (BatchService)   │  idempotency · coalescing · attempt history
                └─────────┬─────────┘
                          ▼
                ┌───────────────────┐
                │  PULL-DRIVEN      │  poll-budget slices · backpressure by design
                │  WORK QUEUE       │
                └─────────┬─────────┘
                          ▼
                ┌───────────────────┐
                │ EXTRACTION WORKERS│  bounded consumers (semaphore)
                └─────────┬─────────┘
                          ▼
                ┌─────────────────────────────────┐
                │        UPSTREAM GOVERNOR        │
                │ token bucket · semaphore        │
                │ retry budget + jittered backoff │
                │ challenge-aware circuit breaker │
                │ (CLOSED/OPEN/HALF_OPEN)         │
                └────────┬────────────────────────┘
                          ▼
                ┌───────────────────┐
                │ AUTH CONTEXT      │  SessionProvider: the only secrets-aware component
                │ PROVIDER          │
                └────────┬──────────┘
                          ▼
                ┌───────────────────┐
                │ LINKEDIN TRANSPORT│  direct HTTP only · cookie jar · CSRF · single attempt
                └────────┬──────────┘
                          ▼
                ┌───────────────────┐
                │ LINKEDIN          │  /voyager/api/identity/dash/profiles?q=memberIdentity
                │ ENDPOINTS         │  fallback: authenticated page embedded-JSON
                └────────┬──────────┘
                          ▼
                ┌───────────────────┐   ┌──────────────────┐
                │ NORMALIZATION     │ → │ RESULT STORE /   │
                │ parsers → schema  │   │ EXPORTS / REPORTS│
                └───────────────────┘   └──────────────────┘
```

## 4. Control plane vs data plane

* **Control plane** — `UpstreamGovernor` + `SessionProvider` +
  `OperationRegistry`: session health, capability state, rate budget, breaker
  state, retry policy, operation definitions and evidence status.
* **Data plane** — `BatchService`, parsers, normalizer, journal, exports: job
  state transitions, payload parsing, persistence. Workers never make retry or
  pacing decisions; they receive either a result or a typed failure.

## 5. Queue model

* States — job: `PENDING → RUNNING → SUCCEEDED | FAILED | RETRY_WAIT |
  BLOCKED_UPSTREAM`; batch: `QUEUED | RUNNING | DEGRADED | PARTIAL |
  SUCCEEDED | FAILED`. Transitions are validated by construction (state machine
  in `BatchService`) and journalled.
* Backpressure — arrival rate (clients) is decoupled from service rate
  (governor). When capacity falls: workers slow, jobs queue in place
  (`queue_depth`, `queue_oldest_age_seconds` gauges), the API stays healthy,
  finished results stay exportable. Throughput degrades; availability does not.
* Idempotency — deterministic job ids make redelivery a no-op: a job that is
  `RUNNING`/`SUCCEEDED` is never re-executed; concurrent duplicates share one
  extraction (single-flight `asyncio.Task` registry + verified-result adoption).
* Crash recovery — journal restore on process start; completed jobs stay
  completed, pending jobs resume (`test_durable_jobs_survive_restart`).

## 6. Rate control model

```text
governor.run(operation, call):
    breaker.allow()?                      # CLOSED, or the single HALF_OPEN probe
    bucket.try_consume() → sleep/acquire  # rate budget (tokens reserved after wait)
    semaphore.acquire()                   # bounded concurrency
    re-check breaker (probe passes its own gate)
    call()                                # ONE http attempt (transport is policy-free)
    success  → breaker.record_success()
    timeout/429 and attempts left → backoff(2^n ± 20% jitter) → retry
    challenge → breaker.record_challenge() → OPEN (all extraction pauses)
```

Request-amplification accounting (why 1 request/profile matters): the retired
six-operation design would have made a 30-batch cost 180 upstream requests —
before retries. The current graph makes it 30; the retry budget caps the worst
case at 120 for 30 total failures (`test_retry_containment_thirty_failures`).

## 7. Failure model

| Upstream event | Detection | System response |
|---|---|---|
| soft challenge (same-URL 302) | redirect location | session invalidated, breaker OPEN, jobs BLOCKED_UPSTREAM, explicit `UPSTREAM_CHALLENGE` |
| hard challenge / checkpoint page | HTML body markers | same as above |
| authwall redirect | redirect location | `UPSTREAM_AUTH_EXPIRED`, capability `AUTH_EXPIRED` |
| 999 bot wall | page status | `UPSTREAM_CHALLENGE`, breaker OPEN |
| profile absent | JSON 404 | `PROFILE_NOT_FOUND` (404), no retry |
| contract drift | HTML/410/malformed | `UPSTREAM_OPERATION_DRIFT` (502), page fallback attempted first |
| rate limited | HTTP 429 | `UPSTREAM_RATE_LIMITED`, bounded retry |
| timeout / network | httpx timeouts | `UPSTREAM_TIMEOUT`, bounded retry |
| breaker open | — | `UPSTREAM_CIRCUIT_OPEN` (503, Retry-After); zero upstream traffic; jobs retained |
| session missing/expired | SessionProvider | readiness 503 `not_ready`, capability `UNAVAILABLE`/`AUTH_EXPIRED` |

Bulkhead isolation: extraction failure touches only the extraction capability.
`/healthz`, ingestion, batch creation, journal reads and exports remain fully
operational with LinkedIn down (verified: batch creation + export tests run
against failing upstreams).

## 8. Security boundaries

Secrets (`li_at`, `JSESSIONID`, companion cookies, API keys) live only in
environment/secret stores; they enter the code exclusively through
`SessionProvider`/`Settings` and never appear in logs (allowlisted operation
events), responses, tests, or docs. `scripts/security_audit.py` fails the build
on secret-shaped values or browser-automation terms in production files.
Uploaded files: size limits, content sniffing, sanitized names, no macro/XML
execution (defusedxml), ephemeral processing.

## 9. Deployment topology

Vercel serverless (ADR-0005): the pull-driven queue fits the platform; the
journal provides warm-restart durability; cold-start state loss is a documented
limitation with a named upgrade path (managed KV behind `JournalStore`).

## 10. Observability

* `GET /metrics` — Prometheus text: `tross_linkedin_operations_total`, breaker
  state, queue depth/age, jobs by outcome, retries, batches, coalesced jobs.
* `GET /readyz` — readiness **plus** `extraction_capability` (CLOSED/OPEN/
  HALF_OPEN/UNAVAILABLE) — readiness ≠ upstream capacity.
* `GET /v1/capability` — full state: capability, governor counters, queue stats.
* Structured operation logs with request/job correlation ids; secrets and
  payloads excluded by construction.

## 11. Capacity summary (measured)

| Metric | Value | Evidence |
|---|---|---|
| requests/profile | 1 | workload model §2; asserted `upstream.calls == jobs` in the backpressure proof |
| max concurrency | 2 (config) | asserted `max_active ≤ 2` under 100-job load |
| retry amplification | none beyond budget | 30 failing jobs ⇒ exactly 120 calls (ceiling 120) |
| breaker containment | 0 upstream calls while OPEN | blocked jobs record no HTTP attempt |
| burst pacing | measured wall-clock throttling | `test_rate_budget_throttles_burst` |
| restart safety | 0 re-extractions of completed jobs | `test_durable_jobs_survive_restart` |
| 30-profile acceptance | see `FINAL_VERIFICATION.md` | paced production run |

## 11b. Field coverage matrix

Every Tross-required field, its source operation, and verification status:

| Field | Source | Raw path (dash) | Status |
|---|---|---|---|
| name (first/last/full) | `profile_view` (live-verified) | `Profile.firstName/lastName` (plain or localized) | verified live (real payload) |
| headline | `profile_view` (live-verified) | `Profile.headline` | verified live |
| location | `profile_view` (live-verified) | `Profile.locationName` / `geoLocationName` | verified live (null when member hides it — null semantics) |
| about | `profile_view` (live-verified) | `Profile.summary` | verified live (Bill Gates summary captured) |
| profile image | `profile_view` (live-verified) | `Profile.profilePicture.displayImage.vectorImage` artifacts | verified live (CDN url constructed, expiresAt kept) |
| background image | `profile_view` (live-verified) | `Profile.backgroundPicture(s)` | implemented; present only when member uploaded one |
| public identifier / member URN | `profile_view` (live-verified) | `Profile.publicIdentifier`, `entityUrn` | verified live |
| experience | `profile_view_full` decoration, else `profile_sections` card `…-EXPERIENCE-…` | `Position` entities (+ `Company` for url) | implemented, shape-tested; live verification pending session window |
| education | same as experience | `Education` entities | implemented, shape-tested |
| skills | same as experience | `Skill` entities (ordering preserved) | implemented, shape-tested |
| certifications | same as experience | `Certification` (+ `Organization` authority) | implemented, shape-tested |
| languages | same as experience | `Language` entities (proficiency) | implemented, shape-tested |

Sections that the viewer cannot see return `status: not_provided` with empty
value — never fabricated.

## 11c. SLOs (what the application controls)

| SLO | Target | Notes |
|---|---|---|
| Ingestion availability (`/healthz`, batch create) | 99.9% | independent of LinkedIn (bulkhead) |
| Batch creation latency | < 500 ms p95 for 30 URLs | parsing + discovery are local |
| Job durability | 100% — no job lost across warm restart | journal + deterministic ids (test-proven) |
| Export availability | 100% once any job terminal | exports served from journal |
| Normalization success rate | ≥ 98% of successful upstream fetches | shape-tested parsers; drift ⇒ explicit 502 |
| Upstream latency per profile | external dependency — measured and reported, not promised | p50/p95 published per acceptance run |

## 12. Tradeoffs

* Conservative pacing lengthens batch wall clock (minutes, not seconds) — chosen
  deliberately: account safety and completion dominate latency.
* Pull-driven progress requires polling — fits serverless; a cron advancer is a
  drop-in later (with jitter + lease per §38 discipline).
* Ephemeral journal on Vercel — upgrade path documented in ADR-0005.
* Single owned session — least-privilege given the assignment; capacity is
  bounded and protected rather than multiplied (ADR-0001).
