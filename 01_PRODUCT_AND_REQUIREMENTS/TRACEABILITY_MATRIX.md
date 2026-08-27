# Traceability Matrix

| Requirement | Decision/component | Code/config | Verification | Status |
|---|---|---|---|---|
| FR-001/002 URL input/canonicalization | URL becomes slug only | `canonicalizer.py` | `test_canonicalizer.py`, API invalid URL | PASS |
| FR-003 direct endpoints | fixed-origin registry transport | `transport.py`, registry | mocked direct HTTP contract | IMPLEMENTED; live blocked |
| FR-004 no browser | dependency/source policy | manifest, security script | CI security audit | PASS |
| FR-005 credential boundary | strict environment settings | `config.py`, `session.py` | live startup validation | PASS |
| FR-006 identity resolution | core profile parser | `parsers.py` | synthetic core parser test | FIXTURE only |
| FR-007 core/image | localized core/media parser | parser/normalizer/models | parser + API integration | FIXTURE only |
| FR-008 experience | deterministic position/company join | `parse_experience` | two independent expected entries | FIXTURE only |
| FR-009 education | deterministic education parser | `parse_education` | independent expected entry | FIXTURE only |
| FR-010 skills | named-entity parser | `parse_skills` | two independent expected entries | FIXTURE only |
| FR-011 certifications | certification/date parser | `parse_certifications` | independent expected entry | FIXTURE only |
| FR-012 languages | language/proficiency parser | `parse_languages` | two independent expected entries | FIXTURE only |
| FR-013 partial results | core-first concurrent orchestration | `orchestrator.py` | forced skills timeout test | PASS fixture contract |
| FR-014 availability | explicit ontology | models/normalizer | 12/12 benchmark statuses | PASS fixture contract |
| FR-015 provenance | semantic operation/time/parser/ref | models/normalizer | 12/12 benchmark coverage | PASS fixture contract |
| FR-016 schema version | Pydantic + Draft 2020-12 | models/schema/validator | schema startup and API tests | PASS |
| FR-017 RFC 9457 errors | stable problem types/codes | `errors.py`, API handler | auth/input/rate/drift tests | PASS |
| FR-018 fixtures | synthetic raw + independent expected | `tests/fixtures` | benchmark | PASS |
| FR-019 public HTTPS | stateless container/Blueprint | Dockerfile/render.yaml | no external endpoint available | BLOCKED |
| FR-020 fresh clone | uv lock, package data, docs | repository | clean clone: sync + 54 tests + benchmark + security | PASS |
| NFR-001 evidence-separated metrics | benchmark/result labels | benchmark/RESULTS | `live_extraction_claim=false` | PASS |
| NFR-002 secrets | secret-only settings/allowlist logs | config/session/observability | scanner/log test/Git scan | PASS automated scope |
| NFR-003 fixed outbound target | canonicalizer + constant origin | canonicalizer/transport | SSRF and host/path tests | PASS |
| NFR-004 challenge fail closed | unavailable session state | session/transport | 403/checkpoint contract tests | PASS contract |
| NFR-005 operation registry | semantic registry/evidence gate | registry YAML/loader | invalid/evidence tests | PASS |
| NFR-006 drift control | typed operation/parser errors | transport/parsers/orchestrator | mutation/malformed/partial tests | PASS |
| NFR-007 observability | allowlisted operation metadata | observability/transport | logging + API metadata tests | PASS |
| NFR-008 credential-free CI | fixture default in CI | workflow | local file complete; remote upload blocked by OAuth scope | PARTIAL |
| NFR-009 no persistent storage | stateless runtime | architecture/source | source review | PASS |
| NFR-010 no unmeasured live SLA | explicit unknown result | RESULTS/LIMITATIONS | judge audit | PASS |
