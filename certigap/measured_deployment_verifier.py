from __future__ import annotations

import hashlib
import json
import math

from .autoindex_verifier import verify_autoindex_artifact


class MeasuredDeploymentVerificationError(ValueError):
    pass


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _close(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=1e-12, abs_tol=1e-12)


def _positive_int(value: object, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise MeasuredDeploymentVerificationError(f"invalid {field}")
    return value


def _finite_number(value: object, field: str) -> float:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(float(value))
    ):
        raise MeasuredDeploymentVerificationError(f"invalid {field}")
    return float(value)


def _verify_spec_and_trace(artifact: dict) -> None:
    spec = artifact["spec"]
    trace = artifact["validation_trace"]
    if (
        spec["schema"] != "certigap-adaptive-spec-v1"
        or spec["fixed_size"] is not True
    ):
        raise MeasuredDeploymentVerificationError("invalid adaptive spec")
    if spec["constraints"] != artifact["autoindex_artifact"]["constraints"]:
        raise MeasuredDeploymentVerificationError("spec constraints mismatch")
    operations = spec["operations"]
    if (
        not isinstance(operations, list)
        or not operations
        or len(set(operations)) != len(operations)
        or any(kind not in {"get", "range", "update"} for kind in operations)
    ):
        raise MeasuredDeploymentVerificationError("invalid declared operations")
    n = _positive_int(artifact["n"], "key universe")
    if (
        not isinstance(trace["n"], int)
        or isinstance(trace["n"], bool)
        or trace["n"] != n
        or not isinstance(trace["operations"], list)
    ):
        raise MeasuredDeploymentVerificationError("validation trace mismatch")
    for operation in trace["operations"]:
        kind = operation["kind"]
        left = operation["left"]
        right = operation["right"]
        value = _finite_number(operation["value"], "operation value")
        if (
            kind not in operations
            or not isinstance(left, int)
            or isinstance(left, bool)
            or not isinstance(right, int)
            or isinstance(right, bool)
            or not 1 <= left <= right <= n
            or (kind in {"get", "update"} and left != right)
            or not math.isfinite(value)
        ):
            raise MeasuredDeploymentVerificationError(
                "invalid validation operation"
            )


def verify_measured_deployment_artifact(artifact: dict) -> dict:
    try:
        if artifact.get("schema") != "certigap-measured-deployment-v1":
            raise MeasuredDeploymentVerificationError("unsupported schema")
        supplied_sha = artifact.get("sha256")
        unsigned = dict(artifact)
        unsigned.pop("sha256", None)
        if supplied_sha != _canonical_sha256(unsigned):
            raise MeasuredDeploymentVerificationError("artifact digest mismatch")
        verify_autoindex_artifact(artifact["autoindex_artifact"])
        _verify_spec_and_trace(artifact)
        if artifact["candidate"] != artifact["autoindex_artifact"]["selected"]:
            raise MeasuredDeploymentVerificationError("candidate selection mismatch")
        candidate_rows = artifact["autoindex_artifact"]["candidates"]
        candidate_row = next(
            row for row in candidate_rows if row["name"] == artifact["candidate"]
        )
        baseline_row = next(
            row
            for row in candidate_rows
            if row["name"] == artifact["baseline"]
        )
        if not candidate_row["feasible"] or not baseline_row["feasible"]:
            raise MeasuredDeploymentVerificationError(
                "candidate or baseline is infeasible"
            )
        policy = artifact["policy"]
        alpha = _finite_number(policy["alpha"], "alpha")
        minimum = _finite_number(
            policy["minimum_normalized_improvement"], "minimum improvement"
        )
        repetitions = _positive_int(policy["repetitions"], "repetitions")
        _positive_int(
            policy["amortization_operations"], "amortization operations"
        )
        warmup = policy["warmup_repetitions"]
        if (
            not 0.0 < alpha < 1.0
            or not 0.0 <= minimum < 1.0
            or not isinstance(warmup, int)
            or isinstance(warmup, bool)
            or warmup < 0
            or policy["baseline"] != artifact["baseline"]
        ):
            raise MeasuredDeploymentVerificationError("invalid policy")
        pairs = artifact["paired_batch_latency_ns"]
        decision = artifact["decision"]
        build = artifact["build_latency_ns"]
        baseline_build = _positive_int(build["baseline"], "baseline build latency")
        candidate_build = _positive_int(
            build["candidate"], "candidate build latency"
        )
        expected_penalty = max(0, candidate_build - baseline_build)
        if build["migration_penalty"] != expected_penalty:
            raise MeasuredDeploymentVerificationError(
                "migration penalty mismatch"
            )
        if artifact["candidate"] == artifact["baseline"]:
            expected_baseline_decision = {
                "candidate_deployed": False,
                "sample_count": 0,
                "mean_normalized_harm": 0.0,
                "hoeffding_radius": 0.0,
                "upper_normalized_harm": 0.0,
                "required_upper_bound": -minimum,
                "reason": "structural winner is the measured baseline",
            }
            if pairs or decision != expected_baseline_decision:
                raise MeasuredDeploymentVerificationError(
                    "baseline winner has an invalid deployment decision"
                )
            expected_selected = artifact["baseline"]
        else:
            if len(pairs) != repetitions:
                raise MeasuredDeploymentVerificationError(
                    "paired latency count mismatch"
                )
            harms = []
            for pair in pairs:
                baseline = _positive_int(
                    pair["baseline"], "baseline paired latency"
                )
                candidate = _positive_int(
                    pair["candidate"], "candidate paired latency"
                )
                harms.append((candidate - baseline) / max(candidate, baseline))
            mean_harm = sum(harms) / len(harms)
            radius = math.sqrt(2.0 * math.log(1.0 / alpha) / len(harms))
            upper = min(1.0, mean_harm + radius)
            deployed = upper <= -minimum + 1e-15
            if decision["sample_count"] != len(harms):
                raise MeasuredDeploymentVerificationError(
                    "decision sample count mismatch"
                )
            for field, expected in {
                "mean_normalized_harm": mean_harm,
                "hoeffding_radius": radius,
                "upper_normalized_harm": upper,
                "required_upper_bound": -minimum,
            }.items():
                if not _close(_finite_number(decision[field], field), expected):
                    raise MeasuredDeploymentVerificationError(
                        f"decision field mismatch: {field}"
                    )
            if bool(decision["candidate_deployed"]) != deployed:
                raise MeasuredDeploymentVerificationError(
                    "deployment decision mismatch"
                )
            expected_reason = (
                "paired measured upper bound passed"
                if deployed
                else "paired measured upper bound did not pass"
            )
            if decision["reason"] != expected_reason:
                raise MeasuredDeploymentVerificationError(
                    "deployment reason mismatch"
                )
            expected_selected = (
                artifact["candidate"] if deployed else artifact["baseline"]
            )
        if artifact["selected"] != expected_selected:
            raise MeasuredDeploymentVerificationError("selected runtime mismatch")
        if artifact["n"] != artifact["autoindex_artifact"]["n"]:
            raise MeasuredDeploymentVerificationError("key universe mismatch")
    except MeasuredDeploymentVerificationError:
        raise
    except (KeyError, StopIteration, TypeError, ValueError) as exc:
        raise MeasuredDeploymentVerificationError(
            "malformed measured deployment artifact"
        ) from exc
    return {
        "verified": True,
        "selected": artifact["selected"],
        "candidate_deployed": artifact["decision"]["candidate_deployed"],
        "sample_count": artifact["decision"]["sample_count"],
    }
