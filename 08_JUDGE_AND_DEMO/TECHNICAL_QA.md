# Likely Technical Q&A

**Why no browser?** Profile Refinery explicitly prohibited it.

**Why Rest.li/GraphQL?** LinkedIn Engineering publicly documents both and says GraphQL powers the rearchitected Profile framework.

**Query-ID drift?** IDs live in registry/config with observation timestamps; invalid operation is a controlled drift state.

**Completeness proof?** Independent consented ground truth for what viewer V can observe at time T.

**Why partial responses?** Optional sections can drift independently; valid core data should survive.

**Secrets?** runtime-only injection, no HAR/secrets in repo, structured allowlist logs, secret scan.

**SSRF?** input becomes slug only; caller never controls outbound host/path.

**Do you bypass CAPTCHA/WAF?** No. Checkpoint is fail-closed/manual recovery.

**100% metrics?** Only if controlled-live report independently proves them. Fixture metrics are labeled fixture-only.

**Database?** not required; ephemeral processing minimizes scope.

**LLM?** upstream data is structured; deterministic parsers are more testable and auditable.
