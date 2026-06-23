#!/usr/bin/env python3
"""Audit the Phase 7A 1000-image pair-level evidence table."""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

MASTER_CSV = PROJECT_ROOT / "data/labels/czechlynx/czechlynx_phase7a_1000_image_annotations_v1.csv"
PAIR_TABLE_CSV = PROJECT_ROOT / "outputs/czechlynx/phase7a/pair_tables/phase7a_1000_image_pair_table_working.csv"
SUMMARY_TXT = PROJECT_ROOT / "outputs/czechlynx/qc/phase7a_1000_image_pair_table_audit_summary.txt"
REPORT_CSV = PROJECT_ROOT / "outputs/czechlynx/qc/phase7a_1000_image_pair_table_audit_report.csv"

VISUAL_FACTORS = [
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
    "quality_bucket",
    "selection_stratum",
]

REQUIRED_COLUMNS = [
    "pair_id",
    "image_id_a",
    "image_id_b",
    "source_image_id_a",
    "source_image_id_b",
    "expanded_image_id_a",
    "expanded_image_id_b",
    "source_phase_a",
    "source_phase_b",
    "source_pair_origin",
    "same_identity",
    "pair_label_available",
    "resnet50_similarity",
    "megadescriptor_similarity",
    "descriptor_available",
    *[f"{factor}_a" for factor in VISUAL_FACTORS],
    *[f"{factor}_b" for factor in VISUAL_FACTORS],
    "pair_source_phase_type",
    "pair_annotation_status",
    "pair_has_needs_review",
    "pair_has_uncertainty",
    "pair_has_missing_mapping",
    "pair_visual_completeness_class",
    "pair_pattern_min",
    "pair_pattern_max",
    "pair_side_model_class_a",
    "pair_side_model_class_b",
    "pair_view_model_class_a",
    "pair_view_model_class_b",
    "pair_side_compatible",
    "pair_has_side_unknown",
    "pair_has_frontal_or_rear",
    "pair_body_fraction_min",
    "pair_has_partial_body",
    "pair_blur_worst",
    "pair_occlusion_worst",
    "pair_lighting_worst",
    "pair_contrast_worst",
    "pair_has_night_ir_artifact",
    "pair_primary_limiting_factor_combined",
    "pair_modeling_eligible",
    "pair_exclusion_reason",
]

ALLOWED_VALUES = {
    "same_identity": {"yes", "no"},
    "pair_label_available": {"yes", "no"},
    "descriptor_available": {"yes", "no"},
    "pair_source_phase_type": {"phase4_phase4", "phase6_phase6", "cross_phase"},
    "pair_annotation_status": {"complete", "needs_review", "mixed_or_unknown"},
    "pair_has_needs_review": {"yes", "no"},
    "pair_has_uncertainty": {"yes", "no"},
    "pair_has_missing_mapping": {"yes", "no"},
    "pair_visual_completeness_class": {
        "core_complete",
        "core_complete_with_mapping_caveat",
        "core_visual_fields_with_unknown",
        "needs_review",
    },
    "pair_side_model_class_a": {"left", "right", "both", "unknown_or_non_side"},
    "pair_side_model_class_b": {"left", "right", "both", "unknown_or_non_side"},
    "pair_view_model_class_a": {"side", "frontal_or_rear", "unknown"},
    "pair_view_model_class_b": {"side", "frontal_or_rear", "unknown"},
    "pair_side_compatible": {"yes", "no", "unknown"},
    "pair_has_side_unknown": {"yes", "no"},
    "pair_has_frontal_or_rear": {"yes", "no"},
    "pair_has_partial_body": {"yes", "no"},
    "pair_has_night_ir_artifact": {"yes", "no"},
    "pair_modeling_eligible": {"yes", "no"},
}

FORBIDDEN_HEADERS = {
    "unique_name",
    "latitude",
    "longitude",
    "trap_id",
    "cell_code",
    "location",
    "working_individual_id",
    "true_id",
    "path",
}

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

REPORT_FIELDS = [
    "severity",
    "issue_type",
    "pair_id",
    "field",
    "value",
    "message",
]


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
    pair_id: str = "",
    field: str = "",
    value: str = "",
) -> None:
    report.append(
        {
            "severity": severity,
            "issue_type": issue_type,
            "pair_id": pair_id,
            "field": field,
            "value": value,
            "message": message,
        }
    )


def is_float(value: str) -> bool:
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True


def expected_side_model(side_visibility: str) -> str:
    if side_visibility in {"left", "right", "both"}:
        return side_visibility
    return "unknown_or_non_side"


def expected_view_model(side_visibility: str) -> str:
    if side_visibility in {"left", "right", "both"}:
        return "side"
    if side_visibility in {"frontal", "rear"}:
        return "frontal_or_rear"
    return "unknown"


