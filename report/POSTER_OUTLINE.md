# CertiGap Poster Outline

## Panel 1: Problem

- Full search structures materialize too much order under a strict split budget.
- Predictions can help, but they can also be wrong.

## Panel 2: Idea

- Build a partial search tree with interval leaves.
- Optimize `(1 - eta) * average_cost + eta * max_cost`.
- Return a solution with a checker and certified bounds.

## Panel 3: Algorithms

- Exact frontier DP
- Beam-search heuristic
- Entropy + Lagrangian lower bounds

## Panel 4: Results

# CertiGap Experiment Summary

## Global Summary

- Rows analyzed: `240`
- Mean greedy gap vs exact: `0.0986`
- Mean beam gap vs exact: `0.0006`
- Beam strictly improves on greedy in `104` rows
- Beam matches exact in `237` rows

## By Distribution

| Distribution | Mean Greedy Gap | Mean Beam Gap | Beam Better Rows |
|---|---:|---:|---:|
| hot_middle | 0.2485 | 0.0000 | 40 |
| hot_tail | 0.0446 | 0.0023 | 17 |
| uniform | 0.0255 | 0.0000 | 9 |
| zipf | 0.0758 | 0.0000 | 38 |

## Top Beam Improvements

| Distribution | n | B | eta | Greedy Gap | Beam Gap |
|---|---:|---:|---:|---:|---:|
| hot_middle | 12 | 4 | 0.00 | 0.8750 | 0.0000 |
| hot_middle | 24 | 4 | 0.00 | 0.8750 | 0.0000 |
| hot_middle | 12 | 3 | 0.00 | 0.7500 | 0.0000 |
| hot_middle | 24 | 3 | 0.00 | 0.7500 | 0.0000 |
| hot_middle | 12 | 3 | 0.15 | 0.6375 | 0.0000 |
| hot_middle | 12 | 4 | 0.15 | 0.6375 | 0.0000 |
| hot_middle | 24 | 3 | 0.15 | 0.6375 | 0.0000 |
| hot_middle | 24 | 4 | 0.15 | 0.6375 | 0.0000 |
| hot_middle | 16 | 4 | 0.00 | 0.6154 | 0.0000 |
| hot_middle | 8 | 4 | 0.00 | 0.5769 | 0.0000 |

## Counterexample Note

See `counterexamples.md` for automatically discovered hot-block families where one-step greedy is much worse than exact while beam recovers the optimum.

## Panel 5: Best Beam Improvements

| Distribution | n | B | eta | Greedy Gap | Beam Gap |
|---|---:|---:|---:|---:|---:|
| hot_middle | 12 | 4 | 0.00 | 0.8750 | 0.0000 |
| hot_middle | 24 | 4 | 0.00 | 0.8750 | 0.0000 |
| hot_middle | 12 | 3 | 0.00 | 0.7500 | 0.0000 |
| hot_middle | 24 | 3 | 0.00 | 0.7500 | 0.0000 |
| hot_middle | 12 | 3 | 0.15 | 0.6375 | 0.0000 |
| hot_middle | 12 | 4 | 0.15 | 0.6375 | 0.0000 |
| hot_middle | 24 | 3 | 0.15 | 0.6375 | 0.0000 |
| hot_middle | 24 | 4 | 0.15 | 0.6375 | 0.0000 |
| hot_middle | 16 | 4 | 0.00 | 0.6154 | 0.0000 |
| hot_middle | 8 | 4 | 0.00 | 0.5769 | 0.0000 |

## Counterexample Note

See `counterexamples.md` for automatically discovered hot-block families where one-step greedy is much worse than exact while beam recovers the optimum.
