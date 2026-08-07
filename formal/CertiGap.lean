/-
  Machine-checked kernel for CertiGap's fixed-point Pareto pruning.

  Scores are non-negative integer units. `nominalWeight` and `tailWeight`
  represent a common scalarization. The theorem states that a state no worse
  in both Pareto coordinates can safely replace a dominated state.
-/

def scalarScore
    (nominalWeight tailWeight average maximum : Nat) : Nat :=
  nominalWeight * average + tailWeight * maximum

theorem dominance_safe
    (nominalWeight tailWeight : Nat)
    (average₁ average₂ maximum₁ maximum₂ : Nat)
    (hAverage : average₁ ≤ average₂)
    (hMaximum : maximum₁ ≤ maximum₂) :
    scalarScore nominalWeight tailWeight average₁ maximum₁ ≤
      scalarScore nominalWeight tailWeight average₂ maximum₂ := by
  unfold scalarScore
  exact Nat.add_le_add
    (Nat.mul_le_mul_left nominalWeight hAverage)
    (Nat.mul_le_mul_left tailWeight hMaximum)

theorem dominance_safe_after_common_additive_extension
    (nominalWeight tailWeight : Nat)
    (average₁ average₂ maximum₁ maximum₂ : Nat)
    (extraAverage extraMaximum : Nat)
    (hAverage : average₁ ≤ average₂)
    (hMaximum : maximum₁ ≤ maximum₂) :
    scalarScore nominalWeight tailWeight
        (average₁ + extraAverage) (maximum₁ + extraMaximum) ≤
      scalarScore nominalWeight tailWeight
        (average₂ + extraAverage) (maximum₂ + extraMaximum) := by
  apply dominance_safe
  · exact Nat.add_le_add_right hAverage extraAverage
  · exact Nat.add_le_add_right hMaximum extraMaximum

/-
  Algebraic kernel of the candidate-pruning / beam-truncation decomposition.
  `optimum`, `restricted`, and `beam` are integer-unit scores.  The practical
  implementation uses floating point, so its generated table separately
  checks the residual numerically.
-/
theorem candidate_pruning_gap_decomposition
    (optimum restricted beam : Nat)
    (hOptimum : optimum ≤ restricted)
    (hRestricted : restricted ≤ beam) :
    beam - optimum = (beam - restricted) + (restricted - optimum) := by
  omega
