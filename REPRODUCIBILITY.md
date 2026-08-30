# Reproducibility

Python 3.12 dependencies are pinned by `uv.lock`. Deterministic verification needs no LinkedIn credentials and never performs a live upstream request.

```bash
git clone https://github.com/Shoryamishra61/profile-refinery-api.git
cd profile-refinery-api
uv sync --extra dev --locked --python 3.12
uv run ruff check src tests config scripts
uv run mypy src/profile_refinery_api
uv run pytest
uv run python scripts/security_audit.py
uv run pip-audit
docker build -t profile-refinery-api:local .
```

Start the API with `uv run uvicorn profile_refinery_api.main:app --host 127.0.0.1 --port 8000`. With no owned LinkedIn session configured, `/healthz` is healthy while `/readyz` and backend-session extraction fail closed. Deterministic tests use authored fixtures or redacted replay inputs and label that evidence separately from live observations.

Live verification is intentionally manual and controlled: configure secrets outside the repository, use one consented profile, make one bounded request, and record only safe counts and provenance. A passing replay or unit suite is not live-extraction evidence.
