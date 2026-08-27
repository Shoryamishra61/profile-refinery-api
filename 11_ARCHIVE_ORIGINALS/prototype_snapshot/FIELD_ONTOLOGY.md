# Field Status Ontology & Semantic Targets
**Role:** Principal Evaluation Scientist, Data-Quality Researcher, and API Schema Architect  
**Status:** Canonical Specifications

---

## 1. The Semantic Target
Every data extraction from a LinkedIn profile must be framed according to the formal semantic definition:

$$\text{Target} = f(P, V, T)$$

Where:
* **$P$ (Target Profile):** The specific individual entity whose profile is being requested.
* **$V$ (Viewer Connection State):** The session authorization level accessing $P$. This degree of connection directly controls visibility boundaries:
  * **$V_1$ (1st-Degree Connection):** Full visibility into personal emails, phone numbers, and direct contact details.
  * **$V_2$ (2nd-Degree Connection):** Gated visibility; contact info is typically restricted to shared links, but full name and career sections remain open.
  * **$V_3$ (3rd-Degree Connection / Out of Network):** Limited profile views. Surnames may be reduced to initials (e.g., "John S."), and specific sub-sections are truncated.
  * **$V_0$ (Logged Out Public):** The strict public-index view. Most metadata is masked or entirely absent, subject to the user's granular off-platform privacy preferences.
* **$T$ (Point in Time):** The precise Unix epoch timestamp of observation. This parameters controls data currency and expires media CDN tokens.

We must reject the naive assumption that a profile has a single static representation. A field value is only defined when bound to $P$, $V$, and $T$.

---

## 2. Granular Field Status Classification (9-State Ontology)
To enforce absolute accuracy and prevent the systemic parsing silent failures found in competitors like PhantomBuster, every field in the `PROFILE_SCHEMA` is wrapped in a strict status block. The field must resolve to one of nine mutually exclusive statuses:

| Status Code | Description | Semantic Cause | Correct API Handling |
| :--- | :--- | :--- | :--- |
| `present` | Data was successfully parsed and populated. | Field exists on the target profile and was fetched successfully. | Return populated `value` + full `provenance` metadata. |
| `not_provided` | Field is empty on the profile. | The user did not fill out this section (e.g., they have no "about" text). | Return `value: null` with status `not_provided`. No further request attempts. |
| `not_visible_to_viewer` | Gated due to viewer degree $V$. | The viewer's connection degree lacks permission (e.g., viewing an email as a $V_3$ connection). | Return `value: null` with status `not_visible_to_viewer`. Differentiate from omission. |
| `not_available_from_endpoint` | Endpoint limitation. | The active endpoint or selected decoration projection mask does not carry this data node. | Return `value: null` with status `not_available_from_endpoint`. |
| `not_loaded` | Deliberate client bypass. | The programmatic engine bypassed loading this section (e.g., skip paginating volunteer history to save rate-limit). | Return `value: null` with status `not_loaded`. |
| `upstream_failed` | LinkedIn network error. | LinkedIn returned a server-side error (e.g., HTTP 500, 429, or 404) for a modular sub-query. | Set status `upstream_failed`. Raise alert if critical, bubble up fallback empty block. |
| `parser_failed` | Local processing code broke. | Data was fetched, but structural schema drift or unexpected data shapes broke the extraction code. | Log traceback, capture raw schema, set status `parser_failed`. Run regression test. |
| `stale_or_expired` | Expired CDN signature. | The resource contains data, but its validation check has failed (e.g., an image URL past its CDN expiration token). | Flag status `stale_or_expired`. Initiate dynamic session token update or re-query. |
| `unknown` | Indeterminate state. | Unmapped processing error occurred. | Default fallback. Monitor for unhandled code exceptions. |

---

## 3. Strict Provenance Architecture
Every extracted data field must be auditable. A schema cannot be greenlit for production without exposing complete provenance records containing:
* **`source_operation`:** The exact network transaction and endpoint used to retrieve the field (e.g., `POST https://www.linkedin.com/voyager/api/graphql` utilizing `queryId: voyagerIdentityDashProfiles.d831bf85b9873ef0228a2bab19781290`).
* **`observation_time`:** The BCP-47 ISO-8601 UTC timestamp of the request.
* **`raw_entity_reference`:** The specific platform URN identifier associated with the record (e.g., `urn:li:fsd_profilePosition:(ACoAAAtp-4U,129883556)`).
* **`normalization_performed`:** A explicit summary of local parsing transformations (e.g., `"Rest.li Multilocale extraction; parsed English locale, stripped nested carriage returns"`).
* **`schema_version`:** The precise semantic version of the targeting schema.
