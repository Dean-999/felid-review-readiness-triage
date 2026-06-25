#!/usr/bin/env python3
"""Audit Phase 7A descriptor-supported staged PF-ERI outputs."""

from __future__ import annotations

import argparse
import csv
import math
import re
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_CSV = PROJECT_ROOT / "outputs/czechlynx/phase7a/visual_only_pf_eri/phase7a_visual_only_pf_eri_pair_scores.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase7a/descriptor_supported_pf_eri"
FIGURE_DIR = OUTPUT_DIR / "figures"

PAIR_SCORES_CSV = OUTPUT_DIR / "phase7a_descriptor_supported_pair_scores.csv"
SEPARATION_CSV = OUTPUT_DIR / "phase7a_descriptor_separation_summary.csv"
RISK_COVERAGE_CSV = OUTPUT_DIR / "phase7a_descriptor_risk_coverage_thresholds.csv"
COMPARISON_CSV = OUTPUT_DIR / "phase7a_visual_gate_vs_descriptor_only_comparison.csv"
HIGH_DESC_LOW_VISUAL_CSV = OUTPUT_DIR / "phase7a_high_descriptor_low_visual_cases.csv"

SUMMARY_TXT = PROJECT_ROOT / "outputs/czechlynx/qc/phase7a_descriptor_supported_pf_eri_audit_summary.txt"
REPORT_CSV = PROJECT_ROOT / "outputs/czechlynx/qc/phase7a_descriptor_supported_pf_eri_audit_report.csv"

REQUIRED_FILES = [
    PAIR_SCORES_CSV,
    SEPARATION_CSV,
    RISK_COVERAGE_CSV,
    COMPARISON_CSV,
    HIGH_DESC_LOW_VISUAL_CSV,
]

REQUIRED_FIGURES = [
    "resnet50_same_vs_different_boxplot.png",
    "megadescriptor_same_vs_different_boxplot.png",
    "descriptor_auc_by_visual_band.png",
    "descriptor_risk_coverage_curves.png",
    "visual_gate_vs_descriptor_only_comparison.png",
    "visual_score_vs_megadescriptor_by_label.png",
    "high_descriptor_low_visual_scatter.png",
]

REQUIRED_PAIR_COLUMNS = [
    "pair_id",
    "same_identity",
    "visual_pf_eri_weighted",
    "visual_pf_eri_min_rule",
    "visual_band",
    "resnet50_similarity",
    "megadescriptor_similarity",
    "pair_side_compatible",
    "primary_limiting_factor_for_score",
    "any_high_descriptor_low_visual_flag",
]

FORBIDDEN_HEADER_PARTS = [
    "unique_name",
    "latitude",
    "longitude",
    "trap_id",
    "cell_code",
    "location",
    "raw_path",
    "review_image_path",
    "working_individual_id",
    "true_id",
]

FORBIDDEN_PATTERNS = [
    re.compile(r"/Users/", re.IGNORECASE),
    re.compile(r"data/raw", re.IGNORECASE),
    re.compile(r"unique_name", re.IGNORECASE),
    re.compile(r"\blatitude\b", re.IGNORECASE),
    re.compile(r"\blongitude\b", re.IGNORECASE),
    re.compile(r"\btrap_id\b", re.IGNORECASE),
    re.compile(r"\bcell_code\b", re.IGNORECASE),
    re.compile(r"(?<![A-Za-z])lynx_[0-9]+", re.IGNORECASE),
]

MISLABEL_PATTERNS = [
    re.compile(r"safety[_ -]?score", re.IGNORECASE),
    re.compile(r"deployment[_ -]?safe", re.IGNORECASE),
    re.compile(r"final[_ -]?policy", re.IGNORECASE),
]

VALID_BANDS = {"high", "medium", "low", "unusable"}
REPORT_FIELDS = ["severity", "issue_type", "file", "row_id", "field", "value", "message"]


def add_issue(
    report: list[dict[str, str]],
    severity: str,
    issue_type: str,
    message: str,
    *,
    file: str = "",
    row_id: str = "",
    field: str = "",
    value: str = "",
) -> None:
    report.append(
        {
            "severity": severity,
            "issue_type": issue_type,
            "file": file,
            "row_id": row_id,
            "field": field,
            "value": value,
            "message": message,
        }
    )


def is_number(value: object) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def expected_pair_count(input_csv: Path) -> int:
    df = pd.read_csv(input_csv)
    return int((df["pair_modeling_eligible"].astype(str).str.lower() == "yes").sum())


