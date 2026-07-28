#!/usr/bin/env python3
"""Build reproducible figures for the PF-ERI v2 model-route review.

These figures summarize a literature- and constraint-based design assessment.
They are not empirical model-performance results.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


MODELS = [
    "Ridge logistic",
    "Restricted GAM",
    "Bayesian logistic",
    "EBM",
    "Shallow CatBoost",
    "TabPFN",
    "GNN / stacking",
]

DIMENSIONS = [
    "Small-sample\nstability",
    "Probability\ncalibration",
    "Scientific\ninterpretability",
    "Auditability",
    "Nonlinear\ncapacity",
    "PF-ERI\nfit",
]

# Ordinal expert assessment based on the cited literature and the frozen PF-ERI
# design constraints. The values are intentionally not presented as measured
# predictive performance.
SCORES = np.array(
    [
        [5, 5, 5, 5, 2, 5],
        [4, 4, 5, 4, 4, 5],
        [4, 4, 5, 3, 3, 4],
        [3, 3, 4, 3, 5, 3],
        [3, 3, 2, 3, 5, 3],
        [4, 3, 1, 2, 5, 2],
        [1, 2, 1, 1, 5, 1],
    ],
    dtype=float,
)


def save_all(fig: plt.Figure, stem: Path) -> None:
    for suffix in (".png", ".svg", ".pdf"):
        kwargs = {"bbox_inches": "tight", "facecolor": "white"}
        if suffix == ".png":
            kwargs["dpi"] = 300
        fig.savefig(stem.with_suffix(suffix), **kwargs)


def build_model_matrix(output_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(10.8, 6.2), constrained_layout=True)
    image = ax.imshow(SCORES, cmap="viridis", vmin=1, vmax=5, aspect="auto")
    ax.set_xticks(range(len(DIMENSIONS)), DIMENSIONS, fontsize=9)
    ax.set_yticks(range(len(MODELS)), MODELS, fontsize=10)
    ax.tick_params(top=True, bottom=False, labeltop=True, labelbottom=False)
    for row in range(SCORES.shape[0]):
        for col in range(SCORES.shape[1]):
            color = "white" if SCORES[row, col] < 3.4 else "black"
            ax.text(col, row, f"{int(SCORES[row, col])}", ha="center", va="center", color=color, fontsize=10)
    cbar = fig.colorbar(image, ax=ax, pad=0.02, shrink=0.84)
    cbar.set_label("Constraint-based suitability (1 low – 5 high)", fontsize=9)
    ax.set_title("PF-ERI v2 model-route comparison\nLiterature- and design-based assessment, not observed performance", fontsize=13, weight="bold", pad=18)
    ax.text(
        0,
        -0.12,
        "Primary: ridge logistic  |  Prespecified nonlinear secondary: restricted GAM  |  Others: sensitivity or exploratory bounds",
        transform=ax.transAxes,
        fontsize=9,
        color="#243b53",
    )
    save_all(fig, output_dir / "figure1_model_route_matrix")
    plt.close(fig)


def add_box(ax: plt.Axes, x: float, y: float, w: float, h: float, title: str, detail: str, color: str) -> None:
    box = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.012,rounding_size=0.025",
        linewidth=1.4,
        edgecolor=color,
        facecolor="white",
    )
    ax.add_patch(box)
    ax.text(x + w / 2, y + h * 0.64, title, ha="center", va="center", fontsize=10.5, weight="bold", color=color)
    ax.text(x + w / 2, y + h * 0.29, detail, ha="center", va="center", fontsize=8.5, color="#334e68")


def add_arrow(ax: plt.Axes, start: tuple[float, float], end: tuple[float, float]) -> None:
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=13, linewidth=1.4, color="#486581"))


def build_math_chain(output_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(12.2, 5.8), constrained_layout=True)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    y, w, h = 0.56, 0.17, 0.23
    xs = [0.03, 0.235, 0.44, 0.645, 0.85]
    add_box(ax, xs[0], y, w, h, "Frozen evidence", "descriptor + quality\n+ local correspondence", "#1a5276")
    add_box(ax, xs[1], y, w, h, "Nested probability models", "active control vs full\nL2 logistic", "#1e8449")
    add_box(ax, xs[2], y, w, h, "Independent calibration", "intercept + slope\ncalibration partition", "#7d3c98")
    add_box(ax, xs[3], y, w, h, "Expected loss", "R_a(p)=pL(a,1)\n+(1-p)L(a,0)", "#b03a2e")
    add_box(ax, xs[4], y, 0.12, h, "Three actions", "admit\nreview\ndefer", "#935116")
    for left, right in zip(xs[:-1], xs[1:]):
        end_x = right
        if right == xs[-1]:
            end_x = right
        add_arrow(ax, (left + w, y + h / 2), (end_x - 0.008, y + h / 2))

    lower_y = 0.14
    add_box(ax, 0.10, lower_y, 0.23, 0.19, "Graph-aware development", "component/node-blocked OOF\npaired Brier loss", "#21618c")
    add_box(ax, 0.385, lower_y, 0.23, 0.19, "One-shot confirmation", "design-weighted paired ΔBrier\ndyadic uncertainty", "#21618c")
    add_box(ax, 0.67, lower_y, 0.23, 0.19, "Budget-constrained policy", "maximize review value\nunder expert-time budget", "#21618c")
    add_arrow(ax, (0.33, lower_y + 0.095), (0.377, lower_y + 0.095))
    add_arrow(ax, (0.615, lower_y + 0.095), (0.662, lower_y + 0.095))
    ax.set_title("PF-ERI v2 mathematical evidence-to-decision chain", fontsize=14, weight="bold", pad=14)
    ax.text(
        0.5,
        0.02,
        "Model complexity is only one link; valid probability, dependency-aware inference, and explicit costs complete the scientific claim.",
        ha="center",
        va="bottom",
        fontsize=9.5,
        color="#334e68",
    )
    save_all(fig, output_dir / "figure2_mathematical_decision_chain")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    build_model_matrix(args.output_dir)
    build_math_chain(args.output_dir)


if __name__ == "__main__":
    main()
