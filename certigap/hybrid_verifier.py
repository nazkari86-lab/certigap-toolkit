from __future__ import annotations

import hashlib
import json
import math

from .autoindex import TraceOperation, WorkloadTrace
from .hybrid import HybridConstraints
from .synthesis import HardwareProfile


class HybridVerificationError(ValueError):
    pass


def _sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    ).hexdigest()


def _trace_statistics(trace: WorkloadTrace) -> dict:
    gets = [0] * (trace.n + 1)
    updates = [0] * (trace.n + 1)
    ranges = []
    for operation in trace.operations:
        if operation.kind == "get":
            gets[operation.left] += 1
        elif operation.kind == "update":
            updates[operation.left] += 1
        else:
            ranges.append(operation)
    get_prefix = [0] * (trace.n + 1)
    update_prefix = [0] * (trace.n + 1)
    weighted_update_prefix = [0] * (trace.n + 1)
    for key in range(1, trace.n + 1):
        get_prefix[key] = get_prefix[key - 1] + gets[key]
        update_prefix[key] = update_prefix[key - 1] + updates[key]
        weighted_update_prefix[key] = (
            weighted_update_prefix[key - 1] + key * updates[key]
        )
    crossing_prefix = [[0] * (trace.n + 1) for _ in range(trace.n + 1)]
    for right in range(1, trace.n + 1):
        starts = [0] * (trace.n + 1)
        for operation in ranges:
            if operation.right > right:
                starts[operation.left] += 1
        for key in range(1, trace.n + 1):
            crossing_prefix[right][key] = (
                crossing_prefix[right][key - 1] + starts[key]
            )
    next_update = [trace.n + 1] * (trace.n + 2)
    nearest = trace.n + 1
    for key in range(trace.n, 0, -1):
        if updates[key]:
            nearest = key
        next_update[key] = nearest
    return {
        "get_prefix": get_prefix,
        "update_prefix": update_prefix,
        "weighted_update_prefix": weighted_update_prefix,
        "crossing_prefix": crossing_prefix,
        "next_update": next_update,
    }


def _score_interval(
    trace: WorkloadTrace,
    left: int,
    right: int,
    block_index: int,
    total_blocks: int,
    constraints: HybridConstraints,
    hardware: HardwareProfile,
    statistics: dict,
) -> float:
    get_count = (
        statistics["get_prefix"][right]
        - statistics["get_prefix"][left - 1]
    )
    update_count = (
        statistics["update_prefix"][right]
        - statistics["update_prefix"][left - 1]
    )
    weighted_updates = (
        statistics["weighted_update_prefix"][right]
        - statistics["weighted_update_prefix"][left - 1]
    )
    crossing_count = (
        statistics["crossing_prefix"][right][right]
        - statistics["crossing_prefix"][right][left - 1]
    )
    top_suffix = total_blocks - block_index + 1
    crossing_cost = (
        4.0 * hardware.aggregate_read_ns + hardware.combine_ns
    )
    update_sum = (
        update_count
        * (
            hardware.value_write_ns
            + (right + 1 + top_suffix) * hardware.aggregate_write_ns
        )
        - weighted_updates * hardware.aggregate_write_ns
    )
    mean = (
        get_count * hardware.value_read_ns
        + update_sum
        + crossing_count * crossing_cost
    ) / len(trace.operations)
    first_update = statistics["next_update"][left]
    maximum_update = (
        hardware.value_write_ns
        + (right - first_update + 1 + top_suffix)
        * hardware.aggregate_write_ns
        if first_update <= right
        else 0.0
    )
    local_maximum = max(
        hardware.value_read_ns if get_count else 0.0,
        maximum_update,
        crossing_cost if crossing_count else 0.0,
    )
    return (
        (1.0 - constraints.tail_weight) * mean
        + constraints.tail_weight * local_maximum
        + 2.0 * constraints.memory_weight_ns
    )


