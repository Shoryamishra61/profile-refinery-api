# ADR-0001: Upstream access model

## Context
A single personal LinkedIn session was simultaneously the authentication mechanism,
throughput ceiling, rate-limit domain and failure domain: ~20 rapid probes pushed the
upstream into a challenge state and the whole extraction capability went down with it.
Tross requires direct HTTP endpoint access with the candidate's own legitimate session;
browser automation and safeguard evasion are out of scope.

## Decision
Model LinkedIn as a scarce external dependency behind one governed subsystem
(`governor.UpstreamGovernor`). Least-privilege order of preference:

1. public/guest-accessible operations — evaluated and rejected by evidence: page
   requests get the 999 bot wall and dash resources require a member context.
2. one authenticated context supplied by the operator through environment secrets
   (`SessionProvider` is the AuthenticationContextProvider: `load()/available/
   fail_closed()`), consumed exclusively by the transport.

## Alternatives considered
* Multiple rotating accounts — rejected: manufacturing/rotating identities to spread
  load is safeguard evasion in spirit.
* Proxy pools / TLS-fingerprint mimicry — rejected: evasion.
* Unauthenticated scraping — rejected by evidence (999 / 410 / 404).

## Tradeoffs
One session remains a single availability dependency; capacity is therefore bounded
by design (rate budget + breaker) instead of hidden behind retries.

## Consequences
Extraction capacity is explicit and conservative; session expiry is an operational
event (capability `AUTH_EXPIRED`) with a documented operator runbook.

## Validation
Anonymous probes recorded in docs/REVERSE_ENGINEERING_PROTOCOL.md; challenge
behaviour reproduced and encoded in tests (challenge → breaker OPEN).