def scan_sensitive_and_mislabels(path: Path, df: pd.DataFrame, report: list[dict[str, str]]) -> tuple[int, int]:
    leakage_count = 0
    mislabel_count = 0
    for column in df.columns:
        if any(part in column.lower() for part in FORBIDDEN_HEADER_PARTS):
            leakage_count += 1
            add_issue(report, "ERROR", "sensitive_header", "sensitive header found", file=str(path), field=column)
        for pattern in MISLABEL_PATTERNS:
            if pattern.search(column):
                mislabel_count += 1
                add_issue(
                    report,
                    "ERROR",
                    "descriptor_support_mislabeled",
                    "descriptor support must not be labeled as safety/final policy",
                    file=str(path),
                    field=column,
                )
    for idx, row in df.astype(str).iterrows():
        row_id = row.get("pair_id", str(idx))
        for column, value in row.items():
            for pattern in FORBIDDEN_PATTERNS:
                if pattern.search(value):
                    leakage_count += 1
                    add_issue(
                        report,
                        "ERROR",
                        "sensitive_value",
                        "sensitive value pattern found",
                        file=str(path),
                        row_id=row_id,
                        field=column,
                        value=value[:120],
                    )
            for pattern in MISLABEL_PATTERNS:
                if pattern.search(value):
                    mislabel_count += 1
                    add_issue(
                        report,
                        "ERROR",
                        "descriptor_support_mislabeled",
                        "descriptor support must not be labeled as safety/final policy",
                        file=str(path),
                        row_id=row_id,
                        field=column,
                        value=value[:120],
                    )
    return leakage_count, mislabel_count


def check_monotonic_thresholds(risk_df: pd.DataFrame, report: list[dict[str, str]]) -> int:
    issue_count = 0
    for (descriptor, gate), group in risk_df.groupby(["descriptor", "visual_gate"]):
        ordered = group.sort_values("threshold")
        selected = ordered["selected_count"].tolist()
        coverage = ordered["coverage"].tolist()
        for i in range(1, len(selected)):
            if selected[i] > selected[i - 1]:
                issue_count += 1
                add_issue(
                    report,
                    "ERROR",
                    "non_monotonic_selected_count",
                    "selected count increased as descriptor threshold increased",
                    row_id=f"{descriptor}:{gate}",
                    field="selected_count",
                )
            if coverage[i] > coverage[i - 1] + 1e-12:
                issue_count += 1
                add_issue(
                    report,
                    "ERROR",
                    "non_monotonic_coverage",
                    "coverage increased as descriptor threshold increased",
                    row_id=f"{descriptor}:{gate}",
                    field="coverage",
                )
    return issue_count


