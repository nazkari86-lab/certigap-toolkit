from certigap import AutoIndexConstraints, WorkloadTrace, compile_autoindex


trace = WorkloadTrace(32)
for _ in range(100):
    trace.add_range(3, 30)

index = compile_autoindex(
    range(32),
    trace,
    constraints=AutoIndexConstraints(aggregate="sum", budget=4),
)

print(index.summary())
print(index.range_query(3, 30))
