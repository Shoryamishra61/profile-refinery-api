# Source of Truth
When materials disagree, use this order:
1. Tross challenge + no-browser clarification
2. current controlled live observation
3. current official LinkedIn docs / LinkedIn Engineering
4. standards/security specs
5. current PhantomBuster first-party docs
6. court/regulator primary records for risk statements
7. current executable source/tests
8. historical open-source wrappers
9. vendor/practitioner blogs
10. generated research prose

## Current externally rechecked foundations
- LinkedIn User Agreement effective 3 Nov 2025 prohibits scraping/copying profiles and bypassing access controls/use limits.
- Current Profile API is restricted; its documentation says other-member Profile API data may not be stored.
- `r_fullprofile` is currently closed.
- `/identityMe` is consented OAuth, not arbitrary rich profile-by-URL.
- LinkedIn Engineering documents Rest.li plus pre-registered GraphQL and says the rearchitected Profile framework uses GraphQL.
- LinkedIn Engineering describes Profile as view/component based and multi-service.
- PhantomBuster currently distinguishes API-call-oriented Profile Scraper from browser-visit Profile Visitor.

These support the research direction. They do not prove any specific private endpoint path in the legacy matrix.
