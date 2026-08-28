# Results

## Verified offline results

Evidence class: `FIXTURE_VERIFIED`.

On 2026-08-27, the release verification produced:

| Gate | Result | Sample size |
|---|---:|---:|
| pytest | PASS | 57 tests |
| Ruff | PASS | 18 production modules plus tests/scripts |
| mypy strict | PASS | 18 production modules |
| required primitive correctness | 100% | 4/4 fields, 1 synthetic case |
| nested entry recall | 100% | 8/8 entries, 1 synthetic case |
| availability-status accuracy | 100% | 12/12 fields, 1 synthetic case |
| provenance coverage | 100% | 12/12 fields, 1 synthetic case |
| fixture operation count | 6 | 1 synthetic profile |
| browser production dependencies | 0 | production manifest/source scan |
| clean-clone verification | PASS | sync + 54 tests + benchmark + security scan |
| container verification | PASS | image build + health + authenticated fixture profile |
| public repository | PARTIAL | cleaned public source/docs; active CI upload blocked by OAuth workflow scope |
| maintained Markdown | PASS | 56 files linted; 57 local link targets resolved |
| public Vercel service | PARTIAL | HTTPS/health deployed; live profile path intentionally returns 503 until current operations exist |
| live fixture-leak regression | PASS | three unrelated real URLs returned 503 with zero fixture sentinels |

The benchmark runs ten local pipeline iterations and reports local p50/p95 each time. Those timings are deliberately not frozen as a performance claim because they vary by machine and do not include LinkedIn or public HTTPS.

## Not measured

No controlled-live profile set, current direct operation, PhantomBuster run, live latency, or live field recall was available. The Vercel deployment is externally reachable but not extraction-ready. Direct unauthenticated LinkedIn requests for three unrelated profiles returned 429 and no profile-specific payload. These metrics are `UNKNOWN`; fixture values are not substitutes.
