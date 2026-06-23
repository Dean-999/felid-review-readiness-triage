#!/usr/bin/env python3
"""Import an assistant-annotated range CSV into the v2 assisted workspace."""

from __future__ import annotations

import argparse
import csv
import shutil
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_NAME = "phase6_unique_500_v2_balanced"
WORKSPACE = PROJECT_ROOT / f"outputs/czechlynx/phase6/annotation_review_packages/{WORKFLOW_NAME}/assisted_annotation_workspace"
ASSISTED = WORKSPACE / "assisted_working" / f"czechlynx_{WORKFLOW_NAME}_assisted_working.csv"
SUMMARY = WORKSPACE / "assisted_working" / f"czechlynx_{WORKFLOW_NAME}_working_summary.csv"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def find_annotated_csv(range_dir: Path, range_id: str) -> Path:
    candidates = sorted(range_dir.rglob(f"*{range_id}*annotated*.csv"))
    candidates = [p for p in candidates if "needs_review" not in p.name]
    if not candidates:
        raise FileNotFoundError(f"No annotated CSV found for {range_id} in {range_dir}")
    return candidates[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--range-id", required=True)
    args = parser.parse_args()
    range_dir = WORKSPACE / "incoming_from_downloads" / args.range_id
    annotated_csv = find_annotated_csv(range_dir, args.range_id)
    incoming = read_csv(annotated_csv)
    working = read_csv(ASSISTED)
    fieldnames = list(working[0].keys())
    incoming_by_id = {row["expanded_image_id"]: row for row in incoming}
    backup = ASSISTED.with_name(f"{ASSISTED.stem}_pre_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    shutil.copy2(ASSISTED, backup)
    updated = 0
    needs_review = []
    for row in working:
        incoming_row = incoming_by_id.get(row["expanded_image_id"])
        if not incoming_row:
            continue
        for key, value in incoming_row.items():
            if key in row:
                row[key] = value
        row["imported_range_id"] = args.range_id
        updated += 1
        if row.get("annotation_status") == "needs_review":
            needs_review.append(row)
    write_csv(ASSISTED, working, fieldnames)
    write_csv(SUMMARY, working, fieldnames)
    index_path = WORKSPACE / "needs_review_index" / f"{args.range_id}_needs_review_index.csv"
    write_csv(index_path, needs_review, fieldnames)
    imported_dir = WORKSPACE / "imported_ranges" / args.range_id
    imported_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(annotated_csv, imported_dir / annotated_csv.name)
    print(f"imported {updated} rows from {annotated_csv}")
    print(f"needs_review rows indexed: {len(needs_review)}")


if __name__ == "__main__":
    main()
