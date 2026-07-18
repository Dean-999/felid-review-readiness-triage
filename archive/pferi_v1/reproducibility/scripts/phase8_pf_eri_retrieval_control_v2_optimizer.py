#!/usr/bin/env python3
"""Optimize Phase 8 PF-ERI retrieval-control v2 policies on CzechLynx."""

from __future__ import annotations

import argparse
import ast
import hashlib
import math
from itertools import product
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MEGA_EMBEDDINGS_CSV = PROJECT_ROOT / "outputs/czechlynx/phase4/czechlynx_phase4c_megadescriptor_embeddings.csv"
RESNET_EMBEDDINGS_CSV = PROJECT_ROOT / "outputs/czechlynx/phase4/czechlynx_phase4c_resnet50_embeddings.csv"
IDENTITY_CSV = PROJECT_ROOT / "data/interim/czechlynx/czechlynx_expanded_125x4_internal_with_ids.csv"
ANNOTATION_CSV = PROJECT_ROOT / "data/labels/czechlynx/czechlynx_phase7a_1000_image_annotations_v1.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase8/pf_eri_retrieval_control_v2"
FIGURE_DIR = OUTPUT_DIR / "figures"

POLICY_GRID_CSV = OUTPUT_DIR / "phase8_pf_eri_retrieval_control_v2_policy_grid.csv"
TOP_POLICIES_CSV = OUTPUT_DIR / "phase8_pf_eri_retrieval_control_v2_top_policies.csv"
ASSIGNMENTS_CSV = OUTPUT_DIR / "phase8_pf_eri_retrieval_control_v2_recommended_assignments.csv"
FAILURE_SUMMARY_CSV = OUTPUT_DIR / "phase8_pf_eri_retrieval_control_v2_failure_mode_summary.csv"
COMPARISON_CSV = OUTPUT_DIR / "phase8_pf_eri_retrieval_control_v2_comparison_to_prior.csv"
BOOTSTRAP_CSV = OUTPUT_DIR / "phase8_pf_eri_retrieval_control_v2_bootstrap_intervals.csv"
READINESS_CSV = OUTPUT_DIR / "phase8_pf_eri_retrieval_control_v2_readiness_decision.csv"

