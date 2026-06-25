#!/usr/bin/env python3
"""Run Phase 8 Slice 3E fixed-descriptor evidence-selection experiment."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from phase8_descriptor_disagreement_false_neighbor_confidence_control import build_mega_candidates
from phase8_pf_eri_deep_algorithm_v4_optimizer import (
    add_retrieval_confidence_features,
    assign_variant,
    compute_metrics as compute_v4_metrics,
    policy_grid as v4_policy_grid,
)
from phase8_pf_eri_retrieval_control_v2_optimizer import (
    ANNOTATION_CSV,
    IDENTITY_CSV,
    MEGA_EMBEDDINGS_CSV,
    RESNET_EMBEDDINGS_CSV,
    align_inputs,
    average_precision,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase8/reid_accuracy_evidence_selection"
FIGURE_DIR = OUTPUT_DIR / "figures"
DOC_PATH = PROJECT_ROOT / "docs/phase8/phase8_slice3e_reid_accuracy_evidence_selection_results.md"

FULL_RETRIEVAL_FILES = [
    PROJECT_ROOT / "outputs/czechlynx/phase8/full_retrieval_benchmark/phase8_czechlynx_full_retrieval_metrics_summary.csv",
    PROJECT_ROOT / "outputs/czechlynx/phase8/full_retrieval_benchmark/phase8_czechlynx_full_retrieval_topk_table.csv",
    PROJECT_ROOT / "outputs/czechlynx/phase8/full_retrieval_benchmark/phase8_czechlynx_full_retrieval_map_summary.csv",
    PROJECT_ROOT / "outputs/czechlynx/phase8/full_retrieval_benchmark/phase8_czechlynx_full_retrieval_pf_eri_filter_comparison.csv",
    PROJECT_ROOT / "outputs/czechlynx/phase8/full_retrieval_benchmark/phase8_czechlynx_full_retrieval_same_identity_rank_distribution.csv",
]
OTHER_INPUT_FILES = [
    PROJECT_ROOT / "outputs/czechlynx/phase8/pf_eri_retrieval_control_v2/phase8_pf_eri_retrieval_control_v2_recommended_assignments.csv",
    PROJECT_ROOT / "outputs/czechlynx/phase8/pf_eri_deep_algorithm_v4/phase8_pf_eri_v4_recommended_assignments.csv",
    PROJECT_ROOT / "outputs/czechlynx/phase8/pf_eri_deep_algorithm_v4/phase8_pf_eri_v4_variant_comparison.csv",
    PROJECT_ROOT / "outputs/czechlynx/phase8/utility_constrained_policy_selection/phase8_utility_policy_candidate_comparison.csv",
    PROJECT_ROOT / "outputs/czechlynx/phase8/utility_constrained_policy_selection/phase8_utility_policy_recommended_assignment.csv",
    PROJECT_ROOT / "outputs/czechlynx/phase7a/visual_only_pf_eri/phase7a_visual_only_pf_eri_pair_scores.csv",
    PROJECT_ROOT / "outputs/czechlynx/phase7a/descriptor_supported_pf_eri/phase7a_descriptor_supported_pair_scores.csv",
    PROJECT_ROOT / "data/interim/czechlynx/czechlynx_expanded_125x4_internal_with_ids.csv",
    PROJECT_ROOT / "outputs/czechlynx/phase4/czechlynx_phase4c_megadescriptor_embeddings.csv",
    PROJECT_ROOT / "outputs/czechlynx/phase4/czechlynx_phase4c_resnet50_embeddings.csv",
]

INPUT_INVENTORY_CSV = OUTPUT_DIR / "phase8_slice3e_input_inventory.csv"
POLICY_COMPARISON_CSV = OUTPUT_DIR / "phase8_slice3e_policy_comparison.csv"
RANDOM_SUMMARY_CSV = OUTPUT_DIR / "phase8_slice3e_random_same_size_baseline_summary.csv"
RANDOM_RAW_CSV = OUTPUT_DIR / "phase8_slice3e_random_same_size_baseline_raw.csv"
RISK_COVERAGE_CSV = OUTPUT_DIR / "phase8_slice3e_risk_coverage_curve.csv"
PARETO_CSV = OUTPUT_DIR / "phase8_slice3e_pareto_frontier.csv"
CALIBRATION_CSV = OUTPUT_DIR / "phase8_slice3e_calibration_evaluation_summary.csv"
BOOTSTRAP_CSV = OUTPUT_DIR / "phase8_slice3e_bootstrap_ci_summary.csv"
FINAL_RECOMMENDATION_CSV = OUTPUT_DIR / "phase8_slice3e_final_recommendation.csv"

RANDOM_SEED = 20260614
RANDOM_REPEATS = 500
BOOTSTRAP_ITERATIONS = 300
TOP_K = [1, 3, 5]
QUERY_COUNT = 500

IMAGE_FILTERS = {
    "all_images": "all_images",
    "pf_eri_low_or_higher": "pf_eri_low_or_higher",
    "pf_eri_medium_or_higher": "pf_eri_medium_or_higher",
    "pf_eri_high_only": "pf_eri_high_only",
    "pf_eri_medium_or_higher_without_severe_failures": "pf_eri_medium_or_higher_no_severe_failure",
}

UTILITY_VARIANTS = {
    "utility_balanced": {
        "visual": 0.25,
        "similarity": 0.25,
        "reciprocal": 0.18,
        "margin": 0.12,
        "disagreement": 0.12,
        "failure": 0.16,
        "cost": 0.04,
        "cap": 5,
    },
    "utility_visual_heavy": {
        "visual": 0.42,
        "similarity": 0.16,
        "reciprocal": 0.12,
        "margin": 0.08,
        "disagreement": 0.12,
        "failure": 0.22,
        "cost": 0.05,
        "cap": 5,
    },
    "utility_descriptor_heavy": {
        "visual": 0.14,
        "similarity": 0.42,
        "reciprocal": 0.14,
        "margin": 0.10,
        "disagreement": 0.10,
        "failure": 0.10,
        "cost": 0.03,
        "cap": 5,
    },
    "utility_confidence_heavy": {
        "visual": 0.16,
        "similarity": 0.20,
        "reciprocal": 0.30,
        "margin": 0.18,
        "disagreement": 0.18,
        "failure": 0.12,
        "cost": 0.04,
        "cap": 5,
    },
    "utility_workload_constrained": {
        "visual": 0.24,
        "similarity": 0.24,
        "reciprocal": 0.18,
        "margin": 0.12,
        "disagreement": 0.16,
        "failure": 0.18,
        "cost": 0.12,
        "cap": 3,
    },
}

STANDARD_METRIC_COLUMNS = [
    "top1_accuracy",
    "top3_accuracy",
    "top5_accuracy",
    "mAP",
    "MRR",
    "false_top1_rate",
    "false_reviewed_candidates_per_query",
    "reviewed_candidate_precision",
    "query_coverage",
    "identity_coverage",
    "positive_query_coverage",
    "positive_retention",
    "candidate_retention",
    "review_workload",
    "descriptor_disagreement_exposure",
    "severe_visual_failure_exposure",
]


def rate(value: float | int | np.floating | None) -> float:
    if value is None:
        return math.nan
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def input_inventory(paths: list[Path]) -> pd.DataFrame:
    rows = []
    for path in paths:
        exists = path.exists()
        row: dict[str, object] = {
            "input_file": str(path.relative_to(PROJECT_ROOT)),
            "exists": "yes" if exists else "no",
            "row_count": 0,
            "column_count": 0,
            "columns": "",
            "status": "available" if exists else "missing",
        }
        if exists:
            try:
                df = pd.read_csv(path)
                row["row_count"] = int(len(df))
                row["column_count"] = int(len(df.columns))
                row["columns"] = ";".join(df.columns)
                row["status"] = "available_nonempty" if len(df) else "available_empty"
            except Exception as exc:  # noqa: BLE001
                row["status"] = f"read_error:{type(exc).__name__}"
        rows.append(row)
    return pd.DataFrame(rows)


def image_mask(metadata: pd.DataFrame, filter_name: str) -> np.ndarray:
    if filter_name == "all_images":
        return np.ones(len(metadata), dtype=bool)
    band = metadata["visual_pf_eri_band"].astype(str)
    if filter_name == "pf_eri_low_or_higher":
        return band.isin(["low", "medium", "high"]).to_numpy()
    if filter_name == "pf_eri_medium_or_higher":
        return band.isin(["medium", "high"]).to_numpy()
    if filter_name == "pf_eri_high_only":
        return band.eq("high").to_numpy()
    if filter_name == "pf_eri_medium_or_higher_no_severe_failure":
        return (band.isin(["medium", "high"]) & ~metadata["severe_visual_failure"].astype(bool)).to_numpy()
    raise ValueError(f"Unknown image filter {filter_name}")


def retrieval_metrics(
    metadata: pd.DataFrame,
    similarity: np.ndarray,
    descriptor: str,
    filter_name: str,
    mask: np.ndarray,
    policy_family: str,
    policy_label: str,
) -> dict[str, object]:
    identities = metadata["working_individual_id"].astype(str).to_numpy()
    rows = np.arange(len(metadata))
    full_positive_queries = int(sum(((identities == identities[i]) & (rows != i)).any() for i in rows))
    selected = np.flatnonzero(mask)
    aps: list[float] = []
    rrs: list[float] = []
    top_hits = {k: [] for k in TOP_K}
    false_top1 = 0
    query_count = 0
    positive_after = 0
    candidate_count = 0
    false_candidate_count = 0
    selected_identities = set(metadata.iloc[selected]["working_individual_id"].astype(str))
    for i in selected:
        gallery = selected[selected != i]
        if len(gallery) == 0:
            continue
        query_count += 1
        scores = similarity[i, gallery]
        ranked = gallery[np.argsort(-scores)]
        relevance = (identities[ranked] == identities[i]).astype(int)
        candidate_count += int(len(relevance))
        false_candidate_count += int((relevance == 0).sum())
        if relevance.sum() == 0:
            continue
        positive_after += 1
        false_top1 += int(relevance[0] == 0)
        aps.append(average_precision(relevance))
        first_positive = int(np.flatnonzero(relevance == 1)[0]) + 1
        rrs.append(1.0 / first_positive)
        for k in TOP_K:
            top_hits[k].append(int(relevance[: min(k, len(relevance))].max()))
    selected_total = int(mask.sum())
    return {
        "policy_id": f"{descriptor}_{filter_name}",
        "policy_family": policy_family,
        "policy_label": policy_label,
        "selection_unit": "image",
        "descriptor": descriptor,
        "source_filter_or_variant": filter_name,
        "selected_count": selected_total,
        "candidate_pool_count": int(len(metadata)),
        "top1_accuracy": float(np.mean(top_hits[1])) if top_hits[1] else math.nan,
        "top3_accuracy": float(np.mean(top_hits[3])) if top_hits[3] else math.nan,
        "top5_accuracy": float(np.mean(top_hits[5])) if top_hits[5] else math.nan,
        "mAP": float(np.mean(aps)) if aps else math.nan,
        "MRR": float(np.mean(rrs)) if rrs else math.nan,
        "false_top1_rate": false_top1 / positive_after if positive_after else math.nan,
        "false_reviewed_candidates_per_query": false_candidate_count / QUERY_COUNT,
        "reviewed_candidate_precision": (candidate_count - false_candidate_count) / candidate_count if candidate_count else math.nan,
        "query_coverage": query_count / len(metadata) if len(metadata) else math.nan,
        "identity_coverage": len(selected_identities) / metadata["working_individual_id"].nunique(),
        "positive_query_coverage": positive_after / full_positive_queries if full_positive_queries else math.nan,
        "positive_retention": positive_after / full_positive_queries if full_positive_queries else math.nan,
        "candidate_retention": selected_total / len(metadata) if len(metadata) else math.nan,
        "review_workload": candidate_count / QUERY_COUNT,
        "descriptor_disagreement_exposure": math.nan,
        "severe_visual_failure_exposure": float(metadata.iloc[selected]["severe_visual_failure"].astype(bool).mean()) if selected_total else math.nan,
        "random_baseline_required": "no" if filter_name == "all_images" else "yes",
        "calibration_role": "fixed_prespecified_policy",
    }


def random_image_metrics(
    metadata: pd.DataFrame,
    similarity: np.ndarray,
    descriptor: str,
    target_policy_id: str,
    target_size: int,
    repeats: int,
    rng: np.random.Generator,
) -> list[dict[str, object]]:
    rows = []
    all_indices = np.arange(len(metadata))
    for repeat in range(1, repeats + 1):
        chosen = rng.choice(all_indices, size=target_size, replace=False)
        mask = np.zeros(len(metadata), dtype=bool)
        mask[chosen] = True
        metric = retrieval_metrics(metadata, similarity, descriptor, f"random_same_size_{target_policy_id}", mask, "random_same_size_image", "Random same-size image subset")
        metric["target_policy_id"] = target_policy_id
        metric["random_repeat"] = repeat
        rows.append(metric)
    return rows


def normalize_series(series: pd.Series) -> pd.Series:
    vals = pd.to_numeric(series, errors="coerce")
    min_v = vals.min()
    max_v = vals.max()
    if pd.isna(min_v) or pd.isna(max_v) or max_v == min_v:
        return pd.Series(np.zeros(len(vals)), index=series.index)
    return (vals - min_v) / (max_v - min_v)


def utility_assignments(candidates: pd.DataFrame, variant_name: str, weights: dict[str, float]) -> pd.DataFrame:
    df = candidates[candidates["rank"] <= 20].copy().sort_values(["query_idx", "rank"]).reset_index(drop=True)
    visual = df["pair_mean_score"] / 100.0
    similarity = normalize_series(df["megadescriptor_similarity"])
    reciprocal = ((df["mega_reciprocal_rank"] <= 10) | (df["resnet50_reciprocal_rank"] <= 10)).astype(float)
    margin = normalize_series(df["margin_confidence"])
    disagreement = df["similarity_high_resnet_low"].astype(float)
    severe = (df["pattern_none"] | df["severe_blur"] | df["major_occlusion"] | df["frontal_rear"]).astype(float)
    review_cost = (df["rank"] - 1) / 19.0
    df["utility_score"] = (
        weights["visual"] * visual
        + weights["similarity"] * similarity
        + weights["reciprocal"] * reciprocal
        + weights["margin"] * margin
        - weights["disagreement"] * disagreement
        - weights["failure"] * severe
        - weights["cost"] * review_cost
    )
    df["detailed_assignment"] = "defer_low_utility"
    for _, group in df.groupby("query_idx", sort=False):
        eligible = group[severe.loc[group.index] == 0].sort_values("utility_score", ascending=False).head(int(weights["cap"]))
        df.loc[eligible.index, "detailed_assignment"] = np.where(
            df.loc[eligible.index, "similarity_high_resnet_low"],
            "review_caution",
            "review_clear",
        )
    df["assignment"] = np.where(df["detailed_assignment"].str.startswith("review"), "review_candidate", "defer_candidate")
    df["active_disagreement"] = df["similarity_high_resnet_low"]
    df["reciprocal_support_flag"] = ((df["mega_reciprocal_rank"] <= 10) | (df["resnet50_reciprocal_rank"] <= 10))
    df["margin_confidence_flag"] = df["margin_confidence"] >= 0.03
    df["variant_id"] = variant_name
    return df


def standardize_candidate_metrics(metrics: dict[str, object], policy_id: str, family: str, label: str, selected: pd.DataFrame, pool_count: int) -> dict[str, object]:
    review_count = int(metrics.get("review_candidate_count", selected["assignment"].eq("review_candidate").sum()))
    true_review = int(selected[selected["assignment"].eq("review_candidate")]["same_identity"].sum())
    return {
        "policy_id": policy_id,
        "policy_family": family,
        "policy_label": label,
        "selection_unit": "candidate",
        "descriptor": "megadescriptor",
        "source_filter_or_variant": policy_id,
        "selected_count": review_count,
        "candidate_pool_count": pool_count,
        "top1_accuracy": rate(metrics.get("top1_success")),
        "top3_accuracy": rate(metrics.get("top3_success")),
        "top5_accuracy": rate(metrics.get("top5_success")),
        "mAP": rate(metrics.get("mAP")),
        "MRR": rate(metrics.get("MRR")),
        "false_top1_rate": rate(metrics.get("false_top1_rate")),
        "false_reviewed_candidates_per_query": rate(metrics.get("false_reviewed_candidates_per_query")),
        "reviewed_candidate_precision": true_review / review_count if review_count else math.nan,
        "query_coverage": rate(metrics.get("query_coverage")),
        "identity_coverage": math.nan,
        "positive_query_coverage": rate(metrics.get("positive_query_coverage")),
        "positive_retention": rate(metrics.get("positive_retention")),
        "candidate_retention": review_count / pool_count if pool_count else math.nan,
        "review_workload": rate(metrics.get("reviewed_candidates_per_query")),
        "descriptor_disagreement_exposure": rate(metrics.get("descriptor_disagreement_exposure")),
        "severe_visual_failure_exposure": rate(metrics.get("failure_exposure_review")),
        "random_baseline_required": "yes",
        "calibration_role": "fixed_prespecified_policy",
    }


def random_candidate_assignment(policy_assigned: pd.DataFrame, candidate_pool: pd.DataFrame, target_policy_id: str, repeat: int, rng: np.random.Generator) -> pd.DataFrame:
    pool = candidate_pool.copy()
    pool["assignment"] = "defer_candidate"
    pool["detailed_assignment"] = "random_defer"
    pool["active_disagreement"] = pool["similarity_high_resnet_low"]
    pool["reciprocal_support_flag"] = ((pool["mega_reciprocal_rank"] <= 10) | (pool["resnet50_reciprocal_rank"] <= 10))
    pool["margin_confidence_flag"] = pool["margin_confidence"] >= 0.03
    review_counts = policy_assigned[policy_assigned["assignment"] == "review_candidate"].groupby("query_idx").size()
    for query_idx, count in review_counts.items():
        group_idx = pool.index[pool["query_idx"] == query_idx].to_numpy()
        if len(group_idx) == 0 or count <= 0:
            continue
        chosen = rng.choice(group_idx, size=min(int(count), len(group_idx)), replace=False)
        pool.loc[chosen, "assignment"] = "review_candidate"
        pool.loc[chosen, "detailed_assignment"] = "random_review"
    pool["variant_id"] = f"random_{target_policy_id}_{repeat:04d}"
    return pool


def random_candidate_metrics(policy_assigned: pd.DataFrame, candidate_pool: pd.DataFrame, target_policy_id: str, repeats: int, rng: np.random.Generator) -> list[dict[str, object]]:
    pool = candidate_pool.sort_values(["query_idx", "rank"]).reset_index(drop=True).copy()
    query_ids = sorted(pool["query_idx"].unique())
    if len(query_ids) != QUERY_COUNT:
        raise ValueError(f"Expected {QUERY_COUNT} query groups for random candidate baseline, found {len(query_ids)}")
    same = pool["same_identity"].to_numpy(dtype=bool).reshape(QUERY_COUNT, 20)
    active_disagreement = pool["similarity_high_resnet_low"].to_numpy(dtype=bool).reshape(QUERY_COUNT, 20)
    severe = (
        pool["pattern_none"]
        | pool["low_pattern_visibility"]
        | pool["severe_blur"]
        | pool["major_occlusion"]
        | pool["frontal_rear"]
        | pool["weak_side_evidence"]
        | pool["uncertainty_flag"]
    ).to_numpy(dtype=bool).reshape(QUERY_COUNT, 20)
    review_counts = (
        policy_assigned[policy_assigned["assignment"] == "review_candidate"]
        .groupby("query_idx")
        .size()
        .reindex(query_ids)
        .fillna(0)
        .astype(int)
        .to_numpy()
    )
    true_total = int(same.sum())
    rows = []
    for repeat in range(1, repeats + 1):
        selected = np.zeros_like(same, dtype=bool)
        for q, count in enumerate(review_counts):
            if count <= 0:
                continue
            chosen = rng.choice(np.arange(20), size=min(int(count), 20), replace=False)
            selected[q, chosen] = True
        has_review = selected.any(axis=1)
        reviewed_count = int(selected.sum())
        true_review = int((selected & same).sum())
        false_review = int((selected & ~same).sum())
        has_positive = (selected & same).any(axis=1)
        top1_hits: list[int] = []
        top3_hits: list[int] = []
        top5_hits: list[int] = []
        aps: list[float] = []
        rrs: list[float] = []
        false_top1 = 0
        for q in range(QUERY_COUNT):
            if not has_review[q]:
                continue
            relevance = same[q][selected[q]].astype(int)
            false_top1 += int(relevance[0] == 0)
            if relevance.sum() == 0:
                continue
            top1_hits.append(int(relevance[0] == 1))
            top3_hits.append(int(relevance[: min(3, len(relevance))].max() == 1))
            top5_hits.append(int(relevance[: min(5, len(relevance))].max() == 1))
            first_positive = int(np.flatnonzero(relevance == 1)[0]) + 1
            aps.append(average_precision(relevance))
            rrs.append(1.0 / first_positive)
        positive_denominator = max(int(has_positive.sum()), 1)
        rows.append(
            {
                "policy_id": f"random_same_size_{target_policy_id}",
                "policy_family": "random_same_size_candidate",
                "policy_label": "Random same-size candidate subset",
                "selection_unit": "candidate",
                "descriptor": "megadescriptor",
                "source_filter_or_variant": f"random_same_size_{target_policy_id}",
                "selected_count": reviewed_count,
                "candidate_pool_count": int(len(candidate_pool)),
                "top1_accuracy": float(np.sum(top1_hits) / positive_denominator) if top1_hits else math.nan,
                "top3_accuracy": float(np.sum(top3_hits) / positive_denominator) if top3_hits else math.nan,
                "top5_accuracy": float(np.sum(top5_hits) / positive_denominator) if top5_hits else math.nan,
                "mAP": float(np.mean(aps)) if aps else math.nan,
                "MRR": float(np.mean(rrs)) if rrs else math.nan,
                "false_top1_rate": false_top1 / int(has_review.sum()) if has_review.sum() else math.nan,
                "false_reviewed_candidates_per_query": false_review / QUERY_COUNT,
                "reviewed_candidate_precision": true_review / reviewed_count if reviewed_count else math.nan,
                "query_coverage": float(has_review.mean()),
                "identity_coverage": math.nan,
                "positive_query_coverage": float(has_positive.mean()),
                "positive_retention": true_review / true_total if true_total else math.nan,
                "candidate_retention": reviewed_count / len(candidate_pool) if len(candidate_pool) else math.nan,
                "review_workload": reviewed_count / QUERY_COUNT,
                "descriptor_disagreement_exposure": float(active_disagreement[selected].mean()) if reviewed_count else math.nan,
                "severe_visual_failure_exposure": float(severe[selected].mean()) if reviewed_count else math.nan,
                "random_baseline_required": "no",
                "calibration_role": "random_same_size_control",
                "target_policy_id": target_policy_id,
                "random_repeat": repeat,
            }
        )
    return rows


def summarize_random(random_raw: pd.DataFrame, comparison: pd.DataFrame) -> pd.DataFrame:
    metric_cols = STANDARD_METRIC_COLUMNS
    rows = []
    for target, group in random_raw.groupby("target_policy_id"):
        actual = comparison[comparison["policy_id"] == target]
        if actual.empty:
            continue
        actual_row = actual.iloc[0]
        for metric in metric_cols:
            vals = pd.to_numeric(group[metric], errors="coerce").dropna()
            actual_value = rate(actual_row.get(metric))
            if vals.empty or math.isnan(actual_value):
                rows.append(
                    {
                        "target_policy_id": target,
                        "metric": metric,
                        "random_repeat_count": int(group["random_repeat"].nunique()),
                        "random_mean": math.nan,
                        "random_std": math.nan,
                        "random_p05": math.nan,
                        "random_p50": math.nan,
                        "random_p95": math.nan,
                        "pf_eri_value": actual_value,
                        "pf_eri_minus_random_mean": math.nan,
                        "pf_eri_percentile_vs_random": math.nan,
                    }
                )
                continue
            percentile = float((vals <= actual_value).mean())
            rows.append(
                {
                    "target_policy_id": target,
                    "metric": metric,
                    "random_repeat_count": int(group["random_repeat"].nunique()),
                    "random_mean": float(vals.mean()),
                    "random_std": float(vals.std(ddof=1)),
                    "random_p05": float(vals.quantile(0.05)),
                    "random_p50": float(vals.quantile(0.50)),
                    "random_p95": float(vals.quantile(0.95)),
                    "pf_eri_value": actual_value,
                    "pf_eri_minus_random_mean": float(actual_value - vals.mean()),
                    "pf_eri_percentile_vs_random": percentile,
                }
            )
    return pd.DataFrame(rows)


def bootstrap_ci(comparison: pd.DataFrame, random_raw: pd.DataFrame, repeats: int) -> pd.DataFrame:
    rows = []
    for _, row in comparison.iterrows():
        for metric in ["top1_accuracy", "top5_accuracy", "mAP", "MRR", "false_top1_rate", "false_reviewed_candidates_per_query", "positive_retention", "query_coverage"]:
            value = rate(row.get(metric))
            rows.append(
                {
                    "policy_id": row["policy_id"],
                    "metric": metric,
                    "bootstrap_iterations": repeats,
                    "estimate": value,
                    "ci_lower": math.nan,
                    "ci_upper": math.nan,
                    "uncertainty_source": "random_baseline_distribution_available_separately" if row["random_baseline_required"] == "yes" else "fixed_full_sample_no_bootstrap",
                }
            )
    for (target, metric), group in random_raw.groupby(["target_policy_id", "policy_id"]):
        pass
    return pd.DataFrame(rows)


def add_random_results(comparison: pd.DataFrame, random_summary: pd.DataFrame) -> pd.DataFrame:
    out = comparison.copy()
    key_metrics = ["mAP", "top1_accuracy", "top5_accuracy", "false_top1_rate", "false_reviewed_candidates_per_query", "positive_retention", "query_coverage"]
    for metric in key_metrics:
        subset = random_summary[random_summary["metric"] == metric][["target_policy_id", "random_mean", "pf_eri_minus_random_mean", "pf_eri_percentile_vs_random"]].rename(
            columns={
                "random_mean": f"{metric}_random_mean",
                "pf_eri_minus_random_mean": f"{metric}_minus_random_mean",
                "pf_eri_percentile_vs_random": f"{metric}_percentile_vs_random",
            }
        )
        out = out.merge(subset, left_on="policy_id", right_on="target_policy_id", how="left").drop(columns=["target_policy_id"], errors="ignore")
    return out


def risk_coverage(comparison: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "policy_family",
        "policy_id",
        "policy_label",
        "selection_unit",
        "descriptor",
        "source_filter_or_variant",
        "query_coverage",
        "identity_coverage",
        "candidate_retention",
        "false_top1_rate",
        "false_reviewed_candidates_per_query",
        "positive_retention",
        "mAP",
        "MRR",
        "review_workload",
    ]
    return comparison[cols].sort_values(["selection_unit", "descriptor", "query_coverage", "mAP"], ascending=[True, True, False, False])


def pareto_frontier(comparison: pd.DataFrame) -> pd.DataFrame:
    df = comparison.copy().reset_index(drop=True)
    objectives = {
        "top1_accuracy": "max",
        "top5_accuracy": "max",
        "mAP": "max",
        "MRR": "max",
        "positive_retention": "max",
        "query_coverage": "max",
        "false_top1_rate": "min",
        "false_reviewed_candidates_per_query": "min",
        "review_workload": "min",
    }
    values = df[list(objectives)].apply(pd.to_numeric, errors="coerce")
    efficient = []
    for i, row in values.iterrows():
        dominated = False
        for j, other in values.iterrows():
            if i == j:
                continue
            better_or_equal = []
            strictly_better = []
            for metric, direction in objectives.items():
                a = row[metric]
                b = other[metric]
                if pd.isna(a) or pd.isna(b):
                    continue
                if direction == "max":
                    better_or_equal.append(b >= a)
                    strictly_better.append(b > a)
                else:
                    better_or_equal.append(b <= a)
                    strictly_better.append(b < a)
            if better_or_equal and all(better_or_equal) and any(strictly_better):
                dominated = True
                break
        efficient.append("yes" if not dominated else "no")
    df["pareto_efficient"] = efficient
    return df


def calibration_summary(comparison: pd.DataFrame) -> pd.DataFrame:
    rows = []
    candidate_rows = comparison[comparison["selection_unit"] == "candidate"].copy()
    for family, group in candidate_rows.groupby("policy_family"):
        best = group.sort_values(["mAP", "false_reviewed_candidates_per_query"], ascending=[False, True]).iloc[0]
        rows.append(
            {
                "split_design": "query_level_calibration_evaluation_recommended_next",
                "policy_family": family,
                "calibration_action": "not_tuned_in_this_slice",
                "selected_operating_point": best["policy_id"],
                "evaluation_status": "full_sample_fixed_policy_reported",
                "limitation": "held_out_split_not_used_for_final_selection_in_this_first_implementation",
            }
        )
    return pd.DataFrame(rows)


def final_recommendation(comparison: pd.DataFrame, random_summary: pd.DataFrame, pareto: pd.DataFrame) -> pd.DataFrame:
    core_metrics = ["mAP", "top1_accuracy", "top5_accuracy", "false_top1_rate", "false_reviewed_candidates_per_query"]
    rows = []
    eligible = comparison[comparison["random_baseline_required"] == "yes"].copy()
    beats_random = []
    for _, policy in eligible.iterrows():
        policy_id = policy["policy_id"]
        metric_results = random_summary[random_summary["target_policy_id"] == policy_id]
        wins = 0
        available = 0
        for metric in core_metrics:
            row = metric_results[metric_results["metric"] == metric]
            if row.empty or pd.isna(row.iloc[0]["pf_eri_minus_random_mean"]):
                continue
            available += 1
            diff = float(row.iloc[0]["pf_eri_minus_random_mean"])
            if metric in {"false_top1_rate", "false_reviewed_candidates_per_query"}:
                wins += int(diff < 0)
            else:
                wins += int(diff > 0)
        beats_random.append((policy_id, wins, available))
    win_df = pd.DataFrame(beats_random, columns=["policy_id", "random_metric_wins", "random_metric_available"])
    merged = comparison.merge(win_df, on="policy_id", how="left")
    merged["pareto_efficient"] = merged["policy_id"].map(dict(zip(pareto["policy_id"], pareto["pareto_efficient"])))
    strong = merged[
        (merged["random_metric_wins"].fillna(0) >= 3)
        & (merged["query_coverage"].fillna(0) >= 0.50)
        & (merged["positive_retention"].fillna(0) >= 0.50)
        & (merged["pareto_efficient"] == "yes")
    ]
    if strong.empty:
        decision = "reid_accuracy_improvement_not_supported_beyond_random_same_size_controls"
        recommended = "candidate_f_remains_review_control_reference"
        rationale = "No PF-ERI strategy met random-baseline, coverage, retention, and Pareto requirements simultaneously."
    else:
        best = strong.sort_values(["random_metric_wins", "mAP", "query_coverage"], ascending=[False, False, False]).iloc[0]
        decision = "conditional_reid_accuracy_improvement_supported_for_czechlynx_fixed_descriptor_setting"
        recommended = str(best["policy_id"])
        rationale = "At least one PF-ERI strategy beat random same-size controls on multiple core metrics while preserving coverage and retention."
    rows.extend(
        [
            {
                "decision_item": "slice3e_reid_accuracy_improvement_claim",
                "decision": decision,
                "rationale": rationale,
            },
            {
                "decision_item": "recommended_policy_family",
                "decision": recommended,
                "rationale": "Selected only if strict Slice 3E success criteria are met; otherwise Candidate F remains review-control reference.",
            },
            {
                "decision_item": "candidate_f_remains_preferred",
                "decision": "yes",
                "rationale": "Candidate F remains the primary carry-forward review-control policy unless a stricter policy beats random controls without unacceptable coverage loss.",
            },
            {
                "decision_item": "v4_0636_becomes_preferred",
                "decision": "no",
                "rationale": "v4_0636 must beat random controls and preserve coverage/retention before replacing Candidate F.",
            },
            {
                "decision_item": "expected_utility_status",
                "decision": "candidate_selection_sensitivity_layer",
                "rationale": "Expected utility is interpretable candidate selection, not an identity score.",
            },
            {
                "decision_item": "training_status",
                "decision": "delayed",
                "rationale": "No training was run; fixed descriptors remain input measurement signals.",
            },
        ]
    )
    return pd.DataFrame(rows)


def make_figures(comparison: pd.DataFrame, random_summary: pd.DataFrame, pareto: pd.DataFrame) -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(9, 6))
    plt.scatter(comparison["query_coverage"], comparison["false_top1_rate"], c=comparison["selection_unit"].map({"image": 0, "candidate": 1}), cmap="viridis", s=70)
    for _, row in comparison.iterrows():
        plt.annotate(str(row["policy_id"])[:18], (row["query_coverage"], row["false_top1_rate"]), fontsize=6, alpha=0.75)
    plt.xlabel("Query coverage")
    plt.ylabel("False top-1 rate")
    plt.title("Slice 3E risk-coverage comparison")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "phase8_slice3e_risk_coverage.png", dpi=180)
    plt.close()

    plot = random_summary[random_summary["metric"].isin(["mAP", "top1_accuracy", "false_top1_rate", "false_reviewed_candidates_per_query"])].copy()
    if not plot.empty:
        plot["label"] = plot["target_policy_id"].astype(str).str[:20] + "\n" + plot["metric"]
        plt.figure(figsize=(13, 6))
        colors = np.where(plot["pf_eri_minus_random_mean"] >= 0, "#117733", "#CC6677")
        plt.bar(np.arange(len(plot)), plot["pf_eri_minus_random_mean"], color=colors)
        plt.axhline(0, color="black", linewidth=0.8)
        plt.xticks(np.arange(len(plot)), plot["label"], rotation=75, ha="right", fontsize=6)
        plt.ylabel("PF-ERI minus random mean")
        plt.title("PF-ERI policies versus repeated random same-size controls")
        plt.tight_layout()
        plt.savefig(FIGURE_DIR / "phase8_slice3e_random_baseline_differences.png", dpi=180)
        plt.close()

    plt.figure(figsize=(9, 6))
    colors = pareto["pareto_efficient"].map({"yes": "#117733", "no": "#999999"})
    plt.scatter(pareto["review_workload"], pareto["mAP"], c=colors, s=70)
    plt.xlabel("Review workload")
    plt.ylabel("mAP")
    plt.title("Slice 3E Pareto context")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "phase8_slice3e_pareto_context.png", dpi=180)
    plt.close()


def markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows available._"
    display = df.copy()
    for col in display.columns:
        if pd.api.types.is_float_dtype(display[col]):
            display[col] = display[col].map(lambda x: "" if pd.isna(x) else f"{float(x):.4f}")
        else:
            display[col] = display[col].astype(str)
    header = "| " + " | ".join(display.columns) + " |"
    separator = "| " + " | ".join(["---"] * len(display.columns)) + " |"
    rows = ["| " + " | ".join(row) + " |" for row in display.to_numpy(dtype=str)]
    return "\n".join([header, separator] + rows)


def write_results_doc(comparison: pd.DataFrame, random_summary: pd.DataFrame, final: pd.DataFrame, inventory: pd.DataFrame, repeats: int) -> None:
    decision = final.loc[final["decision_item"] == "slice3e_reid_accuracy_improvement_claim", "decision"].iloc[0]
    best_map = comparison.sort_values("mAP", ascending=False).head(5)
    candidate_f = comparison[comparison["policy_id"] == "candidate_f"]
    v4 = comparison[comparison["policy_id"] == "v4_0636"]
    utility = comparison[comparison["policy_family"].str.startswith("expected_utility")]
    missing = inventory[inventory["status"].str.contains("missing|read_error", regex=True)]
    text = f"""# Phase 8 Slice 3E Re-ID Accuracy Evidence Selection Results

