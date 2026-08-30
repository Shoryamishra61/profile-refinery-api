# Limitations

- LinkedIn is an undocumented, mutable upstream. A registered request may be challenged or may drift without notice; the service fails closed in either case.
- Completeness depends on what the authenticated viewer can access. Missing data remains missing and is never inferred.
- Languages has successful live operation evidence but no non-empty real sample in the retained evidence set.
- Pagination is not claimed where a captured protocol has not established cursor and termination semantics.
- The caller limiter, circuit breaker, readiness observation, and journal are process-local. Multi-instance production needs shared implementations at the platform boundary.
- Vercel storage is ephemeral. Long-lived batch history requires a persistent `JournalStore` implementation.
- Request-scoped extraction accepts at most 10 profiles per API call. The web client can coordinate up to 200 discovered profiles in sequential groups.
- LinkedIn post URLs are discovered but not resolved to authors without a verified semantic post-to-author protocol.
- PDF is an input format, not an export format. Exports are JSON, CSV, XLSX, and self-contained HTML profile cards.
- The project does not claim LinkedIn endorsement, universal policy compliance, or a lawful basis for every possible deployment. Operators remain responsible for authorization, data protection, and platform terms.