def audit(args: argparse.Namespace) -> int:
    report: list[dict[str, str]] = []
    for path in REQUIRED_FILES:
        if not path.exists():
            add_issue(report, "ERROR", "missing_output_file", f"missing output file: {path}", file=str(path))
    if not args.input_csv.exists():
        add_issue(report, "ERROR", "missing_input_file", f"missing input file: {args.input_csv}", file=str(args.input_csv))

    if report:
        args.summary_txt.parent.mkdir(parents=True, exist_ok=True)
        args.summary_txt.write_text("FAIL\nmissing required files\n", encoding="utf-8")
        pd.DataFrame(report, columns=REPORT_FIELDS).to_csv(args.report_csv, index=False)
        print("FAIL: missing required files")
        return 1

    pair_df = pd.read_csv(args.pair_scores_csv)
    sep_df = pd.read_csv(args.separation_csv)
    risk_df = pd.read_csv(args.risk_coverage_csv)
    comp_df = pd.read_csv(args.comparison_csv)
    failure_df = pd.read_csv(args.high_desc_low_visual_csv)

    expected_count = expected_pair_count(args.input_csv)
    if len(pair_df) != expected_count:
        add_issue(
            report,
            "ERROR",
            "pair_count_mismatch",
            f"descriptor pair-score count {len(pair_df)} does not match expected eligible count {expected_count}",
        )

    missing_columns = [column for column in REQUIRED_PAIR_COLUMNS if column not in pair_df.columns]
    for column in missing_columns:
        add_issue(report, "ERROR", "missing_pair_column", f"missing required pair-score column: {column}", field=column)

    descriptor_numeric_issue_count = 0
    for column in ["resnet50_similarity", "megadescriptor_similarity"]:
        if column in pair_df.columns:
            if pair_df[column].isna().any():
                descriptor_numeric_issue_count += int(pair_df[column].isna().sum())
                add_issue(report, "ERROR", "missing_descriptor", f"missing descriptor value(s): {column}", field=column)
            bad = [value for value in pair_df[column].tolist() if not is_number(value)]
            if bad:
                descriptor_numeric_issue_count += len(bad)
                add_issue(report, "ERROR", "non_numeric_descriptor", f"non-numeric descriptor value(s): {column}", field=column)

    invalid_band_count = 0
    if "visual_band" in pair_df.columns:
        invalid_bands = sorted(set(pair_df["visual_band"].astype(str)) - VALID_BANDS)
        invalid_band_count = len(invalid_bands)
        for band in invalid_bands:
            add_issue(report, "ERROR", "invalid_visual_band", "invalid visual band", field="visual_band", value=band)

    label_issue_count = 0
    if "same_identity" in pair_df.columns:
        invalid_labels = sorted(set(pair_df["same_identity"].astype(str)) - {"yes", "no"})
        label_issue_count = len(invalid_labels)
        for label in invalid_labels:
            add_issue(report, "ERROR", "invalid_label", "same_identity must be preserved as yes/no", field="same_identity", value=label)

    monotonic_issue_count = check_monotonic_thresholds(risk_df, report)

    leakage_issue_count = 0
    mislabel_issue_count = 0
    for path, df in [
        (args.pair_scores_csv, pair_df),
        (args.separation_csv, sep_df),
        (args.risk_coverage_csv, risk_df),
        (args.comparison_csv, comp_df),
        (args.high_desc_low_visual_csv, failure_df),
    ]:
        leakage, mislabel = scan_sensitive_and_mislabels(path, df, report)
        leakage_issue_count += leakage
        mislabel_issue_count += mislabel

    high_desc_low_visual_case_count = len(failure_df)
    if high_desc_low_visual_case_count == 0:
        add_issue(
            report,
            "WARN",
            "no_high_descriptor_low_visual_cases",
            "no high-descriptor low-visual cases were present; file still documents zero cases",
        )

    missing_figure_count = 0
    for figure in REQUIRED_FIGURES:
        path = args.figure_dir / figure
        if not path.exists() or path.stat().st_size == 0:
            missing_figure_count += 1
            add_issue(report, "ERROR", "missing_figure", f"missing or empty figure: {figure}", file=str(path))

    error_count = sum(1 for issue in report if issue["severity"] == "ERROR")
    warning_count = sum(1 for issue in report if issue["severity"] == "WARN")
    status = "PASS" if error_count == 0 else "FAIL"

    summary_lines = [
        status,
        f"expected_pair_count: {expected_count}",
        f"pair_score_count: {len(pair_df)}",
        f"descriptor_numeric_issue_count: {descriptor_numeric_issue_count}",
        f"invalid_visual_band_count: {invalid_band_count}",
        f"label_issue_count: {label_issue_count}",
        f"monotonic_threshold_issue_count: {monotonic_issue_count}",
        f"leakage_issue_count: {leakage_issue_count}",
        f"descriptor_mislabel_issue_count: {mislabel_issue_count}",
        f"high_descriptor_low_visual_case_count: {high_desc_low_visual_case_count}",
        f"missing_figure_count: {missing_figure_count}",
        f"error_count: {error_count}",
        f"warning_count: {warning_count}",
    ]

    args.summary_txt.parent.mkdir(parents=True, exist_ok=True)
    args.summary_txt.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    pd.DataFrame(report, columns=REPORT_FIELDS).to_csv(args.report_csv, index=False)

    print(status)
    for line in summary_lines[1:]:
        print(line)
    return 0 if status == "PASS" else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-csv", type=Path, default=INPUT_CSV)
    parser.add_argument("--pair-scores-csv", type=Path, default=PAIR_SCORES_CSV)
    parser.add_argument("--separation-csv", type=Path, default=SEPARATION_CSV)
    parser.add_argument("--risk-coverage-csv", type=Path, default=RISK_COVERAGE_CSV)
    parser.add_argument("--comparison-csv", type=Path, default=COMPARISON_CSV)
    parser.add_argument("--high-desc-low-visual-csv", type=Path, default=HIGH_DESC_LOW_VISUAL_CSV)
    parser.add_argument("--figure-dir", type=Path, default=FIGURE_DIR)
    parser.add_argument("--summary-txt", type=Path, default=SUMMARY_TXT)
    parser.add_argument("--report-csv", type=Path, default=REPORT_CSV)
    return parser.parse_args()


def main() -> int:
    return audit(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
