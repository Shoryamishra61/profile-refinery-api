# Data Specification: Profile Identifier and Identity Resolution Model
**Author:** Distributed-Systems Research Group  
**Status:** Pre-Design Data Specification  
**Focus:** Mapping mutable public URLs to immutable database primary keys.

---

## 1. Mutable Slugs vs. Immutable Platform Keys
In LinkedIn's technical architecture, a profile can be accessed via different keys [144, 326]. Managing these identifiers is critical to preventing duplicate database entries, tracking career changes, and ensuring cache consistency [144, 326].

| Identifier Type | Format | Mutability | Scoping | Primary Use Case |
| ------ | ------ | ------ | ------ | ------ |
| **Vanity URL Slug** | String (e.g., `janedoe`) [113, 213] | **High.** Users can freely change their custom URL slug at any time [144]. | Global (Public Web) [113, 213] | Human routing, SEO indexing, and initial user input entry [141, 180]. |
| **Hashed Member ID** | Cryptographic hash (e.g., `ACoAAB1a2b3c4d`) [144] | **Stable.** Immutable for the lifetime of the member account [144]. | Global (Public Web/API) [144] | Ideal stable primary key for deduplication and relational indexing [144, 326]. |
| **Numeric Person ID** | Unsigned Integer (e.g., `145991517`) [252] | **Stable.** Immutable for the account [252]. | Scoped strictly to individual Developer Portal applications [213]. | Official 3-legged API calls [213, 229]. *Using it across apps throws HTTP 404* [213]. |
| **Platform URN (Rest.li)** | URN String (e.g., `urn:li:member:123456789`) [120, 213] | **Absolute.** Permanent platform-level database key [213]. | Platform-wide internal scope [213, 326]. | Downstream REST resource queries, relational joins, and database indexes [213, 326]. |

---

## 2. Vanity URL Slug Mutability & Aliasing
Because custom slugs are controlled by the user, a single platform identity can experience "slug mutations" [144, 328]:
1. **The Renaming Event:** A user renames their slug from `jane-doe` to `jane-doe-phd` [144, 328].
2. **The Orphaned Slug:** The old slug `jane-doe` is released back to the platform's pool and can be claimed by a different user [328, 330].
3. **Database Corruption:** If an extraction API treats `publicUrl` as the primary key, it will create two separate database profiles for the same human, and eventually overwrite the first profile with the second human's data [144, 330].

**System Policy:** The extraction service must strictly use the unique platform URN (`urn:li:member:...` or `urn:li:fsd_profile:...`) or the hashed public URL as the primary database key [144, 328].

---

## 3. Resolving Vanity URLs to Platform URNs (No Browser)
To resolve an input URL without loading a heavy browser, the hosted service replays the request against the internal Voyager API to capture the identity mappings inside the JSON payload [304, 307]:

### Step 1: URL Parsing and Canonicalization
Normalize the input URL to extract the slug:
* Input: `https://www.linkedin.com/in/tom-quirk?trk=profile-badge` [141]
* Output: Alphanumeric slug `tom-quirk` [113, 213]

### Step 2: The Gateway Identity Query
Replay a GET request to the Voyager profile gateway, using active session cookies (`li_at` and `JSESSIONID`) with the `X-RestLi-Protocol-Version: 2.0.0` header [114, 309]:
`GET https://www.linkedin.com/voyager/api/identity/profiles/tom-quirk/profileView` [113, 309]

### Step 3: Extracting Identifiers from the Entity Graph
The response contains an array of JSON objects inside the `included` key [16, 415]. The client traverses this array to parse:
1. **The Core Member Object:** Locates the object matching `$type: "com.linkedin.voyager.dash.identity.Profile"` (or similar legacy type) [412, 416].
2. **Extracting the URN:** The `entityUrn` property contains the immutable platform identifier (e.g., `urn:li:fsd_profile:ACoAAAtp-4U`) [410, 412].
3. **Extracting the Hash ID:** The `publicIdentifier` or hashed URL identifier (e.g., `ACoAAAtp-4U`) is extracted [141, 412].
4. **Resolution Caching:** The mapping `tom-quirk` $ightarrow$ `urn:li:fsd_profile:ACoAAAtp-4U` is written to a key-value store with an expiry of 24 hours to prevent redundant lookup costs [148, 174].

---

## 4. Viewer-Specific ID Gating
While platform keys are immutable, their visibility in API responses depends entirely on the session viewer's state and connection degree [204, 330]:
* **1st-Degree Connections:** Replaying the request yields full name, complete URN, and contact-info identifiers [310, 312].
* **2nd/3rd-Degree Connections:** Yields name and URN, but contact-info endpoints return partial schemas or explicit auth blocks [310, 312].
* **Out-of-Network/Private Profiles:** The gateway returns highly restricted elements, and mini-profile objects contain generic placeholders instead of stable platform keys [16, 329].