## 1. Purpose

Slice 3E tests whether PF-ERI-selected evidence improves fixed-descriptor patterned-felid Re-ID retrieval or review metrics beyond repeated random same-size baselines. PF-ERI is not a Re-ID model, not a generic image-quality filter, and not a field deployment system.

## 2. Why Slice 3E Was Needed

Earlier Phase 8 work showed that PF-ERI can control review workload and make evidence risks visible, but it did not prove that selected evidence improves Re-ID accuracy beyond easier-sample filtering. Slice 3E directly tests that stricter claim.

## 3. Input Inventory

Inspected input files: `{len(inventory)}`.

Missing or unreadable inputs: `{len(missing)}`.

All final public outputs are aggregate or policy-level. They do not expose raw paths, original IDs, trap IDs, locations, GPS fields, cell codes, or per-identity split membership.

## 4. Methods

The run used existing MegaDescriptor and ResNet50 embeddings and CzechLynx labels for evaluation only. No model was trained. No external dataset was downloaded. No frozen data were modified.

Image-level policies were evaluated using all-vs-all retrieval with self-matches excluded. Candidate-level policies were evaluated using MegaDescriptor top-20 candidate pools with PF-ERI review/defer selection.

## 5. Policy Families Tested

- all-images baseline;
- raw descriptor ranking baseline;
- PF-ERI image filters;
- Candidate F;
- v4_0636 reconstructed from the v4 policy grid;
- expected-utility candidate-selection variants.

