# Final Release Agent Prompt

Act as release engineer + Tross evaluator. Do not add features.

From clean clone: install; lint/type/test; fixture benchmark; verify independent ground truth; no-browser dependency scan; secret scan; start fixture/live modes; run controlled live benchmark; deploy; call public HTTPS endpoint; reproduce README exactly.

Audit every README/RESULTS claim for fixture vs live vs deployment, sample size, direct endpoint evidence, unsupported performance, safe-limit/full-history/compliance overclaims.

Produce final README, RESULTS, LIMITATIONS, JUDGE_AUDIT, REPRODUCIBILITY, DEMO. No self-awarded PASS without executable evidence.
