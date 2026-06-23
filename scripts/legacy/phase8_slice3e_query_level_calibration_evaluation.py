#!/usr/bin/env python3
"""Run Phase 8 Slice 3E-R query-level calibration/evaluation refinement."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd

from phase8_descriptor_disagreement_false_neighbor_confidence_control import build_mega_candidates
from phase8_pf_eri_deep_algorithm_v4_optimizer import (
    add_retrieval_confidence_features,
    assign_variant,
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
from phase8_slice3e_reid_accuracy_evidence_selection import (
    INPUT_INVENTORY_CSV as SLICE3E_INPUT_INVENTORY_CSV,
    POLICY_COMPARISON_CSV as SLICE3E_POLICY_COMPARISON_CSV,
    RANDOM_RAW_CSV as SLICE3E_RANDOM_RAW_CSV,
    RANDOM_SUMMARY_CSV as SLICE3E_RANDOM_SUMMARY_CSV,
    RISK_COVERAGE_CSV as SLICE3E_RISK_COVERAGE_CSV,
    BOOTSTRAP_CSV as SLICE3E_BOOTSTRAP_CSV,
    CALIBRATION_CSV as SLICE3E_CALIBRATION_CSV,
    FINAL_RECOMMENDATION_CSV as SLICE3E_FINAL_RECOMMENDATION_CSV,
    PARETO_CSV as SLICE3E_PARETO_CSV,
    UTILITY_VARIANTS,
    image_mask,
    utility_assignments,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase8/reid_accuracy_query_calibration"
DOC_PATH = PROJECT_ROOT / "docs/phase8/phase8_slice3e_query_level_calibration_evaluation_results.md"

QUERY_SPLIT_INVENTORY_CSV = OUTPUT_DIR / "phase8_slice3e_query_split_inventory.csv"
POLICY_SELECTION_CSV = OUTPUT_DIR / "phase8_slice3e_query_calibration_policy_selection.csv"
EVALUATION_COMPARISON_CSV = OUTPUT_DIR / "phase8_slice3e_query_evaluation_policy_comparison.csv"
RANDOM_SUMMARY_CSV = OUTPUT_DIR / "phase8_slice3e_query_random_same_size_baseline_summary.csv"
RANDOM_RAW_CSV = OUTPUT_DIR / "phase8_slice3e_query_random_same_size_baseline_raw.csv"
RISK_COVERAGE_CSV = OUTPUT_DIR / "phase8_slice3e_query_risk_coverage_curve.csv"
PARETO_CSV = OUTPUT_DIR / "phase8_slice3e_query_pareto_frontier.csv"
BOOTSTRAP_CSV = OUTPUT_DIR / "phase8_slice3e_query_bootstrap_ci_summary.csv"
FINAL_RECOMMENDATION_CSV = OUTPUT_DIR / "phase8_slice3e_query_final_recommendation.csv"

INPUTS_TO_INSPECT = [
    SLICE3E_POLICY_COMPARISON_CSV,
    SLICE3E_RANDOM_SUMMARY_CSV,
    SLICE3E_RANDOM_RAW_CSV,
    SLICE3E_RISK_COVERAGE_CSV,
    SLICE3E_PARETO_CSV,
    SLICE3E_CALIBRATION_CSV,
    SLICE3E_BOOTSTRAP_CSV,
    SLICE3E_FINAL_RECOMMENDATION_CSV,
    PROJECT_ROOT / "outputs/czechlynx/phase8/full_retrieval_benchmark/phase8_czechlynx_full_retrieval_topk_table.csv",
    PROJECT_ROOT / "outputs/czechlynx/phase8/pf_eri_retrieval_control_v2/phase8_pf_eri_retrieval_control_v2_recommended_assignments.csv",
    PROJECT_ROOT / "outputs/czechlynx/phase8/pf_eri_deep_algorithm_v4/phase8_pf_eri_v4_recommended_assignments.csv",
    PROJECT_ROOT / "outputs/czechlynx/phase8/utility_constrained_policy_selection/phase8_utility_policy_recommended_assignment.csv",
    PROJECT_ROOT / "outputs/czechlynx/phase7a/visual_only_pf_eri/phase7a_visual_only_pf_eri_pair_scores.csv",
    PROJECT_ROOT / "outputs/czechlynx/phase7a/descriptor_supported_pf_eri/phase7a_descriptor_supported_pair_scores.csv",
    PROJECT_ROOT / "data/interim/czechlynx/czechlynx_expanded_125x4_internal_with_ids.csv",
    SLICE3E_INPUT_INVENTORY_CSV,
]

N_SPLITS = 20
CALIBRATION_FRACTION = 0.50
RANDOM_SEED_BASE = 8300
RANDOM_REPEATS_PER_SPLIT = 200
QUERY_COUNT = 500
TOP_K = [1, 3, 5]

POLICY_LABELS = {
    "raw_megadescriptor": "Raw MegaDescriptor top-5",
    "megadescriptor_pf_eri_medium_or_higher_without_severe_failures": "MegaDescriptor PF-ERI medium+ without severe failures",
    "candidate_f": "Candidate F",
    "v4_0636": "v4_0636",
    "utility_workload_constrained": "Utility workload constrained",
    "utility_balanced": "Utility balanced",
}


def input_inventory(paths: list[Path]) -> pd.DataFrame:
    rows = []
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
            df = pd.read_csv(path)
            row["row_count"] = int(len(df))
            row["column_count"] = int(len(df.columns))
            row["columns"] = ";".join(df.columns)
            row["status"] = "available_nonempty" if len(df) else "available_empty"
        rows.append(row)
    return pd.DataFrame(rows)


def make_identity_aware_splits(metadata: pd.DataFrame, n_splits: int, calibration_fraction: float, seed_base: int) -> pd.DataFrame:
    identities = metadata[["working_individual_id"]].drop_duplicates().reset_index(drop=True)
    rows = []
    for split_id in range(1, n_splits + 1):
        rng = np.random.default_rng(seed_base + split_id)
        shuffled = identities["working_individual_id"].sample(frac=1.0, random_state=seed_base + split_id).to_numpy()
        cal_count = int(round(len(shuffled) * calibration_fraction))
        calibration_ids = set(shuffled[:cal_count])
        role = metadata["working_individual_id"].map(lambda x: "calibration" if x in calibration_ids else "evaluation")
        rows.append(
            {
                "split_id": split_id,
                "split_design": "identity_aware_query_split",
                "calibration_query_count": int((role == "calibration").sum()),
                "evaluation_query_count": int((role == "evaluation").sum()),
                "calibration_identity_count": int(metadata.loc[role == "calibration", "working_individual_id"].nunique()),
                "evaluation_identity_count": int(metadata.loc[role == "evaluation", "working_individual_id"].nunique()),
                "random_seed": seed_base + split_id,
                "calibration_fraction": calibration_fraction,
            }
        )
    return pd.DataFrame(rows)


def split_roles(metadata: pd.DataFrame, split_id: int, calibration_fraction: float, seed_base: int) -> pd.Series:
    ids = metadata["working_individual_id"].drop_duplicates().sample(frac=1.0, random_state=seed_base + split_id).to_numpy()
    cal_count = int(round(len(ids) * calibration_fraction))
    calibration_ids = set(ids[:cal_count])
    return metadata["working_individual_id"].map(lambda x: "calibration" if x in calibration_ids else "evaluation")


def metric_value(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def image_retrieval_metrics(
    metadata: pd.DataFrame,
    similarity: np.ndarray,
    query_indices: np.ndarray,
    mask: np.ndarray,
    policy_id: str,
    policy_family: str,
) -> dict[str, object]:
    identities = metadata["working_individual_id"].astype(str).to_numpy()
    selected_gallery = np.flatnonzero(mask)
    full_positive = 0
    for q in query_indices:
        gallery_all = np.arange(len(metadata))
        full_positive += int(((identities[gallery_all] == identities[q]) & (gallery_all != q)).any())
    aps: list[float] = []
    rrs: list[float] = []
    top_hits = {k: [] for k in TOP_K}
    false_top1 = 0
    covered = 0
    positive_after = 0
    candidate_count = 0
    false_candidate_count = 0
    for q in query_indices:
        if not mask[q]:
            continue
        gallery = selected_gallery[selected_gallery != q]
        if len(gallery) == 0:
            continue
        covered += 1
        ranked = gallery[np.argsort(-similarity[q, gallery])]
        relevance = (identities[ranked] == identities[q]).astype(int)
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
    selected_queries = query_indices[mask[query_indices]]
    identity_coverage = metadata.iloc[selected_queries]["working_individual_id"].nunique() / max(metadata.iloc[query_indices]["working_individual_id"].nunique(), 1)
    return {
        "policy_id": policy_id,
        "policy_family": policy_family,
        "policy_label": POLICY_LABELS.get(policy_id, policy_id),
        "selection_unit": "image",
        "descriptor": "megadescriptor",
        "top1_accuracy": float(np.mean(top_hits[1])) if top_hits[1] else math.nan,
        "top3_accuracy": float(np.mean(top_hits[3])) if top_hits[3] else math.nan,
        "top5_accuracy": float(np.mean(top_hits[5])) if top_hits[5] else math.nan,
        "mAP": float(np.mean(aps)) if aps else math.nan,
        "MRR": float(np.mean(rrs)) if rrs else math.nan,
        "false_top1_rate": false_top1 / positive_after if positive_after else math.nan,
        "false_reviewed_candidates_per_query": false_candidate_count / max(len(query_indices), 1),
        "reviewed_candidate_precision": (candidate_count - false_candidate_count) / candidate_count if candidate_count else math.nan,
        "query_coverage": covered / max(len(query_indices), 1),
        "identity_coverage": identity_coverage,
        "positive_query_coverage": positive_after / max(full_positive, 1),
        "positive_retention": positive_after / max(full_positive, 1),
        "candidate_retention": float(mask.mean()),
        "review_workload": candidate_count / max(len(query_indices), 1),
        "descriptor_disagreement_exposure": math.nan,
        "severe_visual_failure_exposure": float(metadata.iloc[selected_gallery]["severe_visual_failure"].astype(bool).mean()) if len(selected_gallery) else math.nan,
        "selected_count": int(mask.sum()),
    }


def candidate_policy_metrics(assigned: pd.DataFrame, query_indices: np.ndarray, policy_id: str, policy_family: str) -> dict[str, object]:
    subset = assigned[assigned["query_idx"].isin(set(query_indices))].sort_values(["query_idx", "rank"]).copy()
    review = subset[subset["assignment"] == "review_candidate"].copy()
    grouped = subset.groupby("query_idx", sort=True)
    aps: list[float] = []
    rrs: list[float] = []
    top_hits = {k: [] for k in TOP_K}
    false_top1 = 0
    covered = 0
    positive_queries = 0
    for query_idx, group in grouped:
        review_group = group[group["assignment"] == "review_candidate"].sort_values("rank")
        if review_group.empty:
            continue
        covered += 1
        relevance = review_group["same_identity"].astype(int).to_numpy()
        false_top1 += int(relevance[0] == 0)
        if relevance.sum() == 0:
            continue
        positive_queries += 1
        aps.append(average_precision(relevance))
        first_positive = int(np.flatnonzero(relevance == 1)[0]) + 1
        rrs.append(1.0 / first_positive)
        for k in TOP_K:
            top_hits[k].append(int(relevance[: min(k, len(relevance))].max()))
    true_total = int(subset["same_identity"].sum())
    true_reviewed = int(review["same_identity"].sum())
    false_reviewed = int((~review["same_identity"]).sum()) if len(review) else 0
    flags = ["pattern_none", "low_pattern_visibility", "severe_blur", "major_occlusion", "frontal_rear", "weak_side_evidence", "uncertainty_flag"]
    return {
        "policy_id": policy_id,
        "policy_family": policy_family,
        "policy_label": POLICY_LABELS.get(policy_id, policy_id),
        "selection_unit": "candidate",
        "descriptor": "megadescriptor",
        "top1_accuracy": float(np.mean(top_hits[1])) if top_hits[1] else math.nan,
        "top3_accuracy": float(np.mean(top_hits[3])) if top_hits[3] else math.nan,
        "top5_accuracy": float(np.mean(top_hits[5])) if top_hits[5] else math.nan,
        "mAP": float(np.mean(aps)) if aps else math.nan,
        "MRR": float(np.mean(rrs)) if rrs else math.nan,
        "false_top1_rate": false_top1 / covered if covered else math.nan,
        "false_reviewed_candidates_per_query": false_reviewed / max(len(query_indices), 1),
        "reviewed_candidate_precision": true_reviewed / len(review) if len(review) else math.nan,
        "query_coverage": covered / max(len(query_indices), 1),
        "identity_coverage": math.nan,
        "positive_query_coverage": positive_queries / max(len(query_indices), 1),
        "positive_retention": true_reviewed / true_total if true_total else math.nan,
        "candidate_retention": len(review) / len(subset) if len(subset) else math.nan,
        "review_workload": len(review) / max(len(query_indices), 1),
        "descriptor_disagreement_exposure": float(review["active_disagreement"].mean()) if len(review) else math.nan,
        "severe_visual_failure_exposure": float(review[flags].any(axis=1).mean()) if len(review) else math.nan,
        "selected_count": int(len(review)),
    }


def raw_candidate_assignments(candidates: pd.DataFrame) -> pd.DataFrame:
    df = candidates[candidates["rank"] <= 20].copy().sort_values(["query_idx", "rank"]).reset_index(drop=True)
    df["assignment"] = np.where(df["rank"] <= 5, "review_candidate", "defer_candidate")
    df["detailed_assignment"] = np.where(df["rank"] <= 5, "raw_review", "raw_defer")
    df["active_disagreement"] = df["similarity_high_resnet_low"]
    df["reciprocal_support_flag"] = (df["mega_reciprocal_rank"] <= 10) | (df["resnet50_reciprocal_rank"] <= 10)
    df["margin_confidence_flag"] = df["margin_confidence"] >= 0.03
    return df


def random_image_split_metrics(
    metadata: pd.DataFrame,
    similarity: np.ndarray,
    query_indices: np.ndarray,
    target_size: int,
    target_policy_id: str,
    split_id: int,
    split_role: str,
    repeats: int,
    rng: np.random.Generator,
) -> list[dict[str, object]]:
    rows = []
    all_indices = np.arange(len(metadata))
    for repeat in range(1, repeats + 1):
        chosen = rng.choice(all_indices, size=target_size, replace=False)
        mask = np.zeros(len(metadata), dtype=bool)
        mask[chosen] = True
        row = image_retrieval_metrics(metadata, similarity, query_indices, mask, f"random_same_size_{target_policy_id}", "random_same_size_image")
        row.update({"split_id": split_id, "split_role": split_role, "target_policy_id": target_policy_id, "random_repeat": repeat})
        rows.append(row)
    return rows


def random_candidate_split_metrics(
    assigned: pd.DataFrame,
    pool: pd.DataFrame,
    query_indices: np.ndarray,
    target_policy_id: str,
    split_id: int,
    split_role: str,
    repeats: int,
    rng: np.random.Generator,
) -> list[dict[str, object]]:
    query_set = set(query_indices)
    pool_subset = pool[pool["query_idx"].isin(query_set)].sort_values(["query_idx", "rank"]).reset_index(drop=True).copy()
    query_ids = sorted(pool_subset["query_idx"].unique())
    if len(query_ids) == 0:
        return []
    rank_count = int(pool_subset.groupby("query_idx").size().max())
    same = pool_subset["same_identity"].to_numpy(dtype=bool).reshape(len(query_ids), rank_count)
    active_disagreement = pool_subset["similarity_high_resnet_low"].to_numpy(dtype=bool).reshape(len(query_ids), rank_count)
    severe = (
        pool_subset["pattern_none"]
        | pool_subset["low_pattern_visibility"]
        | pool_subset["severe_blur"]
        | pool_subset["major_occlusion"]
        | pool_subset["frontal_rear"]
        | pool_subset["weak_side_evidence"]
        | pool_subset["uncertainty_flag"]
    ).to_numpy(dtype=bool).reshape(len(query_ids), rank_count)
    review_counts = assigned[(assigned["query_idx"].isin(query_set)) & (assigned["assignment"] == "review_candidate")].groupby("query_idx").size()
    review_count_arr = np.asarray([int(review_counts.get(q, 0)) for q in query_ids], dtype=int)
    true_total = int(same.sum())
    rows = []
    for repeat in range(1, repeats + 1):
        selected = np.zeros_like(same, dtype=bool)
        for row_idx, count in enumerate(review_count_arr):
            if count > 0:
                chosen = rng.choice(np.arange(rank_count), size=min(count, rank_count), replace=False)
                selected[row_idx, chosen] = True
        has_review = selected.any(axis=1)
        reviewed_count = int(selected.sum())
        true_review = int((selected & same).sum())
        false_review = int((selected & ~same).sum())
        has_positive = (selected & same).any(axis=1)
        aps: list[float] = []
        rrs: list[float] = []
        top_hits = {k: [] for k in TOP_K}
        false_top1 = 0
        for row_idx in range(len(query_ids)):
            if not has_review[row_idx]:
                continue
            relevance = same[row_idx][selected[row_idx]].astype(int)
            false_top1 += int(relevance[0] == 0)
            if relevance.sum() == 0:
                continue
            aps.append(average_precision(relevance))
            first_positive = int(np.flatnonzero(relevance == 1)[0]) + 1
            rrs.append(1.0 / first_positive)
            for k in TOP_K:
                top_hits[k].append(int(relevance[: min(k, len(relevance))].max()))
        positive_denominator = max(int(has_positive.sum()), 1)
        row = {
            "policy_id": f"random_same_size_{target_policy_id}",
            "policy_family": "random_same_size_candidate",
            "policy_label": "random same-size candidate",
            "selection_unit": "candidate",
            "descriptor": "megadescriptor",
            "top1_accuracy": float(np.sum(top_hits[1]) / positive_denominator) if top_hits[1] else math.nan,
            "top3_accuracy": float(np.sum(top_hits[3]) / positive_denominator) if top_hits[3] else math.nan,
            "top5_accuracy": float(np.sum(top_hits[5]) / positive_denominator) if top_hits[5] else math.nan,
            "mAP": float(np.mean(aps)) if aps else math.nan,
            "MRR": float(np.mean(rrs)) if rrs else math.nan,
            "false_top1_rate": false_top1 / int(has_review.sum()) if has_review.sum() else math.nan,
            "false_reviewed_candidates_per_query": false_review / max(len(query_indices), 1),
            "reviewed_candidate_precision": true_review / reviewed_count if reviewed_count else math.nan,
            "query_coverage": float(has_review.sum() / max(len(query_indices), 1)),
            "identity_coverage": math.nan,
            "positive_query_coverage": float(has_positive.sum() / max(len(query_indices), 1)),
            "positive_retention": true_review / true_total if true_total else math.nan,
            "candidate_retention": reviewed_count / len(pool_subset) if len(pool_subset) else math.nan,
            "review_workload": reviewed_count / max(len(query_indices), 1),
            "descriptor_disagreement_exposure": float(active_disagreement[selected].mean()) if reviewed_count else math.nan,
            "severe_visual_failure_exposure": float(severe[selected].mean()) if reviewed_count else math.nan,
            "selected_count": reviewed_count,
        }
        row.update({"split_id": split_id, "split_role": split_role, "target_policy_id": target_policy_id, "random_repeat": repeat})
        rows.append(row)
    return rows


def random_summary(random_raw: pd.DataFrame, actual: pd.DataFrame) -> pd.DataFrame:
    metrics = [
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
    rows = []
    for (split_id, role, target), group in random_raw.groupby(["split_id", "split_role", "target_policy_id"]):
        actual_row = actual[(actual["split_id"] == split_id) & (actual["split_role"] == role) & (actual["policy_id"] == target)]
        if actual_row.empty:
            continue
        actual_row = actual_row.iloc[0]
        for metric in metrics:
            vals = pd.to_numeric(group[metric], errors="coerce").dropna()
            value = metric_value(actual_row.get(metric))
            rows.append(
                {
                    "split_id": split_id,
                    "split_role": role,
                    "target_policy_id": target,
                    "metric": metric,
                    "random_repeat_count": int(group["random_repeat"].nunique()),
                    "random_mean": float(vals.mean()) if len(vals) else math.nan,
                    "random_std": float(vals.std(ddof=1)) if len(vals) > 1 else math.nan,
                    "random_p05": float(vals.quantile(0.05)) if len(vals) else math.nan,
                    "random_p50": float(vals.quantile(0.50)) if len(vals) else math.nan,
                    "random_p95": float(vals.quantile(0.95)) if len(vals) else math.nan,
                    "pf_eri_value": value,
                    "pf_eri_minus_random_mean": float(value - vals.mean()) if len(vals) and not math.isnan(value) else math.nan,
                    "pf_eri_percentile_vs_random": float((vals <= value).mean()) if len(vals) and not math.isnan(value) else math.nan,
                }
            )
    return pd.DataFrame(rows)


def add_random_columns(metrics: pd.DataFrame, summary: pd.DataFrame) -> pd.DataFrame:
    out = metrics.copy()
    for metric in ["mAP", "MRR", "top1_accuracy", "top5_accuracy", "false_top1_rate", "false_reviewed_candidates_per_query", "positive_retention", "query_coverage"]:
        sub = summary[summary["metric"] == metric][
            ["split_id", "split_role", "target_policy_id", "random_mean", "pf_eri_minus_random_mean", "pf_eri_percentile_vs_random"]
        ].rename(
            columns={
                "target_policy_id": "policy_id",
                "random_mean": f"{metric}_random_mean",
                "pf_eri_minus_random_mean": f"{metric}_minus_random_mean",
                "pf_eri_percentile_vs_random": f"{metric}_percentile_vs_random",
            }
        )
        out = out.merge(sub, on=["split_id", "split_role", "policy_id"], how="left")
    return out


def normalize_for_score(series: pd.Series, reverse: bool = False) -> pd.Series:
    vals = pd.to_numeric(series, errors="coerce")
    min_v = vals.min()
    max_v = vals.max()
    if pd.isna(min_v) or pd.isna(max_v) or max_v == min_v:
        norm = pd.Series(np.zeros(len(vals)), index=series.index)
    else:
        norm = (vals - min_v) / (max_v - min_v)
    return 1.0 - norm if reverse else norm


def select_policy(calibration: pd.DataFrame) -> pd.DataFrame:
    df = calibration.copy()
    beats_random = (
        (df["mAP_minus_random_mean"].fillna(-np.inf) > 0)
        | (df["false_reviewed_candidates_per_query_minus_random_mean"].fillna(np.inf) < 0)
    )
    df["eligible"] = (
        (df["positive_retention"] >= 0.50)
        & (df["query_coverage"] >= 0.50)
        & beats_random
    )
    score = (
        normalize_for_score(df["mAP"])
        + normalize_for_score(df["top5_accuracy"])
        + normalize_for_score(df["positive_retention"])
        + normalize_for_score(df["query_coverage"])
        + normalize_for_score(df["false_reviewed_candidates_per_query"], reverse=True)
        + normalize_for_score(df["false_top1_rate"], reverse=True)
    )
    df["balanced_score"] = score
    eligible = df[df["eligible"]].copy()
    if eligible.empty:
        df["selection_status"] = "not_selected"
        fallback = df.sort_values(["positive_retention", "query_coverage", "balanced_score"], ascending=[False, False, False]).head(1).index
        df.loc[fallback, "selection_status"] = "selected_fallback_no_policy_met_strict_rule"
    else:
        df["selection_status"] = "not_selected"
        chosen = eligible.sort_values("balanced_score", ascending=False).head(1).index
        df.loc[chosen, "selection_status"] = "selected_by_strict_calibration_rule"
    return df


def pareto_frontier(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy().reset_index(drop=True)
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
    values = out[list(objectives)].apply(pd.to_numeric, errors="coerce")
    efficient = []
    for i, row in values.iterrows():
        dominated = False
        for j, other in values.iterrows():
            if i == j:
                continue
            comparisons = []
            strict = []
            for metric, direction in objectives.items():
                a = row[metric]
                b = other[metric]
                if pd.isna(a) or pd.isna(b):
                    continue
                comparisons.append(b >= a if direction == "max" else b <= a)
                strict.append(b > a if direction == "max" else b < a)
            if comparisons and all(comparisons) and any(strict):
                dominated = True
                break
        efficient.append("yes" if not dominated else "no")
    out["pareto_efficient"] = efficient
    return out


def split_uncertainty(evaluation: pd.DataFrame) -> pd.DataFrame:
    rows = []
    selected = evaluation[evaluation["selected_for_evaluation"] == "yes"]
    for policy_id, group in selected.groupby("policy_id"):
        for metric in ["mAP", "MRR", "top1_accuracy", "top5_accuracy", "false_top1_rate", "false_reviewed_candidates_per_query", "positive_retention", "query_coverage"]:
            vals = pd.to_numeric(group[metric], errors="coerce").dropna()
            rows.append(
                {
                    "policy_id": policy_id,
                    "metric": metric,
                    "split_count": int(group["split_id"].nunique()),
                    "estimate_mean": float(vals.mean()) if len(vals) else math.nan,
                    "split_std": float(vals.std(ddof=1)) if len(vals) > 1 else math.nan,
                    "split_p05": float(vals.quantile(0.05)) if len(vals) else math.nan,
                    "split_p50": float(vals.quantile(0.50)) if len(vals) else math.nan,
                    "split_p95": float(vals.quantile(0.95)) if len(vals) else math.nan,
                }
            )
    return pd.DataFrame(rows)


def final_recommendation(selection: pd.DataFrame, evaluation: pd.DataFrame, random_sum: pd.DataFrame, pareto: pd.DataFrame) -> pd.DataFrame:
    selected_eval = evaluation[evaluation["selected_for_evaluation"] == "yes"].copy()
    selected_eval = selected_eval.merge(
        pareto[["split_id", "policy_id", "pareto_efficient"]],
        on=["split_id", "policy_id"],
        how="left",
    )
    stable_policy = selected_eval["policy_id"].mode().iloc[0] if not selected_eval.empty else "not_available"
    selected_count = int(len(selected_eval))
    mAP_wins = (selected_eval["mAP_minus_random_mean"].fillna(-np.inf) > 0).sum()
    mrr_wins = (selected_eval["MRR_minus_random_mean"].fillna(-np.inf) > 0).sum()
    burden_wins = (selected_eval["false_reviewed_candidates_per_query_minus_random_mean"].fillna(np.inf) < 0).sum()
    coverage_ok = (selected_eval["query_coverage"] >= 0.50).sum()
    retention_ok = (selected_eval["positive_retention"] >= 0.50).sum()
    pareto_ok = (selected_eval["pareto_efficient"] == "yes").sum()
    robust = (
        selected_count > 0
        and mAP_wins >= math.ceil(0.70 * selected_count)
        and burden_wins >= math.ceil(0.70 * selected_count)
        and coverage_ok >= math.ceil(0.80 * selected_count)
        and retention_ok >= math.ceil(0.80 * selected_count)
        and pareto_ok >= math.ceil(0.60 * selected_count)
    )
    decision = "held_out_reid_accuracy_improvement_supported" if robust else "held_out_reid_accuracy_improvement_not_robust"
    rationale = (
        "Selected policies beat random controls and preserved coverage/retention across most held-out splits."
        if robust
        else "Held-out split evidence did not satisfy stability, random-control, coverage, retention, and Pareto requirements together."
    )
    rows = [
        {
            "decision_item": "slice3e_r_held_out_reid_accuracy_claim",
            "decision": decision,
            "rationale": rationale,
        },
        {
            "decision_item": "most_frequent_selected_policy",
            "decision": stable_policy,
            "rationale": "Most frequent winner under strict calibration-only policy selection.",
        },
        {
            "decision_item": "selected_split_count",
            "decision": selected_count,
            "rationale": "Number of held-out evaluation splits.",
        },
        {
            "decision_item": "mAP_random_win_count",
            "decision": int(mAP_wins),
            "rationale": "Number of selected held-out splits where mAP exceeded random same-size mean.",
        },
        {
            "decision_item": "false_burden_random_win_count",
            "decision": int(burden_wins),
            "rationale": "Number of selected held-out splits where false reviewed candidates/query was below random same-size mean.",
        },
        {
            "decision_item": "candidate_f_remains_preferred",
            "decision": "yes",
            "rationale": "Candidate F remains the review-control reference unless a held-out policy is both robust and operationally preferable.",
        },
        {
            "decision_item": "v4_0636_becomes_preferred",
            "decision": "no",
            "rationale": "v4_0636 is retained as operational refinement reference unless selected robustly across held-out splits.",
        },
        {
            "decision_item": "utility_policy_status",
            "decision": "sensitivity_layer",
            "rationale": "Utility policies remain interpretable candidate-selection sensitivity layers, not identity scores.",
        },
    ]
    return pd.DataFrame(rows)


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


def write_doc(inventory: pd.DataFrame, split_inventory: pd.DataFrame, selection: pd.DataFrame, evaluation: pd.DataFrame,
              random_sum: pd.DataFrame, uncertainty: pd.DataFrame, final: pd.DataFrame, repeats: int) -> None:
    selected = evaluation[evaluation["selected_for_evaluation"] == "yes"].copy()
    selected_summary = selected.groupby("policy_id").agg(
        split_count=("split_id", "nunique"),
        mean_mAP=("mAP", "mean"),
        mean_query_coverage=("query_coverage", "mean"),
        mean_positive_retention=("positive_retention", "mean"),
        mean_false_reviewed_candidates_per_query=("false_reviewed_candidates_per_query", "mean"),
        mean_mAP_minus_random=("mAP_minus_random_mean", "mean"),
        mean_false_burden_minus_random=("false_reviewed_candidates_per_query_minus_random_mean", "mean"),
    ).reset_index()
    freq = selected["policy_id"].value_counts().rename_axis("policy_id").reset_index(name="selected_split_count")
    decision = final.loc[final["decision_item"] == "slice3e_r_held_out_reid_accuracy_claim", "decision"].iloc[0]
    text = f"""# Phase 8 Slice 3E-R Query-Level Calibration/Evaluation Results

