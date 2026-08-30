# Privacy and Platform Notes

This is an engineering risk note, not legal advice.

LinkedIn profile records are identifiable personal data. An operator must establish authorization and a lawful basis before processing them, observe applicable platform terms, and provide suitable retention, access, deletion, and incident-response controls.

Profile Refinery minimizes exposure by accepting only strict member URLs, supporting owned request-scoped sessions, avoiding contact enrichment, processing credentials only in memory, suppressing response caching, excluding raw payloads and secrets from logs, and failing closed on challenges or unknown semantic structures. It does not automate login, solve CAPTCHAs, rotate accounts or proxies, forge challenge tokens, spoof fingerprints, or bypass access controls.

Visibility is contextual to a viewer and observation time. The response therefore preserves provenance and availability instead of treating an absent field as universally absent. Production operators should minimize collected fields, restrict access, define retention, and validate their legal and platform-risk position independently.
