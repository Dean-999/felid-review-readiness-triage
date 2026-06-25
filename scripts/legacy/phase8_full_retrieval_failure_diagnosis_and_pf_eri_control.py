#!/usr/bin/env python3
"""Diagnose full retrieval failures and evaluate PF-ERI retrieval-control modes."""

from __future__ import annotations

import argparse
import ast
import hashlib
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MEGA_EMBEDDINGS_CSV = PROJECT_ROOT / "outputs/czechlynx/phase4/czechlynx_phase4c_megadescriptor_embeddings.csv"
RESNET_EMBEDDINGS_CSV = PROJECT_ROOT / "outputs/czechlynx/phase4/czechlynx_phase4c_resnet50_embeddings.csv"
IDENTITY_CSV = PROJECT_ROOT / "data/interim/czechlynx/czechlynx_expanded_125x4_internal_with_ids.csv"
ANNOTATION_CSV = PROJECT_ROOT / "data/labels/czechlynx/czechlynx_phase7a_1000_image_annotations_v1.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase8/full_retrieval_failure_diagnosis"
FIGURE_DIR = OUTPUT_DIR / "figures"

QUERY_FAILURE_CSV = OUTPUT_DIR / "phase8_full_retrieval_query_failure_table.csv"
FALSE_TOP1_CSV = OUTPUT_DIR / "phase8_full_retrieval_false_top1_diagnosis.csv"
TOPK_BURDEN_CSV = OUTPUT_DIR / "phase8_full_retrieval_topk_false_burden.csv"
CONTROL_COMPARISON_CSV = OUTPUT_DIR / "phase8_pf_eri_control_mode_comparison.csv"
RULES_CSV = OUTPUT_DIR / "phase8_pf_eri_retrieval_control_candidate_rules.csv"
ASSIGNMENT_CSV = OUTPUT_DIR / "phase8_pf_eri_retrieval_control_recommended_assignment.csv"
READINESS_CSV = OUTPUT_DIR / "phase8_pf_eri_retrieval_control_readiness_decision.csv"

TOP_K_VALUES = [1, 3, 5, 10]
BAND_ORDER = {"unusable": 0, "low": 1, "medium": 2, "high": 3}
THRESHOLDS = {
    "low_or_higher": {"low", "medium", "high"},
    "medium_or_higher": {"medium", "high"},
    "high_only": {"high"},
}
STRICTNESS = ["lenient", "standard", "strict"]
RERANKING_ALPHAS = [0.05, 0.10, 0.20]

PATTERN = {"none": 0.0, "low": 1.0, "medium": 2.0, "high": 3.0}
SIDE_QUALITY = {"none": 0.0, "low": 1.0, "medium": 2.0, "high": 3.0}
BODY = {"0_25": 0.0, "26_50": 1.0, "51_75": 2.0, "76_100": 3.0, "unknown": 1.0}
BLUR = {"severe": 0.0, "moderate": 1.0, "mild": 2.0, "none": 3.0, "unknown": 1.0}
OCCLUSION = {"major": 0.0, "partial": 1.5, "none": 3.0, "unknown": 1.5}
CONTRAST = {"low": 0.0, "not_available": 1.0, "good": 2.0, "unknown": 1.0}


def clean_string(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.lower()


def token(value: object) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:12]


def band(score: float) -> str:
    if score >= 75.0:
        return "high"
    if score >= 50.0:
        return "medium"
    if score >= 25.0:
        return "low"
    return "unusable"


def parse_embedding(value: str) -> np.ndarray:
    return np.asarray(ast.literal_eval(value), dtype=np.float64)


def load_embeddings(path: Path) -> tuple[pd.DataFrame, np.ndarray]:
    df = pd.read_csv(path)
    vectors = np.vstack([parse_embedding(value) for value in df["embedding_vector"]])
    if not np.isfinite(vectors).all():
        raise ValueError(f"non-finite embedding values found in {path}")
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    vectors = vectors / norms
    return df[["expanded_image_id", "embedding_model", "embedding_dim"]].copy(), vectors