def _regenerate_candidate(
    trace: WorkloadTrace,
    total_blocks: int,
    constraints: HybridConstraints,
    hardware: HardwareProfile,
) -> dict | None:
    n = trace.n
    statistics = _trace_statistics(trace)
    scores = [[math.inf] * (n + 1) for _ in range(total_blocks + 1)]
    paths: list[list[tuple[int, ...] | None]] = [
        [None] * (n + 1) for _ in range(total_blocks + 1)
    ]
    scores[0][0] = 0.0
    paths[0][0] = ()
    for block_index in range(1, total_blocks + 1):
        maximum_right = min(
            n,
            block_index * constraints.max_block_width,
            n - (total_blocks - block_index),
        )
        for right in range(block_index, maximum_right + 1):
            minimum_left = max(
                block_index,
                right - constraints.max_block_width + 1,
            )
            for left in range(minimum_left, right + 1):
                previous = left - 1
                previous_path = paths[block_index - 1][previous]
                if previous_path is None:
                    continue
                interval = round(
                    _score_interval(
                        trace,
                        left,
                        right,
                        block_index,
                        total_blocks,
                        constraints,
                        hardware,
                        statistics,
                    ),
                    12,
                )
                candidate = round(
                    scores[block_index - 1][previous] + interval,
                    12,
                )
                candidate_path = (*previous_path, right)
                if (
                    candidate < scores[block_index][right] - 1e-12
                    or (
                        abs(candidate - scores[block_index][right]) <= 1e-12
                        and (
                            paths[block_index][right] is None
                            or candidate_path < paths[block_index][right]
                        )
                    )
                ):
                    scores[block_index][right] = candidate
                    paths[block_index][right] = candidate_path
    path = paths[total_blocks][n]
    if path is None:
        return None
    memory_slots = 3 * n + 2 * total_blocks
    return {
        "blocks": total_blocks,
        "boundaries": list(path),
        "score": round(scores[total_blocks][n], 12),
        "memory_slots": memory_slots,
        "feasible": (
            constraints.memory_limit_slots is None
            or memory_slots <= constraints.memory_limit_slots
        ),
    }


def _regenerate_frontier(
    trace: WorkloadTrace,
    constraints: HybridConstraints,
    hardware: HardwareProfile,
) -> list[dict]:
    constraints.validate(trace.n)
    hardware.validate()
    minimum_blocks = math.ceil(trace.n / constraints.max_block_width)
    result = []
    for blocks in range(minimum_blocks, constraints.max_blocks + 1):
        candidate = _regenerate_candidate(
            trace, blocks, constraints, hardware
        )
        if candidate is not None:
            result.append(candidate)
    return result


def verify_hybrid_certificate(artifact: dict) -> dict:
    if not isinstance(artifact, dict):
        raise HybridVerificationError("artifact must be an object")
    unsigned = {key: value for key, value in artifact.items() if key != "sha256"}
    if artifact.get("sha256") != _sha256(unsigned):
        raise HybridVerificationError("artifact digest mismatch")
    if artifact.get("schema") != "certigap-hybrid-v1":
        raise HybridVerificationError("unsupported hybrid schema")
    try:
        trace_payload = artifact["trace"]
        trace = WorkloadTrace(
            int(trace_payload["n"]),
            (
                TraceOperation(
                    operation["kind"],
                    int(operation["left"]),
                    int(operation["right"]),
                    float(operation["value"]),
                )
                for operation in trace_payload["operations"]
            ),
        )
        constraints = HybridConstraints(**artifact["constraints"])
        hardware_payload = {
            key: value
            for key, value in artifact["hardware"].items()
            if key != "sha256"
        }
        hardware = HardwareProfile(**hardware_payload)
        if artifact["hardware"].get("sha256") != hardware.manifest()["sha256"]:
            raise HybridVerificationError("hardware profile digest mismatch")
        regenerated = _regenerate_frontier(trace, constraints, hardware)
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, HybridVerificationError):
            raise
        raise HybridVerificationError(f"malformed hybrid artifact: {error}") from error
    if artifact.get("candidates") != regenerated:
        raise HybridVerificationError("hybrid frontier does not regenerate")
    feasible = [row for row in regenerated if row["feasible"]]
    if not feasible:
        raise HybridVerificationError("hybrid frontier has no feasible design")
    selected = min(
        feasible,
        key=lambda row: (
            row["score"],
            row["memory_slots"],
            row["boundaries"],
        ),
    )
    if artifact.get("selected") != {
        "blocks": selected["blocks"],
        "boundaries": selected["boundaries"],
    }:
        raise HybridVerificationError("reported hybrid winner is not minimal")
    return {
        "verified": True,
        "candidate_count": len(regenerated),
        "selected_blocks": selected["blocks"],
        "score": selected["score"],
    }
