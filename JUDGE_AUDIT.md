# Adversarial Judge Audit

Audit updated: 2026-08-28. Overall challenge verdict: **PARTIAL / externally blocked**, not PASS.

The repository is a reproducible, secured, no-browser implementation with honest fixture evidence. A public Vercel service now exists in fail-closed live mode. It is not yet a completed live Tross submission because no current LinkedIn operation/session evidence is available and live profile requests correctly return 503.

## Definition of Done

| Gate | Status | Executable evidence |
|---|---|---|
| Fresh clone installs; locked package; no path hacks | PASS | clean clone passed sync; current suite has 57 tests |
| Fixtures, schema, registry shipped | PASS | `tests/fixtures`, `schemas`, `config`; startup tests |
| Direct LinkedIn HTTP runtime | PASS as implementation; BLOCKED as live observation | `transport.py`; mocked direct transport contract tests; no live call |
| No browser/DOM runtime | PASS | `uv run python scripts/security_audit.py` |
| URL to current live core fields | BLOCKED | no session/capture/query ID; registry rejects live startup |
| Experience/education/skills/certifications/languages live | BLOCKED | required current operation evidence absent |
| Profile image live | BLOCKED | current core response absent |
| Partial response behavior | PASS (`FIXTURE_VERIFIED`) | `test_optional_failure_returns_200_partial` |
| Independent fixture benchmark | PASS | `uv run tross-benchmark --json --iterations 10`; independent expected file |
| Independent controlled-live benchmark with n | BLOCKED | no consented live profile set or operation |
| No circular ground truth | PASS | benchmark loads checked-in expected file; source review/tests |
| Schema fail closed | PASS | `test_schema_missing_fails_closed` |
| Operation drift controlled | PASS | parser/transport drift tests |
| No secrets in Git/logs | PASS for automated patterns/allowlist tests | security script plus logging test; Git history scan at release |
| API key required | PASS | missing/invalid integration tests and OpenAPI security scheme |
| Fixed outbound host; SSRF/redirect tests | PASS | canonicalizer and transport contract tests |
| Challenge fail closed | PASS as contract test | 403 and checkpoint handling; no live challenge claim |
| Public HTTPS URL/evaluator request/restart | PARTIAL | Vercel URL, health, readiness, auth, and fail-closed profile path exercised; real extraction unavailable |
| Health/readiness/OpenAPI/local evaluator call | PASS locally | API integration and process smoke test |
| README and required technical documents | PASS | research README; 56 maintained Markdown files lint clean; 57 local links resolve |
| Docker image builds and serves API | PASS | image manifest `sha256:76f1e36d...`; container returned health and six-operation fixture profile |
| Public GitHub repository | PARTIAL | cleaned public release `8d916ab`; active workflow is mirrored as `.example` due OAuth scope |

## Critical legacy defects

| # | Legacy defect | Disposition | Evidence |
|---:|---|---|---|
| 1 | README referenced unshipped files | FIXED + TESTED | README commands/files checked in; clean-room procedure |
| 2 | GraphQL call had no registered payload | FIXED + TESTED as transport contract | registry supplies operation/query env; transport sends `queryId` and variables; live evidence still blocked |
| 3 | Full-history pagination existed only in prose | NOT APPLICABLE + EVIDENCE | no pagination claim/code until a current response proves semantics; limitations/assumption A-04 |
| 4 | Benchmark copied output to ground truth | FIXED + TESTED | independent expected JSON; no assignment from actual to expected |
| 5 | Fixture latency called live | FIXED | results/benchmark label `FIXTURE_VERIFIED` and `live_extraction_claim=false` |
| 6 | Request count was not instrumented | FIXED + TESTED | transport increments calls and response reports six fixture operations |
| 7 | Missing schema failed open | FIXED + TESTED | startup raises; unit regression |
| 8 | Missing API key was allowed | FIXED + TESTED | 401 tests/security scheme |
| 9 | Mock generated email from slug | FIXED + TESTED | no contact/email model or generation; source scan |
| 10 | Fake built-in session credentials | FIXED + TESTED | live settings require environment secrets; validation test |
| 11 | Docs claimed curl_cffi/JA4 while code used HTTPX | FIXED | docs and manifest say HTTPX; no fingerprint claim |
| 12 | Anti-abuse thresholds were speculative | FIXED | only configurable caller limit is described; no LinkedIn safety threshold |
| 13 | Endpoint matrix mixed historical/current | FIXED | historical matrix stays reference/archive; runtime uses evidence-gated registry |
| 14 | Query IDs treated as permanent | FIXED + TESTED | registry names environment values and carries observation metadata |
| 15 | Missing fields overclassified as hidden | FIXED + TESTED | no normalizer path emits viewer-hidden without evidence |

## External blockers with evidence

1. Environment contained no `LINKEDIN_*`, `LI_AT`, `JSESSIONID`, or current query-ID variables. No authorized capture/profile matrix was supplied. Attempting guessed historical endpoints would violate project evidence policy.
2. Vercel device authentication was completed and the service deployed at `https://tross-linkedin-profile-api.vercel.app`; hosting access is no longer a blocker.
3. GitHub repository publication succeeded, but the OAuth token lacked `workflow` scope. GitHub rejected `.github/workflows/ci.yml`; no SSH key or connected browser was available to approve the device grant.
4. Docker Desktop was initially stopped; it was started and the build/container smoke gate subsequently passed.
5. Production now starts in degraded `APP_MODE=live`, reports readiness 503, and returns `UPSTREAM_OPERATION_UNAVAILABLE` for profile requests. All checked-in operations remain fixture-verified rather than live-verified.
6. Direct HTTP requests to the requested Shorya profile plus Satya Nadella and Bill Gates returned LinkedIn 429 responses without profile-specific content. No owned session, current query identifiers, authorized capture, or consented differential ground truth is present.

## Release decision

Offline/repository release: **PASS** after final clean-room, dependency, process, Git, and publication checks.

Tross live assignment: **NOT PASS** until one owned-session core operation and required sections are independently verified, a controlled-live benchmark is run, and a public HTTPS deployment is externally exercised.