def score_image_visual(row: pd.Series) -> dict[str, object]:
    pattern = PATTERN[str(row["pattern_visibility"])]
    side = SIDE_QUALITY[str(row["side_evidence_quality"])]
    body = BODY[str(row["body_fraction_visible"])]
    blur = BLUR[str(row["blur_level"])]
    occlusion = OCCLUSION[str(row["occlusion_level"])]
    contrast = CONTRAST[str(row["contrast_level"])]
    frontal_penalty = 8.0 if row["frontal_or_rear_view"] == "yes" else 3.0 if row["frontal_or_rear_view"] == "unknown" else 0.0
    silhouette_penalty = 12.0 if row["silhouette_only"] == "yes" else 0.0
    partial_penalty = 6.0 if row["partial_body"] == "yes" else 0.0
    uncertainty_penalty = 5.0 if row["uncertainty_flag"] == "yes" else 0.0
    night_ir_penalty = 4.0 if row["night_ir_artifact"] == "yes" else 0.0
    weighted = 100.0 * (
        0.26 * (pattern / 3.0)
        + 0.24 * (side / 3.0)
        + 0.16 * (body / 3.0)
        + 0.14 * (blur / 3.0)
        + 0.10 * (occlusion / 3.0)
        + 0.05 * (contrast / 2.0)
    )
    weighted = max(0.0, min(100.0, weighted - frontal_penalty - silhouette_penalty - partial_penalty - uncertainty_penalty - night_ir_penalty))
    components = {
        "pattern_visibility": pattern / 3.0,
        "side_evidence_quality": side / 3.0,
        "body_fraction_visible": body / 3.0,
        "blur_level": blur / 3.0,
        "occlusion_level": occlusion / 3.0,
    }
    if row["contrast_level"] != "not_available":
        components["contrast_level"] = contrast / 2.0
    primary = min(components.items(), key=lambda item: item[1])[0]
    severe_failure = (
        row["pattern_visibility"] == "none"
        or row["blur_level"] == "severe"
        or row["occlusion_level"] == "major"
        or row["silhouette_only"] == "yes"
        or row["frontal_or_rear_view"] == "yes"
    )
    return {
        "visual_pf_eri_score": weighted,
        "visual_pf_eri_band": band(weighted),
        "primary_limiting_factor": primary,
        "severe_visual_failure": "yes" if severe_failure else "no",
    }


def load_metadata(identity_csv: Path, annotation_csv: Path, embedding_ids: set[str]) -> pd.DataFrame:
    ids = pd.read_csv(identity_csv)[["expanded_image_id", "working_individual_id"]].copy()
    annotations = pd.read_csv(annotation_csv)
    visual_cols = [
        "expanded_image_id",
        "pattern_visibility",
        "side_evidence_quality",
        "body_fraction_visible",
        "partial_body",
        "frontal_or_rear_view",
        "silhouette_only",
        "blur_level",
        "occlusion_level",
        "lighting_condition",
        "night_ir_artifact",
        "contrast_level",
        "uncertainty_flag",
        "annotation_status",
    ]
    annotations = annotations[visual_cols].copy()
    for col in visual_cols:
        if col != "expanded_image_id":
            annotations[col] = clean_string(annotations[col])
    metadata = ids.merge(annotations, on="expanded_image_id", how="inner", validate="one_to_one")
    metadata = metadata[metadata["expanded_image_id"].isin(embedding_ids)].copy()
    scored = metadata.apply(score_image_visual, axis=1, result_type="expand")
    metadata = pd.concat([metadata.reset_index(drop=True), scored.reset_index(drop=True)], axis=1)
    metadata["image_token"] = metadata["expanded_image_id"].map(token)
    metadata["identity_token"] = metadata["working_individual_id"].map(token)
    return metadata


def average_precision(relevance: np.ndarray) -> float:
    positives = int(relevance.sum())
    if positives == 0:
        return math.nan
    cumulative = np.cumsum(relevance)
    precision_at_hits = cumulative[relevance == 1] / (np.flatnonzero(relevance == 1) + 1)
    return float(precision_at_hits.mean())