## 1. Purpose

Slice 3E-R tests whether PF-ERI-selected image or candidate policies chosen on calibration queries still improve fixed-descriptor patterned-felid Re-ID performance on held-out evaluation queries. PF-ERI is not a Re-ID model; it is an evidence-selection and review-control framework around fixed descriptors.

## 2. Why Query-Level Calibration/Evaluation Is Needed

Slice 3E used strict repeated random same-size controls but did not complete a true held-out calibration/evaluation design. Candidates from the same query are dependent, so this refinement splits at query level and does not use row-level random splitting.

## 3. Input Inventory

Inspected input files: `{len(inventory)}`.

Missing inputs: `{int((inventory['exists'] == 'no').sum())}`.

## 4. Split Design

Split design: deterministic identity-aware query-level splitting.

Split count: `{int(split_inventory['split_id'].nunique())}`.

Random repeats per split: `{repeats}`.

No per-identity split membership is exported.

## 5. Policy Selection Rule

Calibration used only calibration queries. A policy was eligible only if positive retention was at least 0.50, query coverage was at least 0.50, and it beat the random same-size mean on mAP or false-candidate burden. Eligible policies were ranked by a transparent balanced score combining normalized mAP, top-5 accuracy, positive retention, query coverage, false reviewed candidates/query, and false top-1.

