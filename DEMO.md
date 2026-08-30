# Demo

## Local fixture demo

PowerShell:

```powershell
$env:APP_API_KEYS = "local-demo-key-change-me"
$env:APP_MODE = "fixture"
uv run uvicorn profile_refinery_api.main:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/healthz
Invoke-RestMethod http://127.0.0.1:8000/readyz
$headers = @{ "X-API-Key" = "local-demo-key-change-me" }
$url = [uri]::EscapeDataString("https://www.linkedin.com/in/synthetic-profile")
Invoke-RestMethod -Headers $headers "http://127.0.0.1:8000/v1/profiles?url=$url"
```

Show `meta.operations_succeeded`, `meta.upstream_calls`, every required section, provenance, and the `FIXTURE_VERIFIED` registry status. State clearly that this is a synthetic parser/system demo.

## Failure demo

Run the partial integration test:

```bash
uv run pytest tests/integration/test_partial_and_limits.py -vv
```

It forces skills to time out while core and other sections survive. The response remains 200, sets `partial=true`, and marks skills `upstream_failed`.

Then run:

```bash
uv run python scripts/security_audit.py
uv run profile-refinery-benchmark --json --iterations 10
```

Explain that all metrics are fixture-only. A live/public demo must not be presented until `JUDGE_AUDIT.md` live and deployment gates change from BLOCKED to PASS with executable evidence.
