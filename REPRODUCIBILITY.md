# Reproducibility

## Locked environment

`uv.lock` resolves Python 3.12 dependencies. CI uses `uv sync --extra dev --locked`, Ruff, strict mypy, pytest, the security audit, and the independent fixture benchmark. No LinkedIn secret is needed for CI.

## Clean-room procedure

```bash
git clone https://github.com/Shoryamishra61/tross-linkedin-profile-api.git clean-room
cd clean-room
uv sync --extra dev --locked --python 3.12
uv run ruff check src tests scripts
uv run mypy
uv run pytest
uv run python scripts/security_audit.py
uv run tross-benchmark --json --iterations 10
uv run pip-audit
docker build -t tross-linkedin-profile-api:local .
```

Local API:

```bash
export APP_API_KEYS=replace-with-a-new-random-key
export APP_MODE=fixture
uv run uvicorn tross_linkedin_api.main:app --host 127.0.0.1 --port 8000
```

Then check `/healthz`, `/readyz`, `/openapi.json`, missing/invalid auth, invalid URL, and an authenticated synthetic profile call. Fixture output is deterministic except observation time and measured local durations.

## Independence check

`tests/fixtures/raw/*.json` are synthetic upstream-shaped inputs. `tests/fixtures/expected/synthetic-profile.expected.json` is a separately checked-in semantic answer key. `benchmark.py` parses the actual pipeline response and compares it to that file. It never writes system output into expected data.

## Archive integrity

`11_ARCHIVE_ORIGINALS/` is excluded from lint/runtime and preserved as supplied. Representative SHA-256 values remained equal to `PACKAGE_MANIFEST.json` during the build audit.

