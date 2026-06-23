#!/usr/bin/env python3
"""Inventory current Phase 14 bobcat images and high-confidence candidates."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "outputs/phase14/phase14_bobcat_high_confidence_inventory"

IMAGE_DIRS = [
    PROJECT_ROOT / "data/external/felidae_conservation_fund/images/bobcat_3000",
    PROJECT_ROOT / "data/external/felidae_conservation_fund/images/bobcat_phase14_2x2_expansion_6000",
]

CANDIDATE_POOL = PROJECT_ROOT / "outputs/phase14/phase14_strict_2x2_evidence_sets/phase14_strict_2x2_combined_candidate_pool.csv"
STRICT_SELECTED_HIGH = PROJECT_ROOT / "outputs/phase14/phase14_strict_2x2_evidence_sets/phase14_strict_2x2_bobcat_high_confidence_3000.csv"
DETECTOR_FIRST_SCORES = PROJECT_ROOT / "outputs/phase14/phase14_detector_first_admission/phase14_detector_first_candidate_scores.csv"
MEGADETECTOR_300X2 = PROJECT_ROOT / "outputs/phase14/phase14_megadetector_evidence_gate_300x2/phase14_megadetector_high_gate_candidates.csv"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def norm_path(path_text: object) -> str:
    path = Path(str(path_text))
    if path.is_absolute():
        try:
            return str(path.relative_to(PROJECT_ROOT))
        except ValueError:
            return str(path)
    return str(path)


def image_inventory() -> pd.DataFrame:
    rows = []
    for image_dir in IMAGE_DIRS:
        if not image_dir.exists():
            continue
        for path in image_dir.rglob("*"):
            if path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
                continue
            rows.append(
                {
                    "image_path": rel(path),
                    "image_source_dir": rel(image_dir),
                    "file_size_bytes": path.stat().st_size,
                }
            )
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    return frame.drop_duplicates("image_path").sort_values("image_path").reset_index(drop=True)


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, low_memory=False)


def bobcat_candidate_pool() -> pd.DataFrame:
    frame = read_csv(CANDIDATE_POOL)
    if frame.empty:
        return frame
    if "environment_context" in frame.columns:
        frame = frame[frame["environment_context"].eq("urban_periurban")].copy()
    frame["image_path"] = frame["evidence_image_path"].map(norm_path)
    return frame


def detector_first_bobcat() -> pd.DataFrame:
    frame = read_csv(DETECTOR_FIRST_SCORES)
    if frame.empty:
        return frame
    frame = frame[frame["environment_context"].eq("urban_periurban")].copy()
    frame["image_path"] = frame["evidence_image_path"].map(norm_path)
    return frame


def megadetector_bobcat() -> pd.DataFrame:
    frame = read_csv(MEGADETECTOR_300X2)
    if frame.empty:
        return frame
    frame = frame[frame["environment_context"].eq("urban_periurban")].copy()
    frame["image_path"] = frame["evidence_image_path"].map(norm_path)
    return frame


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    images = image_inventory()
    pool = bobcat_candidate_pool()
    detector = detector_first_bobcat()
    md = megadetector_bobcat()
    strict_selected = read_csv(STRICT_SELECTED_HIGH)
    if not strict_selected.empty:
        strict_selected["image_path"] = strict_selected["evidence_image_path"].map(norm_path)

    strict_high = pool[pool["strict_evidence_tier"].eq("high_confidence")].copy() if not pool.empty else pd.DataFrame()
    strict_stress = pool[pool["strict_evidence_tier"].eq("low_evidence_stress")].copy() if not pool.empty else pd.DataFrame()
    strict_middle = pool[pool["strict_evidence_tier"].eq("middle_reviewable")].copy() if not pool.empty else pd.DataFrame()
    detector_auto_high = (
        detector[detector["ai_route"].eq("ai_auto_high_confidence")].copy() if not detector.empty else pd.DataFrame()
    )
    detector_auto_stress = (
        detector[detector["ai_route"].eq("ai_auto_low_evidence_stress")].copy() if not detector.empty else pd.DataFrame()
    )
    md_auto_high = md[md["md_high_evidence_gate"].fillna(False).astype(bool)].copy() if not md.empty else pd.DataFrame()
    if not images.empty and not pool.empty:
        pool_paths = set(pool["image_path"].astype(str))
        extra_local_images = images[~images["image_path"].isin(pool_paths)].copy()
    else:
        extra_local_images = pd.DataFrame()

    strict_high.to_csv(OUT_DIR / "phase14_bobcat_all_strict_high_candidates.csv", index=False)
    strict_selected.to_csv(OUT_DIR / "phase14_bobcat_selected_strict_high_3000.csv", index=False)
    detector_auto_high.to_csv(OUT_DIR / "phase14_bobcat_detector_first_auto_high.csv", index=False)
    md_auto_high.to_csv(OUT_DIR / "phase14_bobcat_megadetector_sampled_auto_high.csv", index=False)
    images.to_csv(OUT_DIR / "phase14_bobcat_local_image_inventory.csv", index=False)
    extra_local_images.to_csv(OUT_DIR / "phase14_bobcat_local_images_not_in_candidate_pool.csv", index=False)

    source_dir_counts = {}
    if not images.empty:
        source_dir_counts = {str(k): int(v) for k, v in images["image_source_dir"].value_counts().sort_index().items()}
    pool_source_counts = {}
    if not pool.empty and "pool_source" in pool.columns:
        pool_source_counts = {str(k): int(v) for k, v in pool["pool_source"].value_counts().sort_index().items()}
    strict_tier_counts = {}
    if not pool.empty and "strict_evidence_tier" in pool.columns:
        strict_tier_counts = {str(k): int(v) for k, v in pool["strict_evidence_tier"].value_counts().sort_index().items()}

    md_pass_rate = None
    if len(md) > 0:
        md_pass_rate = len(md_auto_high) / len(md)
    strict_high_count = len(strict_high)
    estimated_md_high_from_strict_pool = None
    if md_pass_rate is not None:
        estimated_md_high_from_strict_pool = round(strict_high_count * md_pass_rate)

    summary = {
        "local_bobcat_image_files": int(len(images)),
        "local_bobcat_image_files_by_source_dir": source_dir_counts,
        "candidate_pool_bobcat_rows": int(len(pool)),
        "candidate_pool_bobcat_unique_paths": int(pool["image_path"].nunique()) if not pool.empty else 0,
        "local_images_not_in_candidate_pool": int(len(extra_local_images)),
        "candidate_pool_source_counts": pool_source_counts,
        "strict_evidence_tier_counts": strict_tier_counts,
        "all_strict_high_candidates": int(len(strict_high)),
        "all_strict_high_unique_paths": int(strict_high["image_path"].nunique()) if not strict_high.empty else 0,
        "selected_strict_high_3000_rows": int(len(strict_selected)),
        "selected_strict_high_3000_unique_paths": int(strict_selected["image_path"].nunique()) if not strict_selected.empty else 0,
        "detector_first_auto_high_rows": int(len(detector_auto_high)),
        "detector_first_auto_stress_rows": int(len(detector_auto_stress)),
        "megadetector_sampled_bobcat_rows": int(len(md)),
        "megadetector_sampled_auto_high_rows": int(len(md_auto_high)),
        "megadetector_sampled_auto_high_rate": md_pass_rate,
        "estimated_megadetector_auto_high_if_sample_rate_holds_for_all_strict_high": estimated_md_high_from_strict_pool,
        "important_boundary": (
            "strict_high is an AI/rule-derived candidate pool, not final clean truth; "
            "MegaDetector sampled_auto_high is detector-gated high-evidence seed from the processed subset only."
        ),
        "outputs": {
            "local_image_inventory": rel(OUT_DIR / "phase14_bobcat_local_image_inventory.csv"),
            "local_images_not_in_candidate_pool": rel(OUT_DIR / "phase14_bobcat_local_images_not_in_candidate_pool.csv"),
            "all_strict_high_candidates": rel(OUT_DIR / "phase14_bobcat_all_strict_high_candidates.csv"),
            "selected_strict_high_3000": rel(OUT_DIR / "phase14_bobcat_selected_strict_high_3000.csv"),
            "detector_first_auto_high": rel(OUT_DIR / "phase14_bobcat_detector_first_auto_high.csv"),
            "megadetector_sampled_auto_high": rel(OUT_DIR / "phase14_bobcat_megadetector_sampled_auto_high.csv"),
        },
    }
    (OUT_DIR / "phase14_bobcat_high_confidence_inventory_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "PASS phase14 bobcat high-confidence inventory "
        f"local_images={summary['local_bobcat_image_files']} "
        f"candidate_rows={summary['candidate_pool_bobcat_rows']} "
        f"strict_high={summary['all_strict_high_candidates']} "
        f"md_sampled_auto_high={summary['megadetector_sampled_auto_high_rows']} "
        f"out={rel(OUT_DIR)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
