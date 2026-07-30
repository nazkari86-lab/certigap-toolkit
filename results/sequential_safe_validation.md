# Sequential Safe AutoIndex validation

- Deployment scenarios: `4`.
- Candidate approvals: `2`.
- Replay-verified certificates: `4/4`.
- Stable evidence approves at the first valid prefix.
- Small samples and migration-dominated horizons fail closed.
- Post-stop reversal does not retroactively change deployment; `6512` operations remain evaluation-only.
- Mean-zero Monte Carlo false approvals: `0/5000` for alpha spending versus `576/5000` for invalid repeated fixed-time checks.

The confidence-sequence theorem is conditional on independent IID bounded validation operations. The Monte Carlo row is a diagnostic, not a proof and not evidence for arbitrary drift.
