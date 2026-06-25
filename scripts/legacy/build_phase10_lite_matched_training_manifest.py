#!/usr/bin/env python3
"""Build Phase 10-Lite matched-identity training manifests.

This script does not train models. It creates matched image-selection manifests
that control identity coverage and per-identity image count before any further
PF-ERI metric-learning escalation.
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
TRAINING_GROUP_PLAN = INPUT_DIR / "phase9d_training_group_plan.csv"

IDENTITY_READINESS = OUTPUT_DIR / "phase10_lite_identity_readiness.csv"
SUMMARY = OUTPUT_DIR / "phase10_lite_training_readiness_summary.csv"

RANDOM_SEED = 20260615
GROUPS = {
    "B2_random_matched_identity": "deterministic_random_k_images_per_identity",
    "C2_quality_matched_identity": "top_k_quality_proxy_images_per_identity",
    "D2_pf_eri_matched_identity": "top_k_pf_eri_images_per_identity",
}
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


def stable_random_value(split_id: int, identity: str, image_id: str, k: int) -> float:
    """Return a deterministic pseudo-random value in [0, 1)."""
    text = f"{RANDOM_SEED}|split={split_id}|k={k}|identity={identity}|image={image_id}"
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(digest[:16], 16) / float(16**16)


def require_columns(df: pd.DataFrame, path: Path, columns: list[str]) -> None:
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise ValueError(f"{path} is missing required columns: {', '.join(missing)}")


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if not IMAGE_MANIFEST.exists():
        raise FileNotFoundError(IMAGE_MANIFEST)
    if not SPLIT_DESIGN.exists():
        raise FileNotFoundError(SPLIT_DESIGN)
    if not TRAINING_GROUP_PLAN.exists():
        raise FileNotFoundError(TRAINING_GROUP_PLAN)

    manifest = pd.read_csv(IMAGE_MANIFEST)
    split_design = pd.read_csv(SPLIT_DESIGN)
    group_plan = pd.read_csv(TRAINING_GROUP_PLAN)
    require_columns(
        manifest,
        IMAGE_MANIFEST,
        [
            "image_id",
            "identity_label_internal",
            "pf_eri_image_score",
            "split_id",
            "train_val_test_role",
        ],
    )
    return manifest, split_design, group_plan


def build_identity_readiness(manifest: pd.DataFrame) -> pd.DataFrame:
    unique_images = manifest.drop_duplicates(["identity_label_internal", "image_id"]).copy()
    unique_images["high_pf_eri"] = pd.to_numeric(
        unique_images["pf_eri_image_score"], errors="coerce"
    ).fillna(-1) >= 0.55
    split_counts = (
        manifest.groupby("identity_label_internal")["split_id"].nunique().rename("available_split_count")
    )
    rows = []
    for identity, group in unique_images.groupby("identity_label_internal", sort=True):
        image_count = int(group["image_id"].nunique())
        ready_k2 = image_count >= 2
        ready_k3 = image_count >= 3
        if ready_k2 and ready_k3:
            reason = "ready_k2_and_k3"
        elif ready_k2:
            reason = "ready_k2_only_insufficient_k3_images"
        else:
            reason = "insufficient_images_for_k2"
        rows.append(
            {
                "identity_label_internal": identity,
                "image_count": image_count,
                "available_split_count": int(split_counts.get(identity, 0)),
                "high_pf_eri_count": int(group["high_pf_eri"].sum()),
                "pilot_ready_k2": bool(ready_k2),
                "pilot_ready_k3": bool(ready_k3),
                "failure_reason": reason,
            }
        )
    return pd.DataFrame(rows)


def select_group_rows(group: pd.DataFrame, phase10_group: str, k: int, split_id: int) -> pd.DataFrame:
    work = group.copy()
    work["pf_eri_image_score"] = pd.to_numeric(work["pf_eri_image_score"], errors="coerce").fillna(-1.0)
    work["quality_bucket_rank"] = work.get("quality_bucket", pd.Series(index=work.index, dtype=object)).map(
        QUALITY_BUCKET_RANK
    ).fillna(0)

    if phase10_group == "B2_random_matched_identity":
        work["selection_sort_value"] = [
            stable_random_value(split_id, str(row.identity_label_internal), str(row.image_id), k)
            for row in work.itertuples(index=False)
        ]
        work = work.sort_values(["selection_sort_value", "image_id"], ascending=[True, True])
        limitation = "not_applicable_random_control"
    elif phase10_group == "C2_quality_matched_identity":
        work = work.sort_values(
            ["quality_bucket_rank", "pf_eri_image_score", "image_id"],
            ascending=[False, False, True],
        )
        limitation = "quality_bucket_plus_pf_eri_proxy_no_independent_numeric_quality_score"
    elif phase10_group == "D2_pf_eri_matched_identity":
        work = work.sort_values(["pf_eri_image_score", "image_id"], ascending=[False, True])
        limitation = "not_applicable_pf_eri_selection"
    else:
        raise ValueError(f"unknown group: {phase10_group}")

    selected = work.head(k).copy()
    selected["phase10_lite_group"] = phase10_group
    selected["images_per_identity_k"] = int(k)
    selected["selection_rule"] = GROUPS[phase10_group]
    selected["selection_rank_within_identity"] = range(1, len(selected) + 1)
    selected["quality_proxy_limitation"] = limitation
    return selected


def build_matched_manifest(manifest: pd.DataFrame, k: int) -> pd.DataFrame:
    train = manifest[manifest["train_val_test_role"].astype(str).str.lower() == "train"].copy()
    rows: list[pd.DataFrame] = []
    for split_id, split_rows in train.groupby("split_id", sort=True):
        counts = split_rows.groupby("identity_label_internal")["image_id"].nunique()
        eligible_identities = sorted(counts[counts >= k].index.astype(str))
        eligible_rows = split_rows[
            split_rows["identity_label_internal"].astype(str).isin(eligible_identities)
        ].copy()
        for phase10_group in GROUPS:
            for identity, identity_rows in eligible_rows.groupby("identity_label_internal", sort=True):
                rows.append(select_group_rows(identity_rows, phase10_group, k, int(split_id)))

    if not rows:
        return pd.DataFrame(columns=ESSENTIAL_COLUMNS)

    out = pd.concat(rows, ignore_index=True)
    preserved = [col for col in ESSENTIAL_COLUMNS if col in out.columns]
    added = [
        "phase10_lite_group",
        "images_per_identity_k",
        "selection_rule",
        "selection_rank_within_identity",
        "quality_proxy_limitation",
    ]
    return out[preserved + added].sort_values(
        [
            "split_id",
            "phase10_lite_group",
            "identity_label_internal",
            "selection_rank_within_identity",
            "image_id",
        ]
    )


def build_summary(
    manifest: pd.DataFrame,
    readiness: pd.DataFrame,
    outputs: dict[int, pd.DataFrame],
    split_design: pd.DataFrame,
    group_plan: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    rows.append(
        {
            "section": "input",
            "metric": "phase9d_manifest_rows",
            "value": int(len(manifest)),
            "note": "Phase 9D image manifest loaded; no raw data modified.",
        }
    )
    rows.append(
        {
            "section": "input",
            "metric": "phase9d_split_design_rows",
            "value": int(len(split_design)),
            "note": "Split design inspected for availability.",
        }
    )
    rows.append(
        {
            "section": "input",
            "metric": "phase9d_training_group_plan_rows",
            "value": int(len(group_plan)),
            "note": "Historical Phase 9D group plan retained as motivation only.",
        }
    )
    rows.append(
        {
            "section": "identity_readiness",
            "metric": "identity_count",
            "value": int(readiness["identity_label_internal"].nunique()),
            "note": "Unique internal validation identities in Phase 9D manifest.",
        }
    )
    for k in [2, 3]:
        ready_col = f"pilot_ready_k{k}"
        rows.append(
            {
                "section": "identity_readiness",
                "metric": f"ready_identity_count_k{k}",
                "value": int(readiness[ready_col].sum()) if ready_col in readiness else 0,
                "note": f"Identities with at least {k} unique images.",
            }
        )
    for k, df in outputs.items():
        if df.empty:
            rows.append(
                {
                    "section": "matched_manifest",
                    "metric": f"k{k}_feasible",
                    "value": "no",
                    "note": "No eligible train identities found.",
                }
            )
            continue
        for split_id, split_rows in df.groupby("split_id", sort=True):
            identity_counts = split_rows.groupby("phase10_lite_group")["identity_label_internal"].nunique()
            row_counts = split_rows.groupby("phase10_lite_group").size()
            rows.append(
                {
                    "section": "matched_manifest",
                    "metric": f"k{k}_split_{split_id}_groups",
                    "value": int(split_rows["phase10_lite_group"].nunique()),
                    "note": (
                        "identity_counts="
                        + ";".join(f"{idx}:{val}" for idx, val in identity_counts.items())
                        + " row_counts="
                        + ";".join(f"{idx}:{val}" for idx, val in row_counts.items())
                    ),
                }
            )
    rows.append(
        {
            "section": "limitation",
            "metric": "quality_control_proxy",
            "value": "quality_bucket_plus_pf_eri_score_tiebreak",
            "note": "No independent numeric quality score was available in the Phase 9D manifest.",
        }
    )
    rows.append(
        {
            "section": "claim_boundary",
            "metric": "training_performed",
            "value": "no",
            "note": "Phase 10-Lite only builds and audits manifests.",
        }
    )
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest, split_design, group_plan = load_inputs()
    readiness = build_identity_readiness(manifest)
    readiness.to_csv(args.output_dir / IDENTITY_READINESS.name, index=False)

    outputs: dict[int, pd.DataFrame] = {}
    for k in [2, 3]:
        matched = build_matched_manifest(manifest, k)
        outputs[k] = matched
        if not matched.empty:
            matched.to_csv(
                args.output_dir / f"phase10_lite_matched_training_manifest_k{k}.csv",
                index=False,
            )

    summary = build_summary(manifest, readiness, outputs, split_design, group_plan)
    summary.to_csv(args.output_dir / SUMMARY.name, index=False)

    print("PASS build_phase10_lite_matched_training_manifest")
    print(f"output_dir={args.output_dir}")
    for k, df in outputs.items():
        print(f"k{k}_rows={len(df)}")
        print(f"k{k}_splits={df['split_id'].nunique() if not df.empty else 0}")
        print(f"k{k}_groups={df['phase10_lite_group'].nunique() if not df.empty else 0}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
