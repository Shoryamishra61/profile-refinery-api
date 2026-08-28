# Reverse-Engineering Protocol Notes

This document records the protocol model the live transport implements, the evidence
behind each assumption, and how each assumption can be re-verified. It is the
reference for the entries in `config/operation_registry.yaml`.

## Verified experimentally (2026-08-28)

| # | Observation | Method | Consequence in code |
|---|-------------|--------|---------------------|
| 1 | `GET https://www.linkedin.com/` hands anonymous visitors a `JSESSIONID` cookie of the form `"ajax:<digits>"` | plain HTTPS GET with a browser User-Agent | the CSRF token is derived from the configured `JSESSIONID` (quotes stripped) |
| 2 | Any `/voyager/api/...` request without a matching `csrf-token` header is rejected with `403` and body `CSRF check failed.` — before any authorization check | same request with and without the header | transport sends `csrf-token: <JSESSIONID>` on every API call |
| 3 | The classic resource `GET /voyager/api/identity/profiles/{slug}/profileView` is retired: it answers HTTP `410` with `{"data":{"status":410}}` once CSRF passes | probe with anonymous session | the transport uses the dash resource instead |
| 4 | `GET /voyager/api/identity/dash/profileView?q=memberIdentity&memberIdentity={slug}&decorationId={deco}` exists but requires a member session: decoration ids that are retired answer `404` with an HTML error page, a live one answers with `application/vnd.linkedin.normalized+json+2.1` | probe with anonymous session (all decorations refused) | decoration ids are tried in a configured order; HTML 404 falls through to the next candidate |
| 5 | Unauthenticated page requests to `https://www.linkedin.com/in/{slug}/` are refused with status `999` even with a full browser header set over HTTP/2 | probe from a residential IP | the 999 status is classified as a security challenge and fails the session closed; no evasion is attempted |
| 6 | Requests carrying an invalid/expired `li_at` are redirected to the authwall | probe with a deliberately invalid `li_at` | authwall redirects are classified as `UPSTREAM_AUTH_EXPIRED` and fail the session closed |

## Current protocol model

```text
LinkedIn URL
    → https://www.linkedin.com/in/{slug}/          (canonical form, slug extracted)
    → GET /voyager/api/identity/dash/profileView
        ?q=memberIdentity
        &memberIdentity={slug}
        &decorationId=com.linkedin.voyager.dash.deco.identity.profile.WebFullProfileWithEntityActions-{N}
      headers:
        csrf-token: <JSESSIONID without quotes>    (verified, observation 2)
        x-restli-protocol-version: 2.0.0
        accept: application/vnd.linkedin.normalized+json+2.1
      cookies: li_at=<session>, JSESSIONID="<session>"
    → single JSON entity graph ("included" array) containing
      com.linkedin.voyager.dash.identity.profile.Profile / Position / Education /
      Skill / Certification / Language plus com.linkedin.voyager.dash.*.Company /
      Organization entities
    → normalization (parsers.py) → public schema
```

Fallback strategy: when every registered decoration id is refused, the transport
fetches `https://www.linkedin.com/in/{slug}/` **directly over HTTP** with the same
session and extracts the embedded Voyager JSON documents
(`<code><!--{...}--></code>` blocks and inline-script `{"included": ...}` payloads).
No browser is involved at any point.

## What needs one live session to confirm

The transport, error classification, and parsers are implemented and unit/contract
tested. The only unverified link is which decoration id is currently served for an
authenticated member account, which is unknowable without sending one authenticated
request. The configured candidate list exists precisely so the first request with a
valid session either succeeds or reports exactly which decoration id drifted.
