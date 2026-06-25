#!/usr/bin/env python3
"""Audit the Phase 7A harmonized 1000-image annotation table."""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT_CSV = (
    PROJECT_ROOT / "data/labels/czechlynx/czechlynx_phase7a_1000_image_annotations_working.csv"
)
DEFAULT_REPORT_CSV = PROJECT_ROOT / "outputs/czechlynx/qc/phase7a_1000_image_annotation_audit_report.csv"
DEFAULT_SUMMARY_TXT = PROJECT_ROOT / "outputs/czechlynx/qc/phase7a_1000_image_annotation_audit_summary.txt"

REQUIRED_COLUMNS = [
    "phase7_image_id",
    "source_phase",
    "source_image_id",
    "expanded_image_id",
    "review_image_path_local",
    "batch_id",
    "quality_bucket",
    "selection_stratum",
    "pattern_visibility",
    "side_visibility",
    "side_evidence_quality",
    "body_fraction_visible",
    "partial_body",
    "frontal_or_rear_view",
    "silhouette_only",
    "blur_level",
    "occlusion_level",
    "lighting_condition",
    "night_ir_artifact",
    "contrast_level",
    "primary_limiting_factor",
    "uncertainty_flag",
    "annotation_status",
    "annotator_notes",
]

EXPECTED_SOURCE_COUNTS = {
    "phase4_original_500": 500,
    "phase6_v2_balanced_500": 500,
}

ALLOWED_VALUES = {
    "source_phase": {"phase4_original_500", "phase6_v2_balanced_500"},
    "pattern_visibility": {"high", "medium", "low", "none", "unknown"},
    "side_visibility": {"left", "right", "both", "frontal", "rear", "unknown"},
    "side_evidence_quality": {"high", "medium", "low", "none", "unknown"},
    "body_fraction_visible": {"0_25", "26_50", "51_75", "76_100", "unknown"},
    "partial_body": {"yes", "no", "unknown"},
    "frontal_or_rear_view": {"yes", "no", "unknown"},
    "silhouette_only": {"yes", "no", "unknown"},
    "blur_level": {"none", "mild", "moderate", "severe", "unknown"},
    "occlusion_level": {"none", "partial", "major", "unknown"},
    "lighting_condition": {
        "normal",
        "low_light",
        "night_ir",
        "overexposed",
        "underexposed",
        "mixed",
        "unknown",
    },
    "night_ir_artifact": {"yes", "no", "unknown"},
    "contrast_level": {"good", "low", "not_available", "unknown"},
    "primary_limiting_factor": {
        "none",
        "blur",
        "occlusion",
        "frontal_or_rear_view",
        "low_contrast",
        "night_ir_artifact",
        "overexposed",
        "underexposed",
        "partial_body",
        "pattern_not_visible",
        "side_unknown",
        "side_non_comparable",
        "silhouette",
        "other",
        "unknown",
    },
    "uncertainty_flag": {"yes", "no"},
    "annotation_status": {"complete", "needs_review"},
}

FORBIDDEN_HEADERS = {
    "unique_name",
    "latitude",
    "longitude",
    "trap_id",
    "cell_code",
    "location",
    "internal_id",
    "working_id",
    "working_individual_id",
    "true_id",
    "local_image_path",
    "path",
}

FORBIDDEN_VALUE_PATTERNS = [
    re.compile(r"/Users/", re.IGNORECASE),
    re.compile(r"data/raw", re.IGNORECASE),
    re.compile(r"unique_name", re.IGNORECASE),
    re.compile(r"\btrap_id\b", re.IGNORECASE),
    re.compile(r"\bcell_code\b", re.IGNORECASE),
    re.compile(r"\blatitude\b", re.IGNORECASE),
    re.compile(r"\blongitude\b", re.IGNORECASE),
    re.compile(r"(?<![A-Za-z])lynx_[0-9]+", re.IGNORECASE),
]

PENDING_STATUSES = {"", "pending", "in_progress"}

REPORT_FIELDS = [
    "severity",
    "issue_type",
    "row_number",
    "phase7_image_id",
    "source_phase",
    "field",
    "value",
    "message",
]


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader), list(reader.fieldnames or [])


