# Tross LinkedIn Profile API

A research-grade FastAPI service that turns a validated LinkedIn member URL into a stable, provenance-carrying JSON profile. The runtime has no browser, DOM, screenshot, CAPTCHA, proxy-rotation, or fingerprint-spoofing path. All upstream calls are direct HTTP requests to a fixed LinkedIn origin and must come from an evidence-gated operation registry.

## Current status

The complete fixture/offline system is implemented and verified. The current registry entries are `FIXTURE_VERIFIED`, so live mode intentionally refuses to start. A current authorized network observation, direct replay, redacted fixture, and runtime secrets are still required before any operation can be relabeled `live_verified`. Public HTTPS deployment and controlled-live quality metrics therefore remain blocked; see [JUDGE_AUDIT.md](JUDGE_AUDIT.md).

The fixture API exercises name, headline, location, about, experience, education, skills, certifications, languages, media, provenance, partial results, request-count instrumentation, schema validation, and error behavior. It is not evidence that LinkedIn currently returns those fixture shapes.

## Architecture

```text
caller -> API-key/rate limit -> strict URL canonicalizer -> semantic operation registry
       -> fixture or direct-HTTP transport -> deterministic parsers -> normalizer
       -> partial-result engine -> Pydantic + JSON Schema 2020-12 -> response
```

Volatile paths and query identifiers never appear in business logic. Live session values are loaded only from runtime secrets. A 401/403 or recognized checkpoint makes the session unavailable until manual operator action.

## Fresh setup

Requirements: Git, [uv](https://docs.astral.sh/uv/), and Python 3.12+.

PowerShell:

```powershell
git clone https://github.com/Shoryamishra61/tross-linkedin-profile-api.git
Set-Location tross-linkedin-profile-api
uv sync --extra dev --locked --python 3.12
$env:APP_API_KEYS = uv run python -c "import secrets; print(secrets.token_urlsafe(32))"
$env:APP_MODE = "fixture"
uv run uvicorn tross_linkedin_api.main:app --host 127.0.0.1 --port 8000
```

Bash:

```bash
git clone https://github.com/Shoryamishra61/tross-linkedin-profile-api.git
cd tross-linkedin-profile-api
uv sync --extra dev --locked --python 3.12
export APP_API_KEYS="$(uv run python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export APP_MODE=fixture
uv run uvicorn tross_linkedin_api.main:app --host 127.0.0.1 --port 8000
```

In another shell, substitute the generated key:

```bash
curl http://127.0.0.1:8000/healthz
curl http://127.0.0.1:8000/readyz
curl -H "X-API-Key: YOUR_GENERATED_KEY" "http://127.0.0.1:8000/v1/profiles?url=https%3A%2F%2Fwww.linkedin.com%2Fin%2Fsynthetic-profile"
```

Interactive documentation is at `/docs`; OpenAPI 3.1 is at `/openapi.json`.

## Verification

```bash
uv run ruff check src tests scripts
uv run mypy
uv run pytest
uv run python scripts/security_audit.py
uv run tross-benchmark --json --iterations 10
uv run pip-audit
```

The expected benchmark output is independently authored in `tests/fixtures/expected/`; the evaluator never assigns extractor output to ground truth.

## Live-mode activation

Do not turn on live mode by copying historical routes. Follow [REVERSE_ENGINEERING_METHOD.md](REVERSE_ENGINEERING_METHOD.md) with an owned/authorized account, then for each operation:

1. capture only redacted request semantics;
2. replay the operation through direct HTTP without bypass behavior;
3. add the redacted fixture and parser contract tests;
4. set a current `observed_at`, evidence reference, and `live_verified` status;
5. inject `LINKEDIN_LI_AT`, `LINKEDIN_JSESSIONID`, and current query identifiers outside Git;
6. set `APP_MODE=live`.

The registry rejects fixture/historical operations in live mode and rejects enabled live GraphQL operations whose identifier environment value is missing.

## Documents

- [Architecture](ARCHITECTURE.md)
- [API reference](API_REFERENCE.md)
- [Reverse-engineering method](REVERSE_ENGINEERING_METHOD.md)
- [Results](RESULTS.md) and [limitations](LIMITATIONS.md)
- [Security](SECURITY.md) and [privacy/platform risk](PRIVACY_AND_PLATFORM_NOTES.md)
- [Reproducibility](REPRODUCIBILITY.md)
- [PhantomBuster comparison](PHANTOMBUSTER_COMPARISON.md)
- [Build log](BUILD_LOG.md), [failure log](FAILURE_LOG.md), and [assumptions](ASSUMPTION_REGISTER.md)
- [Judge audit](JUDGE_AUDIT.md) and [demo](DEMO.md)

Historical materials are preserved unchanged under `11_ARCHIVE_ORIGINALS/` and are not production truth.

