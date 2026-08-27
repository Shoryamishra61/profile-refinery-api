# Request Sequence: Browser-less End-to-End Execution Trace

The sequence diagram below traces the end-to-end execution of a profile lookup, detailing the transition through internal boundaries and the isolation of the direct HTTP transport layer.

## 1. Sequence Diagram

```
[API Caller]     [Controller]    [Canonicalizer]    [Identity]     [Session]     [Transport]     [Normalizer]
     │                 │                 │               │             │              │               │
     │──(GET URL)─────►│                 │               │             │              │               │
     │                 │──(Verify Input)►│               │             │              │               │
     │                 │◄─(Clean Slug)───│               │             │              │               │
     │                 │                                 │             │              │               │
     │                 │──(Resolve Identity)────────────►│             │              │               │
     │                 │◄─(Return Member URN)────────────│             │              │               │
     │                 │                                               │              │               │
     │                 │──(Request Session Token)─────────────────────►│              │               │
     │                 │◄─(Return Cookie context & CSRF)───────────────│              │               │
     │                 │                                                              │               │
     │                 │──(Replay Section Queries: HTTP GET/POST)────────────────────►│               │
     │                 │◄─(Return Raw JSON-LD payoads)────────────────────────────────│               │
     │                 │                                                                              │
     │                 │──(Process Raw Payloads)─────────────────────────────────────────────────────►│
     │                 │◄─(Return Normalized canonical JSON)──────────────────────────────────────────│
     │                 │                                                                              │
     │◄─(HTTP JSON)────│                                                                              │
```

---

## 2. Process Trace Step-by-Step

### Phase A: Input Ingestion & Sanitization
1. **Request Received:** The user submits a profile query: `GET /v1/profiles?url=https://www.linkedin.com/in/jane-doe` with an auth token `X-API-Key: user_token_abc` to the API gateway.
2. **Access Control:** The API gateway validates the token, tracks billing limits, and verifies rate-limiting buckets.
3. **Canonicalization:** The input is routed to the `URLCanonicalizer` module. It extracts the clean vanity slug (`jane-doe`), filters subdomains, and verifies that the target host matches `linkedin.com` to prevent SSRF vulnerabilities.

### Phase B: Identity Resolution & Session Fetching
4. **Identity Resolution:** The controller queries the cache. On a miss, it requests the stable platform URN (`urn:li:fsd_profile:ACoAAAtp-4U`) matching `jane-doe` from the `IdentityResolver` module.
5. **Session Acquisition:** The controller requests an active, authenticated session context from the `SessionManager` pool. The manager returns an aligned cookie jar containing valid `li_at` and `JSESSIONID` values, alongside the derived `csrf-token` header.

### Phase C: Transport Execution & Parsing
6. **Programmatic Query Execution:** The `LinkedInTransportAdapter` translates queries into specific Rest.li/GraphQL requests. Using `curl_cffi`, it emulates browser handshakes and triggers parallel queries:
   * `POST /voyager/api/graphql` (Pre-registered profile queryId hashes)
   * `GET /voyager/api/identity/profiles/{id}/contactInfo` (Contact details)
7. **Entity Reconstruction:** The raw JSON-LD array payloads are ingested by the `EntityAssembler` module. It parses the nested `included` array and resolves relationships (e.g., nesting work experiences under parent profile entities).

### Phase D: Normalization & Outbound Verification
8. **Normalization & Mapping:** The parsed objects are converted to the standardized profile schema. The system maps statuses (using our 9-State Ontology) and records deep provenance metadata.
9. **Contract Schema Validation:** The system runs the normalized JSON against `PROFILE_SCHEMA.json` to verify integrity.
10. **Delivery:** The validated canonical JSON payload is returned to the user with an `HTTP 200 OK` status.
