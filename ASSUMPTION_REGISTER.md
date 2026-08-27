# Assumption Register

| ID | Statement | Evidence class/status | Blocking | Required resolution |
|---|---|---|---|---|
| A-01 | A current core profile operation can be directly replayed with an owned session | `UNKNOWN` | Yes | authorized current capture plus replay |
| A-02 | Vanity slug maps to a stable profile URN in the current core response | `UNKNOWN`; fixture parser supports it | Yes | current core fixture |
| A-03 | Required sections use distinct current GraphQL operations | `UNKNOWN`; checked-in shapes are synthetic | Yes | current request graph per section |
| A-04 | Current section operations paginate | `UNKNOWN` | No for parser scaffold; yes for full history | current paging metadata and termination experiment |
| A-05 | Standard HTTPX is sufficient for direct replay | `UNKNOWN` live; transport behavior `FIXTURE_VERIFIED` via mocked HTTP | Yes | controlled direct replay |
| A-06 | JSESSIONID-derived CSRF token remains valid | `HISTORICAL_PRACTITIONER` | Yes | controlled header/cookie replay diff |
| A-07 | Query identifiers are volatile | `INFERENCE` from architecture | No | longitudinal observations |
| A-08 | Missing live keys indicate viewer restriction | Rejected as unsupported | No | explicit upstream/viewer evidence only |
| A-09 | Profile media expiry can be inferred from URL | Rejected as unsupported | No | only use explicit expiry metadata |
| A-10 | One public stateless container is adequate for challenge load | `INFERENCE` | No | deployment load measurement |
| A-11 | Live p50 is below any fixed threshold | `UNKNOWN` | No | controlled-live and public deployment benchmark |
| A-12 | PhantomBuster has lower coverage or higher latency | `UNKNOWN` | No | same-profile controlled comparison |

Excluded and not pursued: CAPTCHA solving, account/session farms, stolen sessions, proxy rotation, telemetry emulation, TLS/WAF fingerprint spoofing, browser runtime, and automatic query-ID harvesting.

