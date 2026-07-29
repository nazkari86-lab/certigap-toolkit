from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict

from .autoindex import TraceOperation, WorkloadTrace
from .synthesis import HardwareProfile, SynthesisConstraints


class SynthesisVerificationError(ValueError):
    pass


def _digest(value: object) -> str:
    try:
        encoded = json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise SynthesisVerificationError("artifact is not canonical JSON") from exc
    return hashlib.sha256(encoded).hexdigest()


def _parse_trace(raw: object, n: int) -> WorkloadTrace:
    if not isinstance(raw, dict) or raw.get("n") != n:
        raise SynthesisVerificationError("trace key universe is invalid")
    operations = raw.get("operations")
    if not isinstance(operations, list):
        raise SynthesisVerificationError("trace operations are missing")
    try:
        parsed = [
            TraceOperation(
                kind=operation["kind"],
                left=operation["left"],
                right=operation["right"],
                value=float(operation["value"]),
            )
            for operation in operations
            if isinstance(operation, dict)
            and set(operation) == {"kind", "left", "right", "value"}
        ]
        if len(parsed) != len(operations):
            raise ValueError("operation schema mismatch")
        return WorkloadTrace(n, parsed)
    except (KeyError, TypeError, ValueError) as exc:
        raise SynthesisVerificationError("trace does not validate") from exc


def _contribution(
    operation: TraceOperation,
    left: int,
    right: int,
    aggregate: str,
    profile: HardwareProfile,
) -> float:
    if operation.right < left or right < operation.left:
        return 0.0
    width = right - left + 1
    if operation.kind == "get":
        return profile.value_read_ns
    if operation.kind == "update":
        if aggregate == "sum":
            return (
                profile.value_read_ns
                + profile.value_write_ns
                + profile.aggregate_write_ns
            )
        return (
            profile.value_write_ns
            + width * (profile.value_read_ns + profile.combine_ns)
            + profile.aggregate_write_ns
        )
    if operation.left <= left and right <= operation.right:
        return profile.aggregate_read_ns + profile.combine_ns
    overlap = min(right, operation.right) - max(left, operation.left) + 1
    return overlap * (profile.value_read_ns + profile.combine_ns)


def _interval_score(
    trace: WorkloadTrace,
    left: int,
    right: int,
    constraints: SynthesisConstraints,
    profile: HardwareProfile,
) -> float:
    costs = [
        _contribution(
            operation, left, right, constraints.aggregate, profile
        )
        for operation in trace.operations
    ]
    return (
        (1.0 - constraints.tail_weight) * sum(costs) / len(costs)
        + constraints.tail_weight * max(costs)
        + 2.0 * constraints.memory_weight_ns
        + (right - left + 2) * constraints.build_weight_ns
    )


def _row(
    trace: WorkloadTrace,
    path: tuple[int, ...],
    certified_score: float,
    constraints: SynthesisConstraints,
    profile: HardwareProfile,
) -> dict:
    costs = []
    for operation in trace.operations:
        total = 0.0
        left = 1
        for right in path:
            total += _contribution(
                operation, left, right, constraints.aggregate, profile
            )
            left = right + 1
        costs.append(total)
    blocks = len(path)
    memory = 2 * trace.n + 2 * blocks
    feasible = (
        constraints.memory_limit_slots is None
        or memory <= constraints.memory_limit_slots
    )
    starts = (1, *(boundary + 1 for boundary in path[:-1]))
    return {
        "blocks": blocks,
        "boundaries": list(path),
        "feasible": feasible,
        "reason": "feasible" if feasible else "memory limit exceeded",
        "resources": {
            "memory_slots": memory,
            "build_units": trace.n + blocks,
            "max_block_width": max(
                right - left + 1 for left, right in zip(starts, path)
            ),
        },
        "train": {
            "mean_ns": round(sum(costs) / len(costs), 12),
            "max_ns": round(max(costs), 12),
            "certified_robust_upper_ns": round(certified_score, 12),
            "operation_count": len(costs),
        },
    }


