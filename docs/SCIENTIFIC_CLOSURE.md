# Scientific Closure Status

## Completed Internally

- Exact frontier DP, independent cost-cap DP, brute-force checks, and proof-carrying exact branch-and-bound.
- Mathematical proofs for the robust objective identity and frontier-DP exactness, plus an infinite unbounded-gap family for one-step greedy.
- Public workload provenance, synthetic stress distributions, and a complete maximum Python benchmark range.
- Candidate-pruned C++ beam with a 432-case exact-oracle ablation: candidate limit 16 has mean relative gap 0.04% on that suite.
- A timestamped MovieLens early-to-late holdout. On tested ranks, eta 0.15/0.30 reduces future worst-case cost while increasing the training objective.

## Honest Boundaries

- The C++ pruned beam is empirical: it has no approximation theorem and no proof certificate.
- The exact DP recurrence is mathematically exact, while the current implementation uses floating-point dominance with `EPS`; rational verification is future work.
- Movie identifier order is not semantic locality; the temporal result is one public dataset, not a production deployment claim.
- Runtime measurements are machine-specific.

## External Work Required For A Literal 10/10 Claim

These cannot be completed truthfully by local code generation:

1. Independent reproduction on a separate machine and review of raw artifacts.
2. External mathematical or machine-assisted verification of the written proofs.
3. A domain-owner pilot with a naturally ordered production lookup catalog and a preregistered latency/memory protocol.
4. Literature-reviewed comparison against external robust BST and learned-index implementations under matched resource budgets.
