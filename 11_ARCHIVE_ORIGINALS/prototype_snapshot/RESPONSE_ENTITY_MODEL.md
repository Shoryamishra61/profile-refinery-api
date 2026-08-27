# Design Specification: Response Entity and Relational Reconstruction Model
**Author:** API Archaeology & Knowledge Representation Team  
**Status:** Pre-Design Technical Specifications  
**Focus:** Unpacking and normalizing flat-JSON relational payloads returned by Rest.li and GraphQL.

---

## 1. Unpacking LinkedIn's Relational JSON-LD / Included Payloads
LinkedIn’s private client architecture is optimized to prevent data duplication over HTTP [102, 125]. When a client queries the `/voyager/api/graphql` POST gateway or a REST endpoint, the server returns a consolidated JSON document consisting of two primary blocks [16, 415]:

```json
{
  "data": {
    "identityDashProfilesByMemberIdentity": {
      "*elements": [
        "urn:li:fsd_profile:ACoAAAtp-4U"
      ],
      "$type": "com.linkedin.voyager.dash.identity.ProfilesCollection"
    }
  },
  "included": [
    {
      "entityUrn": "urn:li:fsd_profile:ACoAAAtp-4U",
      "firstName": "Jane",
      "lastName": "Doe",
      "headline": "Distributed Systems SRE",
      "$type": "com.linkedin.voyager.dash.identity.Profile"
    },
    {
      "entityUrn": "urn:li:fs_position:(urn:li:fs_member:1234,5678)",
      "title": "Senior SRE",
      "companyName": "Contoso",
      "*company": "urn:li:fs_company:98765",
      "$type": "com.linkedin.voyager.dash.identity.Position"
    }
  ]
}
```

### The Architectural Problem
The data is **completely flat**. The hierarchical structure of a profile (Jane Doe $ightarrow$ experiences array $ightarrow$ company profiles) is modeled as a set of relational pointers in the `included` array [35, 410].

Our hosted API extraction layer must parse this flat array, reconstruct the parent-child relationships, and output a clean, nested JSON schema [36, 125].

---

## 2. Platform URN Parsing and Dereferencing
All entities inside the `included` block are identified by a unique **Uniform Resource Name (URN)** [213, 310]. The hosted extraction engine must parse these URN structures to build relational mappings:

* **Profile URN:** `urn:li:fsd_profile:ACoAAAtp-4U` [410, 412]
* **Company URN:** `urn:li:fs_company:98765` [310, 414]
* **Education URN:** `urn:li:fs_education:54321` [413]
* **digitalmediaAsset URN:** `urn:li:digitalmediaAsset:C4D00AAAAbBC` [210, 221] (used to map and resolve expiring media download links [235, 247]).

### Mapping Algorithm Steps
1. **Initialize Indexes:** Scan the raw response and build hash maps of objects indexed by their `entityUrn` [410].
2. **Follow Pointers:** For the main profile object, identify relational keys (e.g., `*elements` mapping list keys to URNs) [410, 415].
3. **Dereference Company Profile:** In a work experience object, resolve the pointer `*company` (e.g., `urn:li:fs_company:98765`) by fetching the matching company details from our company hash map [310, 414].
4. **Build Hierarchical Lists:** Append the dereferenced children arrays to the parent candidate profile before executing the final normalization step [36, 144].

---

## 3. Resolving Multi-Locale Text Structures
LinkedIn stores text fields as localized objects supporting international character sets [63, 236]:

```json
{
  "firstName": {
    "localized": {
      "en_US": "Jane",
      "fr_FR": "Jeanne"
    },
    "preferredLocale": {
      "country": "US",
      "language": "en"
    }
  }
}
```

### Normalization Logic
To maintain a clean public API, our service must compress these structures into simple key-value string pairs [144, 156]:
1. Check `preferredLocale` keys to identify the target country and language (defaulting to `en_US` if missing or unavailable) [210, 221].
2. Extract the string value mapped to that preferred locale [210, 221].
3. Map the extracted text to flat schema keys (`firstName` and `lastName`) [144].

---

## 4. Expire-Aware Profile Media URLs
Profile photos and background banners are returned as digital media asset references [210, 221]:

```json
{
  "profilePicture": {
    "croppedImage": {
      "downloadUrl": "https://media.licdn.com/dms/image/v2/example/profile-pic",
      "downloadUrlExpiresAt": 1762992000000
    }
  }
}
```

### The Expiry Threat
The CDN download URLs carry hardcoded, short-lived authentication signatures [235, 236].
* **System Policy:** If a cached profile’s `downloadUrlExpiresAt` timestamp is less than the current epoch, the cache must be invalidated, and a fresh call must be replayed against the LinkedIn CDN/API gateway to obtain working image URLs [235, 247].
