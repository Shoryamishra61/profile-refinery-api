# Security

## Implemented controls

- Exact ASCII host allowlist for `linkedin.com` and `www.linkedin.com`; HTTPS and port 443 only.
- Only `/in/{strict-slug}` is accepted. Credentials, fragments, decoded extra path segments, traversal, IP hosts, Unicode compatibility hosts, and overlong/control-character input are rejected.
- The submitted URL is never fetched. Outbound origin is a constant and paths come from the validated registry.
- `X-API-Key` is mandatory and compared in constant time. A local sliding-window limit returns 429 with `Retry-After`.
- Schema and registry are mandatory startup inputs; live startup requires non-empty LinkedIn session secrets and live-evidence operations.
- HTTP redirects are refused. Content type, JSON root, response status, and streamed byte ceiling are validated.
- Only bounded network/5xx retries occur. 401/403/checkpoint makes the session unavailable; no bypass is attempted.
- Logs contain an allowlisted operation event: request ID, semantic operation, duration, status, parser outcome, attempt. Cookies, headers, raw payloads, URLs, API keys, and authorization values are not event fields.
- `.env`, HAR, logs, caches, and generated result files are ignored. `.env.example` contains empty values.
- CI scans production source/manifests for browser dependencies and repository text for common secret patterns.

## Threat boundaries

The API is still an upstream-dependent service holding a privileged session. Deploy behind managed TLS, restrict provider log access, rotate caller/session secrets, set ingress request/time limits, and avoid persistent profile storage. The single-process rate limiter is not a distributed abuse control.

Run:

```bash
uv run python scripts/security_audit.py
uv run pytest tests/security tests/unit/test_canonicalizer.py tests/contract/test_transport.py
uv run pip-audit
```

The scanner is defense in depth, not proof that arbitrary binary archives contain no historical secret. The preserved archives were supplied as evidence and are not loaded by production.
