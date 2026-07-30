from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from pathlib import Path

from certigap import (
    verify_anytime_tv_certificate,
    verify_autoindex_artifact,
    verify_autodro_selection_artifact,
    verify_dynamic_range_certificate,
    verify_range_optimizer_artifact,
)


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def csv_rows(name: str) -> tuple[list[str], int]:
    path = RESULTS / name
    if not path.exists() or path.stat().st_size == 0:
        raise ValueError(f"{name} is missing or empty")
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        return list(reader.fieldnames or []), len(rows)


def csv_records(name: str) -> list[dict[str, str]]:
    path = RESULTS / name
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def validate_artifacts(require_max_scaling: bool = True) -> dict[str, int]:
    minimum_rows = {
        "experiment_sweep.csv": 240,
        "exact_cross_validation.csv": 336,
        "pruning_validation.csv": 432,
        "scaling_benchmark.csv": 450 if require_max_scaling else 1,
        "speed_quality.csv": 1_152,
        "temporal_holdout.csv": 9,
        "cpp_lookup_latency.csv": 40,
        "autodro_shift.csv": 24,
        "direct_tv_validation.csv": 100,
        "uncertainty_validation.csv": 12,
        "online_adaptation.csv": 4,
        "anytime_validation.csv": 48,
        "dynamic_range_benchmark.csv": 36,
        "cpp_dynamic_range.csv": 36,
        "range_optimizer_validation.csv": 114,
        "autoindex_validation.csv": 120,
        "compiler_integration_validation.csv": 24,
        "adaptive_header_validation.csv": 24,
        "synthesis_validation.csv": 24,
        "synthesis_native_latency.csv": 40,
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
    lookup_workloads = {
        row["workload"] for row in csv_records("cpp_lookup_latency.csv")
    }
    if not {
        "uniform",
        "zipf",
        "hot_tail",
        "ycsb_hotspot_80_20",
        "ycsb_latest_biased",
    }.issubset(lookup_workloads):
        raise ValueError("lookup benchmark lacks required workload families")

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
    autodro_verified = verify_autodro_selection_artifact(autodro_artifact)
    if not autodro_verified["completeness_verified"]:
        raise ValueError("AutoDRO artifact does not verify portfolio completeness")

    shift_rows = csv_records("autodro_shift.csv")
    shift_groups: dict[tuple[str, str], dict[str, dict[str, str]]] = {}
    for row in shift_rows:
        shift_groups.setdefault((row["scenario"], row["n"]), {})[row["method"]] = row
    required_methods = {
        "tuned_tv_dro",
        "tuned_nominal",
        "fixed_beam",
        "fixed_balanced",
        "fixed_weighted",
    }
    if len(shift_groups) != 24 or any(set(group) != required_methods for group in shift_groups.values()):
        raise ValueError("AutoDRO shift matrix is incomplete")
    for group in shift_groups.values():
        tv, nominal = group["tuned_tv_dro"], group["tuned_nominal"]
        if tv["candidate_count"] != nominal["candidate_count"]:
            raise ValueError("TV and nominal portfolios have unequal candidate counts")
        for row in group.values():
            if not all(
                math.isfinite(float(row[field]))
                for field in ("test_mean_cost", "test_max_cost", "selection_seconds")
            ):
                raise ValueError("AutoDRO shift matrix contains non-finite metrics")

    direct_rows = csv_records("direct_tv_validation.csv")
    gaps = [float(row["heuristic_gap"]) for row in direct_rows]
    if any(gap < -1e-9 for gap in gaps):
        raise ValueError("direct TV exhaustive search lost to a heuristic subset")
    witnesses = [
        row
        for row in direct_rows
        if row["case_family"] == "fixed_tv_separation_witness"
    ]
    if len(witnesses) != 1 or float(witnesses[0]["heuristic_gap"]) <= 0.06:
        raise ValueError("direct TV separation witness is missing or too weak")
    if any(
        len(row["tree_space_sha256"]) != 64
        or "globally optimal" not in row["scope"]
        for row in direct_rows
    ):
        raise ValueError("direct TV validation lacks complete-space provenance")

    temporal_rows = csv_records("temporal_holdout.csv")
    temporal_groups: dict[str, set[str]] = {}
    for row in temporal_rows:
        temporal_groups.setdefault(row["n"], set()).add(row["method"])
    if set(temporal_groups) != {"32", "64", "128"} or any(
        methods != {"tuned_nominal", "tuned_tv_010", "tuned_tv_020"}
        for methods in temporal_groups.values()
    ):
        raise ValueError("temporal holdout matrix is incomplete")

    uncertainty_rows = csv_records("uncertainty_validation.csv")
    if any(float(row["empirical_coverage"]) < 0.95 for row in uncertainty_rows):
        raise ValueError("finite-sample TV coverage fell below its target")
    uncertainty_groups: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in uncertainty_rows:
        uncertainty_groups.setdefault((row["distribution"], row["n"]), []).append(row)
    for group in uncertainty_groups.values():
        ordered = sorted(group, key=lambda row: int(row["sample_size"]))
        radii = [float(row["mean_tv_radius"]) for row in ordered]
        if any(left <= right for left, right in zip(radii, radii[1:])):
            raise ValueError("mean inferred TV radius did not shrink with sample size")

    adaptation_rows = sorted(
        csv_records("online_adaptation.csv"),
        key=lambda row: float(row["drift_threshold"]),
    )
    rebuilds = [int(row["rebuilds_including_initial"]) for row in adaptation_rows]
    if any(left < right for left, right in zip(rebuilds, rebuilds[1:])):
        raise ValueError("higher drift threshold unexpectedly increased rebuild count")
    if abs(float(adaptation_rows[0]["mean_regret"])) > 1e-9:
        raise ValueError("always-refit adaptation does not match the oracle")

    anytime_rows = csv_records("anytime_validation.csv")
    exact_rows = [row for row in anytime_rows if row["phase"] == "exact_oracle"]
    if len(exact_rows) != 12 or any(
        abs(float(row["oracle_gap"])) > 1e-9
        or row["exact"] != "True"
        or row["verified"] != "True"
        for row in exact_rows
    ):
        raise ValueError("anytime exact-oracle validation failed")
    trajectories: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in anytime_rows:
        if row["phase"] == "scaling_trajectory":
            trajectories.setdefault((row["n"], row["distribution"]), []).append(row)
    if len(trajectories) != 9:
        raise ValueError("anytime scaling matrix is incomplete")
    for group in trajectories.values():
        ordered = sorted(group, key=lambda row: int(row["max_expansions"]))
        if [int(row["max_expansions"]) for row in ordered] != [0, 25, 100, 400]:
            raise ValueError("anytime expansion trajectory is incomplete")
        uppers = [float(row["score"]) for row in ordered]
        lowers = [float(row["global_lower_bound"]) for row in ordered]
        gaps = [float(row["relative_gap"]) for row in ordered]
        if (
            any(left < right - 1e-9 for left, right in zip(uppers, uppers[1:]))
            or any(left > right + 1e-9 for left, right in zip(lowers, lowers[1:]))
            or any(left < right - 1e-9 for left, right in zip(gaps, gaps[1:]))
        ):
            raise ValueError("anytime certified intervals are not monotone")
    anytime_artifact = json.loads(
        (RESULTS / "anytime_certificate_example.json").read_text(encoding="utf-8")
    )
    if not verify_anytime_tv_certificate(anytime_artifact)["verified"]:
        raise ValueError("anytime example certificate did not replay")

    dynamic_rows = csv_records("dynamic_range_benchmark.csv")
    if (
        {row["method"] for row in dynamic_rows}
        != {"array", "fenwick", "segment_tree", "certirange"}
        or any(row["correct"] != "True" for row in dynamic_rows)
    ):
        raise ValueError("Python dynamic range benchmark is incomplete")
    cpp_dynamic_rows = csv_records("cpp_dynamic_range.csv")
    if (
        {row["method"] for row in cpp_dynamic_rows}
        != {"array", "fenwick", "segment_tree", "certirange"}
        or any(row["correct"] != "true" for row in cpp_dynamic_rows)
    ):
        raise ValueError("C++ dynamic range benchmark is incomplete")
    cpp_dynamic_metadata = json.loads(
        (RESULTS / "cpp_dynamic_range_metadata.json").read_text(
            encoding="utf-8"
        )
    )
    if (
        cpp_dynamic_metadata.get("measurement_scope")
        != "post-build mixed operations; p95 across batch means"
    ):
        raise ValueError("C++ dynamic range measurement scope is ambiguous")

    autoindex_artifact = json.loads(
        (RESULTS / "autoindex_selection_example.json").read_text(
            encoding="utf-8"
        )
    )
    autoindex_verified = verify_autoindex_artifact(autoindex_artifact)
    if (
        not autoindex_verified["completeness_verified"]
        or autoindex_verified["candidate_count"] != 5
    ):
        raise ValueError("AutoIndex example does not prove portfolio completeness")
    autoindex_rows = csv_records("autoindex_validation.csv")
    autoindex_groups: dict[str, list[dict[str, str]]] = {}
    for row in autoindex_rows:
        autoindex_groups.setdefault(row["group_id"], []).append(row)
    expected_candidates = {
        "sorted_array",
        "fenwick",
        "segment_tree",
        "certirange_point",
        "certirange_range",
    }
    if len(autoindex_groups) != 24:
        raise ValueError("AutoIndex validation matrix is incomplete")
    for group in autoindex_groups.values():
        if (
            {row["candidate"] for row in group} != expected_candidates
            or len([row for row in group if row["selected"] == "True"]) != 1
            or any(row["certificate_verified"] != "True" for row in group)
        ):
            raise ValueError("AutoIndex portfolio is incomplete or unverified")
        selected = next(row for row in group if row["selected"] == "True")
        feasible_scores = [
            float(row["train_score"])
            for row in group
            if row["feasible"] == "True"
        ]
        if abs(float(selected["train_score"]) - min(feasible_scores)) > 1e-9:
            raise ValueError("AutoIndex selected a non-minimum training score")
        regret = float(selected["selected_holdout_regret"])
        if not math.isfinite(regret) or regret < -1e-9:
            raise ValueError("AutoIndex holdout regret is invalid")

    compiler_rows = csv_records("compiler_integration_validation.csv")
    if (
        len({row["group_id"] for row in compiler_rows}) != 24
        or any(
            row["candidate_count"] != "5"
            or row["artifact_verified"] != "True"
            or row["constraints_canonical"] != "True"
            or len(row["artifact_sha256"]) != 64
            or len(row["header_sha256"]) != 64
            or int(row["header_bytes"]) <= 0
            for row in compiler_rows
        )
    ):
        raise ValueError("compiler integration validation is incomplete")

    adaptive_rows = csv_records("adaptive_header_validation.csv")
    if (
        len(adaptive_rows) != 24
        or any(
            row["correct"] != "true"
            or row["candidate_count"] != "5"
            or not math.isfinite(float(row["score"]))
            or int(row["memory_slots"]) <= 0
            for row in adaptive_rows
        )
        or any(
            row["selected"] != "sorted_array"
            for row in adaptive_rows
            if row["scenario"] == "point_hot"
        )
        or any(
            row["selected"] != "segment_tree"
            for row in adaptive_rows
            if row["scenario"] in {"segment_calibrated", "minimum", "maximum"}
        )
        or any(
            not row["selected"].startswith("certirange")
            for row in adaptive_rows
            if row["scenario"] == "certirange_required"
        )
    ):
        raise ValueError("adaptive single-header validation is incomplete")

    synthesis_rows = csv_records("synthesis_validation.csv")
    if (
        len(synthesis_rows) != 24
        or any(
            row["certificate_verified"] != "true"
            or row["runtime_correct"] != "true"
            or int(row["candidate_count"]) <= 0
            or int(row["selected_blocks"]) <= 0
            or not math.isfinite(float(row["selected_certified_score"]))
            or float(row["relative_gain"]) < -1e-12
            for row in synthesis_rows
        )
        or sum(row["nonuniform"] == "true" for row in synthesis_rows) < 12
    ):
        raise ValueError("CertiGap-X synthesis validation is incomplete")

    native_rows = csv_records("synthesis_native_latency.csv")
    native_methods = {
        "array",
        "fenwick",
        "segment_tree",
        "uniform_block",
        "certigap_x",
    }
    native_groups: dict[str, list[dict[str, str]]] = {}
    for row in native_rows:
        native_groups.setdefault(row["scenario"], []).append(row)
    if (
        len(native_groups) != 8
        or any(
            {row["method"] for row in group} != native_methods
            or len(group) != len(native_methods)
            or len({row["checksum"] for row in group}) != 1
            for group in native_groups.values()
        )
        or any(
            row["correct"] != "true"
            or row["operations"] != "6000"
            or row["repeats"] != "9"
            or not math.isfinite(float(row["median_ns_per_operation"]))
            or float(row["median_ns_per_operation"]) <= 0.0
            or not math.isfinite(float(row["p95_batch_ns_per_operation"]))
            or float(row["p95_batch_ns_per_operation"])
            < float(row["median_ns_per_operation"])
            or not math.isfinite(float(row["mad_ns_per_operation"]))
            or float(row["mad_ns_per_operation"]) < 0.0
            for row in native_rows
        )
    ):
        raise ValueError("CertiGap-X native holdout matrix is incomplete")
    native_metadata = json.loads(
        (RESULTS / "synthesis_native_latency_metadata.json").read_text(
            encoding="utf-8"
        )
    )
    if (
        native_metadata.get("schema") != "certigap-native-benchmark-v1"
        or native_metadata.get("holdout_operations_per_scenario") != 6000
        or native_metadata.get("train_operations_per_scenario") != 800
        or native_metadata.get("repeats") != 9
        or set(native_metadata.get("methods", [])) != native_methods
        or "train trace only"
        not in native_metadata.get("selection_protocol", "")
        or len(native_metadata.get("cases", [])) != 8
        or len(native_metadata.get("limitations", [])) < 4
        or native_metadata.get("benchmark_source_sha256")
        != file_sha256(ROOT / "cpp" / "synthesis_native_benchmark.cpp")
        or native_metadata.get("generated_cases_sha256")
        != file_sha256(ROOT / "cpp" / "synthesis_native_cases.hpp")
        or native_metadata.get("results_sha256")
        != file_sha256(RESULTS / "synthesis_native_latency.csv")
    ):
        raise ValueError("CertiGap-X native provenance contract is incomplete")

    optimizer_rows = csv_records("range_optimizer_validation.csv")
    exact_optimizer_rows = [
        row for row in optimizer_rows if row["phase"] == "exact_oracle"
    ]
    if len(exact_optimizer_rows) != 6 or any(
        row["exact"] != "True" or abs(float(row["oracle_gap"])) > 1e-9
        for row in exact_optimizer_rows
    ):
        raise ValueError("range-aware optimizer lost exact-oracle agreement")
    optimizer_groups: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    for row in optimizer_rows:
        if row["phase"] == "scaling":
            optimizer_groups.setdefault(
                (row["n"], row["family"], row["budget"]), []
            ).append(row)
    if len(optimizer_groups) != 36 or any(
        {row["method"] for row in group}
        != {
            "balanced_completion",
            "point_endpoint_proxy",
            "range_aware_beam",
        }
        for group in optimizer_groups.values()
    ):
        raise ValueError("range-aware scaling matrix is incomplete")
    for group in optimizer_groups.values():
        aware = next(
            float(row["objective"])
            for row in group
            if row["method"] == "range_aware_beam"
        )
        if aware > min(float(row["objective"]) for row in group) + 1e-9:
            raise ValueError(
                "range-aware search lost to an included training candidate"
            )

    dynamic_artifact = json.loads(
        (RESULTS / "dynamic_range_certificate_example.json").read_text(
            encoding="utf-8"
        )
    )
    if not verify_dynamic_range_certificate(dynamic_artifact)["verified"]:
        raise ValueError("dynamic range certificate did not replay")
    optimizer_artifact = json.loads(
        (RESULTS / "range_optimizer_example.json").read_text(encoding="utf-8")
    )
    if not verify_range_optimizer_artifact(optimizer_artifact)["verified"]:
        raise ValueError("range optimizer artifact did not replay")
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
