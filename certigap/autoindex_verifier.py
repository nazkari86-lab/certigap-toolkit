from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict

from .api import solve_with
from .autoindex import (
    PORTFOLIO_ORDER,
    AutoIndexConstraints,
    TraceOperation,
    WorkloadTrace,
)
from .dynamic_range import _complete_topology
from .range_optimizer import range_aware_beam_search


class AutoIndexVerificationError(ValueError):
    pass


def _canonical_sha256(value: object) -> str:
    try:
        encoded = json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise AutoIndexVerificationError(
            "artifact is not canonical JSON"
        ) from exc
    return hashlib.sha256(encoded).hexdigest()


def _parse_trace(raw: object, expected_n: int) -> WorkloadTrace:
    if not isinstance(raw, dict) or raw.get("n") != expected_n:
        raise AutoIndexVerificationError("trace key universe is invalid")
    operations = raw.get("operations")
    if not isinstance(operations, list):
        raise AutoIndexVerificationError("trace operations are missing")
    parsed: list[TraceOperation] = []
    try:
        for operation in operations:
            if not isinstance(operation, dict) or set(operation) != {
                "kind",
                "left",
                "right",
                "value",
            }:
                raise AutoIndexVerificationError(
                    "trace operation schema is invalid"
                )
            parsed.append(
                TraceOperation(
                    kind=operation["kind"],
                    left=operation["left"],
                    right=operation["right"],
                    value=float(operation["value"]),
                )
            )
        return WorkloadTrace(expected_n, parsed)
    except (TypeError, ValueError) as exc:
        if isinstance(exc, AutoIndexVerificationError):
            raise
        raise AutoIndexVerificationError("trace does not validate") from exc


def _depths(topology: dict, depth: int = 0) -> list[int]:
    if topology["type"] == "leaf":
        return [depth]
    return _depths(topology["left"], depth + 1) + _depths(
        topology["right"], depth + 1
    )


def _range_visits(topology: dict, left: int, right: int) -> int:
    node_left, node_right = topology["interval"]
    if right < node_left or node_right < left:
        return 1
    if left <= node_left and node_right <= right:
        return 1
    if topology["type"] == "leaf":
        return 1
    return (
        1
        + _range_visits(topology["left"], left, right)
        + _range_visits(topology["right"], left, right)
    )


def _fenwick_prefix_steps(key: int) -> int:
    steps = 0
    while key > 0:
        steps += 1
        key -= key & -key
    return steps


def _fenwick_update_steps(key: int, n: int) -> int:
    steps = 0
    while key <= n:
        steps += 1
        key += key & -key
    return steps


def _segment_range_steps(left: int, right: int, size: int) -> int:
    left = size + left - 1
    right = size + right
    steps = 0
    while left < right:
        if left & 1:
            steps += 1
            left += 1
        if right & 1:
            right -= 1
            steps += 1
        left //= 2
        right //= 2
    return max(1, steps)


def _costs(
    name: str,
    trace: WorkloadTrace,
    topology: dict | None,
    constraints: AutoIndexConstraints,
) -> list[float]:
    n = trace.n
    size = 1 << math.ceil(math.log2(n)) if n > 1 else 1
    depths = _depths(topology) if topology is not None else []
    unit_cost = {
        "sorted_array": constraints.array_unit_cost,
        "fenwick": constraints.fenwick_unit_cost,
        "segment_tree": constraints.segment_tree_unit_cost,
        "certirange_point": constraints.certirange_unit_cost,
        "certirange_range": constraints.certirange_unit_cost,
    }[name]
    result: list[float] = []
    for operation in trace.operations:
        if name == "sorted_array":
            cost = (
                1
                if operation.kind in {"get", "update"}
                else operation.right - operation.left + 1
            )
        elif name == "fenwick":
            if operation.kind == "get":
                cost = 1
            elif operation.kind == "update":
                cost = _fenwick_update_steps(operation.left, n)
            else:
                cost = max(
                    1,
                    _fenwick_prefix_steps(operation.right)
                    + _fenwick_prefix_steps(operation.left - 1),
                )
        elif name == "segment_tree":
            if operation.kind == "get":
                cost = 1
            elif operation.kind == "update":
                cost = int(math.log2(size)) + 1
            else:
                cost = _segment_range_steps(
                    operation.left, operation.right, size
                )
        else:
            if topology is None:
                raise AutoIndexVerificationError(
                    "CertiRange candidate has no topology"
                )
            if operation.kind in {"get", "update"}:
                cost = depths[operation.left - 1] + 1
            else:
                cost = _range_visits(
                    topology, operation.left, operation.right
                )
        result.append(cost * unit_cost)
    return result


