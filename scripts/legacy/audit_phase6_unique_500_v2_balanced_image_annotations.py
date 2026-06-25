#!/usr/bin/env python3
"""Audit the Phase 6 unique-500 v2 balanced image annotation workflow."""

from __future__ import annotations

import argparse
import csv
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_NAME = "phase6_unique_500_v2_balanced"
WORKING_CSV = PROJECT_ROOT / f"data/labels/czechlynx/czechlynx_{WORKFLOW_NAME}_image_annotation_working.csv"
MAPPING_CSV = PROJECT_ROOT / f"data/interim/czechlynx/czechlynx_{WORKFLOW_NAME}_review_mapping_internal.csv"
REVIEW_IMAGE_DIR = PROJECT_ROOT / f"data/review_images/czechlynx/{WORKFLOW_NAME}"
PACKAGE_ROOT = PROJECT_ROOT / f"outputs/czechlynx/phase6/annotation_review_packages/{WORKFLOW_NAME}"
QC_SELECTION_REPORT = PROJECT_ROOT / f"outputs/czechlynx/qc/{WORKFLOW_NAME}_selection_qc_report.txt"
AUDIT_SUMMARY = PROJECT_ROOT / f"outputs/czechlynx/qc/{WORKFLOW_NAME}_annotation_audit_summary.txt"
AUDIT_REPORT = PROJECT_ROOT / f"outputs/czechlynx/qc/{WORKFLOW_NAME}_annotation_audit_report.csv"
LEAKAGE_REPORT = PROJECT_ROOT / f"outputs/czechlynx/qc/{WORKFLOW_NAME}_leakage_scan_report.txt"

TARGET_BOUNDS = {
    "high_evidence_proxy": (125, 175),
    "medium_evidence_proxy": (150, 200),
    "low_but_annotatable_proxy": (100, 125),
    "extreme_hard_proxy": (0, 75),
}

REQUIRED_FIELDS = [
    "expanded_image_id",
    "review_image_path_local",
    "candidate_source_id",
    "candidate_reason",
    "selection_stratum",
    "quality_bucket",
    "batch_id",
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

FINAL_ALLOWED_VALUES = {
    "pattern_visibility": {"high", "medium", "low", "none"},
    "side_visibility": {"left", "right", "unknown"},
    "side_evidence_quality": {"high", "medium", "low", "none"},
    "body_fraction_visible": {"0_25", "26_50", "51_75", "76_100"},
    "partial_body": {"yes", "no"},
    "frontal_or_rear_view": {"yes", "no", "unknown"},
    "silhouette_only": {"yes", "no"},
    "blur_level": {"none", "mild", "moderate", "severe"},
    "occlusion_level": {"none", "partial", "major"},
    "lighting_condition": {"normal", "overexposed", "underexposed", "mixed"},
    "night_ir_artifact": {"yes", "no"},
    "contrast_level": {"good", "low"},
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
        "silhouette",
        "other",
    },
    "uncertainty_flag": {"yes", "no"},
    "annotation_status": {"complete", "needs_review"},
}

SELECTION_ALLOWED_VALUES = {
    field: values | {""}
    for field, values in FINAL_ALLOWED_VALUES.items()
}
SELECTION_ALLOWED_VALUES["annotation_status"] = {"pending", "complete", "needs_review", "in_progress", ""}

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
    re.compile(r"lynx_[0-9]+", re.IGNORECASE),
    re.compile(r"/Users/", re.IGNORECASE),
    re.compile(r"data/raw", re.IGNORECASE),
]
RAW_LYNX_RE = re.compile(r"lynx_[0-9]+", re.IGNORECASE)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def grouped(rows: list[dict[str, str]], key: str) -> dict[str, list[dict[str, str]]]:
    out: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        out[row[key]].append(row)
    return out


