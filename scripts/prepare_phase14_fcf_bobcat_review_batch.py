#!/usr/bin/env python3
"""Prepare a stratified human-review batch from FCF bobcat auto prefeatures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREFEATURES = PROJECT_ROOT / "data/external/felidae_conservation_fund/labels/fcf_bobcat_3000_auto_prefeatures.csv"
OUT_DIR = PROJECT_ROOT / "data/external/felidae_conservation_fund/review_batches"
DEFAULT_REVIEW = OUT_DIR / "fcf_bobcat_400_human_review_manifest.csv"
DEFAULT_AUDIT = OUT_DIR / "fcf_bobcat_400_human_review_manifest_audit.json"
RANDOM_SEED = 20260618

TARGET_BUCKET_COUNTS = {
    "likely_review_ready": 120,
    "review_limited": 120,
    "likely_species_level_only": 100,
    "defer_manual_check": 40,
}


def relative(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT))


def select_bucket(frame: pd.DataFrame, bucket: str, n: int) -> pd.DataFrame:
    part = frame[frame["auto_review_bucket"].eq(bucket)].copy()
    if len(part) == 0:
        return part
    part["boundary_priority"] = (part["auto_evidence_score"] - 0.60).abs()
    part["failure_diversity"] = part["auto_failure_flags"].astype(str)
    selected = (
        part.groupby(["year", "location_id"], group_keys=False)
        .sample(frac=1.0, random_state=RANDOM_SEED)
        .assign(_stratum_order=lambda x: x.groupby(["year", "location_id"]).cumcount())
        .sort_values(["_stratum_order", "boundary_priority", "failure_diversity", "image_id"])
        .head(n)
        .drop(columns=["_stratum_order"])
    )
    return selected


def build_review_manifest(prefeatures: pd.DataFrame, target_size: int) -> pd.DataFrame:
    selected_parts = []
    night_ir = prefeatures[prefeatures["auto_night_ir"].eq("yes")].copy()
    if len(night_ir):
        selected_parts.append(night_ir.sort_values(["auto_evidence_score", "year", "location_id", "image_id"]))
    for bucket, n in TARGET_BUCKET_COUNTS.items():
        remaining_for_bucket = prefeatures[
            ~prefeatures["image_id"].isin(set(pd.concat(selected_parts, ignore_index=True)["image_id"]))
        ].copy() if selected_parts else prefeatures
        selected_parts.append(select_bucket(remaining_for_bucket, bucket, n))
    selected = pd.concat(selected_parts, ignore_index=True)
    if len(selected) < target_size:
        remaining = prefeatures[~prefeatures["image_id"].isin(set(selected["image_id"]))].copy()
        remaining["boundary_priority"] = (remaining["auto_evidence_score"] - 0.60).abs()
        supplement = remaining.sort_values(["boundary_priority", "year", "location_id", "image_id"]).head(target_size - len(selected))
        selected = pd.concat([selected, supplement], ignore_index=True)
    selected = selected.head(target_size).sample(frac=1.0, random_state=RANDOM_SEED).reset_index(drop=True)
    selected.insert(0, "review_index", range(1, len(selected) + 1))

    review = selected[
        [
            "review_index",
            "sample_index",
            "source_dataset",
            "species_label",
            "scientific_name",
            "image_id",
            "datetime",
            "year",
            "month",
            "location_id",
            "local_relative_path",
            "auto_review_bucket",
            "auto_evidence_score",
            "auto_quality_score",
            "auto_night_ir",
            "auto_blur_band",
            "auto_exposure_band",
            "auto_contrast_band",
            "auto_center_animal_signal",
            "auto_failure_flags",
            "brightness_mean",
            "contrast_std",
            "edge_density",
            "center_contrast",
            "center_edge_density",
            "underexposed_fraction",
            "overexposed_fraction",
            "colorfulness",
        ]
    ].copy()
    review["human_pattern_visibility"] = ""
    review["human_side_flank_visibility"] = ""
    review["human_body_visibility"] = ""
    review["human_blur_level"] = ""
    review["human_occlusion_level"] = ""
    review["human_background_complexity"] = ""
    review["human_modified_background"] = ""
    review["human_review_bucket"] = ""
    review["human_review_confidence"] = ""
    review["human_notes"] = ""
    return review


def write_audit(review: pd.DataFrame, prefeatures: pd.DataFrame, audit_path: Path) -> None:
    audit: dict[str, Any] = {
        "review_row_count": int(len(review)),
        "source_prefeature_rows": int(len(prefeatures)),
        "auto_review_bucket_counts": {str(k): int(v) for k, v in review["auto_review_bucket"].value_counts().sort_index().items()},
        "year_counts": {str(k): int(v) for k, v in review["year"].value_counts().sort_index().items()},
        "location_count": int(review["location_id"].nunique()),
        "night_ir_counts": {str(k): int(v) for k, v in review["auto_night_ir"].value_counts().sort_index().items()},
        "claim_boundary": "human_review_manifest_for_auditing_machine_prefeatures_not_ground_truth_until_reviewed",
        "random_seed": RANDOM_SEED,
    }
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefeatures", default=str(DEFAULT_PREFEATURES))
    parser.add_argument("--output", default=str(DEFAULT_REVIEW))
    parser.add_argument("--audit", default=str(DEFAULT_AUDIT))
    parser.add_argument("--target-size", type=int, default=400)
    args = parser.parse_args()

    prefeatures_path = Path(args.prefeatures)
    output = Path(args.output)
    audit = Path(args.audit)
    if not prefeatures_path.is_absolute():
        prefeatures_path = PROJECT_ROOT / prefeatures_path
    if not output.is_absolute():
        output = PROJECT_ROOT / output
    if not audit.is_absolute():
        audit = PROJECT_ROOT / audit

    prefeatures = pd.read_csv(prefeatures_path)
    ok = prefeatures[prefeatures["auto_prefeature_status"].eq("ok")].copy()
    review = build_review_manifest(ok, args.target_size)
    output.parent.mkdir(parents=True, exist_ok=True)
    review.to_csv(output, index=False)
    write_audit(review, ok, audit)
    print(
        "PASS phase14 FCF bobcat review batch "
        f"rows={len(review)} locations={review['location_id'].nunique()} "
        f"output={relative(output)} audit={relative(audit)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
