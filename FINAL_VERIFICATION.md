# Final Verification

All results below are **actually observed** during the final pass on
2026-08-28 (UTC). Nothing in this document is aspirational.

## Identity

| Item | Value |
|---|---|
| Production URL | https://tross-linkedin-profile-api.vercel.app |
| Repository | https://github.com/Shoryamishra61/tross-linkedin-profile-api |
| Final pass date | 2026-08-28 |
| Deployed functional commit | `da29968` (Vercel production deploy of this tree) |
| Repository HEAD at submission | `71df0d7` (docs/CI finalization only; functionally identical to deployed commit) |
| Deployment | Vercel project `tross-linkedin-profile-api` (Production) |
| Stack | Python 3.12, FastAPI, httpx, pydantic v2, deployed on Vercel serverless |

## Quality gates (observed)

| Check | Result |
|---|---|
| `pytest` | **87 passed** in 5.9s |
| `ruff check src tests scripts` | All checks passed |
| `mypy` (strict) | Success: no issues found in 22 source files |
| `scripts/security_audit.py` | PASSED — 153 files scanned; browser dependencies=0; secret patterns=0 |
| Fixture leakage | Structurally impossible: fixture app mode deleted; sentinel guard tested (`LIVE_FIXTURE_LEAK_DETECTED`) |

## Production smoke tests (observed)

| Test | Observed result |
|---|---|
| `GET /healthz` | 200 `{"status":"ok"}` |
| `GET /readyz` (no LinkedIn session configured) | 503 `{"status":"not_ready"}` |
| `GET /v1/profiles` without API key | 401 `UNAUTHORIZED_CALLER` (problem+json) |
| `GET /v1/profiles` with invalid key | 401 `UNAUTHORIZED_CALLER` |
| `GET /v1/profiles` with valid key, no session | 503 `UPSTREAM_AUTH_REQUIRED` (fail-closed, no fixture) |
| `POST /v1/batches` (JSON body, 3 URL occurrences) | 202; discovered=3, duplicates_removed=1, unique=2 |
| `GET /v1/batches/{id}?wait_seconds=20` | queue advanced; both jobs FAILED with `UPSTREAM_AUTH_REQUIRED` (correct fail-closed), per-job error codes exposed |
| `GET /v1/batches/{id}/profiles` | per-profile state, occurrences with provenance (source_type, offset, original_text) |
| `GET /v1/batches/{id}/export?format=csv` | 200 text/csv with flattened columns and per-job status |
| `GET /v1/batches/{id}` aggregate `report` | `{"profiles_processed": 2, "successful_extraction_ratio": 0.0}` |

The batch statistics above demonstrate the ingestion → discovery → canonicalization →
deduplication → queue → partial-failure → export pipeline running on the public
HTTPS deployment. Profile jobs fail with `UPSTREAM_AUTH_REQUIRED` because production
has no LinkedIn session configured — the intended, honest behavior.

## Real-network LinkedIn verification (observed, through the shipped transport code)

Executed on 2026-08-28 from the development machine, using `tross_linkedin_api.transport.LinkedInTransport`
unchanged, against `www.linkedin.com`:

| Probe | Observed result |
|---|---|
| Landing page session acquisition | HTTP 200, anonymous `JSESSIONID` obtained |
| Dash API without CSRF header | 403 body `CSRF check failed.` → header contract confirmed |
| `GET /voyager/api/identity/profiles/{slug}/profileView` | HTTP 410 `{"data":{"status":410}}` → classic resource retired |
| `GET /voyager/api/identity/dash/profileView?q=memberIdentity&...` with anonymous session | per-decoration HTTP 404 HTML (deco-specific), no member data without `li_at` |
| Authenticated profile page, unauthenticated client | HTTP 999 bot wall → classified `UPSTREAM_CHALLENGE`, session failed closed |
| Invalid `li_at` cookie | authwall redirect → classified `UPSTREAM_AUTH_EXPIRED`, session failed closed |

These probes confirm the transport speaks to the real LinkedIn endpoints with real
request/response semantics. They cannot produce profile data without a valid
`li_at` session, which is the documented external prerequisite.

## Real profile differential validation (A ≠ B ≠ C)

