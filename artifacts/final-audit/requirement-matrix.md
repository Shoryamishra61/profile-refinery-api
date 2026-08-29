# Requirement matrix — final audit

Status enum: `VERIFIED` / `IMPLEMENTED_UNVERIFIED` / `PARTIAL` / `MISSING` / `BLOCKED_BY_UPSTREAM` / `NOT_REQUIRED`

Evidence keys: **T#** = named test, **P** = production observation, **L** = live LinkedIn observation, **S** = spec/source inspection.

## P0 — profile path

| Requirement | Status | Evidence |
|---|---|---|
| direct HTTP production path | VERIFIED | S: transport.py only HTTP adapter; P: production extraction calls voyager |
| no browser | VERIFIED | security_audit.py browser-terms gate; S: no such imports |
| no synthetic fallback | VERIFIED | fixture mode deleted; sentinel leak test T(test_live_fail_closed) |
| public HTTPS | VERIFIED | P: https://tross-linkedin-profile-api.vercel.app/healthz 200 |
| profile URL validation | VERIFIED | T(test_canonicalizer) |
| canonical URL | VERIFIED | T(test_canonicalizer), P |
| public identifier | VERIFIED | L: real payload (williamhgates) |
| profile URN | VERIFIED | L: `urn:li:fsd_profile:ACoAAA8BYqE…` |
| first name | VERIFIED | L + T(test_parsers core) |
| last name | VERIFIED | L + T |
| full name | VERIFIED | L + T |
| headline | VERIFIED | L: "Chair, Gates Foundation and Founder, Breakthrough Energy" |
| location | VERIFIED | L-shape (locationName); null when hidden (honest null) |
| about | VERIFIED | L: Gates Foundation summary |
| profile image | VERIFIED | L: CDN url constructed from live vectorImage artifacts |
| background image | IMPLEMENTED_UNVERIFIED | same parser path; present only when member uploaded |
| experience | IMPLEMENTED_UNVERIFIED | shape-tested T(test_parsers, test_normalized_graph); live cards contract unverified |
| company URL/URN | IMPLEMENTED_UNVERIFIED | same |
| is_current | IMPLEMENTED_UNVERIFIED | derived start/end presence |
| education | IMPLEMENTED_UNVERIFIED | same as experience |
| skills | IMPLEMENTED_UNVERIFIED | profile_skills contract historical |
| certifications (+issuer) | IMPLEMENTED_UNVERIFIED | profile_certifications contract historical |
| languages (+proficiency) | IMPLEMENTED_UNVERIFIED | profile_languages contract historical |
| target-URN graph correctness | VERIFIED | T(test_normalized_graph: foreign profile/position, groups, dangling, ambiguous, cycles) |
| attributed text normalization | VERIFIED | T(test_normalized_graph text shapes, test_parsers) |
| JSON Schema on success | VERIFIED | T(test_api contract) + orchestrator validates every response |
| field provenance | VERIFIED | every ProfileField carries source_operation/observation_time/parser_version/URN |
| coverage metadata | VERIFIED | T(test_api coverage assertion); meta.coverage observed/observed_empty/unavailable |
| warnings | VERIFIED | meta.warnings (section failures, drift) |
| typed error envelope | VERIFIED | problem+json with code + request_id; T(test_api) |
| auth/session failure | VERIFIED | T(test_live_fail_closed), P: 401 observed |
| challenge behavior | VERIFIED | T(test_transport challenge, test_resilience breaker); P: UPSTREAM_CHALLENGE observed live |
| 429 behavior | VERIFIED | T(test_transport 429, test_partial_and_limits) |
| 5xx/network behavior | VERIFIED | T(test_transport timeout; governor retry) |
| schema drift | VERIFIED | T(test_parsers wrong-projection → typed drift) |
| raw response hidden | VERIFIED | problem+json envelope only; no raw upstream bodies in responses |

## P0 — section truthfulness

| Requirement | Status | Evidence |
|---|---|---|
| retrieved-empty ⇒ `[]` | VERIFIED | T(test_parsers missing-section) |
| failed ⇒ explicit unavailable | VERIFIED | normalizer section_failures → NOT_AVAILABLE_FROM_ENDPOINT / UPSTREAM_FAILED + coverage=unavailable |
| never [] as disguised failure | VERIFIED | orchestrator section-state plumbing T |

## P1 — batch/file pipeline

| Requirement | Status | Evidence |
|---|---|---|
| raw text / multi-URL | VERIFIED | T(test_batch) |
| JSON / CSV / XLSX / TXT / DOCX / PDF ingestion | VERIFIED | T(test_discovery formats) |
| content sniffing (misleading extension) | VERIFIED | T(test_discovery sniff_kind) |
| URL discovery | VERIFIED | T(test_discovery) |
| source-coordinate provenance | VERIFIED | T(test_discovery, test_batch provenance assertions) |
| canonicalization/dedup | VERIFIED | T(test_discovery, test_batch) |
| deterministic statistics | VERIFIED | batch.summary counters T |
| durable jobs / restart-resume | VERIFIED | T(test_resilience restart) |
| bounded workers / backpressure | VERIFIED | T(test_resilience backpressure: max_active ≤ 2 @100 jobs) |
| single-flight | VERIFIED | T(test_resilience coalescing) |
| retry budget (one layer) | VERIFIED | T(test_resilience containment: 30⇒120 ceiling) |
| circuit breaker | VERIFIED | T(test_resilience breaker open/probe/recover; half-open failure) |
| idempotency (same key/same body) | VERIFIED | T(test_batch idempotency) |
| idempotency (same key/different body ⇒ conflict) | **PARTIAL** | key reuse returns the same batch without body comparison — conflict semantics not implemented (documented gap) |
| JSON export | VERIFIED | T(test_batch exports) |
| CSV export | VERIFIED | T(test_batch exports) |
| XLSX export (8 sheets) | VERIFIED | T(test_batch xlsx sheets + failures sheet) |
| deterministic report + hash | VERIFIED | T(test_batch report determinism) |
| healthz/readyz/capability/metrics | VERIFIED | P: production smoke |
| challenge-aware dispatch | VERIFIED | T(test_resilience challenge recovery) |

## Hygiene / docs

| Requirement | Status | Evidence |
|---|---|---|
| secrets external | VERIFIED | security audit + Vercel secret store |
| logs redact credentials | VERIFIED | T(test_logging allowlist) |
| README complete | VERIFIED | README (narrative per spec §16 updated in this pass) |
| exact curl verified | VERIFIED | release-report.md |
| browser audit | VERIFIED | security_audit.py |

## Live validation

| Requirement | Status | Evidence |
|---|---|---|
| authenticated probe / rich profile core | VERIFIED | L: real williamhgates payload (2026-08-29) |
| section contract live success | BLOCKED_BY_UPSTREAM | LinkedIn client-fingerprint challenge (protocol notes #11); watcher + production breaker auto-retry |
| second/third unrelated profile | BLOCKED_BY_UPSTREAM | same |
| 30-profile live run | BLOCKED_BY_UPSTREAM / NOT_REQUIRED | spec §2 P2: not the core gate; harness staged |
