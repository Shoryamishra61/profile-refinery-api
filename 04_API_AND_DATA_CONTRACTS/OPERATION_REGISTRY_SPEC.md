# Operation Registry Specification

```yaml
version: 1
operations:
  profile_core:
    enabled: false
    evidence_status: unknown
    transport_family: graphql
    method: POST
    path: /voyager/api/graphql
    query_id_env: LINKEDIN_PROFILE_CORE_QUERY_ID
    parser: profile_core_v1
    observed_at: null
    fixture: null
  experience:
    enabled: false
    evidence_status: historical
    transport_family: unknown
    method: null
    path: null
    parser: experience_v1
    observed_at: null
```

Production starts with no unverified operation enabled. GraphQL identifiers are injected from config/environment. Registry validation rejects enabled operations without `live_verified` evidence, observation date, parser, and required identifier.
