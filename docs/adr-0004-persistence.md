# ADR-0004: Persistence model

## Context
Serverless instances are ephemeral; a restart must not destroy batches, and repeated
queue delivery must not duplicate upstream work.

## Decision
JSON journal in `APP_STORE_DIR` (default `./.tross_store`, `/tmp` on Vercel): one
atomic document per batch (temp file + os.replace), rewritten on every state
transition, restored on process start. Job identity is deterministic:
`sha256(canonical_url | parser_version)[:16]` — redelivery and restarts are safe.
Every attempt records started/completed/outcome/latency/breaker state (never secrets).

## Alternatives considered
* SQLite — better queryability but file locking on ephemeral disks adds failure
  modes for zero benefit at this scale.
* Managed DB/Redis — the honest upgrade path when batches must survive cold starts
  and multi-instance fan-out; deferred (ADR-0005).

## Tradeoffs
On Vercel the journal survives warm restarts only; a cold start loses batch state
(in-memory + disk both ephemeral per instance). Documented limitation; the upgrade
path is a managed KV/document store behind the same JournalStore interface.

## Validation
`test_durable_jobs_survive_restart` (new Runtime over same store completes the
batch without re-extracting completed jobs).
