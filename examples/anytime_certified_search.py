from certigap import (
    anytime_tv_branch_and_bound,
    make_distribution,
    verify_anytime_tv_certificate,
)


weights = make_distribution("zipf", 32)
result = anytime_tv_branch_and_bound(
    weights,
    budget=6,
    tv_radius=0.1,
    max_expansions=2_000,
    target_relative_gap=0.05,
)

print(
    {
        "upper_bound": result["score"],
        "lower_bound": result["global_lower_bound"],
        "relative_gap": result["relative_gap"],
        "exact": result["exact"],
        "stop_reason": result["stop_reason"],
    }
)
print(verify_anytime_tv_certificate(result["certificate"]))

