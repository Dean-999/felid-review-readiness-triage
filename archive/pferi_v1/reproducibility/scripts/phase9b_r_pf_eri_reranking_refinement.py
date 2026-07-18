#!/usr/bin/env python3
"""Run Phase 9B-R PF-ERI reranking refinement and visual-utility diagnosis."""

from __future__ import annotations

import argparse
import hashlib
import math
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE9B_DIR = PROJECT_ROOT / "outputs/czechlynx/phase9/pf_eri_fixed_descriptor_reranking"
OUTPUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase9/pf_eri_reranking_refinement"
DOC_PATH = PROJECT_ROOT / "docs/phase9/phase9b_r_pf_eri_reranking_refinement_results.md"

INPUT_INVENTORY_CSV = OUTPUT_DIR / "phase9b_r_input_inventory.csv"
VISUAL_DIAGNOSIS_CSV = OUTPUT_DIR / "phase9b_r_visual_component_diagnosis.csv"
CORRELATION_CSV = OUTPUT_DIR / "phase9b_r_component_correlation_summary.csv"
METHOD_SUMMARY_CSV = OUTPUT_DIR / "phase9b_r_refined_method_metric_summary.csv"
HELDOUT_SPLIT_CSV = OUTPUT_DIR / "phase9b_r_heldout_split_metric_summary.csv"
RANDOM_SIZE_CSV = OUTPUT_DIR / "phase9b_r_random_same_size_controls.csv"
RANDOM_COVERAGE_CSV = OUTPUT_DIR / "phase9b_r_random_same_coverage_controls.csv"
ABLATION_CSV = OUTPUT_DIR / "phase9b_r_feature_ablation_refined_summary.csv"
RISK_COVERAGE_CSV = OUTPUT_DIR / "phase9b_r_risk_coverage_curve.csv"
PARETO_CSV = OUTPUT_DIR / "phase9b_r_pareto_summary.csv"
FINAL_CSV = OUTPUT_DIR / "phase9b_r_final_recommendation.csv"

INPUTS_TO_INSPECT = [
    PROJECT_ROOT / "PROJECT_RULES.md",
    PROJECT_ROOT / "docs/phase9/phase9a_pf_eri_evidence_utility_model_direction_revision.md",
    PROJECT_ROOT / "docs/phase9/phase9b_pf_eri_aware_fixed_descriptor_reranking_results.md",
    PHASE9B_DIR / "phase9b_candidate_level_reranking_table.csv",
    PHASE9B_DIR / "phase9b_method_metric_summary.csv",
    PHASE9B_DIR / "phase9b_heldout_split_metric_summary.csv",
    PHASE9B_DIR / "phase9b_feature_ablation_summary.csv",
    PHASE9B_DIR / "phase9b_risk_coverage_curve.csv",
    PHASE9B_DIR / "phase9b_pareto_summary.csv",
    PHASE9B_DIR / "phase9b_final_recommendation.csv",
    PROJECT_ROOT / "data/labels/czechlynx/czechlynx_phase7a_1000_image_annotations_v1.csv",
    PROJECT_ROOT / "data/labels/czechlynx/czechlynx_mechanism_visual_factors_full_annotated.csv",
]

RANDOM_SEED = 20260615
REPORT_K = 5


def input_inventory(paths: list[Path]) -> pd.DataFrame:
    rows = []
    for path in paths:
        row: dict[str, object] = {
            "input_file": str(path.relative_to(PROJECT_ROOT)),
            "exists": "yes" if path.exists() else "no",
            "row_count": 0,
            "column_count": 0,
            "columns": "",
            "status": "missing",
        }
        if path.exists():
            if path.suffix == ".csv":
                df = pd.read_csv(path)
                row["row_count"] = len(df)
                row["column_count"] = len(df.columns)
                row["columns"] = ";".join(df.columns)
                row["status"] = "available_nonempty" if len(df) else "available_empty"
            else:
                row["status"] = "available_document"
        rows.append(row)
    return pd.DataFrame(rows)


