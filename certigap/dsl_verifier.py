from __future__ import annotations

import hashlib
import json

from .autoindex_verifier import (
    AutoIndexVerificationError,
    verify_autoindex_artifact,
)


class DSLVerificationError(ValueError):
    pass


_ALGEBRAS = {
    "sum": {
        "name": "sum",
        "identity": "zero",
        "combine": "addition",
        "laws": {
            "associative": True,
            "commutative": True,
            "has_identity": True,
            "has_inverse": True,
            "idempotent": False,
        },
        "verification_scope": (
            "mathematical real-addition model; the double runtime is replay-"
            "tested but IEEE-754 addition is not associative"
        ),
    },
    "min": {
        "name": "min",
        "identity": "positive_infinity",
        "combine": "minimum",
        "laws": {
            "associative": True,
            "commutative": True,
            "has_identity": True,
            "has_inverse": False,
            "idempotent": True,
        },
        "verification_scope": "canonical finite-value minimum",
    },
    "max": {
        "name": "max",
        "identity": "negative_infinity",
        "combine": "maximum",
        "laws": {
            "associative": True,
            "commutative": True,
            "has_identity": True,
            "has_inverse": False,
            "idempotent": True,
        },
        "verification_scope": "canonical finite-value maximum",
    },
}

_GRAMMAR = (
    ("flat_fold", "sorted_array", "flat", "monoid"),
    ("prefix_group", "prefix_sum", "prefix", "commutative_group"),
    ("fenwick_group", "fenwick", "tree", "commutative_group"),
    ("sqrt_monoid", "sqrt_decomposition", "blocked", "monoid"),
    ("segment_monoid", "segment_tree", "tree", "monoid"),
    ("sparse_semilattice", "sparse_table", "table", "idempotent_semilattice"),
    ("certirange_point_monoid", "certirange_point", "synthesized_tree", "monoid"),
    ("certirange_range_monoid", "certirange_range", "synthesized_tree", "monoid"),
)


def _canonical_sha256(value: object) -> str:
    try:
        encoded = json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise DSLVerificationError("certificate is not canonical JSON") from exc
    return hashlib.sha256(encoded).hexdigest()


def _eligible(algebra: dict, requirement: str) -> bool:
    laws = algebra["laws"]
    required = {
        "monoid": ("associative", "has_identity"),
        "commutative_group": (
            "associative", "commutative", "has_identity", "has_inverse"
        ),
        "idempotent_semilattice": (
            "associative", "commutative", "has_identity", "idempotent"
        ),
    }[requirement]
    return all(laws[name] for name in required)


def verify_dsl_certificate(artifact: dict) -> dict:
    expected_keys = {
        "schema", "contract", "algebra", "grammar", "selection_artifact",
        "selected_design", "claim_boundary", "sha256",
    }
    if not isinstance(artifact, dict) or set(artifact) != expected_keys:
        raise DSLVerificationError("certificate top-level schema is invalid")
    if artifact.get("schema") != "certigap-proof-carrying-dsl-v1":
        raise DSLVerificationError("unsupported DSL certificate schema")
    unsigned = dict(artifact)
    supplied_digest = unsigned.pop("sha256")
    if supplied_digest != _canonical_sha256(unsigned):
        raise DSLVerificationError("certificate digest mismatch")

    contract = artifact["contract"]
    if not isinstance(contract, dict) or set(contract) != {
        "schema", "fixed_size", "rank_semantics", "operations", "algebra",
        "constraints", "unsupported_operations",
    }:
        raise DSLVerificationError("contract schema is invalid")
    if contract["schema"] != "certigap-dsl-contract-v1":
        raise DSLVerificationError("contract version is invalid")
    if contract["fixed_size"] is not True:
        raise DSLVerificationError("DSL v1 requires a fixed-size universe")
    if contract["rank_semantics"] != "one_based_inclusive":
        raise DSLVerificationError("rank semantics are invalid")
    operations = contract["operations"]
    if (
        not isinstance(operations, list)
        or not operations
        or operations != [
            name for name in ("get", "range", "update") if name in operations
        ]
    ):
        raise DSLVerificationError("operations are not canonical")
    if contract["unsupported_operations"] != [
        "insert", "erase", "range_add", "range_assign"
    ]:
        raise DSLVerificationError("unsupported-operation boundary changed")

    algebra_name = contract["algebra"]
    if algebra_name not in _ALGEBRAS or artifact["algebra"] != _ALGEBRAS[algebra_name]:
        raise DSLVerificationError("algebra laws are not canonical")
    algebra = artifact["algebra"]

    base = artifact["selection_artifact"]
    try:
        base_summary = verify_autoindex_artifact(base)
    except (AutoIndexVerificationError, TypeError, ValueError) as exc:
        raise DSLVerificationError("embedded selection artifact failed") from exc
    if contract["constraints"] != base["constraints"]:
        raise DSLVerificationError("contract and selection constraints differ")
    if base["constraints"]["aggregate"] != algebra_name:
        raise DSLVerificationError("algebra and runtime aggregate differ")
    trace_kinds = {row["kind"] for row in base["train_trace"]["operations"]}
    if not trace_kinds.issubset(set(operations)):
        raise DSLVerificationError("training trace violates the contract")
    holdout = base["holdout_trace"]
    if holdout is not None and not {
        row["kind"] for row in holdout["operations"]
    }.issubset(set(operations)):
        raise DSLVerificationError("holdout trace violates the contract")

    base_rows = {row["name"]: row for row in base["candidates"]}
    expected_designs = []
    for design_id, backend, family, requirement in _GRAMMAR:
        row = base_rows[backend]
        expected_designs.append(
            {
                "id": design_id,
                "backend": backend,
                "family": family,
                "requires": requirement,
                "algebra_eligible": _eligible(algebra, requirement),
                "feasible": row["feasible"],
                "reason": row["reason"],
                "resources": row["resources"],
                "train_score": row["train"]["score"],
            }
        )
    grammar = artifact["grammar"]
    if not isinstance(grammar, dict) or set(grammar) != {
        "schema", "designs", "sha256"
    }:
        raise DSLVerificationError("typed grammar schema is invalid")
    unsigned_grammar = dict(grammar)
    grammar_digest = unsigned_grammar.pop("sha256")
    if grammar_digest != _canonical_sha256(unsigned_grammar):
        raise DSLVerificationError("typed grammar digest mismatch")
    if grammar["schema"] != "certigap-typed-design-grammar-v1":
        raise DSLVerificationError("typed grammar version is invalid")
    if grammar["designs"] != expected_designs:
        raise DSLVerificationError("typed grammar is incomplete or altered")

    expected_selected = next(
        row["id"] for row in expected_designs
        if row["backend"] == base_summary["selected"]
    )
    if artifact["selected_design"] != expected_selected:
        raise DSLVerificationError("selected design does not match the minimum")
    expected_boundary = (
        "The certificate proves typed capability compatibility and the "
        "minimum declared analytical score over the complete DSL v1 "
        "grammar. It does not prove portable wall-clock optimality or "
        "optimality outside this fixed-size grammar."
    )
    if artifact["claim_boundary"] != expected_boundary:
        raise DSLVerificationError("claim boundary is invalid")
    return {
        "verified": True,
        "typed_capabilities_verified": True,
        "grammar_completeness_verified": True,
        "design_count": len(expected_designs),
        "feasible_design_count": sum(row["feasible"] for row in expected_designs),
        "selected_design": expected_selected,
        "selected_backend": base_summary["selected"],
        "train_score": base_summary["train_score"],
        "sha256": supplied_digest,
    }
