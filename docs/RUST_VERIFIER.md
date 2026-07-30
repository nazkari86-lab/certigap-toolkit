# Standalone Rust Verifier

`rust-verifier` is a separate executable for
`certigap-pruned-beam-v1` artifacts. It does not import the Python package or
link the C++ solver.

It independently checks:

- schema and numeric input validity;
- complete contiguous tree ownership;
- split thresholds and split budget;
- fallback costs for every key;
- normalized average and maximum cost;
- robust objective;
- entropy/max-cost lower bound;
- absolute and relative instance-specific gaps.

Build and run:

```bash
cargo build --release --manifest-path rust-verifier/Cargo.toml
rust-verifier/target/release/certigap-verifier \
  results/pruned_beam_certificate_example.json
```

The verifier intentionally does not claim that candidate pruning is close to
optimal. It proves that the exported tree is feasible and that the optimum lies
between the replayed lower bound and the tree's objective.

