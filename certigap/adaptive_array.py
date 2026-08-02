from __future__ import annotations

import math
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .adaptive_profile import parse_adaptive_profile_text
from .autoindex import (
    AutoIndexConstraints,
    CompiledAutoIndex,
    WorkloadTrace,
    compile_autoindex,
)


@dataclass(frozen=True)
class AdaptiveArrayPolicy:
    warmup_operations: int = 256
    check_interval: int = 10_000
    minimum_tv_drift: float = 0.10
    minimum_relative_improvement: float = 0.05
    max_profile_operations: int = 100_000
    automatic_maintenance: bool = True
    profile_path: Path | None = None

    def validate(self) -> None:
        if any(
            not isinstance(value, int) or isinstance(value, bool) or value <= 0
            for value in (
                self.warmup_operations,
                self.check_interval,
                self.max_profile_operations,
            )
        ):
            raise ValueError("operation thresholds must be positive integers")
        if self.max_profile_operations < self.warmup_operations:
            raise ValueError("profile capacity must cover warmup")
        if (
            not math.isfinite(self.minimum_tv_drift)
            or not 0.0 <= self.minimum_tv_drift <= 1.0
            or not math.isfinite(self.minimum_relative_improvement)
            or self.minimum_relative_improvement < 0.0
        ):
            raise ValueError("invalid adaptive deployment thresholds")
        if self.profile_path is not None and not isinstance(
            self.profile_path, Path
        ):
            raise TypeError("profile_path must be pathlib.Path or None")


