from certigap import (
    SafeSelectionPolicy,
    WorkloadTrace,
    compile_safe_autoindex,
)


def range_trace(n: int, count: int, left: int, right: int) -> WorkloadTrace:
    trace = WorkloadTrace(n)
    for _ in range(count):
        trace.add_range(left, right)
    return trace


values = list(range(32))
index = compile_safe_autoindex(
    values,
    range_trace(32, 200, 3, 30),
    range_trace(32, 20_000, 3, 30),
    test_trace=range_trace(32, 1_000, 4, 29),
    policy=SafeSelectionPolicy(
        confidence_alpha=0.05,
        horizon_operations=1_000_000,
        migration_cost_units=500.0,
    ),
)

print(index.summary())
print(index.range_query(3, 30))
print(index.export_certificate()["sha256"])
