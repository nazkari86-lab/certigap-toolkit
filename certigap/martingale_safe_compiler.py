from __future__ import annotations

from .autoindex import AutoIndexConstraints, WorkloadTrace
from .compiler import CompileInputError, _finite_values, _trace, generate_cpp_header
from .martingale_safe_autoindex import (
    MartingaleSafeSelectionPolicy,
    compile_martingale_safe_autoindex,
)
from .martingale_safe_autoindex_verifier import (
    verify_martingale_safe_autoindex_certificate,
)


MARTINGALE_SAFE_INPUT_SCHEMA = "certigap-martingale-safe-compile-input-v1"


def load_martingale_safe_compile_spec(
    raw: object,
) -> tuple[
    list[float],
    WorkloadTrace,
    WorkloadTrace,
    WorkloadTrace | None,
    AutoIndexConstraints,
    MartingaleSafeSelectionPolicy,
]:
    if not isinstance(raw, dict):
        raise CompileInputError(
            "martingale safe compile input must be a JSON object"
        )
    allowed = {
        "schema",
        "values",
        "train_trace",
        "monitoring_trace",
        "test_trace",
        "constraints",
        "policy",
    }
    unknown = set(raw) - allowed
    if unknown:
        raise CompileInputError(
            "unknown top-level fields: " + ", ".join(sorted(unknown))
        )
    if raw.get("schema") != MARTINGALE_SAFE_INPUT_SCHEMA:
        raise CompileInputError(f"schema must be {MARTINGALE_SAFE_INPUT_SCHEMA}")
    values = _finite_values(raw.get("values"))
    n = len(values)
    train = _trace(raw.get("train_trace"), n, "train_trace")
    monitoring = _trace(
        raw.get("monitoring_trace"), n, "monitoring_trace"
    )
    test_raw = raw.get("test_trace")
    test = None if test_raw is None else _trace(test_raw, n, "test_trace")
    constraints_raw = raw.get("constraints", {})
    policy_raw = raw.get("policy", {})
    if not isinstance(constraints_raw, dict):
        raise CompileInputError("constraints must be an object")
    if not isinstance(policy_raw, dict):
        raise CompileInputError("policy must be an object")
    try:
        constraints = AutoIndexConstraints(**constraints_raw)
        constraints.validate(n)
        policy_fields = dict(policy_raw)
        for field in ("betting_fractions", "safe_baselines"):
            if field in policy_fields:
                if not isinstance(policy_fields[field], list):
                    raise ValueError(f"{field} must be an array")
                policy_fields[field] = tuple(policy_fields[field])
        policy = MartingaleSafeSelectionPolicy(**policy_fields)
        policy.validate()
    except (TypeError, ValueError) as exc:
        raise CompileInputError(
            f"martingale safe constraints or policy do not validate: {exc}"
        ) from exc
    return values, train, monitoring, test, constraints, policy


def compile_martingale_safe_spec(raw: object) -> dict:
    values, train, monitoring, test, constraints, policy = (
        load_martingale_safe_compile_spec(raw)
    )
    return compile_martingale_safe_autoindex(
        values,
        train,
        monitoring,
        test_trace=test,
        constraints=constraints,
        policy=policy,
    ).export_certificate()


def generate_martingale_safe_cpp_header(
    certificate: dict,
    *,
    namespace: str = "certigap_generated",
) -> str:
    verification = verify_martingale_safe_autoindex_certificate(certificate)
    return generate_cpp_header(
        certificate["base_artifact"],
        namespace=namespace,
        selected_name=verification["selected"],
        deployment_sha256=certificate["sha256"],
        selection_scope=certificate["scope"],
    )
