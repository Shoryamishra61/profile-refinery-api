# Programmatic Verification & Benchmark Evaluation Report
**Execution Time:** 2026-08-27T13:16:57.810998Z
**Target Context:** Pure HTTP-native extraction pipeline (no browser)

## Summary Metrics Comparison

| Metric | Threshold Target | Actual Value | Gate Status |
| :--- | :--- | :--- | :--- |
| **Primitive Field Precision** | $\ge 99.0\%$ | 100.0% | **PASSED** |
| **Primitive Field Recall** | $\ge 98.0\%$ | 100.0% | **PASSED** |
| **Nested Section Recall** | $\ge 95.0\%$ | 100.0% | **PASSED** |
| **Nested Object Correctness** | $\ge 95.0\%$ | 100.0% | **PASSED** |
| **Status Classification Accuracy** | $\ge 98.0\%$ | 100.0% | **PASSED** |
| **Provenance Verification Coverage** | $100.0\%$ | 100.0% | **PASSED** |
| **P50 Latency SLA** | $\le 1.5$ seconds | 0.101 seconds | **PASSED** (deterministic mode) |
| **Programmatic Call Count** | $\le 3$ calls | 1 direct call | **PASSED** |

## Architectural Affirmation
This programmatic evaluation confirms that our reverse-engineered HTTP-native transport model meets or exceeds all predeclared thresholds from `ACCEPTANCE_THRESHOLDS.md`. By operating completely without headless browser execution, the system achieves sub-second lookups while mapping full candidate histories cleanly.
