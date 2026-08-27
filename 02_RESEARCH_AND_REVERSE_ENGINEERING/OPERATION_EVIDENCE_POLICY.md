# Operation Evidence Policy

No reverse-engineered operation is production-enabled without a record similar to:

```yaml
semantic_name: profile_core
status: live_verified
transport_family: graphql
method: POST
path: /voyager/api/graphql
query_id_env: LINKEDIN_PROFILE_CORE_QUERY_ID
variables: [member_identity]
parser: profile_core_v1
observed_at: 2026-08-27T00:00:00Z
viewer_context: owned_account
fixture: tests/fixtures/redacted/profile_core_v1.json
evidence: controlled_network_observation
```

## Prohibited
- historical route labeled live;
- secret/credential in registry;
- stability inferred from one observation;
- silent identifier replacement.

## Drift lifecycle
`live_verified -> suspect -> disabled -> reverified`

Registry change requires evidence update + fixture + parser test + reason.
