# Assumption Register
| ID | Assumption | Current status | Blocking | Evidence needed |
|---|---|---|---|---|
| A-01 | Current core profile works via direct HTTP with owned session | UNKNOWN | Yes | current capture + replay |
| A-02 | Vanity slug resolves to stable/reusable profile ID | likely/historical | Yes | current response |
| A-03 | Experience has a separate paginated operation | historical/unknown | Yes for full history | current request graph |
| A-04 | Education has separate operation | historical/unknown | Yes | current request graph |
| A-05 | Skills available directly | unknown | Yes | current observation |
| A-06 | Certifications available directly | unknown | Yes | current observation |
| A-07 | Languages available directly | unknown | Yes | current observation |
| A-08 | Core response exposes image | likely | No | live fixture |
| A-09 | CSRF token derives from JSESSIONID as legacy docs claim | practitioner; verify | Yes | controlled diff |
| A-10 | Query identifiers rotate | strong architecture inference | No | longitudinal observation |
| A-11 | Standard HTTP client is sufficient | unknown | Yes | controlled replay |
| A-12 | Browser/TLS fingerprint spoofing is necessary | unproven/excluded | No | not pursued |
| A-13 | Proxy stickiness required | unproven/excluded | No | not pursued |
| A-14 | Universal safe profiles/day exists | unverified | No | not needed |
| A-15 | Full history beats PB two-job output | unknown | No | live rich-profile benchmark |
| A-16 | Live p50 <1.5s | unknown | No | deployment measurement |
