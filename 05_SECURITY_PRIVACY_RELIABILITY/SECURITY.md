# Security Specification

## Assets

LinkedIn session credentials, caller keys, in-memory profile data, operation registry, deployment secrets, repo integrity.

## Input/SSRF

Never fetch the submitted URL. Parse it to a vanity identifier only. Outbound scheme/host/path come from fixed internal registry. Reject non-LinkedIn/lookalike hosts, credentials in URL, unsupported paths, overlong inputs. Disable or validate upstream redirects.

## Secrets

`.env` ignored; `.env.example` placeholders only; deployment secret injection; secret scan; no HAR with cookies; no raw secret in exceptions.

## Logging

Structured allowlist: request_id, semantic operation, duration, status class, parser result. Avoid cookies, headers, raw profile JSON, email/contact data, API keys. Regex redaction is defense-in-depth only.

## Caller auth

The request-scoped extraction desk is public and connection-rate-limited; it
does not expose a backend session. Legacy operator and batch routes retain a
generic API key, where missing/invalid credentials return 401.

## Upstream JSON

Treat as untrusted: size/content-type limits, defensive traversal, bounded arrays, parser contracts.

## Challenge

Checkpoint/challenge -> stop calls, session unavailable, 503 typed problem, manual recovery. No bypass logic.

## Dependency policy

CI fails if browser runtime dependency appears.

## Required security tests

URL allowlist/lookalikes, redirect behavior, missing/invalid key, secret logging, malformed/oversized upstream, browser dependency scan, git secret scan.