def _resources(name: str, n: int, topology: dict | None) -> tuple[int, int, int]:
    size = 1 << math.ceil(math.log2(n)) if n > 1 else 1
    if name == "sorted_array":
        return n, 0, n
    if name == "fenwick":
        height = int(math.log2(size))
        return 2 * n + 1, height, n * (height + 1)
    if name == "segment_tree":
        return 2 * size, int(math.log2(size)), 2 * size
    if topology is None:
        raise AutoIndexVerificationError(
            "CertiRange candidate has no topology"
        )
    return 3 * n - 1, max(_depths(topology)), 2 * n - 1


def _score(
    costs: list[float],
    resources: tuple[int, int, int],
    constraints: AutoIndexConstraints,
) -> dict:
    if not costs:
        raise AutoIndexVerificationError("training trace is empty")
    memory_slots, height, build_units = resources
    mean = sum(costs) / len(costs)
    maximum = max(costs)
    structural = (
        (1.0 - constraints.tail_weight) * mean
        + constraints.tail_weight * maximum
    )
    return {
        "mean_primitive_visits": mean,
        "max_primitive_visits": maximum,
        "structural_score": structural,
        "score": (
            structural
            + constraints.memory_weight * memory_slots
            + constraints.build_weight * build_units
        ),
        "memory_slots": memory_slots,
        "height": height,
        "build_units": build_units,
        "operation_count": len(costs),
    }


def _feasibility(
    name: str,
    resources: tuple[int, int, int],
    constraints: AutoIndexConstraints,
) -> tuple[bool, str]:
    memory_slots, height, _ = resources
    reasons: list[str] = []
    if name == "fenwick" and constraints.aggregate != "sum":
        reasons.append("Fenwick supports sum only")
    if constraints.require_persistent_snapshots and not name.startswith(
        "certirange"
    ):
        reasons.append("persistent snapshots required")
    if (
        constraints.memory_limit_slots is not None
        and memory_slots > constraints.memory_limit_slots
    ):
        reasons.append("memory limit exceeded")
    if constraints.max_depth is not None and height > constraints.max_depth:
        reasons.append("depth limit exceeded")
    return (not reasons, "feasible" if not reasons else "; ".join(reasons))


def _expected_candidates(
    train: WorkloadTrace,
    holdout: WorkloadTrace | None,
    constraints: AutoIndexConstraints,
) -> list[dict]:
    workload = train.aggregate()
    weights = workload.routing_weights()
    point_tree = solve_with(
        weights, constraints.budget, constraints.tail_weight, "beam"
    )["serialized_tree"]
    minimum = 0 if train.n <= 1 else math.ceil(math.log2(train.n))
    max_depth = constraints.max_depth or 2 * minimum + 1
    range_tree = range_aware_beam_search(
        point_counts=workload.point_counts,
        update_counts=workload.update_counts,
        range_counts=[
            (left, right, count)
            for (left, right), count in workload.range_counts.items()
        ],
        budget=constraints.budget,
        max_depth=max_depth,
        tail_weight=constraints.tail_weight,
        beam_width=constraints.range_beam_width,
        candidate_limit=constraints.range_candidate_limit,
    )["routing_tree"]
    routing = {
        "certirange_point": point_tree,
        "certirange_range": range_tree,
    }
    topologies = {
        name: _complete_topology(tree, 1, train.n, max_depth)
        for name, tree in routing.items()
    }
    rows: list[dict] = []
    for name in PORTFOLIO_ORDER:
        topology = topologies.get(name)
        resources = _resources(name, train.n, topology)
        feasible, reason = _feasibility(name, resources, constraints)
        rows.append(
            {
                "name": name,
                "feasible": feasible,
                "reason": reason,
                "capabilities": {
                    "aggregates": (
                        ["sum"]
                        if name == "fenwick"
                        else ["sum", "min", "max"]
                    ),
                    "persistent_snapshots": name.startswith("certirange"),
                },
                "resources": {
                    "memory_slots": resources[0],
                    "height": resources[1],
                    "build_units": resources[2],
                },
                "train": _score(
                    _costs(name, train, topology, constraints),
                    resources,
                    constraints,
                ),
                "holdout": (
                    None
                    if holdout is None or not holdout.operations
                    else _score(
                        _costs(name, holdout, topology, constraints),
                        resources,
                        constraints,
                    )
                ),
                "routing_tree": routing.get(name),
                "topology_sha256": (
                    None
                    if topology is None
                    else _canonical_sha256(topology)
                ),
            }
        )
    return rows


