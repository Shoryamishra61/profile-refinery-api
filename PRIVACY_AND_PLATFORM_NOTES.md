# Privacy and Platform Notes

Engineering risk memo, not legal advice.

LinkedIn profile data is identifiable personal data. LinkedIn's current contractual terms, as recorded in the supplied primary-source research, restrict scraping/copying profiles and bypassing access controls. The Tross challenge nevertheless asks for reverse engineering and direct endpoint calls. This repository states that tension and does not claim LinkedIn approval.

Risk reduction in the implementation:

- validate only owned/consented profiles during research and evaluation;
- use one developer-owned session, never stolen sessions or account farms;
- collect only assignment fields; no email/contact enrichment;
- process ephemerally with no people database or raw payload logs;
- carry viewer context and observation time because visibility is contextual;
- fail closed on challenge and avoid access-control bypass behavior;
- use synthetic checked-in fixtures and independently authored expected results.

Before any real deployment, the operator must establish a lawful basis, retention/access/deletion processes, jurisdiction-specific notices, a platform-risk decision, and incident response. “Publicly visible” does not make personal data privacy-exempt.

