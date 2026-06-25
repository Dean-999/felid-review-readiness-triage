#!/usr/bin/env python3
"""Audit Phase 6 unique-500 image annotations and optionally freeze v1."""

from __future__ import annotations

import argparse
import csv
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from phase6_unique_500_annotation_schema import (  # noqa: E402
    ALLOWED_VALUES,
    ANNOTATION_FIELDS,
    COMPLETE_REQUIRED_FIELDS,
    EXPECTED_ROWS,
    FREEZE_CSV,
    PUBLIC_COLUMNS,
    WORKING_CSV,
    find_leakage_issues,
    path_is_safe_public_path,
)

AUDIT_REPORT_CSV = (
    PROJECT_ROOT / "outputs/czechlynx/qc/phase6_unique_500_annotation_audit_report.csv"
)
AUDIT_SUMMARY_TXT = (
    PROJECT_ROOT / "outputs/czechlynx/qc/phase6_unique_500_annotation_audit_summary.txt"
)
FREEZE_NOTE_DOC = PROJECT_ROOT / "docs/phase6/phase6_unique_500_annotation_freeze_v1_note.md"

DISTRIBUTION_FIELDS = [
    "pattern_visibility",
    "side_visibility",
    "side_evidence_quality",
    "body_fraction_visible",
    "blur_level",
    "occlusion_level",
    "lighting_condition",
    "night_ir_artifact",
    "contrast_level",
    "primary_limiting_factor",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit Phase 6 unique-500 image annotations.")
    parser.add_argument(
        "--input",
        "--input-csv",
        dest="input",
        type=Path,
        default=WORKING_CSV,
        help="Annotation CSV to audit",
    )
    parser.add_argument(
        "--report-out",
        type=Path,
        default=None,
        help="Optional audit report CSV output path",
    )
    parser.add_argument(
        "--summary-out",
        type=Path,
        default=None,
        help="Optional audit summary text output path",
    )
    parser.add_argument(
        "--freeze-if-pass",
        action="store_true",
        help="Copy working CSV to v1 freeze file only if audit passes",
    )
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(f)]


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def add_finding(
    findings: list[dict[str, str]],
    expanded_image_id: str,
    check_name: str,
    severity: str,
    message: str,
) -> None:
    findings.append(
        {
            "expanded_image_id": expanded_image_id,
            "check_name": check_name,
            "severity": severity,
            "message": message,
        }
    )