def _regenerate(
    trace: WorkloadTrace,
    constraints: SynthesisConstraints,
    profile: HardwareProfile,
) -> list[dict]:
    n = trace.n
    maximum = min(constraints.max_blocks, n)
    intervals = {
        (left, right): _interval_score(
            trace, left, right, constraints, profile
        )
        for right in range(1, n + 1)
        for left in range(
            max(1, right - constraints.max_block_width + 1), right + 1
        )
    }
    scores = [[math.inf] * (n + 1) for _ in range(maximum + 1)]
    paths: list[list[tuple[int, ...] | None]] = [
        [None] * (n + 1) for _ in range(maximum + 1)
    ]
    scores[0][0] = 0.0
    paths[0][0] = ()
    result = []
    for blocks in range(1, maximum + 1):
        for right in range(1, n + 1):
            lower = max(blocks - 1, right - constraints.max_block_width)
            for previous in range(lower, right):
                prior = paths[blocks - 1][previous]
                if prior is None:
                    continue
                score = scores[blocks - 1][previous] + intervals[
                    (previous + 1, right)
                ]
                path = prior + (right,)
                if (
                    score < scores[blocks][right] - 1e-12
                    or (
                        abs(score - scores[blocks][right]) <= 1e-12
                        and (paths[blocks][right] is None or path < paths[blocks][right])
                    )
                ):
                    scores[blocks][right] = score
                    paths[blocks][right] = path
        if paths[blocks][n] is not None:
            result.append(
                _row(
                    trace,
                    paths[blocks][n] or (),
                    scores[blocks][n],
                    constraints,
                    profile,
                )
            )
    return result


def verify_synthesis_certificate(artifact: dict) -> dict:
    if (
        not isinstance(artifact, dict)
        or artifact.get("schema") != "certigap-synthesis-v1"
    ):
        raise SynthesisVerificationError("unsupported artifact schema")
    unsigned = dict(artifact)
    supplied = unsigned.pop("sha256", None)
    if supplied != _digest(unsigned):
        raise SynthesisVerificationError("artifact digest mismatch")
    n = artifact.get("n")
    if not isinstance(n, int) or isinstance(n, bool) or n <= 0:
        raise SynthesisVerificationError("invalid key count")
    try:
        constraints = SynthesisConstraints(**artifact["constraints"])
        constraints.validate(n)
        raw_hardware = dict(artifact["hardware"])
        hardware_digest = raw_hardware.pop("sha256")
        if hardware_digest != _digest(raw_hardware):
            raise ValueError("hardware digest mismatch")
        hardware = HardwareProfile(**raw_hardware)
        hardware.validate()
    except (KeyError, TypeError, ValueError) as exc:
        raise SynthesisVerificationError(
            "constraints or hardware profile do not validate"
        ) from exc
    if asdict(constraints) != artifact["constraints"]:
        raise SynthesisVerificationError("constraints are not canonical")
    trace = _parse_trace(artifact.get("trace"), n)
    if not trace.operations:
        raise SynthesisVerificationError("training trace is empty")
    expected = _regenerate(trace, constraints, hardware)
    if artifact.get("candidates") != expected:
        raise SynthesisVerificationError(
            "candidate frontier does not match independent regeneration"
        )
    feasible = [row for row in expected if row["feasible"]]
    if not feasible:
        raise SynthesisVerificationError("certificate has no feasible design")
    winner = min(
        feasible,
        key=lambda row: (
            row["train"]["certified_robust_upper_ns"],
            row["resources"]["memory_slots"],
            row["boundaries"],
        ),
    )
    if artifact.get("selected") != {
        "blocks": winner["blocks"],
        "boundaries": winner["boundaries"],
    }:
        raise SynthesisVerificationError(
            "selected partition is not the certified frontier minimum"
        )
    expected_scope = (
        "exact minimum certified robust upper score over every legal "
        "variable-block partition in the declared grammar; hardware "
        "measurements are treated as supplied conditions"
    )
    if artifact.get("scope") != expected_scope:
        raise SynthesisVerificationError("certificate scope is invalid")
    expected_grammar = {
        "family": "variable_block_aggregate",
        "partition_space": "all contiguous partitions within declared limits",
        "objective": (
            "sum of per-block ((1-tail)*mean + tail*local-max) "
            "plus declared resource penalties"
        ),
        "actual_max_relation": (
            "sum of local maxima upper-bounds maximum whole-operation cost"
        ),
    }
    if artifact.get("grammar") != expected_grammar:
        raise SynthesisVerificationError("synthesis grammar is invalid")
    return {
        "verified": True,
        "completeness_verified": True,
        "candidate_count": len(expected),
        "partition_count": winner["blocks"],
        "boundaries": winner["boundaries"],
        "certified_robust_upper_ns": winner["train"][
            "certified_robust_upper_ns"
        ],
        "hardware_profile_sha256": artifact["hardware"]["sha256"],
    }
