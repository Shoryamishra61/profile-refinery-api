# Engineering Brief: Building a Superior, Pure HTTP-Native LinkedIn API
This document outlines our strategy to build a hosted LinkedIn Profile API that is structurally superior to PhantomBuster. It identifies which competitor concepts are worth adopting, which are completely irrelevant due to our strict **no-browser** mandate, and which are dangerous vendor assumptions that we must reject.

---

## 1. Architectural Alignment

```
                              ┌──────────────────────────────────────┐
                              │  Our Pure HTTP-Native API Strategy   │
                              └──────────────────┬───────────────────┘
                                                 │
         ┌───────────────────────────────────────┼───────────────────────────────────────┐
         ▼                                       ▼                                       ▼
┌──────────────────┐                    ┌──────────────────┐                    ┌──────────────────┐
│  WORTH COPYING   │                    │    IRRELEVANT    │                    │ DANGEROUS REJECT │
└────────┬─────────┘                    └────────┬─────────┘                    └────────┬─────────┘
         │                                       │                                       │
         ├─ Separate Speed from Depth            ├─ Puppeteer & Headless Chrome          ├─ "1,500/day is Safe"
         ├─ Persistent State Management          ├─ DOM Parsing & Click Automation       ├─ Static GraphQL queryId
         └─ Output Normalization Schema          └─ Session Capture Extensions           └─ Naked Voyager API Requests
```

### A. What is Worth Copying (The Architectural Gold)
* **Separating Speed/Throughput from Depth:** We must adopt a clean, two-tier product model:
    * *Fast Path (Direct Profile Scraper):* Bypasses heavy loading to return immediate core profile data.
    * *Deep Path (Full Trajectory Extractor):* Paginates nested career, education, and skill endpoints to build the complete career history.
* **Persistent State Management:** Replaying previous progress markers (pointers) using lightweight, stateless databases in our backend rather than re-querying identical URLs.
* **Output Normalization:** Mapping unstructured, messy raw fields returned by LinkedIn into a highly polished, machine-readable, schema-validated JSON contract.

### B. What is Completely Irrelevant (The Browser Junk)
Because Tross strictly prohibits browser execution at runtime, the following elements of PhantomBuster's architecture are completely discarded:
* **Headless Chrome & Puppeteer Orchestration:** No browser execution in our cloud workers, saving massive compute resources, memory leaks, and cold-start delays.
* **DOM Selector Maintenance:** Zero reliance on CSS classes or fragile page structure parsing.
* **Browser Extension Capture:** We will not force users to install a heavy local extension; instead, our API will accept credentials securely in the backend or programmatically manage session inputs.

### C. Dangerous Competitor Assumptions We Must Reject
1. **The "1,500 Profiles/Day is Safe" Fallacy:** Reject this vendor-level marketing guidance. We will implement strict per-account sliding-window rate limiters capped at a conservative **80–100 actions per day** to guarantee zero account bans in production.
2. **Hardcoded Static queryIds:** PhantomBuster's reliance on hardcoded GraphQL POST hashes means their product instantly breaks when LinkedIn rotates frontend bundles. We will implement a dynamic **JavaScript Archaeology Parser** that automatically fetches and extracts the latest production hashes on the fly.
3. **Naked Voyager Requests:** Replaying raw Voyager calls without mimicking the surrounding transport fingerprinting (JA4/JA4H/JA4T) or client-side telemetry queues (Lempel-Ziv compressed `/li/track` mouse/keyboard events) results in immediate server-side flags. We must construct a complete transport-level TLS-spoofing layer.

---

## 2. Our Structural Differentiation Plan
By focusing entirely on an HTTP-native API, we can achieve substantial product differentiation across five key axes:

### A. Full Career & Education History Retrieval
* *PhantomBuster:* Truncates career and education to the two most recent entries to manage request volume.
* *Our API:* Intelligently checks the initial profile response length. If additional career entries are present, our background egress worker executes lightweight, concurrent sub-resource requests to paginated endpoints (e.g., `/voyager/api/identity/profiles/{id}/positions`) to reconstruct the 100% complete career trajectory.

### B. Direct URN-Level Provenance
* *PhantomBuster:* Delivers flat, detached text strings.
* *Our API:* Appends a nested `_metadata` block to every entity array. This block preserves the originating LinkedIn URNs (e.g., `urn:li:member:12345`, `urn:li:position:98765`), providing clients with auditable data lineage and verifiable data freshness.

### C. Clean, Schema-Validated Nested JSON Contracts
* *PhantomBuster:* Forces flat CSV-mapped keys into JSON.
* *Our API:* Publishes a strict, recursive JSON schema where experiences, schools, certifications, languages, and skills are represented as beautifully nested arrays of objects. Null fields are explicitly handled, and dates are strictly normalized to ISO 8601 formatting.

### D. Deep Error Transparency
* *Our API:* Replaces generic "exit code" architectures with rich, descriptive, and actionable error states conforming to **RFC 9457 (Problem Details for HTTP APIs)**. Our errors clearly isolate the exact cause of a failure:
    * `unauthenticated-session`: Session cookie invalidated or expired.
    * `private-profile-wall`: Target profile is outside the current authenticated viewer's visibility graph.
    * `upstream-schema-drift`: LinkedIn has mutated the underlying Rest.li models, triggering automated alerts to our SRE queue.
    * `rate-limited-cooldown`: Sliding-window limits active.

### E. Low Latency & High Concurrency
* *Our API:* Bypasses all cloud container initialization delays. Our backend endpoints are hosted on a fast, asynchronous routing gateway, achieving sub-second identity resolution and an end-to-end lookup latency of **$\le 3$ seconds per profile**, opening up real-time enrichment use cases that PhantomBuster simply cannot support.