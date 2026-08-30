# Consolidated Research Synthesis

## Established

- Profile Refinery explicitly requires direct endpoint runtime and no browser.
- Official LinkedIn APIs do not provide unrestricted arbitrary rich-profile URL lookup for this task.
- LinkedIn Engineering documents Rest.li, pre-registered GraphQL, multi-service Profile architecture, and GraphQL-powered rearchitected Profile framework.
- PhantomBuster's current Profile Scraper is the relevant prior art; Profile Visitor is browser-visit oriented and architecturally disallowed here.

## Not established

The corpus does **not** prove one permanent GraphQL query ID, universal section paths, a session lifetime, a safe daily request rate, a telemetry-silence threshold, a need for residential proxies/JA4 spoofing, live sub-1.5s latency, live 100% recall, or exact media expiry behavior.

## Research model

Target = information observable for profile **P**, backend viewer **V**, at time **T**, through currently enabled operation set **O**.

The API should promise observed structured data + explicit availability/provenance, not a metaphysical “universal full LinkedIn profile.”

## Best contribution

Current-operation evidence registry + viewer-aware ground truth + nested schema + provenance + partial results + drift handling + reproducibility + honest benchmarks.

The existing ~150-source corpus is already enough. New external research should be triggered only by a concrete unresolved build decision.
