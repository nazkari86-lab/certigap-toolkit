from certigap import (
    CertiRangeWorkload,
    verify_dynamic_range_certificate,
)


workload = CertiRangeWorkload(16)
workload.add_point(1, 1000)
workload.add_range(1, 6, 500)
workload.add_update(2, 100)

index = workload.compile(
    values=list(range(1, 17)),
    budget=4,
    eta=0.10,
    aggregate="sum",
    max_depth=8,
    routing="range_aware",
)

before = index.snapshot()
index.point_update(2, 200)

print("old snapshot sum:", before.range_query(1, 6))
print("current sum:", index.range_query(1, 6))
print("summary:", index.summary())
print("certificate:", verify_dynamic_range_certificate(index.export_certificate()))

