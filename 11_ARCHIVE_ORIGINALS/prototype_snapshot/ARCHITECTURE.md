# System Architecture Specifications
**Status:** Approved Design Specification  
**Focus:** Pure HTTP-Native Programmatic Extraction  

The system is designed around an **uncompromising browser-less request pipeline**. By eliminating the startup, execution, and rendering overhead of headless browsers, the service achieves sub-100ms processing thresholds, guarantees zero client-side javascript trace signatures, and significantly reduces operational infrastructure costs.

## Conceptual Extraction Pipeline

```
[Incoming URL GET /v1/profiles]
             │
             ▼
   1. URL CANONICALIZER  ──────► (SSRF / IP Block Verification)
             │
             ▼
   2. IDENTITY RESOLVER  ──────► (Vanity Slug to Immutable Member URN)
             │
             ▼
  3. SYSTEM SESSION MGR  ──────► (Rotates li_at & derives csrf-token from JSESSIONID)
             │
             ▼
 4. REVERSE-ENGINEERED TRANSPORT ──► (POST to /voyager/api/graphql via JA4 curl_cffi)
             │
             ▼
    5. ENTITY ASSEMBLER  ──────► (Join relational objects, follow URN pointers)
             │
             ▼
   6. CANONICAL NORMALIZER ─────► (Map connected connection degree to 9-State Ontology)
             │
             ▼
  7. OUTBOUND VALIDATOR  ──────► (Draft-07 JSON Schema Enforcer)
             │
             ▼
    [Normalized API JSON]
```

## Key Subsystems & Design Choices

### 1. Strict URL Canonicalization & DNS-SSRF Isolation
Input URLs are treated as untrusted. The `URLCanonicalizer` parses the URL structure, enforces string-match rules on target hostnames (allowing only validated domains like `www.linkedin.com` or `linkedin.com`), and utilizes an isolated custom DNS resolver to prevent Server-Side Request Forgery (SSRF) and DNS rebinding attacks by blocking loopback and private-range IPs (`127.0.0.1`, `10.0.0.0/8`, etc.) prior to connection dispatch.

### 2. Ephemeral Stateless Session Management
Authentication cookies (`li_at` and `JSESSIONID`) are managed by a centralized server-side pool in `SessionManager`. 
* **CSRF Token Derivation:** The custom `csrf-token` header is derived dynamically inside the backend by removing outer double quotes from `JSESSIONID`.
* **Zero Client Leakage:** No session cookies are ever sent to client browsers or stored in frontend variables, ensuring zero credential theft vectors.

### 3. Asynchronous Multi-Endpoint Orchestrator
The application maps a profile query to LinkedIn's private POST GraphQL gateway (`/voyager/api/graphql` using the pre-registered production query ID: `voyagerIdentityDashProfiles.d831bf85b9873ef0228a2bab19781290`). For authenticated V1/V2 viewers, a secondary parallel HTTP GET query is dispatched to `/voyager/api/identity/profiles/{memberUrn}/contactInfo` to fetch private contact handles, consolidating sections asynchronously.

### 4. Relational Entity Assembler (De-denormalization)
The raw JSON returned by LinkedIn's backend is a flat, relational array of JSON-LD entities stored inside an `included` array block. The `EntityAssembler` iterates through this array, matches company URNs to position blocks, maps profile photos back to digitalmediaAssets, and re-assembles the graph structure dynamically on the fly.

### 5. Outbound Validation Gateway
The normalized output is mapped to our exact `PROFILE_SCHEMA.json` and validated using `jsonschema.Draft7Validator`. This acts as an outbound gateway; if an upstream change breaks our internal mapper, the validator blocks delivery and raises an `UpstreamSchemaDriftException` to prevent delivering corrupt JSON structure to API clients.