def rank_gallery(similarity: np.ndarray, query_idx: int, gallery_mask: np.ndarray | None = None, adjusted_scores: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    rows = np.arange(similarity.shape[0])
    if gallery_mask is None:
        mask = np.ones(similarity.shape[0], dtype=bool)
    else:
        mask = gallery_mask.copy()
    mask[query_idx] = False
    gallery_indices = rows[mask]
    scores = adjusted_scores[query_idx, gallery_indices] if adjusted_scores is not None else similarity[query_idx, gallery_indices]
    order = np.argsort(-scores)
    return gallery_indices[order], scores[order]


def allowed_mask(metadata: pd.DataFrame, threshold_name: str) -> np.ndarray:
    return metadata["visual_pf_eri_band"].isin(THRESHOLDS[threshold_name]).to_numpy()


def is_high_similarity_low_evidence(similarity_value: float, query: pd.Series, gallery: pd.Series, descriptor: str) -> bool:
    cutoff = 0.82 if descriptor == "megadescriptor" else 0.72
    low_evidence = min(query["visual_pf_eri_score"], gallery["visual_pf_eri_score"]) < 50.0
    severe = query["severe_visual_failure"] == "yes" or gallery["severe_visual_failure"] == "yes"
    return bool(similarity_value >= cutoff and (low_evidence or severe))


def candidate_assignment(query: pd.Series, gallery: pd.Series, rank: int, similarity_value: float, descriptor: str, strictness: str) -> tuple[str, str]:
    q_band = query["visual_pf_eri_band"]
    g_band = gallery["visual_pf_eri_band"]
    severe = query["severe_visual_failure"] == "yes" or gallery["severe_visual_failure"] == "yes"
    pair_min = min(BAND_ORDER[q_band], BAND_ORDER[g_band])
    contradiction = is_high_similarity_low_evidence(similarity_value, query, gallery, descriptor)

    if q_band == "unusable" or g_band == "unusable":
        return "exclude_candidate", "unusable_query_or_gallery_evidence"
    if strictness == "strict" and severe:
        return "exclude_candidate", "strict_severe_visual_failure"
    if severe or contradiction:
        return "defer_candidate", "visual_failure_or_high_similarity_low_evidence_contradiction"
    if strictness == "lenient":
        if pair_min >= BAND_ORDER["low"] and rank <= 10:
            return "review_candidate", "lenient_low_or_higher_top10"
    elif strictness == "standard":
        if pair_min >= BAND_ORDER["medium"] and rank <= 10:
            return "review_candidate", "standard_medium_or_higher_top10"
        if pair_min >= BAND_ORDER["low"] and rank <= 3:
            return "defer_candidate", "standard_low_evidence_top3_defer"
    else:
        if pair_min >= BAND_ORDER["high"] and rank <= 10:
            return "review_candidate", "strict_high_only_top10"
        if pair_min >= BAND_ORDER["medium"] and rank <= 5:
            return "defer_candidate", "strict_medium_top5_defer"
    return "defer_candidate", "below_review_gate"


def query_failure_rows(metadata: pd.DataFrame, similarity: np.ndarray, descriptor: str) -> list[dict[str, object]]:
    identities = metadata["working_individual_id"].astype(str).to_numpy()
    rows = []
    for query_idx, query in metadata.iterrows():
        ranked, scores = rank_gallery(similarity, query_idx)
        relevance = identities[ranked] == identities[query_idx]
        positive_positions = np.flatnonzero(relevance)
        first_rank = int(positive_positions[0]) + 1 if len(positive_positions) else math.nan
        best_positive_similarity = float(scores[positive_positions[0]]) if len(positive_positions) else math.nan
        top1_idx = int(ranked[0])
        top1 = metadata.iloc[top1_idx]
        top1_similarity = float(scores[0])
        rows.append(
            {
                "descriptor": descriptor,
                "query_token": query["image_token"],
                "query_visual_band": query["visual_pf_eri_band"],
                "query_visual_score": round(float(query["visual_pf_eri_score"]), 4),
                "query_limiting_factor": query["primary_limiting_factor"],
                "query_severe_visual_failure": query["severe_visual_failure"],
                "top1_gallery_token": top1["image_token"],
                "top1_gallery_visual_band": top1["visual_pf_eri_band"],
                "top1_gallery_visual_score": round(float(top1["visual_pf_eri_score"]), 4),
                "top1_gallery_limiting_factor": top1["primary_limiting_factor"],
                "top1_gallery_severe_visual_failure": top1["severe_visual_failure"],
                "top1_same_identity": "yes" if bool(relevance[0]) else "no",
                "first_same_identity_rank": first_rank,
                "same_identity_in_top5": int(relevance[:5].sum()),
                "same_identity_in_top10": int(relevance[:10].sum()),
                "top1_similarity": top1_similarity,
                "best_same_identity_similarity": best_positive_similarity,
                "top1_minus_best_same_identity_similarity": top1_similarity - best_positive_similarity if not math.isnan(best_positive_similarity) else math.nan,
                "high_similarity_low_evidence_contradiction": "yes" if is_high_similarity_low_evidence(top1_similarity, query, top1, descriptor) else "no",
            }
        )
    return rows


def false_top1_diagnosis(query_table: pd.DataFrame) -> pd.DataFrame:
    false_cases = query_table[query_table["top1_same_identity"] == "no"].copy()
    summary_rows: list[dict[str, object]] = []
    group_specs = [
        ("query_visual_band", ["query_visual_band"]),
        ("gallery_visual_band", ["top1_gallery_visual_band"]),
        ("query_limiting_factor", ["query_limiting_factor"]),
        ("gallery_limiting_factor", ["top1_gallery_limiting_factor"]),
        ("query_gallery_visual_band_combo", ["query_visual_band", "top1_gallery_visual_band"]),
        ("query_gallery_limiting_factor_combo", ["query_limiting_factor", "top1_gallery_limiting_factor"]),
    ]
    for descriptor, descriptor_cases in false_cases.groupby("descriptor"):
        total = len(descriptor_cases)
        all_descriptor = query_table[query_table["descriptor"] == descriptor]
        for summary_type, fields in group_specs:
            for keys, group in descriptor_cases.groupby(fields, dropna=False):
                if not isinstance(keys, tuple):
                    keys = (keys,)
                value = " | ".join(str(x) for x in keys)
                denominator = len(all_descriptor)
                if summary_type == "query_visual_band":
                    denominator = int((all_descriptor["query_visual_band"] == keys[0]).sum())
                elif summary_type == "gallery_visual_band":
                    denominator = int((all_descriptor["top1_gallery_visual_band"] == keys[0]).sum())
                summary_rows.append(
                    {
                        "descriptor": descriptor,
                        "summary_type": summary_type,
                        "summary_value": value,
                        "false_top1_count": int(len(group)),
                        "false_top1_share_among_false": len(group) / total if total else math.nan,
                        "false_top1_rate_within_group": len(group) / denominator if denominator else math.nan,
                    }
                )
    return pd.DataFrame(summary_rows)


def topk_false_burden_rows(metadata: pd.DataFrame, similarity: np.ndarray, descriptor: str) -> list[dict[str, object]]:
    identities = metadata["working_individual_id"].astype(str).to_numpy()
    rows: list[dict[str, object]] = []
    for query_idx, query in metadata.iterrows():
        ranked, scores = rank_gallery(similarity, query_idx)
        relevance = identities[ranked] == identities[query_idx]
        for k in TOP_K_VALUES:
            window = ranked[:k]
            rel = relevance[:k]
            false_count = int(k - rel.sum())
            true_count = int(rel.sum())
            rows.append(
                {
                    "descriptor": descriptor,
                    "k": k,
                    "query_visual_band": query["visual_pf_eri_band"],
                    "query_limiting_factor": query["primary_limiting_factor"],
                    "query_severe_visual_failure": query["severe_visual_failure"],
                    "query_count": 1,
                    "topk_candidate_count": int(len(window)),
                    "false_candidate_count": false_count,
                    "false_candidate_proportion": false_count / len(window) if len(window) else math.nan,
                    "same_identity_candidate_count": true_count,
                    "has_same_identity_in_topk": "yes" if true_count > 0 else "no",
                    "review_burden_candidates": int(len(window)),
                }
            )
    raw = pd.DataFrame(rows)
    summary = (
        raw.groupby(["descriptor", "k", "query_visual_band", "query_limiting_factor", "query_severe_visual_failure"], dropna=False)
        .agg(
            query_count=("query_count", "sum"),
            topk_candidate_count=("topk_candidate_count", "sum"),
            false_candidate_count=("false_candidate_count", "sum"),
            same_identity_candidate_count=("same_identity_candidate_count", "sum"),
            query_with_same_identity_in_topk=("has_same_identity_in_topk", lambda s: int((s == "yes").sum())),
        )
        .reset_index()
    )
    summary["false_candidate_proportion"] = summary["false_candidate_count"] / summary["topk_candidate_count"]
    summary["topk_success_rate"] = summary["query_with_same_identity_in_topk"] / summary["query_count"]
    return summary.to_dict("records")


def evaluate_ranking(metadata: pd.DataFrame, similarity: np.ndarray, descriptor: str, mode: str, threshold_name: str,
                     gallery_gate: bool = False, query_gate: bool = False, adjusted_scores: np.ndarray | None = None) -> dict[str, object]:
    identities = metadata["working_individual_id"].astype(str).to_numpy()
    rows = np.arange(len(metadata))
    gate_mask = allowed_mask(metadata, threshold_name)
    ap_values: list[float] = []
    top1_hits: list[int] = []
    top5_hits: list[int] = []
    false_top1 = 0
    average_false_top5: list[int] = []
    covered_queries = 0
    positive_queries = 0
    candidate_total = 0
    full_candidate_total = len(metadata) * (len(metadata) - 1)

    for query_idx in rows:
        if query_gate and not gate_mask[query_idx]:
            continue
        gallery_mask = gate_mask.copy() if gallery_gate else np.ones(len(metadata), dtype=bool)
        ranked, _ = rank_gallery(similarity, int(query_idx), gallery_mask=gallery_mask, adjusted_scores=adjusted_scores)
        if len(ranked) == 0:
            continue
        covered_queries += 1
        candidate_total += len(ranked)
        relevance = (identities[ranked] == identities[query_idx]).astype(int)
        if relevance.sum() == 0:
            continue
        positive_queries += 1
        ap_values.append(average_precision(relevance))
        top1_hits.append(int(relevance[0]))
        top5_hits.append(int(relevance[: min(5, len(relevance))].max()))
        false_top1 += int(relevance[0] == 0)
        average_false_top5.append(int(min(5, len(relevance)) - relevance[: min(5, len(relevance))].sum()))

    return {
        "descriptor": descriptor,
        "control_mode": mode,
        "threshold": threshold_name,
        "top_k": "full_ranked_gallery",
        "strictness": "not_applicable",
        "alpha": math.nan,
        "query_coverage": covered_queries / len(metadata) if len(metadata) else math.nan,
        "candidate_coverage": candidate_total / full_candidate_total if full_candidate_total else math.nan,
        "positive_query_coverage": positive_queries / len(metadata) if len(metadata) else math.nan,
        "top1_accuracy_among_covered_positive_queries": float(np.mean(top1_hits)) if top1_hits else math.nan,
        "top5_success_among_covered_positive_queries": float(np.mean(top5_hits)) if top5_hits else math.nan,
        "mAP_among_covered_positive_queries": float(np.mean(ap_values)) if ap_values else math.nan,
        "false_top1_rate": false_top1 / len(top1_hits) if top1_hits else math.nan,
        "average_false_candidates_in_top5": float(np.mean(average_false_top5)) if average_false_top5 else math.nan,
        "review_burden_reduction": 1.0 - (candidate_total / full_candidate_total) if full_candidate_total else math.nan,
        "positive_retention": positive_queries / len(metadata) if len(metadata) else math.nan,
        "interpretation": "fixed descriptor ranking with PF-ERI admissibility control",
    }


def evaluate_pair_pruning(metadata: pd.DataFrame, similarity: np.ndarray, descriptor: str, threshold_name: str,
                          top_k: int, strictness: str) -> tuple[dict[str, object], list[dict[str, object]]]:
    identities = metadata["working_individual_id"].astype(str).to_numpy()
    assignment_rows: list[dict[str, object]] = []
    top1_hits: list[int] = []
    top5_hits: list[int] = []
    ap_values: list[float] = []
    false_top1 = 0
    false_top5_counts: list[int] = []
    covered_queries = 0
    positive_queries = 0
    review_candidate_count = 0
    full_topk_candidate_count = len(metadata) * top_k
    positive_review_retained = 0
    positive_available_in_topk = 0

    for query_idx, query in metadata.iterrows():
        ranked, scores = rank_gallery(similarity, int(query_idx))
        window = ranked[:top_k]
        window_scores = scores[:top_k]
        reviewed_relevance: list[int] = []
        reviewed_scores: list[float] = []
        any_positive_available = False
        covered_by_review = False
        for local_rank, (gallery_idx, score) in enumerate(zip(window, window_scores), start=1):
            gallery = metadata.iloc[int(gallery_idx)]
            assignment, reason = candidate_assignment(query, gallery, local_rank, float(score), descriptor, strictness)
            if threshold_name != "low_or_higher":
                min_band = min(BAND_ORDER[query["visual_pf_eri_band"]], BAND_ORDER[gallery["visual_pf_eri_band"]])
                if min_band < min(BAND_ORDER[b] for b in THRESHOLDS[threshold_name]):
                    assignment, reason = "defer_candidate", f"{threshold_name}_pair_gate_not_met"
            same_identity = identities[int(gallery_idx)] == identities[int(query_idx)]
            any_positive_available = any_positive_available or bool(same_identity)
            if assignment == "review_candidate":
                covered_by_review = True
                review_candidate_count += 1
                reviewed_relevance.append(int(same_identity))
                reviewed_scores.append(float(score))
                positive_review_retained += int(same_identity)
            assignment_rows.append(
                {
                    "descriptor": descriptor,
                    "control_mode": "pair_level_topk_review_pruning",
                    "threshold": threshold_name,
                    "top_k": top_k,
                    "strictness": strictness,
                    "query_token": query["image_token"],
                    "candidate_rank": local_rank,
                    "gallery_token": gallery["image_token"],
                    "candidate_similarity": float(score),
                    "query_visual_band": query["visual_pf_eri_band"],
                    "gallery_visual_band": gallery["visual_pf_eri_band"],
                    "query_visual_score": round(float(query["visual_pf_eri_score"]), 4),
                    "gallery_visual_score": round(float(gallery["visual_pf_eri_score"]), 4),
                    "query_limiting_factor": query["primary_limiting_factor"],
                    "gallery_limiting_factor": gallery["primary_limiting_factor"],
                    "query_severe_visual_failure": query["severe_visual_failure"],
                    "gallery_severe_visual_failure": gallery["severe_visual_failure"],
                    "high_similarity_low_evidence_contradiction": "yes" if is_high_similarity_low_evidence(float(score), query, gallery, descriptor) else "no",
                    "recommended_assignment": assignment,
                    "assignment_reason": reason,
                }
            )
        positive_available_in_topk += int(any_positive_available)
        if not covered_by_review:
            continue
        covered_queries += 1
        if any(reviewed_relevance):
            positive_queries += 1
            relevance = np.asarray(reviewed_relevance, dtype=int)
            top1_hits.append(int(relevance[0]))
            top5_hits.append(int(relevance[: min(5, len(relevance))].max()))
            false_top1 += int(relevance[0] == 0)
            false_top5_counts.append(int(min(5, len(relevance)) - relevance[: min(5, len(relevance))].sum()))
            ap_values.append(average_precision(relevance))

    metrics = {
        "descriptor": descriptor,
        "control_mode": "pair_level_topk_review_pruning",
        "threshold": threshold_name,
        "top_k": top_k,
        "strictness": strictness,
        "alpha": math.nan,
        "query_coverage": covered_queries / len(metadata) if len(metadata) else math.nan,
        "candidate_coverage": review_candidate_count / full_topk_candidate_count if full_topk_candidate_count else math.nan,
        "positive_query_coverage": positive_queries / len(metadata) if len(metadata) else math.nan,
        "top1_accuracy_among_covered_positive_queries": float(np.mean(top1_hits)) if top1_hits else math.nan,
        "top5_success_among_covered_positive_queries": float(np.mean(top5_hits)) if top5_hits else math.nan,
        "mAP_among_covered_positive_queries": float(np.mean(ap_values)) if ap_values else math.nan,
        "false_top1_rate": false_top1 / len(top1_hits) if top1_hits else math.nan,
        "average_false_candidates_in_top5": float(np.mean(false_top5_counts)) if false_top5_counts else math.nan,
        "review_burden_reduction": 1.0 - (review_candidate_count / full_topk_candidate_count) if full_topk_candidate_count else math.nan,
        "positive_retention": positive_review_retained / max(positive_available_in_topk, 1),
        "interpretation": "descriptor first, PF-ERI assigns top-k candidates to review/defer/exclude",
    }
    return metrics, assignment_rows


def adjusted_score_matrix(similarity: np.ndarray, metadata: pd.DataFrame, alpha: float) -> np.ndarray:
    visual = metadata["visual_pf_eri_score"].to_numpy(dtype=float) / 100.0
    pair_visual = (visual[:, None] + visual[None, :]) / 2.0
    severe = metadata["severe_visual_failure"].eq("yes").to_numpy()
    severe_pair = np.logical_or(severe[:, None], severe[None, :]).astype(float)
    return similarity + alpha * pair_visual - (alpha / 2.0) * severe_pair


def rules_frame() -> pd.DataFrame:
    rows = [
        {
            "rule_id": "R1",
            "stage": "retrieve",
            "condition": "rank gallery by fixed descriptor similarity; do not train or alter descriptor outputs",
            "assignment": "ranked_candidate_pool",
            "purpose": "preserve descriptor as measurement signal and keep PF-ERI limited to evidence-control review",
        },
        {
            "rule_id": "R2",
            "stage": "visual_evidence_gate",
            "condition": "query or gallery visual band is unusable",
            "assignment": "exclude_candidate",
            "purpose": "remove evidence that is not reviewable for patterned-felid flank evidence",
        },
        {
            "rule_id": "R3",
            "stage": "visual_evidence_gate",
            "condition": "severe visual failure or high descriptor similarity with low visual evidence",
            "assignment": "defer_candidate",
            "purpose": "flag descriptor-evidence contradiction for human review caution",
        },
        {
            "rule_id": "R4",
            "stage": "standard_review_gate",
            "condition": "query and gallery are medium-or-higher PF-ERI and candidate is in top-k",
            "assignment": "review_candidate",
            "purpose": "retain candidates with reviewable evidence while reducing top-k burden",
        },
        {
            "rule_id": "R5",
            "stage": "strict_review_gate",
            "condition": "strict mode requires high-high PF-ERI for review; medium evidence can be deferred",
            "assignment": "review_candidate_or_defer_candidate",
            "purpose": "sensitivity check for conservative evidence control",
        },
        {
            "rule_id": "R6",
            "stage": "reranking_diagnostic",
            "condition": "descriptor similarity plus small visual-evidence bonus or severe-failure penalty",
            "assignment": "diagnostic_only",
            "purpose": "explore whether PF-ERI helps ranking, without treating it as final safety score",
        },
    ]
    return pd.DataFrame(rows)


def readiness_frame(control: pd.DataFrame, false_diag: pd.DataFrame) -> pd.DataFrame:
    pair = control[control["control_mode"] == "pair_level_topk_review_pruning"].copy()
    best = pair.sort_values(
        ["false_top1_rate", "top5_success_among_covered_positive_queries", "query_coverage"],
        ascending=[True, False, False],
    ).head(1)
    best_mode = "pair_level_topk_review_pruning" if not best.empty else "undetermined"
    query_only = control[control["control_mode"] == "query_only_filter"]["mAP_among_covered_positive_queries"].max()
    pair_best = pair["mAP_among_covered_positive_queries"].max() if not pair.empty else math.nan
    stronger = "yes" if not math.isnan(pair_best) and not math.isnan(query_only) and pair_best >= query_only else "uncertain"
    dominant = (
        false_diag[(false_diag["descriptor"] == "megadescriptor") & (false_diag["summary_type"] == "query_limiting_factor")]
        .sort_values("false_top1_count", ascending=False)
        .head(1)
    )
    dominant_value = dominant["summary_value"].iloc[0] if not dominant.empty else "undetermined"
    return pd.DataFrame(
        [
            {
                "decision_item": "pf_eri_retrieval_level_control_stronger_than_simple_image_filtering",
                "decision": stronger,
                "rationale": "pair-level top-k pruning evaluates query and gallery evidence together; compare against query-only filtering before treating it as preferred",
            },
            {
                "decision_item": "most_promising_control_mode",
                "decision": best_mode,
                "rationale": "best available mode balances false top-1 reduction, top-5 retention, and query coverage under full retrieval",
            },
            {
                "decision_item": "dominant_false_top1_visual_cause",
                "decision": dominant_value,
                "rationale": "dominant factor is computed from false top-1 query-side diagnosis",
            },
            {
                "decision_item": "external_dataset_audit_next",
                "decision": "yes_with_caution",
                "rationale": "CzechLynx full retrieval is strong enough to motivate an external access/license audit, but not a broader felid validation claim",
            },
            {
                "decision_item": "algorithm_refinement_before_external_benchmarking",
                "decision": "yes",
                "rationale": "retrieval-control should be documented as pair-level top-k review control before external testing",
            },
            {
                "decision_item": "broader_felid_claim_supported",
                "decision": "no",
                "rationale": "only CzechLynx has known-ID validation in this repository slice",
            },
        ]
    )


def make_figures(query_table: pd.DataFrame, topk: pd.DataFrame, control: pd.DataFrame) -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    def false_rate_by(field: str, filename: str, title: str) -> None:
        rows = []
        for (descriptor, value), group in query_table.groupby(["descriptor", field], dropna=False):
            rows.append({"descriptor": descriptor, field: value, "false_top1_rate": float((group["top1_same_identity"] == "no").mean())})
        df = pd.DataFrame(rows)
        labels = df["descriptor"] + "\n" + df[field].astype(str)
        plt.figure(figsize=(9, 5))
        plt.bar(np.arange(len(df)), df["false_top1_rate"], color=["#4477AA" if d == "megadescriptor" else "#CC6677" for d in df["descriptor"]])
        plt.xticks(np.arange(len(df)), labels, rotation=45, ha="right", fontsize=8)
        plt.ylabel("False top-1 rate")
        plt.title(title)
        plt.tight_layout()
        plt.savefig(FIGURE_DIR / filename, dpi=180)
        plt.close()

    false_rate_by("query_visual_band", "phase8_false_top1_rate_by_query_visual_band.png", "False top-1 by query PF-ERI band")
    false_rate_by("top1_gallery_visual_band", "phase8_false_top1_rate_by_gallery_visual_band.png", "False top-1 by top-1 gallery PF-ERI band")

    plt.figure(figsize=(8, 5))
    for band_name, group in query_table[query_table["descriptor"] == "megadescriptor"].groupby("query_visual_band"):
        ranks = pd.to_numeric(group["first_same_identity_rank"], errors="coerce").dropna()
        plt.hist(ranks, bins=20, alpha=0.55, label=band_name)
    plt.xlabel("First same-identity rank")
    plt.ylabel("Query count")
    plt.title("First same-identity rank by query PF-ERI band")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "phase8_first_same_identity_rank_distribution_by_pf_eri_band.png", dpi=180)
    plt.close()

    burden = topk.groupby(["descriptor", "k"], as_index=False)["false_candidate_proportion"].mean()
    plt.figure(figsize=(8, 5))
    for descriptor, group in burden.groupby("descriptor"):
        plt.plot(group["k"], group["false_candidate_proportion"], marker="o", label=descriptor)
    plt.xlabel("Top-k")
    plt.ylabel("Mean false-candidate proportion")
    plt.title("Top-k false burden by descriptor")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "phase8_topk_false_burden_by_descriptor.png", dpi=180)
    plt.close()

    subset = control[(control["threshold"] == "medium_or_higher") & (control["descriptor"] == "megadescriptor")].copy()
    subset = subset.sort_values(["control_mode", "top_k", "strictness", "alpha"]).head(30)
    labels = subset["control_mode"].str.replace("_", " ") + "\n" + subset["top_k"].astype(str) + "/" + subset["strictness"].astype(str)
    plt.figure(figsize=(12, 6))
    plt.bar(np.arange(len(subset)), subset["false_top1_rate"], color="#4477AA")
    plt.xticks(np.arange(len(subset)), labels, rotation=60, ha="right", fontsize=7)
    plt.ylabel("False top-1 rate")
    plt.title("PF-ERI control mode comparison")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "phase8_pf_eri_control_mode_comparison.png", dpi=180)
    plt.close()

    plt.figure(figsize=(8, 5))
    for descriptor, group in control.groupby("descriptor"):
        plt.scatter(group["query_coverage"], group["false_top1_rate"], label=descriptor, alpha=0.75)
    plt.xlabel("Query coverage")
    plt.ylabel("False top-1 rate")
    plt.title("Coverage vs false top-1 tradeoff")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "phase8_coverage_vs_false_top1_tradeoff.png", dpi=180)
    plt.close()

    plt.figure(figsize=(8, 5))
    mega = query_table[query_table["descriptor"] == "megadescriptor"].copy()
    plt.scatter(mega["query_visual_score"], mega["first_same_identity_rank"], alpha=0.45, s=18)
    plt.xlabel("Query visual PF-ERI score")
    plt.ylabel("First same-identity rank")
    plt.title("Query visual score vs first same-identity rank")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "phase8_query_visual_score_vs_first_same_identity_rank.png", dpi=180)
    plt.close()


