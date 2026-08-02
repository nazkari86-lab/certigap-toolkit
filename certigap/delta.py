from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Iterable, Literal


DeltaAlgebra = Literal["sum", "min", "max"]


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


@dataclass(frozen=True)
class DeltaSpec:
    algebra: DeltaAlgebra = "sum"
    rebuild_threshold: int = 64

    def validate(self) -> None:
        if self.algebra not in {"sum", "min", "max"}:
            raise ValueError("algebra must be sum, min, or max")
        if not isinstance(self.rebuild_threshold, int) or self.rebuild_threshold < 1:
            raise ValueError("rebuild_threshold must be a positive integer")

    def contract(self) -> dict:
        self.validate()
        return {
            "schema": "certigap-delta-contract-v1",
            "key_semantics": "unique_signed_integer_keys",
            "range_semantics": "inclusive_key_interval",
            "operations": ["get", "range", "insert", "update", "erase"],
            "algebra": self.algebra,
            "rebuild_threshold": self.rebuild_threshold,
            "rebuild_rule": "after_mutation_when_distinct_delta_keys_reach_threshold",
        }


class ProofCarryingDeltaIndex:
    """Sorted immutable base plus a bounded mutable delta and replay log."""

    def __init__(self, items: Iterable[tuple[int, float]], spec: DeltaSpec):
        if not isinstance(spec, DeltaSpec):
            raise TypeError("spec must be DeltaSpec")
        spec.validate()
        parsed: dict[int, float] = {}
        for key, raw_value in items:
            if not isinstance(key, int) or isinstance(key, bool):
                raise TypeError("keys must be integers")
            value = float(raw_value)
            if not math.isfinite(value):
                raise ValueError("values must be finite")
            if key in parsed:
                raise ValueError(f"duplicate key: {key}")
            parsed[key] = value
        self._spec = spec
        self._initial = self._rows(parsed)
        self._base = parsed
        self._delta: dict[int, float | None] = {}
        self._events: list[dict] = []
        self._rebuilds = 0

    @staticmethod
    def _rows(values: dict[int, float]) -> list[list[int | float]]:
        return [[key, values[key]] for key in sorted(values)]

    def _current(self) -> dict[int, float]:
        values = dict(self._base)
        for key, value in self._delta.items():
            if value is None:
                values.pop(key, None)
            else:
                values[key] = value
        return values

    def _record(self, event: dict) -> None:
        self._events.append({"sequence": len(self._events), **event})

    def _maybe_rebuild(self) -> None:
        if len(self._delta) < self._spec.rebuild_threshold:
            return
        count = len(self._delta)
        self._base = self._current()
        self._delta.clear()
        self._rebuilds += 1
        rows = self._rows(self._base)
        self._record({
            "operation": "rebuild",
            "compacted_delta_keys": count,
            "entry_count": len(rows),
            "state_sha256": _digest(rows),
        })

    def get(self, key: int) -> float:
        values = self._current()
        if key not in values:
            raise KeyError(key)
        result = values[key]
        self._record({"operation": "get", "key": key, "result": result})
        return result

    def range_query(self, left: int, right: int) -> float:
        if left > right:
            raise ValueError("left must not exceed right")
        selected = [
            value for key, value in self._current().items() if left <= key <= right
        ]
        if self._spec.algebra == "sum":
            result = float(sum(selected))
        elif self._spec.algebra == "min":
            result = min(selected, default=math.inf)
        else:
            result = max(selected, default=-math.inf)
        recorded_result: float | str = result
        if math.isinf(result):
            recorded_result = "positive_infinity" if result > 0 else "negative_infinity"
        self._record({
            "operation": "range",
            "left": left,
            "right": right,
            "result": recorded_result,
        })
        return result

    def insert(self, key: int, value: float) -> None:
        if key in self._current():
            raise KeyError(f"key already exists: {key}")
        self._write("insert", key, value)

    def update(self, key: int, value: float) -> None:
        if key not in self._current():
            raise KeyError(key)
        self._write("update", key, value)

    def _write(self, operation: str, key: int, raw_value: float) -> None:
        if not isinstance(key, int) or isinstance(key, bool):
            raise TypeError("keys must be integers")
        value = float(raw_value)
        if not math.isfinite(value):
            raise ValueError("values must be finite")
        self._delta[key] = value
        self._record({"operation": operation, "key": key, "value": value})
        self._maybe_rebuild()

    def erase(self, key: int) -> None:
        if key not in self._current():
            raise KeyError(key)
        self._delta[key] = None
        self._record({"operation": "erase", "key": key})
        self._maybe_rebuild()

    def export_certificate(self) -> dict:
        final = self._rows(self._current())
        artifact = {
            "schema": "certigap-proof-carrying-delta-v1",
            "contract": self._spec.contract(),
            "initial_entries": self._initial,
            "initial_sha256": _digest(self._initial),
            "events": json.loads(json.dumps(self._events, allow_nan=False)),
            "final_entries": final,
            "final_sha256": _digest(final),
            "summary": {
                "event_count": len(self._events),
                "rebuild_count": self._rebuilds,
                "final_entry_count": len(final),
            },
            "claim_boundary": (
                "The certificate replays ordered-map semantics and every deterministic "
                "delta compaction. It does not certify wall-clock optimality, durability, "
                "or concurrent progress."
            ),
        }
        artifact["sha256"] = _digest(artifact)
        from .delta_verifier import verify_delta_certificate

        verify_delta_certificate(artifact)
        return artifact


def compile_proof_carrying_delta_index(
    items: Iterable[tuple[int, float]], spec: DeltaSpec | None = None
) -> ProofCarryingDeltaIndex:
    return ProofCarryingDeltaIndex(items, spec or DeltaSpec())