## 6. Random Same-Size Baseline Design

Random baseline repeats per tested non-baseline policy: `{repeats}`.

Image filters were compared with random same-size image subsets. Candidate policies were compared with random same-size per-query candidate selections matching each policy's reviewed-candidate count per query.

## 7. Calibration/Evaluation Design

This first implementation reports fixed pre-specified policy behavior on the full CzechLynx validation carrier and records the need for query-level calibration/evaluation in the next refinement. Row-level random splitting was not used.

## 8. Metrics

Metrics include top-1, top-3, top-5, mAP, MRR, false top-1, false reviewed candidates per query, reviewed-candidate precision, query coverage, identity coverage where available, positive-query coverage, positive retention, candidate retention, review workload, descriptor-disagreement exposure, and severe visual-failure exposure.

Top-k accuracy is not interpreted alone.

## 9. Main Results

Top policies by mAP:

{markdown_table(best_map[['policy_id', 'policy_family', 'selection_unit', 'descriptor', 'query_coverage', 'positive_retention', 'mAP', 'false_top1_rate', 'false_reviewed_candidates_per_query']])}

## 10. Random Baseline Comparison

The strict decision is:

```text
{decision}
```

PF-ERI is considered to support Re-ID accuracy improvement only if it beats repeated random same-size controls while preserving acceptable coverage and retention.

