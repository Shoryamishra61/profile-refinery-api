# Traceability Matrix
| Challenge requirement | Internal requirement | Component | Evidence/test |
|---|---|---|---|
| URL input | FR-001/002 | URLCanonicalizer | unit + API integration |
| Direct endpoints | FR-003 | Registry + Transport | controlled live trace |
| No browser | FR-004 | dependency policy | CI import/dependency scan |
| Backend credentials | FR-005 | SessionProvider | config + secret scan |
| Name/headline/location/about | FR-007 | core parser | live field matrix |
| Experience | FR-008 | section parser/paginator | rich consented live profile |
| Education | FR-009 | section parser | live profile |
| Skills | FR-010 | section parser | live profile where observable |
| Certifications | FR-011 | section parser | live profile |
| Languages | FR-012 | section parser | live profile |
| Images | FR-007 | media parser | live response validation |
| Structured JSON | FR-014/016 | schema gate | contract test |
| Public HTTPS | FR-019 | deployment | external curl/TLS |
| Public repo/README | FR-020 | repository | clean clone |
| No secrets | NFR-002 | CI/logging | secret/redaction tests |
