# Cost & Dependency Model: Project Unit Economics

This model breaks down the operational cost structures and third-party dependencies required to support a production deployment of 1,000,000 profile extractions per month.

---

## 1. Unit Economics (Per 1,000 Requests)

Unlike browser-driven solutions that consume significant CPU and memory to spin up Chromium instances, our pure HTTP-native microservice has negligible resource requirements. This creates massive cost savings.

| Cost Component | Pricing Tier | Unit consumption | Operational Cost | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Residential Proxies** | $3.50 per GB | ~1.2 MB per full profile (includes paginated calls) | $4.20 | Crucial to match localized Metropolitan areas and avoid rapid session bans. |
| **Cloud Hosting (RAM/CPU)**| $12.00 / Node (AWS Fargate) | Negligible CPU, ~150MB RAM per task frame | $0.20 | Synchronous asynchronous non-blocking I/O allows single containers to scale effectively. |
| **Diagnostics & Logging** | $0.10 per GB | ~5 MB of scrubbed audit text | $0.05 | Voluntary log retention kept to a minimum (30-day purge). |
| **Session Cost (Token Pool)**| Free / Recycled | Upstream cookies pooled and managed | $0.00 | Account pools are maintained manually or via internal test suites. |
| **Total Cost / 1,000 Requests**| | | **$4.45** | Equivalent to **$0.0044** per profile extraction. |

---

## 2. Software Dependency Matrix

To guarantee clean, secure, and easily maintainable code, our dependency stack is completely stripped of browser tools. Every dependency is lightweight, offline, and standard-compliant.

| Dependency Package | Role in System | Security Evaluation | Alternative Considered |
| :--- | :--- | :--- | :--- |
| **`fastapi` / `uvicorn`** | ASGI web interface controller. | High-performance, low memory overhead. Type validation and auto OpenAPI generation. | `Flask` (rejected for lacking type-safety and slower async support). |
| **`curl_cffi`** | Outbound HTTP transport client. | Emulates Chrome browser TLS handshakes and JA4/JA4H profiles perfectly out of the box. | `httpx` or `requests` (rejected for leaking non-browser TLS signatures). |
| **`pydantic`** | Schema parsing and structure mapping. | Type enforcement, schema auto-generation, and ultra-fast validation speeds. | `marshmallow` (rejected for slower speeds and verbose parsing syntax). |
| **`jsonschema`** | Enforces outbox compliance schemas. | Standard Draft-07 validator. Highly stable and secure. | Custom regex parser (rejected as brittle and unmaintainable). |
| **`pyyaml`** | Outbound specifications parsing. | Stable parser, used to format human-readable configurations. | JSON-only (rejected to keep settings documentation clean). |
