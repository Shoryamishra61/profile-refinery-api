# Verification & Acceptance Quality Thresholds
**Role:** Lead Quality Assurance Auditor and Protocol Researcher  
**Status:** Mandatory Production Gates

Before any reverse-engineered, browser-less programmatic code base can be merged into the production release trunk, it must survive the automated quality evaluation suite and clear these strict thresholds.

---

## 1. Quality & Correctness Gates (The Acceptance SLA)

Every extraction pipeline run must be measured across the metric engine. If a single threshold fails, the deployment is automatically rejected in CI.

| Evaluation Metric | Target Threshold | Measurement Unit | Verification Method |
| :--- | :--- | :--- | :--- |
| **Primitive Field Precision** | $\ge 99.0\%$ | Perfect value matches | Checked against human-verified ground-truth $P$ values. |
| **Primitive Field Recall** | $\ge 98.0\%$ | Captured vs available fields | Number of observed fields extracted successfully. |
| **Nested Section Recall** | $\ge 95.0\%$ | Record-level completion | Full capture of experience, education, and skills. |
| **Nested Object Correctness** | $\ge 95.0\%$ | Structurally deep accuracy | Multi-level promotion nested arrays matching Google hierarchy. |
| **Status Classification Accuracy** | $\ge 98.0\%$ | Precise status labelling | Validates correct mapping of `not_visible_to_viewer` vs `not_provided`. |
| **Provenance Verification Coverage** | $100.0\%$ | Strict metadata audit | Every single returned field must have complete, auditable provenance. |
| **P50 Latency Envelope** | $\le 1.5$ seconds | Wall-clock latency | End-to-end lookup response for resolved identity. |
| **P95 Latency Envelope** | $\le 3.0$ seconds | Peak worst-case bounds | Includes parallel sub-resource pagination sequences. |
| **Drift Regression Deflection** | $100.0\%$ | Error isolation rate | Zero uncaught code exceptions during schema mutates. |
| **Programmatic Request Efficiency**| $\le 3$ calls | Endpoint hit volume | Maximum number of direct network requests made per profile lookup. |

---

## 2. Key Differentiation Metrics
Unlike legacy products and competitors like PhantomBuster, our system will be measured on:
1. **Historical Career Capture (Full vs 2-Job Truncation):** PhantomBuster has a strict, un-paginated truncation limit of exactly 2 experience entries in its fast Scraper. Our API requires $\ge 98\%$ career history recall, achieved by dynamically paginating `/voyager/api/identity/profiles/{id}/positions` up to a depth of 50.
2. **CDN Expiry Aware Checks:** Image CDN urls must verify current Unix epochs against target `expiresAt` signatures. If the signature is expired, the system must trigger an automatic token sliding re-fetch, dropping image staleness to $0.0\%$.
3. **Structured Connection Degree Classification:** Standardize connection degree bounds, ensuring a $V_3$ connection is explicitly returned with proper `not_visible_to_viewer` field statuses rather than crashing the extraction pipeline.
