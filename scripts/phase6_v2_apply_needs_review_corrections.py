#!/usr/bin/env python3
"""Apply corrected needs-review rows to the v2 assisted workspace."""

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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--range-id", required=True)
    parser.add_argument("--correction-csv")
    args = parser.parse_args()
    correction_csv = Path(args.correction_csv) if args.correction_csv else None
    if correction_csv is None:
        search_roots = [
            WORKSPACE / "corrections_from_streamlit" / args.range_id,
            WORKSPACE / "incoming_from_downloads" / args.range_id / "needs_review_streamlit_v2_clean",
            WORKSPACE / "incoming_from_downloads" / args.range_id / f"{args.range_id}_needs_review_streamlit",
        ]
        candidates: list[Path] = []
        for root in search_roots:
            if root.exists():
                candidates = sorted(root.rglob("*correction*.csv"))
                if candidates:
                    break
        if not candidates:
            searched = "\n".join(str(root) for root in search_roots)
            raise FileNotFoundError(
                f"No correction CSV found for {args.range_id}. Searched:\n{searched}"
            )
        correction_csv = candidates[0]
    if not correction_csv.exists():
        raise FileNotFoundError(correction_csv)
    corrections = read_csv(correction_csv)
    working = read_csv(ASSISTED)
    fieldnames = list(working[0].keys())
    corrections_by_id = {row["expanded_image_id"]: row for row in corrections}
    backup = ASSISTED.with_name(f"{ASSISTED.stem}_pre_correction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    shutil.copy2(ASSISTED, backup)
    updated = 0
    for row in working:
        correction = corrections_by_id.get(row["expanded_image_id"])
        if not correction:
            continue
        for key, value in correction.items():
            if key in row:
                row[key] = value
        row["correction_applied"] = "yes"
        updated += 1
    write_csv(ASSISTED, working, fieldnames)
    write_csv(SUMMARY, working, fieldnames)
    print(f"applied {updated} corrections from {correction_csv}")


if __name__ == "__main__":
    main()
