#!/usr/bin/env python3
"""Analyze CzechLynx Phase 3B risk-coverage policy trade-offs under MegaDescriptor-S-224."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PAIR_SIMILARITIES_CSV = (
    PROJECT_ROOT
    / "outputs"
    / "czechlynx"
    / "colab_megadescriptor"
    / "czechlynx_wildlife_baseline_outputs"
    / "czechlynx_pair_similarities_megadescriptor_s224.csv"
)

ANALYSIS_DIR = PROJECT_ROOT / "outputs" / "czechlynx" / "analysis"
QC_DIR = PROJECT_ROOT / "outputs" / "czechlynx" / "qc"
FIGURE_DIR = PROJECT_ROOT / "outputs" / "czechlynx" / "figures"

POLICY_COMPARISON_CSV = ANALYSIS_DIR / "phase3_megadescriptor_policy_comparison.csv"
THRESHOLD_POLICY_SUMMARY_CSV = (
    ANALYSIS_DIR / "phase3_megadescriptor_threshold_policy_summary.csv"
)
REPORT_TXT = QC_DIR / "phase3_megadescriptor_risk_coverage_report.txt"
RETAINED_EVIDENCE_PNG = (
    FIGURE_DIR / "phase3_megadescriptor_policy_retained_evidence_bar_chart.png"
)
FALSE_POSITIVE_PROXY_PNG = (
    FIGURE_DIR / "phase3_megadescriptor_policy_false_positive_proxy_bar_chart.png"
)

EXPECTED_PAIR_ROWS = 400
EXPECTED_SAME_PAIRS = 100
EXPECTED_DIFFERENT_PAIRS = 300
THRESHOLD_QUANTILES = [0.50, 0.75, 0.90, 0.95]
POLICY_ORDER = ["no_filter", "balanced_filter", "strict_filter"]

REQUIRED_SIMILARITY_COLUMNS = [
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


def normalize_same_individual(series: pd.Series) -> pd.Series:
    normalized = series.map(clean_cell).str.lower()
    allowed_values = {"true", "false"}
    unexpected = sorted(set(normalized) - allowed_values)
    if unexpected:
        raise ValueError(
            "same_individual contains unexpected value(s): " + ", ".join(unexpected)
        )
    return normalized.map({"true": True, "false": False})


def policy_pair_mask(policy: str, df: pd.DataFrame) -> pd.Series:
    if policy == "no_filter":
        return pd.Series(True, index=df.index)
    if policy == "strict_filter":
        return df["pair_readiness_group"] == "ready_ready"
    if policy == "balanced_filter":
        return (df["triage_label_a"] != "unidentifiable") & (
            df["triage_label_b"] != "unidentifiable"
        )
    raise ValueError(f"Unknown policy: {policy}")


def mean_or_none(series: pd.Series) -> float | None:
    if series.empty:
        return None
    return float(series.mean())


def rate(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return float(numerator / denominator)


def compute_thresholds(similarities: pd.DataFrame) -> list[tuple[float, float]]:
    thresholds: list[tuple[float, float]] = []
    for quantile in THRESHOLD_QUANTILES:
        threshold = float(similarities["cosine_similarity"].quantile(quantile))
        thresholds.append((quantile, threshold))
    return thresholds


def build_policy_comparison(similarities: pd.DataFrame) -> pd.DataFrame:
    total_pairs = len(similarities)
    total_same_pairs = EXPECTED_SAME_PAIRS
    total_different_pairs = EXPECTED_DIFFERENT_PAIRS

    rows: list[dict[str, object]] = []
    for policy in POLICY_ORDER:
        retained_pairs = similarities[policy_pair_mask(policy, similarities)].copy()
        same_pairs = retained_pairs[retained_pairs["same_individual_bool"]]
        different_pairs = retained_pairs[~retained_pairs["same_individual_bool"]]
        same_mean = mean_or_none(same_pairs["cosine_similarity"])
        different_mean = mean_or_none(different_pairs["cosine_similarity"])

        rows.append(
            {
                "policy": policy,
                "retained_pair_count": len(retained_pairs),
                "retained_pair_rate": rate(len(retained_pairs), total_pairs),
                "retained_same_pair_count": len(same_pairs),
                "retained_different_pair_count": len(different_pairs),
                "retained_same_pair_rate": rate(len(same_pairs), total_same_pairs),
                "retained_different_pair_rate": rate(
                    len(different_pairs), total_different_pairs
                ),
                "same_pair_mean_similarity": same_mean,
                "different_pair_mean_similarity": different_mean,
                "same_minus_different_mean_gap": (
                    None
                    if same_mean is None or different_mean is None
                    else same_mean - different_mean
                ),
            }
        )
    return pd.DataFrame(rows)


def build_threshold_summary(
    similarities: pd.DataFrame,
    thresholds: list[tuple[float, float]],
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for policy in POLICY_ORDER:
        retained_pairs = similarities[policy_pair_mask(policy, similarities)].copy()
        for quantile, threshold in thresholds:
            above_threshold = retained_pairs["cosine_similarity"] >= threshold
            retained_same = retained_pairs["same_individual_bool"] & above_threshold
            retained_different = (~retained_pairs["same_individual_bool"]) & above_threshold
            true_positive_proxy_count = int(retained_same.sum())
            false_positive_proxy_count = int(retained_different.sum())
            rows.append(
                {
                    "policy": policy,
                    "threshold_quantile": quantile,
                    "threshold": threshold,
                    "true_positive_proxy_count": true_positive_proxy_count,
                    "false_positive_proxy_count": false_positive_proxy_count,
                    "retained_same_pair_count": true_positive_proxy_count,
                    "retained_different_pair_count": false_positive_proxy_count,
                }
            )
    return pd.DataFrame(rows)


def format_float(value: object) -> str:
    if value is None or pd.isna(value):
        return "not computed"
    return f"{float(value):.6f}"


def format_table(df: pd.DataFrame) -> list[str]:
    display = df.copy()
    for column in display.columns:
        if pd.api.types.is_float_dtype(display[column]):
            display[column] = display[column].map(format_float)
    return display.to_string(index=False).splitlines()


def build_report(
    similarities: pd.DataFrame,
    policy_comparison: pd.DataFrame,
    threshold_summary: pd.DataFrame,
    thresholds: list[tuple[float, float]],
    figures_written: list[Path],
) -> str:
    same_pairs = int(similarities["same_individual_bool"].sum())
    different_pairs = int((~similarities["same_individual_bool"]).sum())
    threshold_lines = [
        f"  quantile {quantile:.2f}: {threshold:.6f}"
        for quantile, threshold in thresholds
    ]

    lines: list[str] = [
        "CzechLynx Phase 3B MegaDescriptor-S-224 Risk-Coverage Policy Analysis Report",
        "",
        "Scope",
        "-----",
        "This is Phase 3B under the MegaDescriptor-S-224 fixed pretrained wildlife baseline.",
        "It uses Colab-generated pairwise cosine similarities as measurement signals, "
        "not animal identification decisions.",
        "No model training or fine-tuning was performed.",
        "",
        "Required Cautions",
        "-----------------",
        "- Thresholds are MegaDescriptor-specific quantiles from the MegaDescriptor cosine "
        "similarity distribution.",
        "- ResNet-50 thresholds must not be reused across embedding baselines.",
        "- False-positive counts are pairwise proxy counts, not real-world false-match rates.",
        "- This analysis does not claim true individual animal identification.",
        "- This analysis does not claim a universal felid Re-ID threshold.",
        "- This analysis does not claim field deployment readiness.",
        "- No final scientific claims are made here.",
        "",
        "Inputs",
        "------",
        f"Pair similarities: {PAIR_SIMILARITIES_CSV}",
        f"Input pair rows: {len(similarities)}",
        f"Same-individual pairs: {same_pairs}",
        f"Different-individual pairs: {different_pairs}",
        "",
        "MegaDescriptor-Specific Thresholds",
        "--------------------------------",
        *threshold_lines,
        "",
        "Policies",
        "--------",
        "- no_filter: all pairs are retained.",
        "- balanced_filter: both images are not unidentifiable.",
        "- strict_filter: pair_readiness_group == ready_ready.",
        "",
        "Policy Comparison",
        "-----------------",
        *format_table(policy_comparison),
        "",
        "Threshold Proxy Summary",
        "-----------------------",
        *format_table(threshold_summary),
        "",
        "Outputs",
        "-------",
        f"- {POLICY_COMPARISON_CSV}",
        f"- {THRESHOLD_POLICY_SUMMARY_CSV}",
        f"- {REPORT_TXT}",
    ]

    if figures_written:
        lines.extend(["", "Figures", "-------"])
        for figure in figures_written:
            lines.append(f"- {figure}")
    else:
        lines.extend(["", "Figures", "-------", "- Skipped; matplotlib is not available."])

    lines.append("")
    return "\n".join(lines)


def write_optional_figures(
    policy_comparison: pd.DataFrame,
    threshold_summary: pd.DataFrame,
) -> list[Path]:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("Skipping figures: matplotlib is not available.")
        return []

    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    figures: list[Path] = []

    x_positions = range(len(policy_comparison))
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(
        [position - 0.15 for position in x_positions],
        policy_comparison["retained_same_pair_count"],
        width=0.3,
        label="retained same pairs",
    )
    ax.bar(
        [position + 0.15 for position in x_positions],
        policy_comparison["retained_different_pair_count"],
        width=0.3,
        label="retained different pairs",
    )
    ax.set_xticks(list(x_positions))
    ax.set_xticklabels(policy_comparison["policy"], rotation=20, ha="right")
    ax.set_title("CzechLynx Phase 3B MegaDescriptor Retained Evidence by Policy")
    ax.set_ylabel("Count")
    ax.legend()
    fig.tight_layout()
    fig.savefig(RETAINED_EVIDENCE_PNG)
    plt.close(fig)
    figures.append(RETAINED_EVIDENCE_PNG)

    pivot = threshold_summary.pivot(
        index="threshold",
        columns="policy",
        values="false_positive_proxy_count",
    )
    pivot = pivot[POLICY_ORDER]
    fig, ax = plt.subplots(figsize=(9, 5))
    pivot.plot(kind="bar", ax=ax)
    ax.set_title("CzechLynx Phase 3B MegaDescriptor False-Positive Proxy Counts")
    ax.set_xlabel("Similarity threshold")
    ax.set_ylabel("Different-individual pairs above threshold")
    ax.legend(title="Policy")
    fig.tight_layout()
    fig.savefig(FALSE_POSITIVE_PROXY_PNG)
    plt.close(fig)
    figures.append(FALSE_POSITIVE_PROXY_PNG)

    return figures


def validate_inputs(similarities: pd.DataFrame) -> None:
    missing_columns = [
        column for column in REQUIRED_SIMILARITY_COLUMNS if column not in similarities.columns
    ]
    if missing_columns:
        raise ValueError(
            "pair similarities missing required column(s): " + ", ".join(missing_columns)
        )
    if len(similarities) != EXPECTED_PAIR_ROWS:
        raise ValueError(
            f"pair similarities row count is {len(similarities)}; "
            f"expected {EXPECTED_PAIR_ROWS}"
        )
    if int(similarities["pair_id"].duplicated().sum()):
        raise ValueError("pair similarities contains duplicate pair_id value(s)")

    similarity_values = pd.to_numeric(similarities["cosine_similarity"], errors="coerce")
    if similarity_values.isna().any():
        bad_count = int(similarity_values.isna().sum())
        raise ValueError(f"cosine_similarity contains {bad_count} nonnumeric value(s)")


def load_inputs() -> pd.DataFrame:
    if not PAIR_SIMILARITIES_CSV.exists():
        raise FileNotFoundError(f"pair similarities not found: {PAIR_SIMILARITIES_CSV}")

    similarities = read_csv_clean(PAIR_SIMILARITIES_CSV)
    validate_inputs(similarities)
    similarities["same_individual_bool"] = normalize_same_individual(
        similarities["same_individual"]
    )
    similarities["cosine_similarity"] = pd.to_numeric(
        similarities["cosine_similarity"],
        errors="raise",
    )
    return similarities


def main() -> int:
    try:
        similarities = load_inputs()
    except Exception as exc:  # noqa: BLE001 - print concise audit-style failure.
        return fail(str(exc))

    thresholds = compute_thresholds(similarities)
    policy_comparison = build_policy_comparison(similarities)
    threshold_summary = build_threshold_summary(similarities, thresholds)

    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    QC_DIR.mkdir(parents=True, exist_ok=True)
    policy_comparison.to_csv(POLICY_COMPARISON_CSV, index=False)
    threshold_summary.to_csv(THRESHOLD_POLICY_SUMMARY_CSV, index=False)

    figures_written = write_optional_figures(policy_comparison, threshold_summary)
    report = build_report(
        similarities,
        policy_comparison,
        threshold_summary,
        thresholds,
        figures_written,
    )
    REPORT_TXT.write_text(report, encoding="utf-8")

    print("CzechLynx Phase 3B MegaDescriptor risk-coverage policy analysis")
    print(f"Input pair rows: {len(similarities)}")
    print("Policies: " + ", ".join(POLICY_ORDER))
    print("Threshold quantiles: " + ", ".join(f"{q:.2f}" for q in THRESHOLD_QUANTILES))
    print(f"Wrote: {POLICY_COMPARISON_CSV}")
    print(f"Wrote: {THRESHOLD_POLICY_SUMMARY_CSV}")
    print(f"Wrote: {REPORT_TXT}")
    for figure in figures_written:
        print(f"Wrote: {figure}")
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