class AdaptiveArray:
    """Zero-based adaptive ordered container over the verified AutoIndex portfolio."""

    def __init__(
        self,
        values: Iterable[float],
        *,
        policy: AdaptiveArrayPolicy = AdaptiveArrayPolicy(),
        constraints: AutoIndexConstraints = AutoIndexConstraints(),
    ) -> None:
        self._values = [float(value) for value in values]
        if not self._values or any(
            not math.isfinite(value) for value in self._values
        ):
            raise ValueError("values must be a non-empty finite sequence")
        if not isinstance(policy, AdaptiveArrayPolicy):
            raise TypeError("policy must be AdaptiveArrayPolicy")
        if not isinstance(constraints, AutoIndexConstraints):
            raise TypeError("constraints must be AutoIndexConstraints")
        policy.validate()
        constraints.validate(len(self._values))
        self._policy = policy
        self._constraints = constraints
        self._gets: dict[int, int] = {}
        self._updates: dict[int, int] = {}
        self._ranges: dict[tuple[int, int], int] = {}
        self._profile_total = 0
        self._runtime: CompiledAutoIndex | None = None
        self._selected = "sorted_array"
        self._operations_since_attempt = 0
        self._lifetime_operations = 0
        self._last_distribution: tuple[float, ...] | None = None
        self._decision = {
            "attempted": False,
            "switched": False,
            "previous": "sorted_array",
            "selected": "sorted_array",
            "relative_improvement": 0.0,
            "reason": "collecting warmup profile",
        }
        self._lock = threading.RLock()
        if policy.profile_path is not None and policy.profile_path.is_file():
            self._load_profile(policy.profile_path)
            if self.profile_operations >= policy.warmup_operations:
                self.maintenance()

    @property
    def selected_name(self) -> str:
        with self._lock:
            return self._selected

    @property
    def optimized(self) -> bool:
        with self._lock:
            return self._runtime is not None

    @property
    def profile_operations(self) -> int:
        with self._lock:
            return self._profile_total

    @property
    def lifetime_operations(self) -> int:
        with self._lock:
            return self._lifetime_operations

    def __len__(self) -> int:
        return len(self._values)

    def _position(self, position: int) -> int:
        if (
            not isinstance(position, int)
            or isinstance(position, bool)
            or not 0 <= position < len(self._values)
        ):
            raise IndexError("adaptive array position out of range")
        return position

    def _range(self, first: int, last: int) -> tuple[int, int]:
        if (
            not isinstance(first, int)
            or isinstance(first, bool)
            or not isinstance(last, int)
            or isinstance(last, bool)
            or first < 0
            or last <= first
            or last > len(self._values)
        ):
            raise IndexError("adaptive array range must be non-empty [first,last)")
        return first, last

    def get(self, position: int) -> float:
        with self._lock:
            position = self._position(position)
            result = (
                self._values[position]
                if self._runtime is None
                else self._runtime.get(position + 1)
            )
            self._record(self._gets, position)
            self._automatic_maintenance()
            return result

    def range_query(self, first: int, last: int) -> float:
        with self._lock:
            first, last = self._range(first, last)
            if self._runtime is None:
                selected = self._values[first:last]
                if self._constraints.aggregate == "sum":
                    result = sum(selected)
                elif self._constraints.aggregate == "min":
                    result = min(selected)
                else:
                    result = max(selected)
            else:
                result = self._runtime.range_query(first + 1, last)
            self._record(self._ranges, (first, last))
            self._automatic_maintenance()
            return result

    def range_sum(self, first: int, last: int) -> float:
        if self._constraints.aggregate != "sum":
            raise RuntimeError("range_sum requires aggregate='sum'")
        return self.range_query(first, last)

    def update(self, position: int, value: float) -> None:
        with self._lock:
            position = self._position(position)
            numeric = float(value)
            if not math.isfinite(numeric):
                raise ValueError("value must be finite")
            self._values[position] = numeric
            if self._runtime is not None:
                self._runtime.point_update(position + 1, numeric)
            self._record(self._updates, position)
            self._automatic_maintenance()

    def _record(self, target: dict, key: object) -> None:
        if self._profile_total >= self._policy.max_profile_operations:
            self._decay_profile()
        target[key] = target.get(key, 0) + 1
        self._profile_total += 1
        self._operations_since_attempt += 1
        self._lifetime_operations += 1

    def _decay_profile(self) -> None:
        for target in (self._gets, self._updates, self._ranges):
            decayed = {
                key: value // 2 for key, value in target.items() if value // 2 > 0
            }
            target.clear()
            target.update(decayed)
        self._profile_total = (
            sum(self._gets.values())
            + sum(self._updates.values())
            + sum(self._ranges.values())
        )

    def _trace(self) -> WorkloadTrace:
        trace = WorkloadTrace(len(self._values))
        for position, count in sorted(self._gets.items()):
            for _ in range(count):
                trace.add_get(position + 1)
        for (first, last), count in sorted(self._ranges.items()):
            for _ in range(count):
                trace.add_range(first + 1, last)
        for position, count in sorted(self._updates.items()):
            for _ in range(count):
                trace.add_update(position + 1)
        return trace

    def _distribution(self) -> tuple[float, ...]:
        heat = [1e-12] * len(self._values)
        for position, count in self._gets.items():
            heat[position] += count
        for position, count in self._updates.items():
            heat[position] += count
        difference = [0.0] * (len(self._values) + 1)
        for (first, last), count in self._ranges.items():
            per_position = count / (last - first)
            difference[first] += per_position
            difference[last] -= per_position
        running = 0.0
        for position in range(len(heat)):
            running += difference[position]
            heat[position] += running
        total = sum(heat)
        return tuple(value / total for value in heat)

    def maintenance(self) -> bool:
        with self._lock:
            if self.profile_operations < self._policy.warmup_operations:
                return False
            if (
                self._runtime is not None
                and self._operations_since_attempt < self._policy.check_interval
            ):
                return False
            distribution = self._distribution()
            if self._runtime is not None and self._last_distribution is not None:
                drift = 0.5 * sum(
                    abs(left - right)
                    for left, right in zip(distribution, self._last_distribution)
                )
                if drift + 1e-12 < self._policy.minimum_tv_drift:
                    self._operations_since_attempt = 0
                    self._decision = {
                        **self._decision,
                        "attempted": False,
                        "switched": False,
                        "reason": "profile drift below reoptimization threshold",
                    }
                    return False
            candidate = compile_autoindex(
                self._values,
                self._trace(),
                constraints=self._constraints,
            )
            rows = candidate.artifact["candidates"]
            previous_row = next(
                row for row in rows if row["name"] == self._selected
            )
            selected_row = next(
                row for row in rows if row["name"] == candidate.selected_name
            )
            previous_score = float(previous_row["train"]["score"])
            selected_score = float(selected_row["train"]["score"])
            improvement = (previous_score - selected_score) / max(
                abs(previous_score), 1e-12
            )
            previous = self._selected
            accepted = (
                candidate.selected_name == previous
                or improvement + 1e-12
                >= self._policy.minimum_relative_improvement
            )
            if accepted:
                self._runtime = candidate
                self._selected = candidate.selected_name
                self._last_distribution = distribution
            self._operations_since_attempt = 0
            self._decision = {
                "attempted": True,
                "switched": accepted and self._selected != previous,
                "previous": previous,
                "selected": self._selected,
                "previous_score": previous_score,
                "selected_score": selected_score,
                "relative_improvement": improvement,
                "reason": (
                    "candidate passed deployment threshold"
                    if accepted and self._selected != previous
                    else (
                        "current backend remains optimal"
                        if accepted
                        else "candidate improvement below deployment threshold"
                    )
                ),
            }
            if self._policy.profile_path is not None:
                self.save_profile()
            return bool(self._decision["switched"])

    def _automatic_maintenance(self) -> None:
        if self._policy.automatic_maintenance:
            self.maintenance()

    def explain(self) -> dict:
        with self._lock:
            return {
                **self._decision,
                "selected": self._selected,
                "optimized": self.optimized,
                "profile_operations": self.profile_operations,
                "lifetime_operations": self._lifetime_operations,
                "claim_boundary": (
                    "The deployment gate compares modeled structural scores; "
                    "it is not a statistical or wall-clock no-regression bound."
                ),
            }

    def save_profile(self) -> None:
        with self._lock:
            path = self._policy.profile_path
            if path is None:
                raise RuntimeError("profile_path is not configured")
            lines = [
                "CERTIGAP_PROFILE_V1",
                f"size {len(self._values)}",
                f"aggregate {self._constraints.aggregate}",
            ]
            lines.extend(
                f"get {position + 1} {count}"
                for position, count in sorted(self._gets.items())
            )
            lines.extend(
                f"update {position + 1} {count}"
                for position, count in sorted(self._updates.items())
            )
            lines.extend(
                f"range {first + 1} {last} {count}"
                for (first, last), count in sorted(self._ranges.items())
            )
            text = "\n".join((*lines, "end", ""))
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_name(path.name + ".tmp")
            temporary.write_text(text, encoding="utf-8")
            os.replace(temporary, path)

    def _load_profile(self, path: Path) -> None:
        text = path.read_text(encoding="utf-8")
        summary = parse_adaptive_profile_text(text)
        if summary["size"] != len(self._values):
            raise ValueError("profile size mismatch")
        if summary["aggregate"] != self._constraints.aggregate:
            raise ValueError("profile aggregate mismatch")
        for line in text.splitlines()[3:-1]:
            fields = line.split()
            count = float(fields[-1])
            if not count.is_integer():
                raise ValueError("Python AdaptiveArray requires integer weights")
            integer = int(count)
            if fields[0] == "get":
                position = int(fields[1]) - 1
                self._gets[position] = self._gets.get(position, 0) + integer
            elif fields[0] == "update":
                position = int(fields[1]) - 1
                self._updates[position] = self._updates.get(position, 0) + integer
            else:
                interval = (int(fields[1]) - 1, int(fields[2]))
                self._ranges[interval] = self._ranges.get(interval, 0) + integer
        self._profile_total = (
            sum(self._gets.values())
            + sum(self._updates.values())
            + sum(self._ranges.values())
        )
        while self._profile_total > self._policy.max_profile_operations:
            self._decay_profile()
        self._lifetime_operations = self._profile_total
        self._operations_since_attempt = self._profile_total

    def close(self) -> None:
        if self._policy.profile_path is not None:
            self.save_profile()

    def __enter__(self) -> AdaptiveArray:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        del exc_type, exc_value, traceback
        self.close()
