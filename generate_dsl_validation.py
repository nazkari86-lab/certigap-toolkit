from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

from certigap import (
    ProofCarryingSpec,
    WorkloadTrace,
    compile_proof_carrying_index,
    verify_dsl_certificate,
)


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
N = 32
ALGEBRAS = ("sum", "min", "max")
CONTRACTS = (
    ("get",),
    ("range",),
    ("range", "update"),
    ("get", "range", "update"),
)
PROFILES = ("default", "tight_memory", "persistent_snapshot")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def training_trace(operations: tuple[str, ...]) -> WorkloadTrace:
    trace = WorkloadTrace(N)
    for step in range(96):
        key = 1 + (step * 7) % N
        if "update" in operations and step % 4 == 0:
            trace.add_update(key, float((step * 13) % 101 - 50))
        elif "range" in operations:
            left = 1 + (step * 3) % (N // 2)
            trace.add_range(left, N - (step % 5))
        else:
            trace.add_get(key)
    return trace


def aggregate(values: list[float], name: str) -> float:
    if name == "sum":
        return sum(values)
    if name == "min":
        return min(values)
    return max(values)


def replay(model, operations: tuple[str, ...], algebra: str) -> tuple[float, float]:
    oracle = [float(value) for value in range(N)]
    actual = 0.0
    expected = 0.0
    for step in range(160):
        key = 1 + (step * 11) % N
        if "update" in operations and step % 5 == 0:
            value = float((step * 17) % 127 - 63)
            model.point_update(key, value)
            oracle[key - 1] = value
        elif "range" in operations:
            left = 1 + (step * 5) % (N // 2)
            right = N - (step % 7)
            actual += model.range_query(left, right)
            expected += aggregate(oracle[left - 1 : right], algebra)
        else:
            actual += model.get(key)
            expected += oracle[key - 1]
    return actual, expected


def main() -> None:
    rows: list[dict] = []
    example: dict | None = None
    for algebra in ALGEBRAS:
        for operations in CONTRACTS:
            trace = training_trace(operations)
            for profile in PROFILES:
                keyword: dict = {}
                if profile == "tight_memory":
                    keyword["memory_limit_slots"] = N
                elif profile == "persistent_snapshot":
                    keyword["require_persistent_snapshots"] = True
                spec = ProofCarryingSpec(
                    operations=operations,
                    algebra=algebra,
                    **keyword,
                )
                model = compile_proof_carrying_index(range(N), trace, spec)
                certificate = model.export_certificate()
                verified = verify_dsl_certificate(certificate)
                actual, expected = replay(model, operations, algebra)
                rows.append(
                    {
                        "algebra": algebra,
                        "operations": "+".join(operations),
                        "profile": profile,
                        "selected_design": verified["selected_design"],
                        "selected_backend": verified["selected_backend"],
                        "design_count": verified["design_count"],
                        "feasible_design_count": verified["feasible_design_count"],
                        "typed_capabilities_verified": verified[
                            "typed_capabilities_verified"
                        ],
                        "grammar_completeness_verified": verified[
                            "grammar_completeness_verified"
                        ],
                        "runtime_checksum": format(actual, ".17g"),
                        "oracle_checksum": format(expected, ".17g"),
                        "runtime_matches_oracle": actual == expected,
                        "certificate_sha256": certificate["sha256"],
                    }
                )
                if (
                    example is None
                    and algebra == "sum"
                    and operations == CONTRACTS[-1]
                    and profile == "default"
                ):
                    example = certificate

    csv_path = RESULTS / "dsl_validation.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(
            output, fieldnames=list(rows[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    if example is None:
        raise RuntimeError("DSL example was not generated")
    example_path = RESULTS / "dsl_certificate_example.json"
    example_path.write_text(
        json.dumps(example, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )

    selected = Counter(row["selected_backend"] for row in rows)
    markdown = f"""# Proof-Carrying DSL Validation

The deterministic matrix covers `{len(rows)}` configurations: three canonical
algebras, four operation contracts, and three resource regimes. Every
configuration regenerates the complete typed grammar, independently verifies the
certificate, and replays 160 operations against a list oracle.

## Results

- Typed capability verification: `{all(row['typed_capabilities_verified'] for row in rows)}`.
- Grammar completeness verification: `{all(row['grammar_completeness_verified'] for row in rows)}`.
- Runtime/oracle checksum agreement: `{all(row['runtime_matches_oracle'] for row in rows)}`.
- Selected backend diversity: `{len(selected)}` backends.
- Selection counts: `{json.dumps(dict(sorted(selected.items())), sort_keys=True)}`.

## Boundary

The matrix validates the fixed-size DSL v1 grammar and built-in `sum`, `min`, and
`max` semantics. It does not establish portable latency optimality, arbitrary
user-defined algebra laws, insert/erase support, or global optimality outside the
declared eight-design grammar.
"""
    (RESULTS / "dsl_validation.md").write_text(markdown, encoding="utf-8")
    metadata = {
        "schema": "certigap-dsl-validation-v1",
        "configurations": len(rows),
        "algebras": list(ALGEBRAS),
        "contracts": ["+".join(value) for value in CONTRACTS],
        "profiles": list(PROFILES),
        "replay_operations": 160,
        "dsl_source_sha256": file_sha256(ROOT / "certigap" / "dsl.py"),
        "verifier_source_sha256": file_sha256(
            ROOT / "certigap" / "dsl_verifier.py"
        ),
        "generator_source_sha256": file_sha256(Path(__file__)),
        "csv_sha256": file_sha256(csv_path),
        "example_sha256": file_sha256(example_path),
    }
    (RESULTS / "dsl_validation.metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(markdown)


if __name__ == "__main__":
    main()
