# Failure Model

## Classes
Input: invalid URL, unsupported profile path, bad caller key.
Upstream/session: expired session, checkpoint/challenge, throttling, timeout, invalid/retired operation.
Semantic: not found, viewer unavailable, section absent, incomplete pagination.
Parser/contract: response type drift, missing reference, unknown date/media shape, normalized schema violation.

## State machine
`READY -> CANONICALIZED -> CORE_REQUEST -> CORE_PARSED -> SECTION_REQUESTS -> NORMALIZE -> SCHEMA_VALIDATE -> COMPLETE|PARTIAL`

Terminal/side states: `NOT_FOUND`, `SESSION_UNAVAILABLE`, `CHALLENGED`, `OPERATION_DRIFT`, `INTERNAL_CONTRACT_FAILURE`.

## Retry
Retry only low bounded connect/reset/clearly transient 5xx. Do not aggressively retry 400/401/403/404/410/challenge/schema drift.

## Challenge
Mark session unavailable, stop live calls, return typed 503, require manual recovery. No bypass.