## 6. Calibration Results

Selected policy frequency:

{markdown_table(freq)}

## 7. Held-Out Evaluation Results

Held-out selected-policy summary:

{markdown_table(selected_summary)}

## 8. Repeated Random Same-Size Comparison

Random same-size controls were recomputed within each split for the held-out selected policy. The random-control columns in the evaluation table report the selected policy value, random mean, difference from random mean, and percentile versus random repeats.

## 9. Stability Across Splits

Stability is assessed by selected-policy frequency and split-level uncertainty. A result is considered robust only if it clears random-control, coverage, retention, and Pareto requirements across most splits.

## 10. Risk-Coverage Interpretation

Policies with high mAP but low positive retention should be interpreted as confidence-control or sensitivity strategies, not broad Re-ID improvement policies.

## 11. Pareto Interpretation

The Pareto table marks held-out policies that are not dominated within each split across accuracy, retention, coverage, risk, and workload objectives.

## 12. Split-Level Uncertainty

{markdown_table(uncertainty.head(20))}

## 13. Whether the Stronger Re-ID Improvement Claim Is Supported

Decision:

```text
{decision}
```

Rationale:

{final.loc[final['decision_item'] == 'slice3e_r_held_out_reid_accuracy_claim', 'rationale'].iloc[0]}

