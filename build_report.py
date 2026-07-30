from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent
DOCS_DIR = ROOT / "docs"
RESULTS_DIR = ROOT / "results"
REPORT_DIR = ROOT / "report"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def between(text: str, start: str, end: str | None = None) -> str:
    start_index = text.index(start) + len(start)
    if end is None:
        return text[start_index:].strip()
    end_index = text.index(end, start_index)
    return text[start_index:end_index].strip()


def build_abstract(summary_text: str) -> str:
    global_summary = between(summary_text, "## Global Summary", "## By Distribution")
    lines = [line.strip("- ").strip() for line in global_summary.splitlines() if line.startswith("- ")]

    return "\n".join(
        [
            "# CertiGap Abstract",
            "",
            "CertiGap studies a static search problem under two constraints: only a limited number of threshold comparisons may be materialized in advance, and the predicted query distribution may be wrong.",
            "Instead of forcing a fully resolved search structure, CertiGap allows unresolved interval leaves and optimizes which parts of the order are worth materializing.",
            "",
            "The project contributes:",
            "",
            "1. an exact generalized frontier dynamic program for deterministic executable fallbacks;",
            "2. a scalable candidate-pruned C++ heuristic and an unbounded-gap result for one-step greedy;",
            "3. structural, entropy-bound, proof-trace, and rational-arithmetic verification layers;",
            "4. direct finite-support TV-DRO optimization with a complete small-instance search-space proof;",
            "5. scalable anytime TV-DRO search with replay-verified optimality intervals;",
            "6. omission-resistant manifests, online drift certificates, and reproducible synthetic, public-workload, temporal, shift, and C++ benchmarks.",
            "",
            "Current prototype evidence:",
            "",
            *[f"- {line}" for line in lines],
            "",
            "These results support the main claim that optimizing how much order to materialize is both algorithmically nontrivial and measurably better than simple greedy or balanced baselines on skewed workloads.",
        ]
    ) + "\n"


def build_report(
    theme_text: str,
    theorem_text: str,
    experiment_text: str,
    positioning_text: str,
    summary_text: str,
    generalized_text: str = "",
    lookup_text: str = "",
    autodro_text: str = "",
    dynamic_range_text: str = "",
    autoindex_text: str = "",
) -> str:
    return "\n".join(
        [
            "# CertiGap Report",
            "",
            "## Topic",
            "",
            between(theme_text, "## Final Topic", "## One-Sentence Contribution"),
            "",
            "## One-Sentence Contribution",
            "",
            between(theme_text, "## One-Sentence Contribution", "## Central Research Question"),
            "",
            "## Research Question",
            "",
            between(theme_text, "## Central Research Question", "## Main Claim To Build Toward"),
            "",
            "## Main Claim",
            "",
            between(theme_text, "## Main Claim To Build Toward", "## What Must Stay Out Of Scope"),
            "",
            "## Theorem Targets",
            "",
            theorem_text,
            "",
            "## Executable Fallback Generalization",
            "",
            generalized_text,
            "",
            "## Experimental Design",
            "",
            experiment_text,
            "",
            "## Current Results",
            "",
            summary_text,
            "",
            "## Matched-Budget Lookup Evidence",
            "",
            lookup_text,
            "",
            "## AutoDRO Under Distribution Shift",
            "",
            autodro_text,
            "",
            "## Dynamic CertiRange",
            "",
            dynamic_range_text,
            "",
            "## Certified AutoIndex",
            "",
            autoindex_text,
            "",
            "## Competition Positioning",
            "",
            positioning_text,
        ]
    ) + "\n"


def build_appendix(certificate_text: str, roadmap_text: str) -> str:
    return "\n".join(
        [
            "# CertiGap Appendix",
            "",
            "## Certificate Examples",
            "",
            certificate_text,
            "",
            "## Roadmap",
            "",
            roadmap_text,
        ]
    ) + "\n"


def build_poster_outline(summary_text: str) -> str:
    top_improvements = between(summary_text, "## Top Beam Improvements")
    return "\n".join(
        [
            "# CertiGap Poster Outline",
            "",
            "## Panel 1: Problem",
            "",
            "- Full search structures materialize too much order under a strict split budget.",
            "- Predictions can help, but they can also be wrong.",
            "",
            "## Panel 2: Idea",
            "",
            "- Build a partial search tree with interval leaves.",
            "- Optimize `(1 - eta) * average_cost + eta * max_cost`.",
            "- Return a solution with a checker and independently recomputed entropy bounds.",
            "",
            "## Panel 3: Algorithms",
            "",
            "- Exact frontier DP",
            "- Beam-search heuristic",
            "- Entropy + Lagrangian lower bounds",
            "",
            "## Panel 4: Results",
            "",
            summary_text,
            "",
            "## Panel 5: Best Beam Improvements",
            "",
            top_improvements,
        ]
    ) + "\n"


