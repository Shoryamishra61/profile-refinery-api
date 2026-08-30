# ADR-0003: Rate budget, retry budget, circuit breaker

## Context

~20 requests in seconds triggered a LinkedIn soft challenge (same-URL 302 + cookie
clearing). Retries consume upstream capacity; uncontrolled retries amplify overload.

## Decision

Three independent controls in `UpstreamGovernor`:

* **Token bucket** — burst capacity `APP_UPSTREAM_BUCKET_CAPACITY` (default 4) and
  sustained refill `APP_UPSTREAM_REFILL_PER_MINUTE` (default 12/min). Tokens are
  acquired after waiting (waiters re-consume in a loop — parallel sleepers cannot
  bypass the budget).
* **Retry budget (single layer)** — only the governor retries; bounded attempts
  (`APP_UPSTREAM_RETRIES`, default 1) with exponential backoff + ±20% jitter, only
  for transient errors (timeout, 429). Deterministic failures never retry.
  Job-level resumption after RETRY_WAIT is capped at 2 executions.
* **Circuit breaker** — challenge ⇒ immediate OPEN; `APP_BREAKER_FAILURE_THRESHOLD`
  consecutive failures ⇒ OPEN. OPEN rejects all extraction without upstream traffic
  (jobs ⇒ BLOCKED_UPSTREAM, retained). After `APP_BREAKER_COOLDOWN_SECONDS`
  (default 300s) exactly one HALF_OPEN probe runs; success ⇒ CLOSED, failure ⇒
  OPEN again. A cancelled probe re-enters OPEN (no wedge).

## Tradeoffs

Conservative pacing extends wall-clock time of large batches (measured: token bucket
adds pure pacing time — see `test_rate_budget_throttles_burst`). Correctness and
account safety outrank throughput.

## Validation

`test_rate_budget_throttles_burst`, `test_retry_containment_thirty_failures`
(30 jobs ⇒ exactly 120 upstream calls ceiling), `test_circuit_breaker_opens_recovers_via_single_probe`,
`test_half_open_probe_failure_reopens_breaker`.
