#!/usr/bin/env python3
"""Build a Phase19 Bobcat clean review queue from direct iNaturalist rows."""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_CSV = (
    PROJECT_ROOT
    / "outputs/phase17/phase17m_inat_annotation_aware_strict_clarity_queue/phase17m_inat_annotation_aware_scored_all.csv"
)
OUT_DIR = PROJECT_ROOT / "outputs/phase19/phase19_bobcat_inat_daylight_clean_queue"
QUEUE_CSV = OUT_DIR / "phase19_bobcat_inat_daylight_nonblur_review_queue.csv"
SAMPLE_CSV = OUT_DIR / "phase19_bobcat_inat_daylight_nonblur_review_sample100.csv"
AUDIT_JSON = OUT_DIR / "phase19_bobcat_inat_daylight_nonblur_queue_audit.json"
DEPRECATION_JSON = OUT_DIR / "phase19_camera_trap_queue_deprecation_manifest.json"

DEPRECATED_PHASE19_DIRS = [
    "phase19_bobcat_wild_area_ge10_review",
    "phase19_bobcat_wild_area_ge10_review_app",
    "phase19_bobcat_wild_blur_gate",
    "phase19_bobcat_wild_blur_gate_review",
    "phase19_bobcat_wild_blur_only_review_v2",
    "phase19_bobcat_wild_body_gate",
    "phase19_bobcat_wild_body_gate_review",
    "phase19_bobcat_wild_clarity_clean_v1",
    "phase19_bobcat_wild_clarity_clean_v1_review",
    "phase19_bobcat_wild_manual_bbox",
    "phase19_bobcat_wild_manual_bbox_area_counts",
    "phase19_bobcat_wild_pixel_clarity_v2",
    "phase19_bobcat_wild_pixel_clarity_v2_review",
    "phase19_bobcat_wild_rescue_review",
    "phase19_bobcat_wild_rescue_review_queue",
    "phase19_object_aware_bobcat_wild_full_strict",
    "phase19_object_aware_bobcat_wild_full_strict_review",
    "phase19_object_aware_clear_candidates",
    "phase19_object_aware_validation_review",
    "phase19_strict_photo_prefilter",
    "phase19_strict_photo_review",
    "phase19_strict_top3000_validation",
    "phase19_strict_top3000_validation_review",
    "phase19_ultra_strict_top3000_validation_review",
]