## 11. Risk-Coverage Interpretation

The risk-coverage table should be used as the main interpretation surface. Policies that improve mAP while sharply reducing query or positive retention should be treated as confidence-control references, not broad Re-ID accuracy improvements.

## 12. Pareto Interpretation

The Pareto frontier marks policies that are not dominated across accuracy, coverage, retention, false-risk, and workload objectives. A policy should not be promoted if it is dominated by raw descriptor ranking or random same-size filtering.

## 13. Bootstrap Uncertainty

The bootstrap CI table records uncertainty placeholders for fixed-policy outputs and points to random-baseline distributions for same-size comparisons. Candidate dependence remains a limitation; future calibration should use query-level splits.

## 14. Whether PF-ERI Improved Re-ID Beyond Random Same-Size Selection

{final.loc[final['decision_item'] == 'slice3e_reid_accuracy_improvement_claim', 'rationale'].iloc[0]}

## 15. Whether Improvements Are Only Easier-Sample Artifacts

The main easier-sample safeguard is the repeated random same-size comparison. If a PF-ERI policy improves over all-images but not over same-size random controls, that result is interpreted as easier-sample filtering rather than Re-ID accuracy improvement.

## 16. Candidate F and v4_0636

Candidate F:

{markdown_table(candidate_f[['policy_id', 'query_coverage', 'positive_retention', 'mAP', 'false_top1_rate', 'false_reviewed_candidates_per_query']]) if not candidate_f.empty else 'Candidate F metrics were not available.'}

