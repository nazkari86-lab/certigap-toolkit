from certigap import (
    MartingaleSafeSelectionPolicy,
    WorkloadTrace,
    compile_martingale_safe_autoindex,
)


def ranges(count: int) -> WorkloadTrace:
    trace = WorkloadTrace(8)
    for _ in range(count):
        trace.add_range(2, 7)
    return trace


monitoring = ranges(1_000)
for operation in range(3_000):
    monitoring.add_update(1 + operation % 8, float(operation))

index = compile_martingale_safe_autoindex(
    range(8),
    ranges(100),
    monitoring,
    policy=MartingaleSafeSelectionPolicy(minimum_observations=50),
)

print(index.summary())
print(index.export_certificate()["sha256"])
