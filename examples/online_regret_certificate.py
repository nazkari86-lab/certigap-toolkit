from certigap import online_regret_certificate


reference = [0.70, 0.20, 0.08, 0.02]
current = [0.25, 0.20, 0.15, 0.40]

certificate = online_regret_certificate(
    reference,
    current,
    budget=2,
    optimization_gap=0.03,
    horizon_queries=50_000,
    rebuild_cost=20_000.0,
)
print(certificate)

