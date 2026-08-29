# Baseline — final audit phase

recorded: 2026-08-29 (session start of the final implementation push)

```text
commit: ffbf5b0 (main, tagged final-audit-baseline)
branch: main
dirty: false
tests: 97 passed in 31.89s
typing: mypy strict — Success: no issues found in 25 source files
lint: ruff — All checks passed
security: scripts/security_audit.py — PASSED (218 files, browser deps=0, secrets=0)
secret scan: PASSED (same audit; no li_at/JSESSIONID/API-key shaped values)
browser audit: PASSED (production browser dependencies = 0)
fixture audit: no fixture mode exists in src; fixtures reachable only from tests
public deployment: https://tross-linkedin-profile-api.vercel.app (Vercel, APP_MODE=live)
healthz: {"status":"ok"}
readyz: 200 {"status":"ready", "extraction_capability": {...}}
capability: GET /v1/capability (auth'd) — breaker/queue/governor state
profile route: GET /v1/profiles?url=<linkedin_profile_url> (+ X-API-Key)
current core contract: GET /voyager/api/identity/dash/profiles?q=memberIdentity
                      (registry: profile_view, evidence_status=live_verified,
                       live-verified 2026-08-29 against a real member payload)
currently verified live fields: name, headline, about(summary), member URN,
                      public identifier, profile image URL (+expiresAt),
                      background image (same shape when present)
known live blocker: LinkedIn client-fingerprint flag — after ~1 scripted request
                      per fresh session, voyager calls answer the soft-challenge
                      302 regardless of pacing/silence/cookie context; system
                      fails closed (UPSTREAM_CHALLENGE / breaker OPEN, cooldown
                      probe). No evasion implemented (deliberate).
```

## Known gaps against the governing specification

| Spec item | Current state | Classification |
|---|---|---|
| §7 NormalizedGraph target-URN ownership | parsers use global `$type` scans (the explicitly forbidden pattern) — foreign Profile/Position in `included[]` would be mixed in | **P0 MUST FIX** |
| P0.3 first/last/full name | only full name exposed | **P0 MUST FIX** |
| P0.4 empty vs unavailable sections | section-fetch failure currently indistinguishable from observed-empty | **P0 MUST FIX** |
| §6 per-section contracts (profile_skills/certifications/languages) | generic `profile_sections` op, no per-section expected types | **P0** |
| §10.8 multi-sheet XLSX | single sheet | P1 |
| §11 `GET /v1/batches/{id}/report` | report embedded in batch summary only | P1 |
| §10.9 report determinism/hash | deterministic content, no hash exposed | P1 |
| §12 coverage metadata | warnings + partial flag only | P0 (with section truthfulness) |
