from __future__ import annotations

from .autoindex import AutoIndexConstraints, WorkloadTrace
from .compiler import (
    CompileInputError,
    _finite_values,
    _trace,
    generate_cpp_header,
)
from .sequential_safe_autoindex import (
    SequentialSafeSelectionPolicy,
    compile_sequential_safe_autoindex,
)
from .sequential_safe_autoindex_verifier import (
    verify_sequential_safe_autoindex_certificate,
)


SEQUENTIAL_SAFE_INPUT_SCHEMA = (
    "certigap-sequential-safe-compile-input-v1"
)


def load_sequential_safe_compile_spec(
    raw: object,
) -> tuple[
    list[float],
    WorkloadTrace,
    WorkloadTrace,
    WorkloadTrace | None,
    AutoIndexConstraints,
    SequentialSafeSelectionPolicy,
]:
    if not isinstance(raw, dict):
        raise CompileInputError(
            "sequential safe compile input must be a JSON object"
        )
    allowed = {
        "schema",
        "values",
        "train_trace",
        "validation_trace",
        "test_trace",
        "constraints",
        "policy",
    }
    unknown = set(raw) - allowed
    if unknown:
        raise CompileInputError(
            "unknown top-level fields: " + ", ".join(sorted(unknown))
        )
    if raw.get("schema") != SEQUENTIAL_SAFE_INPUT_SCHEMA:
        raise CompileInputError(
            f"schema must be {SEQUENTIAL_SAFE_INPUT_SCHEMA}"
        )
    values = _finite_values(raw.get("values"))
    n = len(values)
    train = _trace(raw.get("train_trace"), n, "train_trace")
    validation = _trace(
        raw.get("validation_trace"), n, "validation_trace"
    )
    test_raw = raw.get("test_trace")
    test = None if test_raw is None else _trace(
        test_raw, n, "test_trace"
    )
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
        if "safe_baselines" in policy_fields:
            raw_baselines = policy_fields["safe_baselines"]
            if not isinstance(raw_baselines, list):
                raise ValueError("safe_baselines must be an array")
            policy_fields["safe_baselines"] = tuple(raw_baselines)
        policy = SequentialSafeSelectionPolicy(**policy_fields)
        policy.validate()
    except (TypeError, ValueError) as exc:
        raise CompileInputError(
            f"sequential safe constraints or policy do not validate: {exc}"
        ) from exc
    return values, train, validation, test, constraints, policy


def compile_sequential_safe_spec(raw: object) -> dict:
    values, train, validation, test, constraints, policy = (
        load_sequential_safe_compile_spec(raw)
    )
    return compile_sequential_safe_autoindex(
        values,
        train,
        validation,
        test_trace=test,
        constraints=constraints,
        policy=policy,
    ).export_certificate()


def generate_sequential_safe_cpp_header(
    certificate: dict,
    *,
    namespace: str = "certigap_generated",
) -> str:
    verification = verify_sequential_safe_autoindex_certificate(certificate)
    return generate_cpp_header(
        certificate["base_artifact"],
        namespace=namespace,
        selected_name=verification["selected"],
        deployment_sha256=certificate["sha256"],
        selection_scope=certificate["scope"],
    )
