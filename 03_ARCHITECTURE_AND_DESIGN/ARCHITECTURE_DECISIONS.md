# Architecture Decision Records

- **ADR-001 Direct HTTP only:** explicit Tross requirement. Reject browser acquisition.
- **ADR-002 Single owned session MVP:** challenge permits own credentials; multi-account rotation adds risk without evaluator value.
- **ADR-003 Operation registry:** volatile endpoint/query identifiers are data/config.
- **ADR-004 Start with standard HTTP client:** only change transport behavior if controlled evidence requires it; no default TLS/WAF spoofing.
- **ADR-005 Core-first partial response:** optional section failure should not discard valid core data.
- **ADR-006 Ephemeral processing:** no persistent profile DB for MVP.
- **ADR-007 JSON Schema 2020-12 target:** aligns with OpenAPI 3.1. Preserve Draft-07 legacy schema only as archive.
- **ADR-008 Strict startup:** missing schema/registry/live secrets fail relevant mode.
- **ADR-009 Separate fixture/live/deployment metrics:** no category mixing.
- **ADR-010 No contact enrichment:** not required; adds privacy scope; legacy mock fabricated addresses.
- **ADR-011 API key required:** public upstream-dependent endpoint should not be open abuse surface.
- **ADR-012 No automatic query-ID harvesting:** updates are explicit controlled research/config changes.
