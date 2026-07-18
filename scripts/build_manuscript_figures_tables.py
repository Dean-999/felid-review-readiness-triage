#!/usr/bin/env python3
"""Build manuscript Figures 2-4 and Tables 1-3 for the PF-ERI paper draft.

The script is intentionally conservative: it visualizes existing audited
story-hardening outputs and preserves the claim boundary that the endpoint is
CzechLynx human reviewability / evidential admissibility, not identity accuracy
or retrieval mAP.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "archive/pferi_v1/outputs/manuscript/2026-07-10_pferi_figures_tables"

ISSUE3_MODEL = PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/story-hardening-issue3/issue3_core_incremental_model_comparison.csv"
ISSUE4_QUALITY = PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/story-hardening-issue4/issue4_quality_matched_sensitivity.csv"
ISSUE4_HIGH_QUALITY = PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/story-hardening-issue4/issue4_high_quality_subset.csv"
ISSUE4_HIGH_SIMILARITY = PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/story-hardening-issue4/issue4_high_similarity_subset.csv"
ISSUE4_RANK_SIMILARITY = PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/story-hardening-issue4/issue4_rank_similarity_stratified_sensitivity.csv"
ISSUE5_FIXED_BUDGET = PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/story-hardening-issue5/issue5_fixed_budget_review_utility.csv"
ISSUE5_POLICY_DELTA = PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/story-hardening-issue5/issue5_fixed_budget_policy_delta.csv"
ISSUE6_HYGIENE = PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/story-hardening-issue6/issue6_pre_inference_evidence_hygiene_summary.csv"
BOBCAT_TRANSFER = PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/bobcat-wild-urban-transfer-stress/bobcat_transfer_stress_summary.csv"
BLIND_RELIABILITY_1 = PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/blind-reliability-packet/agreement-analysis/blind_reliability_agreement_summary.csv"
BLIND_RELIABILITY_2 = PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/blind-reliability-packet/agreement-analysis-reviewer2/blind_reliability_agreement_summary.csv"


OKABE = {
    "orange": "#E69F00",
    "sky": "#56B4E9",
    "green": "#009E73",
    "yellow": "#F0E442",
    "blue": "#0072B2",
    "vermillion": "#D55E00",
    "purple": "#CC79A7",
    "black": "#000000",
    "gray": "#666666",
    "light_gray": "#D9D9D9",
}

MODEL_LABELS = {
    "descriptor_only": "Descriptor only",
    "quality_only": "Quality only",
    "pf_eri_evidence_only": "PF-ERI evidence only",
    "descriptor_plus_quality": "Descriptor + quality",
    "descriptor_plus_pf_eri": "Descriptor + PF-ERI",
    "descriptor_plus_quality_plus_pf_eri": "Descriptor + quality + PF-ERI",
}

SCOPE_LABELS = {
    "pooled": "Pooled",
    "megadescriptor_l_384": "MegaDescriptor",
    "dinov2_vitl14": "DINOv2",
}


def require_columns(df: pd.DataFrame, columns: list[str], source: Path) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"{source.relative_to(PROJECT_ROOT)} missing required columns: {missing}")


def configure_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "font.size": 8,
            "axes.labelsize": 8,
            "axes.titlesize": 9,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "legend.fontsize": 7,
            "axes.linewidth": 0.8,
            "xtick.major.width": 0.7,
            "ytick.major.width": 0.7,
            "figure.dpi": 150,
            "savefig.dpi": 300,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
        }
    )


def save_figure(fig: mpl.figure.Figure, stem: str) -> list[str]:
    paths = []
    for suffix in ("svg", "pdf", "png"):
        path = OUT_DIR / f"{stem}.{suffix}"
        fig.savefig(path, bbox_inches="tight", facecolor="white")
        paths.append(str(path.relative_to(PROJECT_ROOT)))
    plt.close(fig)
    return paths


def despine(ax: mpl.axes.Axes) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(direction="out", length=3)


def panel_label(ax: mpl.axes.Axes, label: str) -> None:
    ax.text(-0.12, 1.06, label, transform=ax.transAxes, fontsize=10, fontweight="bold", va="top")


def pct(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return ""
    return f"{100 * float(value):.1f}%"


def num(value: float | int | None, digits: int = 3) -> str:
    if value is None or pd.isna(value):
        return ""
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    return f"{float(value):.{digits}f}"


def ci_metric(row: pd.Series, metric: str) -> str:
    return f"{row[metric]:.3f} [{row[f'{metric}_ci_lower']:.3f}, {row[f'{metric}_ci_upper']:.3f}]"


def markdown_table(df: pd.DataFrame) -> str:
    headers = list(df.columns)
    rows = []
    rows.append("| " + " | ".join(headers) + " |")
    rows.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for _, row in df.iterrows():
        cells = [str(row[col]).replace("\n", " ") for col in headers]
        rows.append("| " + " | ".join(cells) + " |")
    return "\n".join(rows) + "\n"


def write_table(df: pd.DataFrame, stem: str) -> list[str]:
    csv_path = OUT_DIR / f"{stem}.csv"
    md_path = OUT_DIR / f"{stem}.md"
    df.to_csv(csv_path, index=False)
    md_path.write_text(markdown_table(df), encoding="utf-8")
    return [str(csv_path.relative_to(PROJECT_ROOT)), str(md_path.relative_to(PROJECT_ROOT))]


def build_figure2(model_df: pd.DataFrame) -> list[str]:
    required = [
        "scope",
        "model_family",
        "pair_count",
        "auroc",
        "auroc_ci_lower",
        "auroc_ci_upper",
        "auprc",
        "auprc_ci_lower",
        "auprc_ci_upper",
        "brier_score",
        "ece_5bin",
        "delta_auroc_vs_descriptor_plus_quality",
        "delta_auprc_vs_descriptor_plus_quality",
    ]
    require_columns(model_df, required, ISSUE3_MODEL)

    pooled = model_df[model_df["scope"].eq("pooled")].copy()
    order = list(MODEL_LABELS.keys())
    pooled["model_family"] = pd.Categorical(pooled["model_family"], categories=order, ordered=True)
    pooled = pooled.sort_values("model_family")

    fig = plt.figure(figsize=(7.2, 6.0), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, height_ratios=[1.2, 1.0])
    ax_a = fig.add_subplot(gs[0, :])
    ax_b = fig.add_subplot(gs[1, 0])
    ax_c = fig.add_subplot(gs[1, 1])

    x = np.arange(len(pooled))
    width = 0.34
    for offset, metric, color, marker, label in [
        (-width / 2, "auroc", OKABE["blue"], "o", "AUROC"),
        (width / 2, "auprc", OKABE["green"], "s", "AUPRC"),
    ]:
        y = pooled[metric].to_numpy()
        yerr = np.vstack(
            [
                y - pooled[f"{metric}_ci_lower"].to_numpy(),
                pooled[f"{metric}_ci_upper"].to_numpy() - y,
            ]
        )
        ax_a.errorbar(
            x + offset,
            y,
            yerr=yerr,
            fmt=marker,
            markersize=4,
            capsize=2,
            color=color,
            label=f"{label} with 95% bootstrap CI",
            linewidth=1.2,
        )
    ax_a.set_xticks(x)
    ax_a.set_xticklabels([MODEL_LABELS[m] for m in pooled["model_family"]], rotation=25, ha="right")
    ax_a.set_ylim(0.5, 0.96)
    ax_a.set_ylabel("Reviewability discrimination")
    ax_a.set_title("Pooled reviewed CzechLynx pairs, n=400")
    ax_a.legend(frameon=False, loc="lower right")
    ax_a.grid(axis="y", alpha=0.22, linewidth=0.6)
    despine(ax_a)
    panel_label(ax_a, "A")

    full = model_df[model_df["model_family"].eq("descriptor_plus_quality_plus_pf_eri")].copy()
    full["scope"] = pd.Categorical(full["scope"], categories=["pooled", "megadescriptor_l_384", "dinov2_vitl14"], ordered=True)
    full = full.sort_values("scope")
    x2 = np.arange(len(full))
    ax_b.axhline(0, color=OKABE["black"], linewidth=0.8)
    ax_b.bar(
        x2 - 0.18,
        full["delta_auroc_vs_descriptor_plus_quality"],
        width=0.34,
        color=OKABE["sky"],
        edgecolor=OKABE["black"],
        linewidth=0.4,
        label="Delta AUROC",
    )
    ax_b.bar(
        x2 + 0.18,
        full["delta_auprc_vs_descriptor_plus_quality"],
        width=0.34,
        color=OKABE["orange"],
        edgecolor=OKABE["black"],
        linewidth=0.4,
        hatch="//",
        label="Delta AUPRC",
    )
    ax_b.set_xticks(x2)
    ax_b.set_xticklabels([SCOPE_LABELS[str(s)] for s in full["scope"]], rotation=20, ha="right")
    ax_b.set_ylabel("Delta vs descriptor + quality")
    ax_b.set_title("Strict active-control increment")
    ax_b.set_ylim(-0.03, 0.03)
    ax_b.legend(frameon=False, loc="upper right")
    ax_b.grid(axis="y", alpha=0.22, linewidth=0.6)
    despine(ax_b)
    panel_label(ax_b, "B")

    selected = pooled[pooled["model_family"].isin(["descriptor_only", "quality_only", "pf_eri_evidence_only", "descriptor_plus_quality_plus_pf_eri"])].copy()
    x3 = np.arange(len(selected))
    ax_c.bar(
        x3 - 0.18,
        selected["brier_score"],
        width=0.34,
        color=OKABE["purple"],
        edgecolor=OKABE["black"],
        linewidth=0.4,
        label="Brier score",
    )
    ax_c.bar(
        x3 + 0.18,
        selected["ece_5bin"],
        width=0.34,
        color=OKABE["light_gray"],
        edgecolor=OKABE["black"],
        linewidth=0.4,
        hatch="..",
        label="ECE, 5 bins",
    )
    ax_c.set_xticks(x3)
    ax_c.set_xticklabels([MODEL_LABELS[m] for m in selected["model_family"]], rotation=25, ha="right")
    ax_c.set_ylabel("Calibration error, lower is better")
    ax_c.set_title("Pooled calibration diagnostics")
    ax_c.set_ylim(0, 0.24)
    ax_c.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.18), ncol=2)
    ax_c.grid(axis="y", alpha=0.22, linewidth=0.6)
    despine(ax_c)
    panel_label(ax_c, "C")

    fig.suptitle("Figure 2. Reviewability model comparison, not identity accuracy", fontsize=10, fontweight="bold")
    return save_figure(fig, "figure2_model_comparison")


def build_figure3(
    quality_df: pd.DataFrame,
    high_quality_df: pd.DataFrame,
    high_similarity_df: pd.DataFrame,
    rank_df: pd.DataFrame,
) -> list[str]:
    contrast_col = "high_minus_low_review_ready_rate"
    for source, df in [
        (ISSUE4_QUALITY, quality_df),
        (ISSUE4_HIGH_QUALITY, high_quality_df),
        (ISSUE4_HIGH_SIMILARITY, high_similarity_df),
        (ISSUE4_RANK_SIMILARITY, rank_df),
    ]:
        require_columns(df, ["scope", "stratum_label", "row_count", contrast_col, "estimability_status"], source)

    fig = plt.figure(figsize=(7.2, 6.2), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.15])
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[1, :])

    pooled_quality = quality_df[quality_df["scope"].eq("pooled")].copy()
    pooled_quality["quartile"] = pooled_quality["stratum_label"].str.replace("quality_quartile_", "Q", regex=False)
    x = np.arange(len(pooled_quality))
    colors = [OKABE["green"] if value >= 0 else OKABE["vermillion"] for value in pooled_quality[contrast_col]]
    ax_a.axhline(0, color=OKABE["black"], linewidth=0.8)
    ax_a.bar(x, pooled_quality[contrast_col], color=colors, edgecolor=OKABE["black"], linewidth=0.4)
    ax_a.set_xticks(x)
    ax_a.set_xticklabels(pooled_quality["quartile"])
    ax_a.set_ylabel("High minus low PF-ERI\nreview-ready rate")
    ax_a.set_title("Pooled quality-matched strata")
    ax_a.set_ylim(-0.2, 0.34)
    ax_a.grid(axis="y", alpha=0.22, linewidth=0.6)
    despine(ax_a)
    panel_label(ax_a, "A")

    subset = pd.concat(
        [
            high_quality_df.assign(subset="High quality"),
            high_similarity_df.assign(subset="High similarity"),
        ],
        ignore_index=True,
    )
    subset["scope"] = pd.Categorical(subset["scope"], categories=["pooled", "megadescriptor_l_384", "dinov2_vitl14"], ordered=True)
    subset = subset.sort_values(["scope", "subset"])
    scopes = ["pooled", "megadescriptor_l_384", "dinov2_vitl14"]
    x2 = np.arange(len(scopes))
    for offset, subset_name, color, hatch in [
        (-0.18, "High quality", OKABE["sky"], ""),
        (0.18, "High similarity", OKABE["orange"], "//"),
    ]:
        vals = []
        for scope in scopes:
            row = subset[(subset["scope"].astype(str).eq(scope)) & (subset["subset"].eq(subset_name))]
            vals.append(float(row[contrast_col].iloc[0]))
        ax_b.bar(
            x2 + offset,
            vals,
            width=0.34,
            color=color,
            edgecolor=OKABE["black"],
            linewidth=0.4,
            hatch=hatch,
            label=subset_name,
        )
    ax_b.axhline(0, color=OKABE["black"], linewidth=0.8)
    ax_b.set_xticks(x2)
    ax_b.set_xticklabels([SCOPE_LABELS[s] for s in scopes], rotation=20, ha="right")
    ax_b.set_ylabel("High minus low PF-ERI\nreview-ready rate")
    ax_b.set_title("Subset stress tests")
    ax_b.set_ylim(-0.1, 0.38)
    ax_b.legend(frameon=False, loc="upper left")
    ax_b.grid(axis="y", alpha=0.22, linewidth=0.6)
    despine(ax_b)
    panel_label(ax_b, "B")

    pooled_rank = rank_df[(rank_df["scope"].eq("pooled")) & (rank_df["estimability_status"].eq("estimable"))].copy()
    pooled_rank = pooled_rank.sort_values(["rank_bin", "similarity_bin"])
    labels = [label.replace("/", "\n") for label in pooled_rank["stratum_label"]]
    x3 = np.arange(len(pooled_rank))
    marker_colors = [OKABE["blue"] if "high" in str(sim) else OKABE["purple"] for sim in pooled_rank["similarity_bin"]]
    ax_c.axhline(0, color=OKABE["black"], linewidth=0.8)
    ax_c.scatter(x3, pooled_rank[contrast_col], s=36, color=marker_colors, edgecolor=OKABE["black"], linewidth=0.4, zorder=3)
    ax_c.vlines(x3, 0, pooled_rank[contrast_col], color=OKABE["gray"], linewidth=0.8, alpha=0.7)
    ax_c.set_xticks(x3)
    ax_c.set_xticklabels(labels, rotation=35, ha="right")
    ax_c.set_ylabel("High minus low PF-ERI\nreview-ready rate")
    ax_c.set_title(f"Pooled rank/similarity strata, estimable strata={len(pooled_rank)}")
    ax_c.set_ylim(-0.05, max(0.65, float(pooled_rank[contrast_col].max()) + 0.08))
    ax_c.grid(axis="y", alpha=0.22, linewidth=0.6)
    despine(ax_c)
    panel_label(ax_c, "C")

    fig.suptitle("Figure 3. Quality and descriptor-similarity sensitivity", fontsize=10, fontweight="bold")
    return save_figure(fig, "figure3_quality_similarity_sensitivity")


def build_figure4(fixed_budget_df: pd.DataFrame, hygiene_df: pd.DataFrame) -> list[str]:
    require_columns(
        fixed_budget_df,
        [
            "scope",
            "strategy",
            "budget",
            "not_ready_or_uncertain_rate",
            "review_ready_rate",
            "same_id_retention",
        ],
        ISSUE5_FIXED_BUDGET,
    )
    require_columns(
        hygiene_df,
        [
            "scope",
            "simulation_decision",
            "pair_count",
            "review_ready_rate",
            "not_ready_or_uncertain_rate",
        ],
        ISSUE6_HYGIENE,
    )

    pooled = fixed_budget_df[fixed_budget_df["scope"].eq("pooled")].copy()
    pooled = pooled.sort_values(["strategy", "budget"])
    fig = plt.figure(figsize=(7.2, 5.4), constrained_layout=True)
    gs = fig.add_gridspec(2, 2)
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[1, :])

    style = {
        "pferi_priority": (OKABE["blue"], "o", "-", "PF-ERI priority"),
        "descriptor_priority": (OKABE["orange"], "s", "--", "Descriptor priority"),
    }
    for strategy, (color, marker, linestyle, label) in style.items():
        rows = pooled[pooled["strategy"].eq(strategy)]
        ax_a.plot(
            rows["budget"],
            rows["not_ready_or_uncertain_rate"],
            marker=marker,
            linestyle=linestyle,
            color=color,
            linewidth=1.4,
            markersize=4,
            label=label,
        )
    ax_a.set_xlabel("Review budget (pairs)")
    ax_a.set_ylabel("Not-ready or uncertain burden")
    ax_a.set_title("Primary review burden endpoint")
    ax_a.set_ylim(0, 0.36)
    ax_a.legend(frameon=False, loc="upper left")
    ax_a.grid(axis="y", alpha=0.22, linewidth=0.6)
    despine(ax_a)
    panel_label(ax_a, "A")

    for strategy, (color, marker, linestyle, label) in style.items():
        rows = pooled[pooled["strategy"].eq(strategy)]
        ax_b.plot(
            rows["budget"],
            rows["same_id_retention"],
            marker=marker,
            linestyle=linestyle,
            color=color,
            linewidth=1.4,
            markersize=4,
            label=label,
        )
    ax_b.set_xlabel("Review budget (pairs)")
    ax_b.set_ylabel("Same-ID candidate retention")
    ax_b.set_title("Secondary known-ID audit")
    ax_b.set_ylim(0, 1.05)
    ax_b.grid(axis="y", alpha=0.22, linewidth=0.6)
    despine(ax_b)
    panel_label(ax_b, "B")

    pooled_hygiene = hygiene_df[hygiene_df["scope"].eq("pooled")].copy()
    pooled_hygiene["decision_label"] = pooled_hygiene["simulation_decision"].map(
        {
            "admitted_pre_inference": "Admitted\npre-inference",
            "deferred_pre_inference": "Deferred\npre-inference",
        }
    )
    x = np.arange(len(pooled_hygiene))
    ready = pooled_hygiene["review_ready_rate"].to_numpy()
    not_ready = pooled_hygiene["not_ready_or_uncertain_rate"].to_numpy()
    ax_c.bar(x, ready, color=OKABE["green"], edgecolor=OKABE["black"], linewidth=0.4, label="Review-ready")
    ax_c.bar(
        x,
        not_ready,
        bottom=ready,
        color=OKABE["vermillion"],
        edgecolor=OKABE["black"],
        linewidth=0.4,
        hatch="//",
        label="Not-ready or uncertain",
    )
    for idx, row in pooled_hygiene.iterrows():
        pos = list(pooled_hygiene.index).index(idx)
        ax_c.text(pos, 1.03, f"n={int(row['pair_count'])}", ha="center", va="bottom", fontsize=7)
    ax_c.set_xticks(x)
    ax_c.set_xticklabels(pooled_hygiene["decision_label"])
    ax_c.set_ylabel("Pair fraction within route")
    ax_c.set_title("Pre-inference evidence hygiene simulation")
    ax_c.set_ylim(0, 1.15)
    ax_c.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.18), ncol=2)
    ax_c.grid(axis="y", alpha=0.22, linewidth=0.6)
    despine(ax_c)
    panel_label(ax_c, "C")

    fig.suptitle("Figure 4. Selective evidence routing under finite review budget", fontsize=10, fontweight="bold")
    return save_figure(fig, "figure4_review_budget_utility")


def build_table1(model_df: pd.DataFrame) -> pd.DataFrame:
    pooled = model_df[(model_df["scope"].eq("pooled")) & (model_df["model_family"].eq("descriptor_only"))].iloc[0]
    mega = model_df[(model_df["scope"].eq("megadescriptor_l_384")) & (model_df["model_family"].eq("descriptor_only"))].iloc[0]
    dino = model_df[(model_df["scope"].eq("dinov2_vitl14")) & (model_df["model_family"].eq("descriptor_only"))].iloc[0]

    reliability_rows = []
    for label, path in [("Blind reliability packet 1", BLIND_RELIABILITY_1), ("External blind reliability packet", BLIND_RELIABILITY_2)]:
        if path.exists():
            rel = pd.read_csv(path)
            overall = rel[rel["scope"].eq("overall")].iloc[0]
            reliability_rows.append(
                {
                    "validation component": label,
                    "scope or count": f"{int(overall['pair_count'])} pairs",
                    "identity label status": "Not used as model identity prediction",
                    "primary endpoint": f"Binary kappa {overall['binary_cohen_kappa']:.3f}; agreement {overall['binary_percent_agreement']:.3f}",
                    "allowed manuscript claim": "Human reviewability construct has blind reliability support",
                    "blocked claim": "Reviewer labels do not assign automated animal identity",
                }
            )

    bobcat_scope = "Unlabeled transfer-stress"
    if BOBCAT_TRANSFER.exists():
        bobcat = pd.read_csv(BOBCAT_TRANSFER)
        bobcat_scope = f"{int(bobcat['pair_count'].sum())} transfer-stress candidate pairs across {len(bobcat)} pair scopes"

    rows = [
        {
            "validation component": "CzechLynx reviewed candidate-pair validation",
            "scope or count": f"{int(pooled['pair_count'])} pairs; {int(pooled['positive_review_ready_count'])} review-ready; {int(pooled['negative_not_ready_or_uncertain_count'])} not-ready/uncertain",
            "identity label status": "Known-ID labels available for audit",
            "primary endpoint": "Human reviewability / evidential admissibility",
            "allowed manuscript claim": "PF-ERI is evaluated as a post-retrieval pair-level evidence admission layer",
            "blocked claim": "No automatic individual identification, mAP, MRR, or top-k identity improvement claim",
        },
        {
            "validation component": "MegaDescriptor upstream candidate queue",
            "scope or count": f"{int(mega['pair_count'])} reviewed pairs; {int(mega['positive_review_ready_count'])} review-ready; {int(mega['negative_not_ready_or_uncertain_count'])} not-ready/uncertain",
            "identity label status": "Known-ID labels available for CzechLynx audit",
            "primary endpoint": "Reviewability after strong descriptor retrieval",
            "allowed manuscript claim": "Strong descriptor used as upstream source and active control",
            "blocked claim": "PF-ERI is not a replacement descriptor",
        },
        {
            "validation component": "DINOv2 upstream candidate queue",
            "scope or count": f"{int(dino['pair_count'])} reviewed pairs; {int(dino['positive_review_ready_count'])} review-ready; {int(dino['negative_not_ready_or_uncertain_count'])} not-ready/uncertain",
            "identity label status": "Known-ID labels available for CzechLynx audit",
            "primary endpoint": "Reviewability after strong descriptor retrieval",
            "allowed manuscript claim": "Descriptor-agnostic reviewability analysis repeated by descriptor scope",
            "blocked claim": "No universal descriptor-specific superiority claim",
        },
        *reliability_rows,
        {
            "validation component": "Bobcat transfer-stress workflow allocation",
            "scope or count": bobcat_scope,
            "identity label status": "No manuscript identity-performance label contract",
            "primary endpoint": "Evidence burden and route stress only",
            "allowed manuscript claim": "PF-ERI can be used to audit transfer-stress evidence allocation",
            "blocked claim": "No Bobcat identity accuracy, false-match accuracy, mAP, MRR, or top-k claim",
        },
    ]
    return pd.DataFrame(rows)


def build_table2(model_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in model_df.iterrows():
        rows.append(
            {
                "scope": SCOPE_LABELS.get(row["scope"], row["scope"]),
                "model family": MODEL_LABELS.get(row["model_family"], row["model_family"]),
                "n pairs": int(row["pair_count"]),
                "review-ready / not-ready": f"{int(row['positive_review_ready_count'])} / {int(row['negative_not_ready_or_uncertain_count'])}",
                "AUROC [95% CI]": ci_metric(row, "auroc"),
                "AUPRC [95% CI]": ci_metric(row, "auprc"),
                "Brier": num(row["brier_score"]),
                "ECE-5": num(row["ece_5bin"]),
                "delta AUROC vs descriptor+quality": num(row["delta_auroc_vs_descriptor_plus_quality"]),
                "delta AUPRC vs descriptor+quality": num(row["delta_auprc_vs_descriptor_plus_quality"]),
            }
        )
    return pd.DataFrame(rows)


def build_table3(fixed_budget_df: pd.DataFrame, hygiene_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    budget_keep = {50, 100, 150, 200, 300, 400}
    pooled_budget = fixed_budget_df[(fixed_budget_df["scope"].eq("pooled")) & (fixed_budget_df["budget"].isin(budget_keep))].copy()
    strategy_order = {"pferi_priority": 0, "descriptor_priority": 1}
    pooled_budget["strategy_order"] = pooled_budget["strategy"].map(strategy_order)
    pooled_budget = pooled_budget.sort_values(["budget", "strategy_order"])
    for _, row in pooled_budget.iterrows():
        rows.append(
            {
                "analysis": "Fixed review budget",
                "decision or strategy": row["strategy"].replace("_", " "),
                "budget or pair count": int(row["budget"]),
                "review-ready rate": pct(row["review_ready_rate"]),
                "not-ready/uncertain rate": pct(row["not_ready_or_uncertain_rate"]),
                "same-ID retention": pct(row["same_id_retention"]),
                "false-candidate burden": pct(row["false_candidate_burden_rate"]),
                "claim boundary": "Review utility; same-ID retention is an audit, not identity assignment",
            }
        )

    pooled_hygiene = hygiene_df[hygiene_df["scope"].eq("pooled")].copy()
    for _, row in pooled_hygiene.iterrows():
        rows.append(
            {
                "analysis": "Pre-inference evidence hygiene",
                "decision or strategy": row["simulation_decision"].replace("_", " "),
                "budget or pair count": int(row["pair_count"]),
                "review-ready rate": pct(row["review_ready_rate"]),
                "not-ready/uncertain rate": pct(row["not_ready_or_uncertain_rate"]),
                "same-ID retention": pct(row["same_id_retention"]),
                "false-candidate burden": pct(row["false_candidate_burden_rate"]),
                "claim boundary": "Evidence routing before downstream inference; not identity accuracy",
            }
        )
    return pd.DataFrame(rows)


def build_readme(outputs: dict[str, list[str]]) -> str:
    readme = OUT_DIR / "README.md"
    text = """# PF-ERI Manuscript Figures And Tables

