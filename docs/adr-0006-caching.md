# ADR-0006: Caching

## Context

Duplicate profiles across concurrent callers could multiply upstream work. At the
same time, stale data must never be presented as live extraction, and profile
facts must always carry their retrieval provenance.

## Decision

* **Request coalescing (implemented)**: one in-flight extraction per deterministic
  job id; concurrent duplicate requests share the result. Verified-success results
  are also reused across concurrent batches within the process.
* **Persistent result cache (deferred)**: no cross-request TTL cache. Reason: stale
  data must never be presented as live, and labeling stale-vs-live through the
  public schema adds contract surface with little benefit at the target batch size
  (N≈30). The upgrade path — canonical-URL-keyed cache with an explicit
  `retrieval.cached=true` flag plus `retrieved_at` freshness — is recorded here so
  the contract change is deliberate when it happens.

## Tradeoffs

Sequential repeat requests re-hit the upstream (bounded by the governor). In
exchange there is no possibility of cross-profile contamination and no risk of
representing cached data as newly retrieved.

## Consequences

Upstream amplification from duplicates is bounded by coalescing within the process
lifetime; cross-restart duplicates are bounded by the governor's rate budget.

## Validation

`test_request_coalescing_duplicate_profiles`.
