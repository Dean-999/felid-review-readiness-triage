#!/usr/bin/env python3
"""Second-pass clarity cleanup for the Phase19 iNaturalist Bobcat queue."""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_CSV = (
    PROJECT_ROOT
    / "outputs/phase19/phase19_bobcat_inat_daylight_clean_queue/phase19_bobcat_inat_daylight_nonblur_review_queue.csv"
)
OUT_DIR = PROJECT_ROOT / "outputs/phase19/phase19_bobcat_inat_clarity_second_pass"
QUEUE_CSV = OUT_DIR / "phase19_bobcat_inat_clarity_second_pass_review_queue.csv"
SAMPLE_CSV = OUT_DIR / "phase19_bobcat_inat_clarity_second_pass_sample100.csv"
AUDIT_JSON = OUT_DIR / "phase19_bobcat_inat_clarity_second_pass_audit.json"

OUT_FIELDS_EXTRA = [
    "phase19_clarity_second_pass_score",
    "phase19_clarity_second_pass_tier",
    "phase19_clarity_second_pass_reasons",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def f(row: dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        text = str(row.get(key, "")).strip()
        if text in {"", "nan", "None"}:
            return default
        return float(text)
    except (TypeError, ValueError):
        return default


def clarity_gate(row: dict[str, str]) -> tuple[bool, str, float, str]:
    reasons: list[str] = []
    gradient = f(row, "gradient_p90")
    laplacian = f(row, "laplacian_var")
    contrast = f(row, "contrast_std")
    color = f(row, "colorfulness_proxy")
    dark = f(row, "dark_clip_fraction", 1.0)
    bright = f(row, "bright_clip_fraction", 1.0)
    entropy = f(row, "entropy")
    megapixels = f(row, "image_megapixels")
    bytes_count = f(row, "download_bytes")
    width = f(row, "image_width")
    height = f(row, "image_height")
    min_dim = min(width, height) if width and height else 0.0

    if gradient < 30:
        reasons.append("gradient_p90_lt_30")
    if laplacian < 320:
        reasons.append("laplacian_var_lt_320")
    if contrast < 48:
        reasons.append("contrast_std_lt_48")
    if color < 22:
        reasons.append("colorfulness_lt_22")
    if dark > 0.14:
        reasons.append("dark_clip_gt_0_14")
    if bright > 0.16:
        reasons.append("bright_clip_gt_0_16")
    if entropy < 5.2:
        reasons.append("entropy_lt_5_2")

    score = 0.0
    score += min(24.0, gradient / 2.2)
    score += min(28.0, laplacian / 24.0)
    score += min(18.0, contrast / 3.2)
    score += min(12.0, color / 3.0)
    score += min(8.0, entropy)
    score += max(0.0, 6.0 - dark * 28.0)
    score += max(0.0, 4.0 - bright * 14.0)
    score += 7.0 if row.get("phase19_daylight_nonblur_tier") == "tier1_high_resolution_daylight_nonblur" else 0.0
    score += 5.0 if min_dim >= 900 and megapixels >= 1.2 and bytes_count >= 120_000 else 0.0

    if reasons:
        return False, "reject_second_pass_proxy", round(score, 4), ";".join(reasons)
    if row.get("phase19_daylight_nonblur_tier") == "tier1_high_resolution_daylight_nonblur":
        return True, "tier1_second_pass_high_clarity", round(score, 4), ""
    return True, "tier2_second_pass_clear_review", round(score, 4), ""


def sort_key(row: dict[str, Any]) -> tuple[int, float, float, str]:
    tier_rank = {
        "tier1_second_pass_high_clarity": 0,
        "tier2_second_pass_clear_review": 1,
    }.get(str(row.get("phase19_clarity_second_pass_tier", "")), 9)
    return (
        tier_rank,
        -f(row, "phase19_clarity_second_pass_score"),
        -f(row, "phase19_daylight_nonblur_score"),
        str(row.get("phase19_review_id", "")),
    )


def build() -> dict[str, Any]:
    rows = read_csv(INPUT_CSV)
    kept: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for row in rows:
        keep, tier, score, reasons = clarity_gate(row)
        out = dict(row)
        out["phase19_clarity_second_pass_score"] = f"{score:.4f}"
        out["phase19_clarity_second_pass_tier"] = tier
        out["phase19_clarity_second_pass_reasons"] = reasons
        out["phase19_manual_decision"] = ""
        out["phase19_manual_reject_reason"] = ""
        out["phase19_manual_notes"] = ""
        out["phase19_manual_audited_at_utc"] = ""
        if keep:
            kept.append(out)
        else:
            rejected.append(out)
    kept.sort(key=sort_key)
    fieldnames = list(rows[0].keys()) if rows else []
    for column in OUT_FIELDS_EXTRA:
        if column not in fieldnames:
            fieldnames.append(column)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(QUEUE_CSV, kept, fieldnames)
    write_csv(SAMPLE_CSV, kept[:100], fieldnames)
    audit = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "input_csv": str(INPUT_CSV.relative_to(PROJECT_ROOT)),
        "input_rows": len(rows),
        "kept_rows": len(kept),
        "rejected_rows": len(rejected),
        "sample100_rows": min(100, len(kept)),
        "kept_tier_counts": dict(Counter(row["phase19_clarity_second_pass_tier"] for row in kept)),
        "kept_original_tier_counts": dict(Counter(row["phase19_daylight_nonblur_tier"] for row in kept)),
        "top_reject_reason_counts": dict(Counter(row["phase19_clarity_second_pass_reasons"] for row in rejected).most_common(30)),
        "rule": {
            "gradient_p90": ">= 30",
            "laplacian_var": ">= 320",
            "contrast_std": ">= 48",
            "colorfulness_proxy": ">= 22",
            "dark_clip_fraction": "<= 0.14",
            "bright_clip_fraction": "<= 0.16",
            "entropy": ">= 5.2",
        },
        "outputs": {
            "queue_csv": str(QUEUE_CSV.relative_to(PROJECT_ROOT)),
            "sample_csv": str(SAMPLE_CSV.relative_to(PROJECT_ROOT)),
            "audit_json": str(AUDIT_JSON.relative_to(PROJECT_ROOT)),
        },
        "claim_boundary": "Second-pass clarity proxy queue; human CLEAR is still required before final inclusion.",
    }
    AUDIT_JSON.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return audit


def main() -> int:
    print(json.dumps(build(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
