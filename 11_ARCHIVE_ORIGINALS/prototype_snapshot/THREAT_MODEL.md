# Threat Model: Security & SSRF Protections

This threat model outlines the security architecture designed to isolate our service, prevent Server-Side Request Forgery (SSRF), protect programmatic session secrets, and guard residential proxies from abuse.

---

## 1. STRIDE Threat Analysis

### Spoofing (API Callers)
* **Threat:** Malicious callers spoof valid API tokens or impersonate other accounts to drain proxy budgets.
* **Mitigation:** Enforce cryptographically signed API keys checked in memory on the gateway. API keys must map to explicit, bounded request pools.

### Tampering (Arbitrary Hosts & SSRF)
* **Threat:** Attackers pass malformed profile URLs to trick the internal transport layer into querying local cloud metadata nodes (e.g., AWS Metadata Endpoint `169.254.169.254`).
* **Mitigation:** Implement strict regular expression validation in `URLCanonicalizer`. Any input that cannot be resolved to a clean alphanumeric string mapped directly to `linkedin.com` or `www.linkedin.com` is rejected before any HTTP requests are made. Follower redirects inside the HTTP transport client are disabled.

### Repudiation (Unlogged Actions)
* **Threat:** Malicious callers run scrapers anonymously, making it impossible to trace usage back to specific users.
* **Mitigation:** Maintain structured, access-controlled audit logs recording the API token hash, transaction timestamp, status code, and resource volume.

### Information Disclosure (Session Leaks)
* **Threat:** Programmatic session cookies (`li_at`, `JSESSIONID`) are exposed in error logs, stack traces, or responses.
* **Mitigation:** Isolate secret configurations. Filter out cookies, tokens, and authorization headers from logs. The transport layer replaces raw request values in error logs with redacted placeholders (`[REDACTED_COOKIE]`).

### Denial of Service (Upstream Checkpoint Expiry)
* **Threat:** Attackers flood the API to trigger account locks and exhaust the proxy budget.
* **Mitigation:** Implement strict rate limits and fair-queue pacing per client key, isolated from IP pools.

### Elevation of Privilege (Proxy Abuse)
* **Threat:** Attackers bypass API routing to utilize internal residential proxies for arbitrary internet browsing.
* **Mitigation:** Restrict proxy network egress via strict firewall rules. The proxy adapter only routes traffic to verified target hosts (`*.linkedin.com`, `*.licdn.com`). All other destination IPs are blocked.

---

## 2. SSRF Prevention Subsystem

Our SSRF defense prevents arbitrary-host fetching by isolating DNS resolution before requests are dispatched:

```
[Input URL] ──► [Regex Parser: Extract Slug] ──► [Strict Host Check] ──► [Custom DNS Resolver] ──► [Request Dispatch]
                                                                                   │
                                                                           (Private IP Block)
                                                                                   ▼
                                                                           [Aborted: HTTP 400]
```

To prevent DNS rebinding attacks (where a malicious domain changes its DNS resolution to point to a private local IP on subsequent lookups), the system utilizes a custom, isolated DNS resolver that inspects resolved IPs and blocks local address ranges (`127.0.0.1`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.169.254/32`) before completing the TCP handshake.
