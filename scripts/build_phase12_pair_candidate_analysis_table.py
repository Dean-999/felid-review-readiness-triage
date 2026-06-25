#!/usr/bin/env python3
"""Build Phase 12 unified pair/candidate analysis table.

This table is the shared substrate for RQ1-RQ4. It rebuilds the fixed-descriptor
top-k candidate pool from internal inputs, computes pair-level PF-ERI reliability
and descriptor-evidence conflict, then exports only safe tokens and analysis
fields.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from phase9b_pf_eri_aware_fixed_descriptor_reranking import (
    ANNOTATION_CSV,
    IDENTITY_CSV,
    MAX_K,
    MEGA_EMBEDDINGS_CSV,
    RESNET_EMBEDDINGS_CSV,
    SPLIT_DESIGN_CSV,
    add_image_utility_components,
    align_inputs,
    build_candidates,
    load_split_design,
    split_roles,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase12"
OUT_TABLE = OUT_DIR / "phase12_pair_candidate_analysis_table.csv"
OUT_SUMMARY = OUT_DIR / "phase12_pair_candidate_analysis_summary.csv"
OUT_AUDIT_JSON = OUT_DIR / "phase12_pair_candidate_analysis_build_audit.json"
PHASE4_500_ANNOTATION_CSV = PROJECT_ROOT / "data/labels/czechlynx/czechlynx_mechanism_visual_factors_full_annotated.csv"
PHASE6_V2_500_ANNOTATION_CSV = PROJECT_ROOT / "data/labels/czechlynx/czechlynx_phase6_unique_500_v2_balanced_image_annotation_v1.csv"
PHASE7A_1000_ANNOTATION_CSV = PROJECT_ROOT / "data/labels/czechlynx/czechlynx_phase7a_1000_image_annotations_v1.csv"

PAIR_SCORE_WEIGHTS = {
    "side_comparability_score": 0.30,
    "pattern_pair_score": 0.25,
    "blur_pair_score": 0.15,
    "occlusion_pair_score": 0.10,
    "body_visibility_pair_score": 0.10,
    "viewpoint_compatibility_score": 0.10,
}

PATTERN_SCORE = {"high": 1.0, "medium": 0.67, "low": 0.33, "none": 0.0, "not_available": 0.5, "unknown": 0.5}
SIDE_EVIDENCE_SCORE = {"high": 1.0, "medium": 0.67, "low": 0.33, "none": 0.0, "not_available": 0.5, "unknown": 0.5}
BLUR_SCORE = {"none": 1.0, "mild": 0.67, "moderate": 0.33, "severe": 0.0, "not_available": 0.5, "unknown": 0.5}
OCCLUSION_SCORE = {"none": 1.0, "partial": 0.5, "mild": 0.67, "moderate": 0.33, "major": 0.0, "severe": 0.0, "not_available": 0.5, "unknown": 0.5}
BODY_SCORE = {"76_100": 1.0, "51_75": 0.67, "26_50": 0.33, "0_25": 0.0, "not_available": 0.5, "unknown": 0.5}
SIDE_VALUES = {"left", "right"}

SENSITIVE_EXPORT_COLUMNS = {
    "query_idx",
    "gallery_idx",
    "expanded_image_id",
    "working_individual_id",
    "review_image_path",
    "review_image_path_local",
    "source_review_image_path_original",
    "path",
    "local_image_path",
    "source",
    "date",
    "encounter",
    "trap_id",
    "camera_id",
    "site",
    "latitude",
    "longitude",
    "cell_code",
}


def token(value: object, prefix: str) -> str:
    digest = hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def clamp01(value: float) -> float:
    if pd.isna(value):
        return 0.5
    return float(min(1.0, max(0.0, value)))


def score_map(value: object, mapping: dict[str, float], default: float = 0.5) -> float:
    key = str(value).strip().lower()
    return float(mapping.get(key, default))


def percentile_by_descriptor(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    return values.rank(method="average", pct=True).fillna(0.0).clip(0.0, 1.0)


def reliability_band(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.50:
        return "medium"
    if score >= 0.25:
        return "low"
    return "unusable"


def conflict_band(score: float) -> str:
    if score >= 0.75:
        return "high_conflict"
    if score >= 0.50:
        return "medium_conflict"
    if score >= 0.25:
        return "low_conflict"
    return "minimal_conflict"


def review_decision(reliability: float, conflict: float) -> str:
    if reliability < 0.25:
        return "exclude_unusable_evidence"
    if conflict >= 0.75:
        return "defer_high_descriptor_evidence_conflict"
    if reliability >= 0.50:
        return "review_candidate"
    return "defer_low_admissibility"


def add_image_pair_components(metadata: pd.DataFrame) -> pd.DataFrame:
    frame = metadata.copy()
    frame["pattern_score"] = frame["pattern_visibility"].map(lambda x: score_map(x, PATTERN_SCORE))
    frame["side_evidence_score"] = frame["side_evidence_quality"].map(lambda x: score_map(x, SIDE_EVIDENCE_SCORE))
    frame["blur_score"] = frame["blur_level"].map(lambda x: score_map(x, BLUR_SCORE))
    frame["occlusion_score"] = frame["occlusion_level"].map(lambda x: score_map(x, OCCLUSION_SCORE))
    frame["body_visibility_score"] = frame["body_fraction_visible"].map(lambda x: score_map(x, BODY_SCORE))
    return frame


def pair_side_comparability(query: pd.Series, gallery: pd.Series) -> float:
    side_a = str(query.get("side_visibility", "not_available")).strip().lower()
    side_b = str(gallery.get("side_visibility", "not_available")).strip().lower()
    evidence = min(clamp01(float(query["side_evidence_score"])), clamp01(float(gallery["side_evidence_score"])))
    if side_a in SIDE_VALUES and side_b in SIDE_VALUES:
        side_match = 1.0 if side_a == side_b else 0.25
    elif side_a == side_b and side_a not in {"not_available", "unknown", "nan", ""}:
        side_match = 0.50
    else:
        side_match = 0.40
    return clamp01(evidence * side_match)


def pair_viewpoint_compatibility(query: pd.Series, gallery: pd.Series) -> float:
    penalty = 0.0
    if str(query.get("frontal_or_rear_view", "no")).strip().lower() == "yes":
        penalty += 0.30
    if str(gallery.get("frontal_or_rear_view", "no")).strip().lower() == "yes":
        penalty += 0.30
    if str(query.get("silhouette_only", "no")).strip().lower() == "yes":
        penalty += 0.50
    if str(gallery.get("silhouette_only", "no")).strip().lower() == "yes":
        penalty += 0.50
    return clamp01(1.0 - penalty)


def weighted_pair_score(row: dict[str, float]) -> float:
    return clamp01(sum(PAIR_SCORE_WEIGHTS[key] * float(row[key]) for key in PAIR_SCORE_WEIGHTS))


def add_pair_reliability(candidates: pd.DataFrame, metadata: pd.DataFrame) -> pd.DataFrame:
    meta = add_image_pair_components(metadata)
    rows: list[dict[str, float]] = []
    for _, row in candidates.iterrows():
        query = meta.iloc[int(row["query_idx"])]
        gallery = meta.iloc[int(row["gallery_idx"])]
        record = {
            "side_comparability_score": pair_side_comparability(query, gallery),
            "pattern_pair_score": min(float(query["pattern_score"]), float(gallery["pattern_score"])),
            "blur_pair_score": min(float(query["blur_score"]), float(gallery["blur_score"])),
            "occlusion_pair_score": min(float(query["occlusion_score"]), float(gallery["occlusion_score"])),
            "body_visibility_pair_score": min(float(query["body_visibility_score"]), float(gallery["body_visibility_score"])),
            "viewpoint_compatibility_score": pair_viewpoint_compatibility(query, gallery),
        }
        record["pair_reliability_score"] = weighted_pair_score(record)
        record["image_quality_proxy_min"] = min(float(row["query_quality_score"]), float(row["gallery_quality_score"]))
        record["image_quality_proxy_mean"] = (float(row["query_quality_score"]) + float(row["gallery_quality_score"])) / 2.0
        record["image_utility_proxy_min"] = min(float(row["query_image_utility_score"]), float(row["gallery_image_utility_score"]))
        record["image_utility_proxy_mean"] = (float(row["query_image_utility_score"]) + float(row["gallery_image_utility_score"])) / 2.0
        record["visual_identity_evidence_min"] = min(float(row["query_visual_identity_evidence_score"]), float(row["gallery_visual_identity_evidence_score"]))
        record["visual_identity_evidence_mean"] = (
            float(row["query_visual_identity_evidence_score"]) + float(row["gallery_visual_identity_evidence_score"])
        ) / 2.0
        rows.append(record)
    return pd.concat([candidates.reset_index(drop=True), pd.DataFrame(rows)], axis=1)


def add_rank_and_conflict_fields(candidates: pd.DataFrame) -> pd.DataFrame:
    df = candidates.copy()
    df["descriptor_similarity"] = pd.to_numeric(df["base_descriptor_similarity"], errors="coerce")
    df["descriptor_similarity_percentile"] = df.groupby("descriptor")["descriptor_similarity"].transform(percentile_by_descriptor)
    df["descriptor_disagreement_score"] = df["descriptor_disagreement"].astype(float)
    df["reciprocal_rank_support"] = df["reciprocal_support"].astype(float)
    df["margin_confidence"] = pd.to_numeric(df["margin_confidence"], errors="coerce").fillna(0.0)
    df["margin_confidence_norm"] = df.groupby("descriptor")["margin_confidence"].transform(percentile_by_descriptor)
    df["descriptor_evidence_conflict_score"] = (
        df["descriptor_similarity_percentile"] * (1.0 - pd.to_numeric(df["pair_reliability_score"], errors="coerce"))
    ).clip(0.0, 1.0)
    df["descriptor_evidence_conflict_margin_score"] = (
        df["descriptor_similarity_percentile"] * df["margin_confidence_norm"] * (1.0 - df["pair_reliability_score"])
    ).clip(0.0, 1.0)
    df["descriptor_evidence_conflict_disagreement_score"] = (
        df["descriptor_similarity_percentile"] * df["descriptor_disagreement_score"] * (1.0 - df["pair_reliability_score"])
    ).clip(0.0, 1.0)
    df["conflict_band"] = df["descriptor_evidence_conflict_score"].map(conflict_band)
    df["admissibility_band"] = df["pair_reliability_score"].map(reliability_band)
    df["candidate_utility_rq_score"] = (
        0.45 * df["descriptor_similarity_percentile"]
        + 0.25 * df["pair_reliability_score"]
        + 0.10 * df["reciprocal_rank_support"]
        + 0.10 * df["margin_confidence_norm"]
        - 0.05 * df["descriptor_disagreement_score"]
        - 0.15 * df["descriptor_evidence_conflict_score"]
    ).clip(0.0, 1.0)
    df["candidate_rank_raw"] = pd.to_numeric(df["rank"], errors="coerce").astype(int)
    df["candidate_rank_pf_eri"] = (
        df.sort_values(["descriptor", "query_idx", "candidate_utility_rq_score", "descriptor_similarity"], ascending=[True, True, False, False])
        .groupby(["descriptor", "query_idx"], sort=False)
        .cumcount()
        + 1
    )
    df["is_top1_raw"] = df["candidate_rank_raw"] == 1
    df["is_top1_pf_eri"] = df["candidate_rank_pf_eri"] == 1
    df["same_identity"] = df["same_identity_truth_internal"].astype(bool)
    df["false_candidate"] = ~df["same_identity"]
    df["false_top1_raw"] = df["is_top1_raw"] & df["false_candidate"]
    df["false_top1_pf_eri"] = df["is_top1_pf_eri"] & df["false_candidate"]
    df["hard_negative_candidate"] = (
        df["false_candidate"]
        & (df["descriptor_similarity_percentile"] >= 0.90)
        & (df["pair_reliability_score"] <= 0.40)
    )
    df["review_decision"] = [
        review_decision(float(r), float(c))
        for r, c in zip(df["pair_reliability_score"], df["descriptor_evidence_conflict_score"])
    ]
    return df


def public_table(candidates: pd.DataFrame, metadata: pd.DataFrame, split_design: pd.DataFrame) -> pd.DataFrame:
    df = add_rank_and_conflict_fields(candidates)
    df["query_image_id"] = df["query_token"]
    df["candidate_image_id"] = df["gallery_token"]
    identity_tokens = metadata["working_individual_id"].map(lambda x: token(x, "id")).to_dict()
    df["query_identity_token"] = df["query_idx"].map(identity_tokens)
    df["candidate_identity_token"] = df["gallery_idx"].map(identity_tokens)
    df["detection_assisted_fields_available"] = "no"
    df["object_detection_source"] = "not_run_phase12a_placeholder"
    df["detection_box_quality_proxy"] = np.nan
    df["domain_shift_proxy_available"] = "no"
    df["domain_diagnostic_note"] = "future_detection_or_domain_shift_extension_not_used_in_phase12a_scores"

    keep = [
        "split_id",
        "calibration_or_evaluation",
        "descriptor",
        "query_image_id",
        "candidate_image_id",
        "query_identity_token",
        "candidate_identity_token",
        "same_identity",
        "candidate_rank_raw",
        "candidate_rank_pf_eri",
        "is_top1_raw",
        "is_top1_pf_eri",
        "false_candidate",
        "false_top1_raw",
        "false_top1_pf_eri",
        "descriptor_similarity",
        "descriptor_similarity_percentile",
        "other_descriptor_similarity",
        "reciprocal_rank_support",
        "margin_confidence",
        "margin_confidence_norm",
        "descriptor_disagreement_score",
        "side_comparability_score",
        "pattern_pair_score",
        "blur_pair_score",
        "occlusion_pair_score",
        "body_visibility_pair_score",
        "viewpoint_compatibility_score",
        "pair_reliability_score",
        "image_quality_proxy_min",
        "image_quality_proxy_mean",
        "image_utility_proxy_min",
        "image_utility_proxy_mean",
        "visual_identity_evidence_min",
        "visual_identity_evidence_mean",
        "descriptor_evidence_conflict_score",
        "descriptor_evidence_conflict_margin_score",
        "descriptor_evidence_conflict_disagreement_score",
        "conflict_band",
        "admissibility_band",
        "candidate_utility_rq_score",
        "hard_negative_candidate",
        "review_decision",
        "detection_assisted_fields_available",
        "object_detection_source",
        "detection_box_quality_proxy",
        "domain_shift_proxy_available",
        "domain_diagnostic_note",
    ]

    rows: list[pd.DataFrame] = []
    compact = df.copy()
    for _, split_row in split_design.iterrows():
        roles = split_roles(metadata, split_row)
        role_map = roles.to_dict()
        part = compact.copy()
        part["split_id"] = int(split_row["split_id"])
        part["calibration_or_evaluation"] = part["query_idx"].map(role_map)
        rows.append(part[keep])
    out = pd.concat(rows, ignore_index=True)
    for column in ["same_identity", "is_top1_raw", "is_top1_pf_eri", "false_candidate", "false_top1_raw", "false_top1_pf_eri", "hard_negative_candidate"]:
        out[column] = out[column].map(lambda x: "yes" if bool(x) else "no")
    return out


def write_summary(table: pd.DataFrame) -> None:
    rows: list[dict[str, Any]] = []
    grouped = table.groupby(["split_id", "calibration_or_evaluation", "descriptor"], dropna=False)
    for keys, frame in grouped:
        split_id, role, descriptor = keys
        false_candidate = frame["false_candidate"].eq("yes")
        same_identity = frame["same_identity"].eq("yes")
        rows.append(
            {
                "split_id": split_id,
                "calibration_or_evaluation": role,
                "descriptor": descriptor,
                "candidate_count": int(len(frame)),
                "query_count": int(frame["query_image_id"].nunique()),
                "same_identity_candidate_count": int(same_identity.sum()),
                "false_candidate_count": int(false_candidate.sum()),
                "false_candidate_rate": float(false_candidate.mean()) if len(frame) else math.nan,
                "false_top1_raw_count": int(frame["false_top1_raw"].eq("yes").sum()),
                "false_top1_pf_eri_count": int(frame["false_top1_pf_eri"].eq("yes").sum()),
                "mean_pair_reliability_score": float(pd.to_numeric(frame["pair_reliability_score"], errors="coerce").mean()),
                "mean_conflict_score": float(pd.to_numeric(frame["descriptor_evidence_conflict_score"], errors="coerce").mean()),
                "high_conflict_count": int(frame["conflict_band"].eq("high_conflict").sum()),
                "hard_negative_candidate_count": int(frame["hard_negative_candidate"].eq("yes").sum()),
            }
        )
    pd.DataFrame(rows).to_csv(OUT_SUMMARY, index=False)


def _safe_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def _annotation_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    frame = pd.read_csv(path, usecols=["expanded_image_id"])
    return set(frame["expanded_image_id"].astype(str))


def annotation_lineage_audit(annotation_csv: Path, metadata: pd.DataFrame) -> dict[str, Any]:
    active = pd.read_csv(annotation_csv)
    if "expanded_image_id" not in active.columns:
        raise ValueError(f"{annotation_csv} must contain expanded_image_id")

    active_ids = set(active["expanded_image_id"].astype(str))
    metadata_ids = set(metadata["expanded_image_id"].astype(str))
    phase4_ids = _annotation_ids(PHASE4_500_ANNOTATION_CSV)
    phase6_ids = _annotation_ids(PHASE6_V2_500_ANNOTATION_CSV)
    phase7_ids = _annotation_ids(PHASE7A_1000_ANNOTATION_CSV)

    audit: dict[str, Any] = {
        "active_annotation_csv": _safe_relative(annotation_csv),
        "active_annotation_row_count": int(len(active)),
        "active_annotation_unique_ids": int(len(active_ids)),
        "metadata_unique_ids_after_embedding_alignment": int(len(metadata_ids)),
        "expected_phase4_500_csv": _safe_relative(PHASE4_500_ANNOTATION_CSV),
        "expected_phase6_v2_500_csv": _safe_relative(PHASE6_V2_500_ANNOTATION_CSV),
        "expected_phase7a_1000_merged_csv": _safe_relative(PHASE7A_1000_ANNOTATION_CSV),
        "phase4_500_unique_ids": int(len(phase4_ids)),
        "phase6_v2_500_unique_ids": int(len(phase6_ids)),
        "phase7a_1000_unique_ids": int(len(phase7_ids)),
        "phase4_phase6_overlap_ids": int(len(phase4_ids & phase6_ids)),
        "active_overlap_phase4_500_ids": int(len(active_ids & phase4_ids)),
        "active_overlap_phase6_v2_500_ids": int(len(active_ids & phase6_ids)),
        "active_overlap_phase7a_1000_ids": int(len(active_ids & phase7_ids)),
        "metadata_overlap_phase4_500_ids": int(len(metadata_ids & phase4_ids)),
        "metadata_overlap_phase6_v2_500_ids": int(len(metadata_ids & phase6_ids)),
        "metadata_overlap_phase7a_1000_ids": int(len(metadata_ids & phase7_ids)),
    }
    if "source_phase" in active.columns:
        audit["active_source_phase_counts"] = {
            str(key): int(value)
            for key, value in active["source_phase"].astype(str).value_counts(dropna=False).sort_index().items()
        }
    if "annotation_status" in active.columns:
        audit["active_annotation_status_counts"] = {
            str(key): int(value)
            for key, value in active["annotation_status"].astype(str).value_counts(dropna=False).sort_index().items()
        }
    audit["active_source_covers_both_500_halves"] = bool(
        len(active_ids & phase4_ids) == len(phase4_ids) == 500
        and len(active_ids & phase6_ids) == len(phase6_ids) == 500
        and len(phase4_ids & phase6_ids) == 0
    )
    audit["aligned_metadata_uses_both_500_halves"] = bool((metadata_ids & phase4_ids) and (metadata_ids & phase6_ids))
    return audit


def build(args: argparse.Namespace) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    metadata, similarities = align_inputs(args)
    metadata = add_image_utility_components(metadata)
    candidates = build_candidates(metadata, similarities, MAX_K)
    candidates = add_pair_reliability(candidates, metadata)
    split_design = load_split_design(SPLIT_DESIGN_CSV)
    table = public_table(candidates, metadata, split_design)
    table.to_csv(OUT_TABLE, index=False)
    write_summary(table)
    audit = {
        "output_table": str(OUT_TABLE.relative_to(PROJECT_ROOT)),
        "output_summary": str(OUT_SUMMARY.relative_to(PROJECT_ROOT)),
        "row_count": int(len(table)),
        "column_count": int(len(table.columns)),
        "split_count": int(table["split_id"].nunique()),
        "descriptor_values": sorted(table["descriptor"].astype(str).unique()),
        "max_k": int(MAX_K),
        "annotation_lineage": annotation_lineage_audit(args.annotation_csv, metadata),
        "detection_extension_status": "placeholder_only_not_used_in_scores",
        "domain_shift_extension_status": "placeholder_only_not_used_in_scores",
        "sensitive_columns_excluded": sorted(SENSITIVE_EXPORT_COLUMNS),
    }
    OUT_AUDIT_JSON.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_TABLE.relative_to(PROJECT_ROOT)} rows={len(table)}")
    print(f"Wrote {OUT_SUMMARY.relative_to(PROJECT_ROOT)}")
    print(f"Wrote {OUT_AUDIT_JSON.relative_to(PROJECT_ROOT)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--megadescriptor-embeddings-csv", type=Path, default=MEGA_EMBEDDINGS_CSV)
    parser.add_argument("--resnet50-embeddings-csv", type=Path, default=RESNET_EMBEDDINGS_CSV)
    parser.add_argument("--identity-csv", type=Path, default=IDENTITY_CSV)
    parser.add_argument("--annotation-csv", type=Path, default=ANNOTATION_CSV)
    return parser.parse_args()


if __name__ == "__main__":
    build(parse_args())