OUT_FIELDS = [
    "phase19_review_id",
    "phase19_cell",
    "source_dataset",
    "source_platform",
    "source_candidate_id",
    "source_image_uri",
    "source_record_uri",
    "source_image_path",
    "species",
    "domain_label",
    "license",
    "attribution",
    "observed_on",
    "place_guess",
    "image_width",
    "image_height",
    "image_megapixels",
    "download_bytes",
    "contrast_std",
    "gradient_p90",
    "laplacian_var",
    "entropy",
    "dark_clip_fraction",
    "bright_clip_fraction",
    "colorfulness_proxy",
    "phase17m_seed_tier",
    "phase17m_seed_score",
    "phase17m_seed_reject_reasons",
    "phase19_daylight_nonblur_score",
    "phase19_daylight_nonblur_tier",
    "phase19_daylight_nonblur_reasons",
    "phase19_manual_decision",
    "phase19_manual_reject_reason",
    "phase19_manual_notes",
    "phase19_manual_audited_at_utc",
    "phase19_claim_boundary",
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


def clean_decision(row: dict[str, str]) -> tuple[bool, str, float, str]:
    reasons: list[str] = []
    seed_tier = row.get("phase17l_strict_proxy_tier", "")
    if seed_tier not in {"strict_pass", "near_strict"}:
        reasons.append("not_phase17m_strict_or_near")
    color = f(row, "colorfulness_proxy")
    dark = f(row, "dark_clip_fraction", 1.0)
    bright = f(row, "bright_clip_fraction", 1.0)
    contrast = f(row, "contrast_std")
    gradient = f(row, "gradient_p90")
    laplacian = f(row, "laplacian_var")
    entropy = f(row, "entropy")
    megapixels = f(row, "image_megapixels")
    bytes_count = f(row, "download_bytes")
    width = f(row, "image_width")
    height = f(row, "image_height")
    min_dim = min(width, height) if width and height else 0.0

    if color < 20:
        reasons.append("low_color_or_possible_ir_night")
    if dark > 0.18:
        reasons.append("too_dark_or_night_like")
    if bright > 0.18:
        reasons.append("too_much_highlight_clipping")
    if contrast < 45:
        reasons.append("low_contrast")
    if gradient < 20:
        reasons.append("weak_edges_or_motion_blur")
    if laplacian < 160:
        reasons.append("low_laplacian_or_soft")
    if entropy < 5:
        reasons.append("low_entropy")

    score = 0.0
    score += min(20.0, color / 2.5)
    score += min(18.0, contrast / 3.0)
    score += min(18.0, gradient / 2.0)
    score += min(24.0, laplacian / 18.0)
    score += min(8.0, entropy)
    score += max(0.0, 8.0 - dark * 24.0)
    score += max(0.0, 4.0 - bright * 12.0)
    score += 8.0 if seed_tier == "strict_pass" else 3.0
    score += 6.0 if min_dim >= 900 and megapixels >= 1.2 and bytes_count >= 120_000 else 0.0

    if reasons:
        return False, "reject_proxy", round(score, 4), ";".join(reasons)
    if min_dim >= 900 and megapixels >= 1.2 and bytes_count >= 120_000 and row.get("phase17l_proxy_reject_reasons", "") in {"", None}:
        return True, "tier1_high_resolution_daylight_nonblur", round(score, 4), ""
    return True, "tier2_daylight_nonblur_review", round(score, 4), "resolution_size_needs_human_check"


def output_row(row: dict[str, str], tier: str, score: float, reasons: str) -> dict[str, Any]:
    return {
        "phase19_review_id": f"phase19_inat_bobcat_{row.get('source_record_id', '')}_{row.get('photo_id', '')}",
        "phase19_cell": "bobcat_wild_inat_alive_organism_daylight",
        "source_dataset": "iNaturalist Research Grade direct annotation-aware",
        "source_platform": "iNaturalist",
        "source_candidate_id": row.get("candidate_id", ""),
        "source_image_uri": row.get("image_uri", ""),
        "source_record_uri": row.get("source_uri", ""),
        "source_image_path": "",
        "species": "Lynx rufus",
        "domain_label": "wild_or_free_roaming_bobcat",
        "license": row.get("license", ""),
        "attribution": row.get("attribution", ""),
        "observed_on": row.get("observed_on", ""),
        "place_guess": row.get("place_guess", ""),
        "image_width": row.get("image_width", ""),
        "image_height": row.get("image_height", ""),
        "image_megapixels": row.get("image_megapixels", ""),
        "download_bytes": row.get("download_bytes", ""),
        "contrast_std": row.get("contrast_std", ""),
        "gradient_p90": row.get("gradient_p90", ""),
        "laplacian_var": row.get("laplacian_var", ""),
        "entropy": row.get("entropy", ""),
        "dark_clip_fraction": row.get("dark_clip_fraction", ""),
        "bright_clip_fraction": row.get("bright_clip_fraction", ""),
        "colorfulness_proxy": row.get("colorfulness_proxy", ""),
        "phase17m_seed_tier": row.get("phase17l_strict_proxy_tier", ""),
        "phase17m_seed_score": row.get("phase17l_strict_clarity_proxy_score", ""),
        "phase17m_seed_reject_reasons": row.get("phase17l_proxy_reject_reasons", ""),
        "phase19_daylight_nonblur_score": f"{score:.4f}",
        "phase19_daylight_nonblur_tier": tier,
        "phase19_daylight_nonblur_reasons": reasons,
        "phase19_manual_decision": "",
        "phase19_manual_reject_reason": "",
        "phase19_manual_notes": "",
        "phase19_manual_audited_at_utc": "",
        "phase19_claim_boundary": (
            "Direct iNaturalist annotation-aware daylight/nonblur review queue; "
            "manual CLEAR is still required before final 3000 inclusion."
        ),
    }


def sort_key(row: dict[str, Any]) -> tuple[int, float, float, str]:
    tier_rank = {
        "tier1_high_resolution_daylight_nonblur": 0,
        "tier2_daylight_nonblur_review": 1,
    }.get(str(row.get("phase19_daylight_nonblur_tier", "")), 9)
    score = f(row, "phase19_daylight_nonblur_score")
    seed_score = f(row, "phase17m_seed_score")
    return (tier_rank, -score, -seed_score, str(row.get("phase19_review_id", "")))


def build() -> dict[str, Any]:
    source_rows = read_csv(SOURCE_CSV)
    selected: list[dict[str, Any]] = []
    rejected: list[str] = []
    seen_urls: set[str] = set()
    for row in source_rows:
        image_uri = row.get("image_uri", "").split("?")[0]
        if not image_uri or image_uri in seen_urls:
            continue
        seen_urls.add(image_uri)
        keep, tier, score, reasons = clean_decision(row)
        if keep:
            selected.append(output_row(row, tier, score, reasons))
        else:
            rejected.append(reasons)
    selected.sort(key=sort_key)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(QUEUE_CSV, selected, OUT_FIELDS)
    write_csv(SAMPLE_CSV, selected[:100], OUT_FIELDS)
    audit = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_csv": str(SOURCE_CSV.relative_to(PROJECT_ROOT)),
        "input_rows": len(source_rows),
        "deduped_candidate_urls": len(seen_urls),
        "selected_rows": len(selected),
        "sample100_rows": min(100, len(selected)),
        "selected_tier_counts": dict(Counter(row["phase19_daylight_nonblur_tier"] for row in selected)),
        "selected_source_dataset_counts": dict(Counter(row["source_dataset"] for row in selected)),
        "rejected_rows": len(rejected),
        "top_reject_reason_counts": dict(Counter(rejected).most_common(30)),
        "selection_rule": {
            "source": "direct iNaturalist rows from Phase17M annotation-aware seed",
            "semantic_gate": "research-grade direct iNaturalist; organism/not-scat/not-track/not-dead/not-captive inherited from Phase17M",
            "night_gate": "colorfulness_proxy >= 20 and dark_clip_fraction <= 0.18",
            "nonblur_gate": "contrast_std >= 45, gradient_p90 >= 20, laplacian_var >= 160, entropy >= 5",
            "tier1_extra": "min dimension >= 900, megapixels >= 1.2, bytes >= 120000, no prior proxy reject reasons",
        },
        "outputs": {
            "queue_csv": str(QUEUE_CSV.relative_to(PROJECT_ROOT)),
            "sample_csv": str(SAMPLE_CSV.relative_to(PROJECT_ROOT)),
            "audit_json": str(AUDIT_JSON.relative_to(PROJECT_ROOT)),
            "deprecation_manifest": str(DEPRECATION_JSON.relative_to(PROJECT_ROOT)),
        },
        "claim_boundary": "This is a replacement source review queue, not final algorithm-ready inclusion until human CLEAR.",
    }
    AUDIT_JSON.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    deprecation = {
        "built_at_utc": audit["built_at_utc"],
        "status": "deprecated_for_phase19_bobcat_clean_photo_selection",
        "reason": (
            "Camera-trap-derived Bobcat queues repeatedly failed human spot review due to night/IR imagery, "
            "motion blur, small subjects, and unreliable detector area coverage. They remain diagnostic only."
        ),
        "replacement": str(QUEUE_CSV.relative_to(PROJECT_ROOT)),
        "deprecated_output_dirs": DEPRECATED_PHASE19_DIRS,
        "not_deleted": True,
    }
    DEPRECATION_JSON.write_text(json.dumps(deprecation, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return audit


def main() -> int:
    audit = build()
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
