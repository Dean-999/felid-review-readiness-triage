#!/usr/bin/env python3
"""Build strict Phase 14 2x2 evidence sets targeting high manual precision."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BASE_POOL = PROJECT_ROOT / "outputs/phase14/phase14_2x2_evidence_sets/phase14_2x2_combined_evidence_pool.csv"
CZECH_EXTRA = PROJECT_ROOT / "data/interim/czechlynx/phase14/czechlynx_phase14_strict_2x2_extra_15000_refined_review_labels.csv"
OUT_DIR = PROJECT_ROOT / "outputs/phase14/phase14_strict_2x2_evidence_sets"


def resolve(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else PROJECT_ROOT / path


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def normalize_extra(extra: pd.DataFrame) -> pd.DataFrame:
    out = extra.copy()
    out["dataset_role"] = "czechlynx"
    out["environment_context"] = "wild"
    out["pool_source"] = "strict_nonoverlap_extra_15000"
    out["evidence_image_path"] = out["review_image_path_local"].astype(str)
    if "location_id" not in out.columns:
        out["location_id"] = ""
    if "year" not in out.columns:
        out["year"] = ""
    return out


def add_strict_roles(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    body = out["human_body_visibility"].fillna("").astype(str)
    pattern = out["human_pattern_visibility"].fillna("").astype(str)
    blur = out["human_blur_level"].fillna("").astype(str)
    occlusion = out["human_occlusion_level"].fillna("").astype(str)
    bucket = out["human_review_bucket"].fillna("").astype(str)
    status = out["auto_prefeature_status"].fillna("").astype(str)

    readable = status.eq("ok")
    strict_high = (
        readable
        & body.eq("76_100")
        & pattern.isin(["high", "medium"])
        & blur.isin(["none", "mild"])
        & occlusion.isin(["none", "partial"])
    )
    strict_stress = (
        readable
        & ~strict_high
        & (
            body.isin(["0_25", "26_50"])
            | pattern.isin(["none", "low"])
            | blur.isin(["moderate", "severe"])
            | occlusion.eq("major")
            | bucket.isin(["species_level_only", "uncertain"])
        )
    )

    out["strict_training_eligible"] = strict_high.map({True: "yes", False: "no"})
    out["strict_stress_test_eligible"] = strict_stress.map({True: "yes", False: "no"})
    out["strict_evidence_tier"] = "middle_reviewable"
    out.loc[strict_high, "strict_evidence_tier"] = "high_confidence"
    out.loc[strict_stress, "strict_evidence_tier"] = "low_evidence_stress"
    out.loc[~readable, "strict_evidence_tier"] = "excluded"
    out["strict_evidence_role"] = ""
    out.loc[strict_high, "strict_evidence_role"] = "core_training;retrieval_evaluation;wild_urban_clean_comparison"
    out.loc[strict_stress, "strict_evidence_role"] = "low_evidence_stress_test;manual_audit_calibration"
    out.loc[~readable, "strict_evidence_role"] = "excluded_unreadable"
    out["strict_rule_version"] = "phase14_strict_2x2_v1_manual_audit_derived"
    return out


def rank_high(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    pattern_rank = {"high": 0, "medium": 1}
    blur_rank = {"none": 0, "mild": 1}
    occlusion_rank = {"none": 0, "partial": 1}
    bucket_rank = {"review_ready": 0, "review_limited": 1, "species_level_only": 8, "uncertain": 9}
    confidence_rank = {"high": 0, "medium": 1, "low": 8}
    out["_pattern_rank"] = out["human_pattern_visibility"].astype(str).map(pattern_rank).fillna(9)
    out["_blur_rank"] = out["human_blur_level"].astype(str).map(blur_rank).fillna(9)
    out["_occlusion_rank"] = out["human_occlusion_level"].astype(str).map(occlusion_rank).fillna(9)
    out["_bucket_rank"] = out["human_review_bucket"].astype(str).map(bucket_rank).fillna(9)
    out["_confidence_rank"] = out["human_review_confidence"].astype(str).map(confidence_rank).fillna(9)
    out["_evidence_score"] = pd.to_numeric(out["auto_evidence_score"], errors="coerce").fillna(-1)
    out["_quality_score"] = pd.to_numeric(out["auto_quality_score"], errors="coerce").fillna(-1)
    return out.sort_values(
        [
            "_pattern_rank",
            "_blur_rank",
            "_occlusion_rank",
            "_bucket_rank",
            "_confidence_rank",
            "_evidence_score",
            "_quality_score",
            "evidence_image_path",
        ],
        ascending=[True, True, True, True, True, False, False, True],
    ).drop(columns=[c for c in out.columns if c.startswith("_")])


def rank_stress(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    bucket_rank = {"species_level_only": 0, "uncertain": 1, "review_limited": 2, "review_ready": 9}
    pattern_rank = {"none": 0, "low": 1, "medium": 5, "high": 9}
    body_rank = {"0_25": 0, "26_50": 1, "51_75": 4, "76_100": 9}
    blur_rank = {"severe": 0, "moderate": 1, "mild": 4, "none": 9}
    occlusion_rank = {"major": 0, "partial": 4, "none": 9}
    out["_bucket_rank"] = out["human_review_bucket"].astype(str).map(bucket_rank).fillna(9)
    out["_pattern_rank"] = out["human_pattern_visibility"].astype(str).map(pattern_rank).fillna(9)
    out["_body_rank"] = out["human_body_visibility"].astype(str).map(body_rank).fillna(9)
    out["_blur_rank"] = out["human_blur_level"].astype(str).map(blur_rank).fillna(9)
    out["_occlusion_rank"] = out["human_occlusion_level"].astype(str).map(occlusion_rank).fillna(9)
    out["_evidence_score"] = pd.to_numeric(out["auto_evidence_score"], errors="coerce").fillna(1)
    out["_quality_score"] = pd.to_numeric(out["auto_quality_score"], errors="coerce").fillna(1)
    return out.sort_values(
        [
            "_bucket_rank",
            "_pattern_rank",
            "_body_rank",
            "_blur_rank",
            "_occlusion_rank",
            "_evidence_score",
            "_quality_score",
            "evidence_image_path",
        ],
        ascending=[True, True, True, True, True, True, True, True],
    ).drop(columns=[c for c in out.columns if c.startswith("_")])


def round_robin_by_identity(frame: pd.DataFrame, target: int, rank_fn, min_per_identity: int = 2) -> pd.DataFrame:
    ranked = rank_fn(frame)
    counts = ranked["identity_label"].fillna("").astype(str).value_counts()
    keep = set(counts[counts >= min_per_identity].index)
    ranked = ranked[ranked["identity_label"].fillna("").astype(str).isin(keep)].copy()
    groups = {str(k): g.reset_index(drop=True) for k, g in ranked.groupby("identity_label", sort=True)}
    rows: list[pd.Series] = []
    for identity in sorted(groups):
        group = groups[identity]
        for index in range(min_per_identity):
            rows.append(group.iloc[index])
            if len(rows) >= target:
                return pd.DataFrame(rows).reset_index(drop=True)
    depth = min_per_identity
    while len(rows) < target:
        added = 0
        for identity in sorted(groups):
            group = groups[identity]
            if depth >= len(group):
                continue
            rows.append(group.iloc[depth])
            added += 1
            if len(rows) >= target:
                break
        if added == 0:
            break
        depth += 1
    if len(rows) < target:
        raise ValueError(f"identity-balanced selection got {len(rows)} rows, target={target}")
    return pd.DataFrame(rows).reset_index(drop=True)


def select_set(frame: pd.DataFrame, dataset: str, tier: str, target: int) -> pd.DataFrame:
    if tier == "high":
        pool = frame[frame["strict_training_eligible"].eq("yes")].copy()
        rank_fn = rank_high
    elif tier == "stress":
        pool = frame[frame["strict_stress_test_eligible"].eq("yes")].copy()
        rank_fn = rank_stress
    else:
        raise ValueError(tier)
    if len(pool) < target:
        raise ValueError(f"{dataset} {tier} strict pool has {len(pool)} rows, target={target}")
    if dataset == "czechlynx":
        selected = round_robin_by_identity(pool, target, rank_fn, min_per_identity=2)
    else:
        selected = rank_fn(pool).head(target).copy().reset_index(drop=True)
    selected.insert(0, "strict_set_index", range(1, len(selected) + 1))
    selected["strict_final_set"] = f"{dataset}_{tier}_3000"
    return selected


def counts(frame: pd.DataFrame) -> dict[str, Any]:
    result: dict[str, Any] = {
        "rows": int(len(frame)),
        "unique_paths": int(frame["evidence_image_path"].astype(str).nunique()),
        "bucket_counts": {str(k): int(v) for k, v in frame["human_review_bucket"].astype(str).value_counts().sort_index().items()},
        "pattern_counts": {str(k): int(v) for k, v in frame["human_pattern_visibility"].astype(str).value_counts().sort_index().items()},
        "body_counts": {str(k): int(v) for k, v in frame["human_body_visibility"].astype(str).value_counts().sort_index().items()},
        "blur_counts": {str(k): int(v) for k, v in frame["human_blur_level"].astype(str).value_counts().sort_index().items()},
        "occlusion_counts": {str(k): int(v) for k, v in frame["human_occlusion_level"].astype(str).value_counts().sort_index().items()},
        "pool_source_counts": {str(k): int(v) for k, v in frame["pool_source"].astype(str).value_counts().sort_index().items()},
    }
    ids = frame.get("identity_label", pd.Series(dtype=str)).fillna("").astype(str).str.strip()
    ids = ids[ids.ne("")]
    if len(ids):
        vc = ids.value_counts()
        result.update(
            {
                "identity_count": int(vc.size),
                "min_images_per_identity": int(vc.min()),
                "median_images_per_identity": float(vc.median()),
                "max_images_per_identity": int(vc.max()),
            }
        )
    if "location_id" in frame.columns:
        loc = frame["location_id"].where(frame["location_id"].notna(), "").astype(str).str.strip()
        loc = loc[loc.ne("")]
        if len(loc):
            result["location_count"] = int(loc.nunique())
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-pool", default=str(BASE_POOL))
    parser.add_argument("--czech-extra", default=str(CZECH_EXTRA))
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    parser.add_argument("--target", type=int, default=3000)
    args = parser.parse_args()

    base = pd.read_csv(resolve(args.base_pool), low_memory=False)
    extra = normalize_extra(pd.read_csv(resolve(args.czech_extra), low_memory=False))
    combined = pd.concat([base, extra], ignore_index=True, sort=False)
    combined = add_strict_roles(combined)

    duplicate_paths = int(combined["evidence_image_path"].astype(str).duplicated().sum())
    if duplicate_paths:
        raise ValueError(f"combined strict candidate pool has duplicate paths: {duplicate_paths}")

    bobcat = combined[combined["dataset_role"].astype(str).eq("bobcat")].copy()
    czech = combined[combined["dataset_role"].astype(str).eq("czechlynx")].copy()
    outputs = {
        "combined_pool": "phase14_strict_2x2_combined_candidate_pool.csv",
        "bobcat_high": "phase14_strict_2x2_bobcat_high_confidence_3000.csv",
        "bobcat_stress": "phase14_strict_2x2_bobcat_low_evidence_stress_3000.csv",
        "czech_high": "phase14_strict_2x2_czechlynx_high_confidence_3000.csv",
        "czech_stress": "phase14_strict_2x2_czechlynx_low_evidence_stress_3000.csv",
    }
    out_dir = resolve(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    selected = {
        "bobcat_high": select_set(bobcat, "bobcat", "high", args.target),
        "bobcat_stress": select_set(bobcat, "bobcat", "stress", args.target),
        "czech_high": select_set(czech, "czechlynx", "high", args.target),
        "czech_stress": select_set(czech, "czechlynx", "stress", args.target),
    }
    combined.to_csv(out_dir / outputs["combined_pool"], index=False)
    for key, frame in selected.items():
        frame.to_csv(out_dir / outputs[key], index=False)

    audit = {
        "rule_doc": "docs/phase14/phase14_strict_2x2_rescreening_rules.md",
        "outputs": {key: rel(out_dir / filename) for key, filename in outputs.items()},
        "target_per_set": int(args.target),
        "candidate_pool": {
            "combined_rows": int(len(combined)),
            "bobcat_rows": int(len(bobcat)),
            "czechlynx_rows": int(len(czech)),
            "duplicate_paths": duplicate_paths,
            "bobcat_strict_high_candidates": int(bobcat["strict_training_eligible"].eq("yes").sum()),
            "bobcat_strict_stress_candidates": int(bobcat["strict_stress_test_eligible"].eq("yes").sum()),
            "czechlynx_strict_high_candidates": int(czech["strict_training_eligible"].eq("yes").sum()),
            "czechlynx_strict_stress_candidates": int(czech["strict_stress_test_eligible"].eq("yes").sum()),
        },
        "selected_sets": {key: counts(frame) for key, frame in selected.items()},
        "cross_set_path_overlap": {
            "bobcat_high_vs_stress": int(
                len(
                    set(selected["bobcat_high"]["evidence_image_path"].astype(str))
                    & set(selected["bobcat_stress"]["evidence_image_path"].astype(str))
                )
            ),
            "czech_high_vs_stress": int(
                len(
                    set(selected["czech_high"]["evidence_image_path"].astype(str))
                    & set(selected["czech_stress"]["evidence_image_path"].astype(str))
                )
            ),
        },
        "precision_status": "target_90_percent_pending_second_manual_audit",
        "claim_boundary": "strict rescreened sets are rule-derived candidates, not yet validated as 90_percent_correct",
    }
    audit_path = out_dir / "phase14_strict_2x2_evidence_sets_audit.json"
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    failures = sum(audit["cross_set_path_overlap"].values())
    status = "PASS" if failures == 0 else "FAIL"
    print(
        f"{status} phase14 strict 2x2 evidence sets "
        f"bobcat_high={len(selected['bobcat_high'])} bobcat_stress={len(selected['bobcat_stress'])} "
        f"czech_high={len(selected['czech_high'])} czech_stress={len(selected['czech_stress'])} "
        f"out={rel(out_dir)}"
    )
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
