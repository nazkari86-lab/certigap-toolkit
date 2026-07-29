from __future__ import annotations

import hashlib
import json
import math
from typing import Sequence


EPS = 1e-9


class DynamicRangeVerificationError(ValueError):
    pass


def _canonical_sha256(value: object) -> str:
    try:
        payload = json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise DynamicRangeVerificationError(
            "artifact contains non-canonical values"
        ) from exc
    return hashlib.sha256(payload).hexdigest()


def _minimum_height(size: int) -> int:
    return 0 if size <= 1 else math.ceil(math.log2(size))


def _balanced(left: int, right: int) -> dict:
    if left == right:
        return {"type": "leaf", "interval": [left, right]}
    threshold = (left + right) // 2
    return {
        "type": "split",
        "interval": [left, right],
        "threshold": threshold,
        "left": _balanced(left, threshold),
        "right": _balanced(threshold + 1, right),
    }


def _complete(spec: object, left: int, right: int, remaining_depth: int) -> dict:
    if not isinstance(spec, dict) or spec.get("interval") != [left, right]:
        raise DynamicRangeVerificationError(
            "routing tree interval does not match its parent"
        )
    if left == right:
        if spec.get("type") != "leaf":
            raise DynamicRangeVerificationError(
                "singleton routing node must be a leaf"
            )
        return {"type": "leaf", "interval": [left, right]}
    if remaining_depth < _minimum_height(right - left + 1):
        raise DynamicRangeVerificationError("declared max_depth is infeasible")
    if spec.get("type") == "leaf":
        return _balanced(left, right)
    if spec.get("type") != "split":
        raise DynamicRangeVerificationError("invalid routing node type")
    threshold = spec.get("threshold")
    if (
        not isinstance(threshold, int)
        or isinstance(threshold, bool)
        or not left <= threshold < right
    ):
        raise DynamicRangeVerificationError("invalid routing threshold")
    fits = (
        remaining_depth > 0
        and _minimum_height(threshold - left + 1) <= remaining_depth - 1
        and _minimum_height(right - threshold) <= remaining_depth - 1
    )
    if not fits:
        return _balanced(left, right)
    return {
        "type": "split",
        "interval": [left, right],
        "threshold": threshold,
        "left": _complete(spec.get("left"), left, threshold, remaining_depth - 1),
        "right": _complete(
            spec.get("right"), threshold + 1, right, remaining_depth - 1
        ),
    }


def _validate_topology(
    node: object, left: int, right: int, depth: int, depths: list[int]
) -> int:
    if not isinstance(node, dict) or node.get("interval") != [left, right]:
        raise DynamicRangeVerificationError(
            "complete topology interval is invalid"
        )
    if left == right:
        if node != {"type": "leaf", "interval": [left, right]}:
            raise DynamicRangeVerificationError("leaf topology is malformed")
        depths.append(depth)
        return 1
    if node.get("type") != "split":
        raise DynamicRangeVerificationError("internal topology node is malformed")
    threshold = node.get("threshold")
    if (
        not isinstance(threshold, int)
        or isinstance(threshold, bool)
        or not left <= threshold < right
    ):
        raise DynamicRangeVerificationError("complete topology threshold is invalid")
    return (
        1
        + _validate_topology(node.get("left"), left, threshold, depth + 1, depths)
        + _validate_topology(
            node.get("right"), threshold + 1, right, depth + 1, depths
        )
    )


def _aggregate_from_topology(
    node: dict, values: Sequence[float], aggregate: str
) -> float:
    left, _ = node["interval"]
    if node["type"] == "leaf":
        return values[left - 1]
    left_value = _aggregate_from_topology(node["left"], values, aggregate)
    right_value = _aggregate_from_topology(node["right"], values, aggregate)
    if aggregate == "sum":
        return left_value + right_value
    if aggregate == "min":
        return min(left_value, right_value)
    if aggregate == "max":
        return max(left_value, right_value)
    raise DynamicRangeVerificationError("unsupported aggregate")