def audit_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []

    if len(rows) != EXPECTED_ROWS:
        add_finding(
            findings,
            "<dataset>",
            "row_count",
            "failure",
            f"Expected {EXPECTED_ROWS} rows, found {len(rows)}",
        )
        return findings

    entry_ids = [row.get("expanded_image_id", "") for row in rows]
    if len(set(entry_ids)) != EXPECTED_ROWS:
        add_finding(
            findings,
            "<dataset>",
            "unique_expanded_image_id",
            "failure",
            "expanded_image_id values are not all unique",
        )

    missing_columns = [col for col in PUBLIC_COLUMNS if col not in rows[0]]
    if missing_columns:
        add_finding(
            findings,
            "<dataset>",
            "required_columns",
            "failure",
            f"Missing columns: {', '.join(missing_columns)}",
        )
        return findings

    for row in rows:
        image_id = row["expanded_image_id"]
        image_rel = row["review_image_path_local"]
        image_path = PROJECT_ROOT / image_rel
        if not image_path.exists():
            add_finding(
                findings,
                image_id,
                "image_presence",
                "failure",
                f"Missing review image: {image_rel}",
            )

        status = row.get("annotation_status", "")
        uncertainty = row.get("uncertainty_flag", "")

        for field in ANNOTATION_FIELDS:
            value = row.get(field, "")
            if field == "annotator_notes":
                continue
            allowed = ALLOWED_VALUES.get(field)
            if allowed is None:
                continue
            if value and value not in allowed:
                add_finding(
                    findings,
                    image_id,
                    "allowed_values",
                    "failure",
                    f"{field}={value!r} is not allowed",
                )

        if status == "complete":
            for field in COMPLETE_REQUIRED_FIELDS:
                if not row.get(field, ""):
                    add_finding(
                        findings,
                        image_id,
                        "required_fields_complete",
                        "failure",
                        f"complete row has blank {field}",
                    )
            unknown_fields = [
                field
                for field in COMPLETE_REQUIRED_FIELDS
                if row.get(field, "") == "unknown" and not row.get("annotator_notes", "")
            ]
            if unknown_fields:
                add_finding(
                    findings,
                    image_id,
                    "complete_unknown_without_notes",
                    "warning",
                    f"complete row uses unknown for {', '.join(unknown_fields)} without notes",
                )

        if status == "needs_review" and uncertainty != "yes":
            add_finding(
                findings,
                image_id,
                "needs_review_uncertainty",
                "failure",
                "needs_review row must have uncertainty_flag=yes",
            )

        if uncertainty == "yes" and status != "needs_review":
            add_finding(
                findings,
                image_id,
                "uncertainty_status",
                "warning",
                "uncertainty_flag=yes should usually correspond to annotation_status=needs_review",
            )

        body_fraction = row.get("body_fraction_visible", "")
        partial_body = row.get("partial_body", "")
        if body_fraction in {"0_25", "26_50"} and partial_body not in {"yes", "unknown"}:
            add_finding(
                findings,
                image_id,
                "partial_body_consistency",
                "warning",
                f"body_fraction_visible={body_fraction} but partial_body={partial_body or '<blank>'}",
            )

        if row.get("silhouette_only", "") == "yes" and row.get("pattern_visibility", "") not in {
            "",
            "none",
            "low",
            "unknown",
        }:
            add_finding(
                findings,
                image_id,
                "silhouette_pattern_consistency",
                "warning",
                "silhouette_only=yes but pattern_visibility is not none/low/unknown",
            )

        if row.get("frontal_or_rear_view", "") == "yes" and row.get("side_visibility", "") not in {
            "",
            "unknown",
        }:
            add_finding(
                findings,
                image_id,
                "frontal_side_consistency",
                "warning",
                "frontal_or_rear_view=yes but side_visibility is not unknown",
            )

        if row.get("pattern_visibility", "") == "none" and row.get("side_evidence_quality", "") == "high":
            add_finding(
                findings,
                image_id,
                "pattern_side_quality_consistency",
                "warning",
                "pattern_visibility=none but side_evidence_quality=high",
            )

        if row.get("primary_limiting_factor", "") == "none":
            major_problems = []
            if row.get("blur_level", "") in {"moderate", "severe"}:
                major_problems.append("blur_level")
            if row.get("occlusion_level", "") == "major":
                major_problems.append("occlusion_level")
            if row.get("pattern_visibility", "") in {"none", "low"}:
                major_problems.append("pattern_visibility")
            if major_problems:
                add_finding(
                    findings,
                    image_id,
                    "primary_limiting_factor_consistency",
                    "warning",
                    f"primary_limiting_factor=none but major problems present: {', '.join(major_problems)}",
                )

    return findings


def leakage_scan_csv(path: Path) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    rel = path.relative_to(PROJECT_ROOT).as_posix()
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row_id = row.get("expanded_image_id", "?")
            for col, value in row.items():
                if col == "review_image_path_local" and path_is_safe_public_path(value or ""):
                    continue
                for issue in find_leakage_issues(value or "", context=f"{rel}:{row_id}:{col}"):
                    findings.append(
                        {
                            "expanded_image_id": row_id,
                            "check_name": "leakage_scan",
                            "severity": "failure",
                            "message": issue,
                        }
                    )
    return findings


def summarize(rows: list[dict[str, str]], findings: list[dict[str, str]]) -> dict[str, object]:
    failures = [f for f in findings if f["severity"] == "failure"]
    warnings = [f for f in findings if f["severity"] == "warning"]
    pending_count = sum(1 for row in rows if row.get("annotation_status") == "pending")
    return {
        "failures": failures,
        "warnings": warnings,
        "pending_count": pending_count,
        "status_counts": Counter(row.get("annotation_status", "") or "<blank>" for row in rows),
        "uncertainty_counts": Counter(row.get("uncertainty_flag", "") or "<blank>" for row in rows),
        "distributions": {
            field: Counter(row.get(field, "") or "<blank>" for row in rows)
            for field in DISTRIBUTION_FIELDS
        },
    }


