from __future__ import annotations

import csv
import tempfile
from pathlib import Path

from certigap import AdaptiveArray, AdaptiveArrayPolicy, AutoIndexConstraints


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"


def make_policy(**overrides: object) -> AdaptiveArrayPolicy:
    values: dict[str, object] = {
        "warmup_operations": 32,
        "check_interval": 32,
        "minimum_relative_improvement": 0.01,
        "max_profile_operations": 128,
    }
    values.update(overrides)
    return AdaptiveArrayPolicy(**values)  # type: ignore[arg-type]


def row(scenario: str, data: AdaptiveArray, answer: float, expected: float) -> dict:
    explanation = data.explain()
    return {
        "scenario": scenario,
        "selected": data.selected_name,
        "switched": explanation["switched"],
        "optimized": data.optimized,
        "answer": answer,
        "expected": expected,
        "profile_operations": data.profile_operations,
        "lifetime_operations": data.lifetime_operations,
        "passed": abs(answer - expected) <= 1e-9,
    }


def generate() -> list[dict]:
    rows: list[dict] = []

    ranged = AdaptiveArray(range(64), policy=make_policy())
    answer = 0.0
    for _ in range(32):
        answer = ranged.range_sum(2, 60)
    rows.append(row("automatic_range_warmup", ranged, answer, sum(range(2, 60))))

    points = AdaptiveArray(range(64), policy=make_policy())
    for operation in range(32):
        answer = points.get(operation % 4)
    rows.append(row("automatic_point_warmup", points, answer, 3.0))

    mixed = AdaptiveArray(range(64), policy=make_policy())
    oracle = [float(value) for value in range(64)]
    for operation in range(32):
        if operation % 3 == 0:
            oracle[operation] = float(operation * 2)
            mixed.update(operation, oracle[operation])
        else:
            answer = mixed.range_sum(2, 60)
    rows.append(row("mixed_update_workload", mixed, answer, sum(oracle[2:60])))

    rejected = AdaptiveArray(
        range(64),
        policy=make_policy(minimum_relative_improvement=2.0),
    )
    for _ in range(32):
        answer = rejected.range_sum(2, 60)
    rejected_row = row(
        "deployment_threshold_rejection",
        rejected,
        answer,
        sum(range(2, 60)),
    )
    rejected_row["passed"] = rejected_row["passed"] and not rejected.optimized
    rows.append(rejected_row)

    explicit = AdaptiveArray(
        range(64),
        constraints=AutoIndexConstraints(aggregate="min"),
        policy=make_policy(automatic_maintenance=False),
    )
    for _ in range(32):
        answer = explicit.range_query(2, 60)
    switched = explicit.maintenance()
    explicit_row = row("explicit_maintenance", explicit, answer, 2.0)
    explicit_row["passed"] = explicit_row["passed"] and switched
    rows.append(explicit_row)

    with tempfile.TemporaryDirectory() as directory:
        profile_path = Path(directory) / "catalog.profile"
        persistent_policy = make_policy(profile_path=profile_path)
        with AdaptiveArray(range(64), policy=persistent_policy) as writer:
            for _ in range(32):
                answer = writer.range_sum(2, 60)
            rows.append(
                row("profile_writer", writer, answer, sum(range(2, 60)))
            )
        reader = AdaptiveArray(range(64), policy=persistent_policy)
        answer = reader.range_sum(2, 60)
        rows.append(row("profile_reader", reader, answer, sum(range(2, 60))))

    return rows


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    rows = generate()
    output = RESULTS / "python_adaptive_array_validation.csv"
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    markdown = [
        "# Python AdaptiveArray Validation",
        "",
        "Deterministic semantic and lifecycle checks for the public Python API.",
        "",
        "| Scenario | Selected | Optimized | Passed |",
        "|---|---|---:|---:|",
    ]
    markdown.extend(
        f"| {record['scenario']} | {record['selected']} | "
        f"{record['optimized']} | {record['passed']} |"
        for record in rows
    )
    (RESULTS / "python_adaptive_array_validation.md").write_text(
        "\n".join(markdown) + "\n",
        encoding="utf-8",
    )
    if not all(record["passed"] for record in rows):
        raise RuntimeError("Python AdaptiveArray validation failed")
    print(f"Wrote {len(rows)} rows to {output}")


if __name__ == "__main__":
    main()
