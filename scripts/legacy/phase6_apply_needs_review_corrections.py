#!/usr/bin/env python3
"""Apply needs-review correction CSV to assisted working CSV."""

from __future__ import annotations

import argparse
import shutil
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
    correction_range_dir,
    default_correction_csv,
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
from phase6_unique_500_annotation_schema import EXPECTED_ROWS, PUBLIC_COLUMNS  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply needs-review corrections to assisted working CSV.")
    parser.add_argument("--range-id", required=True, help="Range id, e.g. range_000_049")
    parser.add_argument(
        "--correction-csv",
        type=Path,
        default=None,
        help="Correction CSV path (default: workspace correction or streamlit folder)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    range_id = args.range_id
    start_index, end_index = parse_range_id(range_id)
    correction_csv = args.correction_csv.expanduser().resolve() if args.correction_csv else default_correction_csv(range_id)
    if not correction_csv.exists():
        alt = (
            incoming_range_dir(range_id)
            / "needs_review_streamlit"
            / f"{range_id}_needs_review_streamlit"
            / f"{range_id}_needs_review_corrections_working.csv"
        )
        if alt.exists():
            correction_csv = alt
    report_path = IMPORTED_RANGES_DIR / f"{range_id}_correction_report.txt"
    correction_dir = correction_range_dir(range_id)
    correction_dir.mkdir(parents=True, exist_ok=True)
    workspace_copy = correction_dir / f"{range_id}_needs_review_corrections_working.csv"

    if not correction_csv.exists():
        print(f"FAIL: correction CSV not found: {correction_csv}", file=sys.stderr)
        return 1
    if not ASSISTED_WORKING_CSV.exists():
        print(f"FAIL: assisted working CSV not found: {ASSISTED_WORKING_CSV}", file=sys.stderr)
        return 1

    if correction_csv.resolve() != workspace_copy.resolve():
        shutil.copy2(correction_csv, workspace_copy)
        correction_csv = workspace_copy

    try:
        working_rows = read_csv(ASSISTED_WORKING_CSV)
        correction_rows = read_csv(correction_csv)
        if len(working_rows) != EXPECTED_ROWS:
            raise ImportValidationError(
                f"Assisted working CSV has {len(working_rows)} rows; expected {EXPECTED_ROWS}"
            )

        validate_annotated_columns(correction_rows, correction_csv.name)
        working_by_id = {row["expanded_image_id"]: row for row in working_rows}
        import_rows = normalize_import_rows(correction_rows, working_by_id, correction_csv.name)

        backup_path = backup_assisted_working(prefix="pre_correction")
        merged_rows = merge_annotation_rows(working_rows, import_rows)
        write_csv(ASSISTED_WORKING_CSV, merged_rows, PUBLIC_COLUMNS)

        status_counts = Counter(row.get("annotation_status", "") for row in import_rows)
        append_import_log(
            {
                "range_id": range_id,
                "start_index": str(start_index),
                "end_index": str(end_index),
                "annotated_csv": "",
                "needs_review_csv": "",
                "correction_csv": str(correction_csv.relative_to(PROJECT_ROOT)),
                "rows_imported": str(len(import_rows)),
                "needs_review_rows": str(status_counts.get("needs_review", 0)),
                "complete_rows": str(status_counts.get("complete", 0)),
                "import_status": "PASS",
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "notes": f"correction applied; backup={backup_path.relative_to(PROJECT_ROOT)}",
            }
        )
        import_log_rows = read_csv(IMPORT_LOG_CSV)
        rebuild_needs_review_index(merged_rows, import_log_rows)

        report_lines = [
            f"Correction report for {range_id}",
            "",
            "status: PASS",
            f"correction CSV: {correction_csv.relative_to(PROJECT_ROOT)}",
            f"rows corrected: {len(import_rows)}",
            f"backup: {backup_path.relative_to(PROJECT_ROOT)}",
            "",
            "annotation_status counts (corrected rows):",
        ]
        for key, value in sorted(status_counts.items()):
            report_lines.append(f"  {key}: {value}")
        report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

        print("Phase 6 needs-review correction apply: PASS")
        print(f"range_id: {range_id}")
        print(f"corrected rows: {len(import_rows)}")
        print(f"assisted working CSV: {ASSISTED_WORKING_CSV.relative_to(PROJECT_ROOT)}")
        print(f"report: {report_path.relative_to(PROJECT_ROOT)}")
        return 0

    except ImportValidationError as exc:
        report_path.write_text(f"Correction report for {range_id}\n\nstatus: FAIL\n\n{exc}\n", encoding="utf-8")
        print("Phase 6 needs-review correction apply: FAIL", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
