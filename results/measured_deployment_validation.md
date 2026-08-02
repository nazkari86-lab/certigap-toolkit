# Measured Deployment Gate Validation

Deterministic boundary cases for the paired bounded-harm decision.
These are synthetic latency pairs, not hardware benchmark results.

| Scenario | Mean harm | Upper bound | Deploy | Passed |
|---|---:|---:|---:|---:|
| strong_win | -0.900000 | -0.594032 | True | True |
| weak_win | -0.100000 | 0.205968 | False | True |
| parity | 0.000000 | 0.305968 | False | True |
| regression | 0.166667 | 0.472635 | False | True |
