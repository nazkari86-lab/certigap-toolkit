from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from typing import Iterable, Literal

from .autoindex import CompiledAutoIndex, WorkloadTrace
from .compiler import generate_cpp_header
from .spec import AdaptiveSpec, OperationName, compile_from_spec


AlgebraName = Literal["sum", "min", "max"]

_OPERATION_ORDER: tuple[OperationName, ...] = ("get", "range", "update")

_ALGEBRAS: dict[AlgebraName, dict] = {
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

_DESIGN_GRAMMAR: tuple[dict, ...] = (
    {"id": "flat_fold", "backend": "sorted_array", "family": "flat", "requires": "monoid"},
    {"id": "prefix_group", "backend": "prefix_sum", "family": "prefix", "requires": "commutative_group"},
    {"id": "fenwick_group", "backend": "fenwick", "family": "tree", "requires": "commutative_group"},
    {"id": "sqrt_monoid", "backend": "sqrt_decomposition", "family": "blocked", "requires": "monoid"},
    {"id": "segment_monoid", "backend": "segment_tree", "family": "tree", "requires": "monoid"},
    {"id": "sparse_semilattice", "backend": "sparse_table", "family": "table", "requires": "idempotent_semilattice"},
    {"id": "certirange_point_monoid", "backend": "certirange_point", "family": "synthesized_tree", "requires": "monoid"},
    {"id": "certirange_range_monoid", "backend": "certirange_range", "family": "synthesized_tree", "requires": "monoid"},
)


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _laws_satisfy(algebra: dict, requirement: str) -> bool:
    laws = algebra["laws"]
    if requirement == "monoid":
        return laws["associative"] and laws["has_identity"]
    if requirement == "commutative_group":
        return (
            laws["associative"]
            and laws["commutative"]
            and laws["has_identity"]
            and laws["has_inverse"]
        )
    if requirement == "idempotent_semilattice":
        return (
            laws["associative"]
            and laws["commutative"]
            and laws["has_identity"]
            and laws["idempotent"]
        )
    raise RuntimeError(f"unknown algebra requirement: {requirement}")


@dataclass(frozen=True)
class ProofCarryingSpec:
    """Typed contract for the proof-carrying fixed-size compiler."""

    operations: tuple[OperationName, ...] = ("get", "range", "update")
    algebra: AlgebraName = "sum"
    memory_limit_slots: int | None = None
    max_depth: int | None = None
    require_persistent_snapshots: bool = False
    budget: int = 6
    tail_weight: float = 0.10
    memory_weight: float = 0.0
    build_weight: float = 0.0
    array_unit_cost: float = 1.0
    prefix_unit_cost: float = 1.0
    fenwick_unit_cost: float = 1.0
    sqrt_unit_cost: float = 1.0
    segment_tree_unit_cost: float = 1.0
    sparse_unit_cost: float = 1.0
    certirange_unit_cost: float = 1.0

    def _adaptive(self) -> AdaptiveSpec:
        return AdaptiveSpec(
            operations=self.operations,
            aggregate=self.algebra,
            memory_limit_slots=self.memory_limit_slots,
            max_depth=self.max_depth,
            require_persistent_snapshots=self.require_persistent_snapshots,
            budget=self.budget,
            tail_weight=self.tail_weight,
            memory_weight=self.memory_weight,
            build_weight=self.build_weight,
            array_unit_cost=self.array_unit_cost,
            prefix_unit_cost=self.prefix_unit_cost,
            fenwick_unit_cost=self.fenwick_unit_cost,
            sqrt_unit_cost=self.sqrt_unit_cost,
            segment_tree_unit_cost=self.segment_tree_unit_cost,
            sparse_unit_cost=self.sparse_unit_cost,
            certirange_unit_cost=self.certirange_unit_cost,
        )

    def validate(self, n: int) -> None:
        if self.algebra not in _ALGEBRAS:
            raise ValueError("algebra must be sum, min, or max")
        self._adaptive().validate(n)

    def contract(self) -> dict:
        adaptive = self._adaptive()
        constraints = asdict(adaptive.to_constraints())
        return {
            "schema": "certigap-dsl-contract-v1",
            "fixed_size": True,
            "rank_semantics": "one_based_inclusive",
            "operations": [
                operation
                for operation in _OPERATION_ORDER
                if operation in self.operations
            ],
            "algebra": self.algebra,
            "constraints": constraints,
            "unsupported_operations": [
                "insert", "erase", "range_add", "range_assign"
            ],
        }


def _typed_designs(base_artifact: dict, algebra: dict) -> list[dict]:
    base_rows = {row["name"]: row for row in base_artifact["candidates"]}
    designs: list[dict] = []
    for declaration in _DESIGN_GRAMMAR:
        row = base_rows[declaration["backend"]]
        algebra_eligible = _laws_satisfy(algebra, declaration["requires"])
        designs.append(
            {
                **declaration,
                "algebra_eligible": algebra_eligible,
                "feasible": row["feasible"],
                "reason": row["reason"],
                "resources": row["resources"],
                "train_score": row["train"]["score"],
            }
        )
    return designs


@dataclass
class ProofCarryingIndex:
    runtime: CompiledAutoIndex
    artifact: dict

    @property
    def selected_design(self) -> str:
        return str(self.artifact["selected_design"])

    def _require_operation(self, operation: str) -> None:
        if operation not in self.artifact["contract"]["operations"]:
            raise RuntimeError(
                f"operation {operation} is not declared by the DSL contract"
            )

    def get(self, key: int) -> float:
        self._require_operation("get")
        return self.runtime.get(key)

    def range_query(self, left: int, right: int) -> float:
        self._require_operation("range")
        return self.runtime.range_query(left, right)

    def point_update(self, key: int, value: float) -> None:
        self._require_operation("update")
        self.runtime.point_update(key, value)

    def export_certificate(self) -> dict:
        return json.loads(json.dumps(self.artifact))

    def render_cpp_header(self, namespace: str = "certigap_generated") -> str:
        from .dsl_verifier import verify_dsl_certificate

        verify_dsl_certificate(self.artifact)
        detail_namespace = f"{namespace}::dsl_detail"
        base = generate_cpp_header(
            self.artifact["selection_artifact"],
            namespace=detail_namespace,
            deployment_sha256=self.artifact["sha256"],
            selection_scope=(
                "complete typed CertiGap DSL v1 grammar under the declared "
                "structural model"
            ),
        )
        parts = namespace.split("::")
        operations = set(self.artifact["contract"]["operations"])
        lines = [
            base.rstrip().replace(
                "// Generated by certigap-compile. Do not edit.",
                "// Generated by certigap-dsl. Do not edit.",
                1,
            ),
            "",
        ]
        lines.extend(f"namespace {part} {{" for part in parts)
        lines.extend(
            [
                "",
                "using Config = dsl_detail::Config;",
                "",
                "class Index {",
                "public:",
                "    explicit Index(const std::vector<double>& values)",
                "        : inner_(values) {}",
            ]
        )
        if "get" in operations:
            lines.extend(
                [
                    "",
                    "    double get(int key) const { return inner_.get(key); }",
                ]
            )
        if "range" in operations:
            lines.extend(
                [
                    "",
                    "    double range_query(int left, int right) const {",
                    "        return inner_.range_query(left, right);",
                    "    }",
                ]
            )
        if "update" in operations:
            lines.extend(
                [
                    "",
                    "    void point_update(int key, double value) {",
                    "        inner_.point_update(key, value);",
                    "    }",
                ]
            )
        if self.artifact["contract"]["constraints"][
            "require_persistent_snapshots"
        ]:
            lines.extend(
                [
                    "",
                    "    Index snapshot() const { return *this; }",
                ]
            )
        lines.extend(
            [
                "",
                "    static constexpr certigap::Backend backend() {",
                "        return dsl_detail::Index::backend();",
                "    }",
                "    static constexpr certigap::Aggregate aggregate() {",
                "        return dsl_detail::Index::aggregate();",
                "    }",
                "    static constexpr const char* artifact_sha256() {",
                "        return dsl_detail::Config::kArtifactSha256;",
                "    }",
                "",
                "private:",
                "    dsl_detail::Index inner_;",
                "};",
                "",
                "inline constexpr const char* kSelectedName =",
                "    dsl_detail::kSelectedName;",
                "",
            ]
        )
        lines.extend(f"}}  // namespace {part}" for part in reversed(parts))
        return "\n".join(lines) + "\n"


def compile_proof_carrying_index(
    values: Iterable[float],
    train_trace: WorkloadTrace,
    spec: ProofCarryingSpec,
    *,
    holdout_trace: WorkloadTrace | None = None,
) -> ProofCarryingIndex:
    if not isinstance(spec, ProofCarryingSpec):
        raise TypeError("spec must be ProofCarryingSpec")
    value_list = [float(value) for value in values]
    if not value_list or any(not math.isfinite(value) for value in value_list):
        raise ValueError("values must be a non-empty finite sequence")
    spec.validate(len(value_list))
    runtime = compile_from_spec(
        value_list, train_trace, spec._adaptive(), holdout_trace=holdout_trace
    )
    base = runtime.export_selection_artifact()
    algebra = json.loads(json.dumps(_ALGEBRAS[spec.algebra]))
    grammar = {
        "schema": "certigap-typed-design-grammar-v1",
        "designs": _typed_designs(base, algebra),
    }
    grammar["sha256"] = _canonical_sha256(grammar)
    selected_design = next(
        row["id"]
        for row in grammar["designs"]
        if row["backend"] == base["selected"]
    )
    artifact = {
        "schema": "certigap-proof-carrying-dsl-v1",
        "contract": spec.contract(),
        "algebra": algebra,
        "grammar": grammar,
        "selection_artifact": base,
        "selected_design": selected_design,
        "claim_boundary": (
            "The certificate proves typed capability compatibility and the "
            "minimum declared analytical score over the complete DSL v1 "
            "grammar. It does not prove portable wall-clock optimality or "
            "optimality outside this fixed-size grammar."
        ),
    }
    artifact["sha256"] = _canonical_sha256(artifact)

    from .dsl_verifier import verify_dsl_certificate

    verify_dsl_certificate(artifact)
    return ProofCarryingIndex(runtime=runtime, artifact=artifact)