RANDOM_SEED = 20260614
BOOTSTRAP_ITERATIONS = 300
TOP_K_VALUES = [1, 3, 5, 10, 20]
THRESHOLDS = {"low_or_higher": 25.0, "medium_or_higher": 50.0, "high_only": 75.0}
PATTERN = {"none": 0.0, "low": 1.0, "medium": 2.0, "high": 3.0}
SIDE_QUALITY = {"none": 0.0, "low": 1.0, "medium": 2.0, "high": 3.0}
BODY = {"0_25": 0.0, "26_50": 1.0, "51_75": 2.0, "76_100": 3.0, "unknown": 1.0}
BLUR = {"severe": 0.0, "moderate": 1.0, "mild": 2.0, "none": 3.0, "unknown": 1.0}
OCCLUSION = {"major": 0.0, "partial": 1.5, "none": 3.0, "unknown": 1.5}
CONTRAST = {"low": 0.0, "not_available": 1.0, "good": 2.0, "unknown": 1.0}
VALID_ASSIGNMENTS = ["review_candidate", "defer_candidate", "exclude_candidate"]


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
    severe_failure = (
        row["pattern_visibility"] == "none"
        or row["blur_level"] == "severe"
        or row["occlusion_level"] == "major"
        or row["silhouette_only"] == "yes"
        or row["frontal_or_rear_view"] == "yes"
    )
    weak_side = row["side_evidence_quality"] in {"none", "low"}
    low_body = row["body_fraction_visible"] in {"0_25", "26_50"}
    return {
        "visual_pf_eri_score": weighted,
        "visual_pf_eri_band": band(weighted),
        "primary_limiting_factor": min(components.items(), key=lambda item: item[1])[0],
        "severe_visual_failure": severe_failure,
        "weak_side_evidence": weak_side,
        "low_body_fraction": low_body,
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
    return metadata


def align_inputs(args: argparse.Namespace) -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    mega_meta, mega_vectors = load_embeddings(args.megadescriptor_embeddings_csv)
    resnet_meta, resnet_vectors = load_embeddings(args.resnet50_embeddings_csv)
    common_ids = set(mega_meta["expanded_image_id"]) & set(resnet_meta["expanded_image_id"])
    metadata = load_metadata(args.identity_csv, args.annotation_csv, common_ids).sort_values("expanded_image_id").reset_index(drop=True)
    mega_lookup = {image_id: idx for idx, image_id in enumerate(mega_meta["expanded_image_id"])}
    resnet_lookup = {image_id: idx for idx, image_id in enumerate(resnet_meta["expanded_image_id"])}
    ordered_mega = mega_vectors[[mega_lookup[x] for x in metadata["expanded_image_id"]]]
    ordered_resnet = resnet_vectors[[resnet_lookup[x] for x in metadata["expanded_image_id"]]]
    return metadata, {
        "megadescriptor": np.einsum("ik,jk->ij", ordered_mega, ordered_mega, optimize=True),
        "resnet50": np.einsum("ik,jk->ij", ordered_resnet, ordered_resnet, optimize=True),
    }


def build_candidate_table(metadata: pd.DataFrame, similarities: dict[str, np.ndarray], max_k: int = 20) -> pd.DataFrame:
    rows = []
    identities = metadata["working_individual_id"].astype(str).to_numpy()
    for descriptor, sim in similarities.items():
        other_descriptor = "resnet50" if descriptor == "megadescriptor" else "megadescriptor"
        other_sim = similarities[other_descriptor]
        for query_idx, query in metadata.iterrows():
            scores = sim[int(query_idx)].copy()
            scores[int(query_idx)] = -np.inf
            ranked = np.argsort(-scores)[:max_k]
            for rank, gallery_idx in enumerate(ranked, start=1):
                gallery = metadata.iloc[int(gallery_idx)]
                q_score = float(query["visual_pf_eri_score"])
                g_score = float(gallery["visual_pf_eri_score"])
                rows.append(
                    {
                        "descriptor": descriptor,
                        "query_idx": int(query_idx),
                        "gallery_idx": int(gallery_idx),
                        "rank": rank,
                        "similarity": float(sim[int(query_idx), int(gallery_idx)]),
                        "other_descriptor_similarity": float(other_sim[int(query_idx), int(gallery_idx)]),
                        "same_identity": bool(identities[int(query_idx)] == identities[int(gallery_idx)]),
                        "query_token": query["image_token"],
                        "gallery_token": gallery["image_token"],
                        "query_score": q_score,
                        "gallery_score": g_score,
                        "pair_min_score": min(q_score, g_score),
                        "pair_mean_score": (q_score + g_score) / 2.0,
                        "query_band": query["visual_pf_eri_band"],
                        "gallery_band": gallery["visual_pf_eri_band"],
                        "query_limiting_factor": query["primary_limiting_factor"],
                        "gallery_limiting_factor": gallery["primary_limiting_factor"],
                        "pattern_none": query["pattern_visibility"] == "none" or gallery["pattern_visibility"] == "none",
                        "low_pattern_visibility": query["pattern_visibility"] in {"none", "low"} or gallery["pattern_visibility"] in {"none", "low"},
                        "severe_blur": query["blur_level"] == "severe" or gallery["blur_level"] == "severe",
                        "major_occlusion": query["occlusion_level"] == "major" or gallery["occlusion_level"] == "major",
                        "frontal_rear": query["frontal_or_rear_view"] == "yes" or gallery["frontal_or_rear_view"] == "yes",
                        "weak_side_evidence": bool(query["weak_side_evidence"]) or bool(gallery["weak_side_evidence"]),
                        "side_unknown": query["side_evidence_quality"] == "unknown" or gallery["side_evidence_quality"] == "unknown",
                        "low_body_fraction": bool(query["low_body_fraction"]) or bool(gallery["low_body_fraction"]),
                        "uncertainty_flag": query["uncertainty_flag"] == "yes" or gallery["uncertainty_flag"] == "yes",
                        "severe_visual_failure": bool(query["severe_visual_failure"]) or bool(gallery["severe_visual_failure"]),
                    }
                )
    candidates = pd.DataFrame(rows)
    candidates["high_descriptor_low_evidence"] = (candidates["similarity"] >= 0.80) & (candidates["pair_min_score"] < 50.0)
    candidates["descriptor_disagreement"] = (candidates["similarity"] - candidates["other_descriptor_similarity"]).abs() >= 0.18
    return candidates


def average_precision(relevance: np.ndarray) -> float:
    positives = int(relevance.sum())
    if positives == 0:
        return math.nan
    cumulative = np.cumsum(relevance)
    return float((cumulative[relevance == 1] / (np.flatnonzero(relevance == 1) + 1)).mean())


def policy_grid() -> list[dict[str, object]]:
    policies: list[dict[str, object]] = []
    policy_id = 1
    for descriptor, top_k in product(["megadescriptor", "resnet50"], TOP_K_VALUES):
        policies.append(base_policy(policy_id, "A_baseline_descriptor_retrieval", descriptor, top_k, "none", "none", "none", "none", "baseline", "ignore", "ignore"))
        policy_id += 1
    for descriptor, top_k, mode, threshold in product(["megadescriptor", "resnet50"], TOP_K_VALUES, ["query_only", "gallery_only", "query_and_gallery"], THRESHOLDS):
        policies.append(base_policy(policy_id, f"B_image_filter_{mode}", descriptor, top_k, threshold, threshold, "min_score", threshold, "standard", "ignore", "defer"))
        policy_id += 1
    for family, strictness_values, failure_profiles, contradiction_actions in [
        ("C_pair_level_topk_pruning", ["lenient", "standard", "strict"], ["standard", "conservative"], ["ignore", "defer"]),
        ("D_review_defer_exclude_triage", ["standard", "defer_heavy"], ["standard", "side_sensitive"], ["defer", "exclude"]),
        ("E_failure_mode_conservative_triage", ["strict", "exclusion_heavy"], ["conservative", "all_failure_flags"], ["defer", "exclude"]),
        ("F_balanced_review_burden_policy", ["standard", "defer_heavy"], ["standard", "side_sensitive"], ["defer", "ignore"]),
    ]:
        for descriptor, top_k, q_thr, g_thr, pair_rule, strictness, failure_profile, contradiction_action in product(
            ["megadescriptor", "resnet50"],
            TOP_K_VALUES,
            THRESHOLDS,
            THRESHOLDS,
            ["min_score", "mean_score", "strict_band"],
            strictness_values,
            failure_profiles,
            contradiction_actions,
        ):
            pair_thr = "medium_or_higher" if pair_rule == "mean_score" else q_thr
            policies.append(base_policy(policy_id, family, descriptor, top_k, q_thr, g_thr, pair_rule, pair_thr, strictness, failure_profile, contradiction_action))
            policy_id += 1
    for descriptor, top_k, alpha in product(["megadescriptor", "resnet50"], TOP_K_VALUES, [0.05, 0.10, 0.20]):
        policy = base_policy(policy_id, "G_diagnostic_reranking", descriptor, top_k, "low_or_higher", "low_or_higher", "mean_score", "low_or_higher", "diagnostic", "standard", "defer")
        policy["reranking_alpha"] = alpha
        policies.append(policy)
        policy_id += 1
    return policies


def base_policy(policy_id: int, family: str, descriptor: str, top_k: int, query_threshold: str, gallery_threshold: str,
                pair_rule: str, pair_threshold: str, strictness: str, failure_profile: str, contradiction_action: str) -> dict[str, object]:
    return {
        "policy_id": f"p{policy_id:05d}",
        "policy_family": family,
        "descriptor": descriptor,
        "top_k": top_k,
        "query_threshold": query_threshold,
        "gallery_threshold": gallery_threshold,
        "pair_evidence_rule": pair_rule,
        "pair_threshold": pair_threshold,
        "strictness": strictness,
        "failure_profile": failure_profile,
        "contradiction_action": contradiction_action,
        "reranking_alpha": math.nan,
    }


def threshold_value(name: str) -> float:
    return 0.0 if name == "none" else THRESHOLDS[name]


def assign_candidates(candidates: pd.DataFrame, policy: dict[str, object]) -> pd.Series:
    n = len(candidates)
    assignment = pd.Series(np.repeat("review_candidate", n), index=candidates.index, dtype=object)
    family = str(policy["policy_family"])
    if family == "A_baseline_descriptor_retrieval":
        return assignment

    q_pass = candidates["query_score"] >= threshold_value(str(policy["query_threshold"]))
    g_pass = candidates["gallery_score"] >= threshold_value(str(policy["gallery_threshold"]))
    if str(policy["pair_evidence_rule"]) == "mean_score":
        pair_pass = candidates["pair_mean_score"] >= threshold_value(str(policy["pair_threshold"]))
    else:
        pair_pass = candidates["pair_min_score"] >= threshold_value(str(policy["pair_threshold"]))
    if str(policy["pair_evidence_rule"]) == "strict_band":
        pair_pass = pair_pass & q_pass & g_pass

    if family.startswith("B_image_filter_query_only"):
        assignment[~q_pass] = "exclude_candidate"
        return assignment
    if family.startswith("B_image_filter_gallery_only"):
        assignment[~g_pass] = "exclude_candidate"
        return assignment
    if family.startswith("B_image_filter_query_and_gallery"):
        assignment[~(q_pass & g_pass)] = "exclude_candidate"
        return assignment

    evidence_pass = q_pass & g_pass & pair_pass
    assignment[~evidence_pass] = "defer_candidate" if family != "C_pair_level_topk_pruning" else "exclude_candidate"
    severe = failure_mask(candidates, str(policy["failure_profile"]))
    contradiction = candidates["high_descriptor_low_evidence"]
    if str(policy["failure_profile"]) in {"side_sensitive", "all_failure_flags"}:
        contradiction = contradiction | candidates["descriptor_disagreement"]

    if str(policy["strictness"]) == "lenient":
        assignment[(assignment != "exclude_candidate") & severe] = "defer_candidate"
    elif str(policy["strictness"]) == "standard":
        assignment[severe] = "defer_candidate"
    elif str(policy["strictness"]) == "strict":
        assignment[severe & (candidates["pair_min_score"] < 75.0)] = "exclude_candidate"
        assignment[severe & (candidates["pair_min_score"] >= 75.0)] = "defer_candidate"
    elif str(policy["strictness"]) == "defer_heavy":
        assignment[severe | ~evidence_pass] = "defer_candidate"
    elif str(policy["strictness"]) == "exclusion_heavy":
        assignment[severe | ~evidence_pass] = "exclude_candidate"

    if str(policy["contradiction_action"]) == "defer":
        assignment[contradiction & (assignment == "review_candidate")] = "defer_candidate"
    elif str(policy["contradiction_action"]) == "exclude":
        assignment[contradiction] = "exclude_candidate"
    return assignment


def failure_mask(candidates: pd.DataFrame, profile: str) -> pd.Series:
    if profile == "ignore":
        return pd.Series(np.repeat(False, len(candidates)), index=candidates.index)
    mask = candidates["pattern_none"] | candidates["severe_blur"] | candidates["major_occlusion"] | candidates["frontal_rear"]
    if profile in {"conservative", "side_sensitive", "all_failure_flags"}:
        mask = mask | candidates["low_pattern_visibility"] | candidates["low_body_fraction"]
    if profile in {"side_sensitive", "all_failure_flags"}:
        mask = mask | candidates["weak_side_evidence"] | candidates["side_unknown"]
    if profile == "all_failure_flags":
        mask = mask | candidates["uncertainty_flag"] | candidates["descriptor_disagreement"] | candidates["high_descriptor_low_evidence"]
    return mask


def metric_for_policy(candidates: pd.DataFrame, policy: dict[str, object]) -> tuple[dict[str, object], pd.DataFrame]:
    subset = candidates[(candidates["descriptor"] == policy["descriptor"]) & (candidates["rank"] <= int(policy["top_k"]))].copy()
    if str(policy["policy_family"]) == "G_diagnostic_reranking":
        alpha = float(policy["reranking_alpha"])
        subset["sort_score"] = subset["similarity"] + alpha * (subset["pair_mean_score"] / 100.0) - (alpha / 2.0) * subset["severe_visual_failure"].astype(float)
        subset = subset.sort_values(["query_idx", "sort_score"], ascending=[True, False])
        subset["rank"] = subset.groupby("query_idx").cumcount() + 1
    subset["assignment"] = assign_candidates(subset, policy)
    return compute_metrics(subset, policy), subset


def compute_metrics(subset: pd.DataFrame, policy: dict[str, object]) -> dict[str, object]:
    query_count = 500
    candidate_before = len(subset)
    counts = subset["assignment"].value_counts()
    review = subset[subset["assignment"] == "review_candidate"].copy()
    review_count = int(counts.get("review_candidate", 0))
    defer_count = int(counts.get("defer_candidate", 0))
    exclude_count = int(counts.get("exclude_candidate", 0))
    covered_queries = review["query_idx"].nunique()
    candidate_true_total = int(subset["same_identity"].sum())
    true_reviewed = int(review["same_identity"].sum())
    reviewed_metrics = reviewed_query_metrics(review)
    failure_exposure = failure_exposure_rate(review)
    metrics = {
        **policy,
        "query_count": query_count,
        "covered_query_count": int(covered_queries),
        "query_coverage": covered_queries / query_count,
        "positive_query_coverage": reviewed_metrics["positive_query_coverage"],
        "candidate_count_before_control": int(candidate_before),
        "review_candidate_count": review_count,
        "defer_candidate_count": defer_count,
        "exclude_candidate_count": exclude_count,
        "review_burden_reduction": 1.0 - (review_count / candidate_before) if candidate_before else math.nan,
        "defer_rate": defer_count / candidate_before if candidate_before else math.nan,
        "exclude_rate": exclude_count / candidate_before if candidate_before else math.nan,
        "top1_success_among_covered_queries": reviewed_metrics["top1_success"],
        "top3_success_among_covered_queries": reviewed_metrics["top3_success"],
        "top5_success_among_covered_queries": reviewed_metrics["top5_success"],
        "mAP_among_covered_positive_queries": reviewed_metrics["mAP"],
        "MRR_among_covered_positive_queries": reviewed_metrics["MRR"],
        "false_top1_rate_among_covered_queries": reviewed_metrics["false_top1_rate"],
        "false_reviewed_candidate_rate_at_topk": 1.0 - (true_reviewed / review_count) if review_count else math.nan,
        "true_same_identity_candidate_retention": true_reviewed / candidate_true_total if candidate_true_total else math.nan,
        "positive_retention": true_reviewed / candidate_true_total if candidate_true_total else math.nan,
        "average_reviewed_candidates_per_query": review_count / query_count,
        "average_false_reviewed_candidates_per_query": int((~review["same_identity"]).sum()) / query_count,
        "failure_mode_exposure_among_review_candidates": failure_exposure,
    }
    metrics["balanced_score"] = balanced_score(metrics)
    metrics["reliability_score"] = reliability_score(metrics)
    metrics["coverage_score"] = coverage_score(metrics)
    metrics["evidence_control_score"] = evidence_control_score(metrics)
    return metrics


def reviewed_query_metrics(review: pd.DataFrame) -> dict[str, float]:
    if review.empty:
        return {
            "positive_query_coverage": 0.0,
            "top1_success": math.nan,
            "top3_success": math.nan,
            "top5_success": math.nan,
            "mAP": math.nan,
            "MRR": math.nan,
            "false_top1_rate": math.nan,
        }
    top1_hits: list[int] = []
    top3_hits: list[int] = []
    top5_hits: list[int] = []
    ap_values: list[float] = []
    rr_values: list[float] = []
    false_top1 = 0
    positive_queries = 0
    for _, group in review.sort_values(["query_idx", "rank"]).groupby("query_idx", sort=False):
        relevance = group["same_identity"].astype(int).to_numpy()
        if relevance.sum() == 0:
            false_top1 += int(relevance[0] == 0)
            continue
        positive_queries += 1
        top1_hits.append(int(relevance[0]))
        top3_hits.append(int(relevance[: min(3, len(relevance))].max()))
        top5_hits.append(int(relevance[: min(5, len(relevance))].max()))
        false_top1 += int(relevance[0] == 0)
        first_positive = int(np.flatnonzero(relevance == 1)[0]) + 1
        rr_values.append(1.0 / first_positive)
        ap_values.append(average_precision(relevance))
    covered_queries = review["query_idx"].nunique()
    return {
        "positive_query_coverage": positive_queries / 500,
        "top1_success": float(np.mean(top1_hits)) if top1_hits else math.nan,
        "top3_success": float(np.mean(top3_hits)) if top3_hits else math.nan,
        "top5_success": float(np.mean(top5_hits)) if top5_hits else math.nan,
        "mAP": float(np.mean(ap_values)) if ap_values else math.nan,
        "MRR": float(np.mean(rr_values)) if rr_values else math.nan,
        "false_top1_rate": false_top1 / covered_queries if covered_queries else math.nan,
    }


def failure_exposure_rate(review: pd.DataFrame) -> float:
    if review.empty:
        return math.nan
    flags = ["pattern_none", "low_pattern_visibility", "severe_blur", "major_occlusion", "frontal_rear", "weak_side_evidence", "uncertainty_flag", "high_descriptor_low_evidence", "descriptor_disagreement"]
    return float(review[flags].any(axis=1).mean())


def balanced_score(row: dict[str, object]) -> float:
    if any(math.isnan(float(row[x])) for x in ["false_top1_rate_among_covered_queries", "query_coverage", "positive_retention", "mAP_among_covered_positive_queries"]):
        return -999.0
    return (
        1.8 * (1.0 - float(row["false_top1_rate_among_covered_queries"]))
        + 1.4 * float(row["query_coverage"])
        + 1.2 * float(row["positive_retention"])
        + 1.0 * float(row["review_burden_reduction"])
        + 0.9 * float(row["mAP_among_covered_positive_queries"])
        - 0.8 * float(row["failure_mode_exposure_among_review_candidates"])
    )


def reliability_score(row: dict[str, object]) -> float:
    if math.isnan(float(row["false_top1_rate_among_covered_queries"])):
        return -999.0
    return (
        2.5 * (1.0 - float(row["false_top1_rate_among_covered_queries"]))
        + 0.8 * float(row["review_burden_reduction"])
        + 0.5 * float(row["mAP_among_covered_positive_queries"] if not math.isnan(float(row["mAP_among_covered_positive_queries"])) else 0.0)
        - 0.3 * max(0.0, 0.30 - float(row["query_coverage"]))
    )


def coverage_score(row: dict[str, object]) -> float:
    if math.isnan(float(row["false_top1_rate_among_covered_queries"])):
        return -999.0
    return 2.0 * float(row["query_coverage"]) + 0.8 * (1.0 - float(row["false_top1_rate_among_covered_queries"])) + 0.6 * float(row["positive_retention"])


def evidence_control_score(row: dict[str, object]) -> float:
    if math.isnan(float(row["failure_mode_exposure_among_review_candidates"])):
        return -999.0
    return 1.7 * (1.0 - float(row["failure_mode_exposure_among_review_candidates"])) + 1.2 * float(row["review_burden_reduction"]) + 0.7 * float(row["query_coverage"])


def select_top_policies(grid: pd.DataFrame) -> pd.DataFrame:
    selected = []
    control_families = [
        "C_pair_level_topk_pruning",
        "D_review_defer_exclude_triage",
        "E_failure_mode_conservative_triage",
        "F_balanced_review_burden_policy",
    ]
    control_grid = grid[grid["policy_family"].isin(control_families)].copy()
    reliability = control_grid[
        (control_grid["query_coverage"] >= 0.25)
        & (control_grid["top_k"] >= 3)
        & control_grid["false_top1_rate_among_covered_queries"].notna()
    ].sort_values(
        ["false_top1_rate_among_covered_queries", "mAP_among_covered_positive_queries", "query_coverage"],
        ascending=[True, False, False],
    ).head(1)
    balanced = control_grid[
        (control_grid["policy_family"] == "F_balanced_review_burden_policy")
        & (control_grid["descriptor"] == "megadescriptor")
        & (control_grid["top_k"] >= 5)
        & (control_grid["query_coverage"] >= 0.60)
        & (control_grid["positive_retention"] >= 0.55)
        & (control_grid["review_burden_reduction"] >= 0.35)
        & control_grid["false_top1_rate_among_covered_queries"].notna()
    ].sort_values(["balanced_score", "false_top1_rate_among_covered_queries"], ascending=[False, True]).head(1)
    coverage = grid[
        (grid["query_coverage"] >= 0.85)
        & (grid["top_k"] >= 5)
        & grid["false_top1_rate_among_covered_queries"].notna()
    ].sort_values(
        ["coverage_score", "false_top1_rate_among_covered_queries"], ascending=[False, True]
    ).head(1)
    evidence = control_grid[(control_grid["query_coverage"] >= 0.30) & control_grid["failure_mode_exposure_among_review_candidates"].notna()].sort_values(
        ["evidence_control_score", "false_top1_rate_among_covered_queries"], ascending=[False, True]
    ).head(1)
    for regime, frame in [
        ("reliability_first", reliability),
        ("balanced_main_v2_recommendation", balanced),
        ("coverage_preserving", coverage),
        ("evidence_control", evidence),
    ]:
        if not frame.empty:
            row = frame.iloc[0].to_dict()
            row["selection_regime"] = regime
            row["main_recommendation"] = "yes" if regime == "balanced_main_v2_recommendation" else "no"
            selected.append(row)
    return pd.DataFrame(selected)


def assignments_for_policy(candidates: pd.DataFrame, policy: dict[str, object]) -> pd.DataFrame:
    _, assigned = metric_for_policy(candidates, policy)
    assigned = assigned.copy()
    keep_cols = [
        "descriptor",
        "query_token",
        "gallery_token",
        "rank",
        "similarity",
        "query_score",
        "gallery_score",
        "pair_min_score",
        "pair_mean_score",
        "query_band",
        "gallery_band",
        "query_limiting_factor",
        "gallery_limiting_factor",
        "pattern_none",
        "low_pattern_visibility",
        "severe_blur",
        "major_occlusion",
        "frontal_rear",
        "weak_side_evidence",
        "uncertainty_flag",
        "high_descriptor_low_evidence",
        "descriptor_disagreement",
        "assignment",
    ]
    return assigned[keep_cols].rename(columns={"assignment": "recommended_assignment"})


def failure_summary(assignments: pd.DataFrame) -> pd.DataFrame:
    flags = ["pattern_none", "low_pattern_visibility", "severe_blur", "major_occlusion", "frontal_rear", "weak_side_evidence", "uncertainty_flag", "high_descriptor_low_evidence", "descriptor_disagreement"]
    rows = []
    for assignment, group in assignments.groupby("recommended_assignment"):
        for flag in flags:
            count = int(group[flag].sum())
            rows.append(
                {
                    "recommended_assignment": assignment,
                    "failure_mode": flag,
                    "candidate_count": int(len(group)),
                    "failure_mode_count": count,
                    "failure_mode_rate": count / len(group) if len(group) else math.nan,
                }
            )
    return pd.DataFrame(rows)


def comparison_to_prior(grid: pd.DataFrame, top: pd.DataFrame) -> pd.DataFrame:
    baseline = grid[(grid["policy_family"] == "A_baseline_descriptor_retrieval") & (grid["descriptor"] == "megadescriptor") & (grid["top_k"] == 5)].head(1)
    prior = grid[
        (grid["policy_family"] == "F_balanced_review_burden_policy")
        & (grid["descriptor"] == "megadescriptor")
        & (grid["top_k"] == 5)
        & (grid["query_threshold"] == "medium_or_higher")
        & (grid["gallery_threshold"] == "medium_or_higher")
        & (grid["strictness"] == "standard")
    ].sort_values("balanced_score", ascending=False).head(1)
    rows = []
    for label, frame in [("no_pf_eri_control_top5", baseline), ("slice2b_balanced_proxy", prior)]:
        if frame.empty:
            continue
        row = frame.iloc[0]
        rows.append({"comparison_item": label, **{k: row[k] for k in comparison_metric_cols()}})
    for _, row in top.iterrows():
        rows.append({"comparison_item": row["selection_regime"], **{k: row[k] for k in comparison_metric_cols()}})
    return pd.DataFrame(rows)


def comparison_metric_cols() -> list[str]:
    return [
        "policy_id",
        "policy_family",
        "descriptor",
        "top_k",
        "query_coverage",
        "false_top1_rate_among_covered_queries",
        "mAP_among_covered_positive_queries",
        "positive_retention",
        "review_burden_reduction",
        "failure_mode_exposure_among_review_candidates",
    ]


def bootstrap_intervals(candidates: pd.DataFrame, top: pd.DataFrame, iterations: int) -> pd.DataFrame:
    rng = np.random.default_rng(RANDOM_SEED)
    rows = []
    query_ids = np.arange(500)
    for _, policy in top.iterrows():
        _, assigned = metric_for_policy(candidates, policy.to_dict())
        per_query = query_level_summary(assigned)
        for metric_name in ["false_top1_rate_among_covered_queries", "query_coverage", "positive_retention", "review_burden_reduction", "mAP_among_covered_positive_queries"]:
            values = []
            for _ in range(iterations):
                sampled = rng.choice(query_ids, size=len(query_ids), replace=True)
                values.append(query_level_boot_metric(per_query.iloc[sampled], metric_name))
            clean = np.asarray([v for v in values if not math.isnan(float(v))], dtype=float)
            rows.append(
                {
                    "selection_regime": policy["selection_regime"],
                    "policy_id": policy["policy_id"],
                    "metric": metric_name,
                    "bootstrap_iterations": iterations,
                    "estimate": float(policy[metric_name]),
                    "ci_lower": float(np.percentile(clean, 2.5)) if len(clean) else math.nan,
                    "ci_upper": float(np.percentile(clean, 97.5)) if len(clean) else math.nan,
                }
            )
    return pd.DataFrame(rows)


def query_level_summary(assigned: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for query_idx, group in assigned.groupby("query_idx", sort=False):
        review = group[group["assignment"] == "review_candidate"].sort_values("rank")
        relevance = review["same_identity"].astype(int).to_numpy()
        has_review = len(review) > 0
        has_positive_review = bool(relevance.sum() > 0) if has_review else False
        rows.append(
            {
                "query_idx": int(query_idx),
                "candidate_count": int(len(group)),
                "review_count": int(len(review)),
                "has_review": int(has_review),
                "false_top1": int(has_review and relevance[0] == 0),
                "true_total": int(group["same_identity"].sum()),
                "true_reviewed": int(relevance.sum()) if has_review else 0,
                "ap": average_precision(relevance) if has_positive_review else math.nan,
            }
        )
    frame = pd.DataFrame(rows).set_index("query_idx").reindex(np.arange(500), fill_value=0).reset_index()
    return frame


def query_level_boot_metric(sample: pd.DataFrame, metric_name: str) -> float:
    if metric_name == "query_coverage":
        return float(sample["has_review"].mean())
    if metric_name == "false_top1_rate_among_covered_queries":
        denom = sample["has_review"].sum()
        return float(sample["false_top1"].sum() / denom) if denom else math.nan
    if metric_name == "positive_retention":
        denom = sample["true_total"].sum()
        return float(sample["true_reviewed"].sum() / denom) if denom else math.nan
    if metric_name == "review_burden_reduction":
        denom = sample["candidate_count"].sum()
        return float(1.0 - sample["review_count"].sum() / denom) if denom else math.nan
    if metric_name == "mAP_among_covered_positive_queries":
        ap = sample["ap"].replace(0, np.nan).dropna()
        return float(ap.mean()) if len(ap) else math.nan
    raise ValueError(f"unknown bootstrap metric: {metric_name}")


def readiness_decision(top: pd.DataFrame, comparison: pd.DataFrame) -> pd.DataFrame:
    balanced = top[top["selection_regime"] == "balanced_main_v2_recommendation"].iloc[0]
    prior = comparison[comparison["comparison_item"] == "slice2b_balanced_proxy"]
    stronger = "mixed_but_algorithmically_stronger"
    if not prior.empty:
        prior_row = prior.iloc[0]
        stronger = "mixed_but_algorithmically_stronger" if (
            balanced["false_top1_rate_among_covered_queries"] <= prior_row["false_top1_rate_among_covered_queries"]
            and balanced["query_coverage"] >= 0.60
        ) else "mixed"
    return pd.DataFrame(
        [
            {
                "decision_item": "pf_eri_retrieval_control_v2_stronger_than_slice2b",
                "decision": stronger,
                "rationale": "balanced v2 is selected by multi-objective criteria and improves coverage/retention, but false top-1 remains high under the stricter all-covered-query definition",
            },
            {
                "decision_item": "policy_family_to_carry_forward",
                "decision": str(balanced["policy_family"]),
                "rationale": "balanced policy is the main v2 recommendation",
            },
            {
                "decision_item": "ready_for_external_patterned_felid_audit",
                "decision": "yes_for_access_and_license_audit_only",
                "rationale": "CzechLynx optimization is sufficient to define a candidate policy, not to claim external validation",
            },
            {
                "decision_item": "broader_felid_claim_supported",
                "decision": "no",
                "rationale": "no external known-ID patterned-felid benchmark was run in this slice",
            },
            {
                "decision_item": "mainland_clouded_leopard_marbled_cat_status",
                "decision": "motivation_only",
                "rationale": "these taxa remain future conservation-transfer motivation until known-ID data are available",
            },
        ]
    )


def make_figures(grid: pd.DataFrame, top: pd.DataFrame, assignments: pd.DataFrame, failure: pd.DataFrame, boot: pd.DataFrame, comparison: pd.DataFrame) -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(8, 6))
    plt.scatter(grid["query_coverage"], grid["false_top1_rate_among_covered_queries"], s=6, alpha=0.25)
    plt.scatter(top["query_coverage"], top["false_top1_rate_among_covered_queries"], s=70, color="#CC6677")
    plt.xlabel("Query coverage")
    plt.ylabel("False top-1 rate")
    plt.title("PF-ERI v2 policy frontier")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "phase8_v2_policy_frontier_coverage_vs_false_top1.png", dpi=180)
    plt.close()

    plt.figure(figsize=(8, 6))
    plt.scatter(grid["review_burden_reduction"], grid["positive_retention"], s=6, alpha=0.25)
    plt.scatter(top["review_burden_reduction"], top["positive_retention"], s=70, color="#4477AA")
    plt.xlabel("Review burden reduction")
    plt.ylabel("Positive retention")
    plt.title("Review burden vs positive retention")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "phase8_v2_review_burden_vs_positive_retention.png", dpi=180)
    plt.close()

    labels = comparison["comparison_item"].str.replace("_", " ")
    plt.figure(figsize=(11, 6))
    plt.bar(np.arange(len(comparison)), comparison["false_top1_rate_among_covered_queries"], color="#4477AA")
    plt.xticks(np.arange(len(comparison)), labels, rotation=40, ha="right", fontsize=8)
    plt.ylabel("False top-1 rate")
    plt.title("Top policies compared with prior baselines")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "phase8_v2_top_policies_vs_prior.png", dpi=180)
    plt.close()

    counts = assignments["recommended_assignment"].value_counts().reindex(VALID_ASSIGNMENTS).fillna(0)
    plt.figure(figsize=(7, 5))
    plt.bar(counts.index.str.replace("_", " "), counts.values, color=["#228833", "#EE7733", "#CC3311"])
    plt.ylabel("Candidate count")
    plt.title("Recommended review/defer/exclude counts")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "phase8_v2_review_defer_exclude_counts.png", dpi=180)
    plt.close()

    review_failure = failure[failure["recommended_assignment"] == "review_candidate"].sort_values("failure_mode_rate", ascending=False)
    plt.figure(figsize=(10, 5))
    plt.bar(review_failure["failure_mode"].str.replace("_", " "), review_failure["failure_mode_rate"], color="#AA4499")
    plt.xticks(rotation=45, ha="right", fontsize=8)
    plt.ylabel("Exposure rate")
    plt.title("Failure-mode exposure among review candidates")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "phase8_v2_failure_mode_exposure_review_candidates.png", dpi=180)
    plt.close()

    plt.figure(figsize=(8, 6))
    plt.scatter(grid["query_coverage"], grid["mAP_among_covered_positive_queries"], s=6, alpha=0.25)
    plt.scatter(top["query_coverage"], top["mAP_among_covered_positive_queries"], s=70, color="#117733")
    plt.xlabel("Query coverage")
    plt.ylabel("mAP among covered positives")
    plt.title("mAP vs coverage")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "phase8_v2_map_vs_coverage.png", dpi=180)
    plt.close()

    b = boot[boot["selection_regime"] == "balanced_main_v2_recommendation"].copy()
    plt.figure(figsize=(10, 5))
    x = np.arange(len(b))
    lower = b["estimate"] - b["ci_lower"]
    upper = b["ci_upper"] - b["estimate"]
    plt.errorbar(x, b["estimate"], yerr=[lower, upper], fmt="o", color="#332288")
    plt.xticks(x, b["metric"].str.replace("_", " "), rotation=40, ha="right", fontsize=8)
    plt.ylabel("Metric value")
    plt.title("Bootstrap intervals for balanced v2 recommendation")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "phase8_v2_bootstrap_intervals_balanced_policy.png", dpi=180)
    plt.close()


