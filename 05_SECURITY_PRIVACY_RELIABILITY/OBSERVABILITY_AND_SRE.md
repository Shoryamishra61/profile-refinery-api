# Observability and Reliability

## Metrics
API request count/latency/status/caller 429. Per semantic upstream operation: calls, duration, status class, timeout, drift, parser failure. Quality: complete vs partial, section availability.

## Logs
One structured event per operation: request_id, operation, duration_ms, status, parser outcome, attempt. No secrets or profile payload.

## Timeouts/retries
Separate connect/read/total budgets. Retry only low bounded transient network/5xx. Optional slow section cannot exceed total API budget.

## Circuit behavior
Repeated operation drift may temporarily disable that optional operation while preserving core service. Session challenge disables live mode until manual action.

Do not publish SLOs before live measurement. Report fixture, controlled-live, and deployment metrics separately.
