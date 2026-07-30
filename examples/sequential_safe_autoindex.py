from certigap import (
    SequentialSafeSelectionPolicy,
    WorkloadTrace,
    compile_sequential_safe_autoindex,
)


def ranges(count: int) -> WorkloadTrace:
    trace = WorkloadTrace(8)
    for _ in range(count):
        trace.add_range(2, 7)
    return trace


index = compile_sequential_safe_autoindex(
    range(8),
    ranges(100),
    ranges(2_000),
    test_trace=ranges(100),
    policy=SequentialSafeSelectionPolicy(
        confidence_alpha=0.05,
        minimum_observations=100,
        horizon_operations=1_000_000,
    ),
)

print(index.summary())
print(index.range_query(2, 7))
print(index.export_certificate()["sha256"])
