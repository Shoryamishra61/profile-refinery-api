# Data Retention: Compliance-Driven Storage Policy

To satisfy privacy regulations, including European EDPB web scraping guidelines, GDPR, and Indian DPDP (2023) mandates, our microservice implements a strict **ephemeral memory-only execution pipeline**.

---

## 1. Compliance Architecture (Memory-Only Pipeline)

This service enforces privacy compliance by ensuring that target profile data is never written to disk:

```
[Inbound Request]
       │
       ▼
[RAM Extraction Pool] ──► [Entity Parsing & Normalization] ──► [Immediate HTTPS Delivery]
       │                                                                   │
       └───────────────────────────────────────────────────────────────────┼──► [Purge RAM Frame]
                                                                           ▼
                                                                  [Zero File Footprint]
```

Every parsed variable, raw JSON response, and assembled canonical record resides solely in highly localized, transient memory. The instant the outbound HTTPS response is delivered, the localized RAM frame is scrubbed and reclaimed, leaving zero persistent storage traces.

---

## 2. Retention Rules

| Data Category | Target Entity | Retention Limit | Storage Medium | Purpose | Encryption/Sanitization |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **User Inputs** | Alphanumeric Vanity Slugs | Up to 10 Minutes | Transient In-Memory Cache | Cache lookup coordination; rate limiting. | Plaintext inside secure, volatile RAM. |
| **Authentication Secret Keys** | Programmatic Sessions (`li_at`, `JSESSIONID`) | Lifetime of Session | Memory-Only Pool | Upstream REST/GraphQL queries. | Volatile memory, encrypted at rest. |
| **Parsed Target Profiles** | Normalized JSON Models | ephemerally short; discarded on output | Volatile Memory | Parsing and validation. | Purged instantly from RAM after delivery. |
| **Operational Log Audit Traces** | Client IDs & Timestamps | 30 Days | Volatile Docker Logs | Performance analysis; abuse control. | API keys hashed (SHA-256); target profile URLs are scrubbed. |

---

## 3. Log PII Scrubbing Rules
All system diagnostic log streams must pass through an automated regex filter before write-out to standard outputs. The filter dynamically replaces critical PII with anonymous tokens:
* Emails are mapped to `[REDACTED_EMAIL]`.
* Phone numbers are mapped to `[REDACTED_PHONE_NUMBER]`.
* Upstream `li_at` and `JSESSIONID` cookies are redacted to `[REDACTED_SESSION_COOKIE]`.
* Caller-supplied URL query paths are truncated to their alphanumeric vanity slugs to avoid capturing session trackers.
