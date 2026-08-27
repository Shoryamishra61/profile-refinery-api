# Reverse-Engineering Method

## Evidence contract

Protocol claims use exactly one class: `PRIMARY_VERIFIED`, `LIVE_OBSERVED`, `FIXTURE_VERIFIED`, `HISTORICAL_PRACTITIONER`, `VENDOR_CLAIM`, `INFERENCE`, or `UNKNOWN`. Repetition does not upgrade evidence.

## Controlled workflow

1. Select an owned/consented profile and record viewer, locale, timestamp, and manually visible assignment fields.
2. Use DevTools/HAR only as a research instrument. Never commit cookies, tokens, raw HAR, or unrelated profile data.
3. Identify the minimum core operation by semantic purpose. Record redacted method, path template, operation name, input variables, response family, pagination evidence, and timestamp.
4. Replay the request through `LinkedInTransport` using standard HTTPX. Do not add browser runtime, CAPTCHA solving, session theft, account farming, telemetry emulation, TLS/WAF spoofing, or proxy rotation.
5. If LinkedIn returns a checkpoint/challenge, stop requests on that session and require manual recovery.
6. Save a redacted fixture, implement a deterministic parser, and test missing/type-mutated/unknown fields.
7. Update the registry to `live_verified` only after replay succeeds. Query IDs remain environment configuration and carry an observation date.
8. Repeat one section at a time. Implement pagination only when a current response proves pagination semantics and termination.
9. Compare the deployed normalized output to independently recorded human ground truth for viewer V at time T.

The current repository has completed the fixture/parser methodology only. It has no `LIVE_OBSERVED` operation record because no authorized session/capture was available in the execution environment.

