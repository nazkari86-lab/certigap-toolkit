from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from typing import Iterable, cast

from .autoindex import (
    PORTFOLIO_ORDER,
    CandidateName,
    TraceOperation,
    WorkloadTrace,
    _analytical_portfolio_costs_verified,
    materialize_autoindex_candidate,
)
from .dynamic_range import DynamicCertiRange
from .spec import AdaptiveSpec, compile_from_spec


@dataclass(frozen=True)
class TrackingPolicy:
    migration_cost_units: float = 8.0
    max_comparator_switches: int = 4
    initial_candidate: str = "sorted_array"

    def validate(self) -> None:
        if (
            not math.isfinite(self.migration_cost_units)
            or self.migration_cost_units <= 0.0
        ):
            raise ValueError("migration_cost_units must be finite and positive")
        if (
            not isinstance(self.max_comparator_switches, int)
            or isinstance(self.max_comparator_switches, bool)
            or self.max_comparator_switches < 0
        ):
            raise ValueError("max_comparator_switches must be non-negative")
        if self.initial_candidate not in PORTFOLIO_ORDER:
            raise ValueError("initial_candidate is outside the portfolio")


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _distance(left: str, right: str, migration_cost: float) -> float:
    return 0.0 if left == right else migration_cost


def _offline_oracle(
    service_rows: list[dict[str, float]],
    candidates: tuple[str, ...],
    initial: str,
    migration_cost: float,
    max_switches: int,
) -> dict:
    horizon = len(service_rows)
    limit = min(max_switches, horizon)
    infinity = float("inf")
    previous = {
        (candidate, switches): (
            0.0 if candidate == initial and switches == 0 else infinity
        )
        for candidate in candidates
        for switches in range(limit + 1)
    }
    parents: list[dict[tuple[str, int], tuple[str, int]]] = []
    for row in service_rows:
        current: dict[tuple[str, int], float] = {}
        parent: dict[tuple[str, int], tuple[str, int]] = {}
        for candidate in candidates:
            for switches in range(limit + 1):
                best = infinity
                best_parent: tuple[str, int] | None = None
                for prior in candidates:
                    changed = int(prior != candidate)
                    prior_switches = switches - changed
                    if prior_switches < 0:
                        continue
                    value = (
                        previous[(prior, prior_switches)]
                        + _distance(prior, candidate, migration_cost)
                        + row[candidate]
                    )
                    if value < best - 1e-12:
                        best = value
                        best_parent = (prior, prior_switches)
                current[(candidate, switches)] = best
                if best_parent is not None:
                    parent[(candidate, switches)] = best_parent
        previous = current
        parents.append(parent)
    terminal = min(
        previous,
        key=lambda state: (
            previous[state],
            state[1],
            candidates.index(state[0]),
        ),
    )
    path: list[str] = []
    state = terminal
    for parent in reversed(parents):
        path.append(state[0])
        state = parent[state]
    path.reverse()
    return {
        "cost": previous[terminal],
        "switches": terminal[1],
        "path": path,
    }


def _runtime_get(runtime: object, key: int) -> float:
    if isinstance(runtime, DynamicCertiRange):
        return float(runtime.get(key, track=False))
    return float(runtime.get(key))


def _runtime_range(runtime: object, left: int, right: int) -> float:
    if isinstance(runtime, DynamicCertiRange):
        return float(runtime.range_query(left, right, track=False))
    return float(runtime.range_query(left, right))


