from __future__ import annotations

import hashlib
import json
import math
from typing import cast

from .autoindex import (
    CandidateName,
    TraceOperation,
    WorkloadTrace,
    _PreparedAnalyticalPortfolio,
)
from .autoindex_verifier import verify_autoindex_artifact


class TrackingAutoIndexVerificationError(ValueError):
    pass


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _close(left: object, right: float) -> bool:
    if (
        not isinstance(left, (int, float))
        or isinstance(left, bool)
        or not math.isfinite(float(left))
    ):
        return False
    return math.isclose(float(left), right, rel_tol=1e-12, abs_tol=1e-12)


def _distance(left: str, right: str, migration_cost: float) -> float:
    return 0.0 if left == right else migration_cost


def _oracle(
    rows: list[dict[str, float]],
    candidates: tuple[str, ...],
    initial: str,
    migration_cost: float,
    max_switches: int,
) -> dict:
    horizon = len(rows)
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
    for row in rows:
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


def _same_oracle(supplied: dict, expected: dict) -> bool:
    return (
        _close(supplied.get("cost"), expected["cost"])
        and supplied.get("switches") == expected["switches"]
        and supplied.get("path") == expected["path"]
    )


def verify_tracking_autoindex_certificate(artifact: dict) -> dict:
    try:
        if not isinstance(artifact, dict):
            raise TrackingAutoIndexVerificationError(
                "artifact must be a JSON object"
            )
        expected_fields = {
            "schema",
            "n",
            "spec",
            "policy",
            "candidates",
            "steps",
            "actual_cost",
            "constrained_oracle",
            "unrestricted_oracle",
            "dynamic_regret",
            "wfa_competitive_factor",
            "observed_factor_bound",
            "observed_factor_bound_holds",
            "autoindex_artifact",
            "scope",
            "theorem_scope",
            "sha256",
        }
        if set(artifact) != expected_fields:
            raise TrackingAutoIndexVerificationError(
                "tracking artifact fields mismatch"
            )
        if artifact.get("schema") != "certigap-tracking-autoindex-v1":
            raise TrackingAutoIndexVerificationError("unsupported schema")
        supplied_sha = artifact.get("sha256")
        unsigned = dict(artifact)
        unsigned.pop("sha256", None)
        if supplied_sha != _canonical_sha256(unsigned):
            raise TrackingAutoIndexVerificationError("artifact digest mismatch")
        verify_autoindex_artifact(artifact["autoindex_artifact"])
        autoindex = artifact["autoindex_artifact"]
        if artifact["n"] != autoindex["n"]:
            raise TrackingAutoIndexVerificationError("key universe mismatch")
        if artifact["spec"]["constraints"] != autoindex["constraints"]:
            raise TrackingAutoIndexVerificationError("spec constraints mismatch")
        if set(artifact["spec"]) != {
            "schema",
            "operations",
            "fixed_size",
            "constraints",
            "unsupported_operations",
            "claim_boundary",
        } or (
            artifact["spec"].get("schema") != "certigap-adaptive-spec-v1"
            or artifact["spec"].get("fixed_size") is not True
            or not isinstance(artifact["spec"].get("operations"), list)
            or not artifact["spec"]["operations"]
            or len(set(artifact["spec"]["operations"]))
            != len(artifact["spec"]["operations"])
            or not set(artifact["spec"]["operations"])
            <= {"get", "range", "update"}
        ):
            raise TrackingAutoIndexVerificationError("invalid adaptive spec")
        expected_candidates = tuple(
            row["name"] for row in autoindex["candidates"] if row["feasible"]
        )
        candidates = tuple(artifact["candidates"])
        if candidates != expected_candidates or not candidates:
            raise TrackingAutoIndexVerificationError("candidate set mismatch")
        policy = artifact["policy"]
        if set(policy) != {
            "migration_cost_units",
            "max_comparator_switches",
            "initial_candidate",
        }:
            raise TrackingAutoIndexVerificationError("policy fields mismatch")
        migration = policy["migration_cost_units"]
        if (
            not isinstance(migration, (int, float))
            or isinstance(migration, bool)
            or not math.isfinite(float(migration))
            or migration <= 0.0
        ):
            raise TrackingAutoIndexVerificationError("invalid migration cost")
        migration = float(migration)
        limit = policy["max_comparator_switches"]
        if (
            not isinstance(limit, int)
            or isinstance(limit, bool)
            or limit < 0
        ):
            raise TrackingAutoIndexVerificationError("invalid switch limit")
        initial = policy["initial_candidate"]
        if initial not in candidates:
            raise TrackingAutoIndexVerificationError("invalid initial candidate")
        if not isinstance(artifact["steps"], list) or not artifact["steps"]:
            raise TrackingAutoIndexVerificationError("empty tracking history")

        work = {
            candidate: _distance(initial, candidate, migration)
            for candidate in candidates
        }
        selected = initial
        cumulative = 0.0
        service_rows: list[dict[str, float]] = []
        service_cache: dict[tuple, dict[str, float]] = {}
        cost_evaluator = _PreparedAnalyticalPortfolio(autoindex)
        for step in artifact["steps"]:
            if set(step) != {
                "operation",
                "service_costs",
                "work_function",
                "previous",
                "selected",
                "switched",
                "migration_cost",
                "service_cost",
                "cumulative_cost",
            }:
                raise TrackingAutoIndexVerificationError(
                    "tracking step fields mismatch"
                )
            raw = step["operation"]
            if set(raw) != {"kind", "left", "right", "value"}:
                raise TrackingAutoIndexVerificationError(
                    "operation fields mismatch"
                )
            operation = TraceOperation(
                raw["kind"], raw["left"], raw["right"], raw["value"]
            )
            if operation.kind not in artifact["spec"]["operations"]:
                raise TrackingAutoIndexVerificationError(
                    "operation is outside the adaptive spec"
                )
            one = WorkloadTrace(artifact["n"], (operation,))
            signature = (operation.kind, operation.left, operation.right)
            cached = service_cache.get(signature)
            if cached is None:
                portfolio = cost_evaluator.costs(one)
                cached = {
                    candidate: portfolio[cast(CandidateName, candidate)][0]
                    for candidate in candidates
                }
                service_cache[signature] = cached
            service = dict(cached)
            if set(step["service_costs"]) != set(candidates) or any(
                not _close(step["service_costs"][candidate], service[candidate])
                for candidate in candidates
            ):
                raise TrackingAutoIndexVerificationError(
                    "service cost replay mismatch"
                )
            next_work = {
                candidate: service[candidate]
                + min(
                    work[prior] + _distance(prior, candidate, migration)
                    for prior in candidates
                )
                for candidate in candidates
            }
            expected_selected = min(
                candidates,
                key=lambda candidate: (
                    next_work[candidate]
                    + _distance(selected, candidate, migration),
                    candidates.index(candidate),
                ),
            )
            switched = expected_selected != selected
            migration_paid = _distance(selected, expected_selected, migration)
            cumulative += migration_paid + service[expected_selected]
            if (
                set(step["work_function"]) != set(candidates)
                or any(
                    not _close(
                        step["work_function"][candidate], next_work[candidate]
                    )
                    for candidate in candidates
                )
                or step["previous"] != selected
                or step["selected"] != expected_selected
                or step["switched"] is not switched
                or not _close(step["migration_cost"], migration_paid)
                or not _close(
                    step["service_cost"], service[expected_selected]
                )
                or not _close(step["cumulative_cost"], cumulative)
            ):
                raise TrackingAutoIndexVerificationError(
                    "work-function replay mismatch"
                )
            work = next_work
            selected = expected_selected
            service_rows.append(service)

        constrained = _oracle(
            service_rows, candidates, initial, migration, limit
        )
        unrestricted = _oracle(
            service_rows, candidates, initial, migration, len(service_rows)
        )
        if any(
            not isinstance(artifact[name], dict)
            or set(artifact[name]) != {"cost", "switches", "path"}
            for name in ("constrained_oracle", "unrestricted_oracle")
        ):
            raise TrackingAutoIndexVerificationError("oracle fields mismatch")
        if not _same_oracle(artifact["constrained_oracle"], constrained):
            raise TrackingAutoIndexVerificationError(
                "constrained oracle mismatch"
            )
        if not _same_oracle(artifact["unrestricted_oracle"], unrestricted):
            raise TrackingAutoIndexVerificationError(
                "unrestricted oracle mismatch"
            )
        factor = 2 * len(candidates) - 1
        upper = factor * unrestricted["cost"]
        bound_holds = cumulative <= upper + 1e-9
        if (
            not _close(artifact["actual_cost"], cumulative)
            or not _close(
                artifact["dynamic_regret"], cumulative - constrained["cost"]
            )
            or artifact["wfa_competitive_factor"] != factor
            or not _close(artifact["observed_factor_bound"], upper)
            or artifact["observed_factor_bound_holds"] is not bound_holds
            or not isinstance(artifact.get("theorem_scope"), str)
        ):
            raise TrackingAutoIndexVerificationError(
                "tracking guarantee mismatch"
            )
    except TrackingAutoIndexVerificationError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise TrackingAutoIndexVerificationError(
            "malformed tracking certificate"
        ) from exc
    return {
        "verified": True,
        "operations": len(artifact["steps"]),
        "actual_cost": artifact["actual_cost"],
        "dynamic_regret": artifact["dynamic_regret"],
        "wfa_competitive_factor": artifact["wfa_competitive_factor"],
        "observed_factor_bound_holds": artifact[
            "observed_factor_bound_holds"
        ],
    }
