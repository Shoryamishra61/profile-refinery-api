# AGENTS.md — Binding Project Policy

## Mission

Build the Profile Refinery browserless LinkedIn Profile API: URL in -> direct LinkedIn endpoint calls -> normalized JSON out -> public HTTPS.

## Hard Profile Refinery pivot

Runtime browser use is prohibited. Never add Selenium, Playwright, Puppeteer, Chromium, browser workers, DOM acquisition, screenshots, or browser fallback.

Manual DevTools/HAR may be used only during controlled research with an account you control. It must not become a runtime dependency.

## Evidence hierarchy

Every protocol/performance claim must be classified:

1. `PRIMARY_VERIFIED` — official/standard/current primary source
2. `LIVE_OBSERVED` — current controlled live experiment
3. `FIXTURE_VERIFIED` — deterministic local fixture only
4. `HISTORICAL_PRACTITIONER` — old wrappers/blogs
5. `VENDOR_CLAIM` — PhantomBuster/vendor statement
6. `INFERENCE`
7. `UNKNOWN`

Never promote a weaker class to a stronger class without evidence.

## Truthfulness rules

Never report fixture latency as live latency. Never report synthetic recall as live recall. Never claim “100% history” without independent live ground truth. Never cite a universal safe request limit, session lifetime, proxy success rate, or ban probability unless a primary/current source actually proves it.

## Direct endpoint policy

Production may use developer-owned LinkedIn session material loaded from secrets and replay currently verified HTTP operations.

Production must not include:

- automated account creation or session farms;
- CAPTCHA solving;
- proxy rotation designed to defeat restrictions;
- TLS/WAF fingerprint spoofing;
- telemetry emulation;
- automated security-control bypass;
- runtime JS-bundle scraping to recover invalidated security-sensitive identifiers.

On checkpoint/challenge: stop live calls, mark the session unavailable, return a typed upstream error, require manual operator action.

## Operation registry

No endpoint/query ID in business logic. Every operation record requires semantic name, method, path, current identifier if needed, variables, response family, parser version, observed timestamp, viewer context, evidence reference, and status (`live_verified|historical|disabled|unknown`).

## Secrets

Never commit or log `li_at`, `JSESSIONID`, OAuth tokens, API keys, proxy credentials, HAR files with cookies, or raw sensitive profiles. Use deployment secrets/environment and structured allowlisted logging.

## Data minimization

Prioritize assignment fields. Do not collect email/contact data by default. No persistent people database for MVP.

## Missingness

Allowed public states: `present`, `not_provided`, `not_visible_to_viewer`, `not_available_from_endpoint`, `upstream_failed`, `parser_failed`, `stale_or_expired`, `unknown`.

Do not label a missing live field `not_visible_to_viewer` unless evidence establishes viewer restriction.

## Testing

Every enabled operation needs a redacted/synthetic raw fixture, parser contract test, malformed-shape test, and observation metadata. Live metrics require independent human/consented ground truth.

## Build order

Repository hygiene -> models/schema -> URL boundary -> operation registry -> direct HTTP transport -> one live core operation -> normalizer -> public endpoint -> required sections one-by-one -> partial orchestration -> independent live benchmark -> deployment -> adversarial audit.

## Blocking rule

Unknown technical facts go to `ASSUMPTION_REGISTER.md`; do not guess.

## Definition of success

A sophisticated mock is not a completed submission. Completion requires a fresh clone, direct live acquisition on permitted profiles, public HTTPS, no browser dependency, truthful metrics, and all gates in `DEFINITION_OF_DONE.md`.
