from certigap import (
    ProofCarryingSpec,
    WorkloadTrace,
    compile_proof_carrying_index,
    verify_dsl_certificate,
)


trace = WorkloadTrace(16)
for _ in range(20):
    trace.add_range(2, 15)
trace.add_update(4, 20.0)

model = compile_proof_carrying_index(
    range(16),
    trace,
    ProofCarryingSpec(
        operations=("range", "update"),
        algebra="sum",
        memory_limit_slots=64,
    ),
)

certificate = model.export_certificate()
print(verify_dsl_certificate(certificate))
print(model.range_query(2, 15))