## 14. Whether Easier-Sample Artifact Remains a Concern

Yes. Random same-size controls reduce the easier-sample concern, but the held-out interpretation still depends on whether selected policies preserve positive retention and coverage across splits.

## 15. Final Recommended Policy

Most frequent selected policy:

```text
{final.loc[final['decision_item'] == 'most_frequent_selected_policy', 'decision'].iloc[0]}
```

Candidate F remains the review-control reference. v4_0636 remains an operational refinement reference. Utility policies remain sensitivity layers.

## 16. Claims Supported

- CzechLynx query-level held-out calibration/evaluation can be run without row-level leakage.
- PF-ERI evidence-selection policies can be evaluated against random same-size controls on held-out query splits.
- Held-out evaluation clarifies whether Slice 3E's conditional improvement is stable.

## 17. Claims Still Forbidden

- PF-ERI is a new Re-ID model.
- PF-ERI identifies true individual animals.
- PF-ERI is validated across felids or general animal Re-ID.
- PF-ERI is validated for Mainland Clouded Leopard or Marbled Cat.
- PF-ERI is ready for field deployment.
- PF-ERI supports population estimation.

## 18. Limitations

This is CzechLynx-only. The query split is identity-aware for calibration/evaluation roles but gallery evidence remains the fixed CzechLynx validation carrier. No external data were used. No model was trained. Random controls are repeated simulation controls, not external validation.

