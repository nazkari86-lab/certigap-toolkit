# CertiGap Abstract

CertiGap studies a static search problem under two constraints: only a limited number of threshold comparisons may be materialized in advance, and the predicted query distribution may be wrong.
Instead of forcing a fully resolved search structure, CertiGap allows unresolved interval leaves and optimizes which parts of the order are worth materializing.

The project contributes:

1. an exact frontier dynamic program for the budgeted robust partial-search model;
2. a stronger beam-search heuristic for larger instances;
3. a structural checker that recomputes the objective and attaches lower bounds plus certified gaps;
4. a reproducible synthetic benchmark suite.

Current prototype evidence:

- Rows analyzed: `240`
- Mean greedy gap vs exact: `0.0986`
- Mean beam gap vs exact: `0.0006`
- Beam strictly improves on greedy in `104` rows
- Beam matches exact in `237` rows

These results support the main claim that optimizing how much order to materialize is both algorithmically nontrivial and measurably better than simple greedy or balanced baselines on skewed workloads.