def run(args: argparse.Namespace) -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    mega_meta, mega_vectors = load_embeddings(args.megadescriptor_embeddings_csv)
    resnet_meta, resnet_vectors = load_embeddings(args.resnet50_embeddings_csv)
    common_ids = set(mega_meta["expanded_image_id"]) & set(resnet_meta["expanded_image_id"])
    metadata = load_metadata(args.identity_csv, args.annotation_csv, common_ids)
    metadata = metadata.sort_values("expanded_image_id").reset_index(drop=True)
    mega_lookup = {image_id: idx for idx, image_id in enumerate(mega_meta["expanded_image_id"])}
    resnet_lookup = {image_id: idx for idx, image_id in enumerate(resnet_meta["expanded_image_id"])}
    ordered_mega = mega_vectors[[mega_lookup[x] for x in metadata["expanded_image_id"]]]
    ordered_resnet = resnet_vectors[[resnet_lookup[x] for x in metadata["expanded_image_id"]]]
    similarities = {
        "megadescriptor": np.einsum("ik,jk->ij", ordered_mega, ordered_mega, optimize=True),
        "resnet50": np.einsum("ik,jk->ij", ordered_resnet, ordered_resnet, optimize=True),
    }

    query_rows: list[dict[str, object]] = []
    topk_rows: list[dict[str, object]] = []
    control_rows: list[dict[str, object]] = []
    assignment_rows: list[dict[str, object]] = []
    for descriptor, sim in similarities.items():
        query_rows.extend(query_failure_rows(metadata, sim, descriptor))
        topk_rows.extend(topk_false_burden_rows(metadata, sim, descriptor))
        for threshold_name in THRESHOLDS:
            control_rows.append(evaluate_ranking(metadata, sim, descriptor, "no_pf_eri_control", threshold_name))
            control_rows.append(evaluate_ranking(metadata, sim, descriptor, "query_only_filter", threshold_name, query_gate=True))
            control_rows.append(evaluate_ranking(metadata, sim, descriptor, "gallery_only_filter", threshold_name, gallery_gate=True))
            control_rows.append(evaluate_ranking(metadata, sim, descriptor, "query_and_gallery_filter", threshold_name, query_gate=True, gallery_gate=True))
            for top_k in [5, 10]:
                for strictness in STRICTNESS:
                    metrics, assignments = evaluate_pair_pruning(metadata, sim, descriptor, threshold_name, top_k, strictness)
                    control_rows.append(metrics)
                    if descriptor == "megadescriptor" and threshold_name == "medium_or_higher" and top_k == 10 and strictness == "standard":
                        assignment_rows.extend(assignments)
            for alpha in RERANKING_ALPHAS:
                adjusted = adjusted_score_matrix(sim, metadata, alpha)
                metrics = evaluate_ranking(metadata, sim, descriptor, "descriptor_pf_eri_reranking_diagnostic", threshold_name, adjusted_scores=adjusted)
                metrics["alpha"] = alpha
                metrics["interpretation"] = "diagnostic reranking baseline only; not final PF-ERI safety score"
                control_rows.append(metrics)

    query_table = pd.DataFrame(query_rows)
    false_diag = false_top1_diagnosis(query_table)
    topk = pd.DataFrame(topk_rows)
    control = pd.DataFrame(control_rows)
    assignments = pd.DataFrame(assignment_rows)
    rules = rules_frame()
    readiness = readiness_frame(control, false_diag)

    query_table.to_csv(QUERY_FAILURE_CSV, index=False)
    false_diag.to_csv(FALSE_TOP1_CSV, index=False)
    topk.to_csv(TOPK_BURDEN_CSV, index=False)
    control.to_csv(CONTROL_COMPARISON_CSV, index=False)
    rules.to_csv(RULES_CSV, index=False)
    assignments.to_csv(ASSIGNMENT_CSV, index=False)
    readiness.to_csv(READINESS_CSV, index=False)
    make_figures(query_table, topk, control)

    dominant = (
        false_diag[(false_diag["descriptor"] == "megadescriptor") & (false_diag["summary_type"] == "query_limiting_factor")]
        .sort_values("false_top1_count", ascending=False)
        .head(3)
    )
    best_pair = control[control["control_mode"] == "pair_level_topk_review_pruning"].sort_values(
        ["false_top1_rate", "query_coverage"], ascending=[True, False]
    ).head(1)
    print("PASS: Phase 8 Slice 2B full retrieval failure diagnosis complete")
    print(f"query_count: {len(metadata)}")
    print("descriptors_analyzed: megadescriptor, resnet50")
    print("dominant_megadescriptor_false_top1_query_factors:")
    for _, row in dominant.iterrows():
        print(f"  {row['summary_value']}: count={int(row['false_top1_count'])}, share={row['false_top1_share_among_false']:.4f}")
    if not best_pair.empty:
        row = best_pair.iloc[0]
        print(
            "best_pair_level_mode: "
            f"{row['descriptor']} / {row['threshold']} / top_k={row['top_k']} / {row['strictness']} "
            f"false_top1={row['false_top1_rate']:.4f}, query_coverage={row['query_coverage']:.4f}, "
            f"review_burden_reduction={row['review_burden_reduction']:.4f}"
        )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--megadescriptor-embeddings-csv", type=Path, default=MEGA_EMBEDDINGS_CSV)
    parser.add_argument("--resnet50-embeddings-csv", type=Path, default=RESNET_EMBEDDINGS_CSV)
    parser.add_argument("--identity-csv", type=Path, default=IDENTITY_CSV)
    parser.add_argument("--annotation-csv", type=Path, default=ANNOTATION_CSV)
    return parser.parse_args()


def main() -> int:
    return run(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