def minmax(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce").astype(float)
    lo = float(values.min(skipna=True))
    hi = float(values.max(skipna=True))
    if not math.isfinite(lo) or not math.isfinite(hi) or hi <= lo:
        return pd.Series(np.zeros(len(values)), index=series.index, dtype=float)
    return (values - lo) / (hi - lo)


def load_candidate_table() -> pd.DataFrame:
    df = pd.read_csv(PHASE9B_DIR / "phase9b_candidate_level_reranking_table.csv")
    df = df[df["descriptor"].isin(["megadescriptor", "resnet50"])].copy()
    df["same_identity"] = df["same_identity_truth_internal"].eq("same")
    df["false_candidate"] = ~df["same_identity"]
    df["reciprocal_support_bool"] = df["reciprocal_support"].eq("yes")
    df["descriptor_disagreement_bool"] = df["descriptor_disagreement"].eq("yes")
    df["descriptor_similarity_norm"] = df.groupby(["split_id", "descriptor"])["base_descriptor_similarity"].transform(minmax)
    df["margin_confidence_norm"] = df.groupby(["split_id", "descriptor"])["margin_confidence"].transform(minmax)
    df["visual_pair_mean"] = (df["query_image_utility_score"] + df["gallery_image_utility_score"]) / 2.0
    df["visual_pair_min"] = df[["query_image_utility_score", "gallery_image_utility_score"]].min(axis=1)
    df["descriptor_confidence_score"] = (
        0.60 * df["descriptor_similarity_norm"]
        + 0.20 * df["reciprocal_support_bool"].astype(float)
        + 0.15 * df["margin_confidence_norm"]
        + 0.05 * (1.0 - df["descriptor_disagreement_bool"].astype(float))
    )
    df["reciprocal_margin_score"] = (df["reciprocal_support_bool"].astype(float) + df["margin_confidence_norm"]) / 2.0
    catastrophic = (
        (df["visual_failure_penalty"] >= 0.35)
        | (df["visual_pair_min"] < 0.25)
        | ((df["visual_pair_min"] < 0.50) & (df["descriptor_disagreement_bool"]))
    )
    df["catastrophic_visual_failure_proxy"] = catastrophic
    df["low_margin_flag"] = df["margin_confidence_norm"] <= df.groupby(["split_id", "descriptor"])["margin_confidence_norm"].transform("median")
    return df


def visual_component_diagnosis(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    eval_df = df[(df["calibration_or_evaluation"] == "evaluation") & (df["descriptor"] == "megadescriptor")].copy()
    for variable in ["visual_pair_mean", "visual_pair_min", "query_image_utility_score", "gallery_image_utility_score", "visual_failure_penalty"]:
        same = eval_df.loc[eval_df["same_identity"], variable]
        diff = eval_df.loc[~eval_df["same_identity"], variable]
        rows.append(
            {
                "diagnostic_item": f"{variable}_same_vs_different",
                "same_mean": float(same.mean()),
                "different_mean": float(diff.mean()),
                "same_minus_different": float(same.mean() - diff.mean()),
                "same_median": float(same.median()),
                "different_median": float(diff.median()),
                "interpretation": "positive_values_mean_visual_higher_for_true_candidates" if same.mean() > diff.mean() else "nonpositive_values_mean_visual_not_higher_for_true_candidates",
            }
        )
    bins = pd.qcut(eval_df["visual_pair_mean"], q=4, duplicates="drop")
    grouped = eval_df.groupby(bins, observed=True)
    for interval, group in grouped:
        rows.append(
            {
                "diagnostic_item": f"visual_pair_mean_bin_{interval}",
                "same_mean": float(group["same_identity"].mean()),
                "different_mean": float(group["false_candidate"].mean()),
                "same_minus_different": float(group["same_identity"].mean() - group["false_candidate"].mean()),
                "same_median": float(group["base_descriptor_similarity"].median()),
                "different_median": float(group["descriptor_confidence_score"].median()),
                "interpretation": "bin_summary_true_rate_false_rate_descriptor_support",
            }
        )
    phase9b = pd.read_csv(PHASE9B_DIR / "phase9b_method_metric_summary.csv")
    full = phase9b[phase9b["method_id"] == "full_pf_eri_candidate_utility"].iloc[0]
    minus_visual = phase9b[phase9b["method_id"] == "full_minus_visual"].iloc[0]
    rows.append(
        {
            "diagnostic_item": "phase9b_full_minus_visual_minus_full",
            "same_mean": float(minus_visual["mean_mAP"]),
            "different_mean": float(full["mean_mAP"]),
            "same_minus_different": float(minus_visual["mean_mAP"] - full["mean_mAP"]),
            "same_median": float(minus_visual["mean_positive_retention"]),
            "different_median": float(full["mean_positive_retention"]),
            "interpretation": "visual_additive_component_reduced_phase9b_map_and_retention" if minus_visual["mean_mAP"] > full["mean_mAP"] else "visual_additive_component_not_harmful_in_phase9b_summary",
        }
    )
    return pd.DataFrame(rows)


def component_correlations(df: pd.DataFrame) -> pd.DataFrame:
    eval_df = df[(df["calibration_or_evaluation"] == "evaluation") & (df["descriptor"] == "megadescriptor")].copy()
    eval_df["same_identity_numeric"] = eval_df["same_identity"].astype(float)
    eval_df["false_candidate_numeric"] = eval_df["false_candidate"].astype(float)
    variables = [
        "visual_pair_mean",
        "visual_pair_min",
        "query_image_utility_score",
        "gallery_image_utility_score",
        "visual_failure_penalty",
        "descriptor_similarity_norm",
        "descriptor_confidence_score",
        "reciprocal_margin_score",
        "margin_confidence_norm",
    ]
    targets = ["same_identity_numeric", "false_candidate_numeric", "descriptor_similarity_norm"]
    rows = []
    for variable in variables:
        for target in targets:
            if variable == target:
                continue
            rows.append(
                {
                    "variable": variable,
                    "target": target,
                    "spearman_correlation": float(eval_df[[variable, target]].corr(method="spearman").iloc[0, 1]),
                    "pearson_correlation": float(eval_df[[variable, target]].corr(method="pearson").iloc[0, 1]),
                    "n": int(eval_df[[variable, target]].dropna().shape[0]),
                }
            )
    for flag in ["descriptor_disagreement_bool", "reciprocal_support_bool", "catastrophic_visual_failure_proxy", "low_margin_flag"]:
        rows.append(
            {
                "variable": flag,
                "target": "same_identity_numeric",
                "spearman_correlation": float(eval_df[[flag, "same_identity_numeric"]].astype(float).corr(method="spearman").iloc[0, 1]),
                "pearson_correlation": float(eval_df[[flag, "same_identity_numeric"]].astype(float).corr(method="pearson").iloc[0, 1]),
                "n": int(len(eval_df)),
            }
        )
    return pd.DataFrame(rows)


def method_grid() -> list[dict[str, object]]:
    methods = [
        {"method_id": "raw_megadescriptor", "descriptor": "megadescriptor", "family": "raw"},
        {"method_id": "raw_resnet50", "descriptor": "resnet50", "family": "raw"},
        {"method_id": "phase9b_candidate_utility_plus_descriptor", "descriptor": "megadescriptor", "family": "phase9b_reference"},
        {"method_id": "phase9b_full_minus_visual", "descriptor": "megadescriptor", "family": "phase9b_reference"},
        {"method_id": "descriptor_confidence_plus_disagreement", "descriptor": "megadescriptor", "family": "refined_descriptor_confidence"},
        {"method_id": "reciprocal_margin_plus_disagreement", "descriptor": "megadescriptor", "family": "refined_descriptor_confidence"},
        {"method_id": "visual_failure_penalty_only", "descriptor": "megadescriptor", "family": "visual_reformulation"},
        {"method_id": "visual_identity_only_no_generic_quality", "descriptor": "megadescriptor", "family": "visual_reformulation"},
        {"method_id": "quality_only_baseline", "descriptor": "megadescriptor", "family": "quality_baseline"},
    ]
    for method_id in [
        "visual_as_gate_only",
        "visual_as_penalty_only",
        "visual_interaction_with_disagreement",
        "visual_interaction_with_low_margin",
        "candidate_utility_with_retention_constraint",
        "candidate_utility_with_coverage_floor",
        "candidate_utility_pareto_selected",
    ]:
        for weight in [0.05, 0.10, 0.20, 0.35]:
            methods.append({"method_id": method_id, "descriptor": "megadescriptor", "family": "refined_pf_eri", "weight": weight})
    return methods


def score_method(pool: pd.DataFrame, method: dict[str, object]) -> pd.DataFrame:
    df = pool[pool["descriptor"] == method["descriptor"]].copy()
    method_id = str(method["method_id"])
    w = float(method.get("weight", 0.15))
    sim = df["descriptor_similarity_norm"]
    visual = df["visual_pair_mean"]
    visual_min = df["visual_pair_min"]
    conf = df["descriptor_confidence_score"]
    reciprocal_margin = df["reciprocal_margin_score"]
    disagreement = df["descriptor_disagreement_bool"].astype(float)
    severe = df["catastrophic_visual_failure_proxy"].astype(float)
    low_margin = df["low_margin_flag"].astype(float)
    failure = df["visual_failure_penalty"]

    if method_id == "raw_megadescriptor" or method_id == "raw_resnet50":
        score = sim
        retain = pd.Series(True, index=df.index)
    elif method_id == "phase9b_candidate_utility_plus_descriptor":
        score = 0.50 * sim + 0.50 * df["candidate_utility_score"]
        retain = pd.Series(True, index=df.index)
    elif method_id == "phase9b_full_minus_visual":
        score = 0.70 * sim + 0.20 * reciprocal_margin + 0.10 * (1.0 - disagreement)
        retain = pd.Series(True, index=df.index)
    elif method_id == "descriptor_confidence_plus_disagreement":
        score = 0.72 * sim + 0.18 * reciprocal_margin + 0.10 * (1.0 - disagreement)
        retain = pd.Series(True, index=df.index)
    elif method_id == "reciprocal_margin_plus_disagreement":
        score = 0.60 * sim + 0.30 * reciprocal_margin + 0.10 * (1.0 - disagreement)
        retain = pd.Series(True, index=df.index)
    elif method_id == "visual_as_gate_only":
        score = 0.72 * sim + 0.18 * reciprocal_margin + 0.10 * (1.0 - disagreement)
        retain = ~df["catastrophic_visual_failure_proxy"]
    elif method_id == "visual_as_penalty_only":
        score = 0.72 * sim + 0.18 * reciprocal_margin + 0.10 * (1.0 - disagreement) - w * failure
        retain = pd.Series(True, index=df.index)
    elif method_id == "visual_failure_penalty_only":
        score = sim - 0.20 * failure
        retain = pd.Series(True, index=df.index)
    elif method_id == "visual_identity_only_no_generic_quality":
        score = 0.75 * sim + 0.25 * visual_min
        retain = pd.Series(True, index=df.index)
    elif method_id == "visual_interaction_with_disagreement":
        score = 0.72 * sim + 0.18 * reciprocal_margin + 0.10 * (1.0 - disagreement) - w * failure * disagreement
        retain = pd.Series(True, index=df.index)
    elif method_id == "visual_interaction_with_low_margin":
        score = 0.72 * sim + 0.18 * reciprocal_margin + 0.10 * (1.0 - disagreement) - w * failure * low_margin
        retain = pd.Series(True, index=df.index)
    elif method_id == "candidate_utility_with_retention_constraint":
        score = 0.58 * sim + 0.22 * df["candidate_utility_score"] + 0.15 * reciprocal_margin + 0.05 * (1.0 - disagreement)
        retain = visual_min >= 0.20
    elif method_id == "candidate_utility_with_coverage_floor":
        score = 0.60 * sim + 0.20 * df["candidate_utility_score"] + 0.15 * reciprocal_margin + 0.05 * (1.0 - disagreement)
        retain = ~(severe.astype(bool) & (visual_min < 0.30))
    elif method_id == "candidate_utility_pareto_selected":
        score = 0.66 * sim + 0.24 * conf + 0.10 * (1.0 - severe)
        retain = visual_min >= 0.15
    elif method_id == "quality_only_baseline":
        score = 0.75 * sim + 0.25 * (1.0 - failure)
        retain = pd.Series(True, index=df.index)
    else:
        raise ValueError(f"unknown method: {method_id}")
    df["rerank_score"] = pd.to_numeric(score, errors="coerce").fillna(-np.inf)
    df["retained"] = retain.astype(bool)
    return df


def retain_topk(scored: pd.DataFrame, query_ids: set[str]) -> pd.DataFrame:
    eligible = scored[scored["query_image_id"].isin(query_ids) & scored["retained"]].copy()
    if eligible.empty:
        return pd.DataFrame(columns=list(scored.columns) + ["reranked_rank"])
    eligible = eligible.sort_values(
        ["query_image_id", "rerank_score", "base_descriptor_similarity"],
        ascending=[True, False, False],
        kind="mergesort",
    )
    eligible["reranked_rank"] = eligible.groupby("query_image_id", sort=False).cumcount() + 1
    return eligible[eligible["reranked_rank"] <= REPORT_K].copy()


def compute_metrics(retained: pd.DataFrame, pool: pd.DataFrame, query_ids: set[str], method_id: str, family: str, descriptor: str) -> dict[str, object]:
    full = pool[(pool["descriptor"] == descriptor) & (pool["query_image_id"].isin(query_ids))]
    positive_queries = set(full.loc[full["same_identity"], "query_image_id"])
    true_total = int(full["same_identity"].sum())
    covered_queries = set(retained["query_image_id"]) if not retained.empty else set()
    retained_true = int(retained["same_identity"].sum()) if not retained.empty else 0
    retained_false = int((~retained["same_identity"]).sum()) if not retained.empty else 0
    groups = {q: g.sort_values("reranked_rank") for q, g in retained.groupby("query_image_id", sort=False)} if not retained.empty else {}
    ap_values = []
    rr_values = []
    top1_values = []
    top5_values = []
    false_top1 = 0
    for q in sorted(query_ids):
        group = groups.get(q)
        if q in positive_queries:
            if group is None or group.empty:
                ap_values.append(0.0)
                rr_values.append(0.0)
                top1_values.append(0)
                top5_values.append(0)
            else:
                rel = group["same_identity"].astype(int).to_numpy()
                ap_values.append(average_precision(rel))
                pos = np.flatnonzero(rel == 1)
                rr_values.append(1.0 / (int(pos[0]) + 1) if len(pos) else 0.0)
                top1_values.append(int(rel[0] == 1))
                top5_values.append(int(rel[: min(REPORT_K, len(rel))].max() == 1))
        if group is not None and not group.empty:
            false_top1 += int(not bool(group.iloc[0]["same_identity"]))
    reviewed = int(len(retained))
    return {
        "method_id": method_id,
        "method_family": family,
        "descriptor": descriptor,
        "query_count": int(len(query_ids)),
        "positive_query_count": int(len(positive_queries)),
        "candidate_pool_count": int(len(full)),
        "retained_candidate_count": reviewed,
        "query_coverage": len(covered_queries) / max(len(query_ids), 1),
        "positive_retention": retained_true / max(true_total, 1),
        "candidate_retention": reviewed / max(len(full), 1),
        "top1_accuracy": float(np.mean(top1_values)) if top1_values else math.nan,
        "top5_accuracy": float(np.mean(top5_values)) if top5_values else math.nan,
        "mAP": float(np.mean(ap_values)) if ap_values else math.nan,
        "MRR": float(np.mean(rr_values)) if rr_values else math.nan,
        "false_top1_rate": false_top1 / max(len(covered_queries), 1) if covered_queries else math.nan,
        "false_candidate_burden": retained_false / max(len(query_ids), 1),
        "reviewed_candidates_per_query": reviewed / max(len(query_ids), 1),
        "coverage_adjusted_mAP": (float(np.mean(ap_values)) if ap_values else 0.0) * (len(covered_queries) / max(len(query_ids), 1)),
    }


def average_precision(relevance: np.ndarray) -> float:
    positives = int(relevance.sum())
    if positives == 0:
        return 0.0
    cumulative = np.cumsum(relevance)
    return float((cumulative[relevance == 1] / (np.flatnonzero(relevance == 1) + 1)).mean())


def calibration_score(metrics: dict[str, object], enforce_retention: bool = False) -> float:
    def val(name: str) -> float:
        try:
            out = float(metrics.get(name, 0.0))
        except (TypeError, ValueError):
            return 0.0
        return out if math.isfinite(out) else 0.0

    score = (
        2.0 * val("mAP")
        + 1.1 * val("MRR")
        + 0.8 * val("top5_accuracy")
        + 1.0 * val("positive_retention")
        + 0.5 * val("query_coverage")
        - 0.25 * val("false_candidate_burden")
        - 0.4 * val("false_top1_rate")
    )
    if enforce_retention and val("positive_retention") < 0.50:
        score -= 2.0 * (0.50 - val("positive_retention"))
    return score


def selected_methods_for_split(pool: pd.DataFrame, methods: list[dict[str, object]], calibration_ids: set[str]) -> list[dict[str, object]]:
    by_method: dict[str, list[tuple[float, dict[str, object], dict[str, object]]]] = {}
    for method in methods:
        scored = score_method(pool, method)
        retained = retain_topk(scored, calibration_ids)
        metrics = compute_metrics(retained, pool, calibration_ids, str(method["method_id"]), str(method["family"]), str(method["descriptor"]))
        score = calibration_score(metrics, enforce_retention=str(method["method_id"]).startswith("candidate_utility"))
        by_method.setdefault(str(method["method_id"]), []).append((score, method, metrics))
    selected = []
    for method_id, rows in by_method.items():
        rows.sort(key=lambda x: (x[0], x[2]["positive_retention"], x[2]["mAP"]), reverse=True)
        best = dict(rows[0][1])
        best["calibration_score"] = rows[0][0]
        selected.append(best)
    return selected


def random_control_distribution(pool: pd.DataFrame, target: pd.DataFrame, query_ids: set[str], descriptor: str, split_id: int, repeats: int, mode: str, cache_label: str) -> pd.DataFrame:
    digest = hashlib.sha256(f"{cache_label}:{mode}".encode("utf-8")).hexdigest()
    stable_offset = int(digest[:8], 16) % 997
    rng = np.random.default_rng(RANDOM_SEED + split_id * 1000 + stable_offset)
    base = pool[(pool["descriptor"] == descriptor) & (pool["query_image_id"].isin(query_ids))]
    grouped = {
        q: {
            "truth": group.sort_values("base_descriptor_similarity", ascending=False)["same_identity"].astype(bool).to_numpy(),
            "similarity": group.sort_values("base_descriptor_similarity", ascending=False)["base_descriptor_similarity"].to_numpy(),
        }
        for q, group in base.groupby("query_image_id", sort=False)
    }
    true_total = int(base["same_identity"].sum())
    positive_queries = set(base.loc[base["same_identity"], "query_image_id"])
    target_counts = target.groupby("query_image_id").size().to_dict() if not target.empty else {}
    covered_target = sorted(target["query_image_id"].unique()) if not target.empty else []
    avg_count = max(1, int(round(len(target) / max(len(covered_target), 1)))) if covered_target else 0
    rows = []
    for repeat in range(1, repeats + 1):
        eligible = set(rng.choice(sorted(query_ids), size=min(len(covered_target), len(query_ids)), replace=False)) if mode == "same_coverage" and covered_target else set(query_ids)
        retained_true = retained_false = retained_count = covered_count = false_top1 = 0
        ap_values = []
        rr_values = []
        top1_values = []
        top5_values = []
        for q in sorted(query_ids):
            if q not in eligible:
                if q in positive_queries:
                    ap_values.append(0.0)
                    rr_values.append(0.0)
                    top1_values.append(0)
                    top5_values.append(0)
                continue
            group = grouped.get(q)
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
            idx = rng.choice(np.arange(len(group["truth"])), size=count, replace=False)
            idx = idx[np.argsort(-group["similarity"][idx])]
            rel = group["truth"][idx].astype(int)
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
        rows.append(
            {
                "mAP": float(np.mean(ap_values)) if ap_values else math.nan,
                "MRR": float(np.mean(rr_values)) if rr_values else math.nan,
                "top1_accuracy": float(np.mean(top1_values)) if top1_values else math.nan,
                "top5_accuracy": float(np.mean(top5_values)) if top5_values else math.nan,
                "false_top1_rate": false_top1 / max(covered_count, 1) if covered_count else math.nan,
                "false_candidate_burden": retained_false / max(len(query_ids), 1),
                "query_coverage": covered_count / max(len(query_ids), 1),
                "positive_retention": retained_true / max(true_total, 1),
            }
        )
    return pd.DataFrame(rows)


def random_control_summary(frame: pd.DataFrame, target_metrics: dict[str, object], descriptor: str, split_id: int, method_id: str, repeats: int, mode: str) -> dict[str, object]:
    out: dict[str, object] = {"split_id": split_id, "target_method_id": method_id, "descriptor": descriptor, "random_control_type": mode, "random_repeat_count": repeats}
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
        out[f"{metric}_beats_random_mean"] = "yes" if (method_value < float(values.mean()) if metric.startswith("false") else method_value > float(values.mean())) else "no"
    return out


def aggregate(evaluation: pd.DataFrame, random_size: pd.DataFrame, random_coverage: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for method_id, group in evaluation.groupby("method_id", sort=False):
        row = {"method_id": method_id, "method_family": group["method_family"].iloc[0], "descriptor": group["descriptor"].iloc[0], "split_count": group["split_id"].nunique()}
        for metric in ["mAP", "MRR", "top1_accuracy", "top5_accuracy", "false_top1_rate", "false_candidate_burden", "query_coverage", "positive_retention", "candidate_retention", "reviewed_candidates_per_query", "coverage_adjusted_mAP"]:
            row[f"mean_{metric}"] = float(pd.to_numeric(group[metric], errors="coerce").mean())
            row[f"std_{metric}"] = float(pd.to_numeric(group[metric], errors="coerce").std(ddof=0))
        rows.append(row)
    summary = pd.DataFrame(rows)
    baselines = {
        "raw_megadescriptor": "raw_megadescriptor",
        "quality_only": "quality_only_baseline",
        "phase9b_candidate_utility": "phase9b_candidate_utility_plus_descriptor",
        "phase9b_full_minus_visual": "phase9b_full_minus_visual",
    }
    for label, method in baselines.items():
        base = summary[summary["method_id"] == method]
        if base.empty:
            continue
        for metric in ["mAP", "MRR", "top5_accuracy", "false_candidate_burden"]:
            summary[f"{metric}_minus_{label}"] = summary[f"mean_{metric}"] - float(base.iloc[0][f"mean_{metric}"])
    for label, control in [("random_same_size", random_size), ("random_same_coverage", random_coverage)]:
        grouped = control.groupby("target_method_id").agg({"mAP_minus_random_mean": "mean", "MRR_minus_random_mean": "mean", "false_candidate_burden_minus_random_mean": "mean", "positive_retention_minus_random_mean": "mean"})
        for col in grouped.columns:
            summary[f"{label}_{col}"] = summary["method_id"].map(grouped[col])
    return summary


def pareto(evaluation: pd.DataFrame) -> pd.DataFrame:
    df = evaluation.copy()
    max_metrics = ["mAP", "MRR", "top1_accuracy", "top5_accuracy", "positive_retention", "query_coverage"]
    min_metrics = ["false_candidate_burden", "false_top1_rate", "reviewed_candidates_per_query"]
    flags = []
    for _, row in df.iterrows():
        dominated = False
        same_split = df[df["split_id"] == row["split_id"]]
        for _, other in same_split.iterrows():
            if other["method_id"] == row["method_id"]:
                continue
            ge = all(float(other[m]) >= float(row[m]) for m in max_metrics if pd.notna(other[m]) and pd.notna(row[m]))
            le = all(float(other[m]) <= float(row[m]) for m in min_metrics if pd.notna(other[m]) and pd.notna(row[m]))
            strict = any(float(other[m]) > float(row[m]) for m in max_metrics if pd.notna(other[m]) and pd.notna(row[m])) or any(float(other[m]) < float(row[m]) for m in min_metrics if pd.notna(other[m]) and pd.notna(row[m]))
            if ge and le and strict:
                dominated = True
                break
        flags.append("no" if dominated else "yes")
    df["pareto_efficient"] = flags
    return df


def final_recommendation(summary: pd.DataFrame) -> tuple[pd.DataFrame, str, str]:
    eligible = summary[
        (summary["mean_mAP"] > float(summary.loc[summary["method_id"] == "raw_megadescriptor", "mean_mAP"].iloc[0]))
        & (summary["mean_mAP"] > float(summary.loc[summary["method_id"] == "quality_only_baseline", "mean_mAP"].iloc[0]))
        & (summary["mean_positive_retention"] >= 0.50)
        & (summary["mean_query_coverage"] >= 0.50)
        & (summary["mean_false_candidate_burden"] <= float(summary.loc[summary["method_id"] == "raw_megadescriptor", "mean_false_candidate_burden"].iloc[0]) + 0.05)
    ].copy()
    eligible = eligible[eligible["random_same_size_mAP_minus_random_mean"].fillna(0) > 0]
    eligible = eligible[eligible["random_same_coverage_mAP_minus_random_mean"].fillna(0) > 0]
    if eligible.empty:
        decision = "phase9b_r_does_not_support_phase9c"
        best_method = summary.sort_values(["mean_mAP", "mean_positive_retention"], ascending=False).iloc[0]["method_id"]
        rationale = "no refined method satisfied all mAP, retention, coverage, random-control, and risk criteria"
    else:
        best = eligible.sort_values(["mean_mAP", "mean_positive_retention"], ascending=False).iloc[0]
        best_method = str(best["method_id"])
        strong = best["mean_mAP"] >= float(summary.loc[summary["method_id"] == "phase9b_full_minus_visual", "mean_mAP"].iloc[0]) - 0.005 and best["mean_positive_retention"] >= 0.53
        decision = "phase9b_r_supports_cautious_phase9c_planning" if strong else "phase9b_r_supports_refined_no_training_reranking_only"
        rationale = "best eligible method passed required criteria" + (" and near/above full-minus-visual target" if strong else " but did not meet the stronger preferred target")
    rows = [
        {"decision_item": "phase9b_r_refinement_decision", "decision": decision, "rationale": rationale},
        {"decision_item": "best_refined_method", "decision": best_method, "rationale": "selected from aggregate held-out summary"},
        {"decision_item": "phase9c_recommended", "decision": "no" if decision == "phase9b_r_does_not_support_phase9c" else "cautious_planning_only", "rationale": "no training may begin without explicit approval and separate feasibility audit"},
        {"decision_item": "visual_utility_interpretation", "decision": "visual_not_best_as_additive_score", "rationale": "Phase 9B and 9B-R compare additive, gate, penalty, and interaction visual formulations"},
    ]
    return pd.DataFrame(rows), decision, best_method


def markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    out = frame.copy()
    for col in out.columns:
        if pd.api.types.is_numeric_dtype(out[col]):
            out[col] = out[col].map(lambda x: "" if pd.isna(x) else f"{float(x):.4f}")
        else:
            out[col] = out[col].astype(str)
    lines = ["| " + " | ".join(out.columns) + " |", "| " + " | ".join(["---"] * len(out.columns)) + " |"]
    for _, row in out.iterrows():
        lines.append("| " + " | ".join(str(row[col]) for col in out.columns) + " |")
    return "\n".join(lines)


def make_doc(summary: pd.DataFrame, visual: pd.DataFrame, corr: pd.DataFrame, final: pd.DataFrame, pareto_df: pd.DataFrame, repeats: int) -> str:
    best_method = final.loc[final["decision_item"] == "best_refined_method", "decision"].iloc[0]
    decision = final.loc[final["decision_item"] == "phase9b_r_refinement_decision", "decision"].iloc[0]
    best = summary[summary["method_id"] == best_method].iloc[0]
    lines = [
        "# Phase 9B-R PF-ERI Reranking Refinement Results",
        "",
        "## 1. Purpose",
        "",
        "Phase 9B-R diagnoses why the visual utility component did not help as an additive reranking term and tests transparent no-training refinement variants.",
        "",
        "## 2. Relationship to Phase 9B",
        "",
        "Phase 9B showed modest held-out mAP improvement for PF-ERI-aware reranking but failed the pre-set positive-retention criterion. The strongest ablation was `full_minus_visual`, so this slice tests whether visual utility should be used as a gate, penalty, interaction, or workflow-safety signal rather than a simple additive term.",
        "",
        "## 3. Visual Component Diagnosis",
        "",
        markdown_table(visual.head(12)),
        "",
        "## 4. Diagnostic Correlations",
        "",
        markdown_table(corr.sort_values("spearman_correlation", ascending=False).head(12)),
        "",
        "## 5. Refined Methods Tested",
        "",
        ", ".join(summary["method_id"].tolist()),
        "",
        "## 6. Held-Out Split Design and Random Controls",
        "",
        f"The refinement reused the Phase 9B held-out query split roles from the public candidate table. Random same-size and same-coverage controls used `{repeats}` repeats.",
        "",
        "## 7. Main Refined Metric Results",
        "",
        markdown_table(summary.sort_values("mean_mAP", ascending=False).head(10)[["method_id", "mean_mAP", "mean_MRR", "mean_top1_accuracy", "mean_top5_accuracy", "mean_false_candidate_burden", "mean_query_coverage", "mean_positive_retention"]]),
        "",
        "## 8. Success Criteria Decision",
        "",
        f"Decision: `{decision}`.",
        f"Best refined method: `{best_method}` with mAP `{best['mean_mAP']:.4f}`, MRR `{best['mean_MRR']:.4f}`, top-1 `{best['mean_top1_accuracy']:.4f}`, top-5 `{best['mean_top5_accuracy']:.4f}`, query coverage `{best['mean_query_coverage']:.4f}`, and positive retention `{best['mean_positive_retention']:.4f}`.",
        "",
        "## 9. Risk-Coverage and Pareto Interpretation",
        "",
        f"Pareto-efficient held-out method/split rows: `{int((pareto_df['pareto_efficient'] == 'yes').sum())}` of `{len(pareto_df)}`. Interpret mAP gains with positive retention, query coverage, and false-candidate burden.",
        "",
        "## 10. Decision on Phase 9C",
        "",
        "Do not begin Phase 9C training from this document alone. If the decision permits cautious planning, it still requires explicit approval and a separate feasibility audit.",
        "",
        "## 11. Allowed Claims",
        "",
        "- Phase 9B-R evaluates no-training PF-ERI reranking refinements under CzechLynx held-out query validation.",
        "- Visual utility appears weaker as a simple additive reranking term than descriptor-confidence, reciprocal/margin, and disagreement components in this fixed-descriptor setting.",
        "- Refined no-training methods can be compared against raw, quality-only, Phase 9B, and random controls.",
        "",
        "## 12. Forbidden Claims",
        "",
        "- PF-ERI is a new Re-ID descriptor.",
        "- PF-ERI is a new deep Re-ID model.",
        "- PF-ERI performs automatic identity assignment or true individual identification.",
        "- PF-ERI is validated on Mainland Clouded Leopard or Marbled Cat.",
        "- PF-ERI is field deployment ready or supports population estimation, movement, occupancy, abundance, survival, or site-use inference.",
        "- PF-ERI robustly improves Re-ID accuracy beyond the bounded CzechLynx fixed-descriptor setting.",
        "",
        "## 13. Confirmation",
        "",
        "No training, no external data download, no frozen-data edit, no delayed second-review access, no staging, and no commit were performed.",
        "",
    ]
    return "\n".join(lines)


def run(args: argparse.Namespace) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    inventory = input_inventory(INPUTS_TO_INSPECT)
    inventory.to_csv(INPUT_INVENTORY_CSV, index=False)
    candidates = load_candidate_table()
    visual = visual_component_diagnosis(candidates)
    corr = component_correlations(candidates)
    visual.to_csv(VISUAL_DIAGNOSIS_CSV, index=False)
    corr.to_csv(CORRELATION_CSV, index=False)

    methods = method_grid()
    eval_rows = []
    random_size_rows = []
    random_coverage_rows = []
    for split_id, split_df in candidates.groupby("split_id", sort=True):
        calibration_ids = set(split_df.loc[split_df["calibration_or_evaluation"] == "calibration", "query_image_id"])
        evaluation_ids = set(split_df.loc[split_df["calibration_or_evaluation"] == "evaluation", "query_image_id"])
        selected = selected_methods_for_split(split_df, methods, calibration_ids)
        random_cache: dict[tuple[str, str, tuple[tuple[str, int], ...] | tuple[int, int]], pd.DataFrame] = {}
        for method in selected:
            scored = score_method(split_df, method)
            retained = retain_topk(scored, evaluation_ids)
            metrics = compute_metrics(retained, split_df, evaluation_ids, str(method["method_id"]), str(method["family"]), str(method["descriptor"]))
            metrics["split_id"] = int(split_id)
            metrics["split_role"] = "evaluation"
            metrics["calibrated_weight"] = method.get("weight", math.nan)
            metrics["calibration_score"] = method.get("calibration_score", math.nan)
            eval_rows.append(metrics)
            if method["method_id"] not in {"raw_megadescriptor", "raw_resnet50"}:
                target_counts = tuple(sorted((str(k), int(v)) for k, v in retained.groupby("query_image_id").size().to_dict().items()))
                size_key = (str(method["descriptor"]), "same_size", target_counts)
                if size_key not in random_cache:
                    random_cache[size_key] = random_control_distribution(split_df, retained, evaluation_ids, str(method["descriptor"]), int(split_id), args.random_repeats, "same_size", str(size_key))
                random_size_rows.append(random_control_summary(random_cache[size_key], metrics, str(method["descriptor"]), int(split_id), str(method["method_id"]), args.random_repeats, "same_size"))

                coverage_key = (str(method["descriptor"]), "same_coverage", (int(retained["query_image_id"].nunique()), int(round(len(retained) / max(int(retained["query_image_id"].nunique()), 1))) if not retained.empty else 0))
                if coverage_key not in random_cache:
                    random_cache[coverage_key] = random_control_distribution(split_df, retained, evaluation_ids, str(method["descriptor"]), int(split_id), args.random_repeats, "same_coverage", str(coverage_key))
                random_coverage_rows.append(random_control_summary(random_cache[coverage_key], metrics, str(method["descriptor"]), int(split_id), str(method["method_id"]), args.random_repeats, "same_coverage"))

    evaluation = pd.DataFrame(eval_rows)
    random_size = pd.DataFrame(random_size_rows)
    random_coverage = pd.DataFrame(random_coverage_rows)
    summary = aggregate(evaluation, random_size, random_coverage)
    ablation = summary[summary["method_family"].isin(["visual_reformulation", "refined_pf_eri", "refined_descriptor_confidence"])].copy()
    risk = evaluation[["split_id", "method_id", "method_family", "descriptor", "query_coverage", "positive_retention", "false_candidate_burden", "mAP", "MRR", "top1_accuracy", "top5_accuracy", "false_top1_rate", "reviewed_candidates_per_query", "calibrated_weight"]].rename(columns={"calibrated_weight": "threshold_or_weight_setting", "reviewed_candidates_per_query": "review_workload"})
    pareto_df = pareto(evaluation)
    final, _, _ = final_recommendation(summary)

    summary.to_csv(METHOD_SUMMARY_CSV, index=False)
    evaluation.to_csv(HELDOUT_SPLIT_CSV, index=False)
    random_size.to_csv(RANDOM_SIZE_CSV, index=False)
    random_coverage.to_csv(RANDOM_COVERAGE_CSV, index=False)
    ablation.to_csv(ABLATION_CSV, index=False)
    risk.to_csv(RISK_COVERAGE_CSV, index=False)
    pareto_df.to_csv(PARETO_CSV, index=False)
    final.to_csv(FINAL_CSV, index=False)
    DOC_PATH.write_text(make_doc(summary, visual, corr, final, pareto_df, args.random_repeats), encoding="utf-8")
    print(f"wrote {OUTPUT_DIR}")
    print(final.to_string(index=False))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--random-repeats", type=int, default=200)
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