def expected_side_compatible(side_a: str, side_b: str) -> str:
    if "unknown_or_non_side" in {side_a, side_b}:
        return "unknown"
    if side_a == side_b:
        return "yes"
    if side_a == "both" and side_b in {"left", "right", "both"}:
        return "yes"
    if side_b == "both" and side_a in {"left", "right", "both"}:
        return "yes"
    if {side_a, side_b} == {"left", "right"}:
        return "no"
    return "unknown"


def audit(master_csv: Path, pair_table_csv: Path, summary_txt: Path, report_csv: Path) -> int:
    master_rows, _ = read_csv(master_csv)
    pair_rows, headers = read_csv(pair_table_csv)
    master_ids = {row["phase7_image_id"] for row in master_rows}
    master_expanded_ids = {row["expanded_image_id"] for row in master_rows}
    report: list[dict[str, str]] = []

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in headers]
    for column in missing_columns:
        add_issue(report, "ERROR", "missing_column", f"missing required column: {column}", field=column)

    pair_count = len(pair_rows)
    if pair_count <= 0:
        add_issue(report, "ERROR", "pair_count", "pair row count must be greater than zero")

    duplicate_pair_id_count = sum(count - 1 for count in Counter(row.get("pair_id", "") for row in pair_rows).values() if count > 1)
    if duplicate_pair_id_count:
        add_issue(report, "ERROR", "duplicate_pair_id", f"duplicate pair IDs: {duplicate_pair_id_count}")

    self_pair_count = 0
    reversed_duplicate_count = 0
    seen_unordered: set[tuple[str, str]] = set()
    missing_image_count = 0
    invalid_value_count = 0
    leakage_issue_count = 0
    logic_warning_count = 0

    for header in headers:
        if header in FORBIDDEN_HEADERS:
            leakage_issue_count += 1
            add_issue(report, "ERROR", "leakage_header", f"forbidden header present: {header}", field=header)

    for row in pair_rows:
        pair_id = row.get("pair_id", "")
        image_a = row.get("image_id_a", "")
        image_b = row.get("image_id_b", "")
        expanded_a = row.get("expanded_image_id_a", "")
        expanded_b = row.get("expanded_image_id_b", "")

        if image_a == image_b or expanded_a == expanded_b:
            self_pair_count += 1
            add_issue(report, "ERROR", "self_pair", "self-pair found", pair_id=pair_id)

        unordered = tuple(sorted([image_a, image_b]))
        if unordered in seen_unordered:
            reversed_duplicate_count += 1
            add_issue(report, "ERROR", "reversed_duplicate", "duplicate unordered image pair found", pair_id=pair_id)
        seen_unordered.add(unordered)

        for field, value, allowed_set in [
            ("image_id_a", image_a, master_ids),
            ("image_id_b", image_b, master_ids),
            ("expanded_image_id_a", expanded_a, master_expanded_ids),
            ("expanded_image_id_b", expanded_b, master_expanded_ids),
        ]:
            if value not in allowed_set:
                missing_image_count += 1
                add_issue(report, "ERROR", "missing_image", f"{field} not found in 1000-image master", pair_id=pair_id, field=field, value=value)

        for field in ["resnet50_similarity", "megadescriptor_similarity"]:
            value = row.get(field, "")
            if value != "" and not is_float(value):
                invalid_value_count += 1
                add_issue(report, "ERROR", "invalid_similarity", f"{field} is not numeric", pair_id=pair_id, field=field, value=value)

        for field, allowed in ALLOWED_VALUES.items():
            value = row.get(field, "")
            if value not in allowed:
                invalid_value_count += 1
                add_issue(report, "ERROR", "invalid_value", f"invalid {field}: {value}", pair_id=pair_id, field=field, value=value)

        for suffix in ["a", "b"]:
            side_visibility = row.get(f"side_visibility_{suffix}", "")
            side_field = f"pair_side_model_class_{suffix}"
            view_field = f"pair_view_model_class_{suffix}"
            if row.get(side_field) != expected_side_model(side_visibility):
                invalid_value_count += 1
                add_issue(report, "ERROR", "invalid_side_model_class", "side model class mismatch", pair_id=pair_id, field=side_field, value=row.get(side_field, ""))
            if row.get(view_field) != expected_view_model(side_visibility):
                invalid_value_count += 1
                add_issue(report, "ERROR", "invalid_view_model_class", "view model class mismatch", pair_id=pair_id, field=view_field, value=row.get(view_field, ""))

        expected_compat = expected_side_compatible(row.get("pair_side_model_class_a", ""), row.get("pair_side_model_class_b", ""))
        if row.get("pair_side_compatible") != expected_compat:
            invalid_value_count += 1
            add_issue(report, "ERROR", "invalid_side_compatible", "pair side compatibility mismatch", pair_id=pair_id, field="pair_side_compatible", value=row.get("pair_side_compatible", ""))

        eligible = row.get("pair_modeling_eligible", "")
        reason = row.get("pair_exclusion_reason", "")
        if eligible == "yes" and reason != "none":
            invalid_value_count += 1
            add_issue(report, "ERROR", "invalid_eligibility", "eligible pair has non-none exclusion reason", pair_id=pair_id)
        if eligible == "no" and reason in {"", "none"}:
            invalid_value_count += 1
            add_issue(report, "ERROR", "invalid_eligibility", "ineligible pair lacks exclusion reason", pair_id=pair_id)

        if row.get("descriptor_available") == "yes" and (
            row.get("resnet50_similarity", "") == "" or row.get("megadescriptor_similarity", "") == ""
        ):
            invalid_value_count += 1
            add_issue(report, "ERROR", "invalid_descriptor_available", "descriptor_available=yes but a descriptor is missing", pair_id=pair_id)

        for field, value in row.items():
            for pattern in FORBIDDEN_PATTERNS:
                if pattern.search(value or ""):
                    leakage_issue_count += 1
                    add_issue(report, "ERROR", "leakage_value", f"forbidden value pattern matched: {pattern.pattern}", pair_id=pair_id, field=field, value=value)
                    break

    eligible_pair_count = sum(row.get("pair_modeling_eligible") == "yes" for row in pair_rows)
    truth_label_available_count = sum(row.get("pair_label_available") == "yes" for row in pair_rows)
    descriptor_available_count = sum(row.get("descriptor_available") == "yes" for row in pair_rows)
    same_pair_count = sum(row.get("same_identity") == "yes" for row in pair_rows)
    different_pair_count = sum(row.get("same_identity") == "no" for row in pair_rows)
    phase4_phase4_pair_count = sum(row.get("pair_source_phase_type") == "phase4_phase4" for row in pair_rows)
    phase6_phase6_pair_count = sum(row.get("pair_source_phase_type") == "phase6_phase6" for row in pair_rows)
    cross_phase_pair_count = sum(row.get("pair_source_phase_type") == "cross_phase" for row in pair_rows)

    if phase6_phase6_pair_count == 0 and cross_phase_pair_count == 0:
        logic_warning_count += 1
        add_issue(report, "WARNING", "phase6_pair_coverage", "Phase 6 v2 images do not currently contribute pair-labeled evidence")

    error_count = sum(1 for issue in report if issue["severity"] == "ERROR")
    result = "PASS" if error_count == 0 else "FAIL"

    write_csv(report_csv, report, REPORT_FIELDS)
    summary_lines = [
        "Phase 7A 1000-image pair table audit summary",
        "",
        f"result: {result}",
        f"pair_count: {pair_count}",
        f"eligible_pair_count: {eligible_pair_count}",
        f"truth_label_available_count: {truth_label_available_count}",
        f"descriptor_available_count: {descriptor_available_count}",
        f"same_pair_count: {same_pair_count}",
        f"different_pair_count: {different_pair_count}",
        f"phase4_phase4_pair_count: {phase4_phase4_pair_count}",
        f"phase6_phase6_pair_count: {phase6_phase6_pair_count}",
        f"cross_phase_pair_count: {cross_phase_pair_count}",
        f"duplicate_pair_id_count: {duplicate_pair_id_count}",
        f"self_pair_count: {self_pair_count}",
        f"reversed_duplicate_count: {reversed_duplicate_count}",
        f"missing_image_count: {missing_image_count}",
        f"invalid_value_count: {invalid_value_count}",
        f"leakage_issue_count: {leakage_issue_count}",
        f"logic_warning_count: {logic_warning_count}",
        f"report_csv: {report_csv.relative_to(PROJECT_ROOT)}",
    ]
    summary_txt.parent.mkdir(parents=True, exist_ok=True)
    summary_txt.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    print("\n".join(summary_lines))
    return 0 if result == "PASS" else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master-csv", type=Path, default=MASTER_CSV)
    parser.add_argument("--pair-table-csv", type=Path, default=PAIR_TABLE_CSV)
    parser.add_argument("--summary-txt", type=Path, default=SUMMARY_TXT)
    parser.add_argument("--report-csv", type=Path, default=REPORT_CSV)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return audit(
        args.master_csv.resolve(),
        args.pair_table_csv.resolve(),
        args.summary_txt.resolve(),
        args.report_csv.resolve(),
    )


if __name__ == "__main__":
    raise SystemExit(main())
