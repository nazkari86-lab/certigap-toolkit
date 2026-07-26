# CertiGap Abstract

CertiGap studies a static search problem under two constraints: only a limited number of threshold comparisons may be materialized in advance, and the predicted query distribution may be wrong.
Instead of forcing a fully resolved search structure, CertiGap allows unresolved interval leaves and optimizes which parts of the order are worth materializing.

The project contributes:

1. an exact generalized frontier dynamic program for deterministic executable fallbacks;
2. a scalable candidate-pruned C++ heuristic and an unbounded-gap result for one-step greedy;
3. structural, entropy-bound, proof-trace, and rational-arithmetic verification layers;
4. exact finite-support TV-DRO candidate evaluation and auditable automatic portfolio selection;
5. reproducible synthetic, public-workload, temporal, shift, and matched-budget C++ benchmarks.

Current prototype evidence:

- Rows analyzed: `240`
- Mean greedy absolute objective gap vs exact: `0.0986`
- Mean beam absolute objective gap vs exact: `0.0006`
- Mean greedy relative objective gap vs exact: `2.80%`
- Mean beam relative objective gap vs exact: `0.02%`
- Beam strictly improves on greedy in `104` rows
- Beam matches exact in `237` rows

These results support the main claim that optimizing how much order to materialize is both algorithmically nontrivial and measurably better than simple greedy or balanced baselines on skewed workloads.
