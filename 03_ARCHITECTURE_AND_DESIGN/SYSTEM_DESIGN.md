# System Design

## Pipeline

```text
Caller -> HTTPS API/auth/rate limit -> URL canonicalizer -> operation registry
      -> session provider -> direct HTTP transport -> core identity/profile
      -> identity resolver -> required section fetchers (bounded parallel)
      -> raw validators -> entity assembler -> canonical normalizer
      -> status/provenance -> JSON Schema gate -> response
```

## Principles

1. **Operation registry is volatility boundary.** Endpoint/query identifiers are configuration/evidence, not business logic.
2. **Public schema is stable.** Upstream changes do not leak into caller contract.
3. **Core-first partial orchestration.** Core must succeed; optional section failures return partial response.
4. **Bounded concurrency.** Only independent verified operations parallelize.
5. **No persistent people database.** Ephemeral processing by default.
6. **No browser runtime.** Enforced in CI.
7. **No evasion subsystem.** Challenge is a stop state.

## Components

### URLCanonicalizer

Parse URL to slug. Never fetch user-supplied URL directly. Outbound hosts/paths come only from internal registry.

### Settings

Strict startup validation; no live-secret defaults.

### SessionProvider

One developer-owned session context for MVP; no account rotation farm.

### OperationRegistry

Versioned current operation metadata with evidence status.

### LinkedInTransport

Direct HTTP, fixed LinkedIn host allowlist, connection pooling, timeouts, low bounded transient retries, safe response metadata. No challenge bypass.

### IdentityResolver

Extract current profile identity from verified core response.

### SectionFetcher

One parser/fixture contract per semantic section.

### EntityAssembler

Rejoin normalized entity references where response semantics require it.

### Normalizer

Map to public domain model and explicit availability states.

### SchemaValidator

Fail startup if schema missing/invalid. Never fail open.

## Request budgeting

Do not set arbitrary <=3-call gate. Measure actual current graph. Use one core call plus only required section/pagination calls.

## Caching

No persistent profile cache in MVP. Optional in-process request coalescing only. If later caching normalized profiles, disclose TTL/observed_at.

## Deployment

One stateless container behind managed HTTPS ingress is sufficient for challenge scale.

## Explicit exclusions

Redis/PostgreSQL/Celery/RabbitMQ/browser runtime/proxy pool/TLS spoofing/session farm/LLM parser unless new evidence shows a requirement.
