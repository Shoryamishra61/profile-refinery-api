# Test Plan

## L1 Unit
URL parser, settings, status mapper, date/media normalizers, entity reference resolver, Problem Details.

## L2 Raw fixture parser contracts
One fixture per semantic operation: expected shape, missing optional key, type mutation, unknown entity, empty array, malformed pagination.

## L3 Orchestrator fixture integration
Dependency order, bounded concurrency, partial sections, operation metadata, actual request-count instrumentation.

## L4 API integration
200 complete, 200 partial, 400 invalid URL, 401 missing/invalid key, 404 not found, 429 caller rate limit, 502 operation/schema drift, 503 session challenge, 504 timeout.

## L5 Security
SSRF/lookalike domain, redirect, secret redaction, dependency no-browser scan, git secret scan, malformed/oversized upstream.

## L6 Controlled live integration
Own/consented profiles only. Record required field accuracy, operation success, live latency, actual calls/profile, partial behavior.

## L7 Public deployment smoke
HTTPS health, authenticated request, invalid request, controlled live profile if permitted.

## Invariants
Missing schema fails startup; missing live secrets fail live startup; no browser runtime; section failure cannot corrupt successful sections; expected outputs are independent; no fabricated contact data; unknown missingness is not mislabeled hidden.
