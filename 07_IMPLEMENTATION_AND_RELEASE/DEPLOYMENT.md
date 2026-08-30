# Deployment

Container listens on `0.0.0.0:${PORT}`. Endpoints: `/healthz`, `/readyz`, `/docs`, `/v1/profiles`.

## Vercel fixture deployment

The repository declares `src.profile_refinery_api.main:app` as its Vercel Python
entrypoint in `pyproject.toml`. Connect the public GitHub repository to Vercel and set:

- `APP_MODE=fixture`
- `APP_API_KEYS=<optional operator-route keys>`

The fixture deployment is suitable for evaluator access and end-to-end API demonstration.
It must remain labeled `FIXTURE_VERIFIED`; it is not evidence of current LinkedIn behavior.

Verify the resulting HTTPS deployment directly:

```bash
curl https://YOUR_DEPLOYMENT/healthz
curl https://YOUR_DEPLOYMENT/readyz
curl https://YOUR_DEPLOYMENT/openapi.json
curl -H "X-API-Key: YOUR_KEY" \
  "https://YOUR_DEPLOYMENT/v1/profiles?url=https%3A%2F%2Fwww.linkedin.com%2Fin%2Fsynthetic-profile"
```

## Live deployment

Secrets injected at deployment: caller keys, LinkedIn session values, current enabled operation identifiers. Never bake into image.

Fixture mode needs no LinkedIn secrets. Live mode requires `APP_MODE=live`, session
secrets, current operation identifiers, and `live_verified` registry entries.

Deployment checklist: managed TLS ingress, request timeout, restart policy, health probes, minimal logs, no raw profile payload, no debug/env endpoint.

Judge-proof evidence: deployment URL, UTC deployment time, git commit SHA, external curl command, `/openapi.json`, consented demo profile.
