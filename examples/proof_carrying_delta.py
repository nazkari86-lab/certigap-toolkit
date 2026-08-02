from certigap import (
    DeltaSpec,
    compile_proof_carrying_delta_index,
    verify_delta_certificate,
)


index = compile_proof_carrying_delta_index(
    [(10, 1.0), (20, 2.0), (40, 4.0)],
    DeltaSpec(algebra="sum", rebuild_threshold=2),
)
index.insert(30, 3.0)
index.erase(20)  # This mutation deterministically triggers compaction.
print(index.range_query(10, 40))
print(verify_delta_certificate(index.export_certificate()))
