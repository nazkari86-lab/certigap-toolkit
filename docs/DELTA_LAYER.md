# Proof-Carrying Delta Layer

The delta layer extends CertiGap's fixed-size work with an ordered dynamic map.
It uses an immutable sorted base and a bounded overlay containing inserted,
updated, and erased keys. When the number of distinct overlay keys reaches the
declared threshold, compaction is mandatory and deterministic.

```python
from certigap import DeltaSpec, compile_proof_carrying_delta_index

index = compile_proof_carrying_delta_index(
    [(10, 1.0), (20, 2.0)],
    DeltaSpec(algebra="sum", rebuild_threshold=64),
)
index.insert(15, 3.0)
index.erase(20)
print(index.range_query(10, 20))
certificate = index.export_certificate()
```

The independent verifier reconstructs the initial map, replays every read and
mutation, enforces mutation preconditions, checks every mandatory rebuild, and
matches the final state and summary hashes. Rehashing a modified event does not
bypass semantic replay.

This is a correctness and lifecycle certificate, not a performance theorem.
The current Python runtime uses full logical-map materialization for reads and
is therefore a reference implementation. Native indexed delta reads,
durability, and concurrent writers remain future systems work.