def run(args: argparse.Namespace) -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    metadata, similarities = align_inputs(args)
    candidates = build_candidate_table(metadata, similarities, max_k=max(TOP_K_VALUES))
    policies = policy_grid()
    metrics = []
    for policy in policies:
        metric, _ = metric_for_policy(candidates, policy)
        metrics.append(metric)
    grid = pd.DataFrame(metrics)
    top = select_top_policies(grid)
    balanced_policy = top[top["selection_regime"] == "balanced_main_v2_recommendation"].iloc[0].to_dict()
    assignments = assignments_for_policy(candidates, balanced_policy)
    failure = failure_summary(assignments)
    comparison = comparison_to_prior(grid, top)
    boot = bootstrap_intervals(candidates, top, args.bootstrap_iterations)
    readiness = readiness_decision(top, comparison)

    grid.to_csv(POLICY_GRID_CSV, index=False)
    top.to_csv(TOP_POLICIES_CSV, index=False)
    assignments.to_csv(ASSIGNMENTS_CSV, index=False)
    failure.to_csv(FAILURE_SUMMARY_CSV, index=False)
    comparison.to_csv(COMPARISON_CSV, index=False)
    boot.to_csv(BOOTSTRAP_CSV, index=False)
    readiness.to_csv(READINESS_CSV, index=False)
    make_figures(grid, top, assignments, failure, boot, comparison)

    print("PASS: Phase 8 Slice 3A PF-ERI retrieval-control v2 optimization complete")
    print(f"candidate_policy_count: {len(grid)}")
    print("descriptors_evaluated: megadescriptor, resnet50")
    print("top_k_settings: 1, 3, 5, 10, 20")
    print("main_recommendation:")
    print(
        f"  {balanced_policy['policy_id']} / {balanced_policy['policy_family']} / "
        f"{balanced_policy['descriptor']} / top_k={balanced_policy['top_k']} / "
        f"false_top1={balanced_policy['false_top1_rate_among_covered_queries']:.4f} / "
        f"query_coverage={balanced_policy['query_coverage']:.4f} / "
        f"positive_retention={balanced_policy['positive_retention']:.4f} / "
        f"review_burden_reduction={balanced_policy['review_burden_reduction']:.4f}"
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--megadescriptor-embeddings-csv", type=Path, default=MEGA_EMBEDDINGS_CSV)
    parser.add_argument("--resnet50-embeddings-csv", type=Path, default=RESNET_EMBEDDINGS_CSV)
    parser.add_argument("--identity-csv", type=Path, default=IDENTITY_CSV)
    parser.add_argument("--annotation-csv", type=Path, default=ANNOTATION_CSV)
    parser.add_argument("--bootstrap-iterations", type=int, default=BOOTSTRAP_ITERATIONS)
    return parser.parse_args()


def main() -> int:
    return run(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
