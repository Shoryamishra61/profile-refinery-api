# Software Requirements Specification

## Context actors

API caller/evaluator; public service; LinkedIn upstream endpoints; deployment secret store; CI; controlled reverse-engineering workstation.

## Runtime sequence

1. authenticate caller;
2. parse LinkedIn URL -> canonical slug;
3. load enabled operation registry;
4. obtain developer-owned session context;
5. execute direct core operation;
6. resolve stable/current profile identity;
7. execute required optional section operations with bounded concurrency;
8. parse/assemble raw normalized entities;
9. normalize to stable public schema;
10. attach section status/provenance;
11. validate schema;
12. return complete/partial response.

## Internal interfaces

`URLCanonicalizer`, `Settings`, `SessionProvider`, `OperationRegistry`, `LinkedInTransport`, `IdentityResolver`, `SectionFetcher`, `EntityAssembler`, `ProfileNormalizer`, `SchemaValidator`, `MetricsRecorder`.

## Public interface

`GET /v1/profiles?url={linkedin_profile_url}` with required `X-API-Key`.

Health: `/healthz`, `/readyz`.

## Error map

- 400 invalid profile URL
- 401 missing/invalid caller key
- 404 confidently not found
- 429 caller rate limit
- 502 operation/response/schema drift
- 503 upstream auth/challenge/throttle unavailable
- 504 upstream timeout

Upstream 401/403 should not automatically become caller 401/403.

## Startup validation

Fail startup for relevant mode if schema/registry invalid or live mode lacks required secrets.
