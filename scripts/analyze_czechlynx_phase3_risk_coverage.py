#!/usr/bin/env python3
"""Analyze CzechLynx Phase 3 risk-coverage policy trade-offs."""

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
PAIR_CSV = PROJECT_ROOT / "data" / "interim" / "czechlynx" / "czechlynx_pilot_pairs.csv"
VALIDATION_TABLE_CSV = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "czechlynx"
    / "czechlynx_pilot_validation_table.csv"
)

ANALYSIS_DIR = PROJECT_ROOT / "outputs" / "czechlynx" / "analysis"
QC_DIR = PROJECT_ROOT / "outputs" / "czechlynx" / "qc"
FIGURE_DIR = PROJECT_ROOT / "outputs" / "czechlynx" / "figures"

POLICY_COMPARISON_CSV = ANALYSIS_DIR / "phase3_policy_comparison.csv"
THRESHOLD_POLICY_SUMMARY_CSV = ANALYSIS_DIR / "phase3_threshold_policy_summary.csv"
REPORT_TXT = QC_DIR / "phase3_risk_coverage_report.txt"
RETAINED_EVIDENCE_PNG = FIGURE_DIR / "phase3_policy_retained_evidence_bar_chart.png"
FALSE_POSITIVE_PROXY_PNG = (
    FIGURE_DIR / "phase3_policy_false_positive_proxy_bar_chart.png"
)

EXPECTED_PAIR_ROWS = 400
THRESHOLDS = [0.547081, 0.680093, 0.770424, 0.808955]
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
REQUIRED_PAIR_COLUMNS = [
    "pair_id",
    "image_id_a",
    "image_id_b",
    "same_individual",
    "triage_label_a",
    "triage_label_b",
    "pair_readiness_group",
]
REQUIRED_VALIDATION_COLUMNS = ["pilot_image_id", "triage_label"]


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


def require_columns(df: pd.DataFrame, required_columns: list[str], label: str) -> list[str]:
    return [column for column in required_columns if column not in df.columns]


def validate_inputs(
    similarities: pd.DataFrame,
    pairs: pd.DataFrame,
    validation: pd.DataFrame,
) -> None:
    missing_similarity_columns = require_columns(
        similarities, REQUIRED_SIMILARITY_COLUMNS, "pair similarities"
    )
    missing_pair_columns = require_columns(pairs, REQUIRED_PAIR_COLUMNS, "pair file")
    missing_validation_columns = require_columns(
        validation, REQUIRED_VALIDATION_COLUMNS, "validation table"
    )
    failures: list[str] = []
    if missing_similarity_columns:
        failures.append(
            "pair similarities missing required column(s): "
            + ", ".join(missing_similarity_columns)
        )
    if missing_pair_columns:
        failures.append(
            "pair file missing required column(s): " + ", ".join(missing_pair_columns)
        )
    if missing_validation_columns:
        failures.append(
            "validation table missing required column(s): "
            + ", ".join(missing_validation_columns)
        )
    if failures:
        raise ValueError("; ".join(failures))

    if len(similarities) != EXPECTED_PAIR_ROWS:
        raise ValueError(
            f"pair similarities row count is {len(similarities)}; "
            f"expected {EXPECTED_PAIR_ROWS}"
        )
    if len(pairs) != EXPECTED_PAIR_ROWS:
        raise ValueError(
            f"pair file row count is {len(pairs)}; expected {EXPECTED_PAIR_ROWS}"
        )

    for df, label in (
        (similarities, "pair similarities"),
        (pairs, "pair file"),
    ):
        duplicate_count = int(df["pair_id"].duplicated().sum())
        if duplicate_count:
            raise ValueError(f"{label} contains {duplicate_count} duplicate pair_id value(s)")

    if validation["pilot_image_id"].duplicated().any():
        duplicate_count = int(validation["pilot_image_id"].duplicated().sum())
        raise ValueError(
            f"validation table contains {duplicate_count} duplicate pilot_image_id value(s)"
        )

    similarity_pair_ids = set(similarities["pair_id"])
    pair_ids = set(pairs["pair_id"])
    missing_pair_ids = sorted(pair_ids - similarity_pair_ids)
    extra_pair_ids = sorted(similarity_pair_ids - pair_ids)
    if missing_pair_ids or extra_pair_ids:
        details: list[str] = []
        if missing_pair_ids:
            details.append(
                f"{len(missing_pair_ids)} pair ID(s) missing from similarities"
            )
        if extra_pair_ids:
            details.append(f"{len(extra_pair_ids)} extra pair ID(s) in similarities")
        raise ValueError("; ".join(details))

    comparison_columns = [
        "image_id_a",
        "image_id_b",
        "same_individual",
        "triage_label_a",
        "triage_label_b",
        "pair_readiness_group",
    ]
    pairs_by_id = pairs.set_index("pair_id")
    similarities_by_id = similarities.set_index("pair_id")
    for column in comparison_columns:
        mismatched = [
            pair_id
            for pair_id in sorted(pair_ids)
            if pairs_by_id.loc[pair_id, column] != similarities_by_id.loc[pair_id, column]
        ]
        if mismatched:
            raise ValueError(
                f"{len(mismatched)} {column} value(s) differ between pair file "
                "and pair similarities"
            )

    similarity_values = pd.to_numeric(similarities["cosine_similarity"], errors="coerce")
    if similarity_values.isna().any():
        bad_count = int(similarity_values.isna().sum())
        raise ValueError(f"cosine_similarity contains {bad_count} nonnumeric value(s)")

    valid_labels = {"review-ready", "review-limited", "unidentifiable"}
    pair_labels = set(similarities["triage_label_a"]) | set(similarities["triage_label_b"])
    validation_labels = set(validation["triage_label"])
    unexpected_labels = sorted((pair_labels | validation_labels) - valid_labels)
    if unexpected_labels:
        raise ValueError(
            "unexpected triage_label value(s): " + ", ".join(unexpected_labels)
        )


