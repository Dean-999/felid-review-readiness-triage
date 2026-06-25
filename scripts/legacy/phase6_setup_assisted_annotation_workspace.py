#!/usr/bin/env python3
"""Set up the Phase 6 unique-500 assisted annotation workspace."""

from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from phase6_assisted_annotation_workspace import (  # noqa: E402
    ASSISTED_BACKUP_INITIAL,
    ASSISTED_WORKING_CSV,
    IMPORT_LOG_COLUMNS,
    IMPORT_LOG_CSV,
    NEEDS_REVIEW_INDEX_COLUMNS,
    NEEDS_REVIEW_SUMMARY_CSV,
    ALL_NEEDS_REVIEW_CSV,
    WORKSPACE_LEAKAGE_REPORT,
    WORKSPACE_QC_REPORT,
    WORKSPACE_ROOT,
    ensure_workspace_dirs,
    read_csv,
    scan_workspace_leakage,
    write_csv,
)
from phase6_unique_500_annotation_schema import EXPECTED_ROWS, WORKING_CSV  # noqa: E402


def write_readme() -> None:
    readme = WORKSPACE_ROOT / "README.md"
    readme.write_text(
        f"""# Phase 6 Unique 500 Assisted Annotation Workspace

## Purpose

This workspace stores assisted annotation range outputs, correction files, import logs, and a separate **assisted working CSV**. The official project working CSV in `data/labels/czechlynx/` is not overwritten until you explicitly sync after QC.

## Folder Layout

| Folder | Purpose |
|---|---|
| `assisted_working/` | Staging CSV, backups, import log |
| `incoming_from_downloads/` | Organized range files from Downloads |
| `corrections_from_streamlit/` | Needs-review correction CSVs |
| `imported_ranges/` | Per-range import reports |
| `needs_review_index/` | Aggregated needs-review rows |
| `qc/` | Workspace QC and audit summaries |

## Workflow

### Setup once

```bash
python3 scripts/phase6_setup_assisted_annotation_workspace.py
```

### Organize each downloaded range

```bash
python3 scripts/phase6_organize_assisted_range_outputs.py \\
  --range-id range_000_049 \\
  --downloads-dir ~/Downloads
```

### Import range into assisted working CSV

```bash
python3 scripts/phase6_import_assisted_range_to_workspace.py \\
  --range-id range_000_049
```

### Review needs_review rows

```bash
cd "outputs/czechlynx/phase6/annotation_review_packages/phase6_unique_500_assisted_annotation_workspace/incoming_from_downloads/range_000_049/needs_review_streamlit"
streamlit run streamlit/streamlit_needs_review_app.py
```

### Apply corrections

```bash
python3 scripts/phase6_apply_needs_review_corrections.py \\
  --range-id range_000_049
```

### Audit assisted working CSV

```bash
python3 scripts/audit_phase6_unique_500_image_annotations.py \\
  --input-csv outputs/czechlynx/phase6/annotation_review_packages/phase6_unique_500_assisted_annotation_workspace/assisted_working/czechlynx_phase6_unique_500_assisted_working.csv \\
  --summary-out outputs/czechlynx/phase6/annotation_review_packages/phase6_unique_500_assisted_annotation_workspace/qc/assisted_working_audit_summary.txt
```

### Sync to official working CSV (only after audit pass)

```bash
python3 scripts/phase6_sync_assisted_working_to_primary.py
```

## Safety

- Primary working CSV: `data/labels/czechlynx/czechlynx_phase6_unique_500_image_annotation_working.csv`
- Assisted working CSV: `assisted_working/czechlynx_phase6_unique_500_assisted_working.csv`

Import and correction scripts update the assisted CSV only. Sync is explicit and backs up the primary CSV first.
""",
        encoding="utf-8",
    )


def write_workspace_qc(
    leakage_passed: bool,
    leakage_issues: list[str],
) -> None:
    lines = [
        "Phase 6 assisted annotation workspace QC report",
        "",
        f"timestamp: {datetime.now().isoformat(timespec='seconds')}",
        f"workspace root: {WORKSPACE_ROOT.relative_to(PROJECT_ROOT)}",
        f"assisted working CSV exists: {'yes' if ASSISTED_WORKING_CSV.exists() else 'no'}",
        f"initial backup exists: {'yes' if ASSISTED_BACKUP_INITIAL.exists() else 'no'}",
        f"import log exists: {'yes' if IMPORT_LOG_CSV.exists() else 'no'}",
        f"needs_review index exists: {'yes' if ALL_NEEDS_REVIEW_CSV.exists() else 'no'}",
        f"leakage scan passed: {'yes' if leakage_passed else 'no'}",
    ]
    if leakage_issues:
        lines.append("leakage issues:")
        lines.extend(f"- {issue}" for issue in leakage_issues[:30])
    WORKSPACE_QC_REPORT.parent.mkdir(parents=True, exist_ok=True)
    WORKSPACE_QC_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    scan_lines = [
        "Phase 6 assisted annotation workspace leakage scan",
        "",
        f"result: {'PASS' if leakage_passed else 'FAIL'}",
    ]
    if leakage_issues:
        scan_lines.extend(f"- {issue}" for issue in leakage_issues)
    else:
        scan_lines.append("No restricted patterns found in public workspace CSVs/docs.")
    WORKSPACE_LEAKAGE_REPORT.write_text("\n".join(scan_lines) + "\n", encoding="utf-8")


def main() -> int:
    if not WORKING_CSV.exists():
        print(f"FAIL: official working CSV not found: {WORKING_CSV}", file=sys.stderr)
        return 1

    ensure_workspace_dirs()
    write_readme()

    if not ASSISTED_WORKING_CSV.exists():
        shutil.copy2(WORKING_CSV, ASSISTED_WORKING_CSV)
    if not ASSISTED_BACKUP_INITIAL.exists():
        shutil.copy2(WORKING_CSV, ASSISTED_BACKUP_INITIAL)

    if not IMPORT_LOG_CSV.exists():
        write_csv(IMPORT_LOG_CSV, [], IMPORT_LOG_COLUMNS)
    if not ALL_NEEDS_REVIEW_CSV.exists():
        write_csv(ALL_NEEDS_REVIEW_CSV, [], NEEDS_REVIEW_INDEX_COLUMNS)
    if not NEEDS_REVIEW_SUMMARY_CSV.exists():
        write_csv(NEEDS_REVIEW_SUMMARY_CSV, [], ["source_range_id", "needs_review_count"])

    assisted_rows = len(read_csv(ASSISTED_WORKING_CSV)) if ASSISTED_WORKING_CSV.exists() else 0
    if assisted_rows != EXPECTED_ROWS:
        print(f"WARN: assisted working CSV has {assisted_rows} rows; expected {EXPECTED_ROWS}")

    leakage_passed, leakage_issues = scan_workspace_leakage()
    write_workspace_qc(leakage_passed, leakage_issues)

    print("Phase 6 assisted annotation workspace setup: PASS")
    print(f"workspace: {WORKSPACE_ROOT.relative_to(PROJECT_ROOT)}")
    print(f"assisted working CSV: {ASSISTED_WORKING_CSV.relative_to(PROJECT_ROOT)}")
    print(f"QC report: {WORKSPACE_QC_REPORT.relative_to(PROJECT_ROOT)}")
    print(f"leakage scan: {'PASS' if leakage_passed else 'FAIL'}")
    return 0 if leakage_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
