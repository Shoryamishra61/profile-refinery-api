# Architecture Decision Records (ADRs)

These records outline the fundamental architectural choices made during the design of our browser-less LinkedIn Profile API. Each decision is justified through measured evidence, evaluated alternatives, and targeted testing patterns.

---

## ADR-01: Synchronous vs. Asynchronous API Execution
* **Status:** APPROVED
* **Requirement:** The API must accept an HTTPS request and return a normalized profile JSON. It must balance caller experience with resource limits.
* **Evidence:** Upstream network lookups (identity resolution + parallel section scraping) have a combined latency profile of 800ms–2500ms under optimal connection pooling. This is well within standard HTTPS timeout windows (typically 10s–30s).
* **Alternative:** *Asynchronous Event-Driven Queue:* Caller requests profile $ightarrow$ returns immediately with a task ID $ightarrow$ worker executes in background $ightarrow$ caller polls or receives webhooks.
* **Reason Selected:** An asynchronous queue adds database overhead, Redis complexity, background worker management, and polling latency. For a research-grade API, direct synchronous execution dramatically simplifies deployment while easily remaining within acceptable HTTP latency envelopes.
* **Failure Mode:** Upstream timeouts or heavy parallel query spikes causing connection exhaustion and request blocking.
* **Test Proving Correctness:** High-throughput performance test measuring P99 latency. Assert that connections are released cleanly under simultaneous queries without leaking file descriptors.

---

## ADR-02: Bounded Concurrency & Connection Pooling
* **Status:** APPROVED
* **Requirement:** Ensure upstream HTTP requests do not saturate resources or trigger account blocks, while maintaining connection performance.
* **Evidence:** Re-establishing TLS connections for every outbound REST/GraphQL request introduces massive network overhead, increasing latency by up to 500ms per request. 
* **Alternative:** *Unbounded Async HTTP Clients:* Open a new, ephemeral connection client for every individual request.
* **Reason Selected:** Unbounded clients trigger security thresholds by creating an abnormal volume of TCP handshakes from the same host, prompting instant IP blocks. Bounding concurrency through a persistent connection pool (using an active pool size of 10–20 connections per proxy target) stabilizes outbound request pacing and eliminates handshake overhead.
* **Failure Mode:** Pool starvation, where incoming requests are blocked waiting for an available connection from the pool.
* **Test Proving Correctness:** Starvation-test by initiating parallel requests exceeding the pool size. Confirm that subsequent requests queue gracefully and execute immediately as connections are released.

---

## ADR-03: SSRF Prevention & Strict URL Canonicalization
* **Status:** APPROVED
* **Requirement:** The API must treat the user-supplied profile URL as untrusted input. It must prevent arbitrary-host fetching and Server-Side Request Forgery (SSRF).
* **Evidence:** Exploits like OWASP Top 10 API-10 (SSRF) allow attackers to trick systems into querying internal infrastructure (e.g., `http://169.254.169.254/latest/meta-data/` on AWS) by supplying malformed input fields.
* **Alternative:** *Naked URL Redirection:* Rely on the HTTP client library's built-in redirect follower to handle the user-supplied URL directly.
* **Reason Selected:** Follower redirects are extremely vulnerable to DNS rebinding and loopback exploits. By implementing a strict canonicalizer, we parse the URL using isolated regular expressions, extract only the alphanumeric vanity slug, and discard the rest. Any host that does not match `linkedin.com` or `www.linkedin.com` is rejected before any HTTP requests are made.
* **Failure Mode:** Regex bypass or unexpected domain extensions (such as regional subdomains like `jp.linkedin.com`) being blocked erroneously.
* **Test Proving Correctness:** Supply local network ranges, non-LinkedIn domains, and DNS rebinding payloads. Assert that all are blocked before execution with an HTTP 400 Bad Request.

---

## ADR-04: Ephemeral In-Memory Cache vs. Persistent Storage
* **Status:** APPROVED
* **Requirement:** Implement a mechanism to prevent redundant upstream requests for frequently queried profiles.
* **Evidence:** Repeatedly querying the same profile within a short window increases account risks and saturates outbound rate limits unnecessarily.
* **Alternative:** *Persistent PostgreSQL/Redis Database:* Storing full profile records long-term in an external database.
* **Reason Selected:** Persistent storage triggers complex compliance requirements (GDPR, PDPA, and EDPB regulations) regarding data retention, deletion requests, and PII storage. An ephemeral, in-memory cache (like an LRU cache limited to a 10-minute expiry window) achieves performance gains for concurrent requests without persisting PII long-term.
* **Failure Mode:** Cache saturation or memory exhaustion due to large payload strings.
* **Test Proving Correctness:** Verify that consecutive requests for the same profile within the 10-minute window return data instantly from cache, and that records are purged from memory immediately upon expiration.

---

## ADR-05: Protocol Telemetry Emulation & JA4 Transport
* **Status:** APPROVED
* **Requirement:** Upstream connections must avoid triggering bot-detection systems at the network edge.
* **Evidence:** Standard HTTP client libraries (like python `requests` or `urllib3`) utilize default SSL/TLS handshakes that are instantly flagged by network-edge security filters (such as Akamai or Cloudflare bot-management tools) as non-browser traffic.
* **Alternative:** *Standard HTTP Client:* Use simple HTTP libraries with customized headers.
* **Reason Selected:** Modern security systems verify the JA4 TLS handshake fingerprint against the HTTP `User-Agent` header. A mismatch causes an immediate block. By using `curl_cffi` (mimicking a specific Chrome TLS profile), the network fingerprint matches browser signatures exactly, ensuring safe transit.
* **Failure Mode:** Edge updates changing verified JA4 fingerprints, causing connection blocks.
* **Test Proving Correctness:** Run traffic through a local wire-sniffer to verify that JA4 hello signatures match production Chrome browser handshakes.

---

## ADR-06: API Key Caller Authentication & Bounded Rate Limits
* **Status:** APPROVED
* **Requirement:** Control access to the public-facing API to prevent abuse and coordinate session consumption.
* **Evidence:** Unauthenticated endpoints are highly vulnerable to denial-of-service (DoS) attacks, which can quickly exhaust upstream cookie pools and proxy resources.
* **Alternative:** *IP-based Rate Limiting:* Track and rate-limit callers solely by their source IP address.
* **Reason Selected:** IP-based tracking is easily bypassed using rotating proxy pools and does not scale in cloud-routed consumer environments. Standard API key authentication (passed via the `X-API-Key` header) provides precise caller tracking, usage quotas, and predictable resource planning.
* **Failure Mode:** Credential leaks or database lookup bottlenecks for API keys.
* **Test Proving Correctness:** Perform rate-limit test, asserting that requests exceeding the allocated quota are blocked with an HTTP 429 Too Many Requests response.
