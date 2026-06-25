#!/usr/bin/env python3
"""Run Phase 9B no-training PF-ERI-aware fixed-descriptor reranking."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd

from phase8_pf_eri_retrieval_control_v2_optimizer import (
    ANNOTATION_CSV,
    IDENTITY_CSV,
    MEGA_EMBEDDINGS_CSV,
    RESNET_EMBEDDINGS_CSV,
    align_inputs,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase9/pf_eri_fixed_descriptor_reranking"
QC_DIR = PROJECT_ROOT / "outputs/czechlynx/qc"
DOC_PATH = PROJECT_ROOT / "docs/phase9/phase9b_pf_eri_aware_fixed_descriptor_reranking_results.md"

INPUT_INVENTORY_CSV = OUTPUT_DIR / "phase9b_input_inventory.csv"
CANDIDATE_TABLE_CSV = OUTPUT_DIR / "phase9b_candidate_level_reranking_table.csv"
METHOD_SUMMARY_CSV = OUTPUT_DIR / "phase9b_method_metric_summary.csv"
HELDOUT_SPLIT_CSV = OUTPUT_DIR / "phase9b_heldout_split_metric_summary.csv"
RANDOM_SIZE_CSV = OUTPUT_DIR / "phase9b_random_same_size_controls.csv"
RANDOM_COVERAGE_CSV = OUTPUT_DIR / "phase9b_random_same_coverage_controls.csv"
ABLATION_CSV = OUTPUT_DIR / "phase9b_feature_ablation_summary.csv"
RISK_COVERAGE_CSV = OUTPUT_DIR / "phase9b_risk_coverage_curve.csv"
PARETO_CSV = OUTPUT_DIR / "phase9b_pareto_summary.csv"
FINAL_RECOMMENDATION_CSV = OUTPUT_DIR / "phase9b_final_recommendation.csv"

INPUTS_TO_INSPECT = [
    PROJECT_ROOT / "PROJECT_RULES.md",
    PROJECT_ROOT / "docs/phase9/phase9a_pf_eri_evidence_utility_model_direction_revision.md",
    PROJECT_ROOT / "docs/phase8/phase8_post_3e_r_interpretation_and_claim_revision.md",
    PROJECT_ROOT / "docs/phase8/phase8_slice3f_downstream_ecological_sensitivity_simulation_results.md",
    PROJECT_ROOT / "outputs/czechlynx/phase8/pf_eri_retrieval_control_v2/phase8_pf_eri_retrieval_control_v2_recommended_assignments.csv",
    PROJECT_ROOT / "outputs/czechlynx/phase8/pf_eri_deep_algorithm_v4/phase8_pf_eri_v4_recommended_assignments.csv",
    PROJECT_ROOT / "outputs/czechlynx/phase8/pf_eri_deep_algorithm_v4/phase8_pf_eri_v4_policy_grid.csv",
    PROJECT_ROOT / "outputs/czechlynx/phase8/reid_accuracy_query_calibration/phase8_slice3e_query_evaluation_policy_comparison.csv",
    PROJECT_ROOT / "outputs/czechlynx/phase8/reid_accuracy_query_calibration/phase8_slice3e_query_split_design.csv",
    PROJECT_ROOT / "outputs/czechlynx/phase8/reid_accuracy_evidence_selection/phase8_slice3e_policy_comparison.csv",
    PROJECT_ROOT / "data/labels/czechlynx/czechlynx_phase7a_1000_image_annotations_v1.csv",
    PROJECT_ROOT / "data/labels/czechlynx/czechlynx_mechanism_visual_factors_full_annotated.csv",
    PROJECT_ROOT / "outputs/czechlynx/phase5/czechlynx_phase5_pair_eri_scores_internal.csv",
    PROJECT_ROOT / "outputs/czechlynx/phase4/czechlynx_phase4c_pair_level_mechanism_similarity_table.csv",
    MEGA_EMBEDDINGS_CSV,
    RESNET_EMBEDDINGS_CSV,
    IDENTITY_CSV,
    ANNOTATION_CSV,
]

SPLIT_DESIGN_CSV = PROJECT_ROOT / "outputs/czechlynx/phase8/reid_accuracy_query_calibration/phase8_slice3e_query_split_design.csv"

RANDOM_SEED = 20260615
MAX_K = 20
REPORT_K = 5
REQUIRED_METHODS = [
    "raw_megadescriptor_ranking",
    "raw_resnet50_ranking",
    "simple_pf_eri_hard_filtering",
    "quality_only_reranking",
    "image_utility_reranking",
    "pair_utility_reranking",
    "candidate_utility_reranking",
    "candidate_utility_plus_descriptor_reranking",
]

SENSITIVE_COLUMNS = {
    "query_idx",
    "gallery_idx",
    "query_identity_internal",
    "gallery_identity_internal",
    "working_individual_id",
    "expanded_image_id",
    "review_image_path",
    "review_image_path_local",
    "source_review_image_path_original",
    "path",
    "local_image_path",
    "latitude",
    "longitude",
    "cell_code",
    "trap_id",
    "camera_id",
    "site",
    "unique_name",
}


def minmax(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce").astype(float)
    lo = float(values.min(skipna=True))
    hi = float(values.max(skipna=True))
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        return pd.Series(np.zeros(len(values)), index=series.index, dtype=float)
    return (values - lo) / (hi - lo)


def input_inventory(paths: list[Path]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for path in paths:
        row: dict[str, object] = {
            "input_file": str(path.relative_to(PROJECT_ROOT)) if path.is_absolute() else str(path),
            "exists": "yes" if path.exists() else "no",
            "row_count": 0,
            "column_count": 0,
            "columns": "",
            "status": "missing",
        }
        if path.exists():
            if path.suffix.lower() == ".csv":
                df = pd.read_csv(path)
                row["row_count"] = int(len(df))
                row["column_count"] = int(len(df.columns))
                row["columns"] = ";".join(df.columns)
                row["status"] = "available_nonempty" if len(df) else "available_empty"
            else:
                row["status"] = "available_document"
        rows.append(row)
    return pd.DataFrame(rows)


def add_image_utility_components(metadata: pd.DataFrame) -> pd.DataFrame:
    df = metadata.copy()
    pattern = df["pattern_visibility"].map({"none": 0.0, "low": 1.0, "medium": 2.0, "high": 3.0}).fillna(1.0) / 3.0
    side = df["side_evidence_quality"].map({"none": 0.0, "low": 1.0, "medium": 2.0, "high": 3.0}).fillna(1.0) / 3.0
    body = df["body_fraction_visible"].map({"0_25": 0.0, "26_50": 1.0, "51_75": 2.0, "76_100": 3.0, "unknown": 1.0}).fillna(1.0) / 3.0
    blur = df["blur_level"].map({"severe": 0.0, "moderate": 1.0, "mild": 2.0, "none": 3.0, "unknown": 1.0}).fillna(1.0) / 3.0
    occlusion = df["occlusion_level"].map({"major": 0.0, "partial": 1.5, "none": 3.0, "unknown": 1.5}).fillna(1.5) / 3.0
    contrast = df["contrast_level"].map({"low": 0.0, "not_available": 1.0, "good": 2.0, "unknown": 1.0}).fillna(1.0) / 2.0
    uncertainty = (df["uncertainty_flag"] == "yes").astype(float)
    night_ir = (df["night_ir_artifact"] == "yes").astype(float)
    partial = (df["partial_body"] == "yes").astype(float)
    frontal = (df["frontal_or_rear_view"] == "yes").astype(float)
    silhouette = (df["silhouette_only"] == "yes").astype(float)

    df["visual_identity_evidence_score"] = (0.60 * pattern + 0.40 * side).clip(0, 1)
    df["generic_quality_score"] = (
        0.30 * blur
        + 0.25 * occlusion
        + 0.20 * body
        + 0.10 * contrast
        - 0.05 * uncertainty
        - 0.04 * night_ir
        - 0.04 * partial
        - 0.05 * frontal
        - 0.07 * silhouette
    ).clip(0, 1)
    df["image_utility_score"] = (pd.to_numeric(df["visual_pf_eri_score"], errors="coerce").fillna(0.0) / 100.0).clip(0, 1)
    return df


def descriptor_rank_matrix(similarity: np.ndarray) -> np.ndarray:
    n = similarity.shape[0]
    ranks = np.zeros((n, n), dtype=np.int32)
    for i in range(n):
        scores = similarity[i].copy()
        scores[i] = -np.inf
        order = np.argsort(-scores)
        ranks[i, order] = np.arange(1, n + 1)
    return ranks


def build_candidates(metadata: pd.DataFrame, similarities: dict[str, np.ndarray], max_k: int) -> pd.DataFrame:
    identities = metadata["working_individual_id"].astype(str).to_numpy()
    rank_mats = {name: descriptor_rank_matrix(sim) for name, sim in similarities.items()}
    rows: list[dict[str, object]] = []
    n = len(metadata)
    for descriptor, sim in similarities.items():
        other = "resnet50" if descriptor == "megadescriptor" else "megadescriptor"
        other_sim = similarities[other]
        other_rank = rank_mats[other]
        own_rank = rank_mats[descriptor]
        for query_idx, query in metadata.iterrows():
            q = int(query_idx)
            scores = sim[q].copy()
            scores[q] = -np.inf
            order = np.argsort(-scores)
            top_order = order[:max_k]
            top_scores = scores[top_order]
            top1_gap = float(top_scores[0] - top_scores[1]) if len(top_scores) > 1 else 0.0
            for pos, gallery_idx in enumerate(top_order, start=1):
                g = int(gallery_idx)
                gallery = metadata.iloc[g]
                next_gap = float(top_scores[pos - 1] - top_scores[pos]) if pos < len(top_scores) else 0.0
                reciprocal_rank = int(own_rank[g, q])
                other_reciprocal_rank = int(other_rank[g, q])
                reciprocal_support = reciprocal_rank <= 10 and other_reciprocal_rank <= 20
                rank_gap = int(other_rank[q, g]) - pos
                descriptor_disagreement = rank_gap >= 10 or abs(float(sim[q, g]) - float(other_sim[q, g])) >= 0.18
                query_image_utility = float(query["image_utility_score"])
                gallery_image_utility = float(gallery["image_utility_score"])
                query_quality = float(query["generic_quality_score"])
                gallery_quality = float(gallery["generic_quality_score"])
                query_identity_evidence = float(query["visual_identity_evidence_score"])
                gallery_identity_evidence = float(gallery["visual_identity_evidence_score"])
                severe_visual_failure = bool(query["severe_visual_failure"]) or bool(gallery["severe_visual_failure"])
                weak_side = bool(query["weak_side_evidence"]) or bool(gallery["weak_side_evidence"])
                visual_failure_penalty = min(
                    1.0,
                    0.35 * float(severe_visual_failure)
                    + 0.15 * float(weak_side)
                    + 0.15 * float(query["uncertainty_flag"] == "yes" or gallery["uncertainty_flag"] == "yes")
                    + 0.10 * float(query["low_body_fraction"] or gallery["low_body_fraction"])
                    + 0.10 * float(query["night_ir_artifact"] == "yes" or gallery["night_ir_artifact"] == "yes"),
                )
                pair_utility = max(
                    0.0,
                    min(
                        1.0,
                        0.52 * min(query_image_utility, gallery_image_utility)
                        + 0.18 * ((float(sim[q, g]) + 1.0) / 2.0)
                        + 0.10 * float(reciprocal_support)
                        + 0.10 * min(1.0, max(0.0, top1_gap if pos == 1 else next_gap) / 0.10)
                        - 0.10 * float(descriptor_disagreement)
                        - 0.10 * visual_failure_penalty,
                    ),
                )
                candidate_utility = max(
                    0.0,
                    min(
                        1.0,
                        0.30 * query_image_utility
                        + 0.25 * gallery_image_utility
                        + 0.20 * pair_utility
                        + 0.10 * float(reciprocal_support)
                        + 0.10 * min(1.0, max(0.0, top1_gap if pos == 1 else next_gap) / 0.10)
                        - 0.10 * float(descriptor_disagreement)
                        - 0.10 * visual_failure_penalty,
                    ),
                )
                rows.append(
                    {
                        "descriptor": descriptor,
                        "query_idx": q,
                        "gallery_idx": g,
                        "query_token": query["image_token"],
                        "gallery_token": gallery["image_token"],
                        "rank": pos,
                        "base_descriptor_similarity": float(sim[q, g]),
                        "other_descriptor_similarity": float(other_sim[q, g]),
                        "other_descriptor_rank": int(other_rank[q, g]),
                        "reciprocal_rank": reciprocal_rank,
                        "other_descriptor_reciprocal_rank": other_reciprocal_rank,
                        "same_identity_truth_internal": bool(identities[q] == identities[g]),
                        "query_image_utility_score": query_image_utility,
                        "gallery_image_utility_score": gallery_image_utility,
                        "query_quality_score": query_quality,
                        "gallery_quality_score": gallery_quality,
                        "query_visual_identity_evidence_score": query_identity_evidence,
                        "gallery_visual_identity_evidence_score": gallery_identity_evidence,
                        "pair_utility_score": pair_utility,
                        "candidate_utility_score": candidate_utility,
                        "reciprocal_support": bool(reciprocal_support),
                        "margin_confidence": float(max(0.0, top1_gap if pos == 1 else next_gap)),
                        "descriptor_disagreement": bool(descriptor_disagreement),
                        "visual_failure_penalty": visual_failure_penalty,
                        "severe_visual_failure": severe_visual_failure,
                        "source_table": "fixed_embedding_top20_candidate_pool",
                    }
                )
    df = pd.DataFrame(rows)
    df["descriptor_similarity_norm"] = df.groupby("descriptor")["base_descriptor_similarity"].transform(minmax)
    df["margin_confidence_norm"] = df.groupby("descriptor")["margin_confidence"].transform(minmax)
    return df


def load_split_design(path: Path) -> pd.DataFrame:
    if path.exists():
        return pd.read_csv(path)
    rows = []
    for split_id in range(1, 21):
        rows.append(
            {
                "split_id": split_id,
                "split_design": "identity_aware_query_split_reconstructed",
                "calibration_query_count": 0,
                "evaluation_query_count": 0,
                "calibration_identity_count": 0,
                "evaluation_identity_count": 0,
                "random_seed": 8300 + split_id,
                "calibration_fraction": 0.5,
            }
        )
    return pd.DataFrame(rows)


def split_roles(metadata: pd.DataFrame, split_row: pd.Series) -> pd.Series:
    seed = int(split_row["random_seed"])
    frac = float(split_row["calibration_fraction"])
    identities = metadata["working_individual_id"].drop_duplicates().sample(frac=1.0, random_state=seed).to_numpy()
    cal_count = int(round(len(identities) * frac))
    calibration_ids = set(identities[:cal_count])
    return metadata["working_individual_id"].map(lambda x: "calibration" if x in calibration_ids else "evaluation")


def method_variants() -> list[dict[str, object]]:
    variants: list[dict[str, object]] = []
    for descriptor in ["megadescriptor", "resnet50"]:
        variants.append({"method_id": f"raw_{descriptor}_ranking", "method_family": "raw_descriptor_ranking", "descriptor": descriptor, "weight": 0.0, "threshold": math.nan})
    for thr in [0.25, 0.50, 0.75]:
        variants.append({"method_id": "simple_pf_eri_hard_filtering", "method_family": "simple_pf_eri_hard_filtering", "descriptor": "megadescriptor", "weight": 0.0, "threshold": thr})
    for method_id in ["quality_only_reranking", "image_utility_reranking", "pair_utility_reranking", "candidate_utility_reranking", "candidate_utility_plus_descriptor_reranking"]:
        for weight in [0.10, 0.25, 0.50, 0.75]:
            variants.append({"method_id": method_id, "method_family": method_id, "descriptor": "megadescriptor", "weight": weight, "threshold": math.nan})
    for method_id in [
        "descriptor_only",
        "visual_quality_only",
        "visual_identity_evidence_only",
        "descriptor_confidence_only",
        "reciprocal_margin_only",
        "descriptor_disagreement_only",
        "image_utility_only",
        "pair_utility_only",
        "full_pf_eri_candidate_utility",
        "full_minus_visual",
        "full_minus_descriptor_disagreement",
        "full_minus_reciprocal_margin",
    ]:
        variants.append({"method_id": method_id, "method_family": "feature_ablation", "descriptor": "megadescriptor", "weight": 0.50, "threshold": math.nan})
    return variants


def score_candidates(pool: pd.DataFrame, variant: dict[str, object]) -> tuple[pd.DataFrame, str]:
    df = pool[pool["descriptor"] == variant["descriptor"]].copy()
    method = str(variant["method_id"])
    w = float(variant["weight"]) if np.isfinite(float(variant["weight"])) else 0.0
    descriptor = df["descriptor_similarity_norm"]
    image_mean = (df["query_image_utility_score"] + df["gallery_image_utility_score"]) / 2.0
    quality_mean = (df["query_quality_score"] + df["gallery_quality_score"]) / 2.0
    identity_mean = (df["query_visual_identity_evidence_score"] + df["gallery_visual_identity_evidence_score"]) / 2.0
    reciprocal_margin = (df["reciprocal_support"].astype(float) + df["margin_confidence_norm"]) / 2.0
    disagreement_good = 1.0 - df["descriptor_disagreement"].astype(float)
    descriptor_confidence = 0.60 * descriptor + 0.25 * reciprocal_margin + 0.15 * disagreement_good

    if method.startswith("raw_"):
        df["rerank_score"] = descriptor
        df["retained"] = df["rank"] <= REPORT_K
        score_source = "descriptor_similarity_only"
    elif method == "simple_pf_eri_hard_filtering":
        threshold = float(variant["threshold"])
        df["rerank_score"] = descriptor
        df["retained"] = (
            (df["query_image_utility_score"] >= threshold)
            & (df["gallery_image_utility_score"] >= threshold)
            & (df["pair_utility_score"] >= threshold)
            & ~df["severe_visual_failure"].astype(bool)
        )
        score_source = f"pf_eri_hard_filter_threshold_{threshold:.2f}"
    elif method == "quality_only_reranking":
        df["rerank_score"] = (1.0 - w) * descriptor + w * quality_mean - 0.15 * df["visual_failure_penalty"]
        df["retained"] = df["rank"] <= MAX_K
        score_source = "descriptor_plus_generic_quality"
    elif method == "image_utility_reranking":
        df["rerank_score"] = (1.0 - w) * descriptor + w * image_mean
        df["retained"] = df["rank"] <= MAX_K
        score_source = "descriptor_plus_image_utility"
    elif method == "pair_utility_reranking":
        df["rerank_score"] = (1.0 - w) * descriptor + w * df["pair_utility_score"]
        df["retained"] = df["rank"] <= MAX_K
        score_source = "descriptor_plus_pair_utility"
    elif method == "candidate_utility_reranking":
        df["rerank_score"] = df["candidate_utility_score"]
        df["retained"] = df["rank"] <= MAX_K
        score_source = "candidate_utility_only"
    elif method == "candidate_utility_plus_descriptor_reranking":
        df["rerank_score"] = (1.0 - w) * descriptor + w * df["candidate_utility_score"]
        df["retained"] = df["rank"] <= MAX_K
        score_source = "descriptor_plus_candidate_utility"
    elif method == "descriptor_only":
        df["rerank_score"] = descriptor
        df["retained"] = df["rank"] <= MAX_K
        score_source = "ablation_descriptor_only"
    elif method == "visual_quality_only":
        df["rerank_score"] = quality_mean - 0.15 * df["visual_failure_penalty"]
        df["retained"] = df["rank"] <= MAX_K
        score_source = "ablation_visual_quality_only"
    elif method == "visual_identity_evidence_only":
        df["rerank_score"] = identity_mean
        df["retained"] = df["rank"] <= MAX_K
        score_source = "ablation_visual_identity_evidence_only"
    elif method == "descriptor_confidence_only":
        df["rerank_score"] = descriptor_confidence
        df["retained"] = df["rank"] <= MAX_K
        score_source = "ablation_descriptor_confidence_only"
    elif method == "reciprocal_margin_only":
        df["rerank_score"] = reciprocal_margin
        df["retained"] = df["rank"] <= MAX_K
        score_source = "ablation_reciprocal_margin_only"
    elif method == "descriptor_disagreement_only":
        df["rerank_score"] = disagreement_good
        df["retained"] = df["rank"] <= MAX_K
        score_source = "ablation_descriptor_disagreement_only"
    elif method == "image_utility_only":
        df["rerank_score"] = image_mean
        df["retained"] = df["rank"] <= MAX_K
        score_source = "ablation_image_utility_only"
    elif method == "pair_utility_only":
        df["rerank_score"] = df["pair_utility_score"]
        df["retained"] = df["rank"] <= MAX_K
        score_source = "ablation_pair_utility_only"
    elif method == "full_pf_eri_candidate_utility":
        df["rerank_score"] = 0.40 * descriptor + 0.35 * df["candidate_utility_score"] + 0.15 * reciprocal_margin + 0.10 * disagreement_good
        df["retained"] = df["rank"] <= MAX_K
        score_source = "ablation_full_pf_eri_candidate_utility"
    elif method == "full_minus_visual":
        df["rerank_score"] = 0.70 * descriptor + 0.20 * reciprocal_margin + 0.10 * disagreement_good
        df["retained"] = df["rank"] <= MAX_K
        score_source = "ablation_full_minus_visual"
    elif method == "full_minus_descriptor_disagreement":
        df["rerank_score"] = 0.45 * descriptor + 0.40 * df["candidate_utility_score"] + 0.15 * reciprocal_margin
        df["retained"] = df["rank"] <= MAX_K
        score_source = "ablation_full_minus_descriptor_disagreement"
    elif method == "full_minus_reciprocal_margin":
        df["rerank_score"] = 0.55 * descriptor + 0.35 * df["candidate_utility_score"] + 0.10 * disagreement_good
        df["retained"] = df["rank"] <= MAX_K
        score_source = "ablation_full_minus_reciprocal_margin"
    else:
        raise ValueError(f"unknown method: {method}")
    df["rerank_score"] = pd.to_numeric(df["rerank_score"], errors="coerce").fillna(-np.inf)
    return df, score_source


def retained_for_method(pool: pd.DataFrame, variant: dict[str, object], query_indices: set[int]) -> pd.DataFrame:
    scored, score_source = score_candidates(pool, variant)
    scored = scored[scored["query_idx"].isin(query_indices)].copy()
    retained_rows: list[pd.DataFrame] = []
    for _, group in scored.groupby("query_idx", sort=False):
        group = group[group["retained"]].sort_values(["rerank_score", "base_descriptor_similarity"], ascending=[False, False]).head(REPORT_K).copy()
        if not group.empty:
            group["reranked_rank"] = np.arange(1, len(group) + 1)
            retained_rows.append(group)
    if not retained_rows:
        cols = list(scored.columns) + ["reranked_rank", "score_source"]
        return pd.DataFrame(columns=cols)
    out = pd.concat(retained_rows, ignore_index=True)
    out["score_source"] = score_source
    return out


def compute_metrics(retained: pd.DataFrame, pool: pd.DataFrame, query_indices: set[int], method_id: str, method_family: str, descriptor: str) -> dict[str, object]:
    queries = sorted(query_indices)
    full = pool[(pool["descriptor"] == descriptor) & (pool["query_idx"].isin(query_indices))]
    true_total = int(full["same_identity_truth_internal"].sum())
    positive_queries = set(full.loc[full["same_identity_truth_internal"], "query_idx"].astype(int))
    covered_queries = set(retained["query_idx"].astype(int)) if not retained.empty else set()
    retained_true = int(retained["same_identity_truth_internal"].sum()) if not retained.empty else 0
    retained_false = int((~retained["same_identity_truth_internal"]).sum()) if not retained.empty else 0
    ap_values: list[float] = []
    rr_values: list[float] = []
    top1_values: list[int] = []
    top5_values: list[int] = []
    false_top1 = 0
    retained_groups = {
        int(query_idx): group.sort_values("reranked_rank")
        for query_idx, group in retained.groupby("query_idx", sort=False)
    } if not retained.empty else {}
    for q in queries:
        group = retained_groups.get(int(q))
        if q in positive_queries:
            if group is None or group.empty:
                ap_values.append(0.0)
                rr_values.append(0.0)
                top1_values.append(0)
                top5_values.append(0)
            else:
                rel = group["same_identity_truth_internal"].astype(int).to_numpy()
                ap_values.append(average_precision(rel))
                positive_positions = np.flatnonzero(rel == 1)
                rr_values.append(1.0 / (int(positive_positions[0]) + 1) if len(positive_positions) else 0.0)
                top1_values.append(int(rel[0] == 1))
                top5_values.append(int(rel[: min(REPORT_K, len(rel))].max() == 1))
        if group is not None and not group.empty:
            false_top1 += int(not bool(group.iloc[0]["same_identity_truth_internal"]))
    reviewed_candidates = int(len(retained))
    return {
        "method_id": method_id,
        "method_family": method_family,
        "descriptor": descriptor,
        "query_count": int(len(queries)),
        "positive_query_count": int(len(positive_queries)),
        "candidate_pool_count": int(len(full)),
        "retained_candidate_count": reviewed_candidates,
        "query_coverage": len(covered_queries) / max(len(queries), 1),
        "positive_retention": retained_true / max(true_total, 1),
        "candidate_retention": reviewed_candidates / max(len(full), 1),
        "top1_accuracy": float(np.mean(top1_values)) if top1_values else math.nan,
        "top5_accuracy": float(np.mean(top5_values)) if top5_values else math.nan,
        "mAP": float(np.mean(ap_values)) if ap_values else math.nan,
        "MRR": float(np.mean(rr_values)) if rr_values else math.nan,
        "false_top1_rate": false_top1 / max(len(covered_queries), 1) if covered_queries else math.nan,
        "false_candidate_burden": retained_false / max(len(queries), 1),
        "reviewed_candidates_per_query": reviewed_candidates / max(len(queries), 1),
        "coverage_adjusted_mAP": (float(np.mean(ap_values)) if ap_values else 0.0) * (len(covered_queries) / max(len(queries), 1)),
    }


def average_precision(relevance: np.ndarray) -> float:
    positives = int(relevance.sum())
    if positives == 0:
        return 0.0
    cumulative = np.cumsum(relevance)
    return float((cumulative[relevance == 1] / (np.flatnonzero(relevance == 1) + 1)).mean())


def calibration_score(metrics: dict[str, object]) -> float:
    def numeric(name: str) -> float:
        try:
            value = float(metrics.get(name, 0.0))
        except (TypeError, ValueError):
            return 0.0
        return value if math.isfinite(value) else 0.0

    return (
        2.0 * numeric("mAP")
        + 1.0 * numeric("MRR")
        + 0.8 * numeric("top5_accuracy")
        + 0.7 * numeric("positive_retention")
        + 0.6 * numeric("query_coverage")
        - 0.6 * numeric("false_candidate_burden")
        - 0.4 * numeric("false_top1_rate")
    )


def select_variants_for_split(pool: pd.DataFrame, variants: list[dict[str, object]], calibration_queries: set[int]) -> list[dict[str, object]]:
    selected: list[dict[str, object]] = []
    by_method: dict[str, list[tuple[float, dict[str, object], dict[str, object]]]] = {}
    for variant in variants:
        method_id = str(variant["method_id"])
        retained = retained_for_method(pool, variant, calibration_queries)
        metrics = compute_metrics(retained, pool, calibration_queries, method_id, str(variant["method_family"]), str(variant["descriptor"]))
        score = calibration_score(metrics)
        by_method.setdefault(method_id, []).append((score, variant, metrics))
    for method_id, scored in by_method.items():
        scored.sort(key=lambda x: (x[0], x[2].get("query_coverage", 0.0), x[2].get("positive_retention", 0.0)), reverse=True)
        best = dict(scored[0][1])
        best["calibration_score"] = scored[0][0]
        selected.append(best)
    return selected


def random_retained(
    pool: pd.DataFrame,
    target: pd.DataFrame,
    query_indices: set[int],
    descriptor: str,
    rng: np.random.Generator,
    mode: str,
) -> pd.DataFrame:
    base = pool[(pool["descriptor"] == descriptor) & (pool["query_idx"].isin(query_indices))]
    grouped = {int(q): group for q, group in base.groupby("query_idx", sort=False)}
    chunks: list[pd.DataFrame] = []
    if mode == "same_size":
        target_counts = target.groupby("query_idx").size().to_dict() if not target.empty else {}
        for q in sorted(query_indices):
            count = int(target_counts.get(q, 0))
            if count <= 0:
                continue
            group = grouped.get(int(q), pd.DataFrame())
            take = min(count, len(group))
            if take:
                sampled = group.sample(n=take, replace=False, random_state=int(rng.integers(0, 2**31 - 1))).copy()
                sampled = sampled.sort_values("base_descriptor_similarity", ascending=False)
                sampled["reranked_rank"] = np.arange(1, len(sampled) + 1)
                chunks.append(sampled)
    elif mode == "same_coverage":
        covered = sorted(target["query_idx"].astype(int).unique()) if not target.empty else []
        covered_count = len(covered)
        if covered_count:
            sampled_queries = rng.choice(sorted(query_indices), size=min(covered_count, len(query_indices)), replace=False)
            avg_count = max(1, int(round(len(target) / covered_count)))
            for q in sampled_queries:
                group = grouped.get(int(q), pd.DataFrame())
                take = min(avg_count, len(group), REPORT_K)
                if take <= 0:
                    continue
                sampled = group.sample(n=take, replace=False, random_state=int(rng.integers(0, 2**31 - 1))).copy()
                sampled = sampled.sort_values("base_descriptor_similarity", ascending=False)
                sampled["reranked_rank"] = np.arange(1, len(sampled) + 1)
                chunks.append(sampled)
    else:
        raise ValueError(mode)
    if not chunks:
        return pd.DataFrame(columns=list(base.columns) + ["reranked_rank"])
    return pd.concat(chunks, ignore_index=True)


def random_control_summary(
    pool: pd.DataFrame,
    target: pd.DataFrame,
    target_metrics: dict[str, object],
    query_indices: set[int],
    descriptor: str,
    split_id: int,
    method_id: str,
    repeats: int,
    mode: str,
) -> dict[str, object]:
    rng = np.random.default_rng(RANDOM_SEED + split_id * 1000 + abs(hash(method_id + mode)) % 997)
    base = pool[(pool["descriptor"] == descriptor) & (pool["query_idx"].isin(query_indices))].copy()
    query_groups = {
        int(q): {
            "truth": group.sort_values("base_descriptor_similarity", ascending=False)["same_identity_truth_internal"].astype(bool).to_numpy(),
            "similarity": group.sort_values("base_descriptor_similarity", ascending=False)["base_descriptor_similarity"].to_numpy(),
        }
        for q, group in base.groupby("query_idx", sort=False)
    }
    true_total = int(base["same_identity_truth_internal"].sum())
    positive_queries = set(base.loc[base["same_identity_truth_internal"], "query_idx"].astype(int))
    target_counts = target.groupby("query_idx").size().to_dict() if not target.empty else {}
    covered_target = sorted(target["query_idx"].astype(int).unique()) if not target.empty else []
    avg_count = max(1, int(round(len(target) / max(len(covered_target), 1)))) if covered_target else 0

    metric_rows = []
    for repeat in range(1, repeats + 1):
        if mode == "same_coverage":
            eligible_queries = set(rng.choice(sorted(query_indices), size=min(len(covered_target), len(query_indices)), replace=False)) if covered_target else set()
        else:
            eligible_queries = set(query_indices)
        retained_true = 0
        retained_false = 0
        retained_count = 0
        covered_count = 0
        ap_values: list[float] = []
        rr_values: list[float] = []
        top1_values: list[int] = []
        top5_values: list[int] = []
        false_top1 = 0
        for q in sorted(query_indices):
            if q not in eligible_queries:
                if q in positive_queries:
                    ap_values.append(0.0)
                    rr_values.append(0.0)
                    top1_values.append(0)
                    top5_values.append(0)
                continue
            group = query_groups.get(int(q))
            if group is None:
                continue
            count = int(target_counts.get(q, 0)) if mode == "same_size" else avg_count
            count = min(count, len(group["truth"]), REPORT_K)
            if count <= 0:
                if q in positive_queries:
                    ap_values.append(0.0)
                    rr_values.append(0.0)
                    top1_values.append(0)
                    top5_values.append(0)
                continue
            sampled_idx = rng.choice(np.arange(len(group["truth"])), size=count, replace=False)
            sampled_idx = sampled_idx[np.argsort(-group["similarity"][sampled_idx])]
            rel = group["truth"][sampled_idx].astype(int)
            covered_count += 1
            retained_count += len(rel)
            retained_true += int(rel.sum())
            retained_false += int((rel == 0).sum())
            false_top1 += int(rel[0] == 0)
            if q in positive_queries:
                ap_values.append(average_precision(rel))
                pos = np.flatnonzero(rel == 1)
                rr_values.append(1.0 / (int(pos[0]) + 1) if len(pos) else 0.0)
                top1_values.append(int(rel[0] == 1))
                top5_values.append(int(rel[: min(REPORT_K, len(rel))].max() == 1))
        metric_rows.append(
            {
                "random_repeat": repeat,
                "mAP": float(np.mean(ap_values)) if ap_values else math.nan,
                "MRR": float(np.mean(rr_values)) if rr_values else math.nan,
                "top1_accuracy": float(np.mean(top1_values)) if top1_values else math.nan,
                "top5_accuracy": float(np.mean(top5_values)) if top5_values else math.nan,
                "false_top1_rate": false_top1 / max(covered_count, 1) if covered_count else math.nan,
                "false_candidate_burden": retained_false / max(len(query_indices), 1),
                "query_coverage": covered_count / max(len(query_indices), 1),
                "positive_retention": retained_true / max(true_total, 1),
                "candidate_retention": retained_count / max(len(base), 1),
            }
        )
    frame = pd.DataFrame(metric_rows)
    out: dict[str, object] = {
        "split_id": split_id,
        "target_method_id": method_id,
        "descriptor": descriptor,
        "random_control_type": mode,
        "random_repeat_count": repeats,
    }
    for metric in ["mAP", "MRR", "top1_accuracy", "top5_accuracy", "false_candidate_burden", "query_coverage", "positive_retention"]:
        values = pd.to_numeric(frame[metric], errors="coerce")
        method_value = float(target_metrics.get(metric, math.nan))
        out[f"{metric}_random_mean"] = float(values.mean())
        out[f"{metric}_random_std"] = float(values.std(ddof=0))
        out[f"{metric}_random_p05"] = float(values.quantile(0.05))
        out[f"{metric}_random_p50"] = float(values.quantile(0.50))
        out[f"{metric}_random_p95"] = float(values.quantile(0.95))
        out[f"{metric}_method_value"] = method_value
        out[f"{metric}_minus_random_mean"] = method_value - float(values.mean())
        out[f"{metric}_percentile_vs_random"] = float((values <= method_value).mean())
        if metric.startswith("false"):
            out[f"{metric}_beats_random_mean"] = "yes" if method_value < float(values.mean()) else "no"
        else:
            out[f"{metric}_beats_random_mean"] = "yes" if method_value > float(values.mean()) else "no"
    return out


def pareto_efficient(summary: pd.DataFrame) -> pd.DataFrame:
    df = summary.copy()
    metrics_max = ["mAP", "MRR", "top1_accuracy", "top5_accuracy", "positive_retention", "query_coverage"]
    metrics_min = ["false_candidate_burden", "false_top1_rate", "reviewed_candidates_per_query"]
    rows = []
    for _, row in df.iterrows():
        dominated = False
        same_split = df[df["split_id"] == row["split_id"]]
        for _, other in same_split.iterrows():
            if other["method_id"] == row["method_id"]:
                continue
            better_or_equal = True
            strictly_better = False
            for metric in metrics_max:
                a = float(other[metric]) if pd.notna(other[metric]) else -np.inf
                b = float(row[metric]) if pd.notna(row[metric]) else -np.inf
                better_or_equal &= a >= b
                strictly_better |= a > b
            for metric in metrics_min:
                a = float(other[metric]) if pd.notna(other[metric]) else np.inf
                b = float(row[metric]) if pd.notna(row[metric]) else np.inf
                better_or_equal &= a <= b
                strictly_better |= a < b
            if better_or_equal and strictly_better:
                dominated = True
                break
        rows.append("no" if dominated else "yes")
    df["pareto_efficient"] = rows
    return df


def aggregate_summary(evaluation: pd.DataFrame, random_size: pd.DataFrame, random_coverage: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for method_id, group in evaluation.groupby("method_id", sort=False):
        row = {
            "method_id": method_id,
            "method_family": group["method_family"].iloc[0],
            "descriptor": group["descriptor"].iloc[0],
            "split_count": int(group["split_id"].nunique()),
        }
        for metric in ["mAP", "MRR", "top1_accuracy", "top5_accuracy", "false_top1_rate", "false_candidate_burden", "query_coverage", "positive_retention", "candidate_retention", "reviewed_candidates_per_query", "coverage_adjusted_mAP"]:
            values = pd.to_numeric(group[metric], errors="coerce")
            row[f"mean_{metric}"] = float(values.mean())
            row[f"std_{metric}"] = float(values.std(ddof=0))
        rows.append(row)
    summary = pd.DataFrame(rows)
    raw = summary[summary["method_id"] == "raw_megadescriptor_ranking"]
    hard = summary[summary["method_id"] == "simple_pf_eri_hard_filtering"]
    quality = summary[summary["method_id"] == "quality_only_reranking"]
    for baseline_name, baseline in [("raw_descriptor", raw), ("simple_filter", hard), ("quality_only", quality)]:
        if baseline.empty:
            continue
        for metric in ["mAP", "MRR", "top5_accuracy", "false_candidate_burden"]:
            col = f"mean_{metric}"
            summary[f"{metric}_minus_{baseline_name}"] = summary[col] - float(baseline.iloc[0][col])
    for control_name, control in [("random_same_size", random_size), ("random_same_coverage", random_coverage)]:
        control_mean = control.groupby("target_method_id").agg(
            {
                "mAP_minus_random_mean": "mean",
                "MRR_minus_random_mean": "mean",
                "false_candidate_burden_minus_random_mean": "mean",
                "query_coverage_minus_random_mean": "mean",
                "positive_retention_minus_random_mean": "mean",
            }
        )
        for metric_col in control_mean.columns:
            summary[f"{control_name}_{metric_col}"] = summary["method_id"].map(control_mean[metric_col])
    return summary


def risk_coverage(evaluation: pd.DataFrame) -> pd.DataFrame:
    keep = [
        "split_id",
        "method_id",
        "method_family",
        "descriptor",
        "query_coverage",
        "positive_retention",
        "false_candidate_burden",
        "mAP",
        "MRR",
        "top1_accuracy",
        "top5_accuracy",
        "false_top1_rate",
        "reviewed_candidates_per_query",
        "calibrated_weight",
        "calibrated_threshold",
    ]
    return evaluation[keep].copy().rename(columns={"calibrated_weight": "threshold_or_weight_setting", "reviewed_candidates_per_query": "review_workload"})


def final_decision(summary: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    rerank = summary[summary["method_id"] == "candidate_utility_plus_descriptor_reranking"]
    if rerank.empty:
        decision = "phase9b_no_candidate_utility_result"
        rationale = "candidate utility plus descriptor reranking did not produce an output row"
    else:
        row = rerank.iloc[0]
        criteria = {
            "beats_raw_mAP": float(row.get("mAP_minus_raw_descriptor", -999)) > 0,
            "beats_simple_filter_mAP": float(row.get("mAP_minus_simple_filter", -999)) > 0,
            "beats_quality_mAP": float(row.get("mAP_minus_quality_only", -999)) > 0,
            "beats_random_same_size_mAP": float(row.get("random_same_size_mAP_minus_random_mean", -999)) > 0,
            "beats_random_same_coverage_mAP": float(row.get("random_same_coverage_mAP_minus_random_mean", -999)) > 0,
            "coverage_ok": float(row["mean_query_coverage"]) >= 0.50,
            "retention_ok": float(row["mean_positive_retention"]) >= 0.50,
        }
        if all(criteria.values()):
            decision = "pf_eri_reranking_enhancement_supported_for_czechlynx_fixed_descriptor_setting"
        else:
            decision = "pf_eri_reranking_enhancement_not_supported"
        rationale = "; ".join(f"{k}={v}" for k, v in criteria.items())
    rows = [
        {
            "decision_item": "phase9b_fixed_descriptor_reranking_decision",
            "decision": decision,
            "rationale": rationale,
        },
        {
            "decision_item": "training_allowed_next",
            "decision": "no",
            "rationale": "Phase 9B is no-training; any Phase 9C learning requires explicit approval after reviewing this result",
        },
        {
            "decision_item": "external_species_claim_supported",
            "decision": "no",
            "rationale": "CzechLynx-only fixed-descriptor validation; Mainland Clouded Leopard and Marbled Cat remain future motivation only",
        },
    ]
    return pd.DataFrame(rows), decision


def public_candidate_table(candidates: pd.DataFrame, metadata: pd.DataFrame, split_design: pd.DataFrame) -> pd.DataFrame:
    rows = []
    compact = candidates[
        [
            "descriptor",
            "query_token",
            "gallery_token",
            "rank",
            "base_descriptor_similarity",
            "other_descriptor_similarity",
            "same_identity_truth_internal",
            "query_image_utility_score",
            "gallery_image_utility_score",
            "pair_utility_score",
            "candidate_utility_score",
            "reciprocal_support",
            "margin_confidence",
            "descriptor_disagreement",
            "visual_failure_penalty",
            "source_table",
            "query_idx",
        ]
    ].copy()
    for _, split_row in split_design.iterrows():
        roles = split_roles(metadata, split_row)
        role_map = roles.to_dict()
        part = compact.copy()
        part["split_id"] = int(split_row["split_id"])
        part["calibration_or_evaluation"] = part["query_idx"].map(role_map)
        rows.append(part)
    public = pd.concat(rows, ignore_index=True)
    public = public.rename(columns={"query_token": "query_image_id", "gallery_token": "gallery_image_id"})
    public = public.drop(columns=["query_idx"])
    public["reciprocal_support"] = public["reciprocal_support"].map(lambda x: "yes" if bool(x) else "no")
    public["descriptor_disagreement"] = public["descriptor_disagreement"].map(lambda x: "yes" if bool(x) else "no")
    public["same_identity_truth_internal"] = public["same_identity_truth_internal"].map(lambda x: "same" if bool(x) else "different")
    return public


def make_doc(summary: pd.DataFrame, evaluation: pd.DataFrame, random_size: pd.DataFrame, random_coverage: pd.DataFrame, ablation: pd.DataFrame, pareto: pd.DataFrame, final: pd.DataFrame, inventory: pd.DataFrame, repeats: int) -> str:
    decision = final.loc[final["decision_item"] == "phase9b_fixed_descriptor_reranking_decision", "decision"].iloc[0]
    top_rows = summary.sort_values("mean_mAP", ascending=False).head(8)
    rerank = summary[summary["method_id"] == "candidate_utility_plus_descriptor_reranking"].head(1)
    raw = summary[summary["method_id"] == "raw_megadescriptor_ranking"].head(1)
    hard = summary[summary["method_id"] == "simple_pf_eri_hard_filtering"].head(1)
    quality = summary[summary["method_id"] == "quality_only_reranking"].head(1)
    def metric(frame: pd.DataFrame, col: str) -> str:
        if frame.empty or col not in frame.columns:
            return "NA"
        return f"{float(frame.iloc[0][col]):.4f}"
    def markdown_table(frame: pd.DataFrame) -> str:
        if frame.empty:
            return "_No rows._"
        safe = frame.copy()
        for col in safe.columns:
            if pd.api.types.is_numeric_dtype(safe[col]):
                safe[col] = safe[col].map(lambda x: "" if pd.isna(x) else f"{float(x):.4f}")
            else:
                safe[col] = safe[col].astype(str)
        headers = list(safe.columns)
        lines = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(["---"] * len(headers)) + " |",
        ]
        for _, row in safe.iterrows():
            lines.append("| " + " | ".join(str(row[col]) for col in headers) + " |")
        return "\n".join(lines)
    lines = [
        "# Phase 9B PF-ERI-Aware Fixed-Descriptor Reranking Results",
        "",
        "## 1. Purpose",
        "",
        "Phase 9B tests whether PF-ERI image, pair, and candidate utility scores can improve fixed-descriptor candidate reranking without training any model.",
        "",
        "## 2. Relationship to PROJECT_RULES.md and Phase 9A",
        "",
        "This run follows Level 1 only: no-training reranking with fixed MegaDescriptor and ResNet50 embeddings. It does not implement lightweight learning, metric learning, descriptor expansion, or external dataset validation.",
        "",
        "## 3. Phase 8 Boundary",
        "",
        "Phase 8 remains the boundary: simple PF-ERI hard filtering reduced false-candidate burden but did not robustly improve fixed-descriptor mAP under held-out query-level evaluation. Phase 9B tests utility-aware reranking as a stronger use of the same signal family.",
        "",
        "## 4. Input Inventory",
        "",
        f"Inspected inputs: `{len(inventory)}`. Missing inputs: `{int((inventory['exists'] == 'no').sum())}`.",
        "",
        "## 5. Candidate Table Construction",
        "",
        "The candidate table uses descriptor-generated top-20 query-gallery candidates from fixed embeddings. Public outputs use hardened image tokens and do not export raw paths, original IDs, working IDs, locations, trap/camera fields, or per-identity histories.",
        "",
        "## 6. Utility Score Construction",
        "",
        "Image utility uses visual PF-ERI and keeps descriptor similarity out of image-level scoring. Pair and candidate utility add descriptor support, reciprocal support, margin confidence, descriptor disagreement, and visual failure penalties.",
        "",
        "## 7. Baselines and Methods Compared",
        "",
        ", ".join(summary["method_id"].tolist()),
        "",
        "## 8. Held-Out Calibration/Evaluation Design",
        "",
        "The run reconstructs the existing Phase 8 identity-aware query splits. Weights and thresholds are selected on calibration queries and reported on held-out evaluation queries.",
        "",
        "## 9. Random Controls",
        "",
        f"Random same-size and same-coverage controls used `{repeats}` repeats per split and target method.",
        "",
        "## 10. Main Held-Out Results",
        "",
        markdown_table(top_rows[["method_id", "mean_mAP", "mean_MRR", "mean_top1_accuracy", "mean_top5_accuracy", "mean_false_candidate_burden", "mean_query_coverage", "mean_positive_retention"]]),
        "",
        "## 11. Direct Comparisons",
        "",
        f"Candidate utility plus descriptor reranking mean mAP: `{metric(rerank, 'mean_mAP')}`.",
        f"Raw MegaDescriptor mean mAP: `{metric(raw, 'mean_mAP')}`.",
        f"Simple PF-ERI hard filtering mean mAP: `{metric(hard, 'mean_mAP')}`.",
        f"Quality-only reranking mean mAP: `{metric(quality, 'mean_mAP')}`.",
        "",
        "## 12. Feature Ablation Results",
        "",
        markdown_table(ablation.sort_values("mean_mAP", ascending=False)[["method_id", "mean_mAP", "mean_MRR", "mean_false_candidate_burden", "mean_query_coverage", "mean_positive_retention"]]),
        "",
        "## 13. Risk-Coverage and Pareto Interpretation",
        "",
        f"Pareto-efficient held-out method/split rows: `{int((pareto['pareto_efficient'] == 'yes').sum())}` of `{len(pareto)}`. Interpret high mAP alongside query coverage, positive retention, and false-candidate burden.",
        "",
        "## 14. Success/Failure Decision",
        "",
        f"Decision: `{decision}`.",
        "",
        "## 15. Allowed Claims",
        "",
        "- CzechLynx fixed-descriptor PF-ERI-aware reranking can be evaluated without model training.",
        "- Results are bounded to CzechLynx, fixed descriptors, and held-out query-level validation.",
        "- If the decision is negative, PF-ERI remains supported as an evidence utility and review-prioritization framework rather than a proven Re-ID enhancement method.",
        "",
        "## 16. Forbidden Claims",
        "",
        "- PF-ERI is a new Re-ID descriptor.",
        "- PF-ERI is a trained deep Re-ID model.",
        "- PF-ERI identifies true individuals automatically.",
        "- PF-ERI is validated across felids, Mainland Clouded Leopard, or Marbled Cat.",
        "- PF-ERI is field-deployment ready or supports population, movement, occupancy, abundance, survival, or site-use inference.",
        "",
        "## 17. Recommended Next Step",
        "",
        "Review the Phase 9B decision before any Phase 9C lightweight learning. Do not train unless the held-out reranking result is judged strong enough and explicit approval is given.",
        "",
        "## 18. Confirmation",
        "",
        "No training, no external data download, no frozen-data edit, no delayed second-review access, no staging, and no commit were performed.",
        "",
    ]
    return "\n".join(lines)


def run(args: argparse.Namespace) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    QC_DIR.mkdir(parents=True, exist_ok=True)
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)

    if args.doc_only:
        inventory = pd.read_csv(INPUT_INVENTORY_CSV)
        evaluation = pd.read_csv(HELDOUT_SPLIT_CSV)
        random_size = pd.read_csv(RANDOM_SIZE_CSV)
        random_coverage = pd.read_csv(RANDOM_COVERAGE_CSV)
        summary = pd.read_csv(METHOD_SUMMARY_CSV)
        ablation = pd.read_csv(ABLATION_CSV)
        pareto = pd.read_csv(PARETO_CSV)
        final = pd.read_csv(FINAL_RECOMMENDATION_CSV)
        repeats = int(pd.to_numeric(random_size["random_repeat_count"], errors="coerce").min()) if not random_size.empty else args.random_repeats
        DOC_PATH.write_text(make_doc(summary, evaluation, random_size, random_coverage, ablation, pareto, final, inventory, repeats), encoding="utf-8")
        print(f"wrote {DOC_PATH}")
        return

    inventory = input_inventory(INPUTS_TO_INSPECT)
    inventory.to_csv(INPUT_INVENTORY_CSV, index=False)

    metadata, similarities = align_inputs(args)
    metadata = add_image_utility_components(metadata)
    candidates = build_candidates(metadata, similarities, MAX_K)
    split_design = load_split_design(SPLIT_DESIGN_CSV)
    public_candidate_table(candidates, metadata, split_design).to_csv(CANDIDATE_TABLE_CSV, index=False)

    variants = method_variants()
    evaluation_rows: list[dict[str, object]] = []
    random_size_rows: list[dict[str, object]] = []
    random_coverage_rows: list[dict[str, object]] = []
    retained_cache: dict[tuple[int, str], pd.DataFrame] = {}

    for _, split_row in split_design.iterrows():
        split_id = int(split_row["split_id"])
        roles = split_roles(metadata, split_row)
        calibration_queries = set(metadata.index[roles == "calibration"].astype(int))
        evaluation_queries = set(metadata.index[roles == "evaluation"].astype(int))
        selected = select_variants_for_split(candidates, variants, calibration_queries)
        for variant in selected:
            method_id = str(variant["method_id"])
            retained = retained_for_method(candidates, variant, evaluation_queries)
            retained_cache[(split_id, method_id)] = retained
            metrics = compute_metrics(retained, candidates, evaluation_queries, method_id, str(variant["method_family"]), str(variant["descriptor"]))
            metrics["split_id"] = split_id
            metrics["split_role"] = "evaluation"
            metrics["calibrated_weight"] = variant.get("weight", math.nan)
            metrics["calibrated_threshold"] = variant.get("threshold", math.nan)
            metrics["calibration_score"] = variant.get("calibration_score", math.nan)
            evaluation_rows.append(metrics)
            if method_id not in {"raw_megadescriptor_ranking", "raw_resnet50_ranking"} and str(variant["method_family"]) != "feature_ablation":
                random_size_rows.append(random_control_summary(candidates, retained, metrics, evaluation_queries, str(variant["descriptor"]), split_id, method_id, args.random_repeats, "same_size"))
                random_coverage_rows.append(random_control_summary(candidates, retained, metrics, evaluation_queries, str(variant["descriptor"]), split_id, method_id, args.random_repeats, "same_coverage"))

    evaluation = pd.DataFrame(evaluation_rows)
    random_size = pd.DataFrame(random_size_rows)
    random_coverage = pd.DataFrame(random_coverage_rows)
    summary = aggregate_summary(evaluation, random_size, random_coverage)
    ablation = summary[summary["method_family"] == "feature_ablation"].copy()
    risk = risk_coverage(evaluation)
    pareto = pareto_efficient(evaluation)
    final, _ = final_decision(summary)

    evaluation.to_csv(HELDOUT_SPLIT_CSV, index=False)
    random_size.to_csv(RANDOM_SIZE_CSV, index=False)
    random_coverage.to_csv(RANDOM_COVERAGE_CSV, index=False)
    summary.to_csv(METHOD_SUMMARY_CSV, index=False)
    ablation.to_csv(ABLATION_CSV, index=False)
    risk.to_csv(RISK_COVERAGE_CSV, index=False)
    pareto.to_csv(PARETO_CSV, index=False)
    final.to_csv(FINAL_RECOMMENDATION_CSV, index=False)
    DOC_PATH.write_text(make_doc(summary, evaluation, random_size, random_coverage, ablation, pareto, final, inventory, args.random_repeats), encoding="utf-8")

    print(f"wrote {OUTPUT_DIR}")
    print(f"candidate rows: {len(candidates) * len(split_design)}")
    print(final.to_string(index=False))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--megadescriptor-embeddings-csv", type=Path, default=MEGA_EMBEDDINGS_CSV)
    parser.add_argument("--resnet50-embeddings-csv", type=Path, default=RESNET_EMBEDDINGS_CSV)
    parser.add_argument("--identity-csv", type=Path, default=IDENTITY_CSV)
    parser.add_argument("--annotation-csv", type=Path, default=ANNOTATION_CSV)
    parser.add_argument("--random-repeats", type=int, default=500)
    parser.add_argument("--doc-only", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
