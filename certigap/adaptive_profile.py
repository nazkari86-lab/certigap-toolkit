from __future__ import annotations

import math
from pathlib import Path


def parse_adaptive_profile_text(text: str) -> dict:
    lines = text.splitlines()
    if len(lines) < 4 or lines[0] != "CERTIGAP_PROFILE_V1":
        raise ValueError("invalid CertiGap profile header")
    size_fields = lines[1].split()
    aggregate_fields = lines[2].split()
    if len(size_fields) != 2 or size_fields[0] != "size":
        raise ValueError("profile size is missing")
    try:
        size = int(size_fields[1])
    except ValueError as exc:
        raise ValueError("profile size must be an integer") from exc
    if size <= 0 or size > 10_000_000:
        raise ValueError("profile size must lie in [1,10000000]")
    if (
        len(aggregate_fields) != 2
        or aggregate_fields[0] != "aggregate"
        or aggregate_fields[1] not in {"sum", "min", "max"}
    ):
        raise ValueError("profile aggregate is invalid")
    if lines[-1] != "end" or "end" in lines[3:-1]:
        raise ValueError("profile end marker is missing or misplaced")
    records = lines[3:-1]
    if len(records) > 1_000_000:
        raise ValueError("profile record limit exceeded")

    get_weights = [0.0] * size
    update_weights = [0.0] * size
    ranges: dict[tuple[int, int], float] = {}

    def weight(raw: str) -> float:
        try:
            value = float(raw)
        except ValueError as exc:
            raise ValueError("profile weight must be numeric") from exc
        if not math.isfinite(value) or value <= 0.0:
            raise ValueError("profile weight must be finite and positive")
        return value

    for record in records:
        fields = record.split()
        if not fields:
            raise ValueError("empty profile record")
        if fields[0] in {"get", "update"}:
            if len(fields) != 3:
                raise ValueError("invalid point profile record")
            try:
                key = int(fields[1])
            except ValueError as exc:
                raise ValueError("profile key must be an integer") from exc
            if key < 1 or key > size:
                raise ValueError("profile key is out of range")
            target = get_weights if fields[0] == "get" else update_weights
            target[key - 1] += weight(fields[2])
        elif fields[0] == "range":
            if len(fields) != 4:
                raise ValueError("invalid range profile record")
            try:
                left, right = int(fields[1]), int(fields[2])
            except ValueError as exc:
                raise ValueError("profile range must use integer keys") from exc
            if left < 1 or right < left or right > size:
                raise ValueError("profile range is out of bounds")
            key = (left, right)
            ranges[key] = ranges.get(key, 0.0) + weight(fields[3])
        else:
            raise ValueError("unknown profile record")

    total_get = sum(get_weights)
    total_update = sum(update_weights)
    total_range = sum(ranges.values())
    total = total_get + total_update + total_range
    if not math.isfinite(total):
        raise ValueError("profile weight overflow")
    heat = [get_weights[index] + update_weights[index] for index in range(size)]
    difference = [0.0] * (size + 1)
    for (left, right), value in ranges.items():
        per_position = value / (right - left + 1)
        difference[left - 1] += per_position
        difference[right] -= per_position
    running = 0.0
    for position in range(size):
        running += difference[position]
        heat[position] += running
    hottest = sorted(
        (
            {"position": position, "weight": value}
            for position, value in enumerate(heat)
            if value > 0.0
        ),
        key=lambda row: (-row["weight"], row["position"]),
    )[:5]
    return {
        "schema": "CERTIGAP_PROFILE_V1",
        "size": size,
        "aggregate": aggregate_fields[1],
        "total_operations": total,
        "operation_weights": {
            "get": total_get,
            "update": total_update,
            "range": total_range,
        },
        "distinct_range_records": len(ranges),
        "hottest_zero_based_positions": hottest,
        "claim_boundary": (
            "Profile weights describe observed operations; they do not prove "
            "latency improvement or statistical deployment safety."
        ),
    }


def parse_adaptive_profile(path: Path) -> dict:
    return parse_adaptive_profile_text(path.read_text(encoding="utf-8"))
