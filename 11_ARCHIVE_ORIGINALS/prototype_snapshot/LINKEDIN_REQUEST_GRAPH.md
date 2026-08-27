# System Specification: LinkedIn Profile Request Graph
**Author:** Protocol Reverse-Engineering & Systems Architecture Group  
**Status:** Pre-Design Protocol Specification  
**Focus:** Pure HTTP wire-level communication with LinkedIn's internal serving layer.

---

## 1. Topological Request Graph Overview
A pure HTTP-native LinkedIn profile extraction service cannot rely on visual page rendering or DOM traversal [112]. Instead, it must reconstruct the candidate profile by tracing and replaying the exact network requests that the first-party LinkedIn single-page application (SPA) executes during a logged-in session [112, 113].

The request graph originates from a raw, user-provided public profile URL (e.g., `https://www.linkedin.com/in/vanity-slug`) and maps through a sequence of identity resolution, session verification, parallel sub-resource fetches, and entity consolidation steps [113, 115, 304].

### Request Graph Flow Diagram
```
              [Input Public Profile URL]
                          │
                          ▼
            Step 1: Identity Resolution
         (Resolve Vanity Slug to Member URN)
                          │
       ┌──────────────────┴──────────────────┐
       ▼                                     ▼
  Path A (GraphQL)                     Path B (REST Legacy)
POST /voyager/api/graphql            GET /voyager/api/identity/profileView/{slug}
  (queryId: DashProfiles)              (Returns legacy unified payload)
       │                                     │
       ▼                                     ▼
 [Extract Member ID]                  [Extract Member ID]
  (urn:li:member:123)                  (urn:li:member:123)
       │                                     │
       └──────────────────┬──────────────────┘
                          │
                          ▼
            Step 2: Parallel REST Fetches
         (Querying Sub-Sections of the Profile Graph)
       ┌──────────────────┼──────────────────┬──────────────────┐
       ▼                  ▼                  ▼                  ▼
 GET .../contactInfo  GET .../skills     GET .../languages  GET .../entities/companies/{id}
 (Emails, Phones)     (Paginated List)   (Proficiencies)    (Corporate Profile Enrichment)
       │                  │                  │                  │
       └──────────────────┼──────────────────┴──────────────────┘
                          │
                          ▼
            Step 3: Response Reconstruction
         (Deduplicate & Bind Relational Entities)
                          │
                          ▼
            Step 4: Stable Normalization
         (Convert Multi-Locale to Flat JSON)
                          │
                          ▼
               [Structured JSON Output]
```

---

## 2. Core Identity Resolution (Vanity URL Slug to Member ID)
The incoming vanity URL must be parsed to extract the unique alphanumeric slug [141, 198]:
* URL Pattern: `https://www.linkedin.com/in/{vanity-slug}/` [113, 213]
* Trailing query parameters (e.g., `?utm_source=...` or tracking hashes) must be systematically stripped [141].

To fetch any profile data, the vanity slug must be mapped to an immutable, internal LinkedIn **Member ID** (typically represented as an URN like `urn:li:member:123456789` or `urn:li:fsd_profile:123456789`) [120, 213, 309].

There are two distinct paths to resolve this mapping without a browser:

### Path A: Modern GraphQL Resolution (Dash API Gateway)
The client issues a POST request to the consolidated GraphQL gateway [307]:
* **Endpoint:** `https://www.linkedin.com/voyager/api/graphql` [307]
* **Method:** `POST` [307]
* **Payload:** Uses the pre-registered query ID for Dash Profiles [307, 332]:
  ```json
  {
    "query_params": {
      "variables": "(memberIdentity:tom-quirk)",
      "queryId": "voyagerIdentityDashProfiles.d831bf85b9873ef0228a2bab19781290"
    },
    "method": "GET",
    "url": "https://www.linkedin.com/voyager/api/graphql"
  }
  ```
The response's `included` array contains a flat collection of objects [16, 415]. The client scans this list for elements of `$type: "com.linkedin.voyager.dash.identity.Profile"` to extract the unique `entityUrn` (e.g., `urn:li:fsd_profile:ACoAAAtp-4U`) and numerical member ID [120, 410, 412].

### Path B: Legacy REST Resolution
* **Endpoint:** `https://www.linkedin.com/voyager/api/identity/profileView/{vanity-slug}` [81, 113]
* **Method:** `GET` [171, 310]
* **Payload:** Returns a monolithic JSON payload containing a nested `miniProfile` block with the stable URN [81, 120].
* **Status:** This endpoint is deprecated and frequently throws `HTTP 410 Gone` to unauthorized clients, but remains active as an fallback layer for older sessions [307, 310].