def write_audit_outputs(
    findings: list[dict[str, str]],
    summary: dict[str, object],
    audit_passed: bool,
    report_csv: Path,
    summary_txt: Path,
) -> None:
    write_csv(
        report_csv,
        findings,
        ["expanded_image_id", "check_name", "severity", "message"],
    )

    lines = [
        "Phase 6 unique-500 image annotation audit summary",
        "",
        f"audit passed: {'yes' if audit_passed else 'no'}",
        f"total rows: {EXPECTED_ROWS if audit_passed or summary else 'see failures'}",
        f"failures: {len(summary['failures'])}",
        f"warnings: {len(summary['warnings'])}",
        f"pending rows: {summary['pending_count']}",
        "",
        "annotation_status counts:",
    ]
    for key, value in sorted(summary["status_counts"].items()):
        lines.append(f"  {key}: {value}")
    lines.extend(["", "uncertainty_flag counts:"])
    for key, value in sorted(summary["uncertainty_counts"].items()):
        lines.append(f"  {key}: {value}")
    for field, counter in summary["distributions"].items():
        lines.extend(["", f"{field} distribution:"])
        for key, value in sorted(counter.items()):
            lines.append(f"  {key}: {value}")
    if summary["failures"]:
        lines.extend(["", "failure examples:"])
        for item in summary["failures"][:20]:
            lines.append(
                f"  {item['expanded_image_id']} | {item['check_name']} | {item['message']}"
            )
    if summary["warnings"]:
        lines.extend(["", "warning examples:"])
        for item in summary["warnings"][:20]:
            lines.append(
                f"  {item['expanded_image_id']} | {item['check_name']} | {item['message']}"
            )
    summary_txt.parent.mkdir(parents=True, exist_ok=True)
    summary_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")


def freeze_v1(input_csv: Path) -> None:
    FREEZE_CSV.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(input_csv, FREEZE_CSV)
    FREEZE_NOTE_DOC.parent.mkdir(parents=True, exist_ok=True)
    FREEZE_NOTE_DOC.write_text(
        f"""# Phase 6 Unique 500 Annotation Freeze v1 Note

## Frozen File

```text
{FREEZE_CSV.relative_to(PROJECT_ROOT)}
```

## Source

Copied from:

```text
{input_csv.relative_to(PROJECT_ROOT)}
```

## Audit Summary

See:

```text
{AUDIT_SUMMARY_TXT.relative_to(PROJECT_ROOT)}
```

## Use

This v1 file is the audited label table for downstream PF-ERI factor-to-risk analysis after human review is complete.
""",
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    input_csv = args.input.resolve()
    audit_report_csv = (args.report_out or AUDIT_REPORT_CSV).resolve()
    audit_summary_txt = (args.summary_out or AUDIT_SUMMARY_TXT).resolve()

    if not input_csv.exists():
        print(f"FAIL: input CSV not found: {input_csv}", file=sys.stderr)
        return 1

    rows = read_csv(input_csv)
    findings = audit_rows(rows)
    findings.extend(leakage_scan_csv(input_csv))
    summary = summarize(rows, findings)

    failures = summary["failures"]
    warnings = summary["warnings"]
    pending_count = summary["pending_count"]

    audit_passed = not failures
    freeze_ready = audit_passed and pending_count == 0

    write_audit_outputs(findings, summary, audit_passed, audit_report_csv, audit_summary_txt)

    if args.freeze_if_pass:
        if freeze_ready:
            freeze_v1(input_csv)
            print("Freeze v1: PASS")
            print(f"frozen CSV: {FREEZE_CSV.relative_to(PROJECT_ROOT)}")
            print(f"freeze note: {FREEZE_NOTE_DOC.relative_to(PROJECT_ROOT)}")
        else:
            print("Freeze v1: FAIL", file=sys.stderr)
            if pending_count:
                print(f"  pending rows remain: {pending_count}", file=sys.stderr)
            if failures:
                print(f"  audit failures: {len(failures)}", file=sys.stderr)
            return 1

    print(f"Phase 6 unique-500 annotation audit: {'PASS' if audit_passed else 'FAIL'}")
    print(f"audit report: {audit_report_csv.relative_to(PROJECT_ROOT)}")
    print(f"audit summary: {audit_summary_txt.relative_to(PROJECT_ROOT)}")
    print(f"failures: {len(failures)}")
    print(f"warnings: {len(warnings)}")
    print(f"pending rows: {pending_count}")
    return 0 if audit_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
