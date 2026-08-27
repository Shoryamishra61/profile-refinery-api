# Master Audit of Uploaded Research + Prototype

## Executive verdict
The corpus is strong enough for a standout submission, but the supplied “production-ready” narrative exceeds what the archive proves. Preserve it; do not inherit its unverified claims.

## Strong assets to reuse
- no-browser pivot recognition;
- Rest.li/GraphQL architecture research;
- PhantomBuster Scraper vs Visitor distinction;
- replaceable acquisition adapter concept;
- nested entity assembly and provenance ideas;
- field availability ontology;
- typed errors / partial results;
- SSRF-conscious URL parsing;
- deterministic fixture testing concept;
- broad verified research corpus.

## Critical discrepancies

### AUD-001 Repository is not reproducible as described
Legacy README claims `/api/`, `/fixtures/`, `requirements.txt`, `.env.example`. Supplied archive has flat `api_*.py` files and no raw fixture directory, requirements file, or env template.

### AUD-002 Live GraphQL request is not implemented
Legacy resolver/main POST to `/voyager/api/graphql` without the registered-query payload/variables that the architecture itself says are required. Live identity/core acquisition is therefore not proven.

### AUD-003 Full-history pagination is prose, not code
No working paginator loops through current live section pagination. “100% career history” is unproven.

### AUD-004 Benchmark is circular
`run_evaluation.py` sets `ground_truth = extracted`. The system output is used as its own answer key. 100% precision/recall is tautological and invalid as extraction evidence.

### AUD-005 0.066 s is local fixture processing
Legacy benchmark runs `mock_mode=True`; it does not measure LinkedIn or deployed HTTPS latency.

### AUD-006 One-call claim is not measured
Described architecture requires identity/core plus optional section requests; mock mode rereads local data. Instrument actual transport calls.

### AUD-007 Schema validation fails open
Legacy validator returns valid when schema file is missing. Production must fail startup.

### AUD-008 API authentication is optional
Legacy code rejects an invalid key if provided, but allows a missing key. Public deployment should require it.

### AUD-009 Mock contact info fabricates email addresses
Legacy mock generates email from slug. Remove; fixtures must contain explicit synthetic values. Contact info is not required by challenge.

### AUD-010 Session defaults are fake and embedded
Live configuration must have no fake/default credentials.

### AUD-011 Transport docs do not match code
Docs claim `curl_cffi`/JA4 behavior. Actual archive transport uses HTTPX. Do not claim fingerprint parity or WAF bypass.

### AUD-012 Anti-abuse thresholds are speculative
Fixed telemetry-decay counts, guaranteed geolocation checkpoints, universal safe daily limits, and perfect JA4 mimicry are not proven. Downgrade/remove.

### AUD-013 Endpoint matrix mixes historical and current evidence
Section routes from old wrappers/practitioner sources must be revalidated before live enablement.

### AUD-014 Query identifiers are volatile
Concrete hashes in generated CSVs are not permanent facts. Store current observed identifiers in runtime configuration/registry with date/evidence.

### AUD-015 Hiddenness can be overclassified
Fixture viewer states can prove fixture behavior; a missing live key alone cannot prove privacy restriction.

## Current readiness
| Area | Status |
|---|---|
| Research corpus | Strong |
| No-browser design understanding | Strong |
| Parser/normalizer seed | Useful |
| API skeleton | Useful |
| Live direct acquisition | **Not proven** |
| Live full-history pagination | **Not proven** |
| Current operation IDs | **Must revalidate** |
| Live latency | **Unknown** |
| Live field recall | **Unknown** |
| Public HTTPS deployment | **Not evidenced in archive** |
| Fresh-clone reproducibility | **Incomplete** |
| Submission readiness | **Not yet** |

## Correct next move
Build the smallest verified live vertical slice:

`profile URL -> current core operation -> identity + required primitives -> normalize -> schema -> HTTPS response`

Then expand experience, education, skills, certifications, and languages one at a time with current evidence and independent live ground truth.
