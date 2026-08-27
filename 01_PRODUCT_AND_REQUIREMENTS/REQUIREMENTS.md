# Requirements

## Functional

- **FR-001** Accept a LinkedIn member profile URL.
- **FR-002** Validate/canonicalize supported URL shapes before upstream access.
- **FR-003** Production acquisition uses only direct HTTP calls to current evidence-backed LinkedIn endpoints.
- **FR-004** Production contains no browser engine/driver/DOM acquisition path.
- **FR-005** Load LinkedIn credentials exclusively from runtime secret configuration.
- **FR-006** Resolve the input to the identifier required by current verified operations.
- **FR-007** Return name, headline, location, about, and profile image when observable.
- **FR-008** Return experience entries exposed by current verified operations, preserving ordering/nesting.
- **FR-009** Return education entries exposed by current verified operations.
- **FR-010** Return skills when observable through verified operations.
- **FR-011** Return certifications/licenses when observable.
- **FR-012** Return languages when observable.
- **FR-013** Optional section failure must not discard successful core data.
- **FR-014** Every section exposes availability/status.
- **FR-015** Every section exposes observation timestamp + semantic source operation.
- **FR-016** Response includes schema version.
- **FR-017** API-level errors use RFC 9457-compatible Problem Details.
- **FR-018** Repo includes deterministic synthetic/redacted fixtures.
- **FR-019** Final API is publicly reachable over HTTPS.
- **FR-020** Fresh clone contains everything needed except secrets.

## Non-functional

- **NFR-001** Fixture/live/deployment metrics are separate.
- **NFR-002** Secrets never appear in git/logs/errors.
- **NFR-003** User input cannot control outbound host/path.
- **NFR-004** Checkpoint/challenge causes fail-closed live behavior.
- **NFR-005** Volatile operation IDs live in versioned registry.
- **NFR-006** Upstream drift produces controlled partial/parser errors, not crashes.
- **NFR-007** Record per-operation latency/status/retry/parser result without PII payload logging.
- **NFR-008** CI runs without LinkedIn credentials.
- **NFR-009** No persistent profile storage by default.
- **NFR-010** No live latency SLA until measured.

## Explicit non-requirements

Browser automation, CAPTCHA solving, account farms, proxy rotation, TLS fingerprint spoofing, telemetry emulation, contact/email enrichment, persistent people DB, ML/LLM extraction.
