#!/usr/bin/env python3
"""Build Bobcat-wild blur-first review queue.

This queue answers only one question: is the animal image likely not blurred?
It is not a final selection list and does not evaluate area, night/IR, color,
occlusion, partial body, or identity evidence. It only ranks likely non-blurry
images for human review.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT = PROJECT_ROOT / "outputs/phase19/phase19_bobcat_wild_rescue_review_queue/bobcat_wild_full_rescue_ranked_queue.csv"
OUT_DIR = PROJECT_ROOT / "outputs/phase19/phase19_bobcat_wild_blur_gate"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def f(row: dict[str, str], column: str) -> float:
    try:
        return float(row.get(column, "") or "nan")
    except ValueError:
        return float("nan")


def text_reasons(row: dict[str, str]) -> str:
    return ";".join(
        [
            row.get("phase19_prefilter_reject_reasons", ""),
            row.get("object_aware_reject_reasons", ""),
        ]
    )


def blur_gate(row: dict[str, str]) -> tuple[bool, str, str, float]:
    reasons = text_reasons(row)
    reject: list[str] = []
    score = 0.0
    whole_lap = f(row, "laplacian_var")
    whole_grad = f(row, "gradient_p90")
    crop_lap = f(row, "animal_crop_laplacian_var")
    crop_grad = f(row, "animal_crop_gradient_p90")
    contrast = f(row, "contrast_std")

    score += max(0.0, min(45.0, (whole_lap - 350.0) / 45.0))
    score += max(0.0, min(35.0, (whole_grad - 10.0) * 1.8))
    score += max(0.0, min(10.0, (contrast - 30.0) / 3.0))
    crop_lap = f(row, "animal_crop_laplacian_var")
    crop_grad = f(row, "animal_crop_gradient_p90")
    if crop_lap == crop_lap and crop_grad == crop_grad:
        score += max(0.0, min(25.0, (crop_lap - 250.0) / 50.0))
        score += max(0.0, min(20.0, (crop_grad - 12.0) * 1.5))

    if crop_lap == crop_lap and crop_grad == crop_grad and crop_lap >= 900 and crop_grad >= 28:
        tier = "crop_supported_nonblur"
    elif whole_lap >= 1400 and whole_grad >= 32:
        tier = "whole_image_very_sharp"
    elif whole_lap >= 700 and whole_grad >= 20:
        tier = "whole_image_likely_nonblur"
    else:
        tier = "manual_blur_check"

    # Only exclude severe blur-risk. Do not exclude for night/IR, low color,
    # low contrast, small subject, no YOLO box, or partial body at this stage.
    if whole_lap < 450 and whole_grad < 14:
        reject.append("severe_whole_image_blur_risk")
    if crop_lap == crop_lap and crop_grad == crop_grad and crop_lap < 180 and crop_grad < 10:
        reject.append("severe_animal_crop_blur_risk")
    return not reject, tier, ";".join(reject), round(score, 4)


def main() -> None:
    rows = read_csv(INPUT)
    out_rows: list[dict[str, Any]] = []
    all_fields = list(rows[0].keys()) + [
        "bobcat_wild_blur_gate_decision",
        "bobcat_wild_blur_gate_tier",
        "bobcat_wild_blur_gate_reject_reasons",
        "bobcat_wild_blur_score",
    ]
    for row in rows:
        keep, tier, reject, score = blur_gate(row)
        row = dict(row)
        row["bobcat_wild_blur_gate_decision"] = "review_nonblur_candidate" if keep else "exclude_blur_risk"
        row["bobcat_wild_blur_gate_tier"] = tier
        row["bobcat_wild_blur_gate_reject_reasons"] = reject
        row["bobcat_wild_blur_score"] = score
        row["phase19_manual_decision"] = ""
        row["phase19_manual_reject_reason"] = ""
        row["phase19_manual_notes"] = ""
        row["phase19_manual_audited_at_utc"] = ""
        if keep:
            out_rows.append(row)
    out_rows.sort(
        key=lambda row: (
            {
                "crop_supported_nonblur": 0,
                "whole_image_very_sharp": 1,
                "whole_image_likely_nonblur": 2,
                "manual_blur_check": 3,
            }.get(
                row["bobcat_wild_blur_gate_tier"], 9
            ),
            -float(row.get("bobcat_wild_blur_score") or 0),
            row.get("phase19_review_id", ""),
        )
    )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(OUT_DIR / "bobcat_wild_blur_gate_review_queue.csv", out_rows, all_fields)
    audit = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "input_rows": len(rows),
        "review_nonblur_candidate_rows": len(out_rows),
        "excluded_blur_risk_rows": len(rows) - len(out_rows),
        "source_counts": dict(Counter(row["source_dataset"] for row in out_rows)),
        "tier_counts": dict(Counter(row["bobcat_wild_blur_gate_tier"] for row in out_rows)),
        "output": str((OUT_DIR / "bobcat_wild_blur_gate_review_queue.csv").relative_to(PROJECT_ROOT)),
        "rule": "First gate is animal/scene non-blur only; downstream gates handle area, partial body, occlusion, and final freeze.",
    }
    (OUT_DIR / "bobcat_wild_blur_gate_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote Bobcat wild blur gate queue to {OUT_DIR.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