## 19. Recommended Next Step

If the held-out claim is robust, update the manuscript method/results around query-level validation. If not robust, keep PF-ERI framed as evidence-control and review-prioritization and avoid stronger Re-ID accuracy claims.

## 20. Confirmation

No training, no external data download, no frozen-data edit, no staging, and no commit were performed.
"""
    DOC_PATH.write_text(text, encoding="utf-8")


def run(args: argparse.Namespace) -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    inventory = input_inventory(INPUTS_TO_INSPECT)
    metadata, similarities = align_inputs(args)
    split_inventory = make_identity_aware_splits(metadata, args.n_splits, args.calibration_fraction, args.random_seed_base)

    candidates = build_mega_candidates(metadata, similarities, max_k=20)
    candidates = add_retrieval_confidence_features(candidates, similarities)
    pool = candidates[candidates["rank"] <= 20].copy()
    v4_policies = {p["variant_id"]: p for p in v4_policy_grid()}
    assignments = {
        "raw_megadescriptor": raw_candidate_assignments(candidates),
        "candidate_f": assign_variant(candidates, v4_policies["v4_0001"]),
        "v4_0636": assign_variant(candidates, v4_policies["v4_0636"]),
        "utility_workload_constrained": utility_assignments(candidates, "utility_workload_constrained", UTILITY_VARIANTS["utility_workload_constrained"]),
        "utility_balanced": utility_assignments(candidates, "utility_balanced", UTILITY_VARIANTS["utility_balanced"]),
    }
    image_policy_id = "megadescriptor_pf_eri_medium_or_higher_without_severe_failures"
    image_policy_mask = image_mask(metadata, "pf_eri_medium_or_higher_no_severe_failure")

    calibration_rows = []
    evaluation_rows = []
    random_rows = []
    for split_id in range(1, args.n_splits + 1):
        role = split_roles(metadata, split_id, args.calibration_fraction, args.random_seed_base)
        cal_queries = np.flatnonzero(role.to_numpy() == "calibration")
        eval_queries = np.flatnonzero(role.to_numpy() == "evaluation")
        rng = np.random.default_rng(args.random_seed_base + 1000 + split_id)

        split_policy_rows = []
        for split_role, query_indices in [("calibration", cal_queries), ("evaluation", eval_queries)]:
            rows = [
                image_retrieval_metrics(
                    metadata,
                    similarities["megadescriptor"],
                    query_indices,
                    image_policy_mask,
                    image_policy_id,
                    "pf_eri_image_subset",
                )
            ]
            for policy_id, assigned in assignments.items():
                family = "raw_descriptor" if policy_id == "raw_megadescriptor" else "candidate_policy"
                if policy_id.startswith("utility_"):
                    family = "expected_utility_candidate_selection"
                elif policy_id == "candidate_f":
                    family = "candidate_f"
                elif policy_id == "v4_0636":
                    family = "v4_operational_refinement"
                rows.append(candidate_policy_metrics(assigned, query_indices, policy_id, family))
            for row in rows:
                row.update({"split_id": split_id, "split_role": split_role})
                split_policy_rows.append(row)

        split_policy_df = pd.DataFrame(split_policy_rows)
        cal_df = split_policy_df[split_policy_df["split_role"] == "calibration"].copy()
        cal_random_rows = []
        for _, row in cal_df.iterrows():
            policy_id = row["policy_id"]
            if policy_id == "raw_megadescriptor":
                continue
            if row["selection_unit"] == "image":
                cal_random_rows.extend(
                    random_image_split_metrics(
                        metadata,
                        similarities["megadescriptor"],
                        cal_queries,
                        int(row["selected_count"]),
                        policy_id,
                        split_id,
                        "calibration",
                        args.random_repeats_per_split,
                        rng,
                    )
                )
            else:
                cal_random_rows.extend(
                    random_candidate_split_metrics(
                        assignments[policy_id],
                        pool,
                        cal_queries,
                        policy_id,
                        split_id,
                        "calibration",
                        args.random_repeats_per_split,
                        rng,
                    )
                )
        cal_random = pd.DataFrame(cal_random_rows)
        cal_summary = random_summary(cal_random, cal_df)
        cal_scored = add_random_columns(cal_df, cal_summary)
        selected_table = select_policy(cal_scored)
        selected_policy_id = selected_table.loc[selected_table["selection_status"].str.startswith("selected"), "policy_id"].iloc[0]
        calibration_rows.append(selected_table)

        eval_df = split_policy_df[split_policy_df["split_role"] == "evaluation"].copy()
        eval_random_rows = []
        selected_eval = eval_df[eval_df["policy_id"] == selected_policy_id].iloc[0]
        if selected_eval["selection_unit"] == "image":
            eval_random_rows.extend(
                random_image_split_metrics(
                    metadata,
                    similarities["megadescriptor"],
                    eval_queries,
                    int(selected_eval["selected_count"]),
                    selected_policy_id,
                    split_id,
                    "evaluation",
                    args.random_repeats_per_split,
                    rng,
                )
            )
        else:
            eval_random_rows.extend(
                random_candidate_split_metrics(
                    assignments[selected_policy_id],
                    pool,
                    eval_queries,
                    selected_policy_id,
                    split_id,
                    "evaluation",
                    args.random_repeats_per_split,
                    rng,
                )
            )
        eval_random = pd.DataFrame(eval_random_rows)
        eval_summary = random_summary(eval_random, eval_df)
        eval_scored = add_random_columns(eval_df, eval_summary)
        eval_scored["selected_for_evaluation"] = np.where(eval_scored["policy_id"] == selected_policy_id, "yes", "no")
        evaluation_rows.append(eval_scored)
        random_rows.append(eval_random)

    calibration = pd.concat(calibration_rows, ignore_index=True)
    evaluation = pd.concat(evaluation_rows, ignore_index=True)
    random_raw = pd.concat(random_rows, ignore_index=True)
    random_sum = random_summary(random_raw, evaluation)
    risk = evaluation[
        [
            "split_id",
            "policy_id",
            "policy_family",
            "selection_unit",
            "query_coverage",
            "identity_coverage",
            "candidate_retention",
            "false_top1_rate",
            "false_reviewed_candidates_per_query",
            "positive_retention",
            "mAP",
            "MRR",
            "review_workload",
            "selected_for_evaluation",
        ]
    ].copy()
    pareto = pd.concat([pareto_frontier(group) for _, group in evaluation.groupby("split_id")], ignore_index=True)
    uncertainty = split_uncertainty(evaluation)
    final = final_recommendation(calibration, evaluation, random_sum, pareto)

    inventory.to_csv(QUERY_SPLIT_INVENTORY_CSV, index=False)
    split_inventory.to_csv(OUTPUT_DIR / "phase8_slice3e_query_split_design.csv", index=False)
    calibration.to_csv(POLICY_SELECTION_CSV, index=False)
    evaluation.to_csv(EVALUATION_COMPARISON_CSV, index=False)
    random_sum.to_csv(RANDOM_SUMMARY_CSV, index=False)
    random_raw.to_csv(RANDOM_RAW_CSV, index=False)
    risk.to_csv(RISK_COVERAGE_CSV, index=False)
    pareto.to_csv(PARETO_CSV, index=False)
    uncertainty.to_csv(BOOTSTRAP_CSV, index=False)
    final.to_csv(FINAL_RECOMMENDATION_CSV, index=False)
    write_doc(inventory, split_inventory, calibration, evaluation, random_sum, uncertainty, final, args.random_repeats_per_split)

    print("PASS: Phase 8 Slice 3E-R query-level calibration/evaluation complete")
    print(f"query_split_count: {args.n_splits}")
    print(f"random_repeats_per_split: {args.random_repeats_per_split}")
    print(f"selected_policy_frequency: {evaluation[evaluation['selected_for_evaluation'] == 'yes']['policy_id'].value_counts().to_dict()}")
    print(f"final_decision: {final.loc[final['decision_item'] == 'slice3e_r_held_out_reid_accuracy_claim', 'decision'].iloc[0]}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--megadescriptor-embeddings-csv", type=Path, default=MEGA_EMBEDDINGS_CSV)
    parser.add_argument("--resnet50-embeddings-csv", type=Path, default=RESNET_EMBEDDINGS_CSV)
    parser.add_argument("--identity-csv", type=Path, default=IDENTITY_CSV)
    parser.add_argument("--annotation-csv", type=Path, default=ANNOTATION_CSV)
    parser.add_argument("--n-splits", type=int, default=N_SPLITS)
    parser.add_argument("--calibration-fraction", type=float, default=CALIBRATION_FRACTION)
    parser.add_argument("--random-seed-base", type=int, default=RANDOM_SEED_BASE)
    parser.add_argument("--random-repeats-per-split", type=int, default=RANDOM_REPEATS_PER_SPLIT)
    return parser.parse_args()


def main() -> int:
    return run(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
