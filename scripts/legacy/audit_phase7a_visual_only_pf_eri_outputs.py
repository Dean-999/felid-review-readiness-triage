#!/usr/bin/env python3
"""Audit Phase 7A visual-only PF-ERI gate outputs."""

from __future__ import annotations

import argparse
import csv
import math
import re
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_CSV = PROJECT_ROOT / "outputs/czechlynx/phase7a/pair_tables/phase7a_1000_image_pair_table_v1.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase7a/visual_only_pf_eri"
SCORES_CSV = OUTPUT_DIR / "phase7a_visual_only_pf_eri_pair_scores.csv"
SUMMARY_CSV = OUTPUT_DIR / "phase7a_visual_only_pf_eri_summary.csv"
DRIVER_CSV = OUTPUT_DIR / "phase7a_visual_only_pf_eri_factor_driver_summary.csv"
RISK_BINS_CSV = OUTPUT_DIR / "phase7a_visual_only_pf_eri_risk_bins.csv"
FIGURE_DIR = OUTPUT_DIR / "figures"
SUMMARY_TXT = PROJECT_ROOT / "outputs/czechlynx/qc/phase7a_visual_only_pf_eri_audit_summary.txt"
REPORT_CSV = PROJECT_ROOT / "outputs/czechlynx/qc/phase7a_visual_only_pf_eri_audit_report.csv"

REQUIRED_SCORE_COLUMNS = [
    "pair_id",
    "image_id_a",
    "image_id_b",
    "same_identity",
    "source_phase_a",
    "source_phase_b",
    "pair_source_phase_type",
    "pair_modeling_eligible",
    "pair_exclusion_reason",
    "pair_side_compatible",
    "pair_primary_limiting_factor_combined",
    "pair_pattern_min_score",
    "pair_side_quality_min_score",
    "pair_body_fraction_min_score",
    "pair_blur_min_score",
    "pair_occlusion_min_score",
    "pair_contrast_min_score",
    "pair_side_compatibility_score",
    "visual_pf_eri_min_rule",
    "visual_pf_eri_weighted",
    "visual_pf_eri_band",
    "primary_limiting_factor_for_score",
    "resnet50_similarity_reference_only",
    "megadescriptor_similarity_reference_only",
    "descriptor_reference_note",
]

REQUIRED_FILES = [SCORES_CSV, SUMMARY_CSV, DRIVER_CSV, RISK_BINS_CSV]
REQUIRED_FIGURES = [
    "visual_pf_eri_weighted_histogram.png",
    "visual_pf_eri_same_vs_different_boxplot.png",
    "visual_pf_eri_by_side_compatibility.png",
    "visual_pf_eri_by_primary_limiting_factor.png",
    "visual_pf_eri_score_bin_composition.png",
    "visual_pf_eri_vs_descriptor_similarity_reference_only.png",
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

REPORT_FIELDS = ["severity", "issue_type", "file", "row_id", "field", "value", "message"]


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader), list(reader.fieldnames or [])


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


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


def is_float(value: str) -> bool:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(parsed)


def clean(value: str) -> str:
    return str(value).strip().lower()


def expected_eligible_count(input_csv: Path) -> int:
    rows, _ = read_csv(input_csv)
    return sum(
        1
        for row in rows
        if clean(row.get("pair_modeling_eligible", "")) == "yes"
        and clean(row.get("pair_label_available", "")) == "yes"
    )


