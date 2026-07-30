# Reproducibility Protocol

## Evidence Levels

Do not combine these levels into one claim:

1. Unit and property tests establish implementation invariants.
2. Artifact replay establishes consistency and completeness inside a declared
   model or portfolio.
3. Native benchmarks establish timing only for the recorded machine, compiler,
   build flags, and traces.
4. Independent reproduction requires a different machine and a reviewer who
   did not generate the committed results.
5. Production evidence requires naturally occurring traces and a domain-owner
   protocol.

## Fast Local Verification

```bash
python3 -m pip install -e '.[dev]'
python3 build_cpp_core.py
certigap reproduce --mode tests
certigap reproduce --mode artifacts
```

The artifact command checks row counts, provenance hashes, independent replay,
runtime checksums, benchmark metadata, and that reader-facing claims still
match the committed CSV evidence.

## Full Rebuild

```bash
certigap reproduce --mode full --benchmark-mode max
```

This regenerates source headers, native validations, exact and heuristic
matrices, public-frequency inputs, figures, report material, and package
artifacts before running the integrity verifier.

## Container

```bash
docker build -t certigap-toolkit:1.10.1 .
docker run --rm certigap-toolkit:1.10.1
```

The default container command runs the complete test suite. Native timings
inside Docker are not interchangeable with bare-metal results.

## Independent Machine Run

The independent reviewer should:

1. Record commit SHA, OS, CPU model, available memory, compiler, Python, and
   governor/power mode.
2. Run tests and artifact verification before generating new timings.
3. Run `generate_synthesis_native_benchmark.py` without editing workloads.
4. Preserve the generated CSV and metadata JSON before comparing results.
5. Report every scenario, including regressions and temporal shift.
6. Sign the result manifest or publish it in a repository controlled by the
   reviewer.

Minimum independent report fields:

```json
{
  "commit": "full git SHA",
  "cpu": "vendor and model",
  "os": "name and version",
  "compiler": "name and version",
  "python": "version",
  "commands": [],
  "artifact_sha256": {},
  "deviations": [],
  "reviewer": "independent identity or organization"
}
```

## Train, Validation, Test Rule

- Training traces may select partitions and backends.
- Validation traces may tune grammar limits and hyperparameters.
- Test traces are opened once after those choices are frozen.
- Native holdout operations must not be reused to alter candidate generation.
- Any post-test change creates a new experiment version and a new test set.

The current committed H benchmark has train and holdout roles but not a
separate validation corpus for grammar design. It must therefore be described
as development evidence rather than a final preregistered external test.
