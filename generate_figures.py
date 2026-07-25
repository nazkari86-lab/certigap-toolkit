from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "results"
FIGURES_DIR = ROOT / "figures"


def read_speed_quality_summary_rows() -> list[tuple[str, float]]:
    mapping = []
    summary = (RESULTS_DIR / "speed_quality_summary.md").read_text(encoding="utf-8")
    for line in summary.splitlines():
        if "mean gap vs exact" in line:
            label, value = line.split("`")[0], line.split("`")[1]
            mapping.append((label.strip("- ").strip(), float(value)))
        if "mean time:" in line:
            label, value = line.split("`")[0], line.split("`")[1].split()[0]
            mapping.append((label.strip("- ").strip(), float(value)))
    return mapping


def bar_svg(title: str, rows: list[tuple[str, float]], out_path: Path) -> None:
    width = 900
    bar_height = 28
    gap = 12
    left_pad = 330
    top_pad = 50
    max_val = max(value for _, value in rows) if rows else 1.0
    height = top_pad + len(rows) * (bar_height + gap) + 40

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        '<style>text{font-family:Menlo,monospace;font-size:14px;} .title{font-size:20px;font-weight:bold;} .bar{fill:#1f77b4;} .label{fill:#111;} .value{fill:#333;}</style>',
        f'<text class="title" x="20" y="30">{title}</text>',
    ]
    for idx, (label, value) in enumerate(rows):
        y = top_pad + idx * (bar_height + gap)
        bar_w = 0 if max_val == 0 else (width - left_pad - 80) * (value / max_val)
        parts.append(f'<text class="label" x="20" y="{y + 18}">{label}</text>')
        parts.append(f'<rect class="bar" x="{left_pad}" y="{y}" width="{bar_w:.2f}" height="{bar_height}" rx="4"/>')
        parts.append(f'<text class="value" x="{left_pad + bar_w + 8:.2f}" y="{y + 18}">{value:.6f}</text>')
    parts.append("</svg>")
    out_path.write_text("\n".join(parts), encoding="utf-8")


def main() -> None:
    FIGURES_DIR.mkdir(exist_ok=True)
    rows = read_speed_quality_summary_rows()
    gap_rows = [row for row in rows if "gap" in row[0]]
    time_rows = [row for row in rows if "time" in row[0]]
    bar_svg("CertiGap Mean Gaps", gap_rows, FIGURES_DIR / "mean_gaps.svg")
    bar_svg("CertiGap Mean Times (ms)", time_rows, FIGURES_DIR / "mean_times.svg")
    print(f"Wrote {FIGURES_DIR / 'mean_gaps.svg'}")
    print(f"Wrote {FIGURES_DIR / 'mean_times.svg'}")


if __name__ == "__main__":
    main()
