# Reverse-Engineering Method

Protocol work is evidence-led and semantic. It models stable operations and entities rather than DOM layout.

1. Select an owned or consented profile and record viewer, locale, timestamp, and visible ground truth.
2. Capture a bounded request with developer tools. Never commit cookies, tokens, raw HAR files, or unrelated personal data.
3. Reduce the capture to a safe contract: method, host, path, parameter names, component identifier, body keys, protocol headers, redirect policy, response type, size, and semantic markers.
4. Replay with standard HTTP through the same transport boundary. Stop on challenges; do not synthesize telemetry or bypass access controls.
5. Decode React Flight records and resolve target ownership before accepting any entity. Unknown or identity-less shapes are operation drift, not profiles.
6. Add a redacted replay fixture, an independent expected result, and mutation tests for missing, reordered, and unknown fields.
7. Mark an operation `live_verified` only after an authorized direct request succeeds. Keep live, real replay, and synthetic-unit evidence distinct.
8. Implement pagination or new sections only after captures establish their semantics and termination conditions.
9. Compare normalized output with viewer-specific ground truth and report missing values honestly.

The registered primary path is an SDUI React Flight component request for core identity followed by identity-scoped profile-card requests. An authenticated profile-page operation is a core fallback and bounded location-enrichment path. Safe request-shape details live in [docs/REVERSE_ENGINEERING_PROTOCOL.md](docs/REVERSE_ENGINEERING_PROTOCOL.md).
