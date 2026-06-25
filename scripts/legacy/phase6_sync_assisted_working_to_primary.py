#!/usr/bin/env python3
"""Sync assisted working CSV to official primary working CSV after validation."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from phase6_assisted_annotation_workspace import (  # noqa: E402
    ASSISTED_WORKING_CSV,
    WORKSPACE_QC_DIR,
    read_csv,
    scan_public_csv_leakage,
)
from phase6_unique_500_annotation_schema import (  # noqa: E402
    ALLOWED_VALUES,
    ANNOTATION_FIELDS,
    EXPECTED_ROWS,
    PROJECT_ROOT as SCHEMA_ROOT,
    WORKING_CSV,
)

SYNC_REPORT = WORKSPACE_QC_DIR / "assisted_to_primary_sync_report.txt"
BACKUP_DIR = PROJECT_ROOT / "outputs/czechlynx/phase6/annotation_backups"
AUDIT_SCRIPT = SCRIPT_DIR / "audit_phase6_unique_500_image_annotations.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync assisted working CSV to primary working CSV.")
    parser.add_argument(
        "--skip-audit",
        action="store_true",
        help="Copy without running official audit (not recommended)",
    )
    return parser.parse_args()


def validate_assisted_rows(rows: list[dict[str, str]]) -> list[str]:
    issues: list[str] = []
    if len(rows) != EXPECTED_ROWS:
        issues.append(f"Expected {EXPECTED_ROWS} rows, found {len(rows)}")
    for row in rows:
        image_id = row.get("expanded_image_id", "?")
        image_path = PROJECT_ROOT / row.get("review_image_path_local", "")
        if not image_path.exists():
            issues.append(f"{image_id}: missing image {row.get('review_image_path_local', '')}")
        for field in ANNOTATION_FIELDS:
            if field == "annotator_notes":
                continue
            value = row.get(field, "")
            allowed = ALLOWED_VALUES.get(field)
            if value and allowed is not None and value not in allowed:
                issues.append(f"{image_id}: invalid {field}={value!r}")
    issues.extend(scan_public_csv_leakage(ASSISTED_WORKING_CSV))
    return issues


def main() -> int:
    args = parse_args()

    if not ASSISTED_WORKING_CSV.exists():
        print(f"FAIL: assisted working CSV not found: {ASSISTED_WORKING_CSV}", file=sys.stderr)
        return 1

    rows = read_csv(ASSISTED_WORKING_CSV)
    issues = validate_assisted_rows(rows)
    if issues:
        SYNC_REPORT.parent.mkdir(parents=True, exist_ok=True)
        SYNC_REPORT.write_text(
            "Assisted to primary sync report\n\nstatus: FAIL\n\n"
            + "\n".join(f"- {issue}" for issue in issues[:50])
            + "\n",
            encoding="utf-8",
        )
        print("Phase 6 assisted-to-primary sync: FAIL", file=sys.stderr)
        for issue in issues[:20]:
            print(f"  - {issue}", file=sys.stderr)
        return 1

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"czechlynx_phase6_unique_500_image_annotation_working_backup_pre_sync_{timestamp}.csv"
    if WORKING_CSV.exists():
        shutil.copy2(WORKING_CSV, backup_path)
    shutil.copy2(ASSISTED_WORKING_CSV, WORKING_CSV)

    audit_exit = 0
    audit_summary = "skipped"
    if not args.skip_audit:
        result = subprocess.run(
            [sys.executable, str(AUDIT_SCRIPT), "--input", str(WORKING_CSV)],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        audit_exit = result.returncode
        audit_summary = result.stdout.strip() or result.stderr.strip()

    passed = audit_exit == 0
    SYNC_REPORT.parent.mkdir(parents=True, exist_ok=True)
    SYNC_REPORT.write_text(
        "\n".join(
            [
                "Assisted to primary sync report",
                "",
                f"timestamp: {datetime.now().isoformat(timespec='seconds')}",
                f"status: {'PASS' if passed else 'FAIL'}",
                f"assisted source: {ASSISTED_WORKING_CSV.relative_to(PROJECT_ROOT)}",
                f"primary target: {WORKING_CSV.relative_to(PROJECT_ROOT)}",
                f"primary backup: {backup_path.relative_to(PROJECT_ROOT) if WORKING_CSV.exists() else '<none>'}",
                "",
                "audit output:",
                audit_summary,
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    if not passed:
        print("Phase 6 assisted-to-primary sync: FAIL (post-sync audit)", file=sys.stderr)
        print(audit_summary, file=sys.stderr)
        return 1

    print("Phase 6 assisted-to-primary sync: PASS")
    print(f"primary working CSV: {WORKING_CSV.relative_to(PROJECT_ROOT)}")
    print(f"backup: {backup_path.relative_to(PROJECT_ROOT)}")
    print(f"sync report: {SYNC_REPORT.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
