# Related Work And Positioning

## Comparison Matrix

| Line of work | Ordered keys | Objective | Partial materialization with interval fallback | Robust contamination objective |
|---|---:|---|---:|---:|
| Hu--Tucker optimal alphabetic trees | yes | expected weighted path length | no | no |
| Scenario-based robust BSTs (AAAI-25) | yes | scenario regret / competitive ratio | no | no |
| Dinitz et al. distributional predictions | yes | entropy plus earth-mover prediction error | no | different uncertainty model |
| PGM-index | ordered predecessor queries | space-time learned-index tradeoff | different model | no |
| CertiGap | yes | average plus worst-case contamination risk | yes | yes |

CertiGap must not be described as the first robust search-tree method. Its
research claim is narrower: it studies the combination of a budgeted set of
materialized threshold comparisons, contiguous unresolved leaves with binary
fallback, and a contamination-robust objective.

## Primary Sources

1. T. C. Hu and A. C. Tucker, *Optimal Computer Search Trees and
   Variable-Length Alphabetical Codes*, SIAM J. Applied Mathematics, 1971.
   DOI: 10.1137/0121057.
2. S. Angelopoulos, C. Durr, A. Elenter, and G. Melidi, *Scenario-Based
   Robust Optimization of Tree Structures*, AAAI 2025.
   DOI: 10.1609/aaai.v39i25.34894.
3. P. Ferragina and G. Vinciguerra, *The PGM-index: a fully-dynamic
   compressed learned index with provable worst-case bounds*, PVLDB 2020.
4. M. Dinitz, S. Im, T. Lavastida, B. Moseley, A. Niaparast, and
   S. Vassilvitskii, *Binary Search with Distributional Predictions*,
   NeurIPS 2024. The work gives a distributionally robust optimal-BST result
   under earth mover's distance, not CertiGap's split budget, interval fallback,
   or contamination uncertainty set.

The project currently provides internal baseline implementations only.
Reproducing external robust-BST and learned-index code under matched memory,
hardware, and workload protocols remains future empirical work.
