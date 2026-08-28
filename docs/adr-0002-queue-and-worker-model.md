# ADR-0002: Queue and worker model

## Context
Batches of ~30 profiles must not translate into 30 simultaneous upstream requests.
The deployment platform is serverless (Vercel): no always-on background workers.

## Decision
Queue-based load leveling with a **pull-driven worker model**: `POST /v1/batches`
creates durable jobs; every polling `GET` advances the queue for a bounded time
budget (`wait_seconds`, capped) under a bounded-concurrency semaphore. The queue
absorbs client arrival rate; the upstream governor determines processing rate.

## Alternatives considered
* Synchronous fan-out — rejected: unbounded burst.
* Celery/Redis/Kafka — rejected: heavy infrastructure for a ≤200-job workload;
  violates "smallest justified change".
* Vercel Cron — rejected: fixed-interval polling is the load problem, not the cure
  (prompt §38); the pull model advances work only when a client actually asks.

## Tradeoffs
Throughput depends on clients polling. Idle batches do not progress — acceptable for
an on-demand API; jobs are never lost (journal) and resume on the next poll.

## Validation
`test_backpressure_hundred_jobs_two_concurrent` (max concurrency 2 observed, exactly
one upstream request per profile, 100/100 succeeded), `test_durable_jobs_survive_restart`.
