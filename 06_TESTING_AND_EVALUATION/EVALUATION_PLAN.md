# Evaluation Plan

## Golden rule

Ground truth must be independent of system output.

## Fixture benchmark

Tests parser/schema regressions only. Expected normalized JSON is manually authored and checked in. Prefix metrics with `fixture_`. Fixture metrics do not prove LinkedIn extraction accuracy.

## Controlled live benchmark

Recommended 8–15 consented profiles if time constrained; include sparse/rich, multiple jobs/schools, missing sections, images, multiple locales.

Human ground truth records expected visible value, visibility state, timestamp, reviewer.

Metrics:

- required-field precision
- observable-field recall
- experience entry recall
- education entry recall
- section success/classification
- defensible status accuracy
- real wall-clock latency
- actual upstream calls/profile

Always state sample size, e.g. `94.1% (n=153 observable fields across 12 profiles)`.

## PhantomBuster comparison

Same profiles/viewer context/time window where possible. Never compare our fixture timing/recall to PB live behavior.

## Suggested gates

Fixture: 100% contract tests/schema validity/no uncaught mutation errors.
Live: >=99% precision on returned mandatory primitive fields; >=90% recall on mandatory observable fields; >=90% experience/education entry recall where enabled operation exposes them; 100% honest tested failure classification.
