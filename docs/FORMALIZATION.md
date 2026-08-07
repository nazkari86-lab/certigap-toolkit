# Lean Formalization

`formal/CertiGap.lean` is a deliberately small machine-checked kernel for the
fixed-point Pareto-pruning argument.

It proves:

1. If one DP state is no worse in both average and maximum coordinates, every
   non-negative scalarization also scores it no worse.
2. The ordering remains safe after adding the same non-negative continuation
   cost to both states.
3. For integer scores satisfying `OPT <= restricted <= beam`, the total
   heuristic gap is exactly the sum of the candidate-pruning and
   beam-truncation gaps. This is the machine-checked algebraic kernel of
   Corollary Q.2; the floating-point implementation is cross-validated by the
   generated decomposition table.

The checked-in `lean-toolchain` pins the exact Lean 4 release. Run:

```bash
elan show
lean formal/CertiGap.lean
```

This is not a formalization of recurrence completeness, the C++ runtime, or
the complete CertiGap paper. Theorem Q has a full written inductive proof and
independent proof-sized exhaustive validation; Lean currently checks its
dominance and gap-decomposition kernels, not the complete recurrence. Those
remaining formalization layers stay explicit future work.