def _finite_sequence(value: object, name: str) -> list[float]:
    if not isinstance(value, list) or not value:
        raise DynamicRangeVerificationError(f"{name} must be a non-empty list")
    try:
        result = [float(item) for item in value]
    except (TypeError, ValueError) as exc:
        raise DynamicRangeVerificationError(f"{name} must be numeric") from exc
    if any(not math.isfinite(item) for item in result):
        raise DynamicRangeVerificationError(f"{name} must be finite")
    return result


def verify_dynamic_range_certificate(artifact: dict) -> dict:
    """Replay a Dynamic CertiRange structural and aggregate certificate."""
    if not isinstance(artifact, dict):
        raise DynamicRangeVerificationError("artifact must be an object")
    if artifact.get("schema") != "certigap-dynamic-range-v1":
        raise DynamicRangeVerificationError("unsupported artifact schema")
    values = _finite_sequence(artifact.get("values"), "values")
    weights = _finite_sequence(artifact.get("fit_weights"), "fit_weights")
    if len(values) != len(weights):
        raise DynamicRangeVerificationError("values and weights differ in length")
    if any(weight < 0 for weight in weights) or abs(sum(weights) - 1.0) > EPS:
        raise DynamicRangeVerificationError(
            "fit_weights must be a probability distribution"
        )
    aggregate = artifact.get("aggregate")
    if aggregate not in {"sum", "min", "max"}:
        raise DynamicRangeVerificationError("unsupported aggregate")
    settings = artifact.get("settings")
    state = artifact.get("state")
    digests = artifact.get("digests")
    if not all(isinstance(value, dict) for value in (settings, state, digests)):
        raise DynamicRangeVerificationError(
            "artifact settings, state, and digests are required"
        )
    max_depth = settings.get("max_depth")
    eta = settings.get("eta")
    if (
        not isinstance(max_depth, int)
        or isinstance(max_depth, bool)
        or max_depth < _minimum_height(len(values))
    ):
        raise DynamicRangeVerificationError("invalid max_depth")
    if not isinstance(eta, (int, float)) or not math.isfinite(eta) or not 0 <= eta <= 1:
        raise DynamicRangeVerificationError("invalid eta")

    expected_topology = _complete(
        artifact.get("routing_tree"), 1, len(values), max_depth
    )
    topology = artifact.get("complete_topology")
    if topology != expected_topology:
        raise DynamicRangeVerificationError(
            "complete topology is not the deterministic routing completion"
        )
    depths: list[int] = []
    node_count = _validate_topology(topology, 1, len(values), 0, depths)
    height = max(depths)
    if height > max_depth:
        raise DynamicRangeVerificationError("complete topology exceeds max_depth")
    root_aggregate = _aggregate_from_topology(topology, values, aggregate)
    average_depth = sum(weight * depth for weight, depth in zip(weights, depths))
    objective = (1.0 - float(eta)) * average_depth + float(eta) * height

    expected_state = {
        "root_aggregate": root_aggregate,
        "height": height,
        "node_count": node_count,
        "leaf_count": len(values),
        "per_key_depths": depths,
        "realized_average_point_depth": average_depth,
        "realized_max_point_depth": height,
        "realized_objective": objective,
    }
    for field, expected in expected_state.items():
        supplied = state.get(field)
        if isinstance(expected, float):
            try:
                valid = math.isfinite(float(supplied)) and abs(
                    float(supplied) - expected
                ) <= EPS
            except (TypeError, ValueError):
                valid = False
            if not valid:
                raise DynamicRangeVerificationError(
                    f"state field {field} does not replay"
                )
        elif supplied != expected:
            raise DynamicRangeVerificationError(
                f"state field {field} does not replay"
            )
    for field in ("data_version", "structure_version", "rebuild_count"):
        value = state.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise DynamicRangeVerificationError(f"invalid {field}")

    expected_digests = {
        "topology_sha256": _canonical_sha256(topology),
        "values_sha256": _canonical_sha256(values),
        "fit_weights_sha256": _canonical_sha256(weights),
    }
    if digests != expected_digests:
        raise DynamicRangeVerificationError("artifact digest mismatch")
    return {
        "verified": True,
        "aggregate": aggregate,
        "n": len(values),
        "height": height,
        "node_count": node_count,
        "root_aggregate": root_aggregate,
        "realized_objective": objective,
        "scope": artifact.get("scope"),
    }
