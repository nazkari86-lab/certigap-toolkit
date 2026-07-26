from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

from certigap import verify_autodro_selection_artifact


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"


def csv_rows(name: str) -> tuple[list[str], int]:
    path = RESULTS / name
    if not path.exists() or path.stat().st_size == 0:
        raise ValueError(f"{name} is missing or empty")
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        return list(reader.fieldnames or []), len(rows)


def validate_artifacts(require_max_scaling: bool = True) -> dict[str, int]:
    minimum_rows = {
        "experiment_sweep.csv": 240,
        "exact_cross_validation.csv": 336,
        "pruning_validation.csv": 432,
        "scaling_benchmark.csv": 450 if require_max_scaling else 1,
        "speed_quality.csv": 1_152,
        "temporal_holdout.csv": 9,
        "cpp_lookup_latency.csv": 24,
        "autodro_shift.csv": 24,
    }
    observed: dict[str, int] = {}
    for name, minimum in minimum_rows.items():
        _, count = csv_rows(name)
        if count < minimum:
            raise ValueError(f"{name} has {count} rows; expected at least {minimum}")
        observed[name] = count

    scaling_text = (RESULTS / "scaling_benchmark.md").read_text(encoding="utf-8")
    match = re.search(r"- Rows: `(\d+)`", scaling_text)
    if match is None or int(match.group(1)) != observed["scaling_benchmark.csv"]:
        raise ValueError("scaling Markdown row count disagrees with its CSV")

    lookup_fields, _ = csv_rows("cpp_lookup_latency.csv")
    required_lookup_fields = {
        "budget",
        "fallback",
        "median_batch_ns_per_query",
        "p95_batch_ns_per_query",
        "auxiliary_bytes",
        "total_index_bytes",
    }
    if not required_lookup_fields.issubset(lookup_fields):
        raise ValueError("lookup CSV uses an obsolete or incomplete schema")

    provenance = json.loads((RESULTS / "benchmark_provenance.json").read_text(encoding="utf-8"))
    loaded_sources = [
        record for record in provenance.values()
        if isinstance(record, dict) and record.get("status") == "loaded"
    ]
    if len(loaded_sources) < 3 or any(not record.get("sha256") for record in loaded_sources):
        raise ValueError("benchmark provenance contains no source records")
    lookup_metadata = json.loads((RESULTS / "cpp_lookup_metadata.json").read_text(encoding="utf-8"))
    if lookup_metadata.get("measurement_scope") != "post-build lookup; p95 across batch means":
        raise ValueError("lookup benchmark metadata is missing or ambiguous")
    autodro_artifact = json.loads(
        (RESULTS / "autodro_selection_example.json").read_text(encoding="utf-8")
    )
    verify_autodro_selection_artifact(autodro_artifact)
    return observed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate generated CertiGap artifacts.")
    parser.add_argument(
        "--allow-nonmax-scaling",
        action="store_true",
        help="Accept a quick/full scaling run instead of the published max matrix.",
    )
    args = parser.parse_args()
    rows = validate_artifacts(require_max_scaling=not args.allow_nonmax_scaling)
    print("Artifact integrity verified:", ", ".join(f"{name}={count}" for name, count in rows.items()))
