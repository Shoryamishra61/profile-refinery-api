# P0 Engineering Reading Order: Pure Reverse-Engineered HTTP Client Implementation
**Target Audience:** Core Protocol Engineers & Systems Integration Team  
**Focus:** Executing a browser-less HTTP extraction layer utilizing the private Voyager/Dash API.

This roadmap categorizes and sequences the supplied source corpus to provide the fastest path to a production-ready, un-instrumented HTTP extraction gateway.

---

## Phase 1: Core Protocol Mechanics (Rest.li & Pegasus)
Before writing any transport logic, engineers must understand LinkedIn's underlying serialization and query framework.
1. **Rest.li Protocol (V2.0.0 Spec):**
   * *Relevance:* Direct mapping of parenthetical key-value URL queries, list notations, and standard request headers.
   * *Core Concepts:* Key-value mapping: `(key:value)`, array representation: `List(a1,a2)`, and protocol headers (`X-RestLi-Protocol-Version: 2.0.0`, `X-RestLi-Method`).
2. **Rest.li Server Architecture User Guide:**
   * *Relevance:* Detailed explanation of the non-blocking asynchronous Netty architecture and the `ParSeq` execution engine. Understands how parallel downstream fetches are batched.
3. **How LinkedIn Adopted A GraphQL Architecture for Product Development:**
   * *Relevance:* Explains how Rest.li schemas are federated into a single GraphQL system. Documents the central Query Registry Service and pre-registered `queryId` lifecycle.

---

## Phase 2: Session Hijacking & CSRF Coupling
Establishes the minimal secure state needed to execute an authenticated API call.
1. **How to Access LinkedIn Data Without the Official API (r/SaaS):**
   * *Relevance:* Step-by-step documentation of direct, browser-less Voyager API extraction using simple requests.
   * *Core Concepts:* Hijacking the `li_at` cookie and coupling it with the `csrf-token` header.
2. **Postman request (r/learnjavascript) & Bypassing Search Limits (Habr):**
   * *Relevance:* Practical demonstration of the JSESSIONID-to-CSRF-token transformation. Detailed troubleshooting for "CSRF check failed" errors.
   * *Core Concepts:* Stripping double quotes from JSESSIONID to populate the `csrf-token` header. Applying `Accept: application/vnd.linkedin.normalized+json+2.1` to enforce modern schema models.

---

## Phase 3: Technical Prior Art (The Wire-Level Wrappers)
Audit existing open-source codebases to build the backend request client.
1. **`open-linkedin-api` (PyPI & GitHub):**
   * *Relevance:* The most active, community-driven Python implementation targeting the newer Dash API and GraphQL gateway.
   * *Core Concepts:* Replaying POST payloads to `/voyager/api/graphql` with hardcoded variables and hashes.
2. **`linkedin-api` (nsandman / tomquirk fork on GitHub):**
   * *Relevance:* Technical reference of Voyager REST resources, specifically the datalet-based endpoint discovery method.
3. **`linkedinscraper` (masa-finance package in Go):**
   * *Relevance:* Demonstrates how to unmarshal nested Voyager responses into a clean, typed model. Excellent reference for compiling experiences, education, and skill arrays.

---

## Phase 4: Server-Side Detection Evasion
Mitigating risks visible in network transport and behavioral traces.
1. **JA3/JA4 TLS Fingerprinting Guide (Scrapfly) & TLS Bypass Techniques:**
   * *Relevance:* Explains how WAFs detect standard HTTP libraries.
   * *Core Concepts:* The mechanics of JA4 (TLS, HTTP/2, TCP window alignment) and implementing `curl_cffi` to mimic Chrome's Client Hello handshake.
2. **How LinkedIn Catches Automation (Linked Helper Audit Teardown):**
   * *Relevance:* Deep analysis of Request-Map anomalies. Shows how direct API calls with zero page rendering/telemetry pings are identified in server logs.
