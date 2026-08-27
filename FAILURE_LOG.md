# Failure Log

## 2026-08-27

| ID | Observation | Root cause | Repair/evidence | Final state |
|---|---|---|---|---|
| F-001 | Ruff reported hundreds of archive findings | Immutable legacy prototype was inside default lint traversal | Limited production lint to `src tests scripts`; archive remains preserved and excluded | FIXED |
| F-002 | App startup could not parse comma-separated `APP_API_KEYS` | Settings source attempted JSON decoding before validation | Added `NoDecode` plus an explicit splitter | FIXED + tested |
| F-003 | mypy could not inspect package/stubbed libraries | Missing `py.typed`, JSON Schema, and YAML stubs | Added marker and dev stubs; strict mypy passes | FIXED |
| F-004 | Unicode compatibility hostname was accepted | NFKC/IDNA collapsed a non-ASCII dot to ASCII | Reject non-ASCII/compatibility-transformed hosts before allowlist comparison | FIXED + regression test |
| F-005 | Locally scoped API-key security dependency broke OpenAPI and injected no value | Postponed annotation could not resolve closure-local dependency | Promoted `APIKeyHeader` to module scope and used `Security` | FIXED + API/OpenAPI tests |
| F-006 | Security scan flagged a synthetic test cookie | Test value matched the scanner's credential shape | Replaced it with a short non-secret fixture token; scanner still scans tests | FIXED |
| F-007 | Docker daemon connection failed | Docker Desktop Linux engine pipe did not exist | Started Docker Desktop, built the image, and exercised health/profile from the container | FIXED |
| F-008 | Railway/Fly/Wrangler/Zerops/Render CLIs unavailable | No configured deployment platform in environment | Added provider-neutral Dockerfile and Render Blueprint; do not fabricate URL | EXTERNAL |
| F-009 | Live operation work could not start | No owned LinkedIn session, authorized network capture, current identifiers, or ground-truth profiles | Completed all offline work; registry makes live enablement fail closed | EXTERNAL |
| F-010 | `pip-audit` reported `PYSEC-2026-1845` in pytest 8.4.2 | Original dev constraint excluded the fixed major release | Raised pytest floor to 9.0.3, relocked, and reran the suite/audit | FIXED |
| F-011 | GitHub rejected the active CI workflow on push | Authenticated OAuth token has `repo` but not `workflow`; SSH key and connected browser were unavailable | Published all source/tests/docs publicly with the workflow mirrored as `.example`; local main remains complete | EXTERNAL PERMISSION |
| F-012 | Maintained Markdown had 814 default-linter findings | The supplied corpus had no shared Markdown policy and used research tables, long source URLs, and compact generated prose | Added an explicit policy, auto-fixed safe spacing/EOF issues, and reran lint across 56 maintained files | FIXED |

No checkpoint was triggered because no live LinkedIn request was attempted.
