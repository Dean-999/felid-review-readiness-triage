#!/usr/bin/env python3
"""Build Phase 10-Lite Plus accuracy-oriented training manifests.

This is a manifest-generation step only. It does not train models or alter
source data.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase9/pf_eri_metric_learning_prep"
OUTPUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase10_lite"
IMAGE_MANIFEST = INPUT_DIR / "phase9d_image_training_manifest_internal.csv"
SPLIT_DESIGN = INPUT_DIR / "phase9d_split_design_internal.csv"

PLUS_MANIFEST = OUTPUT_DIR / "phase10_lite_plus_matched_training_manifest_k3.csv"
SUMMARY = OUTPUT_DIR / "phase10_lite_plus_training_readiness_summary.csv"

RANDOM_SEED = 20260615
K = 3
MATCHED_GROUPS = {
    "B3_random_matched_identity": "deterministic_random_3_images_per_identity",
    "C3_quality_proxy_matched_identity": "top_3_quality_bucket_then_pf_eri_tiebreak",
    "D3_pf_eri_matched_identity": "top_3_pf_eri_images_per_identity",
    "H3_pf_eri_quality_hybrid_matched_identity": "top_3_predeclared_hybrid_score",
}
E4_GROUP = "E4_pf_eri_weighted_all_train_reference"
ESSENTIAL_COLUMNS = [
    "image_path_internal",
    "image_id",
    "identity_label_internal",
    "pf_eri_image_score",
    "visual_penalty",
    "quality_bucket",
    "source_phase",
    "split_id",
    "train_val_test_role",
    "near_duplicate_group_if_available",
    "image_file_available",
    "embedding_required",
]
QUALITY_BUCKET_RANK = {
    "high": 4,
    "medium_high": 3,
    "medium_low": 2,
    "low": 1,
}


def stable_random_value(split_id: int, identity: str, image_id: str) -> float:
    text = f"{RANDOM_SEED}|phase10_lite_plus|split={split_id}|identity={identity}|image={image_id}"
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(digest[:16], 16) / float(16**16)


def add_components(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["pf_eri_image_score"] = pd.to_numeric(out["pf_eri_image_score"], errors="coerce").fillna(0.0)
    out["quality_bucket_rank"] = out.get("quality_bucket", pd.Series(index=out.index, dtype=object)).map(
        QUALITY_BUCKET_RANK
    ).fillna(0.0)
    out["quality_bucket_rank_normalized"] = (out["quality_bucket_rank"] / 4.0).clip(0, 1)
    out["hybrid_score"] = (
        0.65 * out["pf_eri_image_score"] + 0.35 * out["quality_bucket_rank_normalized"]
    ).clip(0, 1)
    out["sample_weight"] = (0.25 + 0.75 * out["pf_eri_image_score"]).clip(0.25, 1.0)
    return out


def load_manifest() -> pd.DataFrame:
    if not IMAGE_MANIFEST.exists():
        raise FileNotFoundError(IMAGE_MANIFEST)
    manifest = pd.read_csv(IMAGE_MANIFEST)
    required = {"image_id", "identity_label_internal", "pf_eri_image_score", "split_id", "train_val_test_role"}
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"{IMAGE_MANIFEST} missing required columns: {sorted(missing)}")
    return add_components(manifest)


def select_matched_identity_rows(identity_rows: pd.DataFrame, group_name: str, split_id: int) -> pd.DataFrame:
    work = identity_rows.copy()
    if group_name == "B3_random_matched_identity":
        work["selection_sort_value"] = [
            stable_random_value(split_id, str(row.identity_label_internal), str(row.image_id))
            for row in work.itertuples(index=False)
        ]
        work = work.sort_values(["selection_sort_value", "image_id"], ascending=[True, True])
    elif group_name == "C3_quality_proxy_matched_identity":
        work = work.sort_values(
            ["quality_bucket_rank_normalized", "pf_eri_image_score", "image_id"],
            ascending=[False, False, True],
        )
    elif group_name == "D3_pf_eri_matched_identity":
        work = work.sort_values(["pf_eri_image_score", "image_id"], ascending=[False, True])
    elif group_name == "H3_pf_eri_quality_hybrid_matched_identity":
        work = work.sort_values(["hybrid_score", "pf_eri_image_score", "image_id"], ascending=[False, False, True])
    else:
        raise ValueError(f"unknown group: {group_name}")

    selected = work.head(K).copy()
    selected["phase10_lite_plus_group"] = group_name
    selected["images_per_identity_k"] = K
    selected["selection_rule"] = MATCHED_GROUPS[group_name]
    selected["selection_rank_within_identity"] = range(1, len(selected) + 1)
    if group_name == "C3_quality_proxy_matched_identity":
        selected["quality_proxy_limitation"] = "quality_bucket_first_pf_eri_tiebreak_not_fully_independent"
    else:
        selected["quality_proxy_limitation"] = "not_applicable"
    return selected


def build_plus_manifest(manifest: pd.DataFrame) -> pd.DataFrame:
    train = manifest[manifest["train_val_test_role"].astype(str).str.lower() == "train"].copy()
    parts: list[pd.DataFrame] = []
    for split_id, split_rows in train.groupby("split_id", sort=True):
        counts = split_rows.groupby("identity_label_internal")["image_id"].nunique()
        eligible_identities = sorted(counts[counts >= K].index.astype(str))
        eligible_rows = split_rows[split_rows["identity_label_internal"].astype(str).isin(eligible_identities)].copy()
        for group_name in MATCHED_GROUPS:
            for _, identity_rows in eligible_rows.groupby("identity_label_internal", sort=True):
                parts.append(select_matched_identity_rows(identity_rows, group_name, int(split_id)))

        e4 = split_rows.copy()
        e4["phase10_lite_plus_group"] = E4_GROUP
        e4["images_per_identity_k"] = "4_or_all_available"
        e4["selection_rule"] = "all_available_train_images_pf_eri_weighted_reference"
        e4["selection_rank_within_identity"] = (
            e4.sort_values(["identity_label_internal", "image_id"])
            .groupby("identity_label_internal")
            .cumcount()
            + 1
        )
        e4["quality_proxy_limitation"] = "not_applicable_all_train_reference"
        parts.append(e4)

    out = pd.concat(parts, ignore_index=True)
    preserved = [col for col in ESSENTIAL_COLUMNS if col in out.columns]
    added = [
        "phase10_lite_plus_group",
        "images_per_identity_k",
        "selection_rule",
        "selection_rank_within_identity",
        "sample_weight",
        "quality_bucket_rank_normalized",
        "hybrid_score",
        "quality_proxy_limitation",
    ]
    return out[preserved + added].sort_values(
        [
            "split_id",
            "phase10_lite_plus_group",
            "identity_label_internal",
            "selection_rank_within_identity",
            "image_id",
        ]
    )


def build_summary(plus: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for split_id, split_rows in plus.groupby("split_id", sort=True):
        for group, group_rows in split_rows.groupby("phase10_lite_plus_group", sort=True):
            per_identity = group_rows.groupby("identity_label_internal")["image_id"].nunique()
            rows.append(
                {
                    "split_id": int(split_id),
                    "phase10_lite_plus_group": group,
                    "row_count": int(len(group_rows)),
                    "identity_count": int(group_rows["identity_label_internal"].nunique()),
                    "min_images_per_identity": int(per_identity.min()),
                    "max_images_per_identity": int(per_identity.max()),
                    "is_matched_k3_group": group in MATCHED_GROUPS,
                    "is_all_train_reference": group == E4_GROUP,
                    "note": (
                        "matched_k3_accuracy_candidate"
                        if group in MATCHED_GROUPS
                        else "all_train_pf_eri_weighted_reference_not_matched_k3"
                    ),
                }
            )
    rows.append(
        {
            "split_id": "all",
            "phase10_lite_plus_group": "quality_proxy_limitation",
            "row_count": "",
            "identity_count": "",
            "min_images_per_identity": "",
            "max_images_per_identity": "",
            "is_matched_k3_group": "",
            "is_all_train_reference": "",
            "note": "C3 uses quality_bucket first; pf_eri_image_score only tie-break/fallback.",
        }
    )
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    plus = build_plus_manifest(manifest)
    plus.to_csv(args.output_dir / PLUS_MANIFEST.name, index=False)
    build_summary(plus).to_csv(args.output_dir / SUMMARY.name, index=False)
    print("PASS build_phase10_lite_plus_matched_training_manifest")
    print(f"rows={len(plus)}")
    print(f"splits={plus['split_id'].nunique()}")
    print(f"groups={plus['phase10_lite_plus_group'].nunique()}")
    print(f"manifest={args.output_dir / PLUS_MANIFEST.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