def verify_autoindex_artifact(artifact: dict) -> dict:
    if not isinstance(artifact, dict) or artifact.get("schema") != "certigap-autoindex-v1":
        raise AutoIndexVerificationError("unsupported artifact schema")
    supplied_digest = artifact.get("sha256")
    unsigned = dict(artifact)
    unsigned.pop("sha256", None)
    if supplied_digest != _canonical_sha256(unsigned):
        raise AutoIndexVerificationError("artifact digest mismatch")
    n = artifact.get("n")
    if not isinstance(n, int) or isinstance(n, bool) or n <= 0:
        raise AutoIndexVerificationError("invalid key count")
    raw_constraints = artifact.get("constraints")
    if not isinstance(raw_constraints, dict):
        raise AutoIndexVerificationError("constraints are missing")
    try:
        constraints = AutoIndexConstraints(**raw_constraints)
        constraints.validate(n)
    except (TypeError, ValueError) as exc:
        raise AutoIndexVerificationError("constraints do not validate") from exc
    if asdict(constraints) != raw_constraints:
        raise AutoIndexVerificationError("constraints are not canonical")
    train = _parse_trace(artifact.get("train_trace"), n)
    if not train.operations:
        raise AutoIndexVerificationError("training trace is empty")
    holdout_raw = artifact.get("holdout_trace")
    holdout = (
        None if holdout_raw is None else _parse_trace(holdout_raw, n)
    )
    if artifact.get("portfolio_order") != list(PORTFOLIO_ORDER):
        raise AutoIndexVerificationError(
            "portfolio order is incomplete or reordered"
        )
    try:
        expected = _expected_candidates(train, holdout, constraints)
    except (TypeError, ValueError) as exc:
        raise AutoIndexVerificationError(
            "candidate regeneration failed"
        ) from exc
    if artifact.get("candidates") != expected:
        raise AutoIndexVerificationError(
            "candidate portfolio does not match deterministic regeneration"
        )
    feasible = [row for row in expected if row["feasible"]]
    if not feasible:
        raise AutoIndexVerificationError("artifact has no feasible candidate")
    selected = min(
        feasible,
        key=lambda row: (
            row["train"]["score"],
            row["resources"]["memory_slots"],
            PORTFOLIO_ORDER.index(row["name"]),
        ),
    )
    if artifact.get("selected") != selected["name"]:
        raise AutoIndexVerificationError(
            "selected candidate is not the portfolio minimum"
        )
    expected_scope = (
        "minimum declared analytical score over the complete deterministic "
        "five-candidate portfolio; holdout is evaluation-only"
    )
    if artifact.get("scope") != expected_scope:
        raise AutoIndexVerificationError("selection scope is invalid")
    if artifact.get("metric") != {
        "unit": "declared_weighted_primitive_work",
        "warning": (
            "defaults are uncalibrated structural visits, not nanoseconds; "
            "set candidate unit costs from target-system measurements"
        ),
    }:
        raise AutoIndexVerificationError("metric declaration is invalid")
    selected_holdout = selected["holdout"]
    holdout_best = (
        None
        if selected_holdout is None
        else min(
            row["holdout"]["score"]
            for row in feasible
            if row["holdout"] is not None
        )
    )
    return {
        "verified": True,
        "completeness_verified": True,
        "selected": selected["name"],
        "train_score": selected["train"]["score"],
        "holdout_score": (
            None if selected_holdout is None else selected_holdout["score"]
        ),
        "holdout_oracle_score": holdout_best,
        "holdout_regret": (
            None
            if selected_holdout is None or holdout_best is None
            else selected_holdout["score"] - holdout_best
        ),
        "candidate_count": len(expected),
        "feasible_candidate_count": len(feasible),
    }
