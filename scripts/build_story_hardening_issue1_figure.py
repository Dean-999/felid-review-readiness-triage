#!/usr/bin/env python3
"""Build Figure 1 for the story-hardening evidence-chain outline."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/story-hardening-issue1"
FIGURE_STEM = OUTPUT_DIR / "figure1_pair_level_evidence_admission_chain"
AUDIT_JSON = OUTPUT_DIR / "story_hardening_issue1_figure_audit.json"


COLORS = {
    "archive": "#E69F00",
    "descriptor": "#56B4E9",
    "queue": "#0072B2",
    "pferi": "#009E73",
    "review": "#CC79A7",
    "inference": "#D55E00",
    "line": "#222222",
    "muted": "#666666",
    "background": "#FFFFFF",
    "panel_fill": "#F7F7F7",
}


def add_box(
    ax,
    xy: tuple[float, float],
    width: float,
    height: float,
    text: str,
    facecolor: str,
    edgecolor: str = "#222222",
    text_color: str = "#111111",
    fontsize: int = 8,
    linewidth: float = 1.0,
) -> None:
    box = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle="round,pad=0.018,rounding_size=0.03",
        facecolor=facecolor,
        edgecolor=edgecolor,
        linewidth=linewidth,
    )
    ax.add_patch(box)
    ax.text(
        xy[0] + width / 2,
        xy[1] + height / 2,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        color=text_color,
        linespacing=1.12,
    )


def add_arrow(
    ax,
    start: tuple[float, float],
    end: tuple[float, float],
    color: str = COLORS["line"],
    mutation_scale: int = 10,
    linewidth: float = 1.1,
) -> None:
    arrow = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=mutation_scale,
        linewidth=linewidth,
        color=color,
        shrinkA=4,
        shrinkB=4,
    )
    ax.add_patch(arrow)


def add_panel_label(ax, label: str, x: float, y: float) -> None:
    ax.text(x, y, label, fontsize=11, fontweight="bold", ha="left", va="top")


def build_figure() -> plt.Figure:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8,
            "axes.linewidth": 0.8,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )

    fig = plt.figure(figsize=(7.1, 4.9), facecolor=COLORS["background"])
    gs = fig.add_gridspec(2, 1, height_ratios=[2.1, 1.35], hspace=0.23)
    ax_top = fig.add_subplot(gs[0])
    ax_bottom = fig.add_subplot(gs[1])

    for ax in [ax_top, ax_bottom]:
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")

    add_panel_label(ax_top, "A", 0.01, 0.98)
    ax_top.text(
        0.06,
        0.96,
        "Photographic Re-ID as an evidence chain",
        fontsize=10,
        fontweight="bold",
        ha="left",
        va="top",
    )
    ax_top.text(
        0.06,
        0.88,
        "Candidate retrieval is necessary, but admissible individual-level evidence requires a separate pair-level decision.",
        fontsize=7.6,
        color=COLORS["muted"],
        ha="left",
        va="top",
    )

    y = 0.53
    w = 0.128
    h = 0.22
    xs = [0.03, 0.195, 0.36, 0.525, 0.69, 0.855]
    labels = [
        "Image\narchive",
        "Strong descriptor\nretrieval",
        "Candidate\npair queue",
        "PF-ERI\npair-level\nevidence admission",
        "Expert\nreview",
        "Cautious\nevidence use",
    ]
    fills = [
        "#FFF2CC",
        "#D9EEF8",
        "#DCEBFA",
        "#DDF1E5",
        "#F3DCEB",
        "#F7E0D5",
    ]

    for x, label, fill in zip(xs, labels, fills):
        add_box(ax_top, (x, y), w, h, label, fill, fontsize=7.1)

    for i in range(len(xs) - 1):
        add_arrow(ax_top, (xs[i] + w, y + h / 2), (xs[i + 1], y + h / 2))

    ax_top.text(
        xs[1] + w / 2,
        0.40,
        "answers:\nwhich candidates look similar?",
        ha="center",
        va="top",
        fontsize=7,
        color=COLORS["muted"],
        linespacing=1.1,
    )
    ax_top.text(
        xs[3] + w / 2,
        0.40,
        "answers:\nwhich pairs are admissible evidence?",
        ha="center",
        va="top",
        fontsize=7,
        color=COLORS["muted"],
        linespacing=1.1,
    )

    ax_top.plot([xs[3] + w / 2, xs[3] + w / 2], [0.51, 0.41], color=COLORS["pferi"], linewidth=1.0)
    ax_top.plot([xs[1] + w / 2, xs[1] + w / 2], [0.51, 0.41], color=COLORS["descriptor"], linewidth=1.0)

    add_panel_label(ax_bottom, "B", 0.01, 0.96)
    ax_bottom.text(
        0.06,
        0.95,
        "PF-ERI separates similarity from admissibility",
        fontsize=10,
        fontweight="bold",
        ha="left",
        va="top",
    )

    add_box(
        ax_bottom,
        (0.06, 0.53),
        0.30,
        0.25,
        "Descriptor score\nvisual similarity context",
        "#D9EEF8",
        fontsize=7.8,
    )
    add_box(
        ax_bottom,
        (0.06, 0.16),
        0.30,
        0.25,
        "Pair-level evidence\nvisibility, comparability,\nconflict, weakest image",
        "#DDF1E5",
        fontsize=7.4,
    )
    add_arrow(ax_bottom, (0.37, 0.66), (0.49, 0.66), color=COLORS["descriptor"])
    add_arrow(ax_bottom, (0.37, 0.29), (0.49, 0.49), color=COLORS["pferi"])

    add_box(
        ax_bottom,
        (0.50, 0.41),
        0.18,
        0.30,
        "Evidence\nadmission\nscore",
        "#EEF7F1",
        edgecolor=COLORS["pferi"],
        fontsize=7.8,
        linewidth=1.3,
    )

    route_x = 0.76
    route_w = 0.18
    route_h = 0.12
    routes = [
        ("accept review-ready", 0.73, "#DDF1E5"),
        ("conflict review", 0.56, "#F7E0D5"),
        ("defer low-evidence", 0.39, "#F8EBC6"),
        ("non-comparable", 0.22, "#E6E6E6"),
    ]
    for route, y0, fill in routes:
        add_box(ax_bottom, (route_x, y0), route_w, route_h, route, fill, fontsize=7.0)
        add_arrow(ax_bottom, (0.68, 0.56), (route_x, y0 + route_h / 2), color=COLORS["line"], mutation_scale=8, linewidth=0.9)

    ax_bottom.text(
        0.50,
        0.20,
        "Admissibility is a route decision before evidence enters review or downstream use.",
        fontsize=7.4,
        color=COLORS["muted"],
        ha="left",
        va="top",
        wrap=True,
    )

    fig.suptitle(
        "Similarity is not admissibility",
        fontsize=12,
        fontweight="bold",
        y=0.995,
    )
    return fig


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig = build_figure()
    outputs = {}
    for suffix, kwargs in {
        ".svg": {},
        ".pdf": {},
        ".png": {"dpi": 300},
    }.items():
        path = FIGURE_STEM.with_suffix(suffix)
        fig.savefig(path, bbox_inches="tight", facecolor="white", **kwargs)
        outputs[suffix.lstrip(".")] = str(path.relative_to(PROJECT_ROOT))
    plt.close(fig)

    audit = {
        "status": "PASS",
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "figure_role": "Issue 1 manuscript evidence-chain Figure 1 concept",
        "claim_boundary": (
            "Conceptual evidence-chain figure only; does not report identity "
            "accuracy, Bobcat identity performance, or descriptor replacement."
        ),
        "outputs": outputs,
        "style_notes": {
            "format": "vector PDF/SVG plus 300 dpi PNG",
            "palette": "Okabe-Ito inspired colorblind-safe categorical palette",
            "journal_orientation": "double-column conceptual figure",
        },
    }
    AUDIT_JSON.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(f"PASS story hardening issue1 figure wrote {OUTPUT_DIR}")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