This folder contains manuscript-ready display items generated from audited
story-hardening outputs. The endpoint is CzechLynx human reviewability /
evidential admissibility. These figures and tables do not claim automated
individual identification, Bobcat identity accuracy, or retrieval mAP/top-k
improvement.

## Generated Display Items

- Figure 2: Reviewability model comparison with active-control increments.
- Figure 3: Quality and descriptor-similarity sensitivity analyses.
- Figure 4: Fixed-budget review utility and pre-inference evidence hygiene.
- Table 1: Dataset and validation contract.
- Table 2: Pooled and descriptor-specific model comparison.
- Table 3: Review routing and evidence hygiene.

## Files

"""
    for label, paths in outputs.items():
        text += f"- {label}: " + ", ".join(paths) + "\n"
    readme.write_text(text, encoding="utf-8")
    return str(readme.relative_to(PROJECT_ROOT))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    configure_style()

    sources = [
        ISSUE3_MODEL,
        ISSUE4_QUALITY,
        ISSUE4_HIGH_QUALITY,
        ISSUE4_HIGH_SIMILARITY,
        ISSUE4_RANK_SIMILARITY,
        ISSUE5_FIXED_BUDGET,
        ISSUE5_POLICY_DELTA,
        ISSUE6_HYGIENE,
    ]
    missing = [str(path.relative_to(PROJECT_ROOT)) for path in sources if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing source artifacts: {missing}")

    model_df = pd.read_csv(ISSUE3_MODEL)
    quality_df = pd.read_csv(ISSUE4_QUALITY)
    high_quality_df = pd.read_csv(ISSUE4_HIGH_QUALITY)
    high_similarity_df = pd.read_csv(ISSUE4_HIGH_SIMILARITY)
    rank_df = pd.read_csv(ISSUE4_RANK_SIMILARITY)
    fixed_budget_df = pd.read_csv(ISSUE5_FIXED_BUDGET)
    policy_delta_df = pd.read_csv(ISSUE5_POLICY_DELTA)
    hygiene_df = pd.read_csv(ISSUE6_HYGIENE)

    outputs: dict[str, list[str]] = {}
    outputs["Figure 2"] = build_figure2(model_df)
    outputs["Figure 3"] = build_figure3(quality_df, high_quality_df, high_similarity_df, rank_df)
    outputs["Figure 4"] = build_figure4(fixed_budget_df, hygiene_df)
    outputs["Table 1"] = write_table(build_table1(model_df), "table1_dataset_validation_contract")
    outputs["Table 2"] = write_table(build_table2(model_df), "table2_model_comparison")
    outputs["Table 3"] = write_table(build_table3(fixed_budget_df, hygiene_df), "table3_review_routing_evidence_hygiene")
    outputs["README"] = [build_readme(outputs)]

    audit = {
        "status": "PASS",
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "claim_boundary": (
            "CzechLynx human reviewability/evidential admissibility only; no automatic identity "
            "assignment, Bobcat identity accuracy, or retrieval mAP/MRR/top-k claim."
        ),
        "source_artifacts": {str(path.relative_to(PROJECT_ROOT)): int(pd.read_csv(path).shape[0]) for path in sources},
        "policy_delta_rows_loaded_for_audit_context": int(policy_delta_df.shape[0]),
        "outputs": outputs,
    }
    audit_path = OUT_DIR / "manuscript_figures_tables_audit.json"
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Built manuscript display items in {OUT_DIR.relative_to(PROJECT_ROOT)}")
    print(f"Audit: {audit_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
