#!/usr/bin/env python3
"""Recompute Bobcat wild subject-area counts with manual bbox annotations."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_CSV = (
    PROJECT_ROOT
    / "outputs/phase19/phase19_bobcat_wild_body_gate/bobcat_wild_blur_pass_body_gate_queue.csv"
)
DEFAULT_MANUAL_CSV = (
    PROJECT_ROOT
    / "outputs/phase19/phase19_bobcat_wild_manual_bbox/phase19_bobcat_wild_manual_bbox_working.csv"
)
DEFAULT_OUT_DIR = PROJECT_ROOT / "outputs/phase19/phase19_bobcat_wild_manual_bbox_area_counts"
THRESHOLDS = [0.10, 0.15, 0.20, 0.30]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def maybe_float(value: object) -> float | None:
    try:
        text = str(value).strip()
        if text in {"", "nan", "None"}:
            return None
        return float(text)
    except (TypeError, ValueError):
        return None


def best_area(row: dict[str, Any]) -> tuple[float | None, str]:
    sources = [
        ("manual_bbox", row.get("manual_bbox_area_fraction", "")),
        ("yolo_animal_bbox", row.get("animal_area_fraction", "")),
        ("megadetector", row.get("phase14_md_area_fraction", "")),
    ]
    for source, value in sources:
        area = maybe_float(value)
        if area is not None and area > 0:
            return area, source
    return None, "unknown"


def area_bin(area: float | None) -> str:
    if area is None:
        return "unknown"
    if area < 0.10:
        return "lt_10pct"
    if area < 0.15:
        return "10_15pct"
    if area < 0.20:
        return "15_20pct"
    if area < 0.30:
        return "20_30pct"
    return "ge_30pct"


def merge_rows(source_rows: list[dict[str, str]], manual_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    manual_by_id = {row.get("phase19_review_id", ""): row for row in manual_rows if row.get("phase19_review_id", "")}
    out: list[dict[str, Any]] = []
    for row in source_rows:
        merged: dict[str, Any] = dict(row)
        manual = manual_by_id.get(row.get("phase19_review_id", ""), {})
        for column in [
            "manual_bbox_status",
            "manual_bbox_x1",
            "manual_bbox_y1",
            "manual_bbox_x2",
            "manual_bbox_y2",
            "manual_bbox_area_fraction",
            "manual_bbox_notes",
            "manual_bbox_audited_at_utc",
        ]:
            merged[column] = manual.get(column, "")
        area, source = best_area(merged)
        merged["best_subject_area_fraction"] = "" if area is None else f"{area:.8f}"
        merged["best_subject_area_source"] = source
        merged["best_subject_area_bin"] = area_bin(area)
        out.append(merged)
    return out


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    known_rows = [row for row in rows if row["best_subject_area_source"] != "unknown"]
    source_counter = Counter(row["best_subject_area_source"] for row in rows)
    bin_counter = Counter(row["best_subject_area_bin"] for row in rows)
    threshold_counts: dict[str, Any] = {}
    for threshold in THRESHOLDS:
        label = f"ge_{int(threshold * 100)}pct"
        passed = [
            row
            for row in known_rows
            if (maybe_float(row.get("best_subject_area_fraction", "")) or 0.0) >= threshold
        ]
        threshold_counts[label] = {
            "rows": len(passed),
            "by_source_dataset": dict(Counter(row.get("source_dataset", "") for row in passed)),
            "by_area_source": dict(Counter(row.get("best_subject_area_source", "") for row in passed)),
        }
    return {
        "built_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "input_rows": len(rows),
        "known_area_rows": len(known_rows),
        "unknown_area_rows": len(rows) - len(known_rows),
        "area_source_counts": dict(source_counter),
        "area_bin_counts": dict(bin_counter),
        "threshold_counts": threshold_counts,
        "manual_bbox_status_counts": dict(Counter(row.get("manual_bbox_status", "") for row in rows)),
        "important_boundary": (
            "Counts are exact for rows with an available manual, YOLO, or MegaDetector bbox. "
            "Rows with best_subject_area_source=unknown still have no measurable animal box."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-csv", type=Path, default=DEFAULT_SOURCE_CSV)
    parser.add_argument("--manual-csv", type=Path, default=DEFAULT_MANUAL_CSV)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_rows = read_csv(args.source_csv)
    manual_rows = read_csv(args.manual_csv) if args.manual_csv.exists() else []
    merged = merge_rows(source_rows, manual_rows)
    summary = summarize(merged)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    scored_csv = args.output_dir / "bobcat_wild_area_recomputed_with_manual_bbox.csv"
    audit_json = args.output_dir / "bobcat_wild_area_recomputed_with_manual_bbox_audit.json"
    fieldnames = list(merged[0].keys()) if merged else []
    write_csv(scored_csv, merged, fieldnames)
    summary["outputs"] = {
        "scored_csv": str(scored_csv.relative_to(PROJECT_ROOT)),
        "audit_json": str(audit_json.relative_to(PROJECT_ROOT)),
    }
    audit_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
