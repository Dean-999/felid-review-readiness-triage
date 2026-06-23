#!/usr/bin/env python3
"""Build Phase 14 2x2 high-confidence and low-evidence evidence sets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "outputs/phase14/phase14_2x2_evidence_sets"

BOBCAT_ORIGINAL = PROJECT_ROOT / "data/external/felidae_conservation_fund/review_batches/fcf_bobcat_3000_ai_refined_review_labels.csv"
BOBCAT_EXPANSION = (
    PROJECT_ROOT
    / "data/external/felidae_conservation_fund/review_batches/fcf_bobcat_phase14_2x2_expansion_6000_ai_refined_review_labels.csv"
)
CZECH_ORIGINAL = PROJECT_ROOT / "data/interim/czechlynx/phase14/czechlynx_phase14_3000_pose_refined_review_labels.csv"
CZECH_EXPANSION = PROJECT_ROOT / "data/interim/czechlynx/phase14/czechlynx_phase14_2x2_expansion_6000_refined_review_labels.csv"

HIGH_BUCKETS = {"review_ready", "review_limited"}
HIGH_CONFIDENCE = {"high", "medium"}
STRESS_BUCKETS = {"species_level_only", "uncertain"}


def resolve(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else PROJECT_ROOT / path


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def load_table(path: Path, dataset: str, context: str, pool_source: str) -> pd.DataFrame:
    frame = pd.read_csv(path)
    frame["dataset_role"] = dataset
    frame["environment_context"] = context
    frame["pool_source"] = pool_source
    if "review_image_path_local" in frame.columns:
        frame["evidence_image_path"] = frame["review_image_path_local"].astype(str)
    else:
        frame["evidence_image_path"] = frame["local_relative_path"].astype(str)
    if "identity_label" not in frame.columns:
        frame["identity_label"] = ""
    if "location_id" not in frame.columns:
        frame["location_id"] = ""
    if "year" not in frame.columns:
        frame["year"] = ""
    if "auto_prefeature_status" not in frame.columns:
        frame["auto_prefeature_status"] = "unknown"
    if "auto_evidence_score" not in frame.columns:
        frame["auto_evidence_score"] = 0.0
    if "auto_quality_score" not in frame.columns:
        frame["auto_quality_score"] = 0.0
    return frame


def normalize_bool_text(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.lower()


def assign_roles(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    bucket = normalize_bool_text(out["human_review_bucket"])
    confidence = normalize_bool_text(out["human_review_confidence"])
    manual = normalize_bool_text(out["needs_manual_check"])
    status = normalize_bool_text(out["auto_prefeature_status"])

    readable = status.eq("ok")
    high_eligible = bucket.isin(HIGH_BUCKETS) & confidence.isin(HIGH_CONFIDENCE) & manual.eq("no") & readable
    strict_high = bucket.eq("review_ready") & confidence.eq("high") & manual.eq("no") & readable
    stress_eligible = (
        readable
        & (
            manual.eq("yes")
            | confidence.eq("low")
            | bucket.isin(STRESS_BUCKETS)
        )
    )
    excluded = ~readable

    out["training_eligible"] = high_eligible.map({True: "yes", False: "no"})
    out["strict_high_confidence_eligible"] = strict_high.map({True: "yes", False: "no"})
    out["stress_test_eligible"] = stress_eligible.map({True: "yes", False: "no"})
    out["manual_audit_needed"] = manual.where(manual.isin(["yes", "no"]), "unknown")
    out["evidence_tier"] = "medium_reviewable"
    out.loc[high_eligible, "evidence_tier"] = "high_confidence"
    out.loc[stress_eligible, "evidence_tier"] = "low_evidence_stress"
    out.loc[excluded, "evidence_tier"] = "excluded"
    out["evidence_role"] = ""
    out.loc[high_eligible, "evidence_role"] = "core_training;retrieval_evaluation;wild_urban_clean_comparison"
    out.loc[stress_eligible, "evidence_role"] = "low_evidence_stress_test;manual_audit_calibration"
    out.loc[excluded, "evidence_role"] = "excluded_non_felid_or_duplicate"
    out["exclusion_reason"] = ""
    out.loc[excluded, "exclusion_reason"] = "auto_prefeature_failed_or_unreadable"
    out["risk_control_notes"] = ""
    out.loc[high_eligible, "risk_control_notes"] = "admit_to_clean_evidence_pool"
    out.loc[stress_eligible, "risk_control_notes"] = "route_to_stress_or_manual_audit_not_core_training"
    out.loc[excluded, "risk_control_notes"] = "exclude_from_training_and_stress_analysis"
    return out


def sorted_high(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    bucket_rank = {"review_ready": 0, "review_limited": 1}
    confidence_rank = {"high": 0, "medium": 1}
    out["_bucket_rank"] = normalize_bool_text(out["human_review_bucket"]).map(bucket_rank).fillna(9)
    out["_confidence_rank"] = normalize_bool_text(out["human_review_confidence"]).map(confidence_rank).fillna(9)
    out["_evidence_score"] = pd.to_numeric(out["auto_evidence_score"], errors="coerce").fillna(-1)
    out["_quality_score"] = pd.to_numeric(out["auto_quality_score"], errors="coerce").fillna(-1)
    return out.sort_values(
        ["_bucket_rank", "_confidence_rank", "_evidence_score", "_quality_score", "evidence_image_path"],
        ascending=[True, True, False, False, True],
    ).drop(columns=["_bucket_rank", "_confidence_rank", "_evidence_score", "_quality_score"])


def sorted_stress(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    bucket_rank = {"uncertain": 0, "species_level_only": 1, "review_limited": 2, "review_ready": 3}
    confidence_rank = {"low": 0, "medium": 1, "high": 2}
    out["_bucket_rank"] = normalize_bool_text(out["human_review_bucket"]).map(bucket_rank).fillna(9)
    out["_confidence_rank"] = normalize_bool_text(out["human_review_confidence"]).map(confidence_rank).fillna(9)
    out["_manual_rank"] = normalize_bool_text(out["needs_manual_check"]).map({"yes": 0, "no": 1}).fillna(9)
    out["_evidence_score"] = pd.to_numeric(out["auto_evidence_score"], errors="coerce").fillna(1)
    out["_quality_score"] = pd.to_numeric(out["auto_quality_score"], errors="coerce").fillna(1)
    return out.sort_values(
        ["_manual_rank", "_confidence_rank", "_bucket_rank", "_evidence_score", "_quality_score", "evidence_image_path"],
        ascending=[True, True, True, True, True, True],
    ).drop(columns=["_bucket_rank", "_confidence_rank", "_manual_rank", "_evidence_score", "_quality_score"])


def round_robin_by_identity(frame: pd.DataFrame, target: int, sort_fn, min_per_identity: int = 1) -> pd.DataFrame:
    ordered = sort_fn(frame)
    if min_per_identity > 1:
        counts = ordered["identity_label"].astype(str).value_counts()
        keep = set(counts[counts >= min_per_identity].index)
        ordered = ordered[ordered["identity_label"].astype(str).isin(keep)].copy()
    groups = {str(k): g.reset_index(drop=True) for k, g in ordered.groupby("identity_label", sort=True)}
    rows: list[pd.Series] = []
    if min_per_identity > 1:
        for identity in sorted(groups):
            group = groups[identity]
            for index in range(min_per_identity):
                rows.append(group.iloc[index])
                if len(rows) >= target:
                    return pd.DataFrame(rows).reset_index(drop=True)
    depth = min_per_identity if min_per_identity > 1 else 0
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
        raise ValueError(f"identity round-robin selected {len(rows)} rows, target={target}")
    return pd.DataFrame(rows).reset_index(drop=True)


def select_dataset(frame: pd.DataFrame, target: int, dataset: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    high_pool = frame[frame["training_eligible"].eq("yes")].copy()
    stress_pool = frame[frame["stress_test_eligible"].eq("yes")].copy()
    if len(high_pool) < target:
        raise ValueError(f"{dataset} high-confidence pool has {len(high_pool)} rows, target={target}")
    if len(stress_pool) < target:
        raise ValueError(f"{dataset} low-evidence stress pool has {len(stress_pool)} rows, target={target}")

    if dataset == "czechlynx":
        high = round_robin_by_identity(high_pool, target, sorted_high, min_per_identity=2)
        stress = round_robin_by_identity(stress_pool, target, sorted_stress, min_per_identity=2)
    else:
        high = sorted_high(high_pool).head(target).copy().reset_index(drop=True)
        stress = sorted_stress(stress_pool).head(target).copy().reset_index(drop=True)
    high.insert(0, "phase14_2x2_set_index", range(1, len(high) + 1))
    stress.insert(0, "phase14_2x2_set_index", range(1, len(stress) + 1))
    return high, stress


def write_outputs(
    bobcat: pd.DataFrame,
    czech: pd.DataFrame,
    bobcat_high: pd.DataFrame,
    bobcat_stress: pd.DataFrame,
    czech_high: pd.DataFrame,
    czech_stress: pd.DataFrame,
    out_dir: Path,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "combined_pool": out_dir / "phase14_2x2_combined_evidence_pool.csv",
        "bobcat_high": out_dir / "phase14_2x2_bobcat_high_confidence_3000.csv",
        "bobcat_stress": out_dir / "phase14_2x2_bobcat_low_evidence_stress_3000.csv",
        "czech_high": out_dir / "phase14_2x2_czechlynx_high_confidence_3000.csv",
        "czech_stress": out_dir / "phase14_2x2_czechlynx_low_evidence_stress_3000.csv",
    }
    combined = pd.concat([bobcat, czech], ignore_index=True)
    combined.to_csv(outputs["combined_pool"], index=False)
    bobcat_high.to_csv(outputs["bobcat_high"], index=False)
    bobcat_stress.to_csv(outputs["bobcat_stress"], index=False)
    czech_high.to_csv(outputs["czech_high"], index=False)
    czech_stress.to_csv(outputs["czech_stress"], index=False)

    def counts(frame: pd.DataFrame) -> dict[str, Any]:
        result = {
            "rows": int(len(frame)),
            "evidence_tier_counts": {str(k): int(v) for k, v in frame["evidence_tier"].value_counts().sort_index().items()},
            "bucket_counts": {str(k): int(v) for k, v in frame["human_review_bucket"].value_counts().sort_index().items()},
            "confidence_counts": {str(k): int(v) for k, v in frame["human_review_confidence"].value_counts().sort_index().items()},
            "training_eligible": int(frame["training_eligible"].eq("yes").sum()),
            "stress_test_eligible": int(frame["stress_test_eligible"].eq("yes").sum()),
            "excluded": int(frame["evidence_tier"].eq("excluded").sum()),
            "unique_paths": int(frame["evidence_image_path"].astype(str).nunique()),
        }
        identity_values = frame["identity_label"].fillna("").astype(str).str.strip() if "identity_label" in frame.columns else pd.Series(dtype=str)
        if len(identity_values) and identity_values.ne("").any():
            identity_counts = identity_values[identity_values.ne("")].value_counts()
            result["identity_count"] = int(identity_counts.size)
            result["min_images_per_identity"] = int(identity_counts.min())
            result["median_images_per_identity"] = float(identity_counts.median())
            result["max_images_per_identity"] = int(identity_counts.max())
        if "location_id" in frame.columns and frame["location_id"].astype(str).str.len().gt(0).any():
            result["location_count"] = int(frame["location_id"].astype(str).nunique())
        return result

    audit = {
        "outputs": {key: rel(path) for key, path in outputs.items()},
        "target_per_final_set": int(len(bobcat_high)),
        "bobcat_pool": counts(bobcat),
        "czechlynx_pool": counts(czech),
        "bobcat_high_confidence_3000": counts(bobcat_high),
        "bobcat_low_evidence_stress_3000": counts(bobcat_stress),
        "czechlynx_high_confidence_3000": counts(czech_high),
        "czechlynx_low_evidence_stress_3000": counts(czech_stress),
        "cross_set_path_overlap": {
            "bobcat_high_vs_stress": int(
                len(set(bobcat_high["evidence_image_path"].astype(str)) & set(bobcat_stress["evidence_image_path"].astype(str)))
            ),
            "czechlynx_high_vs_stress": int(
                len(set(czech_high["evidence_image_path"].astype(str)) & set(czech_stress["evidence_image_path"].astype(str)))
            ),
        },
        "claim_boundary": "AI-assisted evidence routing for 2x2 risk-control; human audit still required for final labels",
    }
    audit_path = out_dir / "phase14_2x2_evidence_sets_audit.json"
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=int, default=3000)
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    args = parser.parse_args()

    bobcat = pd.concat(
        [
            load_table(BOBCAT_ORIGINAL, "bobcat", "urban_periurban", "original_3000"),
            load_table(BOBCAT_EXPANSION, "bobcat", "urban_periurban", "nonoverlap_expansion_6000"),
        ],
        ignore_index=True,
    )
    czech = pd.concat(
        [
            load_table(CZECH_ORIGINAL, "czechlynx", "wild", "original_3000"),
            load_table(CZECH_EXPANSION, "czechlynx", "wild", "nonoverlap_expansion_6000"),
        ],
        ignore_index=True,
    )
    bobcat = assign_roles(bobcat)
    czech = assign_roles(czech)

    for name, frame in [("bobcat", bobcat), ("czechlynx", czech)]:
        duplicate_paths = int(frame["evidence_image_path"].astype(str).duplicated().sum())
        if duplicate_paths:
            raise ValueError(f"{name} pool has duplicate evidence_image_path rows: {duplicate_paths}")

    bobcat_high, bobcat_stress = select_dataset(bobcat, args.target, "bobcat")
    czech_high, czech_stress = select_dataset(czech, args.target, "czechlynx")
    audit = write_outputs(bobcat, czech, bobcat_high, bobcat_stress, czech_high, czech_stress, resolve(args.out_dir))

    failures = sum(audit["cross_set_path_overlap"].values())
    status = "PASS" if failures == 0 else "FAIL"
    print(
        f"{status} phase14 2x2 evidence sets "
        f"bobcat_high={len(bobcat_high)} bobcat_stress={len(bobcat_stress)} "
        f"czech_high={len(czech_high)} czech_stress={len(czech_stress)} "
        f"out={rel(resolve(args.out_dir))}"
    )
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
