# Assumption Register: Protocol, Session & Network Assumptions

This document registers the non-obvious engineering assumptions, token lifetimes, edge constraints, and verification steps that govern the programmatic, browser-less LinkedIn Profile Extraction API. These assumptions serve as the baseline for system reliability and maintenance.

---

## 1. Authentication & Session Lifetimes

### Assumption: `li_at` Cookie Decay Profile
* **Definition:** The `li_at` session cookie is assumed to have a typical lifespan of 90 to 180 days under normal browser usage. However, under direct, raw programmatic HTTP replaying, we assume that high query volumes lacking corresponding client-side telemetry (mouse movements, scrolls) trigger automatic, server-side session invalidation within 500 to 1,000 queries.
* **Verification:** Monitor session statuses dynamically in the `SessionManager` pool. Any response returning HTTP 401 must flag the target cookie immediately as `unhealthy`.

### Assumption: `csrf-token` Header Suffix Aligns with `JSESSIONID`
* **Definition:** The `csrf-token` header used to satisfy LinkedIn's gatekeeper must align exactly with the value inside the `JSESSIONID` cookie (excluding outer double quotes). We assume this binding is checked symmetrically at LinkedIn’s Edge Router.
* **Verification:** Unit tests extract `JSESSIONID` and confirm derived `csrf-token` matches the expected string suffix.

---

## 2. API Rate Limiting & Account Safety Limits

### Assumption: Safe Extraction Ceilings (Direct API)
* **Definition:** Unlike browser-based scraping which can trigger blocks quickly due to high resource footprints, raw HTTP endpoint replaying is highly efficient. However, to evade account restrictions, we assume a safe operational ceiling of **50 to 100 profile extractions per account per day** for standard (non-premium) sessions.
* **Verification:** Rate-limiting queues on our API entrypoint enforce bounding per session key, staggering parallel requests with random jitter.

---

## 3. Network Signatures & Client Fingerprinting

### Assumption: Edge WAF TLS Verification (JA4)
* **Definition:** We assume that LinkedIn's network-edge Web Application Firewall (WAF) checks incoming TLS handshakes, cipher suites, and TCP window frames to verify client authenticity. If standard libraries like `requests` or `urllib3` are used with their default headers and ciphers, the connection will be blocked before routing.
* **Verification:** In live production mode, the transport adapter simulates Chrome-specific TLS ciphers, ALIC protocols, and custom header ordering to achieve JA4 parity.

---

## 4. Viewer Connection Degrees & Visible Schemas

### Assumption: Visibility Boundaries ($V_1$ vs. $V_2$ vs. $V_3$)
* **Definition:** We assume that the profile content returned by the server-driven UI layer is tightly coupled to the degree of connection between the viewer account (V) and the candidate (P).
  * **$V_1$ (First Degree):** Access to full experience, contactInfo, full names, and images.
  * **$V_2$ (Second Degree):** Experience and education present; contactInfo restricted.
  * **$V_3$ (Out of Network):** Surname truncated, about and pictures hidden; experience hidden.
* **Verification:** The `CanonicalNormalizer` maps connection degrees to proper `not_visible_to_viewer` status flags, ensuring the API behaves deterministically rather than crashing on missing fields.

---

## 5. Media URL & CDN Image Token Decay

### Assumption: CDN Image URL Timestamps
* **Definition:** LinkedIn profile and background image URLs are served via a Content Delivery Network (CDN) with an embedded signature parameter `expiresAt` or `e=`. We assume these tokens expire exactly at the epoch timestamp specified, resulting in broken image rendering for downstream clients if accessed post-expiry.
* **Verification:** The API normalizer checks the expiration parameter against the current system time. If expired, it flags the status as `stale_or_expired`, prompting the caller to re-fetch or triggering a sliding-window session re-query.