def audit(args: argparse.Namespace) -> int:
    report: list[dict[str, str]] = []

    for path in REQUIRED_FILES:
        if not path.exists():
            add_issue(report, "ERROR", "missing_output_file", f"missing output file: {path}", file=str(path))

    if not args.input_csv.exists():
        add_issue(
            report,
            "ERROR",
            "missing_input_file",
            f"missing input file: {args.input_csv}",
            file=str(args.input_csv),
        )

    if report:
        write_csv(args.report_csv, report, REPORT_FIELDS)
        args.summary_txt.parent.mkdir(parents=True, exist_ok=True)
        args.summary_txt.write_text("FAIL\nmissing required input or output files\n", encoding="utf-8")
        print("FAIL: missing required input or output files")
        return 1

    input_eligible_count = expected_eligible_count(args.input_csv)
    score_rows, score_headers = read_csv(args.scores_csv)
    risk_rows, risk_headers = read_csv(args.risk_bins_csv)

    missing_score_columns = [column for column in REQUIRED_SCORE_COLUMNS if column not in score_headers]
    for column in missing_score_columns:
        add_issue(report, "ERROR", "missing_score_column", f"missing score column: {column}", field=column)

    forbidden_headers = [
        header for header in score_headers if any(part in header.lower() for part in FORBIDDEN_HEADER_PARTS)
    ]
    for header in forbidden_headers:
        add_issue(report, "ERROR", "sensitive_header", f"forbidden/sensitive header present: {header}", field=header)

    if len(score_rows) != input_eligible_count:
        add_issue(
            report,
            "ERROR",
            "row_count_mismatch",
            f"score rows ({len(score_rows)}) do not match eligible input rows ({input_eligible_count})",
        )

    duplicate_pair_count = sum(count - 1 for count in Counter(row["pair_id"] for row in score_rows).values() if count > 1)
    if duplicate_pair_count:
        add_issue(report, "ERROR", "duplicate_pair_id", f"duplicate pair score rows: {duplicate_pair_count}")

    numeric_score_columns = [
        "visual_pf_eri_min_rule",
        "visual_pf_eri_weighted",
        "pair_pattern_min_score",
        "pair_side_quality_min_score",
        "pair_body_fraction_min_score",
        "pair_blur_min_score",
        "pair_occlusion_min_score",
        "pair_contrast_min_score",
        "pair_side_compatibility_score",
    ]

    missing_visual_score_count = 0
    invalid_numeric_count = 0
    invalid_range_count = 0
    label_issue_count = 0
    descriptor_note_issue_count = 0
    leakage_issue_count = 0

    for row in score_rows:
        pair_id = row.get("pair_id", "")
        for column in numeric_score_columns:
            value = row.get(column, "")
            if value == "":
                missing_visual_score_count += 1
                add_issue(report, "ERROR", "missing_score_value", "missing visual score value", row_id=pair_id, field=column)
                continue
            if not is_float(value):
                invalid_numeric_count += 1
                add_issue(
                    report,
                    "ERROR",
                    "non_numeric_score",
                    "visual score value is not numeric",
                    row_id=pair_id,
                    field=column,
                    value=value,
                )

        for column in ["visual_pf_eri_min_rule", "visual_pf_eri_weighted"]:
            if is_float(row.get(column, "")):
                parsed = float(row[column])
                if parsed < 0.0 or parsed > 100.0:
                    invalid_range_count += 1
                    add_issue(
                        report,
                        "ERROR",
                        "score_range",
                        "visual PF-ERI score outside 0-100 range",
                        row_id=pair_id,
                        field=column,
                        value=row[column],
                    )

        if row.get("same_identity") not in {"yes", "no"}:
            label_issue_count += 1
            add_issue(
                report,
                "ERROR",
                "invalid_label",
                "same_identity must be preserved as yes/no",
                row_id=pair_id,
                field="same_identity",
                value=row.get("same_identity", ""),
            )

        descriptor_headers = [
            header
            for header in score_headers
            if "descriptor" in header.lower() or "resnet50" in header.lower() or "similarity" in header.lower()
        ]
        unsafe_descriptor_headers = [
            header
            for header in descriptor_headers
            if not header.endswith("_reference_only") and header != "descriptor_reference_note"
        ]
        for header in unsafe_descriptor_headers:
            descriptor_note_issue_count += 1
            add_issue(
                report,
                "ERROR",
                "descriptor_not_reference_only",
                "descriptor/similarity column must be clearly marked reference-only",
                field=header,
            )

        if "not used" not in row.get("descriptor_reference_note", "").lower():
            descriptor_note_issue_count += 1
            add_issue(
                report,
                "ERROR",
                "descriptor_note_missing",
                "descriptor reference note must state descriptors were not used in score",
                row_id=pair_id,
                field="descriptor_reference_note",
            )

        for field, value in row.items():
            text = str(value)
            for pattern in FORBIDDEN_PATTERNS:
                if pattern.search(text):
                    leakage_issue_count += 1
                    add_issue(
                        report,
                        "ERROR",
                        "sensitive_value",
                        "sensitive value pattern found",
                        row_id=pair_id,
                        field=field,
                        value=text[:120],
                    )

    sparse_bin_count = 0
    if risk_headers:
        for row in risk_rows:
            count_value = row.get("pair_count", "")
            if not count_value.isdigit():
                add_issue(
                    report,
                    "ERROR",
                    "invalid_bin_count",
                    "risk bin pair_count must be an integer",
                    row_id=row.get("bin", ""),
                    field="pair_count",
                    value=count_value,
                )
                continue
            if int(count_value) < 30:
                sparse_bin_count += 1
                if row.get("minimum_sample_caveat") != "sparse_bin":
                    add_issue(
                        report,
                        "ERROR",
                        "sparse_bin_unflagged",
                        "bins with fewer than 30 pairs must be flagged",
                        row_id=row.get("bin", ""),
                    )

    missing_figures = []
    for figure in REQUIRED_FIGURES:
        path = args.figure_dir / figure
        if not path.exists() or path.stat().st_size == 0:
            missing_figures.append(figure)
            add_issue(report, "ERROR", "missing_figure", f"missing or empty figure: {figure}", file=str(path))

    error_count = sum(1 for issue in report if issue["severity"] == "ERROR")
    warning_count = sum(1 for issue in report if issue["severity"] == "WARN")
    status = "PASS" if error_count == 0 else "FAIL"

    summary_lines = [
        status,
        f"input_eligible_pair_count: {input_eligible_count}",
        f"score_pair_count: {len(score_rows)}",
        f"missing_visual_score_count: {missing_visual_score_count}",
        f"invalid_numeric_score_count: {invalid_numeric_count}",
        f"invalid_score_range_count: {invalid_range_count}",
        f"label_issue_count: {label_issue_count}",
        f"descriptor_reference_issue_count: {descriptor_note_issue_count}",
        f"leakage_issue_count: {leakage_issue_count}",
        f"sparse_bin_count: {sparse_bin_count}",
        f"missing_figure_count: {len(missing_figures)}",
        f"error_count: {error_count}",
        f"warning_count: {warning_count}",
    ]
    args.summary_txt.parent.mkdir(parents=True, exist_ok=True)
    args.summary_txt.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    write_csv(args.report_csv, report, REPORT_FIELDS)

    print(status)
    for line in summary_lines[1:]:
        print(line)
    return 0 if status == "PASS" else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-csv", type=Path, default=INPUT_CSV)
    parser.add_argument("--scores-csv", type=Path, default=SCORES_CSV)
    parser.add_argument("--summary-csv", type=Path, default=SUMMARY_CSV)
    parser.add_argument("--driver-csv", type=Path, default=DRIVER_CSV)
    parser.add_argument("--risk-bins-csv", type=Path, default=RISK_BINS_CSV)
    parser.add_argument("--figure-dir", type=Path, default=FIGURE_DIR)
    parser.add_argument("--summary-txt", type=Path, default=SUMMARY_TXT)
    parser.add_argument("--report-csv", type=Path, default=REPORT_CSV)
    return parser.parse_args()


def main() -> int:
    return audit(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
