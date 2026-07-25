# Greedy Counterexample Family

## Proven Infinite Family

For every `m >= 3`, set:

- `n = 2^m`;
- split budget `B = 3`;
- `eta = 0`;
- hot block `[n/2, n/2 + 1]` with each hot key weight `W = n*m`;
- all other keys weight `1`.

The one-step greedy implementation makes no split: the central split is neutral and every off-centre split makes the two hot keys one comparison more expensive. A three-split witness isolates both hot keys at depth two.

The resulting greedy-to-optimum absolute objective gap is at least

`[2W(m - 2) - (n - 2)] / [2W + n - 2]`,

which is positive for every `m >= 3` and grows asymptotically as `m - 2`.

The executable construction is `power_of_two_greedy_family(m)`; generated rows for `m=3..10` are in `results/power_of_two_greedy_family.csv`.

## Historical Empirical Family

The most important discovered family has the following structure:

- the key set is contiguous and sorted;
- a short hot block of width `2` sits near the center;
- all surrounding keys are cold;
- the split budget is at least `3`.

Empirically, a one-step greedy rule often spends its first split too far away from the hot block, because that split gives the largest immediate reduction on a large cold region. Once that happens, the remaining budget is insufficient to isolate both hot keys efficiently.

By contrast, the global optimum first places a preparatory split near the hot block, then spends the remaining splits to isolate the two hot keys.

## Canonical Prototype Instance

As of **July 25, 2026**, the strongest automatically discovered fast-mode instance is:

- `n = 10`
- `B = 3`
- `eta = 0.00`
- hot block start `5`
- hot block width `2`
- hot weight `24.0`

Observed gaps:

- greedy gap vs exact: `1.642857`
- beam gap vs exact: `0.000000`

## Candidate Formal Proposition

There exists an infinite family of hot-block instances for which:

1. one-step greedy chooses a first split outside the eventual optimal refinement zone;
2. the exact optimum uses a sequence of preparatory splits adjacent to the hot block;
3. the objective gap between greedy and optimum stays bounded away from zero and can be scaled upward with the hot-to-cold weight ratio.

## What Still Needs To Be Proved

- a closed-form description of the family as a function of `m`;
- an argument that greedy's locally best first split is uniquely outside the optimal refinement zone;
- a lower bound on the resulting objective gap.

## Why This Matters

This family is the cleanest route to a real negative result in the project:

- it explains why CertiGap is not solved by a trivial local rule;
- it justifies the need for exact DP or stronger search;
- it strengthens the project beyond “we tried a few heuristics”.