v4_0636:

{markdown_table(v4[['policy_id', 'query_coverage', 'positive_retention', 'mAP', 'false_top1_rate', 'false_reviewed_candidates_per_query']]) if not v4.empty else 'v4_0636 metrics were not available.'}

## 17. Expected Utility

Expected-utility variants were implemented as transparent review-value candidate selection rules. They are not identity scores.

{markdown_table(utility[['policy_id', 'query_coverage', 'positive_retention', 'mAP', 'false_top1_rate', 'false_reviewed_candidates_per_query']]) if not utility.empty else 'Expected-utility metrics were not available.'}

## 18. Claims Supported

- CzechLynx fixed-descriptor evidence-selection behavior can be evaluated with strict random same-size controls.
- PF-ERI can be compared as an evidence-selection layer around fixed descriptors.
- Candidate-level review-control and image-level admissibility produce measurable accuracy, coverage, retention, and workload tradeoffs.

## 19. Claims Not Supported

- PF-ERI is a new Re-ID model.
- PF-ERI identifies true individual animals.
- PF-ERI is validated across felids or general animal Re-ID.
- PF-ERI is validated for Mainland Clouded Leopard or Marbled Cat.
- PF-ERI is ready for field deployment.
- PF-ERI supports population estimation.

## 20. Limitations

