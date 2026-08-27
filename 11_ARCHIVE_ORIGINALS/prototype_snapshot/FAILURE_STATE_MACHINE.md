# Failure State Machine: Programmatic Error Taxonomy

Our service manages runtime state transitively. This document outlines our state transitions, detailing conditions, error codes, and fallback strategies.

```
                   [IDLE]
                     │
                     ▼
             [RESOLVING_IDENTITY] ──(Invalid URL / Non-existent Slug)──► [PROFILE_NOT_FOUND]
                     │                                                        │
              (Member URN Found)                                              ▼
                     ▼                                                  [HTTP 404 Error]
             [FETCHING_PROFILE]
                     │
                     ├──────────(HTTP 401 / 403: Cookie Invalidated)───► [SESSION_EXPIRED]
                     │                                                        │
                     ├──────────(HTTP 302: Redirect to Captcha)────────► [CHALLENGED_BLOCKED]
                     │                                                        │
                     ├──────────(HTTP 429: Rate Limit Exceeded)────────► [RATE_LIMITED]
                     │                                                        │
                     ├──────────(Payload Missing Keys / Drifted)───────► [UPSTREAM_DRIFT]
                     │                                                        │
                     ▼                                                        ▼
             [NORMALIZING_DATA] ◄─────────────────────────────────────────────┘
                     │
                     ▼
             [VALIDATING_SCHEMA] ──(Schema mismatch)──► [PARSER_FAILED]
                     │
                     ▼
              [RESPONSE_READY]
```

## State Transition Conditions

| Source State | Destination State | Triggering Event / Condition | Action / Remediation |
| :--- | :--- | :--- | :--- |
| **IDLE** | **RESOLVING_IDENTITY** | Ingestion of profile lookup request. | Validate user token; check URL safety. |
| **RESOLVING_IDENTITY** | **PROFILE_NOT_FOUND** | Upstream returns HTTP 404 or profile slug resolution fails. | Terminate process, return standard RFC 9457 error to caller. |
| **FETCHING_PROFILE** | **SESSION_EXPIRED** | Upstream API returns HTTP 401 Unauthorized or Cookie expired flag. | Flag session as dead; execute failover to clean session. |
| **FETCHING_PROFILE** | **CHALLENGED_BLOCKED** | Upstream redirects to verification check (reCAPTCHA, security checkpoint). | Quarantine IP/Proxy; flag session as challenged. |
| **FETCHING_PROFILE** | **RATE_LIMITED** | Upstream returns HTTP 429 Too Many Requests. | Implement backoff; rotate IP/Proxy; request retry bucket validation. |
| **FETCHING_PROFILE** | **UPSTREAM_DRIFT** | JSON response parses successfully but queryIds fail or mandatory keys are missing. | Capture raw payload for developers; set status to `not_available_from_endpoint`. |
| **NORMALIZING_DATA** | **PARSER_FAILED** | Incompatible data types (e.g., string returned instead of expected date integer). | Capture mapping error; set field status to `parser_failed` in canonical schema. |
| **VALIDATING_SCHEMA** | **RESPONSE_READY** | Normalized JSON matches schema definitions exactly. | Serve response payload with HTTP 200 OK. |

---

## 2. Recovery Protocols

### Session Rollover
If the Active Session Manager detects a `SESSION_EXPIRED` state, it immediately quarantines the current session from rotation. The request is dispatched to a standby session cookie, with zero impact on the caller's request lifecycle.

### Upstream Drift Mitigation
If the system encounters an `UPSTREAM_DRIFT` state, it halts the parse pipeline for the affected section, logs the updated payload structure to a secure diagnostics logger, and sets the affected field statuses to `not_available_from_endpoint`. The system then delivers the remaining sections of the profile, avoiding a hard crash.
