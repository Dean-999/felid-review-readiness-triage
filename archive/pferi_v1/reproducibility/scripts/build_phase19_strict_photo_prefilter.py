#!/usr/bin/env python3
"""Build strict Phase19 photo review queues from downloaded candidate pools.

This script is intentionally conservative. It ranks and rejects obvious
technical failures, but it does not certify final 3000 membership. Final
algorithm entry still requires a human CLEAR label under the Phase19 visual
evidence standard.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageStat


PROJECT_ROOT = Path(__file__).resolve().parents[1]
POOL_ROOT = PROJECT_ROOT / "data/phase19_candidate_pools"
OUT_DIR = PROJECT_ROOT / "outputs/phase19/phase19_strict_photo_prefilter"

PHASE14_BOBCAT_HIGH = (
    PROJECT_ROOT
    / "outputs/phase14/phase14_final_2x2_working_labels/"
    / "phase14_bobcat_high_confidence_3000_working_final_labels.csv"
)

POOLS = [
    "bobcat_wild_camera_trap",
    "bobcat_urban_heterogeneous",
    "lynx_external_heterogeneous_supplement",
]

BAD_TEXT_RE = re.compile(
    r"track|tracks|footprint|scat|feces|faeces|poop|dropping|dung|skull|skeleton|taxiderm|pelt|fur|dead|roadkill|sign|label|poster|map",
    re.IGNORECASE,
)

FIELDNAMES = [
    "phase19_review_id",
    "phase19_cell",
    "source_dataset",
    "source_platform",
    "source_candidate_id",
    "source_image_uri",
    "source_image_path",
    "species",
    "domain_label",
    "license",
    "attribution",
    "selection_basis",
    "download_status",
    "bytes",
    "image_width",
    "image_height",
    "image_megapixels",
    "contrast_std",
    "gradient_mean",
    "gradient_p90",
    "laplacian_var",
    "entropy",
    "dark_clip_fraction",
    "bright_clip_fraction",
    "colorfulness_proxy",
    "brightness_mean",
    "saturation_mean",
    "grayscale_proxy",
    "phase14_md_area_fraction",
    "phase14_md_width_fraction",
    "phase14_md_height_fraction",
    "phase14_md_edge_touch",
    "subject_area_rule",
    "technical_quality_rule",
    "phase19_strict_photo_score",
    "phase19_prefilter_tier",
    "phase19_prefilter_decision",
    "phase19_prefilter_reject_reasons",
    "phase19_manual_review_priority",
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


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] = FIELDNAMES) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def safe_float(value: Any) -> float | None:
    try:
        if value in {"", None}:
            return None
        out = float(value)
        return out if math.isfinite(out) else None
    except (TypeError, ValueError):
        return None


def load_phase14_md_lookup() -> dict[str, dict[str, str]]:
    lookup: dict[str, dict[str, str]] = {}
    for row in read_csv(PHASE14_BOBCAT_HIGH):
        for key in [row.get("image_id", ""), row.get("file_name", ""), row.get("download_url", "")]:
            if key:
                lookup[key] = row
    return lookup


def md_match_for_row(row: dict[str, str], lookup: dict[str, dict[str, str]]) -> dict[str, str] | None:
    source_id = row.get("source_candidate_id", "")
    image_uri = row.get("source_image_uri", "")
    for key in [source_id, image_uri]:
        if key in lookup:
            return lookup[key]
    if source_id:
        for suffix_key in [source_id, f"https://storage.googleapis.com/public-datasets-lila/felidae-conservation-fund/{source_id}"]:
            if suffix_key in lookup:
                return lookup[suffix_key]
    return None


def laplacian_variance(gray: np.ndarray) -> float:
    if gray.shape[0] < 3 or gray.shape[1] < 3:
        return 0.0
    center = gray[1:-1, 1:-1] * -4.0
    lap = center + gray[:-2, 1:-1] + gray[2:, 1:-1] + gray[1:-1, :-2] + gray[1:-1, 2:]
    return float(np.var(lap))


def image_metrics(path: Path) -> dict[str, Any]:
    with Image.open(path) as image:
        image = image.convert("RGB")
        width, height = image.size
        resized = image.copy()
        resized.thumbnail((768, 768))
        gray_image = resized.convert("L")
        gray = np.asarray(gray_image, dtype=np.float32)
        contrast_std = float(np.std(gray))
        dx = np.diff(gray, axis=1)
        dy = np.diff(gray, axis=0)
        gradient = np.sqrt(dx[:-1, :] ** 2 + dy[:, :-1] ** 2) if gray.shape[0] > 1 and gray.shape[1] > 1 else np.asarray([0.0])
        hist = gray_image.histogram()
        total = sum(hist) or 1
        entropy = -sum((count / total) * math.log2(count / total) for count in hist if count)
        r, g, b = [np.asarray(channel, dtype=np.float32) for channel in resized.split()]
        rg = np.abs(r - g)
        yb = np.abs(0.5 * (r + g) - b)
        stat = ImageStat.Stat(resized)
        hsv = resized.convert("HSV")
        saturation = np.asarray(hsv.getchannel("S"), dtype=np.float32)
        channel_spread = np.maximum.reduce([r, g, b]) - np.minimum.reduce([r, g, b])
        return {
            "image_width": width,
            "image_height": height,
            "image_megapixels": round((width * height) / 1_000_000, 4),
            "contrast_std": round(contrast_std, 4),
            "gradient_mean": round(float(np.mean(gradient)), 4),
            "gradient_p90": round(float(np.percentile(gradient, 90)), 4),
            "laplacian_var": round(laplacian_variance(gray), 4),
            "entropy": round(float(entropy), 4),
            "dark_clip_fraction": round(sum(hist[:8]) / total, 6),
            "bright_clip_fraction": round(sum(hist[248:]) / total, 6),
            "colorfulness_proxy": round(float(np.std(rg) + np.std(yb) + 0.3 * np.mean(rg + yb)), 4),
            "brightness_mean": round(float(stat.mean[0]), 4),
            "saturation_mean": round(float(np.mean(saturation)), 4),
            "grayscale_proxy": round(float(np.mean(channel_spread < 8.0)), 6),
        }


def subject_area_rule(row: dict[str, Any]) -> tuple[str, list[str], float]:
    area = safe_float(row.get("phase14_md_area_fraction"))
    edge_touch = str(row.get("phase14_md_edge_touch", "")).lower() == "true"
    if area is None:
        return "manual_area_required", ["no_detector_area_available"], 0.0
    if area < 0.20:
        return "reject_area_lt_0_20", ["subject_area_lt_0_20"], -50.0
    if edge_touch:
        return "cautious_edge_touch", ["detector_edge_touch"], -18.0
    if area < 0.30:
        return "cautious_area_0_20_to_0_30", ["subject_area_0_20_to_0_30_requires_true_clarity"], -8.0
    return "pass_area_ge_0_30", [], 14.0 + min(10.0, (area - 0.30) * 50.0)


def technical_quality_rule(metrics: dict[str, Any], byte_count: int) -> tuple[str, list[str], float]:
    reject: list[str] = []
    min_dim = min(float(metrics["image_width"]), float(metrics["image_height"]))
    megapixels = float(metrics["image_megapixels"])
    contrast = float(metrics["contrast_std"])
    gradient_p90 = float(metrics["gradient_p90"])
    lap_var = float(metrics["laplacian_var"])
    entropy = float(metrics["entropy"])
    clipping = float(metrics["dark_clip_fraction"]) + float(metrics["bright_clip_fraction"])

    brightness = float(metrics.get("brightness_mean", 0.0))
    saturation = float(metrics.get("saturation_mean", 0.0))
    grayscale_proxy = float(metrics.get("grayscale_proxy", 1.0))

    if min_dim < 850:
        reject.append("min_dimension_lt_850_ultra")
    if min_dim < 700:
        reject.append("min_dimension_lt_700")
    if megapixels < 0.9:
        reject.append("megapixels_lt_0_90_ultra")
    if megapixels < 0.65:
        reject.append("megapixels_lt_0_65")
    if byte_count < 140_000:
        reject.append("small_file_lt_140kb_ultra")
    if byte_count < 75_000:
        reject.append("small_file_lt_75kb")
    if contrast < 45:
        reject.append("low_contrast_ultra")
    if contrast < 34:
        reject.append("low_contrast")
    if gradient_p90 < 30:
        reject.append("weak_edges_ultra")
    if gradient_p90 < 12:
        reject.append("weak_edges")
    if lap_var < 950:
        reject.append("low_sharpness_proxy_ultra")
    if lap_var < 45:
        reject.append("low_sharpness_proxy")
    if entropy < 5.4:
        reject.append("low_entropy_ultra")
    if entropy < 4.5:
        reject.append("low_entropy")
    if clipping > 0.28:
        reject.append("heavy_shadow_highlight_clipping_ultra")
    if clipping > 0.45:
        reject.append("heavy_shadow_highlight_clipping")
    if brightness < 55:
        reject.append("too_dark_or_night_ultra")
    if brightness > 210:
        reject.append("too_bright_washed_ultra")
    if saturation < 18 or grayscale_proxy > 0.82:
        reject.append("low_color_or_ir_night_ultra")

    score = 0.0
    score += min(16.0, megapixels * 3.0)
    score += min(20.0, contrast / 3.0)
    score += min(18.0, gradient_p90 / 2.0)
    score += min(22.0, lap_var / 16.0)
    score += min(8.0, entropy)
    score += max(0.0, 8.0 - clipping * 16.0)
    if byte_count >= 250_000:
        score += 4.0
    elif byte_count >= 150_000:
        score += 2.0

    if not reject and score >= 74:
        rule = "technical_strict_pass"
    elif len(reject) <= 2 and score >= 64:
        rule = "technical_cautious_pass"
    else:
        rule = "technical_reject_or_low_priority"
    return rule, reject, round(score, 4)


def score_row(index: int, row: dict[str, str], md_lookup: dict[str, dict[str, str]]) -> dict[str, Any]:
    out: dict[str, Any] = {field: "" for field in FIELDNAMES}
    out.update(row)
    out["phase19_review_id"] = f"phase19_{row.get('phase19_cell', 'pool')}_{index:05d}"
    out["phase19_claim_boundary"] = (
        "strict automatic prefilter and human review queue only; final algorithm entry requires manual CLEAR"
    )
    image_path = PROJECT_ROOT / row.get("source_image_path", "")
    if not image_path.exists():
        out["phase19_prefilter_decision"] = "auto_reject"
        out["phase19_prefilter_tier"] = "missing_file"
        out["phase19_prefilter_reject_reasons"] = "missing_file"
        out["phase19_manual_review_priority"] = "exclude"
        return out

    md_row = md_match_for_row(row, md_lookup)
    if md_row:
        out["phase14_md_area_fraction"] = md_row.get("md_area_fraction", "")
        out["phase14_md_width_fraction"] = md_row.get("md_width_fraction", "")
        out["phase14_md_height_fraction"] = md_row.get("md_height_fraction", "")
        out["phase14_md_edge_touch"] = md_row.get("md_edge_touch", "")

    text = " ".join(str(row.get(key, "")) for key in ["source_candidate_id", "source_image_uri", "selection_basis", "attribution"])
    reject_reasons: list[str] = []
    if BAD_TEXT_RE.search(text):
        reject_reasons.append("bad_text_track_scat_dead_sign")

    try:
        metrics = image_metrics(image_path)
        out.update(metrics)
        byte_count = int(row.get("bytes") or image_path.stat().st_size)
        out["bytes"] = byte_count
        tech_rule, tech_reject, tech_score = technical_quality_rule(metrics, byte_count)
        area_rule, area_reject, area_score = subject_area_rule(out)
        reject_reasons.extend(tech_reject)
        reject_reasons.extend(area_reject)
        out["technical_quality_rule"] = tech_rule
        out["subject_area_rule"] = area_rule
        score = tech_score + area_score
        if row.get("source_dataset") == "Felidae Conservation Fund 2020-2025":
            score += 4.0
        if row.get("source_platform") == "iNaturalist" and row.get("license", "").lower().startswith("cc-"):
            score += 2.0
        out["phase19_strict_photo_score"] = round(score, 4)

        hard_reject = {
            "missing_file",
            "bad_text_track_scat_dead_sign",
            "subject_area_lt_0_20",
            "min_dimension_lt_700",
            "megapixels_lt_0_65",
            "small_file_lt_75kb",
        }
        if any(reason in hard_reject for reason in reject_reasons):
            out["phase19_prefilter_decision"] = "auto_reject"
            out["phase19_prefilter_tier"] = "strict_reject"
            out["phase19_manual_review_priority"] = "exclude"
        elif tech_rule == "technical_strict_pass" and area_rule == "pass_area_ge_0_30":
            out["phase19_prefilter_decision"] = "review"
            out["phase19_prefilter_tier"] = "strict_high_confidence_candidate"
            out["phase19_manual_review_priority"] = "high"
        elif tech_rule in {"technical_strict_pass", "technical_cautious_pass"} and area_rule in {
            "cautious_area_0_20_to_0_30",
            "manual_area_required",
        }:
            out["phase19_prefilter_decision"] = "review"
            out["phase19_prefilter_tier"] = "cautious_manual_area_candidate"
            out["phase19_manual_review_priority"] = "cautious"
        elif tech_rule == "technical_strict_pass":
            out["phase19_prefilter_decision"] = "review"
            out["phase19_prefilter_tier"] = "technical_high_manual_area_candidate"
            out["phase19_manual_review_priority"] = "medium"
        else:
            out["phase19_prefilter_decision"] = "low_priority_review"
            out["phase19_prefilter_tier"] = "low_priority_not_final_reject"
            out["phase19_manual_review_priority"] = "low"
    except Exception as error:
        out["phase19_prefilter_decision"] = "auto_reject"
        out["phase19_prefilter_tier"] = "decode_failed"
        out["phase19_prefilter_reject_reasons"] = f"decode_failed:{type(error).__name__}:{str(error)[:100]}"
        out["phase19_manual_review_priority"] = "exclude"
        return out

    out["phase19_prefilter_reject_reasons"] = ";".join(dict.fromkeys(reject_reasons))
    return out


def sort_key(row: dict[str, Any]) -> tuple[int, float, str]:
    priority_rank = {"high": 0, "cautious": 1, "medium": 2, "low": 3, "exclude": 9}
    return (
        priority_rank.get(str(row.get("phase19_manual_review_priority", "low")), 5),
        -float(row.get("phase19_strict_photo_score") or -999),
        str(row.get("phase19_review_id", "")),
    )


def build(args: argparse.Namespace) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    md_lookup = load_phase14_md_lookup()
    all_rows: list[dict[str, Any]] = []
    audit: dict[str, Any] = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "standard": {
            "accept_core": "animal itself sharp; no severe motion blur/compression; subject large enough; body/marking evidence complete; not scat/track/dead/sign; not severe partial/occlusion",
            "area_rule": "<0.20 reject when detector area is available; 0.20-0.30 cautious only if truly clear and complete; no detector area means manual area review required",
            "claim_boundary": "automatic prefilter ranks/rejects obvious failures only; final 3000 requires human CLEAR",
        },
        "pools": {},
    }

    for pool in args.pools:
        manifest = POOL_ROOT / pool / f"{pool}_download_manifest.csv"
        rows = [row for row in read_csv(manifest) if row.get("download_status") in {"downloaded", "already_present"}]
        scored: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = [executor.submit(score_row, index, row, md_lookup) for index, row in enumerate(rows, start=1)]
            for done, future in enumerate(as_completed(futures), start=1):
                scored.append(future.result())
                if done % 1000 == 0:
                    print(f"{pool}: scored {done}/{len(futures)}")
        scored.sort(key=sort_key)
        out_csv = OUT_DIR / f"{pool}_strict_photo_prefilter.csv"
        write_csv(out_csv, scored)
        all_rows.extend(scored)
        audit["pools"][pool] = {
            "input_downloaded_rows": len(rows),
            "output_rows": len(scored),
            "decision_counts": dict(Counter(str(row.get("phase19_prefilter_decision", "")) for row in scored)),
            "priority_counts": dict(Counter(str(row.get("phase19_manual_review_priority", "")) for row in scored)),
            "tier_counts": dict(Counter(str(row.get("phase19_prefilter_tier", "")) for row in scored)),
            "top_queue_csv": str(out_csv.relative_to(PROJECT_ROOT)),
        }

    reviewable = [row for row in all_rows if row.get("phase19_manual_review_priority") in {"high", "cautious", "medium"}]
    reviewable.sort(key=sort_key)
    write_csv(OUT_DIR / "phase19_strict_photo_review_queue.csv", reviewable)

    per_pool_targets: list[dict[str, Any]] = []
    for pool in args.pools:
        pool_rows = [row for row in reviewable if row.get("phase19_cell") == pool]
        selected = pool_rows[: args.review_per_pool]
        write_csv(OUT_DIR / f"{pool}_strict_photo_review_queue_top{args.review_per_pool}.csv", selected)
        per_pool_targets.append(
            {
                "pool": pool,
                "review_queue_rows": len(pool_rows),
                "top_export_rows": len(selected),
                "priority_counts": dict(Counter(str(row.get("phase19_manual_review_priority", "")) for row in pool_rows)),
            }
        )

    audit["combined_review_queue_rows"] = len(reviewable)
    audit["per_pool_review_exports"] = per_pool_targets
    audit["outputs"] = {
        "combined_review_queue_csv": str((OUT_DIR / "phase19_strict_photo_review_queue.csv").relative_to(PROJECT_ROOT)),
        "audit_json": str((OUT_DIR / "phase19_strict_photo_prefilter_audit.json").relative_to(PROJECT_ROOT)),
    }
    (OUT_DIR / "phase19_strict_photo_prefilter_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote Phase19 strict photo prefilter outputs to {OUT_DIR.relative_to(PROJECT_ROOT)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pools", nargs="+", choices=POOLS, default=POOLS)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--review-per-pool", type=int, default=6000)
    return parser.parse_args()


if __name__ == "__main__":
    build(parse_args())