This is CzechLynx-only. Identity labels are used for evaluation only. Candidate-level policies use MegaDescriptor-generated candidates. Held-out calibration/evaluation is recorded as a next refinement rather than treated as completed final evidence. Random same-size controls reduce but do not eliminate all easier-sample concerns.

## 21. Recommended Next Step

Use the Slice 3E outputs to decide whether a query-level calibration/evaluation refinement is warranted. Do not train models or download external data until fixed-descriptor evidence-selection value is clear.

## 22. Confirmation

No model training, no external data download, no frozen-data edit, and no commit were performed by this slice.
"""
    DOC_PATH.write_text(text, encoding="utf-8")


def run(args: argparse.Namespace) -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    inventory = input_inventory(FULL_RETRIEVAL_FILES + OTHER_INPUT_FILES)
    inventory.to_csv(INPUT_INVENTORY_CSV, index=False)

    metadata, similarities = align_inputs(args)
    rng = np.random.default_rng(args.random_seed)

    comparison_rows: list[dict[str, object]] = []
    random_rows: list[dict[str, object]] = []
    for descriptor, sim in similarities.items():
        for label, filter_name in IMAGE_FILTERS.items():
            mask = image_mask(metadata, filter_name)
            family = "all_images_baseline" if filter_name == "all_images" else "pf_eri_image_subset"
            row = retrieval_metrics(metadata, sim, descriptor, label, mask, family, label)
            comparison_rows.append(row)
            if filter_name != "all_images":
                random_rows.extend(random_image_metrics(metadata, sim, descriptor, row["policy_id"], int(mask.sum()), args.random_repeats, rng))

    candidates = build_mega_candidates(metadata, similarities, max_k=20)
    candidates = add_retrieval_confidence_features(candidates, similarities)
    pool = candidates[candidates["rank"] <= 20].copy()

    candidate_assignments: dict[str, pd.DataFrame] = {}
    v4_policies = {p["variant_id"]: p for p in v4_policy_grid()}
    for policy_id, family, label, variant_id in [
        ("candidate_f", "candidate_f", "Candidate F", "v4_0001"),
        ("v4_0636", "v4_operational_refinement", "v4_0636 risk-calibrated review tiers", "v4_0636"),
    ]:
        assigned = assign_variant(candidates, v4_policies[variant_id])
        metric = compute_v4_metrics(assigned, v4_policies[variant_id])
        comparison_rows.append(standardize_candidate_metrics(metric, policy_id, family, label, assigned, len(pool)))
        candidate_assignments[policy_id] = assigned
        random_rows.extend(random_candidate_metrics(assigned, pool, policy_id, args.random_repeats, rng))

    for variant_name, weights in UTILITY_VARIANTS.items():
        assigned = utility_assignments(candidates, variant_name, weights)
        metric = compute_v4_metrics(assigned, {"variant_id": variant_name, "variant_family": "expected_utility", "variant_label": variant_name, "top_k": 20})
        comparison_rows.append(standardize_candidate_metrics(metric, variant_name, "expected_utility_candidate_selection", variant_name, assigned, len(pool)))
        candidate_assignments[variant_name] = assigned
        random_rows.extend(random_candidate_metrics(assigned, pool, variant_name, args.random_repeats, rng))

    comparison = pd.DataFrame(comparison_rows)
    random_raw = pd.DataFrame(random_rows)
    random_summary = summarize_random(random_raw, comparison)
    comparison = add_random_results(comparison, random_summary)
    risk = risk_coverage(comparison)
    pareto = pareto_frontier(comparison)
    calibration = calibration_summary(comparison)
    bootstrap = bootstrap_ci(comparison, random_raw, args.bootstrap_iterations)
    final = final_recommendation(comparison, random_summary, pareto)

    comparison.to_csv(POLICY_COMPARISON_CSV, index=False)
    random_summary.to_csv(RANDOM_SUMMARY_CSV, index=False)
    random_raw.to_csv(RANDOM_RAW_CSV, index=False)
    risk.to_csv(RISK_COVERAGE_CSV, index=False)
    pareto.to_csv(PARETO_CSV, index=False)
    calibration.to_csv(CALIBRATION_CSV, index=False)
    bootstrap.to_csv(BOOTSTRAP_CSV, index=False)
    final.to_csv(FINAL_RECOMMENDATION_CSV, index=False)
    make_figures(comparison, random_summary, pareto)
    write_results_doc(comparison, random_summary, final, inventory, args.random_repeats)

    print("PASS: Phase 8 Slice 3E fixed-descriptor evidence-selection experiment complete")
    print(f"policy_count: {len(comparison)}")
    print(f"random_repeat_count: {args.random_repeats}")
    print(f"random_raw_row_count: {len(random_raw)}")
    print(f"final_decision: {final.loc[final['decision_item'] == 'slice3e_reid_accuracy_improvement_claim', 'decision'].iloc[0]}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--megadescriptor-embeddings-csv", type=Path, default=MEGA_EMBEDDINGS_CSV)
    parser.add_argument("--resnet50-embeddings-csv", type=Path, default=RESNET_EMBEDDINGS_CSV)
    parser.add_argument("--identity-csv", type=Path, default=IDENTITY_CSV)
    parser.add_argument("--annotation-csv", type=Path, default=ANNOTATION_CSV)
    parser.add_argument("--random-repeats", type=int, default=RANDOM_REPEATS)
    parser.add_argument("--bootstrap-iterations", type=int, default=BOOTSTRAP_ITERATIONS)
    parser.add_argument("--random-seed", type=int, default=RANDOM_SEED)
    return parser.parse_args()


def main() -> int:
    return run(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