class TrackingAutoIndex:
    """Causal Work Function Algorithm over feasible AutoIndex backends."""

    def __init__(
        self,
        values: list[float],
        autoindex_artifact: dict,
        spec: AdaptiveSpec,
        policy: TrackingPolicy,
    ) -> None:
        if not isinstance(spec, AdaptiveSpec):
            raise TypeError("spec must be AdaptiveSpec")
        policy.validate()
        from .autoindex_verifier import verify_autoindex_artifact

        verify_autoindex_artifact(autoindex_artifact)
        spec.validate(len(values))
        if (
            not values
            or any(not math.isfinite(float(value)) for value in values)
            or isinstance(autoindex_artifact.get("n"), bool)
            or autoindex_artifact["n"] != len(values)
            or autoindex_artifact["constraints"] != asdict(spec.to_constraints())
        ):
            raise ValueError("AutoIndex artifact does not match values and spec")
        self._values = list(values)
        self._artifact = json.loads(json.dumps(autoindex_artifact))
        self._spec = spec
        self._policy = policy
        self._candidates = tuple(
            row["name"]
            for row in autoindex_artifact["candidates"]
            if row["feasible"]
        )
        if policy.initial_candidate not in self._candidates:
            raise ValueError("initial candidate is infeasible")
        self._selected = policy.initial_candidate
        self._runtime = materialize_autoindex_candidate(
            self._values,
            self._artifact,
            cast(CandidateName, self._selected),
        )
        self._work = {
            candidate: _distance(
                self._selected, candidate, policy.migration_cost_units
            )
            for candidate in self._candidates
        }
        self._steps: list[dict] = []
        self._service_cache: dict[tuple, dict[str, float]] = {}

    @property
    def selected_name(self) -> str:
        return self._selected

    @property
    def switch_count(self) -> int:
        return sum(step["switched"] for step in self._steps)

    def _step(self, operation: TraceOperation) -> float | None:
        one = WorkloadTrace(len(self._values), (operation,))
        signature = (
            operation.kind,
            operation.left,
            operation.right,
        )
        cached = self._service_cache.get(signature)
        if cached is None:
            portfolio = _analytical_portfolio_costs_verified(self._artifact, one)
            cached = {
                candidate: portfolio[cast(CandidateName, candidate)][0]
                for candidate in self._candidates
            }
            self._service_cache[signature] = cached
        service = dict(cached)
        next_work = {
            candidate: service[candidate]
            + min(
                self._work[prior]
                + _distance(
                    prior,
                    candidate,
                    self._policy.migration_cost_units,
                )
                for prior in self._candidates
            )
            for candidate in self._candidates
        }
        previous = self._selected
        selected = min(
            self._candidates,
            key=lambda candidate: (
                next_work[candidate]
                + _distance(
                    previous,
                    candidate,
                    self._policy.migration_cost_units,
                ),
                self._candidates.index(candidate),
            ),
        )
        migration = _distance(
            previous, selected, self._policy.migration_cost_units
        )
        if selected != previous:
            self._runtime = materialize_autoindex_candidate(
                self._values,
                self._artifact,
                cast(CandidateName, selected),
            )
        if operation.kind == "get":
            result: float | None = _runtime_get(self._runtime, operation.left)
        elif operation.kind == "range":
            result = _runtime_range(
                self._runtime, operation.left, operation.right
            )
        else:
            self._runtime.point_update(operation.left, operation.value)
            self._values[operation.left - 1] = operation.value
            result = None
        prior_total = self._steps[-1]["cumulative_cost"] if self._steps else 0.0
        self._steps.append(
            {
                "operation": operation.to_dict(),
                "service_costs": service,
                "work_function": next_work,
                "previous": previous,
                "selected": selected,
                "switched": selected != previous,
                "migration_cost": migration,
                "service_cost": service[selected],
                "cumulative_cost": prior_total + migration + service[selected],
            }
        )
        self._selected = selected
        self._work = next_work
        return result

    def get(self, key: int) -> float:
        result = self._step(TraceOperation("get", key, key))
        assert result is not None
        return result

    def range_query(self, left: int, right: int) -> float:
        result = self._step(TraceOperation("range", left, right))
        assert result is not None
        return result

    def point_update(self, key: int, value: float) -> None:
        self._step(TraceOperation("update", key, key, float(value)))

    def snapshot(self):
        if not isinstance(self._runtime, DynamicCertiRange):
            raise RuntimeError(
                f"{self._selected} does not provide persistent snapshots"
            )
        return self._runtime.snapshot()

    def explain(self) -> dict:
        return {
            "selected": self._selected,
            "operations": len(self._steps),
            "switches": self.switch_count,
            "cumulative_cost": (
                0.0 if not self._steps else self._steps[-1]["cumulative_cost"]
            ),
        }

    def export_certificate(self) -> dict:
        if not self._steps:
            raise RuntimeError("at least one operation is required")
        service_rows = [step["service_costs"] for step in self._steps]
        constrained = _offline_oracle(
            service_rows,
            self._candidates,
            self._policy.initial_candidate,
            self._policy.migration_cost_units,
            self._policy.max_comparator_switches,
        )
        unrestricted = _offline_oracle(
            service_rows,
            self._candidates,
            self._policy.initial_candidate,
            self._policy.migration_cost_units,
            len(self._steps),
        )
        actual = self._steps[-1]["cumulative_cost"]
        factor = 2 * len(self._candidates) - 1
        unsigned = {
            "schema": "certigap-tracking-autoindex-v1",
            "n": len(self._values),
            "spec": self._spec.to_dict(),
            "policy": asdict(self._policy),
            "candidates": list(self._candidates),
            "steps": self._steps,
            "actual_cost": actual,
            "constrained_oracle": constrained,
            "unrestricted_oracle": unrestricted,
            "dynamic_regret": actual - constrained["cost"],
            "wfa_competitive_factor": factor,
            "observed_factor_bound": factor * unrestricted["cost"],
            "observed_factor_bound_holds": (
                actual <= factor * unrestricted["cost"] + 1e-9
            ),
            "autoindex_artifact": self._artifact,
            "scope": (
                "causal deterministic Work Function Algorithm over the fixed "
                "feasible portfolio with a positive uniform metric migration "
                "cost; the exact replay oracle uses the recorded structural "
                "cost model, not wall-clock latency"
            ),
            "theorem_scope": (
                "The classical finite metrical-task-system WFA guarantee is "
                "(2m-1)-competitive under its standard theorem conventions, "
                "including initialization-dependent additive terms. This "
                "artifact verifies the realized trajectory and exact ex-post "
                "oracles; observed_factor_bound_holds is an observation for "
                "this trace, not a standalone proof of the universal theorem."
            ),
        }
        artifact = unsigned | {"sha256": _canonical_sha256(unsigned)}
        from .tracking_autoindex_verifier import (
            verify_tracking_autoindex_certificate,
        )

        verify_tracking_autoindex_certificate(artifact)
        return json.loads(json.dumps(artifact))


def start_tracking_autoindex(
    values: Iterable[float],
    train_trace: WorkloadTrace,
    spec: AdaptiveSpec,
    *,
    policy: TrackingPolicy = TrackingPolicy(),
) -> TrackingAutoIndex:
    if not isinstance(spec, AdaptiveSpec):
        raise TypeError("spec must be AdaptiveSpec")
    if not isinstance(policy, TrackingPolicy):
        raise TypeError("policy must be TrackingPolicy")
    value_list = [float(value) for value in values]
    compiled = compile_from_spec(value_list, train_trace, spec)
    return TrackingAutoIndex(
        value_list,
        compiled.export_selection_artifact(),
        spec,
        policy,
    )
