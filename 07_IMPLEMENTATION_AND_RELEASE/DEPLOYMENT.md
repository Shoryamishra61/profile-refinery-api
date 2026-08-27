# Deployment

Container listens on `0.0.0.0:${PORT}`. Endpoints: `/healthz`, `/readyz`, `/docs`, `/v1/profiles`.

Secrets injected at deployment: caller keys, LinkedIn session values, current enabled operation identifiers. Never bake into image.

Fixture mode needs no LinkedIn secrets. Live mode requires explicit `LIVE_MODE_ENABLED=true`, secrets, and a `live_verified` core operation.

Deployment checklist: managed TLS ingress, request timeout, restart policy, health probes, minimal logs, no raw profile payload, no debug/env endpoint.

Judge-proof evidence: deployment URL, UTC deployment time, git commit SHA, external curl command, `/openapi.json`, consented demo profile.
