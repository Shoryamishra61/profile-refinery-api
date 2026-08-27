# Product Limitations & Operational Boundaries: PhantomBuster
This document evaluates the critical constraints, failure modes, and architectural trade-offs of PhantomBuster's LinkedIn Profile Scraper.

---

## 1. The Hard Two-Job / Two-Education Ceiling
The most severe limitation of PhantomBuster's Profile Scraper is its structural restriction to the **two most recent career positions** and **two most recent education entries**.
* **Why this ceiling exists:** To minimize the risk of account bans. When loading a profile's full history, the LinkedIn client must issue secondary paginated requests to nested sub-endpoints. Programmatically replaying these pagination calls increases the request volume per profile by 3x–5x. To stay safely under rate-limiting and behavioral biometrics sensors, PhantomBuster's Scraper deliberately caps data collection at the initial response payload, discarding historical data.
* **Consequence:** This makes the product highly inadequate for deep talent sourcing, executive recruiting, or comprehensive career-trajectory analysis.

---

## 2. Active Session Dependency & Cookie Decay
* **The "Device Geolocation Stickiness" Rule:** LinkedIn tracks where a session is logged in. If a user uploads a session cookie captured on a residential connection in Paris, and PhantomBuster replays it from a cloud server located in a US-east AWS datacenter, the abrupt geolocation shift triggers an immediate login alert or invalidates the cookie.
* **The User-Agent Decay Loop:** If the user's browser version updates locally, the User-Agent string captured during cookie extraction becomes mismatched with the cloud container's runtime signature. This immediately flags the session, leading to "exit code: 87" (Invalid or Expired Cookie).

---

## 3. Vulnerability to Upstream API Changes
Because LinkedIn's internal Voyager API is undocumented, it is highly unstable:
* **Query ID Rotation:** Modern modular profile cards are retrieved via `/voyager/api/graphql` using hardcoded POST hashes called `queryId` values. When LinkedIn’s frontend teams rotate these hashes during routine deployments, PhantomBuster's hardcoded queries immediately fail until their developers manually reverse-engineer the updated hashes.
* **Header and Telemetry Drift:** LinkedIn constantly shifts the required format of headers. For example, if the derivation of the `csrf-token` from `JSESSIONID` changes or if the platform introduces mandatory client-side telemetry payloads (such as the base64-encoded `/li/track` queue), the scraper's direct requests appear as anomalous naked API hits, resulting in instant account bans.

---

## 4. Cloud Sandboxing and Sync Overhead
* **No Real-Time Synchronous Execution:** PhantomBuster is built as an asynchronous worker scheduler. A user must configure a job, queue it, wait for container spin-up, execute, and retrieve results from S3. This introduces severe latency (minimum 1–2 minutes of environment overhead even for a single profile look-up), making it completely useless for real-time synchronous enrichment APIs.
* **Storage Latency:** Results files are combined and synced back to S3 upon container teardown. If a container crashes or is abruptly killed, progress data since the last sync is lost.