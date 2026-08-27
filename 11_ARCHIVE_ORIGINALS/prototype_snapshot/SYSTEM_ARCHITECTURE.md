# System Architecture: Browser-less Direct HTTP LinkedIn Profile API

This document details the software architecture of our research-grade, browser-less HTTPS API designed to resolve, fetch, and normalize LinkedIn profile data. Guided by the strict constraint of zero runtime browser dependency, every architectural component in this pipeline is lightweight, deterministic, and isolated.

## 1. High-Level Architecture Block Diagram

```
[API Caller] 
     │ (HTTPS request)
     ▼
[1. REST API Controller / Caller Auth & Rate Limiter]
     │ (Trusted input pass)
     ▼
[2. URL Canonicalizer & SSRF Filter] ──(Valid Slug)──► [3. Cache Lookup (In-Memory)]
                                                            │
                                                     (Miss/Stale)
                                                            ▼
                                                [4. Identity Resolver (Voyager)]
                                                            │
                                                     (Mutable URN Resolved)
                                                            ▼
                                                [5. Active Session Manager]
                                                            │
                                                   (Acquires JWT context)
                                                            ▼
                                                [6. LinkedIn HTTP Adapter (JA4/cffi)]
                                                            │
                                                   (Raw API GET/POST Calls)
                                                            ▼
                                                [7. Endpoint Orchestrator]
                                                    ├── GET /identity/profiles/{id}/positions (Paginated)
                                                    ├── GET /identity/profiles/{id}/educations (Paginated)
                                                    └── GET /identity/profiles/{id}/contactInfo
                                                            │
                                                   (Raw JSON Entities Array)
                                                            ▼
                                                [8. Parser & Entity Relational Assembler]
                                                            │
                                                   (De-normalized Graph -> Nested Struct)
                                                            ▼
                                                [9. Canonical Normalizer & Status Mapper]
                                                            │
                                                   (Enforces 9-State Field Ontology)
                                                            ▼
                                                [10. JSON Schema Validator (PROFILE_SCHEMA)]
                                                            │
                                                   (100% Schema & Provenance Match)
                                                            ▼
[API Response (Normalized JSON)] ◄──────────────────────────┘
```

---

## 2. The 11-Stage Conceptual Pipeline

### 1. API Request & Entry-point Gateway
* **Description:** The entry-point HTTP controller receives the incoming request (e.g., `GET /v1/profiles?url=https://www.linkedin.com/in/jane-doe`). It validates caller-level API tokens, applies client-specific rate limits, and registers the session context.
* **Failure Mode:** System saturation or database exhaustion when querying caller credentials.
* **Verification Test:** High-throughput mock load test asserting correct caller status mapping (e.g., HTTP 401 on missing tokens, HTTP 429 on rate-limit violations).

### 2. Strict URL Canonicalizer & SSRF Filter
* **Description:** Parses the user-supplied profile URL, stripping sub-domains, tracking query parameters, and extracting the clean alphanumeric vanity slug. It isolates DNS resolution of the parsed input using loopback-blocking checks to prevent Server-Side Request Forgery (SSRF) and arbitrary host routing.
* **Failure Mode:** Ingestion of malicious URLs designed to query local microservices or private internal network nodes.
* **Verification Test:** Pass invalid strings, local address spaces (`localhost`, `127.0.0.1`, `10.0.0.1`), and malformed URLs to confirm the module throws a strict validation exception.

### 3. Cache & Freshness Evaluation
* **Description:** Inspects a local transient in-memory cache to check if a fresh extraction of the requested slug is already available. If the cached record is within the freshness threshold, it returns the structured profile immediately, skipping upstream networks.
* **Failure Mode:** Cache poison attacks or returned stale entities that have already mutated upstream.
* **Verification Test:** Assert cache hits return immediately under identical query slugs, and cache misses fallback dynamically to the identity resolver.

### 4. Profile Identity Resolver
* **Description:** Maps the vanity alphanumeric slug to an immutable internal member identifier (such as the numeric member ID or platform URN e.g., `urn:li:fsd_profile:ACoAAAtp-4U`). It does this by executing a targeted call to the Voyager identity resolution endpoints or decoding historical lookup records.
* **Failure Mode:** Upstream slug changes resulting in a `PROFILE_NOT_FOUND` error or mismatching older numeric keys.
* **Verification Test:** Resolve a pre-mapped test slug and assert that the correct, stable platform URN is successfully returned.

