from __future__ import annotations

import hashlib
import json
import math


class DeltaVerificationError(ValueError):
    pass


def _digest(value: object) -> str:
    try:
        raw = json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    except (TypeError, ValueError) as exc:
        raise DeltaVerificationError("artifact is not canonical JSON") from exc
    return hashlib.sha256(raw).hexdigest()


def _parse_rows(rows: object, label: str) -> dict[int, float]:
    if not isinstance(rows, list):
        raise DeltaVerificationError(f"{label} must be a list")
    values: dict[int, float] = {}
    previous: int | None = None
    for row in rows:
        if not isinstance(row, list) or len(row) != 2:
            raise DeltaVerificationError(f"{label} row is invalid")
        key, raw_value = row
        if not isinstance(key, int) or isinstance(key, bool):
            raise DeltaVerificationError(f"{label} key is invalid")
        value = float(raw_value)
        if not math.isfinite(value) or previous is not None and key <= previous:
            raise DeltaVerificationError(f"{label} is not canonical")
        values[key] = value
        previous = key
    return values


def _rows(values: dict[int, float]) -> list[list[int | float]]:
    return [[key, values[key]] for key in sorted(values)]


def verify_delta_certificate(artifact: dict) -> dict:
    fields = {
        "schema", "contract", "initial_entries", "initial_sha256", "events",
        "final_entries", "final_sha256", "summary", "claim_boundary", "sha256",
    }
    if not isinstance(artifact, dict) or set(artifact) != fields:
        raise DeltaVerificationError("artifact schema is invalid")
    unsigned = dict(artifact)
    supplied = unsigned.pop("sha256")
    if artifact["schema"] != "certigap-proof-carrying-delta-v1" or supplied != _digest(unsigned):
        raise DeltaVerificationError("artifact digest or version is invalid")
    contract = artifact["contract"]
    if not isinstance(contract, dict) or set(contract) != {
        "schema", "key_semantics", "range_semantics", "operations", "algebra",
        "rebuild_threshold", "rebuild_rule",
    }:
        raise DeltaVerificationError("contract schema is invalid")
    if (
        contract["schema"] != "certigap-delta-contract-v1"
        or contract["key_semantics"] != "unique_signed_integer_keys"
        or contract["range_semantics"] != "inclusive_key_interval"
        or contract["operations"] != ["get", "range", "insert", "update", "erase"]
        or contract["rebuild_rule"]
        != "after_mutation_when_distinct_delta_keys_reach_threshold"
    ):
        raise DeltaVerificationError("contract constants are invalid")
    algebra, threshold = contract["algebra"], contract["rebuild_threshold"]
    if algebra not in {"sum", "min", "max"} or not isinstance(threshold, int) or threshold < 1:
        raise DeltaVerificationError("contract parameters are invalid")
    initial = _parse_rows(artifact["initial_entries"], "initial_entries")
    if artifact["initial_sha256"] != _digest(_rows(initial)):
        raise DeltaVerificationError("initial digest mismatch")
    base, delta, rebuilds = dict(initial), {}, 0

    def current() -> dict[int, float]:
        result = dict(base)
        for key, value in delta.items():
            result.pop(key, None) if value is None else result.__setitem__(key, value)
        return result

    events = artifact["events"]
    if not isinstance(events, list):
        raise DeltaVerificationError("events must be a list")
    for sequence, event in enumerate(events):
        if not isinstance(event, dict) or event.get("sequence") != sequence:
            raise DeltaVerificationError("event sequence is invalid")
        operation, values = event.get("operation"), current()
        if operation in {"insert", "update"}:
            if set(event) != {"sequence", "operation", "key", "value"}:
                raise DeltaVerificationError("write event schema is invalid")
            key, value = event["key"], float(event["value"])
            if not isinstance(key, int) or isinstance(key, bool) or not math.isfinite(value):
                raise DeltaVerificationError("write value is invalid")
            if (operation == "insert") != (key not in values):
                raise DeltaVerificationError("write precondition failed")
            delta[key] = value
        elif operation == "erase":
            if set(event) != {"sequence", "operation", "key"} or event["key"] not in values:
                raise DeltaVerificationError("erase event is invalid")
            delta[event["key"]] = None
        elif operation == "get":
            if set(event) != {"sequence", "operation", "key", "result"} or event["key"] not in values:
                raise DeltaVerificationError("get event is invalid")
            if float(event["result"]) != values[event["key"]]:
                raise DeltaVerificationError("get replay mismatch")
        elif operation == "range":
            if set(event) != {"sequence", "operation", "left", "right", "result"} or event["left"] > event["right"]:
                raise DeltaVerificationError("range event is invalid")
            selected = [value for key, value in values.items() if event["left"] <= key <= event["right"]]
            expected = float(sum(selected)) if algebra == "sum" else (
                min(selected, default=math.inf) if algebra == "min"
                else max(selected, default=-math.inf)
            )
            expected_recorded: float | str = expected
            if math.isinf(expected):
                expected_recorded = (
                    "positive_infinity" if expected > 0 else "negative_infinity"
                )
            if event["result"] != expected_recorded:
                raise DeltaVerificationError("range replay mismatch")
        elif operation == "rebuild":
            if set(event) != {"sequence", "operation", "compacted_delta_keys", "entry_count", "state_sha256"}:
                raise DeltaVerificationError("rebuild event schema is invalid")
            if len(delta) < threshold or event["compacted_delta_keys"] != len(delta):
                raise DeltaVerificationError("rebuild rule mismatch")
            base = current()
            delta.clear()
            rebuilds += 1
            if event["entry_count"] != len(base) or event["state_sha256"] != _digest(_rows(base)):
                raise DeltaVerificationError("rebuild state mismatch")
        else:
            raise DeltaVerificationError("unknown operation")
        if operation in {"insert", "update", "erase"} and len(delta) >= threshold:
            if sequence + 1 >= len(events) or events[sequence + 1].get("operation") != "rebuild":
                raise DeltaVerificationError("mandatory rebuild is missing")
    final = _parse_rows(artifact["final_entries"], "final_entries")
    if final != current() or artifact["final_sha256"] != _digest(_rows(final)):
        raise DeltaVerificationError("final state mismatch")
    summary = {
        "event_count": len(events), "rebuild_count": rebuilds,
        "final_entry_count": len(final),
    }
    if artifact["summary"] != summary:
        raise DeltaVerificationError("summary mismatch")
    boundary = (
        "The certificate replays ordered-map semantics and every deterministic "
        "delta compaction. It does not certify wall-clock optimality, durability, "
        "or concurrent progress."
    )
    if artifact["claim_boundary"] != boundary:
        raise DeltaVerificationError("claim boundary is invalid")
    return {"verified": True, **summary, "sha256": supplied}
