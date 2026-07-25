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
            "1. an exact frontier dynamic program for the budgeted robust partial-search model;",
            "2. a stronger beam-search heuristic for larger instances;",
            "3. a structural checker that recomputes the objective and an entropy lower bound;",
            "4. a reproducible synthetic benchmark suite.",
            "",
            "Current prototype evidence:",
            "",
            *[f"- {line}" for line in lines],
            "",
            "These results support the main claim that optimizing how much order to materialize is both algorithmically nontrivial and measurably better than simple greedy or balanced baselines on skewed workloads.",
        ]
    ) + "\n"


def build_report(theme_text: str, theorem_text: str, experiment_text: str, positioning_text: str, summary_text: str) -> str:
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
            "## Experimental Design",
            "",
            experiment_text,
            "",
            "## Current Results",
            "",
            summary_text,
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
        ),
        encoding="utf-8",
    )
    (REPORT_DIR / "APPENDIX.md").write_text(
        build_appendix(
            certificate_text
            + ("\n\n" + speed_quality_text if speed_quality_text else "")
            + ("\n\n" + counterexample_text if counterexample_text else "")
            + ("\n\n" + technical_note_text if technical_note_text else ""),
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
