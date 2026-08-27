# Implementation Plan

## Phase 0 Archive freeze

Never edit `11_ARCHIVE_ORIGINALS/`. Build clean new application tree.

## Phase 1 Repository skeleton

`src/tross_linkedin_api/`, tests, pyproject, env example, gitignore, Dockerfile, CI, schema, operation registry. Gate: clean install/test start/no-browser scan.

## Phase 2 Contracts/config

Typed settings, JSON Schema 2020-12, domain models, RFC 9457, strict startup validation.

## Phase 3 API boundary

URL canonicalizer, required API key, caller limiter, health/readiness. Gate adversarial URLs/status tests.

## Phase 4 Operation registry

Implement parser/validator. Initially no unverified operation enabled.

## Phase 5 Direct HTTP transport

Fixed LinkedIn host, pooling, timeouts, redirect policy, sanitized metadata, owned session secret injection. No anti-bot/WAF evasion.

## Phase 6 Current core operation

Controlled research -> enable one current core/identity operation -> parser + fixture. Gate direct live call on own/consented profile and mandatory primitives.

## Phase 7 First live API

Normalize/schema validate core response; public contract hides upstream shape.

## Phase 8 Required sections one by one

Experience -> education -> skills -> certifications -> languages. Each requires current evidence, fixture, parser, pagination only if observed, live benchmark.

## Phase 9 Partial orchestration

Independent section failures -> 200 partial; drift mutation tests.

## Phase 10 Independent benchmark

Replace circular benchmark; run controlled live matrix; publish sample sizes.

## Phase 11 Deploy HTTPS

Secrets injected outside repo; external health/authenticated query/restart.

## Phase 12 Final audit

Fresh clone, tests, secret scan, browser dependency scan, docs accuracy, judge matrix.

Rule: do not block submission chasing optional profile sections before mandatory fields work end-to-end.