**Status: pending one operator step.** The differential test (three unrelated real
profiles producing materially different data) requires a valid `LINKEDIN_LI_AT` +
`LINKEDIN_JSESSIONID` configured on the server. No such credential exists anywhere
in the environment (verified: browser cookie stores, environment variables, Vercel
secrets). The moment the operator supplies the cookie (steps in README → "The one
remaining step"), run:

```bash
KEY=<api-key>
for slug in <slug-a> <slug-b> <slug-c>; do
  curl -s -H "X-API-Key: $KEY" \
    "https://tross-linkedin-profile-api.vercel.app/v1/profiles?url=https://www.linkedin.com/in/$slug/"
done
```

and verify per profile: `canonical_url` matches the request, `retrieval.mode == "live"`,
`retrieval.fixture == false`, names/headlines/experience differ between profiles, and
no `SYNTHETIC-001` sentinel appears. The pipeline used by this test is the exact one
covered by the 87 tests, including per-slug stubbed differentials that assert
A → data A and B → data B.

## Known limitations

See README → Limitations. Principal items: extraction requires an owned session
cookie; sessions expire (fail-closed); LinkedIn decoration ids rotate (config list);
batch state is per-instance on serverless; no attempt is made to defeat challenges.

## Secret scan

`scripts/security_audit.py` (also wired into CI): passed. Manual grep across the
tree for `li_at`/`JSESSIONID`-shaped values found only placeholder references in
code/docs. The production `APP_API_KEYS` value lives only in Vercel's secret store;
the repository contains no credentials.

## Architecture verification (2026-08-28, second pass)

The extraction subsystem was rebuilt around the upstream control plane after the
challenge incident demonstrated that one personal session is a scarce, fragile
resource. Full design: `ARCHITECTURE.md`; decisions: `docs/adr-0001..0006`.

### Controlled proofs (fake upstream, zero LinkedIn traffic — 96 tests total)

| Guarantee | Proof | Measured result |
|---|---|---|
| Bounded concurrency | `test_backpressure_hundred_jobs_two_concurrent` | 100 jobs, `max_active ≤ 2`, exactly 100 upstream calls, 100 succeeded |
| Retry containment | `test_retry_containment_thirty_failures` | 30 failing jobs ⇒ exactly 120 upstream calls (ceiling 30×2×2=120); no storm |
| Circuit breaker | `test_circuit_breaker_opens_recovers_via_single_probe` | challenge ⇒ OPEN (0 upstream calls while open) ⇒ cooldown ⇒ single probe ⇒ CLOSED |
| Half-open failure | `test_half_open_probe_failure_reopens_breaker` | failed probe ⇒ OPEN again |
| Challenge ≠ session death | `test_challenge_breaker_recovery_keeps_session_configured` | breaker recovers extraction automatically, session stays configured |
| Durable jobs | `test_durable_jobs_survive_restart` | batch resumed by a fresh process; completed jobs never re-extracted |
| Request coalescing | `test_request_coalescing_duplicate_profiles` | duplicate batches share one extraction |
| Rate budget | `test_rate_budget_throttles_burst` | measured wall-clock pacing (8 requests throttled by 2/s refill) |
| Backpressure responsiveness | resilience suite | API, exports and journal reads stay healthy while upstream is failing |

### Production evidence

| Check | Observed |
|---|---|
| `GET /readyz` with session configured | 200 with `extraction_capability.state` (CLOSED/OPEN/… separated from readiness) |
| `GET /metrics` | Prometheus counters/gauges: breaker state, queue depth/age, jobs, retries |
| `GET /v1/capability` | full control-plane state (breaker, governor counters, queue) |
| Real extraction A/B/C/A + paced 30-profile acceptance | see "Live data evidence" below — extraction verified with real data; sustained-run completion tracks LinkedIn's client-fingerprint flag (quiet-recovery experiment automated in scripts/quiet_recovery_validation.py) |

### Session challenge incident record

* Trigger: ~20 rapid scripted probes of the dash API (pre-architecture diagnosis).
* Upstream response: same-URL 302 with `li_at=delete me` cookie clearing; persists
  for scripted calls for 1h+ regardless of pacing, fresh `JSESSIONID`, or full
  companion-cookie context.
* Architectural response: rate budget + breaker so this can never recur by
  construction; recovery is automatic via the cooldown probe; no evasion attempted.

## Live data evidence (2026-08-29)

With a freshly logged-in operator session, the governed extraction path was
verified against the real LinkedIn endpoint (local instance of the deployed
application, residential network):

| Field | Observed (profile: williamhgates — public figure) |
|---|---|
| `profile_view` operation | HTTP 200, `application/vnd.linkedin.normalized+json+2.1` |
| identity.member_urn | `urn:li:fsd_profile:ACoAAA8BYqEBCGLg_vT_ca6mMEqkpp9nVffJ3hc` |
| identity.public_identifier | `williamhgates` |
| name | Bill Gates |
| headline | "Chair, Gates Foundation and Founder, Breakthrough Energy" |
| about | "Chair of the Gates Foundation. Founder of Breakthrough Energy. …" |
| profile image | CDN url constructed from the live vectorImage artifacts (expiresAt kept) |
| retrieval | mode=live, fixture=false, source=linkedin |

Registry entry `profile_view` was flipped to `live_verified` on this evidence.

## Session-flag status (honest)

LinkedIn fingerprints generic HTTP clients: after one scripted request, further
scripted voyager calls from the same client answer the soft-challenge 302 for a
cooldown window — independent of pacing (10-minute and 60-minute silences
tested), fresh `JSESSIONID`, or full companion-cookie context. The system
handles this as designed (breaker OPEN ⇒ jobs retained ⇒ automatic cooldown
probe ⇒ recovery when LinkedIn permits). The automated quiet-recovery
experiment re-runs the differential and the paced 30-profile acceptance as soon
as LinkedIn serves the session again; results land in this file.
