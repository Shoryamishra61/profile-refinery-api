# Build Log

## 2026-08-27

### Phase 0 — workspace audit

- Read all canonical documents and inspected reference data, templates, archived Python, schemas, manifests, and ZIP inventories.
- Found no Git repository, production package, fixtures, runtime secrets, live operation evidence, or deployment-provider environment variables.
- Verified representative archive SHA-256 values against `PACKAGE_MANIFEST.json`; archive remained unchanged.
- Confirmed Python 3.12 is available through uv, Git/GitHub CLI are installed, and GitHub is authenticated as `Shoryamishra61`.

### Phases 1–5 — reproducible security boundary

- Initialized Git and a Python 3.12 `src/` package with locked dependencies, Dockerfile, CI, `.env.example`, schemas, registry, and typed settings.
- Implemented strict startup, exact URL-to-slug canonicalization, API-key authentication, caller limiting, health/readiness, RFC 9457-compatible errors, fixed-origin HTTPX transport, environment-only session loading, bounded retries, streamed size limit, redirect refusal, structured allowlist logging, and challenge fail-closed behavior.
- Implemented fixture/live evidence gating. No fixture/historical record can start in live mode.

### Phases 6–10 — parser/orchestration work

- Live discovery could not begin: no authorized session/capture/current query IDs were present.
- Implemented deterministic parser contracts for core, experience, education, skills, certifications, languages, company reference resolution, localized text, dates, and media.
- Implemented core-first orchestration, bounded concurrent sections, measured call counts/timing, stable Pydantic models, JSON Schema 2020-12 validation, and typed partial responses.
- Did not implement pagination because no current response proved pagination semantics.

### Phases 11–13 — evaluation and security

- Replaced circular evaluation with independent raw and expected files.
- Added unit, contract, integration, and security tests covering URL attacks, auth, rate limit, schemas, registry evidence, parsers, partials, redirects, content types, malformed JSON, operation drift, and checkpoint handling.
- Ruff and strict mypy pass. Pytest passes. Security scan reports zero production browser dependencies and zero recognized secret patterns.
- Fixture benchmark is 4/4 primitives, 8/8 nested entries, 12/12 statuses, and 12/12 provenance fields. It makes no live claim.

### Phases 14–16 — release

- Added production container and Render Blueprint configuration with secret-store inputs.
- Docker Desktop was initially stopped. After one controlled startup, image build and container health/profile smoke tests passed. Deployment-provider access remained unavailable.
- Added architecture, API, method, results, limitations, security, privacy/platform, comparison, reproducibility, demo, logs, and adversarial audit documents.
- Created logical Git milestones for package, implementation, tests, documentation, and clean-room evidence.
- Published `https://github.com/Shoryamishra61/profile-refinery-api` as PUBLIC. The OAuth token lacked `workflow` scope, so the public fallback mirrors CI at `ci/github-actions-ci.yml.example`; local `main` retains the active `.github/workflows/ci.yml`.

### Public research-documentation release

- Reframed the README as a research artifact with an abstract, research question,
  contributions, evidence taxonomy, architecture, measured results, reproduction protocol,
  repository map, responsible-use boundary, and explicit blocked gates.
- Added MIT license and Citation File Format metadata.
- Added a project-owned Markdown policy and mechanically normalized all 56 maintained
  Markdown files; `11_ARCHIVE_ORIGINALS/` remained untouched.
- Verified zero Markdown lint findings, 57 local document links, citation parsing, Ruff,
  strict mypy, 54 tests, security audit, independent fixture benchmark, and dependency audit.
- Published the cleaned documentation tree at public commit `8d916ab`. GitHub reported no
  deployments; provider credential variables were absent; an `APP_MODE=live` preflight
  failed closed on the missing LinkedIn session secrets as designed.

### Production recovery — 2026-08-28

- Traced `/v1/profiles` through authentication, canonicalization, runtime selection,
  operation registry, transport, parsers, normalization, schema validation, and response.
- Confirmed the synthetic production response was caused by the explicit Vercel setting
  `APP_MODE=fixture`, not by a hidden live-to-fixture fallback.
- Added explicit retrieval provenance and a hard live sentinel guard for fixture-only IDs,
  companies, and institutions.
- Changed live startup to a safe degraded state when no live-verified core operation exists;
  readiness and profile requests now return explicit 503 behavior without invoking fixtures.
- Deployed Vercel production in live mode and verified health 200, readiness 503, missing
  caller key 401, malformed URL 400, and three unrelated real URLs 503 with zero sentinel leaks.
- Direct LinkedIn HTTP checks for those profiles returned 429 without profile-specific data;
  authenticated extraction remains blocked by absent owned-session/current-operation evidence.