def add_report(
    report_rows: list[dict[str, str]],
    severity: str,
    issue_type: str,
    message: str,
    row_number: int | str = "",
    expanded_image_id: str = "",
    field: str = "",
    value: str = "",
) -> None:
    report_rows.append(
        {
            "severity": severity,
            "issue_type": issue_type,
            "row_number": str(row_number),
            "expanded_image_id": expanded_image_id,
            "field": field,
            "value": value,
            "message": message,
        }
    )


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def scan_final_annotation_rows(rows: list[dict[str, str]]) -> list[str]:
    issues: list[str] = []
    allowed_operational_fields = {
        "expanded_image_id",
        "review_image_path_local",
        "candidate_source_id",
        "candidate_reason",
        "selection_stratum",
        "quality_bucket",
        "batch_id",
        "imported_range_id",
        "correction_applied",
    }
    for header in rows[0].keys():
        if header in allowed_operational_fields:
            continue
        if header in FORBIDDEN_HEADERS:
            issues.append(f"forbidden header: {header}")
    for row_number, row in enumerate(rows, start=2):
        for field, value in row.items():
            if field == "review_image_path_local":
                if "/Users/" in value or "data/raw" in value:
                    issues.append(f"row {row_number} forbidden path value in {field}")
                continue
            for pattern in FORBIDDEN_VALUE_PATTERNS:
                if pattern.search(value):
                    issues.append(f"row {row_number} forbidden value in {field}")
                    break
    return issues


def resolve_review_image_path(value: str) -> tuple[Path, bool]:
    """Resolve final review-image paths without treating package images/ as root."""
    candidate = PROJECT_ROOT / value
    if candidate.exists():
        return candidate, False
    fallback = REVIEW_IMAGE_DIR / Path(value).name
    if fallback.exists():
        return fallback, True
    return candidate, False


