# Operational Specification: API Error Taxonomy and Failure Signatures
**Author:** Systems Reliability & Protocol Engineering Group  
**Status:** Pre-Design Technical Specifications  
**Focus:** Translating raw HTTP/WAF failures into typed API errors.

---

## 1. Upstream Failure Mapping
The hosted extraction service must not return generic "500 Internal Server Error" responses [330]. It must systematically analyze upstream HTTP status codes and response JSON objects to expose a highly transparent, actionable error taxonomy [196, 330].

| Upstream HTTP Status | Server Response Keyword / Signature | Inferred Structural Failure Mode | Hosted API Typed Error Code | Solution / Protocol Action |
| ------ | ------ | ------ | ------ | ------ |
| **400 Bad Request** | `"Invalid parameters"` / GraphQL bad request [679] | Endpoint path renamed or pre-registered GraphQL `queryId` rotated [160, 308]. | `UPSTREAM_SCHEMA_DRIFT` | Block queue, alert developers to fetch new query hashes from production JS [160, 308]. |
| **401 Unauthorized** | `"CSRF check failed."` [193, 310] | `csrf-token` header desynchronized from rotating `JSESSIONID` [176, 310]. | `CSRF_DESYNCHRONIZATION` | Re-derive token from cookie jar, retry request once [176]. |
| **401 Unauthorized** | `"expired_token"` [64, 679] | Session cookie `li_at` invalidated or expired [153]. | `SESSION_EXPIRED` | Notify account owner to re-authenticate and submit new cookies [64, 81]. |
| **403 Forbidden** | `/checkpoint/challenge/` / reCAPTCHA redirect [9, 759] | Anti-bot engine triggered; account flagged [176, 330]. | `ACCOUNT_CHALLENGED` | Immediately isolate account, route traffic to backup session in pool [176]. |
| **404 Not Found** | Empty elements / `"Resource not found"` [213, 679] | Public URL refers to a deleted, deactivated, or restricted member profile [198, 213]. | `PROFILE_NOT_FOUND` | Terminate request loudly; do not retry. Return HTTP 404 to caller [196]. |
| **410 Gone** | Legacy endpoint response [7, 307] | REST endpoint decommissioned by LinkedIn engineers [7, 307]. | `ENDPOINT_DEPRECATED` | Migrate query path dynamically to the GraphQL gateway POST endpoint [17, 307]. |
| **429 Too Many Requests** | `"Rate limit exceeded"` [679] | Operating volume ceiling breached [679]. | `RATE_LIMIT_EXCEEDED` | Extract value from `Retry-After` header; pause task queue for specified delay [679]. |

---

## 2. Differentiating Private, Empty, and Hidden States
A major threat to data quality is the misinterpretation of missing fields [320, 330]. Downstream consumers must know whether a field is missing because the user omitted it, or because the viewer lacks access [156, 329].

1. **Empty Facts (User Omission):**
   * **Signature:** The endpoint returns HTTP 200, the member URN exists, but the sections array (e.g., `positions: []`) is empty or omitted [237].
   * **Semantic Meaning:** The candidate genuinely does not have educational or experience history populated on their profile [237, 248].
   * **Schema Representation:** `{"experience": []}` (Explicitly empty array).
2. **Hidden / Restricted Facts (Privacy Controls):**
   * **Signature:** The endpoint returns HTTP 200, the top card parses correctly, but nested sub-resources return empty arrays or access denied codes [120, 330].
   * **Semantic Meaning:** The data exists on LinkedIn, but the active session viewer’s connection degree (e.g., out-of-network) prevents reading it [204, 330].
   * **Schema Representation:** `{"experience": null}` (Null denotes restricted visibility/absence of evidence).
3. **Extraction / Pipeline Failures:**
   * **Signature:** Upstream returns status 500 or parser throws an exception [176, 330].
   * **Semantic Meaning:** A technical barrier prevented data acquisition [330].
   * **Schema Representation:** The endpoint returns `HTTP 502 Bad Gateway` carrying details of the parsed error [330].
