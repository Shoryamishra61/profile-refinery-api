# System Implementation Backlog: Agile Development Plan

This backlog outlines the sprints, tasks, and definitions of done (DoD) to guide the engineering team toward a production-grade deploy.

---

## Sprint 1: Strict URL Sanitization & SSRF Defense (1 Week)
* **Objective:** Ensure the system safely and correctly processes user inputs, stripping tracking parameters and blocking SSRF exploits before triggering upstream network requests.
* **Tasks:**
  * **TSK-101: URL Canonicalizer Module:** Write Python parser to validate domains and extract clean alphanumeric slugs.
  * **TSK-102: Custom Loopback Block Resolver:** Implement DNS resolution interceptor to block private network spaces and loopback addresses.
  * **TSK-103: API Route Entry Points:** Build the primary GET controller with API-key checking.
* **Definition of Done:** 100% of local range URLs are rejected with HTTP 400 Bad Request, and clean subdomains resolve correctly to slugs.

---

## Sprint 2: JA4 Transport & Secure Session Manager (1 Week)
* **Objective:** Establish browser-less HTTP-native communication, spoofing edge security checks using low-level fingerprint emulation.
* **Tasks:**
  * **TSK-201: Active Session Pool Manager:** Create in-memory credential rotator with support for CSRF derivation.
  * **TSK-202: curl_cffi Integration:** Integrate HTTP client mimicking Chrome browser TLS profiles and JA4 signatures.
  * **TSK-203: Automated Session Rollover:** Build recovery mechanisms to handle HTTP 401/403 blocks and rotate compromised tokens.
* **Definition of Done:** Network-edge requests pass edge validation blocks and retrieve REST raw JSON payloads without throwing security checkpoint challenges.

---

## Sprint 3: Section Scrapers & Entity Assembler (1.5 Weeks)
* **Objective:** Retrieve, de-normalize, and nest all career sections to bypass the two-job ceiling.
* **Tasks:**
  * **TSK-301: Paginated Section Downloader:** Implement loop routines with offset parameters for `/positions` and `/educations`.
  * **TSK-302: Relational Entity Assembler:** Build de-flattening algorithms to map nested array relationships inside the raw `included` payloads.
  * **TSK-303: Schema Normalization Engine:** Map raw string attributes, converting Unix timestamp objects to clean RFC 3339 formats.
* **Definition of Done:** Parser correctly nests 100% of historical career positions and education records under their parent profiles, verified against the rich test fixture payload.

---

## Sprint 4: Validation Engine & Production Hardening (1 Week)
* **Objective:** Standardize the outbound API response, enforce status ontologies, and run regression tests.
* **Tasks:**
  * **TSK-401: Draft-07 JSON Schema Validation:** Wire `PROFILE_SCHEMA.json` validator into response pipeline.
  * **TSK-402: 9-State Ontology Mapping:** Write logic evaluating connection degrees and mapping field statuses.
  * **TSK-403: Drift Simulation Validation:** Implement tests validating graceful failure states under mock schema alterations.
* **Definition of Done:** Extraction responses pass outbound JSON schema validation with 100% metadata provenance coverage and correct status mappings.