def policy_pair_mask(policy: str, df: pd.DataFrame) -> pd.Series:
    if policy == "no_filter":
        return pd.Series(True, index=df.index)
    if policy == "strict_filter":
        return (df["triage_label_a"] == "review-ready") & (
            df["triage_label_b"] == "review-ready"
        )
    if policy == "balanced_filter":
        return (df["triage_label_a"] != "unidentifiable") & (
            df["triage_label_b"] != "unidentifiable"
        )
    raise ValueError(f"Unknown policy: {policy}")


def policy_image_mask(policy: str, df: pd.DataFrame) -> pd.Series:
    if policy == "no_filter":
        return pd.Series(True, index=df.index)
    if policy == "strict_filter":
        return df["triage_label"] == "review-ready"
    if policy == "balanced_filter":
        return df["triage_label"] != "unidentifiable"
    raise ValueError(f"Unknown policy: {policy}")


def mean_or_none(series: pd.Series) -> float | None:
    if series.empty:
        return None
    return float(series.mean())


def rate(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return float(numerator / denominator)


def build_policy_comparison(
    similarities: pd.DataFrame,
    validation: pd.DataFrame,
) -> pd.DataFrame:
    total_pairs = len(similarities)
    total_same_pairs = int((similarities["same_individual_bool"]).sum())
    total_different_pairs = int((~similarities["same_individual_bool"]).sum())
    total_images = len(validation)
    has_unique_ids = "unique_name" in validation.columns

    rows: list[dict[str, object]] = []
    for policy in POLICY_ORDER:
        retained_pairs = similarities[policy_pair_mask(policy, similarities)].copy()
        retained_images = validation[policy_image_mask(policy, validation)].copy()
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
                "retained_image_count": len(retained_images),
                "retained_image_rate": rate(len(retained_images), total_images),
                "retained_unique_identity_count": (
                    retained_images["unique_name"].nunique() if has_unique_ids else None
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


def build_threshold_summary(similarities: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for policy in POLICY_ORDER:
        retained_pairs = similarities[policy_pair_mask(policy, similarities)].copy()
        for threshold in THRESHOLDS:
            above_threshold = retained_pairs["cosine_similarity"] >= threshold
            true_positive_proxy_count = int(
                (retained_pairs["same_individual_bool"] & above_threshold).sum()
            )
            false_positive_proxy_count = int(
                ((~retained_pairs["same_individual_bool"]) & above_threshold).sum()
            )
            rows.append(
                {
                    "policy": policy,
                    "threshold": threshold,
                    "true_positive_proxy_count": true_positive_proxy_count,
                    "false_positive_proxy_count": false_positive_proxy_count,
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
    validation: pd.DataFrame,
    policy_comparison: pd.DataFrame,
    threshold_summary: pd.DataFrame,
    figures_written: list[Path],
) -> str:
    same_pairs = int(similarities["same_individual_bool"].sum())
    different_pairs = int((~similarities["same_individual_bool"]).sum())
    identity_text = (
        str(validation["unique_name"].nunique())
        if "unique_name" in validation.columns
        else "not available"
    )

    lines: list[str] = [
        "CzechLynx Phase 3 Risk-Coverage Policy Analysis Report",
        "",
        "Scope",
        "-----",
        "This is a pilot-level CzechLynx risk-coverage analysis.",
        "It uses existing Phase 2 pairwise cosine similarities under a fixed generic ResNet-50 ImageNet baseline.",
        "The baseline is not a wildlife-specialized Re-ID model and no model training or fine-tuning is added here.",
        "Similarity scores are measurement signals for review-readiness evaluation, not true individual identification results.",
        "",
        "Required Cautions",
        "-----------------",
        "- False-positive counts are pairwise proxy counts, not real-world false-match rates.",
        "- Thresholds are pilot-specific and model-specific; they are not universal felid Re-ID thresholds.",
        "- This analysis does not claim true individual identification.",
        "- This analysis does not claim field deployment readiness.",
        "- No final scientific claims are made here.",
        "",
        "Inputs",
        "------",
        f"Pair similarities: {PAIR_SIMILARITIES_CSV}",
        f"Pair file: {PAIR_CSV}",
        f"Validation table: {VALIDATION_TABLE_CSV}",
        f"Input pair rows: {len(similarities)}",
        f"Same-individual pairs: {same_pairs}",
        f"Different-individual pairs: {different_pairs}",
        f"Validation-table images: {len(validation)}",
        f"Validation-table unique identity count: {identity_text}",
        "",
        "Policies",
        "--------",
        "- no_filter: all pairs and images are retained.",
        "- balanced_filter: review-ready and review-limited images are retained; unidentifiable images are excluded.",
        "- strict_filter: only review-ready images are retained.",
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
        [position - 0.2 for position in x_positions],
        policy_comparison["retained_image_count"],
        width=0.2,
        label="retained images",
    )
    ax.bar(
        x_positions,
        policy_comparison["retained_unique_identity_count"],
        width=0.2,
        label="retained identities",
    )
    ax.bar(
        [position + 0.2 for position in x_positions],
        policy_comparison["retained_same_pair_count"],
        width=0.2,
        label="retained same pairs",
    )
    ax.set_xticks(list(x_positions))
    ax.set_xticklabels(policy_comparison["policy"], rotation=20, ha="right")
    ax.set_title("CzechLynx Phase 3 Retained Evidence by Policy")
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
    ax.set_title("CzechLynx Phase 3 False-Positive Proxy Counts")
    ax.set_xlabel("Similarity threshold")
    ax.set_ylabel("Different-individual pairs above threshold")
    ax.legend(title="Policy")
    fig.tight_layout()
    fig.savefig(FALSE_POSITIVE_PROXY_PNG)
    plt.close(fig)
    figures.append(FALSE_POSITIVE_PROXY_PNG)

    return figures


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    for path, label in (
        (PAIR_SIMILARITIES_CSV, "pair similarities"),
        (PAIR_CSV, "pair file"),
        (VALIDATION_TABLE_CSV, "validation table"),
    ):
        if not path.exists():
            raise FileNotFoundError(f"{label} not found: {path}")

    similarities = read_csv_clean(PAIR_SIMILARITIES_CSV)
    pairs = read_csv_clean(PAIR_CSV)
    validation = read_csv_clean(VALIDATION_TABLE_CSV)
    validate_inputs(similarities, pairs, validation)
    similarities["same_individual_bool"] = normalize_same_individual(
        similarities["same_individual"]
    )
    similarities["cosine_similarity"] = pd.to_numeric(
        similarities["cosine_similarity"],
        errors="raise",
    )
    return similarities, pairs, validation


def main() -> int:
    try:
        similarities, _pairs, validation = load_inputs()
    except Exception as exc:  # noqa: BLE001 - print concise audit-style failure.
        return fail(str(exc))

    policy_comparison = build_policy_comparison(similarities, validation)
    threshold_summary = build_threshold_summary(similarities)

    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    QC_DIR.mkdir(parents=True, exist_ok=True)
    policy_comparison.to_csv(POLICY_COMPARISON_CSV, index=False)
    threshold_summary.to_csv(THRESHOLD_POLICY_SUMMARY_CSV, index=False)

    figures_written = write_optional_figures(policy_comparison, threshold_summary)
    report = build_report(
        similarities,
        validation,
        policy_comparison,
        threshold_summary,
        figures_written,
    )
    REPORT_TXT.write_text(report, encoding="utf-8")

    print("CzechLynx Phase 3 risk-coverage policy analysis")
    print(f"Input pair rows: {len(similarities)}")
    print(f"Validation-table images: {len(validation)}")
    print("Policies: " + ", ".join(POLICY_ORDER))
    print(f"Wrote: {POLICY_COMPARISON_CSV}")
    print(f"Wrote: {THRESHOLD_POLICY_SUMMARY_CSV}")
    print(f"Wrote: {REPORT_TXT}")
    for figure in figures_written:
        print(f"Wrote: {figure}")
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
