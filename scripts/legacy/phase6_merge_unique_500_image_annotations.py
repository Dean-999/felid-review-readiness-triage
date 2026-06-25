#!/usr/bin/env python3
"""Merge completed Phase 6 unique-500 image-level annotation batch CSVs."""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

DEFAULT_INPUT_DIR = (
    PROJECT_ROOT / "outputs/czechlynx/phase6/manual_annotations/image_batches_completed"
)
DEFAULT_OUTPUT_CSV = (
    PROJECT_ROOT / "data/labels/czechlynx/czechlynx_phase6_unique_500_image_annotations_completed.csv"
)
DEFAULT_QC_REPORT = (
    PROJECT_ROOT / "outputs/czechlynx/qc/phase6_unique_500_image_annotation_merge_audit_report.txt"
)
DEFAULT_RESULTS_DOC = (
    PROJECT_ROOT / "docs/phase6/phase6_unique_500_image_annotation_merge_results.md"
)

BATCH_COUNT = 10
ROWS_PER_BATCH = 50
EXPECTED_TOTAL_ROWS = 500

REQUIRED_COLUMNS = [
    "review_entry_id",
    "batch_id",
    "review_image_filename",
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

OPTIONAL_COLUMNS = [
    "relative_image_path",
    "neutral_image_id",
    "candidate_reason",
    "selection_stratum",
]

ANNOTATION_COLUMNS = [
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

OUTPUT_COLUMN_ORDER = [
    "review_entry_id",
    "batch_id",
    "review_image_filename",
    *OPTIONAL_COLUMNS,
    *ANNOTATION_COLUMNS,
]

ALLOWED_VALUES: dict[str, set[str]] = {
    "pattern_visibility": {"high", "medium", "low", "none", "unknown"},
    "side_visibility": {"left", "right", "both", "unknown"},
    "side_evidence_quality": {"high", "medium", "low", "none", "unknown"},
    "body_fraction_visible": {"0_25", "26_50", "51_75", "76_100", "unknown"},
    "partial_body": {"yes", "no", "unknown"},
    "frontal_or_rear_view": {"yes", "no", "unknown"},
    "silhouette_only": {"yes", "no", "unknown"},
    "blur_level": {"none", "mild", "moderate", "severe", "unknown"},
    "occlusion_level": {"none", "partial", "major", "unknown"},
    "lighting_condition": {"normal", "overexposed", "underexposed", "mixed", "unknown"},
    "night_ir_artifact": {"yes", "no", "unknown"},
    "contrast_level": {"good", "low", "unknown"},
    "primary_limiting_factor": {
        "none",
        "blur",
        "occlusion",
        "low_contrast",
        "overexposed",
        "underexposed",
        "night_ir_artifact",
        "pattern_not_visible",
        "side_unknown",
        "side_non_comparable",
        "partial_body",
        "frontal_or_rear_view",
        "silhouette",
        "non_target_species",
        "other",
        "unknown",
    },
    "uncertainty_flag": {"yes", "no"},
    "annotation_status": {"complete", "needs_review"},
}

RESTRICTED_PATTERNS = [
    "unique_name",
    "lynx_",
    "/Users/",
    "data/raw",
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
    "review_image_path",
    "czlx_expanded",
    "CzechLynx/",
]


class MergeValidationError(Exception):
    """Raised when batch annotation merge validation fails."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge completed Phase 6 unique-500 image annotation batch CSVs."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help="Directory containing batch_XXX_annotated.csv files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_CSV,
        help="Path for merged analysis-ready CSV",
    )
    parser.add_argument(
        "--qc-report",
        type=Path,
        default=DEFAULT_QC_REPORT,
        help="Path for merge audit QC report",
    )
    parser.add_argument(
        "--results-doc",
        type=Path,
        default=DEFAULT_RESULTS_DOC,
        help="Path for merge results markdown doc",
    )
    return parser.parse_args()


def expected_batch_files() -> list[str]:
    return [f"batch_{idx:03d}_annotated.csv" for idx in range(1, BATCH_COUNT + 1)]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def validate_input_presence(input_dir: Path) -> list[Path]:
    missing = [name for name in expected_batch_files() if not (input_dir / name).exists()]
    if missing:
        raise MergeValidationError(
            "Missing required batch annotation files:\n"
            + "\n".join(f"- {input_dir / name}" for name in missing)
        )
    return [input_dir / name for name in expected_batch_files()]


def validate_columns(rows: list[dict[str, str]], source_label: str) -> None:
    if not rows:
        raise MergeValidationError(f"{source_label}: file is empty")
    missing = [col for col in REQUIRED_COLUMNS if col not in rows[0]]
    if missing:
        raise MergeValidationError(
            f"{source_label}: missing required columns: {', '.join(missing)}"
        )


def validate_row_counts(batch_rows: dict[str, list[dict[str, str]]]) -> None:
    for batch_id, rows in batch_rows.items():
        if len(rows) != ROWS_PER_BATCH:
            raise MergeValidationError(
                f"{batch_id}: expected {ROWS_PER_BATCH} rows, found {len(rows)}"
            )
    total = sum(len(rows) for rows in batch_rows.values())
    if total != EXPECTED_TOTAL_ROWS:
        raise MergeValidationError(
            f"Expected {EXPECTED_TOTAL_ROWS} total rows, found {total}"
        )


def validate_uniqueness(rows: list[dict[str, str]]) -> None:
    entry_ids = [row["review_entry_id"] for row in rows]
    filenames = [row["review_image_filename"] for row in rows]

    dup_entries = [item for item, count in Counter(entry_ids).items() if count > 1]
    if dup_entries:
        raise MergeValidationError(
            "Duplicate review_entry_id values found: " + ", ".join(sorted(dup_entries)[:20])
        )

    dup_files = [item for item, count in Counter(filenames).items() if count > 1]
    if dup_files:
        raise MergeValidationError(
            "Duplicate review_image_filename values found: "
            + ", ".join(sorted(dup_files)[:20])
        )


def validate_allowed_values(rows: list[dict[str, str]]) -> list[str]:
    issues: list[str] = []
    for row in rows:
        row_ref = (
            f"{row.get('batch_id', '?')} / {row.get('review_entry_id', '?')} / "
            f"{row.get('review_image_filename', '?')}"
        )
        for field in ANNOTATION_COLUMNS:
            value = (row.get(field) or "").strip()
            if field == "annotator_notes":
                continue
            if not value:
                issues.append(f"{row_ref}: `{field}` is blank")
                continue
            allowed = ALLOWED_VALUES.get(field)
            if allowed is not None and value not in allowed:
                issues.append(
                    f"{row_ref}: `{field}` has invalid value `{value}` "
                    f"(allowed: {', '.join(sorted(allowed))})"
                )
    return issues


def normalize_row(row: dict[str, str], optional_present: set[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for col in OUTPUT_COLUMN_ORDER:
        if col in OPTIONAL_COLUMNS and col not in optional_present:
            continue
        out[col] = (row.get(col) or "").strip()
    return out


def merge_batches(batch_paths: list[Path]) -> tuple[list[dict[str, str]], dict[str, list[dict[str, str]]]]:
    batch_rows: dict[str, list[dict[str, str]]] = {}
    optional_present: set[str] = set()

    for path in batch_paths:
        rows = read_csv(path)
        validate_columns(rows, path.name)
        batch_id = f"batch_{path.stem.split('_')[1]}"
        for row in rows:
            if row.get("batch_id") and row["batch_id"] != batch_id:
                raise MergeValidationError(
                    f"{path.name}: row {row.get('review_entry_id')} has batch_id "
                    f"{row['batch_id']}, expected {batch_id}"
                )
            row["batch_id"] = batch_id
        batch_rows[batch_id] = rows
        for col in OPTIONAL_COLUMNS:
            if col in rows[0]:
                optional_present.add(col)

    validate_row_counts(batch_rows)

    merged = [row for batch_id in sorted(batch_rows) for row in batch_rows[batch_id]]
    validate_uniqueness(merged)

    value_issues = validate_allowed_values(merged)
    if value_issues:
        preview = value_issues[:50]
        suffix = f"\n... and {len(value_issues) - 50} more" if len(value_issues) > 50 else ""
        raise MergeValidationError(
            "Invalid or blank annotation values detected:\n"
            + "\n".join(f"- {issue}" for issue in preview)
            + suffix
        )

    output_columns = [
        col
        for col in OUTPUT_COLUMN_ORDER
        if col not in OPTIONAL_COLUMNS or col in optional_present
    ]
    normalized = [normalize_row(row, optional_present) for row in merged]
    normalized.sort(key=lambda r: r["review_entry_id"])
    return normalized, batch_rows


def leakage_scan(rows: list[dict[str, str]]) -> tuple[bool, list[str]]:
    issues: list[str] = []
    for row in rows:
        row_ref = row["review_entry_id"]
        for col, value in row.items():
            lower = value.lower()
            for pattern in RESTRICTED_PATTERNS:
                if pattern.lower() in lower:
                    issues.append(
                        f"{row_ref}: column `{col}` matched restricted pattern `{pattern}`"
                    )
                    break
    return not issues, issues


def distribution_counter(rows: list[dict[str, str]], field: str) -> Counter[str]:
    return Counter((row.get(field) or "").strip() or "<blank>" for row in rows)


def missing_value_audit(rows: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for field in ANNOTATION_COLUMNS:
        if field == "annotator_notes":
            continue
        counts[field] = sum(1 for row in rows if not (row.get(field) or "").strip())
    return counts


def batch_status_counts(rows: list[dict[str, str]]) -> tuple[dict[str, int], dict[str, int]]:
    complete_by_batch: dict[str, int] = defaultdict(int)
    needs_review_by_batch: dict[str, int] = defaultdict(int)
    for row in rows:
        batch_id = row["batch_id"]
        status = (row.get("annotation_status") or "").strip()
        if status == "complete":
            complete_by_batch[batch_id] += 1
        elif status == "needs_review":
            needs_review_by_batch[batch_id] += 1
    return dict(sorted(complete_by_batch.items())), dict(sorted(needs_review_by_batch.items()))


def format_counter(counter: Counter[str]) -> list[str]:
    return [f"  {key}: {value}" for key, value in sorted(counter.items())]


def write_qc_report(
    path: Path,
    rows: list[dict[str, str]],
    batch_rows: dict[str, list[dict[str, str]]],
    leakage_passed: bool,
    leakage_issues: list[str],
    status: str,
) -> None:
    missing_counts = missing_value_audit(rows)
    complete_by_batch, needs_review_by_batch = batch_status_counts(rows)
    lines = [
        "Phase 6 unique-500 image annotation merge audit report",
        "",
        f"status: {status}",
        f"total row count: {len(rows)}",
        "",
        "row count per batch:",
    ]
    for batch_id in sorted(batch_rows):
        lines.append(f"  {batch_id}: {len(batch_rows[batch_id])}")

    lines.extend(["", "missing-value audit (excluding annotator_notes):"])
    for field, count in missing_counts.items():
        lines.append(f"  {field}: {count}")

    lines.extend(["", "duplicate review_entry_id audit: 0"])
    lines.extend(["", "annotation_status counts:"])
    lines.extend(format_counter(distribution_counter(rows, "annotation_status")))
    lines.extend(["", "uncertainty_flag counts:"])
    lines.extend(format_counter(distribution_counter(rows, "uncertainty_flag")))

    for field in [
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
    ]:
        lines.extend(["", f"{field} distribution:"])
        lines.extend(format_counter(distribution_counter(rows, field)))

    lines.extend(["", "complete count by batch:"])
    for batch_id in sorted(batch_rows):
        lines.append(f"  {batch_id}: {complete_by_batch.get(batch_id, 0)}")

    lines.extend(["", "needs_review count by batch:"])
    for batch_id in sorted(batch_rows):
        lines.append(f"  {batch_id}: {needs_review_by_batch.get(batch_id, 0)}")

    lines.extend(["", f"leakage scan passed: {'yes' if leakage_passed else 'no'}"])
    if leakage_issues:
        lines.append("leakage issues:")
        lines.extend(f"  - {issue}" for issue in leakage_issues)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_results_doc(
    path: Path,
    input_dir: Path,
    output_csv: Path,
    rows: list[dict[str, str]],
    leakage_passed: bool,
    needs_review_total: int,
) -> None:
    ready = leakage_passed and needs_review_total == 0
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""# Phase 6 Unique 500 Image Annotation Merge Results

## Purpose

Merge ten completed Phase 6 unique image annotation batch CSVs into one analysis-ready label table for downstream PF-ERI factor-to-risk analysis.

## Input Directory

```text
{input_dir.relative_to(PROJECT_ROOT)}
```

## Output CSV

```text
{output_csv.relative_to(PROJECT_ROOT)}
```

## Row Counts

- batches merged: {BATCH_COUNT}
- rows per batch: {ROWS_PER_BATCH}
- total merged rows: {len(rows)}

## QC Summary

See:

```text
{DEFAULT_QC_REPORT.relative_to(PROJECT_ROOT)}
```

- duplicate `review_entry_id` values: 0
- annotation_status `needs_review`: {needs_review_total}
- annotation_status `complete`: {len(rows) - needs_review_total}

## Distribution Summary

Key distributions are recorded in the QC audit report, including pattern visibility, side visibility, blur, occlusion, lighting, contrast, and primary limiting factor.

## Leakage Scan Result

{'PASS' if leakage_passed else 'FAIL'}

## Ready for PF-ERI Factor Sensitivity Analysis

{'Yes — merged labels passed validation and contain no needs_review rows.' if ready else 'Not yet — review needs_review rows and/or leakage findings before downstream PF-ERI factor sensitivity analysis.'}

## Limitations

- Merge validates against the PF-ERI analysis annotation schema defined in the merge script.
- Rows marked `needs_review` should be resolved or explicitly excluded before factor sensitivity analysis.
- This step does not train models or modify PF-ERI scores.
""",
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    input_dir = args.input_dir.resolve()
    output_csv = args.output.resolve()
    qc_report = args.qc_report.resolve()
    results_doc = args.results_doc.resolve()

    try:
        batch_paths = validate_input_presence(input_dir)
        merged_rows, batch_rows = merge_batches(batch_paths)

        output_columns = list(merged_rows[0].keys()) if merged_rows else []
        leakage_passed, leakage_issues = leakage_scan(merged_rows)
        if not leakage_passed:
            preview = leakage_issues[:20]
            suffix = (
                f"\n... and {len(leakage_issues) - 20} more"
                if len(leakage_issues) > 20
                else ""
            )
            raise MergeValidationError(
                "Leakage scan failed on merged output:\n"
                + "\n".join(f"- {issue}" for issue in preview)
                + suffix
            )

        write_csv(output_csv, merged_rows, output_columns)
        write_qc_report(
            qc_report,
            merged_rows,
            batch_rows,
            leakage_passed=True,
            leakage_issues=[],
            status="PASS",
        )

        needs_review_total = sum(
            1 for row in merged_rows if row.get("annotation_status") == "needs_review"
        )
        write_results_doc(
            results_doc,
            input_dir,
            output_csv,
            merged_rows,
            leakage_passed=True,
            needs_review_total=needs_review_total,
        )

        print("Phase 6 unique-500 image annotation merge: PASS")
        print(f"merged CSV: {output_csv.relative_to(PROJECT_ROOT)}")
        print(f"QC report: {qc_report.relative_to(PROJECT_ROOT)}")
        print(f"results doc: {results_doc.relative_to(PROJECT_ROOT)}")
        print(f"total rows: {len(merged_rows)}")
        return 0

    except MergeValidationError as exc:
        print("Phase 6 unique-500 image annotation merge: FAIL", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