### 5. Active Session Manager
* **Description:** Selects a valid, authenticated session context (derived from `li_at` and `JSESSIONID` cookies) from a local, rotation-aware pool. It validates cookie session health and dynamically extracts the required `csrf-token` header by stripping outer quotes from `JSESSIONID`.
* **Failure Mode:** Session expiration, silent account logging, or credentials-revocation under heavy load, causing upstream HTTP 403 blocks.
* **Verification Test:** Intercept requests with a deliberately expired session to verify the system correctly transitions the session to `EXPIRED` status and rolls over to a healthy standby cookie.

### 6. Authenticated Direct HTTP Transport Adapter
* **Description:** Emulates client web behavior at the lowest network levels. It isolates network traffic using `curl_cffi` to perform hardcoded JA4/JA4H TLS fingerprinting spoofing, ensuring headers (`X-RestLi-Protocol-Version: 2.0.0`, matching `User-Agent`, derived `csrf-token`) match browser footprints perfectly.
* **Failure Mode:** Handshake mismatch alerting edge firewalls (like Akamai or Cloudflare), causing CAPTCHA challenges.
* **Verification Test:** Inspect outbound packets in a mock environment to verify TLS hello-headers and JA4 profiles are identical to legitimate Chrome sessions.

### 7. Endpoint/Request Orchestrator
* **Description:** Runs parallel, non-blocking requests against modular LinkedIn endpoints (experience, education, skills, contactInfo). By isolating requests behind separate calls, it avoids legacy `/profileView/{slug}` monoliths that are highly prone to returning `HTTP 410 Gone`.
* **Failure Mode:** Sub-endpoint partial timeouts or unexpected structural updates to the API routing table.
* **Verification Test:** Verify that a slow response in the `/contactInfo` query does not halt the collection of `/positions` or `/educations`.

### 8. Response Validator
* **Description:** Audits the raw responses received from the upstream endpoints. It ensures status codes are `HTTP 200 OK` and inspects payloads for structural integrity, intercepting redirects to security checkpoints (reCAPTCHA, verification).
* **Failure Mode:** Upstream changes mutating payload structures, causing key-error crashes.
* **Verification Test:** Feed mock payloads with missing expected schema blocks and assert the system flags the issue as `UPSTREAM_SCHEMA_DRIFT` rather than crashing.

### 9. LinkedIn Entity/URN Assembler
* **Description:** De-normalizes the raw JSON-LD styled models. It processes the flat `included` array structure returned by Rest.li/GraphQL, recursively following relational URN pointers to match individual experience and educational blocks back to their parent profiles.
* **Failure Mode:** Relational mismatch or orphaned experience blocks that cannot be mapped to any parent profile ID.
* **Verification Test:** Provide a mock payload with out-of-order relational entities and assert the de-flattened output correctly nests positions under their respective company nodes.

### 10. Canonical Normalizer & Status Mapper
* **Description:** Transforms assembled entities into our standardized schema, converting varied strings and epoch dates to RFC 3339 format. It evaluates the **9-State Field Ontology** to assign accurate availability status (e.g., `not_visible_to_viewer` on non-connections) to every single schema field.
* **Failure Mode:** Data loss or misclassification of field availability status during mapping.
* **Verification Test:** Assert that a private email address hidden by user visibility rules is correctly flagged as `not_visible_to_viewer` rather than `not_provided`.

### 11. JSON Schema Validator
* **Description:** Validates the final canonical model against `PROFILE_SCHEMA.json` before sending the response. It asserts the schema format, checks field statuses, and verifies provenance metadata to ensure zero data regressions are returned to the caller.
* **Failure Mode:** Outbound payload fails schema validation, blocking the response.
* **Verification Test:** Intentionally corrupt a normalized record (e.g., change an integer string to raw data) and confirm the outbound validation layer catches and flags the regression.

---

## 3. High-Value Subsystem Architectural Decisions

This service isolates the direct LinkedIn transport behind an explicit adapter boundary:

```
[System Core / Normalizer] ◄──(Contract: Normalized JSON)──► [LinkedInTransportAdapter]
                                                                     │
                                                       (Emulated Wire-Level Layer)
                                                                     ▼
                                                         [Undocumented REST/GraphQL]
```

By decoupling these layers, any change to LinkedIn's private API (such as GraphQL queryId rotations or REST endpoint deprecations) only impacts the `LinkedInTransportAdapter` implementation. The outward-facing schema, validation layers, and caller interfaces remain completely stable, preserving downstream integrations from upstream protocol drift.
