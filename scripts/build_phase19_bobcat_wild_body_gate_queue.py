#!/usr/bin/env python3
"""Build Bobcat-wild body-completeness gate after blur gate.

This gate removes only evidence-backed incomplete-body risks: detector edge
touch and YOLO animal boxes cut by image borders. Rows without reliable boxes
are retained for manual body-completeness review.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BLUR_QUEUE = PROJECT_ROOT / "outputs/phase19/phase19_bobcat_wild_blur_gate/bobcat_wild_blur_gate_review_queue.csv"
PREFILTER = PROJECT_ROOT / "outputs/phase19/phase19_strict_photo_prefilter/bobcat_wild_camera_trap_strict_photo_prefilter.csv"
OBJECT_AWARE = (
    PROJECT_ROOT
    / "outputs/phase19/phase19_object_aware_bobcat_wild_full_strict/bobcat_wild_camera_trap_object_aware_all_scored.csv"
)
OUT_DIR = PROJECT_ROOT / "outputs/phase19/phase19_bobcat_wild_body_gate"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def lookup(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for row in rows:
        for key in [row.get("phase19_review_id", ""), row.get("source_image_path", ""), row.get("source_candidate_id", "")]:
            if key:
                out[key] = row
    return out


def f(row: dict[str, Any], key: str) -> float | None:
    try:
        value = row.get(key, "")
        if value in {"", None}:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def body_gate(row: dict[str, Any]) -> tuple[str, str, str]:
    reasons: list[str] = []
    md_edge = str(row.get("phase14_md_edge_touch", "")).lower() == "true"
    if md_edge:
        reasons.append("megadetector_edge_touch")

    x1 = f(row, "animal_bbox_x1")
    y1 = f(row, "animal_bbox_y1")
    x2 = f(row, "animal_bbox_x2")
    y2 = f(row, "animal_bbox_y2")
    width = f(row, "image_width")
    height = f(row, "image_height")
    has_yolo_box = all(v is not None for v in [x1, y1, x2, y2, width, height])
    if has_yolo_box and width and height:
        margin_x = width * 0.025
        margin_y = height * 0.025
        touches = []
        if x1 <= margin_x:
            touches.append("left")
        if y1 <= margin_y:
            touches.append("top")
        if x2 >= width - margin_x:
            touches.append("right")
        if y2 >= height - margin_y:
            touches.append("bottom")
        if touches:
            reasons.append("yolo_animal_box_touches_" + "_".join(touches))

    if reasons:
        return "exclude_incomplete_body_risk", "edge_or_cut_body_risk", ";".join(reasons)
    if has_yolo_box or row.get("phase14_md_area_fraction", "") not in {"", None}:
        return "review_body_candidate", "box_supported_body_check", ""
    return "review_body_candidate", "manual_body_check_required", ""


def main() -> None:
    blur_rows = read_csv(BLUR_QUEUE)
    pre_lookup = lookup(read_csv(PREFILTER))
    obj_lookup = lookup(read_csv(OBJECT_AWARE))
    output: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    fieldnames = list(blur_rows[0].keys())
    for extra in [
        "phase14_md_edge_touch",
        "animal_bbox_x1",
        "animal_bbox_y1",
        "animal_bbox_x2",
        "animal_bbox_y2",
        "animal_width_fraction",
        "animal_height_fraction",
        "bobcat_wild_body_gate_decision",
        "bobcat_wild_body_gate_tier",
        "bobcat_wild_body_gate_reject_reasons",
    ]:
        if extra not in fieldnames:
            fieldnames.append(extra)

    for row in blur_rows:
        merged = dict(row)
        pre = pre_lookup.get(row.get("phase19_review_id", "")) or pre_lookup.get(row.get("source_image_path", "")) or {}
        obj = obj_lookup.get(row.get("phase19_review_id", "")) or obj_lookup.get(row.get("source_image_path", "")) or {}
        for key in [
            "phase14_md_edge_touch",
            "phase14_md_width_fraction",
            "phase14_md_height_fraction",
            "animal_bbox_x1",
            "animal_bbox_y1",
            "animal_bbox_x2",
            "animal_bbox_y2",
            "animal_width_fraction",
            "animal_height_fraction",
        ]:
            if key in pre and pre.get(key, "") != "":
                merged[key] = pre[key]
            if key in obj and obj.get(key, "") != "":
                merged[key] = obj[key]
        decision, tier, reject = body_gate(merged)
        merged["bobcat_wild_body_gate_decision"] = decision
        merged["bobcat_wild_body_gate_tier"] = tier
        merged["bobcat_wild_body_gate_reject_reasons"] = reject
        merged["phase19_manual_decision"] = ""
        merged["phase19_manual_reject_reason"] = ""
        merged["phase19_manual_notes"] = ""
        merged["phase19_manual_audited_at_utc"] = ""
        if decision == "review_body_candidate":
            output.append(merged)
        else:
            excluded.append(merged)

    output.sort(
        key=lambda row: (
            {"box_supported_body_check": 0, "manual_body_check_required": 1}.get(row["bobcat_wild_body_gate_tier"], 9),
            -float(row.get("bobcat_wild_blur_score") or 0),
            row.get("phase19_review_id", ""),
        )
    )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(OUT_DIR / "bobcat_wild_blur_pass_body_gate_queue.csv", output, fieldnames)
    write_csv(OUT_DIR / "bobcat_wild_body_incomplete_risk_excluded.csv", excluded, fieldnames)
    audit = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "input_blur_gate_rows": len(blur_rows),
        "body_gate_review_rows": len(output),
        "excluded_incomplete_body_risk_rows": len(excluded),
        "review_tier_counts": dict(Counter(row["bobcat_wild_body_gate_tier"] for row in output)),
        "excluded_reason_counts": dict(Counter(row["bobcat_wild_body_gate_reject_reasons"] for row in excluded)),
        "source_counts": dict(Counter(row["source_dataset"] for row in output)),
        "output": str((OUT_DIR / "bobcat_wild_blur_pass_body_gate_queue.csv").relative_to(PROJECT_ROOT)),
        "excluded": str((OUT_DIR / "bobcat_wild_body_incomplete_risk_excluded.csv").relative_to(PROJECT_ROOT)),
        "rule": "Remove only evidence-backed incomplete-body risks; rows without boxes remain manual body-check candidates.",
    }
    (OUT_DIR / "bobcat_wild_body_gate_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote Bobcat wild body gate queue to {OUT_DIR.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
