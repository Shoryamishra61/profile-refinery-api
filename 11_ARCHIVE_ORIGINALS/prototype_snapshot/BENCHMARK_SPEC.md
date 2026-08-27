# Automated Quality Benchmark Framework Specification
**Role:** Distributed-Systems Researcher and Evaluation Scientist  
**Status:** Architecture Blueprint

---

## 1. Architectural Architecture
The benchmark framework is designed to test the extraction accuracy, parsing stability, and performance envelope of our browser-less HTTP extraction API without incurring network overhead or risking real-world test accounts during automated CI/CD sweeps.

```
                  ┌───────────────────────────────┐
                  │   FIXTURE_MANIFEST.jsonl      │
                  └───────────────┬───────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                     AUTOMATED BENCHMARK RUNNER                  │
│                                                                 │
│  1. Ingest Manifest & Expected JSON Payloads                     │
│  2. Run Pure-HTTP Extractor Module on Mock Network Interface     │
│  3. Validate Extracted Output against PROFILE_SCHEMA.json        │
│  4. Execute metrics_implementation.py Engine                    │
└────────────────┬────────────────────────────────┬───────────────┘
                 │                                │
                 ▼                                ▼
┌─────────────────────────────────┐ ┌─────────────────────────────┐
│  DATA QUALITY EVALUATION REPORT │ │ RECONCILIATION AUDIT LEDGER │
│  - Field Precision & Recall     │ │ - Mismatched Field Paths    │
│  - Latency Metrics (P50/P95)    │ │ - Schema Drift Traces       │
│  - Provenance Verifiability     │ │ - Uncaught Exception Alerts │
└─────────────────────────────────┘ └─────────────────────────────┘
```

---

## 2. Test Execution Modes
The framework supports two distinct test execution modes:

### A. Deterministic Sandbox Replay (Mock Network)
* **Objective:** Verify parser and extraction logic isolation.
* **Mechanism:** The network wrapper intercepts outgoing REST/GraphQL HTTP requests and replays saved raw JSON network responses from `/workspace/scratch/expected_responses/` based on matched query parameters and slugs.
* **Benefit:** 100% deterministic, zero latency fluctuation, zero rate-limit depletion, zero account checkpoint risk.

### B. Live Integration Check
* **Objective:** Detect real-time LinkedIn upstream schema drift and session invalidation.
* **Mechanism:** Executes raw HTTP queries against LinkedIn's production network using active test session cookies.
* **Safety Rules:** Executed only in low-frequency, scheduled batches (twice daily) to preserve session integrity.

---

## 3. Schema Drift & Regression Survival Testing
To ensure the API does not fail silently when LinkedIn mutates backend GraphQL shapes, the benchmark runner executes a destructive drift simulation block:
1. **Key Deletion:** Remove critical keys (such as `title`, `companyName`, `geoLocation`) from raw mock network responses and verify the parser outputs status `parser_failed` rather than throwing unhandled `KeyError` or `TypeError` exceptions.
2. **Type Mutation:** Mutate integer timestamps to string date arrays and verify that the parser cleanly catches the validation error, falling back to empty fields labeled with `parser_failed` status.
3. **Relational Disconnects:** Inject orphan company URNs that do not exist inside the raw payload's `included` relational array. Ensure the parser returns a status `not_available_from_endpoint` or `parser_failed` on company fields while keeping the parent experience entry completely intact.
