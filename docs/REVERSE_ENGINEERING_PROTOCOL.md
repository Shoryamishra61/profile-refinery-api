# Reverse-Engineering Protocol Notes

This document records the protocol model the live transport implements, the evidence
behind each assumption, and how each assumption can be re-verified. It is the
reference for the entries in `config/operation_registry.yaml`.

## Verified experimentally (2026-08-28)

| # | Observation | Method | Consequence in code |
|---|-------------|--------|---------------------|
| 1 | `GET https://www.linkedin.com/` hands anonymous visitors a `JSESSIONID` cookie of the form `"ajax:<digits>"` | plain HTTPS GET with a browser User-Agent | the CSRF token is derived from the `JSESSIONID` cookie (quotes stripped) |
| 2 | Any `/voyager/api/...` request without a matching `csrf-token` header is rejected with `403` and body `CSRF check failed.` — before any authorization check | same request with and without the header | the CSRF header is sent on every API call |
| 3 | The classic resource `GET /voyager/api/identity/profiles/{slug}/profileView` is retired: HTTP `410` with `{"data":{"status":410}}` once CSRF passes | probe with a real authenticated session | the transport does not use it |
| 4 | The intermediate dash resource `/voyager/api/identity/dash/profileView` is gone: HTTP 404 (HTML error page) for every decoration id and even without parameters | probe with a real authenticated session | the transport does not use it |
| 5 | The live member finder is **`GET /voyager/api/identity/dash/profiles?q=memberIdentity&memberIdentity={slug}`** — observed HTTP 200 with a `{"data":{"entityUrn":"urn:li:collectionResponse:…",…},"included":[…]}` body for an authenticated session | one request with the owned session (bursty follow-up probing then triggered a soft challenge, so the full payload capture is paced) | this is the primary `profile_view` operation |
| 6 | LinkedIn **rotates session cookies server-side** (`Set-Cookie` on voyager responses). A stateless hand-built `Cookie:` header goes stale | observed during live probing | the transport seeds a persistent cookie jar with `li_at`/`JSESSIONID` and derives `csrf-token` from the jar's current `JSESSIONID` per request |
| 7 | Bursty scripted traffic (~15 rapid requests) is answered with a **same-URL 302** that sets `li_at=delete me` cookies — a soft challenge, not an auth failure. A subsequent authenticated page fetch still worked earlier; the flag clears with time and gentle pacing | observed live after the probe burst | the transport retries a same-URL redirect once with the refreshed jar and then fails closed with `UPSTREAM_CHALLENGE`. It never loops and never tries to evade the challenge; the correct response is slower pacing |
| 8 | Requests carrying an invalid/expired `li_at` are redirected to the authwall | probe with a deliberately invalid `li_at` | authwall redirects classify as `UPSTREAM_AUTH_EXPIRED` and fail the session closed |
| 9 | Unauthenticated page requests are refused with status `999` even with a full browser header set over HTTP/2 | probe | 999 classifies as `UPSTREAM_CHALLENGE`; no evasion is attempted |
| 10 | `GET /voyager/api/me` returns the session owner's identity (200 JSON) — used as a session liveness check | probe | documented as an operator diagnostic |

| 11 | **Client fingerprinting**: with a freshly logged-in session, the first scripted voyager request succeeds; subsequent scripted requests from the same client answer the soft-challenge 302 regardless of pacing (10-minute pauses included), fresh `JSESSIONID`, or full companion-cookie context. The same session keeps working in a real browser | live observation, 2026-08-28/29 | the breaker treats challenges as capacity events; overcoming fingerprinting would require mimicking a browser TLS stack or automating logins — both rejected as evasion. Extraction is verified within usable windows and fails closed otherwise |

## Current protocol model

```text
LinkedIn URL
    → https://www.linkedin.com/in/{slug}/          (canonical form, slug extracted)
    → GET /voyager/api/identity/dash/profiles
        ?q=memberIdentity
        &memberIdentity={slug}
      headers:
        csrf-token: <current jar JSESSIONID, quotes stripped>   (observation 2, 6)
        x-restli-protocol-version: 2.0.0
        accept: application/vnd.linkedin.normalized+json+2.1
      cookies (persistent jar, server-rotatable): li_at=<session>, JSESSIONID="<session>"
    → JSON envelope: data.entityUrn = urn:li:collectionResponse:…, included: [entities]
      expected entities: com.linkedin.voyager.dash.identity.profile.Profile /
      Position / Education / Skill / Certification / Language and
      com.linkedin.voyager.dash.*.Company / Organization
    → normalization (parsers.py) → public schema
```

Fallback strategy: when the Rest.li contract drifts, the transport fetches
`https://www.linkedin.com/in/{slug}/` **directly over HTTP** with the same session
and extracts the embedded Voyager JSON documents (`<code><!--{...}--></code>` blocks
and inline-script `{"included": ...}` payloads). No browser is involved at any
point.

## Pacing / account safety

Observation 7 is a hard constraint: aggressive scripted request volume triggers a
soft challenge. The service therefore keeps upstream volume minimal (one profile
request per profile in the common case), bounds batch concurrency
(`APP_BATCH_CONCURRENCY`, default 3), uses bounded retry with backoff, and fails
closed on challenges. Session refresh happens in the operator's browser, never by
automating login.

## What needs one paced live session to finish

The endpoint contract, CSRF model, cookie rotation, and error taxonomy are all
verified. The remaining live work is a paced capture of the full default-projection
payload (to confirm which entities the `included` array carries for a third-party
member — everything the parsers need is shape-tested against sanitized fixtures)
and the three-profile differential run. The transport retries this automatically
as the challenge window clears.
