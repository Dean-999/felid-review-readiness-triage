#!/usr/bin/env python3
"""Build a full Bobcat-wild rescue review queue.

This is deliberately not an automatic final selector. Earlier object-aware
filters were too brittle for camera-trap bobcats: YOLO misses animals, and crop
sharpness can still be fooled. This script restores the original project logic:
keep the full reservoir, rank it with multiple weak signals, and create a
stratified human-calibration sample.
"""

from __future__ import annotations

import csv
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "outputs/phase19/phase19_bobcat_wild_rescue_review_queue"
MANIFEST = (
    PROJECT_ROOT
    / "data/phase19_candidate_pools/bobcat_wild_camera_trap/bobcat_wild_camera_trap_download_manifest.csv"
)
PREFILTER = (
    PROJECT_ROOT
    / "outputs/phase19/phase19_strict_photo_prefilter/bobcat_wild_camera_trap_strict_photo_prefilter.csv"
)
OBJECT_AWARE = (
    PROJECT_ROOT
    / "outputs/phase19/phase19_object_aware_bobcat_wild_full_strict/bobcat_wild_camera_trap_object_aware_all_scored.csv"
)

OUTPUT_FIELDS = [
    "phase19_review_id",
    "phase19_cell",
    "source_dataset",
    "source_platform",
    "source_candidate_id",
    "source_image_path",
    "source_image_uri",
    "species",
    "domain_label",
    "license",
    "attribution",
    "download_status",
    "bytes",
    "image_width",
    "image_height",
    "image_megapixels",
    "contrast_std",
    "gradient_p90",
    "laplacian_var",
    "entropy",
    "brightness_mean",
    "saturation_mean",
    "grayscale_proxy",
    "phase14_md_area_fraction",
    "subject_area_rule",
    "technical_quality_rule",
    "phase19_prefilter_reject_reasons",
    "object_aware_decision",
    "object_aware_reject_reasons",
    "yolo_class",
    "yolo_confidence",
    "animal_area_fraction",
    "animal_crop_laplacian_var",
    "animal_crop_gradient_p90",
    "bobcat_wild_rescue_score",
    "bobcat_wild_rescue_tier",
    "bobcat_wild_review_sample_role",
    "phase19_manual_decision",
    "phase19_manual_reject_reason",
    "phase19_manual_notes",
    "phase19_manual_audited_at_utc",
    "phase19_claim_boundary",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def safe_float(value: Any, default: float = math.nan) -> float:
    try:
        out = float(value)
        return out if math.isfinite(out) else default
    except (TypeError, ValueError):
        return default


def norm(value: Any, low: float, high: float) -> float:
    x = safe_float(value, math.nan)
    if not math.isfinite(x):
        return 0.0
    return max(0.0, min(1.0, (x - low) / (high - low)))


def build_lookup(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    lookup: dict[str, dict[str, str]] = {}
    for row in rows:
        for key in [row.get("phase19_review_id", ""), row.get("source_image_path", ""), row.get("source_candidate_id", "")]:
            if key:
                lookup[key] = row
    return lookup


def rescue_score(row: dict[str, Any]) -> tuple[float, str]:
    score = 0.0
    score += 18.0 * norm(row.get("bytes"), 250_000, 1_400_000)
    score += 12.0 * norm(row.get("image_megapixels"), 0.8, 6.0)
    score += 14.0 * norm(row.get("contrast_std"), 38, 70)
    score += 14.0 * norm(row.get("gradient_p90"), 18, 58)
    score += 14.0 * norm(row.get("laplacian_var"), 350, 2200)
    score += 8.0 * norm(row.get("entropy"), 4.8, 6.8)
    score += 6.0 * norm(row.get("saturation_mean"), 20, 80)

    brightness = safe_float(row.get("brightness_mean"), math.nan)
    if math.isfinite(brightness) and 65 <= brightness <= 190:
        score += 5.0

    md_area = safe_float(row.get("phase14_md_area_fraction"), math.nan)
    if math.isfinite(md_area):
        if md_area >= 0.30:
            score += 18.0
        elif md_area >= 0.20:
            score += 8.0
        else:
            score -= 16.0

    if row.get("object_aware_decision") == "keep":
        score += 24.0
    animal_area = safe_float(row.get("animal_area_fraction"), math.nan)
    if math.isfinite(animal_area) and animal_area >= 0.20:
        score += min(14.0, animal_area * 35.0)

    reject_reasons = str(row.get("phase19_prefilter_reject_reasons", ""))
    soft_penalties = {
        "too_dark_or_night_ultra": 8.0,
        "low_color_or_ir_night_ultra": 6.0,
        "low_sharpness_proxy_ultra": 6.0,
        "weak_edges_ultra": 5.0,
        "low_contrast_ultra": 5.0,
        "animal_area_lt_0_20": 12.0,
        "animal_crop_motion_or_soft_laplacian_lt_1400": 8.0,
    }
    object_reasons = str(row.get("object_aware_reject_reasons", ""))
    for reason, penalty in soft_penalties.items():
        if reason in reject_reasons or reason in object_reasons:
            score -= penalty

    if score >= 72:
        tier = "tier1_high_priority_review"
    elif score >= 56:
        tier = "tier2_plausible_review"
    elif score >= 42:
        tier = "tier3_rescue_review"
    else:
        tier = "tier4_low_priority"
    return round(score, 4), tier


def build_rows() -> list[dict[str, Any]]:
    prefilter_lookup = build_lookup(read_csv(PREFILTER))
    object_lookup = build_lookup(read_csv(OBJECT_AWARE))
    rows: list[dict[str, Any]] = []
    for index, manifest_row in enumerate(read_csv(MANIFEST), start=1):
        if manifest_row.get("download_status") not in {"downloaded", "already_present"}:
            continue
        pre = (
            prefilter_lookup.get(manifest_row.get("source_image_path", ""))
            or prefilter_lookup.get(manifest_row.get("source_candidate_id", ""))
            or {}
        )
        obj = object_lookup.get(pre.get("phase19_review_id", "")) or object_lookup.get(manifest_row.get("source_image_path", "")) or {}
        row = {field: "" for field in OUTPUT_FIELDS}
        row.update(manifest_row)
        row.update({key: pre.get(key, "") for key in OUTPUT_FIELDS if key in pre})
        row.update({key: obj.get(key, "") for key in OUTPUT_FIELDS if key in obj and obj.get(key, "") != ""})
        row["phase19_review_id"] = pre.get("phase19_review_id") or f"phase19_bobcat_wild_rescue_{index:05d}"
        row["phase19_cell"] = "bobcat_wild_camera_trap"
        row["bobcat_wild_review_sample_role"] = ""
        row["phase19_claim_boundary"] = "rescue review queue; not an automatic final selector"
        score, tier = rescue_score(row)
        row["bobcat_wild_rescue_score"] = score
        row["bobcat_wild_rescue_tier"] = tier
        rows.append(row)
    rows.sort(
        key=lambda row: (
            {"tier1_high_priority_review": 0, "tier2_plausible_review": 1, "tier3_rescue_review": 2, "tier4_low_priority": 3}.get(
                str(row.get("bobcat_wild_rescue_tier")), 9
            ),
            -safe_float(row.get("bobcat_wild_rescue_score"), -999),
            str(row.get("source_dataset", "")),
            str(row.get("phase19_review_id", "")),
        )
    )
    return rows


def stratified_sample(rows: list[dict[str, Any]], sample_size: int = 600) -> list[dict[str, Any]]:
    picked: list[dict[str, Any]] = []
    seen: set[str] = set()

    def take(role: str, pool: list[dict[str, Any]], count: int) -> None:
        if not pool or count <= 0:
            return
        if len(pool) <= count:
            indexes = list(range(len(pool)))
        else:
            indexes = sorted({round(i * (len(pool) - 1) / (count - 1)) for i in range(count)})
        for index in indexes:
            row = pool[index]
            row_id = str(row.get("phase19_review_id", ""))
            if row_id and row_id not in seen:
                out = dict(row)
                out["bobcat_wild_review_sample_role"] = role
                picked.append(out)
                seen.add(row_id)

    tier_counts = {
        "tier1_high_priority_review": 180,
        "tier2_plausible_review": 180,
        "tier3_rescue_review": 120,
        "tier4_low_priority": 60,
    }
    for tier, count in tier_counts.items():
        take(tier, [row for row in rows if row.get("bobcat_wild_rescue_tier") == tier], count)
    for source in sorted({str(row.get("source_dataset", "")) for row in rows}):
        take(f"source_check:{source}", [row for row in rows if row.get("source_dataset") == source], 20)
    if len(picked) < sample_size:
        take("fill_by_rank", rows, sample_size - len(picked))
    return picked[:sample_size]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = build_rows()
    sample = stratified_sample(rows)
    write_csv(OUT_DIR / "bobcat_wild_full_rescue_ranked_queue.csv", rows)
    write_csv(OUT_DIR / "bobcat_wild_full_rescue_review_sample600.csv", sample)
    audit = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "input_downloaded_rows": len(rows),
        "output_ranked_queue": str((OUT_DIR / "bobcat_wild_full_rescue_ranked_queue.csv").relative_to(PROJECT_ROOT)),
        "output_sample": str((OUT_DIR / "bobcat_wild_full_rescue_review_sample600.csv").relative_to(PROJECT_ROOT)),
        "tier_counts": dict(Counter(row["bobcat_wild_rescue_tier"] for row in rows)),
        "source_counts": dict(Counter(row["source_dataset"] for row in rows)),
        "sample_rows": len(sample),
        "sample_tier_counts": dict(Counter(row["bobcat_wild_rescue_tier"] for row in sample)),
        "principle": "Full reservoir plus human calibration; automatic scores rank review priority only.",
    }
    (OUT_DIR / "bobcat_wild_full_rescue_review_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote Bobcat wild rescue queue to {OUT_DIR.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
