# ADR-0005: Deployment runtime

## Context
The workload: interactive single-profile requests (latency-sensitive), batches of
~30 (throughput-insensitive, durability-sensitive), file parsing, exports. Current
platform: Vercel serverless.

## Decision
Keep Vercel. The pull-driven queue (ADR-0002) is designed for it; long-running work
is chunked into poll-budget slices. Smallest justified change, no migration.

## Consequences / honest limits
* Batch state is per-instance (in-memory + /tmp journal): cold starts lose state.
* No scheduled recovery: batches progress when polled.
* Capacity per instance is bounded by the governor — safe by construction.

## Upgrade path (when required)
Move the journal behind a managed store (Vercel KV / Upstash Redis) and add a
cron-driven advancer with jitter+lease. The service boundary (JournalStore) is
already the only thing that changes.

## Validation
Production smoke tests on the deployed HTTPS service; resilience tests run the same
application object the deployment runs.
