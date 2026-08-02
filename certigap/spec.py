from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Literal

from .autoindex import (
    AutoIndexConstraints,
    CompiledAutoIndex,
    WorkloadTrace,
    compile_autoindex,
)


OperationName = Literal["get", "range", "update"]


@dataclass(frozen=True)
class AdaptiveSpec:
    """Declarative contract for a fixed-size ordered adaptive container."""

    operations: tuple[OperationName, ...] = ("get", "range", "update")
    aggregate: Literal["sum", "min", "max"] = "sum"
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

    def validate(self, n: int) -> None:
        allowed = {"get", "range", "update"}
        if (
            not self.operations
            or len(set(self.operations)) != len(self.operations)
            or any(operation not in allowed for operation in self.operations)
        ):
            raise ValueError("operations must be unique supported operation names")
        self.to_constraints().validate(n)

    def to_constraints(self) -> AutoIndexConstraints:
        return AutoIndexConstraints(
            aggregate=self.aggregate,
            budget=self.budget,
            tail_weight=self.tail_weight,
            memory_limit_slots=self.memory_limit_slots,
            max_depth=self.max_depth,
            require_persistent_snapshots=self.require_persistent_snapshots,
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

    def validate_trace(self, trace: WorkloadTrace, *, role: str) -> None:
        if not isinstance(trace, WorkloadTrace):
            raise TypeError(f"{role} trace must be WorkloadTrace")
        undeclared = sorted(
            {operation.kind for operation in trace.operations}
            - set(self.operations)
        )
        if undeclared:
            raise ValueError(
                f"{role} trace contains undeclared operations: "
                + ", ".join(undeclared)
            )

    def to_dict(self) -> dict:
        return {
            "schema": "certigap-adaptive-spec-v1",
            "operations": list(self.operations),
            "fixed_size": True,
            "constraints": self.to_constraints().__dict__,
            "unsupported_operations": [
                "insert",
                "erase",
                "range_add",
                "range_assign",
            ],
            "claim_boundary": (
                "The current contract covers fixed-size get/range/update "
                "containers; unsupported operations fail before compilation."
            ),
        }


def compile_from_spec(
    values: Iterable[float],
    train_trace: WorkloadTrace,
    spec: AdaptiveSpec,
    *,
    holdout_trace: WorkloadTrace | None = None,
) -> CompiledAutoIndex:
    if not isinstance(spec, AdaptiveSpec):
        raise TypeError("spec must be AdaptiveSpec")
    value_list = [float(value) for value in values]
    if not value_list or any(not math.isfinite(value) for value in value_list):
        raise ValueError("values must be a non-empty finite sequence")
    spec.validate(len(value_list))
    spec.validate_trace(train_trace, role="training")
    if holdout_trace is not None:
        spec.validate_trace(holdout_trace, role="holdout")
    return compile_autoindex(
        value_list,
        train_trace,
        constraints=spec.to_constraints(),
        holdout_trace=holdout_trace,
    )
