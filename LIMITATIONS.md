# Limitations

- No current LinkedIn operation has been observed or directly replayed in this environment. All enabled records are synthetic `FIXTURE_VERIFIED` operations and live mode refuses them.
- No LinkedIn session secrets or current query identifiers were available. This blocks core identity resolution and all live sections.
- Pagination is not implemented because no current response established cursor/count/termination semantics. “Full history” is not claimed.
- A missing key is classified as `not_provided` only for a successful fixture contract. Live hiddenness is never inferred from absence alone.
- The in-process caller limiter is appropriate for one challenge container. Multiple replicas would need an ingress-level shared limiter, not an unmeasured Redis addition.
- No public HTTPS service or external latency evidence is available. Deployment files are prepared, but provider access is external to the repository.
- The container builds and passes local health/profile smoke tests. This is not public deployment evidence.
- LinkedIn may change operations, response entities, query IDs, viewer behavior, and access controls without notice. The registry/parser boundary controls failure; it cannot guarantee upstream stability.
- This project does not claim LinkedIn approval, platform-policy compliance, legal authorization for production scraping, GDPR/DPDP compliance, or universal profile completeness.
- PhantomBuster was not run on comparable profiles, so no speed or coverage superiority is claimed.
