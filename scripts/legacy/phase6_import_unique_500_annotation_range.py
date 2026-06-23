#!/usr/bin/env python3
"""Import an externally annotated Phase 6 range CSV into the unified working CSV."""

from __future__ import annotations

import argparse
import csv
import shutil
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from phase6_unique_500_annotation_schema import (  # noqa: E402
    ALLOWED_VALUES,
    ANNOTATION_FIELDS,
    COMPLETE_REQUIRED_FIELDS,
    EXPECTED_ROWS,
    PUBLIC_COLUMNS,
    WORKING_CSV,
)

DEFAULT_BACKUP_DIR = PROJECT_ROOT / "outputs/czechlynx/phase6/annotation_backups"
DEFAULT_QC_REPORT = PROJECT_ROOT / "outputs/czechlynx/qc/phase6_unique_500_range_import_qc_report.txt"

IMPORT_REQUIRED_COLUMNS = [
    "expanded_image_id",
    *ANNOTATION_FIELDS,
]

IMPORT_OPTIONAL_COLUMNS = [
    "review_image_path_local",
]

IMPORT_UPDATE_FIELDS = list(ANNOTATION_FIELDS)


class ImportValidationError(Exception):
    """Raised when range import validation fails."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import a Phase 6 unique-500 annotated range CSV into the working CSV."
    )
    parser.add_argument(
        "--annotated-csv",
        type=Path,
        required=True,
        help="Annotated range CSV to import",
    )
    parser.add_argument(
        "--working-csv",
        type=Path,
        default=WORKING_CSV,
        help="Unified working CSV to update",
    )
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=DEFAULT_BACKUP_DIR,
        help="Directory for working CSV backups",
    )
    parser.add_argument(
        "--qc-report",
        type=Path,
        default=DEFAULT_QC_REPORT,
        help="QC report output path",
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


def validate_annotated_columns(rows: list[dict[str, str]], source: str) -> None:
    if not rows:
        raise ImportValidationError(f"{source}: annotated CSV is empty")
    missing = [col for col in IMPORT_REQUIRED_COLUMNS if col not in rows[0]]
    if missing:
        raise ImportValidationError(
            f"{source}: missing required columns: {', '.join(missing)}"
        )


def normalize_import_rows(
    annotated_rows: list[dict[str, str]],
    working_by_id: dict[str, dict[str, str]],
    source: str,
) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    issues: list[str] = []

    for row in annotated_rows:
        image_id = row.get("expanded_image_id", "")
        if not image_id:
            issues.append("row with blank expanded_image_id")
            continue
        if image_id in seen_ids:
            issues.append(f"duplicate expanded_image_id: {image_id}")
            continue
        seen_ids.add(image_id)

        if image_id not in working_by_id:
            issues.append(f"unknown expanded_image_id: {image_id}")
            continue

        working_row = working_by_id[image_id]
        review_path = row.get("review_image_path_local", "")
        if not review_path:
            review_path = working_row.get("review_image_path_local", "")
        elif review_path != working_row.get("review_image_path_local", ""):
            issues.append(
                f"{image_id}: review_image_path_local does not match working CSV "
                f"({review_path!r} vs {working_row.get('review_image_path_local', '')!r})"
            )

        import_row = {col: row.get(col, "").strip() for col in IMPORT_UPDATE_FIELDS}
        import_row["expanded_image_id"] = image_id
        import_row["review_image_path_local"] = review_path

        status = import_row.get("annotation_status", "")
        uncertainty = import_row.get("uncertainty_flag", "")

        for field in ANNOTATION_FIELDS:
            if field == "annotator_notes":
                continue
            value = import_row.get(field, "")
            allowed = ALLOWED_VALUES.get(field)
            if not value:
                if status in {"complete", "needs_review"}:
                    issues.append(f"{image_id}: blank {field} with annotation_status={status}")
                continue
            if allowed is not None and value not in allowed:
                issues.append(f"{image_id}: invalid {field}={value!r}")

        if status == "needs_review" and uncertainty != "yes":
            issues.append(f"{image_id}: needs_review requires uncertainty_flag=yes")

        if status == "complete":
            for field in COMPLETE_REQUIRED_FIELDS:
                if not import_row.get(field, ""):
                    issues.append(f"{image_id}: complete row missing {field}")

        normalized.append(import_row)

    if issues:
        preview = issues[:50]
        suffix = f"\n... and {len(issues) - 50} more" if len(issues) > 50 else ""
        raise ImportValidationError(
            "Annotated range validation failed:\n"
            + "\n".join(f"- {issue}" for issue in preview)
            + suffix
        )

    return normalized


def backup_working_csv(working_csv: Path, backup_dir: Path) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"czechlynx_phase6_unique_500_image_annotation_working_backup_{timestamp}.csv"
    shutil.copy2(working_csv, backup_path)
    return backup_path


def merge_rows(
    working_rows: list[dict[str, str]],
    import_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    import_by_id = {row["expanded_image_id"]: row for row in import_rows}
    merged: list[dict[str, str]] = []
    for row in working_rows:
        updated = dict(row)
        image_id = row["expanded_image_id"]
        if image_id in import_by_id:
            incoming = import_by_id[image_id]
            for field in IMPORT_UPDATE_FIELDS:
                updated[field] = incoming.get(field, "")
        merged.append(updated)
    return merged


def id_range_label(image_ids: list[str]) -> str:
    if not image_ids:
        return "<none>"
    ordered = sorted(image_ids)
    return f"{ordered[0]} .. {ordered[-1]} ({len(ordered)} ids)"


def write_qc_report(
    path: Path,
    *,
    annotated_csv: Path,
    imported_count: int,
    image_ids: list[str],
    backup_path: Path | None,
    status_counts: Counter[str],
    uncertainty_counts: Counter[str],
    passed: bool,
    rejected: bool,
    working_updated: bool,
    error_message: str = "",
) -> None:
    lines = [
        "Phase 6 unique-500 range import QC report",
        "",
        f"validation: {'PASS' if passed else 'FAIL'}",
        f"annotated CSV: {annotated_csv}",
        f"rows imported: {imported_count}",
        f"expanded_image_id range: {id_range_label(image_ids)}",
        f"backup path: {backup_path if backup_path else '<none>'}",
        f"rows rejected: {'yes' if rejected else 'no'}",
        f"working CSV updated: {'yes' if working_updated else 'no'}",
        "",
        "annotation_status counts (imported rows):",
    ]
    for key, value in sorted(status_counts.items()):
        lines.append(f"  {key or '<blank>'}: {value}")
    lines.extend(["", "uncertainty_flag counts (imported rows):"])
    for key, value in sorted(uncertainty_counts.items()):
        lines.append(f"  {key or '<blank>'}: {value}")
    if error_message:
        lines.extend(["", "error:", error_message])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    annotated_csv = args.annotated_csv.expanduser().resolve()
    working_csv = args.working_csv.resolve()
    backup_dir = args.backup_dir.resolve()
    qc_report = args.qc_report.resolve()

    if not annotated_csv.exists():
        message = f"Annotated CSV not found: {annotated_csv}"
        write_qc_report(
            qc_report,
            annotated_csv=annotated_csv,
            imported_count=0,
            image_ids=[],
            backup_path=None,
            status_counts=Counter(),
            uncertainty_counts=Counter(),
            passed=False,
            rejected=True,
            working_updated=False,
            error_message=message,
        )
        print("Phase 6 range import: FAIL", file=sys.stderr)
        print(message, file=sys.stderr)
        return 1

    if not working_csv.exists():
        message = f"Working CSV not found: {working_csv}"
        write_qc_report(
            qc_report,
            annotated_csv=annotated_csv,
            imported_count=0,
            image_ids=[],
            backup_path=None,
            status_counts=Counter(),
            uncertainty_counts=Counter(),
            passed=False,
            rejected=True,
            working_updated=False,
            error_message=message,
        )
        print("Phase 6 range import: FAIL", file=sys.stderr)
        print(message, file=sys.stderr)
        return 1

    try:
        working_rows = read_csv(working_csv)
        annotated_rows = read_csv(annotated_csv)

        if len(working_rows) != EXPECTED_ROWS:
            raise ImportValidationError(
                f"Working CSV has {len(working_rows)} rows; expected {EXPECTED_ROWS}"
            )

        validate_annotated_columns(annotated_rows, annotated_csv.name)
        working_by_id = {row["expanded_image_id"]: row for row in working_rows}
        import_rows = normalize_import_rows(annotated_rows, working_by_id, annotated_csv.name)

        backup_path = backup_working_csv(working_csv, backup_dir)
        merged_rows = merge_rows(working_rows, import_rows)
        write_csv(working_csv, merged_rows, PUBLIC_COLUMNS)

        image_ids = [row["expanded_image_id"] for row in import_rows]
        status_counts = Counter(row.get("annotation_status", "") or "<blank>" for row in import_rows)
        uncertainty_counts = Counter(
            row.get("uncertainty_flag", "") or "<blank>" for row in import_rows
        )

        write_qc_report(
            qc_report,
            annotated_csv=annotated_csv,
            imported_count=len(import_rows),
            image_ids=image_ids,
            backup_path=backup_path,
            status_counts=status_counts,
            uncertainty_counts=uncertainty_counts,
            passed=True,
            rejected=False,
            working_updated=True,
        )

        print("Phase 6 range import: PASS")
        print(f"imported rows: {len(import_rows)}")
        print(f"updated working CSV: {working_csv.relative_to(PROJECT_ROOT)}")
        print(f"backup: {backup_path.relative_to(PROJECT_ROOT)}")
        print(f"QC report: {qc_report.relative_to(PROJECT_ROOT)}")
        return 0

    except ImportValidationError as exc:
        write_qc_report(
            qc_report,
            annotated_csv=annotated_csv,
            imported_count=0,
            image_ids=[],
            backup_path=None,
            status_counts=Counter(),
            uncertainty_counts=Counter(),
            passed=False,
            rejected=True,
            working_updated=False,
            error_message=str(exc),
        )
        print("Phase 6 range import: FAIL", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        print(f"QC report: {qc_report.relative_to(PROJECT_ROOT)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