def write_report(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=REPORT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def add_issue(
    report_rows: list[dict[str, str]],
    severity: str,
    issue_type: str,
    message: str,
    *,
    row_number: int | str = "",
    row: dict[str, str] | None = None,
    field: str = "",
    value: str = "",
) -> None:
    report_rows.append(
        {
            "severity": severity,
            "issue_type": issue_type,
            "row_number": str(row_number),
            "phase7_image_id": "" if row is None else row.get("phase7_image_id", ""),
            "source_phase": "" if row is None else row.get("source_phase", ""),
            "field": field,
            "value": value,
            "message": message,
        }
    )


def resolve_image_path(value: str) -> Path:
    return PROJECT_ROOT / value


def scan_leakage(
    rows: list[dict[str, str]],
    headers: list[str],
    report_rows: list[dict[str, str]],
) -> int:
    count = 0
    for header in headers:
        if header in FORBIDDEN_HEADERS:
            count += 1
            add_issue(report_rows, "ERROR", "leakage_header", f"forbidden header: {header}", field=header)
    for row_number, row in enumerate(rows, start=2):
        for field, value in row.items():
            if field == "review_image_path_local":
                patterns = FORBIDDEN_VALUE_PATTERNS[:2]
            elif field.startswith("source_") and field.endswith("_original"):
                patterns = FORBIDDEN_VALUE_PATTERNS
            else:
                patterns = FORBIDDEN_VALUE_PATTERNS
            for pattern in patterns:
                if pattern.search(value or ""):
                    count += 1
                    add_issue(
                        report_rows,
                        "ERROR",
                        "leakage_value",
                        f"forbidden value pattern matched: {pattern.pattern}",
                        row_number=row_number,
                        row=row,
                        field=field,
                        value=value,
                    )
                    break
    return count


def audit(input_csv: Path, report_csv: Path, summary_txt: Path) -> int:
    rows, headers = read_csv(input_csv)
    report_rows: list[dict[str, str]] = []

    row_count = len(rows)
    source_counts = Counter(row.get("source_phase", "") for row in rows)
    phase4_count = source_counts.get("phase4_original_500", 0)
    phase6_v2_count = source_counts.get("phase6_v2_balanced_500", 0)

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in headers]
    missing_required_count = 0
    invalid_value_count = 0
    missing_image_count = 0
    logic_warning_count = 0
    mapping_warning_count = 0

    if row_count != 1000:
        add_issue(report_rows, "ERROR", "row_count", f"expected 1000 rows, found {row_count}")

    for source_phase, expected in EXPECTED_SOURCE_COUNTS.items():
        observed = source_counts.get(source_phase, 0)
        if observed != expected:
            add_issue(
                report_rows,
                "ERROR",
                "source_count",
                f"expected {expected} rows for {source_phase}, found {observed}",
                field="source_phase",
                value=source_phase,
            )

    for column in missing_columns:
        add_issue(report_rows, "ERROR", "missing_column", f"missing required column: {column}", field=column)
        missing_required_count += 1

    if not missing_columns:
        required_value_columns = [column for column in REQUIRED_COLUMNS if column != "annotator_notes"]
        for row_number, row in enumerate(rows, start=2):
            for column in required_value_columns:
                if row.get(column, "") == "":
                    missing_required_count += 1
                    add_issue(
                        report_rows,
                        "ERROR",
                        "missing_required_value",
                        f"missing required value in {column}",
                        row_number=row_number,
                        row=row,
                        field=column,
                    )

    phase7_ids = [row.get("phase7_image_id", "") for row in rows]
    duplicate_phase7_image_id_count = sum(count - 1 for count in Counter(phase7_ids).values() if count > 1)
    if duplicate_phase7_image_id_count:
        duplicates = sorted(key for key, count in Counter(phase7_ids).items() if count > 1)
        add_issue(
            report_rows,
            "ERROR",
            "duplicate_phase7_image_id",
            f"duplicate phase7_image_id values: {duplicates[:10]}",
        )

    source_keys = [(row.get("source_phase", ""), row.get("source_image_id", "")) for row in rows]
    duplicate_source_image_id_count = sum(count - 1 for count in Counter(source_keys).values() if count > 1)
    if duplicate_source_image_id_count:
        duplicates = sorted(key for key, count in Counter(source_keys).items() if count > 1)
        add_issue(
            report_rows,
            "ERROR",
            "duplicate_source_image_id",
            f"duplicate source image rows: {duplicates[:10]}",
        )

    pending_count = 0
    needs_review_count = 0
    for row_number, row in enumerate(rows, start=2):
        status = row.get("annotation_status", "")
        if status in PENDING_STATUSES:
            pending_count += 1
            add_issue(
                report_rows,
                "ERROR",
                "pending_annotation",
                f"pending annotation status: {status}",
                row_number=row_number,
                row=row,
                field="annotation_status",
                value=status,
            )
        if status == "needs_review":
            needs_review_count += 1
            logic_warning_count += 1
            add_issue(
                report_rows,
                "WARNING",
                "needs_review_status",
                "row remains marked needs_review in source annotation",
                row_number=row_number,
                row=row,
                field="annotation_status",
                value=status,
            )

    for row_number, row in enumerate(rows, start=2):
        for field, allowed in ALLOWED_VALUES.items():
            value = row.get(field, "")
            if value not in allowed:
                invalid_value_count += 1
                add_issue(
                    report_rows,
                    "ERROR",
                    "invalid_value",
                    f"invalid value for {field}: {value}",
                    row_number=row_number,
                    row=row,
                    field=field,
                    value=value,
                )

    for row_number, row in enumerate(rows, start=2):
        image_path = resolve_image_path(row.get("review_image_path_local", ""))
        if not image_path.exists():
            missing_image_count += 1
            add_issue(
                report_rows,
                "ERROR",
                "missing_image",
                f"image path does not resolve relative to repo root: {row.get('review_image_path_local', '')}",
                row_number=row_number,
                row=row,
                field="review_image_path_local",
                value=row.get("review_image_path_local", ""),
            )

    for row_number, row in enumerate(rows, start=2):
        mapping_notes = row.get("mapping_notes", "")
        if row.get("source_phase") == "phase4_original_500" and not mapping_notes:
            mapping_warning_count += 1
            add_issue(
                report_rows,
                "WARNING",
                "missing_mapping_notes",
                "Phase 4 row lacks mapping notes",
                row_number=row_number,
                row=row,
                field="mapping_notes",
            )
        for marker in [
            "not_available",
            "collapsed",
            "mapped_to",
            "preserved_as_phase7_specific_state",
            "assigned_phase4_original_500",
        ]:
            if marker in mapping_notes:
                mapping_warning_count += 1
                add_issue(
                    report_rows,
                    "WARNING",
                    "mapping_warning",
                    f"mapping note contains {marker}",
                    row_number=row_number,
                    row=row,
                    field="mapping_notes",
                    value=marker,
                )
                break

    leakage_issue_count = scan_leakage(rows, headers, report_rows)

    error_count = sum(1 for issue in report_rows if issue["severity"] == "ERROR")
    result = "PASS" if error_count == 0 else "FAIL"

    write_report(report_csv, report_rows)
    summary_txt.parent.mkdir(parents=True, exist_ok=True)
    input_display = input_csv.relative_to(PROJECT_ROOT) if input_csv.is_relative_to(PROJECT_ROOT) else input_csv
    report_display = report_csv.relative_to(PROJECT_ROOT) if report_csv.is_relative_to(PROJECT_ROOT) else report_csv
    summary_lines = [
        "Phase 7A 1000-image annotation audit summary",
        "",
        f"input_csv: {input_display}",
        f"result: {result}",
        f"row_count: {row_count}",
        f"phase4_count: {phase4_count}",
        f"phase6_v2_count: {phase6_v2_count}",
        f"duplicate_phase7_image_id_count: {duplicate_phase7_image_id_count}",
        f"duplicate_source_image_id_count: {duplicate_source_image_id_count}",
        f"pending_count: {pending_count}",
        f"needs_review_count: {needs_review_count}",
        f"invalid_value_count: {invalid_value_count}",
        f"missing_required_count: {missing_required_count}",
        f"missing_image_count: {missing_image_count}",
        f"leakage_issue_count: {leakage_issue_count}",
        f"mapping_warning_count: {mapping_warning_count}",
        f"logic_warning_count: {logic_warning_count}",
        f"report_csv: {report_display}",
    ]
    summary_txt.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    print("\n".join(summary_lines))
    return 0 if result == "PASS" else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-csv", type=Path, default=DEFAULT_INPUT_CSV)
    parser.add_argument("--report-csv", type=Path, default=DEFAULT_REPORT_CSV)
    parser.add_argument("--summary-txt", type=Path, default=DEFAULT_SUMMARY_TXT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return audit(args.input_csv.resolve(), args.report_csv.resolve(), args.summary_txt.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
