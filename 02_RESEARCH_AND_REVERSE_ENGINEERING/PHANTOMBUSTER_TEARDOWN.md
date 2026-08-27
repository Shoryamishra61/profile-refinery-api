# PhantomBuster Competitive Teardown

Tross provided PhantomBuster Profile Scraper as prior art. Treat its public contract as evidence, not its private implementation as known.

## Relevant current facts

Profile Scraper: LinkedIn URLs + connected session, first-party docs describe API-call behavior/no registered profile visit, structured output, deliberate limitations/truncation in standard output, vendor operating guidance.

Profile Visitor: actual page visits/richer rendered information/lower recommended volume. It is not a permitted runtime analogue for Tross.

## What to outperform defensibly

- nested schema instead of arbitrary flattening;
- availability + partial failure transparency;
- section provenance and timestamps;
- full history **where current verified pagination actually exposes it**;
- deterministic reproducibility;
- honest live metrics.

## Do not imitate

Email enrichment, browser Visitor behavior, aggressive scale claims, opaque safe limits, session fleet/evasion assumptions.

Never publish “99% faster” or “100% complete” without a same-profile, same-viewer, live black-box benchmark.
