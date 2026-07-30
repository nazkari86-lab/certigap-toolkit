# CertiGap Theme

## Final Topic

**CertiGap: certified workload-adaptive synthesis and selection of ordered
in-memory structures**

## One-Sentence Contribution

We synthesize or select an ordered in-memory structure inside an explicit finite
design space, optimize its structural cost under workload and resource
constraints, and emit a replay-verifiable artifact that states exactly what was
and was not proved.

## Central Research Question

Given ordered data, supported operations, a measured workload, and resource
constraints, which legal representation should be materialized so that modeled
work is minimized without claiming optimality outside the declared design
space?

## Main Claim To Build Toward

For each declared finite grammar or portfolio, CertiGap aims to produce:

1. an exact optimum and replayable winner when exhaustive dynamic programming
   is tractable;
2. a feasible incumbent and certified interval for supported anytime paths;
3. an explicitly labelled empirical heuristic when neither guarantee is
   available;
4. native measurements separated from structural certificates.

The claim-by-claim source of truth is [`CLAIMS.md`](CLAIMS.md).

## What Must Stay Out Of Scope

- insertions and deletions;
- production DBMS claims before a real integration exists;
- portable hardware/cache claims from single-machine measurements;
- neural or LLM components;
- multidimensional data.

## Objective Positioning

This is a **theory-first informatics project with executable systems
validation**, not an AI application and not a systems-only benchmark.
