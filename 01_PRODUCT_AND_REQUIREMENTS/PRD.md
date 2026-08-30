# Product Requirements Document

## Product

Profile Refinery LinkedIn Profile API.

## User/job

A developer/evaluator submits a LinkedIn member profile URL and needs a machine-readable profile response from direct reverse-engineered LinkedIn endpoints, with no runtime browser.

## Primary success

One public HTTPS endpoint returns mandatory observable fields with documented schema, provenance, partial-result behavior, and honest live evaluation.

## MVP MUST

- LinkedIn URL input
- direct HTTP runtime
- developer-owned secret session configuration
- name/headline/location/about
- experience/education/skills/certifications/languages
- profile image when available
- nested JSON contract
- partial errors/provenance
- deterministic fixtures
- independent controlled-live benchmark
- public HTTPS
- public repo/README/API docs/limitations/no secrets

## SHOULD

- background image
- multilingual handling
- grouped role fidelity
- drift detection
- PhantomBuster measured comparison

## COULD

- volunteering/projects/publications/honors
- short request coalescing
- richer telemetry

## WON'T for challenge

- email enrichment
- persistent people database
- browser runtime
- CAPTCHA solving
- account farms
- proxy/WAF evasion
- LLM parsing
- broad people-search product
