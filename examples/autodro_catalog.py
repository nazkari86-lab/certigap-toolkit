from certigap import CertiGapAutoDRO, verify_autodro_selection_artifact


query_counts = [12_000, 4_500, 1_100, 300, 80, 20, 4, 1]

model = CertiGapAutoDRO().fit(
    query_counts,
    max_budget=5,
    confidence=0.95,
    memory_limit_bytes=2048,
)

artifact = model.export_selection_artifact()
verification = verify_autodro_selection_artifact(artifact)

print("selection:", model.summary())
print("hot-key comparison cost:", model.query_cost(1))
print("verified candidates:", verification["candidate_count"])