---

## 3. Parallel REST Sub-Resource Fetches
Once the stable **Member URN** is resolved, the main profile gateway payload often only returns a subset of elements (the "Top Card" and the first two positions/schools) due to server-side optimization and projections [31, 310]. To retrieve the full professional profile, the client must trigger parallel HTTP GET calls against dedicated sub-resource REST endpoint families [31]:

1. **Positions & Experience History:**
   * **Endpoint:** `https://www.linkedin.com/voyager/api/identity/profiles/{memberId}/positions` [414, 415]
   * **Purpose:** Returns the complete work history array, bypassing the standard two-job truncation [120, 415].
2. **Education Details:**
   * **Endpoint:** `https://www.linkedin.com/voyager/api/identity/profiles/{memberId}/educations` [404, 413]
   * **Purpose:** Returns complete educational background, including degrees, school URNs, and date ranges [120, 404].
3. **Skills & Endorsements:**
   * **Endpoint:** `https://www.linkedin.com/voyager/api/identity/profiles/{memberId}/skills` [422, 423]
   * **Purpose:** Returns full list of skills, each decorated with `endorsementCount` and viewer-specific flags [422].
4. **Licenses & Certifications:**
   * **Endpoint:** `https://www.linkedin.com/voyager/api/identity/profiles/{memberId}/certifications` [120, 403]
   * **Purpose:** Returns certifications with issuer, credential IDs, and validation URLs [120, 403].
5. **Languages:**
   * **Endpoint:** `https://www.linkedin.com/voyager/api/identity/profiles/{memberId}/languages` [120, 143]
   * **Purpose:** Returns self-declared languages and proficiency enums [143].
6. **Volunteer Work & Honors:**
   * **Endpoints:** `/profiles/{id}/volunteerExperiences` and `/profiles/{id}/honors` [120, 502]
7. **Contact Information:**
   * **Endpoint:** `https://www.linkedin.com/voyager/api/identity/profiles/{memberId}/contactInfo` [113, 310]
   * **Required Input:** Stable Member ID. Returns phone numbers, instant messaging links, and verified emails [25, 113, 310].
   * **Viewer Dependency:** Returns email and phone only if the authenticated account has a 1st-degree connection or if explicit consent is established [204, 310].

---

## 4. REST Sub-Resource Query Projections (Rest.li Projections)
LinkedIn uses Rest.li 2.0 query projections via the custom `decoration` and `fields` URL parameters to request nested elements and limit payload sizes [91, 269].

To fetch nested school or company logos, we request recursive expansion using the asterisk-tilde (`*~`) operator [91, 130]:
`/voyager/api/organization/companies?decoration=(name,groups*~(entityUrn,largeLogo,groupName,memberCount))` [91, 130]

This expression requests the company's name and recursively expands the `groups` array to return only the `entityUrn`, `largeLogo`, and `groupName` for each group [91, 130].

---

## 5. Session and Protocol Header Requirements
Every HTTP request issued against Voyager must include a strict set of session cookies and custom headers, matching the exact browser session state to avoid security check failures [193, 309].

### Required Cookie Jar
* **`li_at` Cookie:** Cryptographically signed JWT token carrying session auth [20, 224].
* **`JSESSIONID` Cookie:** CSRF session cookie. **Crucial Formatting Rule:** Must be wrapped in double quotes in the cookie jar [19, 101]:
  `JSESSIONID="ajax:1812219885785541610"` [309, 310]

### Required Request Headers
* **`csrf-token` Header:** Derived by extracting the alphanumeric string inside the double quotes of the `JSESSIONID` cookie [19, 404, 310]:
  `csrf-token: ajax:1812219885785541610` [309, 310]
  *If this header value does not match the cookie value exactly, the server gatekeeper returns a `403 CSRF check failed` response* [193, 310].
* **`X-RestLi-Protocol-Version`:** Must be set to `2.0.0` [171, 310].
* **`Accept`:** Must be configured as `application/vnd.linkedin.normalized+json+2.1` to force the server to return highly structured, machine-readable JSON rather than generic HTML embeds [17, 310].
* **`User-Agent`:** Must match the exact user agent associated with the captured session to prevent client-fingerprint desynchronization blocks [28, 105].
