# CertiGap Theme

## Final Topic

**CertiGap: budgeted robust partial search trees with certified near-optimality**

## One-Sentence Contribution

We optimize **how much order to materialize** under a strict split budget, under **unreliable query predictions**, and return a solution together with a **verifiable certificate of its quality**.

## Central Research Question

Given sorted keys, a predicted query distribution, and a budget `B` on materialized threshold comparisons, which parts of the order should be resolved in advance and which should remain unresolved intervals, so that the resulting search structure is both efficient under the prediction and robust when the prediction is wrong?

## Main Claim To Build Toward

For the budgeted partial-search model with interval leaves and contamination robustness, CertiGap can produce:

1. an exact optimum on small and medium instances;
2. a scalable heuristic on larger instances;
3. a certificate containing an upper bound, a lower bound, and a gap between them.

## What Must Stay Out Of Scope

- insertions and deletions;
- real DBMS integration;
- hardware/cache-level claims as the main story;
- neural or LLM components;
- multidimensional data.

## Objective Positioning

This is a **theory-first informatics project**, not an AI application and not a systems-only benchmark.
