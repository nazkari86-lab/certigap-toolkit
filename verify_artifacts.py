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
    verify_dsl_certificate,
    verify_hybrid_certificate,
    verify_martingale_safe_autoindex_certificate,
    verify_pruned_beam_certificate,
    verify_range_optimizer_artifact,
    verify_safe_autoindex_certificate,
    verify_sequential_safe_autoindex_certificate,
    verify_tracking_autoindex_certificate,
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
        "tracking_autoindex_validation.csv": 15,
        "tracking_autoindex_comparison.csv": 882 if require_max_scaling else 70,
        "tracking_autoindex_candidates.csv": 882 if require_max_scaling else 70,
        "tracking_autoindex_runtime.csv": 90 if require_max_scaling else 45,
        "tracking_autoindex_native_runtime.csv": 108,
        "tracking_autoindex_fast_runtime.csv": 384,
        "tracking_hot_path_runtime.csv": 448,
        "concurrent_tracking_runtime.csv": 48,
        "dsl_validation.csv": 36,
        "safe_autoindex_validation.csv": 16,
        "sequential_safe_validation.csv": 4,
        "optional_stopping_monte_carlo.csv": 1,
        "martingale_safe_validation.csv": 4,
        "martingale_null_monte_carlo.csv": 1,
        "compiler_integration_validation.csv": 24,
        "adaptive_header_validation.csv": 24,
        "adaptive_array_validation.csv": 6,
        "python_adaptive_array_validation.csv": 7,
        "measured_deployment_validation.csv": 4,
        "synthesis_validation.csv": 24,
        "hybrid_validation.csv": 24,
        "synthesis_native_latency.csv": 110,
        "sqlite_ycsb_raw.csv": 375,
        "sqlite_ycsb_summary.csv": 15,
        "sqlite_vtab_validation.csv": 6,
    }
    observed: dict[str, int] = {}
    for name, minimum in minimum_rows.items():
        _, count = csv_rows(name)
        if count < minimum:
            raise ValueError(f"{name} has {count} rows; expected at least {minimum}")
        observed[name] = count

    tracking_rows = csv_records("tracking_autoindex_validation.csv")
    if (
        {row["scenario"] for row in tracking_rows}
        != {
            "stable_points",
            "stable_ranges",
            "point_to_range_shift",
            "range_to_updates_shift",
            "alternating",
        }
        or {row["migration_cost_units"] for row in tracking_rows}
        != {"2.0", "8.0", "32.0"}
        or any(row["certificate_verified"] != "True" for row in tracking_rows)
    ):
        raise ValueError("tracking AutoIndex validation is incomplete")
    tracking_artifact = json.loads(
        (RESULTS / "tracking_autoindex_example.json").read_text(encoding="utf-8")
    )
    verify_tracking_autoindex_certificate(tracking_artifact)

    comparison_rows = csv_records("tracking_autoindex_comparison.csv")
    comparison_policies = {
        "tracking_wfa",
        "initial_static",
        "best_fixed_hindsight",
        "myopic_current_operation",
        "cumulative_leader",
        "exact_k_switch_oracle",
        "exact_unrestricted_oracle",
    }
    comparison_groups: dict[tuple[str, str, str], set[str]] = {}
    for row in comparison_rows:
        comparison_groups.setdefault(
            (row["n"], row["scenario"], row["migration_cost_units"]), set()
        ).add(row["policy"])
    expected_groups = 126 if require_max_scaling else 10
    if (
        len(comparison_groups) < expected_groups
        or any(
            policies != comparison_policies
            for policies in comparison_groups.values()
        )
        or any(row["certificate_verified"] != "True" for row in comparison_rows)
    ):
        raise ValueError("tracking policy comparison is incomplete")
    candidate_rows = csv_records("tracking_autoindex_candidates.csv")
    if len(candidate_rows) != len(comparison_groups) * 7:
        raise ValueError("tracking fixed-candidate comparison is incomplete")
    runtime_rows = csv_records("tracking_autoindex_runtime.csv")
    runtime_groups: dict[tuple[str, str], set[str]] = {}
    for row in runtime_rows:
        runtime_groups.setdefault((row["n"], row["scenario"]), set()).add(
            row["method"]
        )
    if any(len(methods) != 9 for methods in runtime_groups.values()) or any(
        not math.isfinite(float(row["median_ns_per_operation"]))
        for row in runtime_rows
    ):
        raise ValueError("tracking runtime comparison is incomplete")
    comparison_metadata = json.loads(
        (RESULTS / "tracking_autoindex_comparison_metadata.json").read_text(
            encoding="utf-8"
        )
    )
    if require_max_scaling and comparison_metadata.get("mode") != "max":
        raise ValueError("tracking comparison is not the maximum matrix")

    native_tracking = csv_records("tracking_autoindex_native_runtime.csv")
    native_implementations = {
        "sorted_array",
        "prefix_sum",
        "fenwick",
        "sqrt_decomposition",
        "segment_tree",
        "tracking_native_uniform_production",
        "tracking_native_rebuild_metric_production",
        "tracking_native_rebuild_metric_audit",
        "tracking_python_reference",
    }
    native_groups: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in native_tracking:
        native_groups.setdefault((row["n"], row["workload"]), []).append(row)
    if (
        set(native_groups)
        != {
            (str(n), workload)
            for n in (64, 256, 4096)
            for workload in (
                "range_to_update",
                "update_to_range",
                "alternating",
                "read_mostly",
            )
        }
        or any(
            {row["implementation"] for row in group} != native_implementations
            or {row["operations"] for row in group} != {"5000"}
            or any(
                not math.isfinite(float(row["ns_per_operation"]))
                or float(row["ns_per_operation"]) <= 0.0
                for row in group
            )
            or any(
                not math.isclose(
                    float(group[0]["checksum"]),
                    float(row["checksum"]),
                    rel_tol=1e-12,
                    abs_tol=1e-9,
                )
                for row in group[1:]
            )
            for group in native_groups.values()
        )
    ):
        raise ValueError("native tracking runtime comparison is incomplete")
    native_tracking_metadata = json.loads(
        (RESULTS / "tracking_autoindex_native_runtime.metadata.json").read_text(
            encoding="utf-8"
        )
    )
    if (
        native_tracking_metadata.get("schema")
        != "certigap-native-tracking-benchmark-v1"
        or native_tracking_metadata.get("operations_per_configuration") != 5000
        or native_tracking_metadata.get("native_repetitions") != 5
        or native_tracking_metadata.get("python_repetitions") != 3
        or native_tracking_metadata.get("source_sha256")
        != file_sha256(ROOT / "cpp" / "tracking_autoindex_benchmark.cpp")
        or native_tracking_metadata.get("header_sha256")
        != file_sha256(ROOT / "cpp" / "certigap_tracking.hpp")
        or native_tracking_metadata.get("csv_sha256")
        != file_sha256(RESULTS / "tracking_autoindex_native_runtime.csv")
    ):
        raise ValueError("native tracking benchmark provenance is invalid")

    fast_tracking = csv_records("tracking_autoindex_fast_runtime.csv")
    fast_groups: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    for row in fast_tracking:
        fast_groups.setdefault(
            (row["horizon"], row["n"], row["workload"]), []
        ).append(row)
    fast_implementations = {
        "sorted_array", "prefix_sum", "fenwick", "sqrt_decomposition",
        "segment_tree", "tracking_native_fast_sampled",
    }
    if (
        len(fast_groups) != 64
        or any(
            {row["implementation"] for row in group} != fast_implementations
            or {row["operations"] for row in group} != {group[0]["horizon"]}
            or any(float(row["ns_per_operation"]) <= 0.0 for row in group)
            or any(
                not math.isclose(
                    float(group[0]["checksum"]), float(row["checksum"]),
                    rel_tol=1e-12, abs_tol=1e-9,
                )
                for row in group[1:]
            )
            for group in fast_groups.values()
        )
    ):
        raise ValueError("fast tracking runtime comparison is incomplete")
    fast_metadata = json.loads(
        (RESULTS / "tracking_autoindex_fast_runtime.metadata.json").read_text(
            encoding="utf-8"
        )
    )
    if (
        fast_metadata.get("schema") != "certigap-fast-tracking-benchmark-v1"
        or fast_metadata.get("horizons") != [5000, 50000]
        or fast_metadata.get("native_repetitions") != 5
        or fast_metadata.get("configurations") != 64
        or fast_metadata.get("source_sha256")
        != file_sha256(ROOT / "cpp" / "tracking_autoindex_benchmark.cpp")
        or fast_metadata.get("header_sha256")
        != file_sha256(ROOT / "cpp" / "certigap_tracking.hpp")
        or fast_metadata.get("csv_sha256")
        != file_sha256(RESULTS / "tracking_autoindex_fast_runtime.csv")
    ):
        raise ValueError("fast tracking benchmark provenance is invalid")

    hot_path = csv_records("tracking_hot_path_runtime.csv")
    hot_groups: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    for row in hot_path:
        hot_groups.setdefault(
            (row["horizon"], row["n"], row["workload"]), []
        ).append(row)
    hot_implementations = {
        "frozen_fenwick_checked", "frozen_fenwick_unchecked",
        "static_fenwick_checked", "static_fenwick_unchecked",
        "fast_checked", "fast_unchecked", "fast_detached_data_plane",
    }
    if (
        len(hot_groups) != 64
        or len(hot_path) != 448
        or any(
            {row["implementation"] for row in group} != hot_implementations
            or {row["operations"] for row in group} != {group[0]["horizon"]}
            or any(
                float(row["ns_per_operation"]) <= 0.0
                or float(row["baseline_ns_per_operation"]) <= 0.0
                or float(row["ratio_to_direct"]) <= 0.0
                or not math.isclose(
                    float(row["checksum"]), float(row["baseline_checksum"]),
                    rel_tol=1e-12, abs_tol=1e-9,
                )
                for row in group
            )
            for group in hot_groups.values()
        )
    ):
        raise ValueError("tracking hot-path comparison is incomplete")
    hot_metadata = json.loads(
        (RESULTS / "tracking_hot_path_runtime.metadata.json").read_text(
            encoding="utf-8"
        )
    )
    if (
        hot_metadata.get("schema") != "certigap-tracking-hot-path-v1"
        or hot_metadata.get("horizons") != [5000, 50000]
        or hot_metadata.get("native_repetitions") != 7
        or hot_metadata.get("configurations") != 64
        or hot_metadata.get("source_sha256")
        != file_sha256(ROOT / "cpp" / "tracking_hot_path_benchmark.cpp")
        or hot_metadata.get("header_sha256")
        != file_sha256(ROOT / "cpp" / "certigap_tracking.hpp")
        or hot_metadata.get("csv_sha256")
        != file_sha256(RESULTS / "tracking_hot_path_runtime.csv")
    ):
        raise ValueError("tracking hot-path benchmark provenance is invalid")

    concurrent_tracking = csv_records("concurrent_tracking_runtime.csv")
    concurrent_groups: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    for row in concurrent_tracking:
        concurrent_groups.setdefault(
            (row["n"], row["scenario"], row["threads"]), []
        ).append(row)
    concurrent_implementations = {
        "direct_fenwick", "direct_prefix", "concurrent_fallback",
        "concurrent_snapshot", "concurrent_snapshot_session",
        "concurrent_snapshot_session_unchecked",
    }
    if (
        len(concurrent_groups) != 8
        or len(concurrent_tracking) != 48
        or any(
            {row["implementation"] for row in group}
                != concurrent_implementations
            or {row["operations"] for row in group} != {"500000"}
            or {row["atomics_lock_free"] for row in group} != {"true"}
            or any(
                float(row["ns_per_operation"]) <= 0.0
                or not math.isclose(
                    float(group[0]["checksum"]), float(row["checksum"]),
                    rel_tol=1e-12, abs_tol=1e-9,
                )
                for row in group
            )
            for group in concurrent_groups.values()
        )
    ):
        raise ValueError("concurrent tracking benchmark is incomplete")
    concurrent_metadata = json.loads(
        (RESULTS / "concurrent_tracking_runtime.metadata.json").read_text(
            encoding="utf-8"
        )
    )
    if (
        concurrent_metadata.get("schema")
            != "certigap-concurrent-tracking-v1"
        or concurrent_metadata.get("operations_per_configuration") != 500000
        or concurrent_metadata.get("native_repetitions") != 5
        or concurrent_metadata.get("configurations") != 8
        or concurrent_metadata.get("atomics_lock_free") is not True
        or concurrent_metadata.get("source_sha256")
        != file_sha256(ROOT / "cpp" / "concurrent_tracking_benchmark.cpp")
        or concurrent_metadata.get("header_sha256")
        != file_sha256(ROOT / "cpp" / "certigap_concurrent.hpp")
        or concurrent_metadata.get("csv_sha256")
        != file_sha256(RESULTS / "concurrent_tracking_runtime.csv")
    ):
        raise ValueError("concurrent tracking benchmark provenance is invalid")

    dsl_rows = csv_records("dsl_validation.csv")
    if (
        len(dsl_rows) != 36
        or {row["algebra"] for row in dsl_rows} != {"sum", "min", "max"}
        or {row["operations"] for row in dsl_rows}
        != {"get", "range", "range+update", "get+range+update"}
        or {row["profile"] for row in dsl_rows}
        != {"default", "tight_memory", "persistent_snapshot"}
        or len(
            {
                (row["algebra"], row["operations"], row["profile"])
                for row in dsl_rows
            }
        ) != 36
        or any(
            row["design_count"] != "8"
            or row["typed_capabilities_verified"] != "True"
            or row["grammar_completeness_verified"] != "True"
            or row["runtime_matches_oracle"] != "True"
            or row["runtime_checksum"] != row["oracle_checksum"]
            or not re.fullmatch(r"[0-9a-f]{64}", row["certificate_sha256"])
            for row in dsl_rows
        )
        or len({row["selected_backend"] for row in dsl_rows}) < 3
    ):
        raise ValueError("proof-carrying DSL validation is incomplete")
    dsl_example_path = RESULTS / "dsl_certificate_example.json"
    dsl_example = json.loads(dsl_example_path.read_text(encoding="utf-8"))
    if not verify_dsl_certificate(dsl_example)["verified"]:
        raise ValueError("proof-carrying DSL example did not verify")
    dsl_metadata = json.loads(
        (RESULTS / "dsl_validation.metadata.json").read_text(encoding="utf-8")
    )
    if (
        dsl_metadata.get("schema") != "certigap-dsl-validation-v1"
        or dsl_metadata.get("configurations") != 36
        or dsl_metadata.get("algebras") != ["sum", "min", "max"]
        or dsl_metadata.get("replay_operations") != 160
        or dsl_metadata.get("dsl_source_sha256")
        != file_sha256(ROOT / "certigap" / "dsl.py")
        or dsl_metadata.get("verifier_source_sha256")
        != file_sha256(ROOT / "certigap" / "dsl_verifier.py")
        or dsl_metadata.get("generator_source_sha256")
        != file_sha256(ROOT / "generate_dsl_validation.py")
        or dsl_metadata.get("csv_sha256")
        != file_sha256(RESULTS / "dsl_validation.csv")
        or dsl_metadata.get("example_sha256")
        != file_sha256(dsl_example_path)
    ):
        raise ValueError("proof-carrying DSL provenance is invalid")

    sqlite_vtab_rows = csv_records("sqlite_vtab_validation.csv")
    if (
        {row["scenario"] for row in sqlite_vtab_rows}
        != {
            "planner_equality",
            "planner_bounded_range",
            "range_sum_pushdown",
            "rollback_after_reconnect",
            "insert_update_delete",
            "durable_shadow_consistency",
        }
        or any(row["passed"] != "True" for row in sqlite_vtab_rows)
        or {row["planner_strategy"] for row in sqlite_vtab_rows[:2]}
        != {"key_eq", "key_ge_key_le"}
    ):
        raise ValueError("SQLite virtual-table validation is incomplete")

    adaptive_array_rows = csv_records("adaptive_array_validation.csv")
    if (
        {row["scenario"] for row in adaptive_array_rows}
        != {
            "automatic_range_warmup",
            "automatic_point_warmup",
            "deployment_threshold_rejection",
            "explicit_maintenance",
            "profile_writer",
            "profile_reader",
        }
        or any(row["passed"] != "true" for row in adaptive_array_rows)
        or {
            row["selected"]
            for row in adaptive_array_rows
            if row["scenario"] in {"profile_writer", "profile_reader"}
        }
        != {"prefix_sum"}
    ):
        raise ValueError("adaptive_array validation is incomplete")

    python_adaptive_rows = csv_records("python_adaptive_array_validation.csv")
    if (
        {row["scenario"] for row in python_adaptive_rows}
        != {
            "automatic_range_warmup",
            "automatic_point_warmup",
            "mixed_update_workload",
            "deployment_threshold_rejection",
            "explicit_maintenance",
            "profile_writer",
            "profile_reader",
        }
        or any(row["passed"] != "True" for row in python_adaptive_rows)
        or {
            row["selected"]
            for row in python_adaptive_rows
            if row["scenario"] in {"profile_writer", "profile_reader"}
        }
        != {"prefix_sum"}
        or next(
            row
            for row in python_adaptive_rows
            if row["scenario"] == "deployment_threshold_rejection"
        )["optimized"]
        != "False"
    ):
        raise ValueError("Python AdaptiveArray validation is incomplete")

    measured_rows = csv_records("measured_deployment_validation.csv")
    if (
        {row["scenario"] for row in measured_rows}
        != {"strong_win", "weak_win", "parity", "regression"}
        or any(row["passed"] != "True" for row in measured_rows)
        or {
            row["scenario"]
            for row in measured_rows
            if row["candidate_deployed"] == "True"
        }
        != {"strong_win"}
    ):
        raise ValueError("measured deployment validation is incomplete")

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
        or autoindex_verified["candidate_count"] != 8
    ):
        raise ValueError("AutoIndex example does not prove portfolio completeness")
    autoindex_rows = csv_records("autoindex_validation.csv")
    autoindex_groups: dict[str, list[dict[str, str]]] = {}
    for row in autoindex_rows:
        autoindex_groups.setdefault(row["group_id"], []).append(row)
    expected_candidates = {
        "sorted_array",
        "prefix_sum",
        "fenwick",
        "sqrt_decomposition",
        "segment_tree",
        "sparse_table",
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

    safe_artifact = json.loads(
        (RESULTS / "safe_autoindex_example.json").read_text(encoding="utf-8")
    )
    if not verify_safe_autoindex_certificate(safe_artifact)["verified"]:
        raise ValueError("Safe AutoIndex example did not replay")
    safe_rows = csv_records("safe_autoindex_validation.csv")
    if (
        len(safe_rows) != 16
        or len({row["group_id"] for row in safe_rows}) != 16
        or any(row["certificate_verified"] != "True" for row in safe_rows)
        or sum(row["candidate_approved"] == "True" for row in safe_rows) != 4
    ):
        raise ValueError("Safe AutoIndex validation matrix is incomplete")
    for row in safe_rows:
        approved = row["candidate_approved"] == "True"
        if approved != (float(row["upper_difference"]) < 0.0):
            raise ValueError("Safe AutoIndex decision contradicts its bound")
        if not approved and row["deployed"] != row["safe_baseline"]:
            raise ValueError("Safe AutoIndex failed to retain its baseline")

    sequential_artifact = json.loads(
        (RESULTS / "sequential_safe_example.json").read_text(
            encoding="utf-8"
        )
    )
    if not verify_sequential_safe_autoindex_certificate(
        sequential_artifact
    )["verified"]:
        raise ValueError("Sequential Safe AutoIndex example did not replay")
    sequential_rows = csv_records("sequential_safe_validation.csv")
    by_scenario = {row["scenario"]: row for row in sequential_rows}
    if (
        set(by_scenario)
        != {
            "stable_stream",
            "insufficient_stream",
            "migration_dominated",
            "post_stop_reversal",
        }
        or any(
            row["certificate_verified"] != "True"
            for row in sequential_rows
        )
        or sum(
            row["candidate_approved"] == "True"
            for row in sequential_rows
        )
        != 2
    ):
        raise ValueError(
            "Sequential Safe AutoIndex validation matrix is incomplete"
        )
    stable = by_scenario["stable_stream"]
    reversal = by_scenario["post_stop_reversal"]
    if (
        not stable["stopping_operation"]
        or not reversal["stopping_operation"]
        or float(reversal["final_upper_difference"]) <= 0.0
        or int(reversal["post_stop_operations"]) <= 0
    ):
        raise ValueError(
            "Sequential stopping or post-stop reversal witness is missing"
        )
    monte_carlo = csv_records("optional_stopping_monte_carlo.csv")
    if (
        len(monte_carlo) != 1
        or int(monte_carlo[0]["anytime_false_approvals"])
        > int(float(monte_carlo[0]["alpha"]) * int(monte_carlo[0]["trials"]))
        or float(
            monte_carlo[0]["repeated_fixed_false_approval_rate"]
        )
        <= float(monte_carlo[0]["alpha"])
    ):
        raise ValueError("optional-stopping Monte Carlo witness is invalid")

    martingale_artifact = json.loads(
        (RESULTS / "martingale_safe_example.json").read_text(
            encoding="utf-8"
        )
    )
    if not verify_martingale_safe_autoindex_certificate(
        martingale_artifact
    )["verified"]:
        raise ValueError("Martingale Safe AutoIndex example did not replay")
    martingale_rows = csv_records("martingale_safe_validation.csv")
    martingale_by_scenario = {
        row["scenario"]: row for row in martingale_rows
    }
    if (
        set(martingale_by_scenario)
        != {
            "stable_benefit",
            "insufficient_evidence",
            "migration_dominated",
            "deploy_then_harm",
        }
        or any(
            row["certificate_verified"] != "True"
            for row in martingale_rows
        )
        or martingale_by_scenario["stable_benefit"][
            "candidate_approved"
        ]
        != "True"
        or martingale_by_scenario["deploy_then_harm"][
            "candidate_revoked"
        ]
        != "True"
        or martingale_by_scenario["deploy_then_harm"]["deployed"]
        != martingale_by_scenario["deploy_then_harm"]["baseline"]
    ):
        raise ValueError(
            "Martingale Safe AutoIndex lifecycle matrix is incomplete"
        )
    adapted_null = csv_records("martingale_null_monte_carlo.csv")
    if (
        len(adapted_null) != 1
        or adapted_null[0]["within_nominal_alpha"] != "True"
        or float(adapted_null[0]["false_deployment_rate"])
        > float(adapted_null[0]["alpha"])
    ):
        raise ValueError("adapted martingale-null diagnostic is invalid")

    compiler_rows = csv_records("compiler_integration_validation.csv")
    if (
        len({row["group_id"] for row in compiler_rows}) != 24
        or any(
            row["candidate_count"] != "8"
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
            or row["candidate_count"] != "8"
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

    hybrid_rows = csv_records("hybrid_validation.csv")
    if (
        len(hybrid_rows) != 24
        or any(
            row["certificate_verified"] != "true"
            or row["runtime_correct"] != "true"
            or int(row["candidate_count"]) <= 0
            or int(row["selected_blocks"]) <= 0
            or not math.isfinite(float(row["selected_score"]))
            or float(row["relative_gain"]) < -1e-9
            for row in hybrid_rows
        )
        or sum(row["nonuniform"] == "true" for row in hybrid_rows) < 8
    ):
        raise ValueError("CertiGap-H exact validation is incomplete")
    hybrid_artifact = json.loads(
        (RESULTS / "hybrid_certificate_example.json").read_text(
            encoding="utf-8"
        )
    )
    if not verify_hybrid_certificate(hybrid_artifact)["verified"]:
        raise ValueError("CertiGap-H certificate did not replay")
    pruned_artifact = json.loads(
        (RESULTS / "pruned_beam_certificate_example.json").read_text(
            encoding="utf-8"
        )
    )
    if not verify_pruned_beam_certificate(
        pruned_artifact["weights"], pruned_artifact
    )["verified"]:
        raise ValueError("C++ pruned-beam certificate did not replay")

    native_rows = csv_records("synthesis_native_latency.csv")
    native_methods = {
        "array",
        "global_prefix",
        "fenwick",
        "segment_tree",
        "uniform_block",
        "certigap_x",
        "uniform_prefix",
        "certigap_x_prefix",
        "certigap_hybrid",
        "certigap_auto",
    }
    native_groups: dict[str, list[dict[str, str]]] = {}
    for row in native_rows:
        native_groups.setdefault(row["scenario"], []).append(row)
    if (
        len(native_groups) != 11
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
    selectable_native = {"global_prefix", "fenwick", "certigap_hybrid"}
    for group in native_groups.values():
        automatic = next(
            row for row in group if row["method"] == "certigap_auto"
        )
        selected = automatic["selected_backend"]
        if (
            selected not in selectable_native
            or float(automatic["train_selection_ns_per_operation"]) <= 0.0
        ):
            raise ValueError("native AutoIndex selection record is invalid")
        selected_row = next(row for row in group if row["method"] == selected)
        if any(
            automatic[field] != selected_row[field]
            for field in (
                "median_ns_per_operation",
                "p95_batch_ns_per_operation",
                "mad_ns_per_operation",
                "checksum",
                "memory_slots",
                "blocks",
            )
        ):
            raise ValueError(
                "native AutoIndex holdout row does not reuse its selected backend"
            )

    hybrid_vs_fenwick = 0
    hybrid_vs_uniform = 0
    hybrid_fastest = 0
    for group in native_groups.values():
        by_method = {row["method"]: row for row in group}
        hybrid_latency = float(
            by_method["certigap_hybrid"]["median_ns_per_operation"]
        )
        if hybrid_latency < float(
            by_method["fenwick"]["median_ns_per_operation"]
        ):
            hybrid_vs_fenwick += 1
        if hybrid_latency < float(
            by_method["uniform_prefix"]["median_ns_per_operation"]
        ):
            hybrid_vs_uniform += 1
        specialized = [
            float(row["median_ns_per_operation"])
            for row in group
            if row["method"] != "certigap_auto"
        ]
        if hybrid_latency <= min(specialized) + 1e-12:
            hybrid_fastest += 1
    claim_register = (ROOT / "docs" / "CLAIMS.md").read_text(
        encoding="utf-8"
    )
    required_claim_values = {
        f"`{hybrid_vs_fenwick}/11` holdout scenarios",
        f"`{hybrid_vs_uniform}/11` holdout scenarios",
        f"`{hybrid_fastest}/11` holdout scenarios",
    }
    if not required_claim_values.issubset(set(claim_register.splitlines())):
        # Values normally occur inside table rows, so use substring validation.
        if any(value not in claim_register for value in required_claim_values):
            raise ValueError(
                "CLAIMS.md native claims disagree with committed CSV evidence"
            )
    reader_surfaces = [
        ROOT / "README.md",
        ROOT / "paper" / "main.tex",
        ROOT / "docs" / "RKNP_ISEF_POSITIONING.md",
    ]
    forbidden_unscoped_claims = (
        "fastest possible index",
        "universally faster",
        "universal speedup",
        "first robust search",
        "first in the world",
    )
    for path in reader_surfaces:
        content = path.read_text(encoding="utf-8").lower()
        for phrase in forbidden_unscoped_claims:
            if phrase in content:
                raise ValueError(
                    f"{path.relative_to(ROOT)} contains forbidden unscoped "
                    f"claim: {phrase}"
                )
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
        or len(native_metadata.get("cases", [])) != 11
        or len(native_metadata.get("limitations", [])) < 4
        or native_metadata.get("benchmark_source_sha256")
        != file_sha256(ROOT / "cpp" / "synthesis_native_benchmark.cpp")
        or native_metadata.get("generated_cases_sha256")
        != file_sha256(ROOT / "cpp" / "synthesis_native_cases.hpp")
        or native_metadata.get("results_sha256")
        != file_sha256(RESULTS / "synthesis_native_latency.csv")
    ):
        raise ValueError("CertiGap-X native provenance contract is incomplete")

    sqlite_rows = csv_records("sqlite_ycsb_raw.csv")
    sqlite_summary = csv_records("sqlite_ycsb_summary.csv")
    sqlite_groups = {
        (row["workload"], row["backend"]) for row in sqlite_summary
    }
    if sqlite_groups != {
        (workload, backend)
        for workload in ("A", "B", "C", "F", "R")
        for backend in ("sqlite_btree", "fenwick", "certigap_h")
    }:
        raise ValueError("SQLite/YCSB-compatible summary is incomplete")
    if any(
        float(row["bootstrap_median_ci95_low"])
        > float(row["median_ns_per_operation"])
        or float(row["median_ns_per_operation"])
        > float(row["bootstrap_median_ci95_high"])
        or float(row["median_ns_per_operation"]) <= 0.0
        for row in sqlite_summary
    ):
        raise ValueError("SQLite/YCSB-compatible confidence interval is invalid")
    for workload in ("A", "B", "C", "F", "R"):
        checksums = {
            row["checksum"]
            for row in sqlite_rows
            if row["workload"] == workload
        }
        if len(checksums) != 1:
            raise ValueError(
                f"SQLite/YCSB-compatible checksum mismatch for {workload}"
            )
    sqlite_metadata = json.loads(
        (RESULTS / "sqlite_ycsb_metadata.json").read_text(encoding="utf-8")
    )
    if (
        sqlite_metadata.get("schema")
        != "certigap-sqlite-ycsb-pilot-v1"
        or sqlite_metadata.get("mode") != "full"
        or len(sqlite_metadata.get("limitations", [])) < 5
    ):
        raise ValueError("SQLite/YCSB-compatible metadata is incomplete")

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
