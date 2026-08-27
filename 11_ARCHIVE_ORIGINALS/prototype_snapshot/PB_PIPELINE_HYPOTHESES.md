# Observable Pipeline Hypotheses: PhantomBuster Profile Scraper
Because PhantomBuster’s cloud extraction runs inside private Docker sandboxes, we must treat its exact execution pipeline as a black box. This document establishes an observable pipeline hypothesis mapping the exact stages from raw input URL to normalized JSON, labeling each stage based on the strength of our evidence.

---

## The Observable Pipeline Map

```
[Input URL] 
     │
     ▼
1. IDENTITY RESOLUTION ──────────────────────────► [VERIFIED]
     │
     ▼
2. AUTHENTICATED REQUEST CONTEXT ────────────────► [VERIFIED]
     │
     ▼
3. DIRECT ENDPOINT REPLAYING ────────────────────► [STRONG INFERENCE]
     │
     ▼
4. MULTIPLE PROFILE-SECTION RESPONSES ──────────► [STRONG INFERENCE]
     │
     ▼
5. RESPONSE & ENTITY RECONSTRUCTION ─────────────► [STRONG INFERENCE]
     │
     ▼
6. DATA NORMALIZATION & STRUCTURING ─────────────► [VERIFIED]
     │
     ▼
[Normalized JSON Output]
```

---

## Detailed Evaluation of Pipeline Stages

### Stage 1: LinkedIn Identity Resolution
* **Description:** The scraper accepts a vanity URL (e.g., `https://www.linkedin.com/in/vanity-slug`) and must resolve this to an immutable internal member identifier (URN format: `urn:li:member:123456789`).
* **Evidence Label:** **VERIFIED**
* **Supporting Fact:** PhantomBuster outputs both `linkedinProfileSlug` (the vanilla slug) and `linkedinProfileUrn` (the unique numeric URN) in every successful scrape. It must resolve this mapping at the start of execution.

---

### Stage 2: Authenticated Request Context
* **Description:** The cloud container instantiates a secure session using the user-provided `li_at` and `JSESSIONID` cookies. It derives a custom `csrf-token` header directly from the browser's `JSESSIONID` cookie (removing the double quotes and matching the alphanumeric string) to bypass LinkedIn's strict gatekeeper validation.
* **Evidence Label:** **VERIFIED**
* **Supporting Fact:** Both our previous reverse-engineering traces and public open-source implementations (e.g., `nsandman/linkedin-api` and `open-linkedin-api`) confirm that raw HTTP headers must include the exact derived `csrf-token` matching the `JSESSIONID` cookie to avoid immediate HTTP 403 Forbidden blocks.

---

### Stage 3: Direct Endpoint Replaying
* **Description:** To achieve speeds of ~30 minutes per 1,000 profiles (an incredible ~1.8 seconds per profile), PhantomBuster's Scraper **does not visit the profile**. It bypasses headless page loading and instead directly replays HTTP GET requests against LinkedIn's private Voyager REST API or POST requests against the GraphQL gateway (`/voyager/api/graphql`).
* **Evidence Label:** **STRONG INFERENCE**
* **Supporting Fact:** PhantomBuster's official tutorials state that the Profile Scraper "does not visit" the profile and "relies on API calls," meaning it registers zero profile-view notifications. Headless browsers cannot load, scroll, and parse a page in 1.8 seconds. This speed is mathematically impossible without direct API-level JSON replaying.

---

### Stage 4: Multiple Profile-Section Responses
* **Description:** The scraper issues focused queries requesting the profile view, contact information, and (if toggled) the company entities page. It queries specific sub-sections using Rest.li decoration projection masks (e.g., `(positions*~(companyName,title)))`) to fetch only the current and previous employment elements.
* **Evidence Label:** **STRONG INFERENCE**
* **Supporting Fact:** The hard, un-paginated ceiling of exactly two positions matches the default response length of the initial `/voyager/api/identity/profileView/{slug}` or GraphQL profile cards payload. Pulling further history requires paginating nested endpoints (such as `/voyager/api/identity/profiles/{id}/positions`), which PhantomBuster deliberately skips in this product to minimize execution footprints and account risks.

---

### Stage 5: Response & Entity Reconstruction
* **Description:** The raw JSON payloads returned from Voyager contain relational pointers (URN relationships, e.g., company pointers mapping to `urn:li:company:98765`). The scraper's backend parses these references, follows the entity graph to pull company data, and matches them to the candidate's profile.
* **Evidence Label:** **STRONG INFERENCE**
* **Supporting Fact:** In the output schema, company data is enriched with website and industry strings *only* when the "Enrich company data" behavior checkbox is active, proving that secondary entity-resolution calls are performed to follow company URN pointers.

---

### Stage 6: Data Normalization & Structuring
* **Description:** The parsed raw nested JSON objects are mapped to flat, standardized keys (e.g., mapping `geoLocationName` to `location`, or `summary` to `linkedinDescription`). The pipeline converts these entities into the final exportable CSV/JSON schema.
* **Evidence Label:** **VERIFIED**
* **Supporting Fact:** The output fields are highly standardized across hundreds of different runs and are explicitly structured to be compatible with CRM systems (HubSpot, Salesforce) and Google Sheets.