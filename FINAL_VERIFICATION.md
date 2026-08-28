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