def audit(final: bool = False) -> tuple[bool, list[str], dict[str, object]]:
    issues: list[str] = []
    report_rows: list[dict[str, str]] = []
    rows = read_csv(WORKING_CSV)
    mapping = read_csv(MAPPING_CSV)
    if len(rows) != 500:
        message = f"expected 500 working rows, found {len(rows)}"
        issues.append(message)
        add_report(report_rows, "ERROR", "row_count", message)
    if len(mapping) != 500:
        message = f"expected 500 mapping rows, found {len(mapping)}"
        issues.append(message)
        add_report(report_rows, "ERROR", "mapping_count", message)
    image_count = len(list(REVIEW_IMAGE_DIR.glob("*.jpg")))
    if image_count != 500:
        message = f"expected 500 copied images, found {image_count}"
        issues.append(message)
        add_report(report_rows, "ERROR", "image_count", message)

    missing = [field for field in REQUIRED_FIELDS if field not in rows[0]]
    if missing:
        message = f"missing required fields: {missing}"
        issues.append(message)
        add_report(report_rows, "ERROR", "missing_required_fields", message)

    quality_counts = Counter(row["quality_bucket"] for row in rows)
    for bucket, (lo, hi) in TARGET_BOUNDS.items():
        value = quality_counts.get(bucket, 0)
        if not (lo <= value <= hi):
            message = f"quality bucket {bucket} count {value} outside {lo}-{hi}"
            issues.append(message)
            add_report(report_rows, "ERROR", "quality_distribution", message, field="quality_bucket", value=bucket)

    batch_counts = Counter(row["batch_id"] for row in rows)
    if len(batch_counts) != 10:
        message = f"expected 10 batches, found {len(batch_counts)}"
        issues.append(message)
        add_report(report_rows, "ERROR", "batch_count", message)
    for batch_id, count in batch_counts.items():
        if count != 50:
            message = f"{batch_id} has {count} rows"
            issues.append(message)
            add_report(report_rows, "ERROR", "batch_size", message, field="batch_id", value=batch_id)

    batch_quality = {}
    for batch_id, batch_rows in grouped(rows, "batch_id").items():
        counts = Counter(row["quality_bucket"] for row in batch_rows)
        batch_quality[batch_id] = dict(counts)
        if counts.get("extreme_hard_proxy", 0) > 10:
            message = f"{batch_id} has more than 10 extreme hard images"
            issues.append(message)
            add_report(report_rows, "ERROR", "batch_extreme_hard_cap", message, field="batch_id", value=batch_id)
        if counts.get("extreme_hard_proxy", 0) > 25:
            message = f"{batch_id} dominated by extreme hard images"
            issues.append(message)
            add_report(report_rows, "ERROR", "batch_extreme_hard_dominance", message, field="batch_id", value=batch_id)

    mapping_by_id = {row["expanded_image_id"]: row for row in mapping}
    near_by_batch = {}
    for batch_id, batch_rows in grouped(rows, "batch_id").items():
        near_count = 0
        for row in batch_rows:
            meta = mapping_by_id[row["expanded_image_id"]]
            if meta["near_black_flag"] == "yes" or meta["eye_shine_only_flag"] == "yes" or meta["almost_empty_flag"] == "yes":
                near_count += 1
        near_by_batch[batch_id] = near_count
        if near_count > 10:
            message = f"{batch_id} has more than 10 near-black/extreme-hard images"
            issues.append(message)
            add_report(report_rows, "ERROR", "batch_near_black_cap", message, field="batch_id", value=batch_id)

    pending_count = sum(1 for row in rows if row.get("annotation_status") == "pending")
    if final and pending_count:
        message = f"final audit found pending rows: {pending_count}"
        issues.append(message)
        add_report(report_rows, "ERROR", "pending_rows", message, field="annotation_status", value="pending")

    allowed_values = FINAL_ALLOWED_VALUES if final else SELECTION_ALLOWED_VALUES
    invalid_value_count = 0
    missing_image_count = 0
    logic_warning_count = 0
    for idx, row in enumerate(rows, start=2):
        expanded_image_id = row.get("expanded_image_id", "")
        for field, allowed in allowed_values.items():
            if row.get(field, "") not in allowed:
                invalid_value_count += 1
                message = f"invalid {field}={row.get(field)}"
                issues.append(f"row {idx} {message}")
                add_report(
                    report_rows,
                    "ERROR",
                    "invalid_value",
                    message,
                    row_number=idx,
                    expanded_image_id=expanded_image_id,
                    field=field,
                    value=row.get(field, ""),
                )
        if row.get("annotation_status") == "needs_review" and row.get("uncertainty_flag") != "yes":
            message = "needs_review requires uncertainty_flag=yes"
            issues.append(f"row {idx} {message}")
            add_report(report_rows, "ERROR", "needs_review_uncertainty", message, idx, expanded_image_id, "uncertainty_flag", row.get("uncertainty_flag", ""))
        if row.get("annotation_status") == "complete" and row.get("uncertainty_flag") == "yes":
            logic_warning_count += 1
            add_report(
                report_rows,
                "WARNING",
                "complete_with_uncertainty",
                "complete row has uncertainty_flag=yes; allowed but should be documented",
                idx,
                expanded_image_id,
                "uncertainty_flag",
                row.get("uncertainty_flag", ""),
            )
        if row.get("body_fraction_visible") in {"0_25", "26_50"} and row.get("partial_body") != "yes":
            logic_warning_count += 1
            add_report(report_rows, "WARNING", "partial_body_consistency", "low body fraction should usually have partial_body=yes", idx, expanded_image_id, "partial_body", row.get("partial_body", ""))
        if row.get("pattern_visibility") == "none" and row.get("side_evidence_quality") != "none":
            logic_warning_count += 1
            add_report(report_rows, "WARNING", "pattern_side_evidence_consistency", "pattern_visibility=none usually implies side_evidence_quality=none", idx, expanded_image_id, "side_evidence_quality", row.get("side_evidence_quality", ""))
        if row.get("side_visibility") == "unknown" and row.get("side_evidence_quality") == "high":
            notes = row.get("annotator_notes", "").strip()
            if not notes:
                logic_warning_count += 1
                add_report(report_rows, "WARNING", "unknown_side_high_evidence", "side_visibility=unknown should not be high without explanatory notes", idx, expanded_image_id, "side_evidence_quality", row.get("side_evidence_quality", ""))
        image_path, used_review_dir_fallback = resolve_review_image_path(row["review_image_path_local"])
        if used_review_dir_fallback:
            logic_warning_count += 1
            add_report(
                report_rows,
                "WARNING",
                "review_image_path_normalized",
                "review_image_path_local did not resolve from repo root; image found by basename in v2 review-image folder",
                idx,
                expanded_image_id,
                "review_image_path_local",
                row.get("review_image_path_local", ""),
            )
        if not image_path.exists():
            missing_image_count += 1
            message = f"missing review image {row['review_image_path_local']}"
            issues.append(f"row {idx} {message}")
            add_report(report_rows, "ERROR", "missing_image", message, idx, expanded_image_id, "review_image_path_local", row.get("review_image_path_local", ""))

    zip_issues = []
    for i in range(1, 11):
        zip_path = PACKAGE_ROOT / "batch_zips" / f"batch_{i:03d}.zip"
        if not zip_path.exists():
            zip_issues.append(f"missing {zip_path}")
            continue
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
            image_files = [name for name in names if name.startswith("images/") and name.lower().endswith(".jpg")]
            required = {"batch_manifest.csv", "batch_annotation_template.csv", "batch_review_protocol.md", "qc_report.txt"}
            if len(image_files) != 50:
                zip_issues.append(f"{zip_path.name} has {len(image_files)} images")
            missing_required = required - set(names)
            if missing_required:
                zip_issues.append(f"{zip_path.name} missing {sorted(missing_required)}")
    issues.extend(zip_issues)
    for zip_issue in zip_issues:
        add_report(report_rows, "ERROR", "batch_zip_integrity", zip_issue)

    leak_issues = scan_final_annotation_rows(rows)
    leakage_issue_count = len(leak_issues)
    if leak_issues:
        issues.extend(leak_issues)
        for leak_issue in leak_issues:
            add_report(report_rows, "ERROR", "leakage", leak_issue)
    leak_pass = not leak_issues

    summary = {
        "row_count": len(rows),
        "image_count": image_count,
        "quality_counts": dict(quality_counts),
        "batch_counts": dict(sorted(batch_counts.items())),
        "batch_quality": batch_quality,
        "near_black_extreme_by_batch": near_by_batch,
        "near_black_extreme_overall": sum(near_by_batch.values()),
        "pending_count": pending_count,
        "leakage_pass": leak_pass,
        "invalid_value_count": invalid_value_count,
        "missing_image_count": missing_image_count,
        "leakage_issue_count": leakage_issue_count,
        "logic_warning_count": logic_warning_count,
        "zip_issues": zip_issues,
    }
    write_csv(
        AUDIT_REPORT,
        report_rows,
        ["severity", "issue_type", "row_number", "expanded_image_id", "field", "value", "message"],
    )
    return not issues, issues, summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--final", action="store_true", help="enforce no pending rows")
    args = parser.parse_args()
    passed, issues, summary = audit(final=args.final)
    AUDIT_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "Phase 6 unique-500 v2 balanced annotation audit summary",
        "",
        f"mode: {'final' if args.final else 'selection'}",
        f"result: {'PASS' if passed else 'FAIL'}",
    ]
    lines.extend(f"{key}: {value}" for key, value in summary.items())
    lines.append(f"detailed_report: {AUDIT_REPORT.relative_to(PROJECT_ROOT)}")
    if issues:
        lines.append("issues:")
        lines.extend(f"- {issue}" for issue in issues)
    AUDIT_SUMMARY.write_text("\n".join(lines) + "\n", encoding="utf-8")
    LEAKAGE_REPORT.write_text(
        "\n".join(
            [
                "Phase 6 unique-500 v2 balanced leakage scan",
                "",
                f"result: {'PASS' if summary['leakage_pass'] else 'FAIL'}",
                f"leakage_issue_count: {summary['leakage_issue_count']}",
                "See annotation audit report for any leakage issues.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print("\n".join(lines[:12]))
    print(f"invalid_value_count: {summary['invalid_value_count']}")
    print(f"missing_image_count: {summary['missing_image_count']}")
    print(f"leakage_issue_count: {summary['leakage_issue_count']}")
    print(f"logic_warning_count: {summary['logic_warning_count']}")
    print(f"detailed_report: {AUDIT_REPORT.relative_to(PROJECT_ROOT)}")
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
