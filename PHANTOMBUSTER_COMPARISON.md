# PhantomBuster Comparison

Evidence classes in this document are explicit.

| Dimension | This repository | PhantomBuster profile product |
|---|---|---|
| Runtime approach | Direct HTTP adapter; browser runtime prohibited (`FIXTURE_VERIFIED` in code) | API-call-oriented Profile Scraper is described separately from Profile Visitor (`VENDOR_CLAIM`) |
| Output contract | Nested typed schema with field status and provenance (`FIXTURE_VERIFIED`) | Vendor export schema/coverage varies by product documentation (`VENDOR_CLAIM`) |
| Drift boundary | Versioned semantic registry plus parser fixtures/tests (`FIXTURE_VERIFIED`) | Internal implementation not observable here (`UNKNOWN`) |
| Partial failure | Core preserved; per-section status (`FIXTURE_VERIFIED`) | Comparable semantics not measured (`UNKNOWN`) |
| History depth | Two synthetic experience entries; no live pagination claim (`FIXTURE_VERIFIED`) | Historical research reports limited examples, but no comparable current run (`HISTORICAL_PRACTITIONER`/`UNKNOWN`) |
| Live latency | Not measured (`UNKNOWN`) | Not measured in a controlled same-profile experiment (`UNKNOWN`) |
| Live field coverage | Not measured (`UNKNOWN`) | Not measured in a controlled same-profile experiment (`UNKNOWN`) |

A defensible comparison requires the same consented profiles, viewer context, observation window, independently recorded truth, and end-to-end timing. Until then, no “faster,” “more complete,” or percentage advantage is claimed.
