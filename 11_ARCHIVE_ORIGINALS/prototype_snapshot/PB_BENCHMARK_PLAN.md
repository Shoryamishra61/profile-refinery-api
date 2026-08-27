# Controlled Benchmarking & Evaluation Plan: Pure HTTPS API vs. PhantomBuster
To validate our purely reverse-engineered, no-browser architecture, we must execute a scientific, black-box benchmarking study. This plan establishes the metrics, gold-standard dataset criteria, and experimental conditions to compare our system's performance against PhantomBuster.

---

## 1. Core Evaluation Metrics
We will evaluate and measure performance across eight primary engineering axes:

| Metric | Measurement Methodology | Target Success Threshold |
| --- | --- | --- |
| **Field Recall** | Ratio of correctly populated fields vs. total fields present on the live profile page. | $\ge 95\%$ across all standard sections. |
| **Historical Coverage** | The depth of career and educational history retrieved. | **100% full career history** (effectively bypassing PhantomBuster's 2-job ceiling). |
| **Schema Quality** | Absence of flat-column flattening. Structured nested JSON arrays vs. rigid `linkedinJob1`, `linkedinJob2` structures. | 100% structured nested JSON matching RFC specifications. |
| **Provenance** | Inclusion of immutable URN tracing and metadata hashes representing the origin of each field. | Every major entity must contain its originating LinkedIn URN. |
| **Latency** | End-to-end processing time from HTTP request to JSON response. | $\le 3$ seconds per profile (bypassing PhantomBuster's 1–2 minute spin-up latency). |
| **Error Transparency** | Accuracy of returned status codes (e.g., distinguishing a 404 Not Found, 403 Session Expired, or 401 Private Profile vs. generic exit codes). | Strict adherence to RFC 9457 (Problem Details). Zero generic "exit code: 87" failures. |
| **Reproducibility** | Ratio of identical payloads returned across consecutive non-cached runs of the same profile URL. | $\ge 99\%$ consistency. |
| **Maintenance Overhead** | Number of engineering hours required to adapt code to an upstream LinkedIn layout or API change. | Minimal; isolated entirely to JSON-parsing and query ID adaptation scripts. |

---

## 2. Gold-Standard Test Set (The "Gold Set")
To ensure the benchmark covers real-world edge cases, we will construct a test set of **50 consented profiles** distributed across the following five morphological categories:

1. **The Career Veteran (10 Profiles):** Highly populated profiles containing $\ge 15$ experience entries, $\ge 5$ education entries, and multiple concurrent roles. This cohort is designed to test the limits of our historical coverage vs. PhantomBuster's 2-job ceiling.
2. **The Non-Latin / Multilingual Profile (10 Profiles):** Profiles containing characters in Cyrillic, Chinese, Arabic, or Hebrew, as well as profiles with headlines and summaries in multiple languages. Tests Unicode compliance and internationalization.
3. **The Minimalist (10 Profiles):** Fresh or highly restricted profiles containing only a name, headline, and location (with empty About and zero experience arrays). Tests the system's "missing-field" semantics (ensuring keys are cleanly omitted or set to null rather than throwing parsing errors).
4. **The Privacy-Wall Profile (10 Profiles):** Profiles configured with maximum privacy constraints (e.g., hidden profile pictures to non-connections, private work histories). Evaluates our API's ability to cleanly return authorized visibility metrics.
5. **The Non-Standard Slug (10 Profiles):** Profiles containing special characters, accented letters, or duplicate vanity names in their URLs. Evaluates our input sanitization and Identity Resolution stages.

---

## 3. Controlled Experimental Conditions
To maintain perfect scientific integrity and protect our test sessions:
* **Consented Access Only:** All test targets must represent consented personal profiles of team members or public entities. No active personal accounts will be used to scrape unauthorized profiles during testing.
* **Isolated Session Environments:** The benchmarking tests for our API and PhantomBuster will execute using completely separate LinkedIn accounts to prevent activity overlaps from poisoning our request volume tracking.
* **Deterministic Jitter & Latency Logs:** All requests will be logged with microsecond-precision timestamps to record exact endpoint execution delays.