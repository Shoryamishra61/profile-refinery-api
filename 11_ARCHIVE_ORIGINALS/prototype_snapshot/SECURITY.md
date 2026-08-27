# Security Architecture & Vulnerability Mitigation

This document outlines the security controls, SSRF defenses, and credential protections engineered into the hosted profile API.

## 1. Defending Against Server-Side Request Forgery (SSRF)

Because our API accepts arbitrary, client-provided profile URLs, there is a risk of Server-Side Request Forgery (SSRF) where attackers attempt to use our server to access private local networks or execute unauthorized queries on downstream cloud endpoints.

### Implemented Defenses:
* **Host Filtering:** The `URLCanonicalizer` parses the URL scheme and strictly enforces that the hostname matches `www.linkedin.com` or `linkedin.com` exactly. No relative routes, file protocols (`file://`), or local endpoints are permitted.
* **Isolated DNS Resolution:** The runtime environment's network layer utilizes an isolated custom DNS resolver that resolves domains prior to initiating connection. If the IP resolved maps to private network segments (e.g. loopback `127.0.0.1`, private IP address pools `192.168.0.0/16`, `10.0.0.0/8`, or link-local address spaces `169.254.169.254`), the request is instantly blocked at the gateway.

## 2. Secure Credential Isolation
* **Zero Client Exposure:** User session cookies (`li_at` and `JSESSIONID`) remain exclusively on the server side. They are injected programmatically into headers at the transport boundary and are never transmitted, exposed, or leaked back to API callers.
* **Environment Separation:** API keys and credentials are loaded dynamically from environment files (`.env`). No secrets, private keys, or actual account credentials are committed to the git repository.

## 3. Log Redaction (PII and Secret Masking)
The FastAPI logger utilizes a custom formatter (`PIIRedactingFormatter`) that intercepts and sanitizes outbound log streams. Sensitive variables, authorization headers, API keys, and cookie headers are automatically replaced with a static string `[REDACTED]` prior to storage or display on standard out.
