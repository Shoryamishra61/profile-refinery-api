# Controlled Reverse-Engineering Protocol

## Goal

Find the smallest current direct HTTP request graph required for the challenge, while keeping browser use out of production.

## Step 1 — consented fixtures

Choose own/authorized profiles. Record URL, viewer account/context, locale, timestamp, and manually visible required fields.

## Step 2 — manual network observation

Use DevTools/HAR only in research. Never commit HAR with cookies/tokens. Record redacted metadata: semantic purpose, method, path template, operation name, variables, response family, pagination metadata, status, date.

## Step 3 — minimum core operation

Identify current operation that yields/resolves identity and mandatory primitives (name/headline/location/about/image when available).

## Step 4 — direct replay

Replay via direct HTTP using owned session. Do not add anti-detection/bypass systems. Record status, response shape, latency, viewer context.

## Step 5 — required sections

For experience, education, skills, certifications, languages determine whether data is in core response, separate operation, paginated, or unavailable to current viewer.

## Step 6 — registry

Only `live_verified` operations may be enabled. Record semantic name, family, method/path, query ID env key if needed, variables, parser, observation time, evidence, viewer context.

## Step 7 — fixture

Save redacted/synthetic raw fixtures for every enabled operation. Remove secrets, tracking values, unrelated personal data.

## Step 8 — independent live field matrix

Compare API output with manually established ground truth. Never use extractor output as its own answer key.

## Query-ID policy

Treat pre-registered identifiers as volatile. Store in config/secret environment, record observation date, explicitly detect invalid operation. Do not auto-scrape production bundles as runtime evasion logic.

## Failure is evidence

On failure: capture redacted status/shape, do not retry aggressively, classify auth vs operation drift vs viewer restriction vs upstream issue, update registry.
