# Direct Endpoint Research Map: Undocumented LinkedIn REST & GraphQL Interfaces
**Author:** Protocol Reverse-Engineering Task Force  
**Status:** Pre-Design Technical Specifications  
**Focus:** Pure HTTP wire-level communication with LinkedIn internal serving layer (Voyager & Dash).

---

## 1. Authentication & Session Context Coupling
A secure, authenticated session context must be established and attached to every HTTP request. This is achieved by binding three key state variables in the headers and cookies of the client [22, 171]:

### A. The Aligned Cookie Jar
* **`li_at` Cookie:** The primary session bearer token, represented as a cryptographically signed JSON Web Token (JWT) [22, 224]. 
* **`JSESSIONID` Cookie:** The CSRF session state cookie. It must be wrapped in double quotes in the cookie jar [19, 101]:
  `JSESSIONID="ajax:XXXXXXXXXXXXXXXXXXX"`

### B. CSRF Derivation Code Path
The custom `csrf-token` header is derived directly from the `JSESSIONID` cookie value. The client must extract the alphanumeric string inside the double quotes (stripping the quotes entirely) [19, 404]:
```python
# Technical CSRF derivation implementation
raw_jsession = cookie_jar.get("JSESSIONID")  # e.g., '"ajax:812219885785541610"'
csrf_token = raw_jsession.replace('"', '')    # e.g., 'ajax:812219885785541610'
headers["csrf-token"] = csrf_token
```
If the custom `csrf-token` header does not match the cookie value exactly, the server gatekeeper returns an immediate `HTTP 403 Forbidden` response [19, 404].

### C. Standard Protocol Configuration Headers
To mimic a modern browser client and comply with Rest.li schema requirements, the following headers are mandatory for every outbound query [19, 171]:
* `X-RestLi-Protocol-Version: 2.0.0` [171, 346]
* `User-Agent`: Must match the exact user agent of the browser session from which the cookies were captured [28, 105].
* `Accept`: `application/vnd.linkedin.normalized+json+2.1` (to return highly structured, normalized JSON models) [19].

---

## 2. Endpoint Catalog & Specifications

### A. Modern Profile Gateway (GraphQL/Dash API)
The web client primarily loads profile sections dynamically using parallel queries routed through a consolidated GraphQL gateway [402, 1011]:
* **URL:** `https://www.linkedin.com/voyager/api/graphql` [402, 924]
* **HTTP Method:** `POST` [402, 924]
* **Request Payload Structure:**
  The request payload is structured as a JSON document containing a static, pre-registered `queryId` and a serialized Rest.li representation of variables [114, 924]:
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
  *(Note: Specific queryIds are extracted dynamically from production JS bundles or intercepted via network traces) [403, 439].*

### B. Legacy Profile Endpoint
Historically used to retrieve a unified full-profile document [401]:
* **URL:** `https://www.linkedin.com/voyager/api/identity/profileView/{vanity_name}` [81, 170]
* **HTTP Method:** `GET` [171, 405]
* **Stability Level:** Extremely low. Frequently returns `HTTP 410 Gone` to unauthorized requests or external clients, as LinkedIn has transitioned to the server-driven modular UI model [7, 402].

### C. Contact Information Endpoint
Highly stable endpoint returning user-specific communication links [255, 405]:
* **URL:** `https://www.linkedin.com/voyager/api/identity/profiles/{profileId}/contactInfo` [240, 405]
* **HTTP Method:** `GET` [255, 405]
* **Payload:** Standard URL parameters. Returns emails, phone numbers, and connected instant messaging handles [25, 405].

### D. Company Entity Mapping Endpoint
Used to resolve relational company references found within the profile work experience [405]:
* **URL:** `https://www.linkedin.com/voyager/api/entities/companies/{companyId}` [389, 390]
* **HTTP Method:** `GET` [389]
* **Payload Parameters:** Standard decoration parameters (`decorationId`) to expand fields like employee count, industries, and headquarters [91, 389].

---

## 3. The Rest.li 2.0 Protocol Specifications
LinkedIn’s private client relies extensively on the **Rest.li Protocol (V2.0.0)**, which defines type-safe data serialization and projection protocols [83, 107].

### A. URL-Encoded Key-Value Representation
In Rest.li 2.0, objects passed in URLs or query strings are represented as parentheses-wrapped key-value maps with colon separators [369, 816]:
`(key1:value1,key2:value2)`

### B. Array Notation
Arrays must be encoded using the explicit `List(...)` constructor [370, 818]:
`List(item1,item2,item3)`

### C. Decoration & Projection Masks
Rest.li allows client-side field selection masks (similar to GraphQL selectors) passed via the `decoration` parameter [91, 172]. Relational collections are expanded using the asterisks-tilde (`*~`) operator [91, 172]:
`/voyager/api/organization/companies?decoration=(name,groups*~(entityUrn,largeLogo,groupName,memberCount))`
This requests the organization's name and recursively expands the `groups` collection, returning only the `entityUrn`, `largeLogo`, and `groupName` of each group [91].

---

## 4. Discovery & Schema Reverse-Engineering Protocol
Because these APIs are private, the extraction service must implement a structured discovery protocol to adapt to upstream changes:
1. **The HTML pre-load `<code>` Scan:** When a profile is loaded in a browser, LinkedIn bootstrap servers inject structured data into hidden `<code>` blocks [82, 1000]. The discovery module can scan the static source code of an authenticated page load for elements matching [82, 1000]:
   `<code style="display: none" id="datalet-bpr-guid-XXXX">`
2. **Request Mapping:** Inside these blocks, a structured JSON document defines the relative target URI mapped to the page view section [83, 1000]:
   `{"request":"/voyager/api/identity/profiles/{slug}/profileView", "status":200, "body":"bpr-guid-XXXX"}`
   The value of the `request` key reveals the exact relative endpoint and required query parameters [83, 1000].
