#!/usr/bin/env python3
"""Prepare unused CzechLynx high-confidence top-up candidates for MegaDetector screening."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POOL = PROJECT_ROOT / "outputs/phase14/phase14_strict_2x2_evidence_sets/phase14_strict_2x2_combined_candidate_pool.csv"
DEFAULT_GATED = PROJECT_ROOT / "outputs/phase14/phase14_colab_megadetector_final_selection/phase14_colab_megadetector_all_gated_candidates.csv"
DEFAULT_LOW = PROJECT_ROOT / "outputs/phase14/phase14_strict_2x2_evidence_sets/phase14_strict_2x2_czechlynx_low_evidence_stress_3000.csv"
DEFAULT_OUT_DIR = PROJECT_ROOT / "outputs/phase14/phase14_czechlynx_high_topup"


def resolve(path_text: object) -> Path:
    path = Path(str(path_text))
    return path if path.is_absolute() else PROJECT_ROOT / path


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def path_column(frame: pd.DataFrame) -> str:
    for col in ["candidate_source_path", "evidence_image_path", "local_image_path", "review_image_path_local"]:
        if col in frame.columns:
            return col
    raise ValueError("no image path column found")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pool", default=str(DEFAULT_POOL))
    parser.add_argument("--gated", default=str(DEFAULT_GATED))
    parser.add_argument("--low", default=str(DEFAULT_LOW))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--candidate-count", type=int, default=2500)
    args = parser.parse_args()

    out_dir = resolve(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    pool = pd.read_csv(resolve(args.pool), low_memory=False)
    wild = pool[pool["environment_context"].eq("wild")].copy()
    wild["candidate_source_path"] = wild["evidence_image_path"].fillna(wild.get("local_image_path", "")).astype(str)

    used_paths: set[str] = set()
    for source_path in [resolve(args.gated), resolve(args.low)]:
        source = pd.read_csv(source_path, low_memory=False)
        col = path_column(source)
        used_paths.update(source[col].dropna().astype(str).tolist())

    candidates = wild[
        wild["strict_evidence_tier"].eq("middle_reviewable")
        & ~wild["candidate_source_path"].isin(used_paths)
    ].copy()
    candidates["candidate_source_exists"] = candidates["candidate_source_path"].map(lambda p: resolve(p).exists())
    candidates = candidates[candidates["candidate_source_exists"]].copy()

    for col in ["auto_evidence_score", "auto_quality_score", "blur_laplacian_var", "contrast_std"]:
        candidates[col] = pd.to_numeric(candidates[col], errors="coerce").fillna(0)

    candidates["phase14_czechlynx_topup_score"] = (
        candidates["auto_evidence_score"] * 3.0
        + candidates["auto_quality_score"] * 1.5
        + candidates["blur_laplacian_var"].clip(upper=2000) / 2000
        + candidates["contrast_std"].clip(upper=120) / 120
    )
    candidates = candidates.sort_values(
        [
            "phase14_czechlynx_topup_score",
            "auto_evidence_score",
            "auto_quality_score",
            "blur_laplacian_var",
        ],
        ascending=[False, False, False, False],
    ).head(args.candidate_count).copy()
    candidates.insert(0, "phase14_topup_candidate_index", range(1, len(candidates) + 1))
    candidates["dataset_label"] = "czechlynx"
    candidates["phase14_md_candidate_id"] = [
        f"phase14_czechlynx_high_topup_{i:05d}" for i in range(1, len(candidates) + 1)
    ]
    candidates["phase14_topup_source"] = "middle_reviewable_unused_ranked_by_prefeature_score"
    candidates["phase14_topup_role"] = "czechlynx_high_confidence_detector_screening_topup"

    manifest_path = out_dir / "phase14_czechlynx_high_topup_candidate_manifest.csv"
    candidates.to_csv(manifest_path, index=False)

    summary = {
        "candidate_count_requested": args.candidate_count,
        "candidate_rows": int(len(candidates)),
        "source_pool": rel(resolve(args.pool)),
        "excluded_used_sources": [rel(resolve(args.gated)), rel(resolve(args.low))],
        "selection_rule": "wild middle_reviewable unused images ranked by auto evidence, quality, blur, and contrast",
        "score_summary": {
            str(stat): {
                str(col): float(value)
                for col, value in row.items()
            }
            for stat, row in candidates[
                [
                    "phase14_czechlynx_topup_score",
                    "auto_evidence_score",
                    "auto_quality_score",
                    "blur_laplacian_var",
                    "contrast_std",
                ]
            ].agg(["min", "mean", "median", "max"]).iterrows()
        },
        "bucket_counts": {
            f"{bucket}|{conf}": int(count)
            for (bucket, conf), count in candidates.groupby(
                ["human_review_bucket", "human_review_confidence"], dropna=False
            ).size().sort_values(ascending=False).items()
        },
        "outputs": {"manifest": rel(manifest_path)},
    }
    summary_path = out_dir / "phase14_czechlynx_high_topup_candidate_manifest_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"PASS prepared CzechLynx high top-up candidates rows={len(candidates)} manifest={rel(manifest_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
