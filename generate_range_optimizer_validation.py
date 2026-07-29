from __future__ import annotations

import csv
import json
from pathlib import Path

from certigap import (
    CertiRangeWorkload,
    range_aware_beam_search,
    make_range_optimizer_artifact,
    score_range_workload,
)
from certigap.api import solve_with


ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "results" / "range_optimizer_validation.csv"
MD_PATH = ROOT / "results" / "range_optimizer_validation.md"
EXAMPLE_PATH = ROOT / "results" / "range_optimizer_example.json"


def workload_family(n: int, family: str) -> CertiRangeWorkload:
    workload = CertiRangeWorkload(n)
    if family == "point_hotspot":
        workload.add_point(1, 800).add_point(2, 150).add_point(n, 50)
    elif family == "clustered_ranges":
        workload.add_range(1, max(2, n // 3), 600)
        workload.add_range(n // 2, min(n, n // 2 + n // 4), 300)
        workload.add_range(max(1, n - n // 5), n, 100)
    elif family == "mixed":
        workload.add_point(1, 300).add_point(n, 100)
        workload.add_update(max(1, n // 2), 100)
        workload.add_range(1, max(2, n // 4), 300)
        workload.add_range(n // 3, min(n, 2 * n // 3), 200)
    else:
        raise ValueError(f"unknown family: {family}")
    return workload


def range_records(workload: CertiRangeWorkload) -> list[tuple[int, int, float]]:
    return [
        (left, right, count)
        for (left, right), count in sorted(workload.range_counts.items())
    ]


def exact_routing_space(n: int, budget: int) -> list[dict]:
    root = {"type": "leaf", "interval": [1, n]}
    seen = {json.dumps(root, sort_keys=True, separators=(",", ":")): root}
    frontier = [root]

    def leaves(tree: dict) -> list[tuple[int, int]]:
        if tree["type"] == "leaf":
            return [tuple(tree["interval"])]
        return leaves(tree["left"]) + leaves(tree["right"])

    def replace(
        tree: dict, target: tuple[int, int], threshold: int
    ) -> dict:
        left, right = tree["interval"]
        if tree["type"] == "leaf":
            if (left, right) != target:
                return tree
            return {
                "type": "split",
                "interval": [left, right],
                "threshold": threshold,
                "left": {"type": "leaf", "interval": [left, threshold]},
                "right": {
                    "type": "leaf",
                    "interval": [threshold + 1, right],
                },
            }
        return {
            "type": "split",
            "interval": [left, right],
            "threshold": tree["threshold"],
            "left": replace(tree["left"], target, threshold),
            "right": replace(tree["right"], target, threshold),
        }

    for _ in range(budget):
        next_frontier: dict[str, dict] = {}
        for tree in frontier:
            for left, right in leaves(tree):
                for threshold in range(left, right):
                    child = replace(tree, (left, right), threshold)
                    encoded = json.dumps(
                        child, sort_keys=True, separators=(",", ":")
                    )
                    seen[encoded] = child
                    next_frontier[encoded] = child
        frontier = list(next_frontier.values())
    return list(seen.values())


def evaluate(
    tree: dict, workload: CertiRangeWorkload, max_depth: int, eta: float
) -> dict:
    score = score_range_workload(
        tree,
        point_counts=workload.point_counts,
        update_counts=workload.update_counts,
        range_counts=range_records(workload),
        max_depth=max_depth,
        tail_weight=eta,
    )
    return {
        "objective": score.objective,
        "mean_node_visits": score.mean_node_visits,
        "max_point_depth": score.max_point_depth,
        "point_contribution": score.point_contribution,
        "range_contribution": score.range_contribution,
    }


def main() -> None:
    rows: list[dict[str, object]] = []
    exact_matches = 0
    for family in ("point_hotspot", "clustered_ranges", "mixed"):
        workload = workload_family(8, family)
        for budget in (1, 2):
            max_depth = 6
            eta = 0.10
            trees = exact_routing_space(8, budget)
            oracle = min(
                (evaluate(tree, workload, max_depth, eta) | {"tree": tree} for tree in trees),
                key=lambda item: item["objective"],
            )
            aware = range_aware_beam_search(
                point_counts=workload.point_counts,
                update_counts=workload.update_counts,
                range_counts=range_records(workload),
                budget=budget,
                max_depth=max_depth,
                tail_weight=eta,
                beam_width=10_000,
                candidate_limit=8,
            )
            gap = aware["objective"] - oracle["objective"]
            exact = abs(gap) <= 1e-12
            exact_matches += int(exact)
            rows.append(
                {
                    "phase": "exact_oracle",
                    "n": 8,
                    "family": family,
                    "budget": budget,
                    "method": "range_aware_beam_complete",
                    "objective": f"{aware['objective']:.12f}",
                    "mean_node_visits": f"{aware['mean_node_visits']:.12f}",
                    "max_point_depth": aware["max_point_depth"],
                    "oracle_objective": f"{oracle['objective']:.12f}",
                    "oracle_gap": f"{gap:.12f}",
                    "exact": exact,
                    "tree_space_size": len(trees),
                    "scope": "complete routing-tree enumeration up to budget",
                }
            )

    for n in (32, 64, 128):
        for family in ("point_hotspot", "clustered_ranges", "mixed"):
            workload = workload_family(n, family)
            weights = workload.routing_weights()
            max_depth = 2 * (n - 1).bit_length() + 1
            eta = 0.10
            balanced = {"type": "leaf", "interval": [1, n]}
            for budget in (0, 2, 4, 6):
                proxy = solve_with(weights, budget, eta, "beam")[
                    "serialized_tree"
                ]
                aware = range_aware_beam_search(
                    point_counts=workload.point_counts,
                    update_counts=workload.update_counts,
                    range_counts=range_records(workload),
                    budget=budget,
                    max_depth=max_depth,
                    tail_weight=eta,
                    beam_width=8,
                    candidate_limit=12,
                )
                for method, tree in (
                    ("balanced_completion", balanced),
                    ("point_endpoint_proxy", proxy),
                    ("range_aware_beam", aware["routing_tree"]),
                ):
                    score = evaluate(tree, workload, max_depth, eta)
                    rows.append(
                        {
                            "phase": "scaling",
                            "n": n,
                            "family": family,
                            "budget": budget,
                            "method": method,
                            "objective": f"{score['objective']:.12f}",
                            "mean_node_visits": f"{score['mean_node_visits']:.12f}",
                            "max_point_depth": score["max_point_depth"],
                            "oracle_objective": "",
                            "oracle_gap": "",
                            "exact": "",
                            "tree_space_size": "",
                            "scope": (
                                "bounded heuristic comparison on exact trace evaluator"
                            ),
                        }
                    )

    CSV_PATH.parent.mkdir(exist_ok=True)
    with CSV_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    scaling = [row for row in rows if row["phase"] == "scaling"]
    groups: dict[tuple[int, str, int], list[dict[str, object]]] = {}
    for row in scaling:
        groups.setdefault(
            (int(row["n"]), str(row["family"]), int(row["budget"])), []
        ).append(row)
    aware_wins = sum(
        float(
            next(
                row["objective"]
                for row in group
                if row["method"] == "range_aware_beam"
            )
        )
        <= min(float(row["objective"]) for row in group) + 1e-12
        for group in groups.values()
    )
    strict_proxy_wins = sum(
        float(
            next(
                row["objective"]
                for row in group
                if row["method"] == "range_aware_beam"
            )
        )
        < float(
            next(
                row["objective"]
                for row in group
                if row["method"] == "point_endpoint_proxy"
            )
        )
        - 1e-12
        for group in groups.values()
    )
    MD_PATH.write_text(
        "\n".join(
            [
                "# Range-aware optimizer validation",
                "",
                f"- Rows: `{len(rows)}`",
                f"- Complete small-space oracle matches: `{exact_matches}/6`",
                f"- Scaling groups where range-aware is tied for best or best: `{aware_wins}/{len(groups)}`",
                f"- Strict improvements over point/endpoint proxy: `{strict_proxy_wins}/{len(groups)}`",
                "- Every objective is recomputed by the exact mixed-trace evaluator.",
                "- Scaling rows are bounded beam results, not global optimality claims.",
                "",
                "The complete-tree-space checks validate the search implementation on n=8. "
                "The scaling matrix tests whether direct range-cost optimization improves over "
                "the former endpoint proxy without hiding cases where it ties or loses.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    example = workload_family(32, "clustered_ranges")
    example_result = range_aware_beam_search(
        point_counts=example.point_counts,
        update_counts=example.update_counts,
        range_counts=range_records(example),
        budget=4,
        max_depth=8,
    )
    EXAMPLE_PATH.write_text(
        json.dumps(
            make_range_optimizer_artifact(
                point_counts=example.point_counts,
                update_counts=example.update_counts,
                range_counts=range_records(example),
                max_depth=8,
                tail_weight=0.10,
                budget=4,
                result=example_result,
            ),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        f"Wrote {len(rows)} rows; exact matches={exact_matches}/6; "
        f"strict proxy improvements={strict_proxy_wins}/{len(groups)}"
    )


if __name__ == "__main__":
    main()
