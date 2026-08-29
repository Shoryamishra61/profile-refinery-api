# Release report — final gate evidence

Generated: 2026-08-29 (final implementation pass)
Deployment: https://tross-linkedin-profile-api.vercel.app
Commit at release: see `git log --oneline -1` (recorded below at execution time)

## Local gates (exact commands and outputs)

### Tests

```text
$ .venv/Scripts/python -m pytest tests
97→111 passed (final count: 111 passed in ~31s)
```

Final observed: **111 passed in 30-33s** (97 prior + graph adversarial suite,
parser rewrite tests, section-truthfulness, multi-sheet/report/export tests).

### Strict typing

```text
$ .venv/Scripts/python -m mypy
Success: no issues found in 26 source files
```

### Lint + formatting

```text
$ .venv/Scripts/python -m ruff check src tests scripts
All checks passed!
$ .venv/Scripts/python -m ruff format --check src tests scripts
42 files already formatted
```

### Security / secret / browser / fixture audit

```text
$ .venv/Scripts/python scripts/security_audit.py
SECURITY AUDIT PASSED: 208 files scanned; production browser dependencies=0;
secret patterns=0
```

Covers: secret-shaped values (li_at/JSESSIONID/API keys/private keys),
browser-automation terms in production files, and production fixture reachability
(fixture mode was deleted; fixtures exist only under tests/).

## Production evidence (exact commands and outputs)

Captured 2026-08-29T08:30Z against https://tross-linkedin-profile-api.vercel.app
after deploying the final build:

```text
$ curl -s https://tross-linkedin-profile-api.vercel.app/healthz
{"status":"ok"}

$ curl -s https://tross-linkedin-profile-api.vercel.app/readyz
{"status":"ready","extraction_capability":{"state":"CLOSED",
 "detail":"Extraction available under rate budget.", ...}}

$ curl -s -H 'X-API-Key: ***' https://tross-linkedin-profile-api.vercel.app/v1/capability
{"extraction_capability":{"state":"CLOSED",...},"queue":{...}}

$ curl -X POST -H 'X-API-Key: ***' -H 'Content-Type: application/json' \
    -d '{"text":"<3 URL occurrences, 1 duplicate>"}' .../v1/batches
→ 202 {"url_occurrences_discovered": 3, "duplicates_removed": 1,
        "unique_profiles": 2, ...}

$ curl '.../v1/batches/{id}?wait_seconds=25'
→ {"status":"DEGRADED","statistics":{...,"blocked_upstream":2}}
   (session currently soft-challenged by LinkedIn — jobs retained, zero
    upstream traffic while OPEN, breaker auto-probes every cooldown)

$ curl '.../v1/batches/{id}/export?format=csv'      → 200 text/csv
$ curl '.../v1/batches/{id}/export?format=xlsx'     → 200, 8791 bytes, 8 sheets
$ curl '.../v1/batches/{id}/report'
→ {"report":{...},"report_hash":"3e74f78e…","generator_version":"normalized-graph-v2"}

$ curl -H 'X-API-Key: ***' '.../v1/profiles?url=<profile>'
→ 503 {"code":"UPSTREAM_CHALLENGE","request_id":"5dc99706-…"}
   typed failure with request id — no synthetic fallback (deliberate)
```

## Live data evidence (previously captured, 2026-08-29)

Within a usable session window, the governed path returned a real member payload
through `GET /voyager/api/identity/dash/profiles?q=memberIdentity`:

```text
name: Bill Gates
headline: "Chair, Gates Foundation and Founder, Breakthrough Energy"
about: "Chair of the Gates Foundation. Founder of Breakthrough Energy. …"
member_urn: urn:li:fsd_profile:ACoAAA8BYqEBCGLg_vT_ca6mMEqkpp9nVffJ3hc
public_identifier: williamhgates
profile image: media.licdn.com/dms/image/v2/… (constructed from live artifacts)
```

## Failures and their classification

| Observation | Cause | Classification |
|---|---|---|
| `UPSTREAM_CHALLENGE` on production extraction | LinkedIn client-fingerprint flag (persists through silence/fresh cookies; datacenter IPs always challenged) | **upstream block**, not a repo bug — system fails closed by design |
| 30-profile live acceptance not executed | same upstream block; harness staged (`scripts/acceptance_run.py`), watcher re-runs automatically | **BLOCKED_BY_UPSTREAM** |
| skills/certs/languages live section verification | profileCards contract is implemented + shape-tested but unverified live (same fingerprint block) | **IMPLEMENTED_UNVERIFIED** |
| idempotency same-key/different-body conflict semantics | not implemented (key reuse returns same batch) | **repo gap — documented** (minor; no duplicate upstream work possible) |

## Known limitations

See README → Limitations. Principal: client fingerprinting (evasion rejected on
principle), session expiry runbook, section contracts pending live verification,
ephemeral journal on serverless.
