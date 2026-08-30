# Migration from Legacy Prototype

## Reuse carefully

URL canonicalization idea, entity assembler patterns, normalization helpers, Problem Details model, logging-redaction tests, field ontology, fixture concepts.

## Rewrite

- flat files -> real package;
- fake session pool -> validated environment settings;
- incomplete live GraphQL transport/resolver -> operation-registry-driven current payload;
- circular benchmark -> independent expected outputs;
- missing fixtures -> checked-in synthetic/redacted fixtures;
- fail-open schema -> strict startup;
- optional operator API key retained only for backend-session and batch routes;
- fabricated mock email -> remove;
- `/workspace/*` path hacks -> package-relative config/resources;
- aspirational README -> generated from actual final repo behavior.

Never “repair” a live function by guessing endpoint strings. Revalidate first.
