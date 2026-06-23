#!/usr/bin/env python3
"""Import an organized assisted range CSV into the assisted working CSV."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from phase6_assisted_annotation_workspace import (  # noqa: E402
    ASSISTED_WORKING_CSV,
    IMPORTED_RANGES_DIR,
    IMPORT_LOG_CSV,
    append_import_log,
    backup_assisted_working,
    incoming_range_dir,
    merge_annotation_rows,
    parse_range_id,
    read_csv,
    rebuild_needs_review_index,
    write_csv,
)
from phase6_import_unique_500_annotation_range import (  # noqa: E402
    ImportValidationError,
    normalize_import_rows,
    validate_annotated_columns,
)
from phase6_unique_500_annotation_schema import EXPECTED_ROWS, PUBLIC_COLUMNS, WORKING_CSV  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import assisted range into workspace assisted working CSV.")
    parser.add_argument("--range-id", required=True, help="Range id, e.g. range_000_049")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    range_id = args.range_id
    start_index, end_index = parse_range_id(range_id)
    incoming_dir = incoming_range_dir(range_id)
    annotated_csv = incoming_dir / f"{range_id}_annotated.csv"
    needs_review_csv = incoming_dir / f"{range_id}_needs_review.csv"
    report_path = IMPORTED_RANGES_DIR / f"{range_id}_import_report.txt"

    if not annotated_csv.exists():
        print(f"FAIL: annotated CSV not found: {annotated_csv}", file=sys.stderr)
        return 1
    if not ASSISTED_WORKING_CSV.exists():
        print(f"FAIL: assisted working CSV not found: {ASSISTED_WORKING_CSV}", file=sys.stderr)
        return 1

    try:
        working_rows = read_csv(ASSISTED_WORKING_CSV)
        annotated_rows = read_csv(annotated_csv)
        if len(working_rows) != EXPECTED_ROWS:
            raise ImportValidationError(
                f"Assisted working CSV has {len(working_rows)} rows; expected {EXPECTED_ROWS}"
            )

        validate_annotated_columns(annotated_rows, annotated_csv.name)
        working_by_id = {row["expanded_image_id"]: row for row in working_rows}
        import_rows = normalize_import_rows(annotated_rows, working_by_id, annotated_csv.name)

        backup_path = backup_assisted_working(prefix="pre_import")
        merged_rows = merge_annotation_rows(working_rows, import_rows)
        write_csv(ASSISTED_WORKING_CSV, merged_rows, PUBLIC_COLUMNS)

        status_counts = Counter(row.get("annotation_status", "") for row in import_rows)
        append_import_log(
            {
                "range_id": range_id,
                "start_index": str(start_index),
                "end_index": str(end_index),
                "annotated_csv": str(annotated_csv.relative_to(PROJECT_ROOT)),
                "needs_review_csv": str(needs_review_csv.relative_to(PROJECT_ROOT))
                if needs_review_csv.exists()
                else "",
                "correction_csv": "",
                "rows_imported": str(len(import_rows)),
                "needs_review_rows": str(status_counts.get("needs_review", 0)),
                "complete_rows": str(status_counts.get("complete", 0)),
                "import_status": "PASS",
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "notes": f"backup={backup_path.relative_to(PROJECT_ROOT)}",
            }
        )
        import_log_rows = read_csv(IMPORT_LOG_CSV)
        rebuild_needs_review_index(merged_rows, import_log_rows)

        report_lines = [
            f"Import report for {range_id}",
            "",
            f"status: PASS",
            f"annotated CSV: {annotated_csv.relative_to(PROJECT_ROOT)}",
            f"rows imported: {len(import_rows)}",
            f"assisted working CSV: {ASSISTED_WORKING_CSV.relative_to(PROJECT_ROOT)}",
            f"primary working CSV untouched: {WORKING_CSV.relative_to(PROJECT_ROOT)}",
            f"backup: {backup_path.relative_to(PROJECT_ROOT)}",
            "",
            "annotation_status counts:",
        ]
        for key, value in sorted(status_counts.items()):
            report_lines.append(f"  {key}: {value}")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

        print("Phase 6 assisted range import: PASS")
        print(f"range_id: {range_id}")
        print(f"imported rows: {len(import_rows)}")
        print(f"assisted working CSV: {ASSISTED_WORKING_CSV.relative_to(PROJECT_ROOT)}")
        print(f"import report: {report_path.relative_to(PROJECT_ROOT)}")
        return 0

    except ImportValidationError as exc:
        append_import_log(
            {
                "range_id": range_id,
                "start_index": str(start_index),
                "end_index": str(end_index),
                "annotated_csv": str(annotated_csv.relative_to(PROJECT_ROOT)),
                "needs_review_csv": "",
                "correction_csv": "",
                "rows_imported": "0",
                "needs_review_rows": "0",
                "complete_rows": "0",
                "import_status": "FAIL",
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "notes": str(exc).replace("\n", " ")[:500],
            }
        )
        report_path.write_text(f"Import report for {range_id}\n\nstatus: FAIL\n\n{exc}\n", encoding="utf-8")
        print("Phase 6 assisted range import: FAIL", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
