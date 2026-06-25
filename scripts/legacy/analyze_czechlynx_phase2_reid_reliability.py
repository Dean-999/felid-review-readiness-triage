#!/usr/bin/env python3
"""Analyze CzechLynx Phase 2 pair similarity reliability signals."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PAIR_SIMILARITIES_CSV = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "czechlynx"
    / "czechlynx_pair_similarities.csv"
)

ANALYSIS_DIR = PROJECT_ROOT / "outputs" / "czechlynx" / "analysis"
QC_DIR = PROJECT_ROOT / "outputs" / "czechlynx" / "qc"
FIGURE_DIR = PROJECT_ROOT / "outputs" / "czechlynx" / "figures"

OVERALL_SUMMARY_CSV = ANALYSIS_DIR / "phase2_overall_similarity_summary.csv"
GROUP_SUMMARY_CSV = ANALYSIS_DIR / "phase2_readiness_group_similarity_summary.csv"
THRESHOLD_SUMMARY_CSV = ANALYSIS_DIR / "phase2_threshold_proxy_summary.csv"
REPORT_TXT = QC_DIR / "phase2_reliability_report.txt"
HISTOGRAM_PNG = FIGURE_DIR / "phase2_same_different_similarity_histogram.png"
BOXPLOT_PNG = FIGURE_DIR / "phase2_readiness_group_similarity_boxplot.png"

EXPECTED_ROWS = 400
EXPECTED_SAME_PAIRS = 100
EXPECTED_DIFFERENT_PAIRS = 300
THRESHOLD_QUANTILES = [0.50, 0.75, 0.90, 0.95]

REQUIRED_COLUMNS = [
    "pair_id",
    "image_id_a",
    "image_id_b",
    "same_individual",
    "triage_label_a",
    "triage_label_b",
    "pair_readiness_group",
    "cosine_similarity",
]


def clean_cell(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def read_csv_clean(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    for column in df.columns:
        df[column] = df[column].map(clean_cell)
    return df


def fail(message: str) -> int:
    print(f"FAIL: {message}")
    return 1


def summarize_similarity(df: pd.DataFrame, group_columns: list[str]) -> pd.DataFrame:
    grouped = df.groupby(group_columns, dropna=False)["cosine_similarity"]
    summary = grouped.agg(
        count="count",
        mean="mean",
        median="median",
        std="std",
        min="min",
        max="max",
        q25=lambda series: series.quantile(0.25),
        q75=lambda series: series.quantile(0.75),
    ).reset_index()
    return summary


def separation_gap(df: pd.DataFrame) -> float | None:
    same = df[df["same_individual"] == "True"]["cosine_similarity"]
    different = df[df["same_individual"] == "False"]["cosine_similarity"]
    if same.empty or different.empty:
        return None
    return float(same.mean() - different.mean())


def compute_auc(df: pd.DataFrame) -> str:
    try:
        from sklearn.metrics import roc_auc_score
    except ImportError:
        return "skipped; scikit-learn is not available"

    y_true = (df["same_individual"] == "True").astype(int)
    if y_true.nunique() < 2:
        return "skipped; only one same_individual class is present"
    auc = roc_auc_score(y_true, df["cosine_similarity"])
    return f"{auc:.6f}"


def threshold_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, float | int]] = []
    for quantile in THRESHOLD_QUANTILES:
        threshold = float(df["cosine_similarity"].quantile(quantile))
        same_above = df[
            (df["same_individual"] == "True") & (df["cosine_similarity"] >= threshold)
        ]
        different_above = df[
            (df["same_individual"] == "False") & (df["cosine_similarity"] >= threshold)
        ]
        rows.append(
            {
                "threshold_quantile": quantile,
                "threshold": threshold,
                "true_positive_proxy_count": len(same_above),
                "false_positive_proxy_count": len(different_above),
                "retained_same_pair_count": len(same_above),
                "retained_different_pair_count": len(different_above),
            }
        )
    return pd.DataFrame(rows)


def format_summary_table(summary: pd.DataFrame) -> list[str]:
    display = summary.copy()
    for column in ["mean", "median", "std", "min", "max", "q25", "q75"]:
        if column in display.columns:
            display[column] = display[column].map(lambda value: f"{value:.6f}")
    return display.to_string(index=False).splitlines()


def build_report(
    df: pd.DataFrame,
    overall_summary: pd.DataFrame,
    group_summary: pd.DataFrame,
    thresholds: pd.DataFrame,
    auc_text: str,
    figures_written: list[Path],
) -> str:
    same_count = int((df["same_individual"] == "True").sum())
    different_count = int((df["same_individual"] == "False").sum())
    overall_gap = separation_gap(df)

    group_gap_lines: list[str] = []
    for group, group_df in df.groupby("pair_readiness_group"):
        gap = separation_gap(group_df)
        if gap is None:
            group_gap_lines.append(f"- {group}: not computed; both classes not present")
        else:
            group_gap_lines.append(f"- {group}: {gap:.6f}")

    lines: list[str] = [
        "CzechLynx Phase 2 Reliability Analysis Report",
        "",
        "Scope",
        "-----",
        "This report summarizes pilot similarity behavior under a fixed generic ResNet-50 embedding baseline.",
        "Embeddings are treated as measurement signals for review-readiness validation, not as animal identification results.",
        "",
        "Inputs",
        "------",
        f"Pair similarities: {PAIR_SIMILARITIES_CSV}",
        f"Input row count: {len(df)}",
        f"Same-individual pairs: {same_count}",
        f"Different-individual pairs: {different_count}",
        "",
        "Overall Same/Different Summary",
        "------------------------------",
        *format_summary_table(overall_summary),
        "",
        "Separation Gap",
        "--------------",
        "Same-minus-different mean cosine similarity gap:",
        f"- Overall: {'not computed' if overall_gap is None else f'{overall_gap:.6f}'}",
        *group_gap_lines,
        "",
        "ROC-AUC",
        "-------",
        f"ROC-AUC for same_individual prediction from cosine_similarity: {auc_text}",
        "",
        "Threshold Proxy Summary",
        "-----------------------",
        *thresholds.to_string(index=False).splitlines(),
        "",
        "Pair Readiness Group Interpretation",
        "-----------------------------------",
        "Readiness-group summaries compare similarity behavior across triage-derived pair categories.",
        "Groups with both same- and different-individual pairs can support pilot separation-gap comparisons.",
        "Groups with sparse same-pair counts should be interpreted cautiously.",
        "",
        "Cautions",
        "--------",
        "- This is a pilot analysis under a fixed generic ResNet-50 ImageNet embedding baseline.",
        "- The baseline is not wildlife-specialized and was not trained or fine-tuned for CzechLynx.",
        "- Similarity scores are not real-world identity decisions.",
        "- Threshold summaries are pilot-specific proxies, not universal thresholds.",
        "- No final scientific claim is made here.",
        "",
        "Outputs",
        "-------",
        f"- {OVERALL_SUMMARY_CSV}",
        f"- {GROUP_SUMMARY_CSV}",
        f"- {THRESHOLD_SUMMARY_CSV}",
        f"- {REPORT_TXT}",
    ]

    if figures_written:
        lines.append("")
        lines.append("Figures")
        lines.append("-------")
        for path in figures_written:
            lines.append(f"- {path}")

    lines.append("")
    return "\n".join(lines)


def write_optional_figures(df: pd.DataFrame) -> list[Path]:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("Skipping figures: matplotlib is not available.")
        return []

    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    figures: list[Path] = []

    fig, ax = plt.subplots()
    same = df[df["same_individual"] == "True"]["cosine_similarity"]
    different = df[df["same_individual"] == "False"]["cosine_similarity"]
    ax.hist([same, different], label=["same_individual", "different_individual"])
    ax.set_title("CzechLynx Phase 2 Same/Different Similarity")
    ax.set_xlabel("Cosine similarity")
    ax.set_ylabel("Pair count")
    ax.legend()
    fig.tight_layout()
    fig.savefig(HISTOGRAM_PNG)
    plt.close(fig)
    figures.append(HISTOGRAM_PNG)

    fig, ax = plt.subplots(figsize=(10, 6))
    df.boxplot(
        column="cosine_similarity",
        by="pair_readiness_group",
        ax=ax,
        rot=45,
    )
    ax.set_title("Cosine Similarity by Pair Readiness Group")
    ax.set_xlabel("Pair readiness group")
    ax.set_ylabel("Cosine similarity")
    fig.suptitle("")
    fig.tight_layout()
    fig.savefig(BOXPLOT_PNG)
    plt.close(fig)
    figures.append(BOXPLOT_PNG)

    return figures


def main() -> int:
    if not PAIR_SIMILARITIES_CSV.exists():
        return fail(f"pair similarities file not found: {PAIR_SIMILARITIES_CSV}")

    df = read_csv_clean(PAIR_SIMILARITIES_CSV)
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing_columns:
        return fail("missing required column(s): " + ", ".join(missing_columns))

    if len(df) != EXPECTED_ROWS:
        return fail(f"expected {EXPECTED_ROWS} rows, found {len(df)}")

    same_count = int((df["same_individual"] == "True").sum())
    different_count = int((df["same_individual"] == "False").sum())
    if same_count != EXPECTED_SAME_PAIRS:
        return fail(f"expected {EXPECTED_SAME_PAIRS} same-individual pairs, found {same_count}")
    if different_count != EXPECTED_DIFFERENT_PAIRS:
        return fail(
            f"expected {EXPECTED_DIFFERENT_PAIRS} different-individual pairs, "
            f"found {different_count}"
        )

    df["cosine_similarity"] = pd.to_numeric(df["cosine_similarity"], errors="coerce")
    if df["cosine_similarity"].isna().any():
        return fail("cosine_similarity contains missing or nonnumeric values")

    overall_summary = summarize_similarity(df, ["same_individual"])
    group_summary = summarize_similarity(df, ["pair_readiness_group", "same_individual"])
    thresholds = threshold_summary(df)
    auc_text = compute_auc(df)

    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    QC_DIR.mkdir(parents=True, exist_ok=True)
    overall_summary.to_csv(OVERALL_SUMMARY_CSV, index=False)
    group_summary.to_csv(GROUP_SUMMARY_CSV, index=False)
    thresholds.to_csv(THRESHOLD_SUMMARY_CSV, index=False)

    figures_written = write_optional_figures(df)
    report = build_report(df, overall_summary, group_summary, thresholds, auc_text, figures_written)
    REPORT_TXT.write_text(report, encoding="utf-8")

    print("CzechLynx Phase 2 reliability analysis")
    print(f"Input rows: {len(df)}")
    print(f"Same-individual pairs: {same_count}")
    print(f"Different-individual pairs: {different_count}")
    print(f"ROC-AUC: {auc_text}")
    print(f"Wrote: {OVERALL_SUMMARY_CSV}")
    print(f"Wrote: {GROUP_SUMMARY_CSV}")
    print(f"Wrote: {THRESHOLD_SUMMARY_CSV}")
    print(f"Wrote: {REPORT_TXT}")
    for figure in figures_written:
        print(f"Wrote: {figure}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
