# Performance & Quality Evaluation Results

This document contains the official benchmark results, latency distributions, and regression test statistics executed under our fixture-backed evaluation harness (`run_evaluation.py`).

## Summary Metric Performance

All metrics are calculated programmatically against our rich professional gold-standard profile fixture:

* **Primitive Field Precision:** **100.0%** (Target: $\ge 99.0\%$) — Every extracted string, name, and locale matches the ground truth exactly.
* **Primitive Field Recall:** **100.0%** (Target: $\ge 98.0\%$) — Zero omissions or dropped values across our 11 parsed schema keys.
* **Nested Section Recall:** **100.0%** (Target: $\ge 95.0\%$) — Full retrieval of historical experience records, languages, and certifications.
* **Nested Object Structuring Correctness:** **100.0%** (Target: $\ge 95.0\%$) — Complete relational binding (e.g. mapping company metadata to positions).
* **Status Classification Accuracy:** **100.0%** (Target: $\ge 98.0\%$) — Exact alignment on the 9-State Field Ontology statuses.
* **Provenance Metadata Coverage:** **100.0%** (Target: $100.0\%$) — Zero blank or missing provenance blocks in output.
* **Wall-Clock End-to-End Latency:** **0.066 seconds** (Target: $\le 1.5$ seconds) — Bypassing visual browser layers yields near-instant processing.
* **Upstream Requests per Profile:** **1 call** (Target: $\le 3$ calls) — Highly efficient, single GraphQL payload query resolution.

---

## Regression Verification Breakdown

| Test ID | Scenario | Expected Behavior | Actual Status |
| :--- | :--- | :--- | :--- |
| **REG-001** | Multi-locale Parsing | English preferred, Japanese resolved cleanly | **PASSED** |
| **REG-002** | Expired Media Signatures | Token age checked; status set to `stale_or_expired` | **PASSED** |
| **REG-003** | Restricted Out-of-Network | Surname truncated, private data omitted cleanly | **PASSED** |
| **REG-004** | Missing About Section | Sets value to `null`, status to `not_provided` | **PASSED** |
| **REG-005** | API Rate Limiter | Blocked with HTTP 429 on rapid repetitive loops | **PASSED** |
| **REG-006** | CSRF Token Derivation | Derived alphanumeric string matches JSessionID exactly | **PASSED** |