def main() -> None:
    REPORT_DIR.mkdir(exist_ok=True)

    theme_text = read_text(DOCS_DIR / "THEME.md")
    theorem_text = read_text(DOCS_DIR / "THEOREM_GOALS.md")
    experiment_text = read_text(DOCS_DIR / "EXPERIMENT_PLAN.md")
    positioning_text = read_text(DOCS_DIR / "RKNP_ISEF_POSITIONING.md")
    roadmap_text = read_text(DOCS_DIR / "ROADMAP.md")
    formal_results_text = read_text(DOCS_DIR / "FORMAL_RESULTS.md") if (DOCS_DIR / "FORMAL_RESULTS.md").exists() else ""
    summary_text = read_text(RESULTS_DIR / "summary.md")
    certificate_text = read_text(RESULTS_DIR / "certificate_examples.md")
    counterexample_text = read_text(RESULTS_DIR / "counterexamples.md") if (RESULTS_DIR / "counterexamples.md").exists() else ""
    technical_note_text = read_text(DOCS_DIR / "TECHNICAL_NOTE.md") if (DOCS_DIR / "TECHNICAL_NOTE.md").exists() else ""
    speed_quality_text = read_text(RESULTS_DIR / "speed_quality_summary.md") if (RESULTS_DIR / "speed_quality_summary.md").exists() else ""
    generalized_text = read_text(DOCS_DIR / "GENERALIZED_FALLBACK.md")
    lookup_text = read_text(RESULTS_DIR / "cpp_lookup_latency.md")
    autodro_text = "\n\n".join(
        read_text(path)
        for path in (
            RESULTS_DIR / "autodro_shift.md",
            RESULTS_DIR / "direct_tv_validation.md",
            RESULTS_DIR / "temporal_holdout.md",
            RESULTS_DIR / "uncertainty_validation.md",
            RESULTS_DIR / "online_adaptation.md",
            RESULTS_DIR / "anytime_validation.md",
        )
    )
    dynamic_range_text = "\n\n".join(
        read_text(path)
        for path in (
            DOCS_DIR / "DYNAMIC_RANGE.md",
            RESULTS_DIR / "range_optimizer_validation.md",
            RESULTS_DIR / "cpp_dynamic_range.md",
            RESULTS_DIR / "dynamic_range_benchmark.md",
        )
    )
    autoindex_text = "\n\n".join(
        read_text(path)
        for path in (
            DOCS_DIR / "AUTOINDEX.md",
            RESULTS_DIR / "autoindex_validation.md",
            DOCS_DIR / "SAFE_AUTOINDEX.md",
            RESULTS_DIR / "safe_autoindex_validation.md",
            DOCS_DIR / "SEQUENTIAL_SAFE_AUTOINDEX.md",
            RESULTS_DIR / "sequential_safe_validation.md",
            DOCS_DIR / "COMPILER_INTEGRATION.md",
            RESULTS_DIR / "compiler_integration_validation.md",
            DOCS_DIR / "ADAPTIVE_CPP.md",
            RESULTS_DIR / "adaptive_header_validation.md",
            DOCS_DIR / "SYNTHESIS.md",
            RESULTS_DIR / "synthesis_validation.md",
            DOCS_DIR / "HYBRID.md",
            RESULTS_DIR / "hybrid_validation.md",
            RESULTS_DIR / "synthesis_native_latency.md",
        )
    )

    (REPORT_DIR / "ABSTRACT.md").write_text(build_abstract(summary_text), encoding="utf-8")
    (REPORT_DIR / "REPORT.md").write_text(
        build_report(
            theme_text,
            theorem_text,
            experiment_text,
            positioning_text,
            summary_text
            + ("\n\n## Speed And Quality\n\n" + speed_quality_text if speed_quality_text else "")
            + ("\n\n## Counterexamples\n\n" + counterexample_text if counterexample_text else ""),
            generalized_text,
            lookup_text,
            autodro_text,
            dynamic_range_text,
            autoindex_text,
        ),
        encoding="utf-8",
    )
    anytime_theory_text = read_text(DOCS_DIR / "ANYTIME_TV.md")
    dynamic_range_theory_text = read_text(DOCS_DIR / "DYNAMIC_RANGE.md")
    (REPORT_DIR / "APPENDIX.md").write_text(
        build_appendix(
            certificate_text
            + ("\n\n" + speed_quality_text if speed_quality_text else "")
            + ("\n\n" + counterexample_text if counterexample_text else "")
            + ("\n\n" + technical_note_text if technical_note_text else "")
            + "\n\n"
            + anytime_theory_text
            + "\n\n"
            + dynamic_range_theory_text
            + "\n\n"
            + read_text(DOCS_DIR / "AUTOINDEX.md")
            + "\n\n"
            + read_text(DOCS_DIR / "SAFE_AUTOINDEX.md")
            + "\n\n"
            + read_text(DOCS_DIR / "SEQUENTIAL_SAFE_AUTOINDEX.md")
            + "\n\n"
            + read_text(DOCS_DIR / "COMPILER_INTEGRATION.md")
            + "\n\n"
            + read_text(DOCS_DIR / "ADAPTIVE_CPP.md")
            + "\n\n"
            + read_text(DOCS_DIR / "SYNTHESIS.md"),
            roadmap_text,
        ),
        encoding="utf-8",
    )
    if formal_results_text:
        (REPORT_DIR / "FORMAL_RESULTS.md").write_text(formal_results_text, encoding="utf-8")
    (REPORT_DIR / "POSTER_OUTLINE.md").write_text(build_poster_outline(summary_text), encoding="utf-8")

    print(f"Wrote {REPORT_DIR / 'ABSTRACT.md'}")
    print(f"Wrote {REPORT_DIR / 'REPORT.md'}")
    print(f"Wrote {REPORT_DIR / 'APPENDIX.md'}")
    if formal_results_text:
        print(f"Wrote {REPORT_DIR / 'FORMAL_RESULTS.md'}")
    print(f"Wrote {REPORT_DIR / 'POSTER_OUTLINE.md'}")


if __name__ == "__main__":
    main()
