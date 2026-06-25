"""Shared paths and helpers for Phase 6 assisted annotation workspace."""

from __future__ import annotations

import csv
import re
import shutil
from collections import Counter
from datetime import datetime
from pathlib import Path

from phase6_unique_500_annotation_schema import (
    PUBLIC_COLUMNS,
    find_leakage_issues,
    path_is_safe_public_path,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

WORKSPACE_ROOT = (
    PROJECT_ROOT
    / "outputs/czechlynx/phase6/annotation_review_packages/phase6_unique_500_assisted_annotation_workspace"
)
ASSISTED_WORKING_DIR = WORKSPACE_ROOT / "assisted_working"
ASSISTED_WORKING_CSV = ASSISTED_WORKING_DIR / "czechlynx_phase6_unique_500_assisted_working.csv"
ASSISTED_BACKUP_INITIAL = ASSISTED_WORKING_DIR / "czechlynx_phase6_unique_500_assisted_working_backup_initial.csv"
IMPORT_LOG_CSV = ASSISTED_WORKING_DIR / "import_log.csv"
INCOMING_DIR = WORKSPACE_ROOT / "incoming_from_downloads"
CORRECTIONS_DIR = WORKSPACE_ROOT / "corrections_from_streamlit"
IMPORTED_RANGES_DIR = WORKSPACE_ROOT / "imported_ranges"
NEEDS_REVIEW_INDEX_DIR = WORKSPACE_ROOT / "needs_review_index"
ALL_NEEDS_REVIEW_CSV = NEEDS_REVIEW_INDEX_DIR / "all_needs_review_rows.csv"
NEEDS_REVIEW_SUMMARY_CSV = NEEDS_REVIEW_INDEX_DIR / "needs_review_by_range_summary.csv"
WORKSPACE_QC_DIR = WORKSPACE_ROOT / "qc"
WORKSPACE_QC_REPORT = WORKSPACE_QC_DIR / "workspace_qc_report.txt"
WORKSPACE_LEAKAGE_REPORT = WORKSPACE_QC_DIR / "leakage_scan_report.txt"
ASSISTED_AUDIT_SUMMARY = WORKSPACE_QC_DIR / "assisted_working_audit_summary.txt"

IMPORT_LOG_COLUMNS = [
    "range_id",
    "start_index",
    "end_index",
    "annotated_csv",
    "needs_review_csv",
    "correction_csv",
    "rows_imported",
    "needs_review_rows",
    "complete_rows",
    "import_status",
    "timestamp",
    "notes",
]

NEEDS_REVIEW_INDEX_COLUMNS = PUBLIC_COLUMNS + ["source_range_id"]

RANGE_ID_PATTERN = re.compile(r"^range_(\d{3})_(\d{3})$")

IMPORT_UPDATE_FIELDS = [
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


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(f)]


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def parse_range_id(range_id: str) -> tuple[int, int]:
    match = RANGE_ID_PATTERN.match(range_id)
    if not match:
        raise ValueError(f"Invalid range_id: {range_id!r} (expected range_NNN_NNN)")
    start_index = int(match.group(1))
    end_index = int(match.group(2))
    if end_index < start_index:
        raise ValueError(f"Invalid range_id: end_index < start_index for {range_id}")
    return start_index, end_index


def ensure_workspace_dirs() -> None:
    for path in [
        ASSISTED_WORKING_DIR,
        INCOMING_DIR,
        CORRECTIONS_DIR,
        IMPORTED_RANGES_DIR,
        NEEDS_REVIEW_INDEX_DIR,
        WORKSPACE_QC_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)


def backup_assisted_working(prefix: str = "backup") -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = ASSISTED_WORKING_DIR / f"czechlynx_phase6_unique_500_assisted_working_{prefix}_{timestamp}.csv"
    shutil.copy2(ASSISTED_WORKING_CSV, backup_path)
    return backup_path


def merge_annotation_rows(
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


def append_import_log(entry: dict[str, str]) -> None:
    rows: list[dict[str, str]] = []
    if IMPORT_LOG_CSV.exists():
        rows = read_csv(IMPORT_LOG_CSV)
    rows.append(entry)
    write_csv(IMPORT_LOG_CSV, rows, IMPORT_LOG_COLUMNS)


def rebuild_needs_review_index(working_rows: list[dict[str, str]], import_log_rows: list[dict[str, str]]) -> None:
    range_by_id: dict[str, str] = {}
    for log_row in import_log_rows:
        if log_row.get("import_status") != "PASS":
            continue
        range_id = log_row.get("range_id", "")
        if not range_id:
            continue
        try:
            start_index, end_index = parse_range_id(range_id)
        except ValueError:
            continue
        for idx in range(start_index, end_index + 1):
            range_by_id[f"czlx_phase6_expanded_{idx:04d}"] = range_id

    needs_review_rows: list[dict[str, str]] = []
    summary_counter: Counter[str] = Counter()
    for row in working_rows:
        if row.get("annotation_status") != "needs_review":
            continue
        out = dict(row)
        out["source_range_id"] = range_by_id.get(row["expanded_image_id"], "")
        needs_review_rows.append(out)
        summary_counter[out["source_range_id"] or "<unknown>"] += 1

    write_csv(ALL_NEEDS_REVIEW_CSV, needs_review_rows, NEEDS_REVIEW_INDEX_COLUMNS)
    summary_rows = [
        {"source_range_id": range_id, "needs_review_count": count}
        for range_id, count in sorted(summary_counter.items())
    ]
    write_csv(
        NEEDS_REVIEW_SUMMARY_CSV,
        summary_rows,
        ["source_range_id", "needs_review_count"],
    )


def scan_public_csv_leakage(path: Path) -> list[str]:
    issues: list[str] = []
    rel = path.relative_to(PROJECT_ROOT).as_posix()
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row_id = row.get("expanded_image_id", "?")
            for col, value in row.items():
                if col == "review_image_path_local" and path_is_safe_public_path(value or ""):
                    continue
                issues.extend(find_leakage_issues(value or "", context=f"{rel}:{row_id}:{col}"))
    return issues


def scan_workspace_leakage() -> tuple[bool, list[str]]:
    issues: list[str] = []
    scan_roots = [
        ASSISTED_WORKING_DIR,
        NEEDS_REVIEW_INDEX_DIR,
        WORKSPACE_ROOT / "README.md",
    ]
    for root in scan_roots:
        if root.is_file():
            paths = [root]
        elif root.exists():
            paths = [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in {".csv", ".md", ".txt"}]
        else:
            continue
        for path in paths:
            if "backup" in path.name or path.name == "import_log.csv":
                continue
            if path.suffix.lower() == ".csv":
                issues.extend(scan_public_csv_leakage(path))
            else:
                rel = path.relative_to(PROJECT_ROOT).as_posix()
                issues.extend(find_leakage_issues(path.read_text(encoding="utf-8"), context=rel))
    return not issues, issues


def incoming_range_dir(range_id: str) -> Path:
    return INCOMING_DIR / range_id


def correction_range_dir(range_id: str) -> Path:
    return CORRECTIONS_DIR / range_id


def default_correction_csv(range_id: str) -> Path:
    local = correction_range_dir(range_id) / f"{range_id}_needs_review_corrections_working.csv"
    if local.exists():
        return local
    return (
        incoming_range_dir(range_id)
        / "needs_review_streamlit"
        / f"{range_id}_needs_review_corrections_working.csv"
    )
