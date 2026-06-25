#!/usr/bin/env python3
"""Optimize staged PF-ERI Retrieval-Control v4 variants on CzechLynx."""

from __future__ import annotations

import argparse
import math
from itertools import product
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from phase8_descriptor_disagreement_false_neighbor_confidence_control import (
    ANNOTATION_CSV,
    IDENTITY_CSV,
    MEGA_EMBEDDINGS_CSV,
    RESNET_EMBEDDINGS_CSV,
    build_mega_candidates,
    failure_flags,
    threshold_value,
    v2_policy,
)
from phase8_pf_eri_retrieval_control_v2_optimizer import align_inputs, average_precision

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase8/pf_eri_deep_algorithm_v4"
FIGURE_DIR = OUTPUT_DIR / "figures"

VARIANT_COMPARISON_CSV = OUTPUT_DIR / "phase8_pf_eri_v4_variant_comparison.csv"
POLICY_GRID_CSV = OUTPUT_DIR / "phase8_pf_eri_v4_policy_grid.csv"
TOP_VARIANTS_CSV = OUTPUT_DIR / "phase8_pf_eri_v4_top_variants.csv"
ASSIGNMENTS_CSV = OUTPUT_DIR / "phase8_pf_eri_v4_recommended_assignments.csv"
BOOTSTRAP_CSV = OUTPUT_DIR / "phase8_pf_eri_v4_bootstrap_intervals.csv"
SENSITIVITY_CSV = OUTPUT_DIR / "phase8_pf_eri_v4_sensitivity_audit.csv"
FAILURE_SUMMARY_CSV = OUTPUT_DIR / "phase8_pf_eri_v4_failure_mode_summary.csv"
ALGORITHM_DECISION_CSV = OUTPUT_DIR / "phase8_pf_eri_v4_algorithm_decision.csv"

RANDOM_SEED = 20260614
BOOTSTRAP_ITERATIONS = 300
QUERY_COUNT = 500

VALID_DETAIL_CLASSES = [
    "review_clear",
    "review_caution",
    "defer_visual",
    "defer_descriptor_conflict",
    "defer_low_confidence",
    "exclude_inadmissible",
]
VALID_SIMPLE_CLASSES = ["review_candidate", "defer_candidate", "exclude_candidate"]


def add_retrieval_confidence_features(candidates: pd.DataFrame, similarities: dict[str, np.ndarray]) -> pd.DataFrame:
    df = candidates.copy()
    mega = similarities["megadescriptor"]
    resnet = similarities["resnet50"]
    n = mega.shape[0]
    reciprocal_mega = np.zeros(len(df), dtype=int)
    reciprocal_resnet = np.zeros(len(df), dtype=int)
    top1_gap = np.zeros(len(df), dtype=float)
    candidate_next_gap = np.zeros(len(df), dtype=float)
    mega_rank_score = np.zeros(len(df), dtype=float)
    for query_idx, group in df.groupby("query_idx", sort=False):
        q = int(query_idx)
        mega_scores = mega[q].copy()
        mega_scores[q] = -np.inf
        order = np.argsort(-mega_scores)
        top_scores = mega_scores[order[:21]]
        q_top1_gap = float(top_scores[0] - top_scores[1]) if len(top_scores) > 1 else 0.0
        for pos, idx in enumerate(group.index):
            gallery_idx = int(df.at[idx, "gallery_idx"])
            gallery_mega_scores = mega[gallery_idx].copy()
            gallery_resnet_scores = resnet[gallery_idx].copy()
            gallery_mega_scores[gallery_idx] = -np.inf
            gallery_resnet_scores[gallery_idx] = -np.inf
            reciprocal_mega[idx] = int(np.where(np.argsort(-gallery_mega_scores) == q)[0][0] + 1)
            reciprocal_resnet[idx] = int(np.where(np.argsort(-gallery_resnet_scores) == q)[0][0] + 1)
            top1_gap[idx] = q_top1_gap
            rank = int(df.at[idx, "rank"])
            if rank < 20:
                next_score = float(group.loc[group["rank"] == rank + 1, "megadescriptor_similarity"].iloc[0])
                candidate_next_gap[idx] = float(df.at[idx, "megadescriptor_similarity"] - next_score)
            else:
                candidate_next_gap[idx] = 0.0
            mega_rank_score[idx] = 1.0 - ((rank - 1) / 19.0)
    df["mega_reciprocal_rank"] = reciprocal_mega
    df["resnet50_reciprocal_rank"] = reciprocal_resnet
    df["top1_top2_margin"] = top1_gap
    df["candidate_next_margin"] = candidate_next_gap
    df["mega_rank_score"] = mega_rank_score
    df["reciprocal_support"] = (df["mega_reciprocal_rank"] <= 10) & (df["resnet50_reciprocal_rank"] <= 20)
    df["margin_confidence"] = np.where(df["rank"] == 1, df["top1_top2_margin"], df["candidate_next_margin"])
    df["descriptor_consensus"] = (df["resnet50_rank"] <= 10) & ~df["rank_gap_ge_10"]
    return df


def policy_grid() -> list[dict[str, object]]:
    policies: list[dict[str, object]] = [
        {
            "variant_id": "v4_0001",
            "variant_family": "candidate_f_baseline",
            "variant_label": "Candidate F baseline",
            "top_k": 5,
            "visual_threshold": 50.0,
            "clear_visual_threshold": 75.0,
            "disagreement_definition": "rank_gap_ge_10",
            "margin_threshold": 0.03,
            "reciprocal_rank_threshold": 10,
            "workload_cap": 5,
            "algorithm_role": "baseline",
        }
    ]
    pid = 2
    families = [
        "evidence_admissibility_first",
        "retrieval_margin_confidence",
        "reciprocal_retrieval_support",
        "cross_descriptor_consensus_visual_rescue",
        "risk_calibrated_review_tiers",
        "topk_burden_optimizer",
        "diagnostic_reranking_exploratory",
    ]
    for family, top_k, visual, clear_visual, disagreement, margin, reciprocal, workload in product(
        families,
        [3, 5, 10],
        [50.0, 75.0],
        [75.0],
        ["rank_gap_ge_10", "similarity_high_resnet_low", "absent_resnet_top5"],
        [0.03, 0.05],
        [5, 10],
        [3, 5],
    ):
        policies.append(
            {
                "variant_id": f"v4_{pid:04d}",
                "variant_family": family,
                "variant_label": family.replace("_", " "),
                "top_k": top_k,
                "visual_threshold": visual,
                "clear_visual_threshold": max(clear_visual, visual),
                "disagreement_definition": disagreement,
                "margin_threshold": margin,
                "reciprocal_rank_threshold": reciprocal,
                "workload_cap": workload,
                "algorithm_role": "rule_based" if family != "diagnostic_reranking_exploratory" else "exploratory_formula",
            }
        )
        pid += 1
    return policies


def simple_class(detail: pd.Series) -> pd.Series:
    return detail.map(
        {
            "review_clear": "review_candidate",
            "review_caution": "review_candidate",
            "defer_visual": "defer_candidate",
            "defer_descriptor_conflict": "defer_candidate",
            "defer_low_confidence": "defer_candidate",
            "exclude_inadmissible": "exclude_candidate",
        }
    )


def assign_variant(candidates: pd.DataFrame, policy: dict[str, object]) -> pd.DataFrame:
    df = candidates[candidates["rank"] <= int(policy["top_k"])].copy().sort_values(["query_idx", "rank"]).reset_index(drop=True)
    dis = df[str(policy["disagreement_definition"])]
    severe = df["pattern_none"] | df["severe_blur"] | df["major_occlusion"] | df["frontal_rear"]
    visual_ok = df["pair_min_score"] >= float(policy["visual_threshold"])
    visual_clear = df["pair_min_score"] >= float(policy["clear_visual_threshold"])
    reciprocal = (df["mega_reciprocal_rank"] <= int(policy["reciprocal_rank_threshold"])) & (df["resnet50_reciprocal_rank"] <= int(policy["reciprocal_rank_threshold"]) * 2)
    margin_ok = df["margin_confidence"] >= float(policy["margin_threshold"])
    consensus = df["descriptor_consensus"]
    family = str(policy["variant_family"])
    detail = pd.Series("defer_low_confidence", index=df.index, dtype=object)

    if family == "candidate_f_baseline":
        q_pass = df["query_score"] >= threshold_value("low_or_higher")
        g_pass = df["gallery_score"] >= threshold_value("medium_or_higher")
        pair_pass = df["pair_min_score"] >= threshold_value("low_or_higher")
        v2_pass = q_pass & g_pass & pair_pass & ~severe
        detail[~v2_pass] = "defer_visual"
        detail[v2_pass & dis] = "review_caution"
        detail[v2_pass & ~dis] = "review_clear"
    elif family == "evidence_admissibility_first":
        detail[severe | df["pattern_none"]] = "exclude_inadmissible"
        detail[~severe & ~visual_ok] = "defer_visual"
        detail[~severe & visual_ok & dis] = "defer_descriptor_conflict"
        detail[~severe & visual_clear & ~dis] = "review_clear"
        detail[~severe & visual_ok & ~visual_clear & ~dis] = "review_caution"
    elif family == "retrieval_margin_confidence":
        detail[severe | ~visual_ok] = "defer_visual"
        detail[visual_ok & ~severe & margin_ok & consensus] = "review_clear"
        detail[visual_ok & ~severe & (margin_ok | consensus) & ~detail.eq("review_clear")] = "review_caution"
        detail[visual_ok & ~severe & dis & ~margin_ok] = "defer_descriptor_conflict"
    elif family == "reciprocal_retrieval_support":
        detail[severe | ~visual_ok] = "defer_visual"
        detail[visual_ok & ~severe & reciprocal & ~dis] = "review_clear"
        detail[visual_ok & ~severe & reciprocal & dis] = "review_caution"
        detail[visual_ok & ~severe & ~reciprocal] = "defer_low_confidence"
    elif family == "cross_descriptor_consensus_visual_rescue":
        detail[severe | ~visual_ok] = "defer_visual"
        detail[visual_ok & ~severe & consensus & ~dis] = "review_clear"
        detail[visual_clear & ~severe & dis] = "review_caution"
        detail[visual_ok & ~visual_clear & ~severe & dis] = "defer_descriptor_conflict"
        detail[visual_ok & ~severe & ~dis & ~consensus] = "review_caution"
    elif family == "risk_calibrated_review_tiers":
        strong = visual_clear & ~severe & (consensus | reciprocal) & margin_ok & ~dis
        caution = visual_ok & ~severe & ((consensus | reciprocal | margin_ok) | (visual_clear & dis))
        detail[severe | df["pattern_none"]] = "exclude_inadmissible"
        detail[~severe & ~visual_ok] = "defer_visual"
        detail[strong] = "review_clear"
        detail[caution & ~strong] = "review_caution"
        detail[visual_ok & ~severe & dis & ~caution] = "defer_descriptor_conflict"
    elif family == "topk_burden_optimizer":
        supported = visual_ok & ~severe & ((consensus & margin_ok) | reciprocal)
        df["_support_score"] = (
            df["megadescriptor_similarity"]
            + 0.002 * df["pair_min_score"]
            + 0.05 * reciprocal.astype(float)
            + 0.03 * consensus.astype(float)
            - 0.08 * dis.astype(float)
            - 0.20 * severe.astype(float)
        )
        detail[severe | ~visual_ok] = "defer_visual"
        detail[visual_ok & ~severe & dis & ~supported] = "defer_descriptor_conflict"
        for _, group in df.groupby("query_idx", sort=False):
            ranked = group[supported.loc[group.index]].sort_values("_support_score", ascending=False)
            keep = ranked.head(int(policy["workload_cap"])).index
            detail.loc[keep] = np.where(dis.loc[keep], "review_caution", "review_clear")
    elif family == "diagnostic_reranking_exploratory":
        score = (
            df["megadescriptor_similarity"]
            + 0.002 * df["pair_min_score"]
            - 0.06 * dis.astype(float)
            - 0.12 * severe.astype(float)
            + 0.04 * reciprocal.astype(float)
            + 0.02 * margin_ok.astype(float)
        )
        df["_diagnostic_score"] = score
        detail[severe | ~visual_ok] = "defer_visual"
        for _, group in df.groupby("query_idx", sort=False):
            keep = group.sort_values("_diagnostic_score", ascending=False).head(int(policy["workload_cap"])).index
            eligible = keep[visual_ok.loc[keep] & ~severe.loc[keep]]
            detail.loc[eligible] = np.where(dis.loc[eligible], "review_caution", "review_clear")
    else:
        raise ValueError(f"Unknown variant family: {family}")

    df["detailed_assignment"] = detail
    df["assignment"] = simple_class(detail)
    df["active_disagreement"] = dis
    df["reciprocal_support_flag"] = reciprocal
    df["margin_confidence_flag"] = margin_ok
    df["confidence_tier"] = np.select(
        [
            df["detailed_assignment"] == "review_clear",
            df["detailed_assignment"] == "review_caution",
            df["detailed_assignment"].str.startswith("defer"),
        ],
        ["clear", "caution", "defer"],
        default="exclude",
    )
    return df.drop(columns=[c for c in ["_support_score", "_diagnostic_score"] if c in df.columns])


def average_precision_from_relevance(relevance: np.ndarray) -> float:
    return average_precision(relevance)


def query_level_summary(assigned: pd.DataFrame) -> pd.DataFrame:
    assigned = assigned.sort_values(["query_idx", "rank"])
    rows = []
    for query_idx, group in assigned.groupby("query_idx", sort=True):
        review = group[group["assignment"] == "review_candidate"].sort_values("rank")
        relevance = review["same_identity"].to_numpy(dtype=int)
        has_review = len(review) > 0
        has_positive = bool(relevance.sum() > 0) if has_review else False
        first_positive = int(np.flatnonzero(relevance == 1)[0]) + 1 if has_positive else 0
        rows.append(
            {
                "query_idx": int(query_idx),
                "candidate_count": int(len(group)),
                "review_count": int(len(review)),
                "has_review": int(has_review),
                "has_positive_review": int(has_positive),
                "false_top1": int(has_review and relevance[0] == 0),
                "top1": int(has_positive and relevance[0] == 1),
                "top3": int(has_positive and relevance[: min(3, len(relevance))].max() == 1),
                "top5": int(has_positive and relevance[: min(5, len(relevance))].max() == 1),
                "ap": average_precision_from_relevance(relevance) if has_positive else math.nan,
                "rr": 1.0 / first_positive if first_positive else math.nan,
                "true_total": int(group["same_identity"].sum()),
                "true_reviewed": int(review["same_identity"].sum()),
                "false_reviewed": int((~review["same_identity"]).sum()) if has_review else 0,
                "disagreement_review": float(review["active_disagreement"].mean()) if has_review else math.nan,
                "reciprocal_review": float(review["reciprocal_support_flag"].mean()) if has_review else math.nan,
                "margin_review": float(review["margin_confidence"].mean()) if has_review else math.nan,
                "clear_review_count": int((review["detailed_assignment"] == "review_clear").sum()),
                "caution_review_count": int((review["detailed_assignment"] == "review_caution").sum()),
                "clear_false_count": int((review["detailed_assignment"].eq("review_clear") & ~review["same_identity"]).sum()),
                "caution_false_count": int((review["detailed_assignment"].eq("review_caution") & ~review["same_identity"]).sum()),
            }
        )
    return pd.DataFrame(rows)


def compute_metrics(assigned: pd.DataFrame, policy: dict[str, object]) -> dict[str, object]:
    review = assigned[assigned["assignment"] == "review_candidate"]
    defer = assigned[assigned["assignment"] == "defer_candidate"]
    exclude = assigned[assigned["assignment"] == "exclude_candidate"]
    ordered = assigned.sort_values(["query_idx", "rank"])
    k = int(len(ordered) / QUERY_COUNT)
    review_matrix = (ordered["assignment"].to_numpy() == "review_candidate").reshape(QUERY_COUNT, k)
    same_matrix = ordered["same_identity"].to_numpy(dtype=bool).reshape(QUERY_COUNT, k)
    has_review = review_matrix.any(axis=1)
    has_positive = (review_matrix & same_matrix).any(axis=1)
    false_top1 = np.zeros(QUERY_COUNT, dtype=int)
    top1 = np.zeros(QUERY_COUNT, dtype=int)
    top3 = np.zeros(QUERY_COUNT, dtype=int)
    top5 = np.zeros(QUERY_COUNT, dtype=int)
    aps: list[float] = []
    rrs: list[float] = []
    for i in range(QUERY_COUNT):
        if not has_review[i]:
            continue
        relevance = same_matrix[i][review_matrix[i]].astype(int)
        false_top1[i] = int(relevance[0] == 0)
        if relevance.sum() > 0:
            first_positive = int(np.flatnonzero(relevance == 1)[0]) + 1
            top1[i] = int(relevance[0] == 1)
            top3[i] = int(relevance[: min(3, len(relevance))].max() == 1)
            top5[i] = int(relevance[: min(5, len(relevance))].max() == 1)
            aps.append(average_precision_from_relevance(relevance))
            rrs.append(1.0 / first_positive)
    true_total = int(assigned["same_identity"].sum())
    true_review = int(review["same_identity"].sum())
    clear = review[review["detailed_assignment"] == "review_clear"]
    caution = review[review["detailed_assignment"] == "review_caution"]
    flags = failure_flags()
    positive_denominator = max(int(has_positive.sum()), 1)
    return {
        **policy,
        "query_count": QUERY_COUNT,
        "candidate_count": int(len(assigned)),
        "query_coverage": float(has_review.mean()),
        "positive_query_coverage": float(has_positive.mean()),
        "positive_retention": float(true_review / true_total) if true_total else math.nan,
        "reviewed_candidates_per_query": float(len(review) / QUERY_COUNT),
        "false_reviewed_candidates_per_query": float((~review["same_identity"]).sum() / QUERY_COUNT) if len(review) else 0.0,
        "review_burden_reduction": float(1.0 - len(review) / len(assigned)) if len(assigned) else math.nan,
        "defer_rate": float(len(defer) / len(assigned)) if len(assigned) else math.nan,
        "exclude_rate": float(len(exclude) / len(assigned)) if len(assigned) else math.nan,
        "false_top1_rate": float(false_top1.sum() / has_review.sum()) if has_review.sum() else math.nan,
        "top1_success": float(top1.sum() / positive_denominator),
        "top3_success": float(top3.sum() / positive_denominator),
        "top5_success": float(top5.sum() / positive_denominator),
        "mAP": float(np.mean(aps)) if aps else math.nan,
        "MRR": float(np.mean(rrs)) if rrs else math.nan,
        "same_candidate_retention": float(true_review / true_total) if true_total else math.nan,
        "false_candidate_review_rate": float((~review["same_identity"]).mean()) if len(review) else math.nan,
        "descriptor_disagreement_exposure": float(review["active_disagreement"].mean()) if len(review) else math.nan,
        "reciprocal_retrieval_support_rate": float(review["reciprocal_support_flag"].mean()) if len(review) else math.nan,
        "margin_confidence_mean": float(review["margin_confidence"].mean()) if len(review) else math.nan,
        "review_clear_count": int(len(clear)),
        "review_caution_count": int(len(caution)),
        "review_clear_risk": float((~clear["same_identity"]).mean()) if len(clear) else math.nan,
        "review_caution_risk": float((~caution["same_identity"]).mean()) if len(caution) else math.nan,
        "failure_exposure_review": float(review[flags].any(axis=1).mean()) if len(review) else math.nan,
        "review_candidate_count": int(len(review)),
        "defer_candidate_count": int(len(defer)),
        "exclude_candidate_count": int(len(exclude)),
    }


def selection_score(row: pd.Series) -> float:
    reliability = (1 - row["false_top1_rate"]) + (1 - min(row["false_reviewed_candidates_per_query"] / 5, 1)) + (1 - row["descriptor_disagreement_exposure"])
    coverage = row["query_coverage"] + row["positive_retention"]
    burden = row["review_burden_reduction"] + (1 - min(row["reviewed_candidates_per_query"] / 8, 1))
    evidence = (1 - row["failure_exposure_review"]) + row["reciprocal_retrieval_support_rate"]
    return float(0.28 * reliability + 0.28 * coverage + 0.24 * burden + 0.20 * evidence)


def select_top_variants(grid: pd.DataFrame) -> pd.DataFrame:
    df = grid.copy()
    df["selection_score"] = df.apply(selection_score, axis=1)
    rows = []
    baseline = df[df["variant_family"] == "candidate_f_baseline"].iloc[0].copy()
    baseline["selection_regime"] = "candidate_f_baseline"
    rows.append(baseline)
    reliability = df[(df["query_coverage"] >= 0.20) & df["false_top1_rate"].notna()].sort_values(
        ["false_top1_rate", "false_reviewed_candidates_per_query", "descriptor_disagreement_exposure"],
        ascending=[True, True, True],
    ).iloc[0].copy()
    reliability["selection_regime"] = "best_reliability_focused"
    rows.append(reliability)
    operational_pool = df[
        (df["query_coverage"] >= 0.60)
        & (df["positive_retention"] >= 0.55)
        & (df["false_reviewed_candidates_per_query"] <= 5.0)
        & (df["reviewed_candidates_per_query"] <= 6.0)
    ]
    if operational_pool.empty:
        operational_pool = df
    operational = operational_pool.sort_values(["selection_score", "query_coverage"], ascending=[False, False]).iloc[0].copy()
    operational["selection_regime"] = "best_operational"
    rows.append(operational)
    evidence_pool = df[(df["failure_exposure_review"] <= 0.10) & (df["query_coverage"] >= 0.20)]
    if evidence_pool.empty:
        evidence_pool = df
    evidence = evidence_pool.sort_values(["failure_exposure_review", "false_reviewed_candidates_per_query"], ascending=[True, True]).iloc[0].copy()
    evidence["selection_regime"] = "best_evidence_control"
    rows.append(evidence)
    external_pool = df[
        (df["query_coverage"] >= 0.65)
        & (df["positive_retention"] >= 0.55)
        & (df["false_reviewed_candidates_per_query"] <= 5.5)
    ]
    if external_pool.empty:
        external_pool = operational_pool
    external = external_pool.sort_values(["selection_score", "descriptor_disagreement_exposure"], ascending=[False, True]).iloc[0].copy()
    external["selection_regime"] = "external_feasibility_candidate"
    rows.append(external)
    return pd.DataFrame(rows).drop_duplicates(subset=["selection_regime", "variant_id"])


def boot_metric(sample: pd.DataFrame, metric: str) -> float:
    if metric == "false_top1_rate":
        denom = sample["has_review"].sum()
        return float(sample["false_top1"].sum() / denom) if denom else math.nan
    if metric == "query_coverage":
        return float(sample["has_review"].mean())
    if metric == "positive_retention":
        denom = sample["true_total"].sum()
        return float(sample["true_reviewed"].sum() / denom) if denom else math.nan
    if metric == "mAP":
        vals = sample["ap"].dropna()
        return float(vals.mean()) if len(vals) else math.nan
    if metric == "reviewed_candidates_per_query":
        return float(sample["review_count"].sum() / len(sample))
    if metric == "false_reviewed_candidates_per_query":
        return float(sample["false_reviewed"].sum() / len(sample))
    if metric == "descriptor_disagreement_exposure":
        rows = sample[sample["has_review"] == 1]
        return float(rows["disagreement_review"].mean()) if len(rows) else math.nan
    if metric == "review_clear_risk":
        denom = sample["clear_review_count"].sum()
        return float(sample["clear_false_count"].sum() / denom) if denom else math.nan
    if metric == "review_caution_risk":
        denom = sample["caution_review_count"].sum()
        return float(sample["caution_false_count"].sum() / denom) if denom else math.nan
    raise ValueError(metric)


def bootstrap_intervals(assignments: dict[str, pd.DataFrame], top: pd.DataFrame, iterations: int) -> pd.DataFrame:
    rng = np.random.default_rng(RANDOM_SEED)
    metrics = [
        "false_top1_rate",
        "query_coverage",
        "positive_retention",
        "mAP",
        "reviewed_candidates_per_query",
        "false_reviewed_candidates_per_query",
        "descriptor_disagreement_exposure",
        "review_clear_risk",
        "review_caution_risk",
    ]
    rows = []
    for _, variant in top.iterrows():
        summary = query_level_summary(assignments[variant["variant_id"]])
        for metric in metrics:
            vals = []
            for _ in range(iterations):
                sample = summary.iloc[rng.choice(np.arange(len(summary)), size=len(summary), replace=True)]
                vals.append(boot_metric(sample, metric))
            clean = np.asarray([v for v in vals if not math.isnan(float(v))], dtype=float)
            rows.append(
                {
                    "variant_id": variant["variant_id"],
                    "selection_regime": variant["selection_regime"],
                    "metric": metric,
                    "bootstrap_iterations": iterations,
                    "estimate": variant[metric],
                    "ci_lower": float(np.percentile(clean, 2.5)) if len(clean) else math.nan,
                    "ci_upper": float(np.percentile(clean, 97.5)) if len(clean) else math.nan,
                }
            )
    return pd.DataFrame(rows)


def sensitivity_audit(grid: pd.DataFrame, baseline: pd.Series) -> pd.DataFrame:
    rows = []
    for family, group in grid.groupby("variant_family"):
        if family == "candidate_f_baseline":
            continue
        for parameter in ["top_k", "visual_threshold", "disagreement_definition", "margin_threshold", "reciprocal_rank_threshold", "workload_cap"]:
            winners = []
            for value, subset in group.groupby(parameter):
                best = subset.sort_values("selection_score", ascending=False).iloc[0]
                winners.append(
                    {
                        "value": value,
                        "winner_variant_id": best["variant_id"],
                        "selection_score": best["selection_score"],
                        "query_coverage": best["query_coverage"],
                        "false_top1_rate": best["false_top1_rate"],
                        "positive_retention": best["positive_retention"],
                        "false_reviewed_candidates_per_query": best["false_reviewed_candidates_per_query"],
                    }
                )
            w = pd.DataFrame(winners)
            rows.append(
                {
                    "variant_family": family,
                    "sensitivity_parameter": parameter,
                    "settings_tested": int(len(w)),
                    "unique_winning_variants": int(w["winner_variant_id"].nunique()),
                    "score_range": float(w["selection_score"].max() - w["selection_score"].min()),
                    "query_coverage_range": float(w["query_coverage"].max() - w["query_coverage"].min()),
                    "false_top1_range": float(w["false_top1_rate"].max() - w["false_top1_rate"].min()),
                    "positive_retention_range": float(w["positive_retention"].max() - w["positive_retention"].min()),
                    "false_reviewed_per_query_range": float(w["false_reviewed_candidates_per_query"].max() - w["false_reviewed_candidates_per_query"].min()),
                    "fragility_interpretation": "fragile" if w["winner_variant_id"].nunique() <= 1 and len(w) > 1 and w["score_range"].max() > 0.20 else "sensitivity_documented",
                    "baseline_selection_score": float(baseline["selection_score"]),
                }
            )
    return pd.DataFrame(rows)


def failure_mode_summary(assignments: dict[str, pd.DataFrame], top: pd.DataFrame) -> pd.DataFrame:
    flags = failure_flags()
    rows = []
    for _, variant in top.iterrows():
        assigned = assignments[variant["variant_id"]]
        for detail, group in assigned.groupby("detailed_assignment"):
            for flag in flags + ["reciprocal_support_flag", "margin_confidence_flag"]:
                rows.append(
                    {
                        "variant_id": variant["variant_id"],
                        "selection_regime": variant["selection_regime"],
                        "detailed_assignment": detail,
                        "failure_mode": flag,
                        "candidate_count": int(len(group)),
                        "failure_mode_count": int(group[flag].sum()),
                        "failure_mode_rate": float(group[flag].mean()) if len(group) else math.nan,
                    }
                )
    return pd.DataFrame(rows)


def decision_rows(top: pd.DataFrame, sensitivity: pd.DataFrame) -> pd.DataFrame:
    baseline = top[top["selection_regime"] == "candidate_f_baseline"].iloc[0]
    operational = top[top["selection_regime"] == "best_operational"].iloc[0]
    reliability = top[top["selection_regime"] == "best_reliability_focused"].iloc[0]
    improves = (
        operational["variant_id"] != baseline["variant_id"]
        and operational["false_top1_rate"] <= baseline["false_top1_rate"] - 0.02
        and operational["positive_retention"] >= baseline["positive_retention"] - 0.05
        and operational["false_reviewed_candidates_per_query"] <= baseline["false_reviewed_candidates_per_query"] + 0.50
    )
    fragile = bool((sensitivity["fragility_interpretation"] == "fragile").any()) if not sensitivity.empty else False
    replace = "yes" if improves and not fragile else "no"
    final_variant = operational["variant_id"] if replace == "yes" else baseline["variant_id"]
    return pd.DataFrame(
        [
            {
                "decision_item": "v4_replaces_candidate_f",
                "decision": replace,
                "rationale": "replacement requires non-fragile improvement in false top-1 without unacceptable retention or burden loss",
            },
            {
                "decision_item": "candidate_f_remains_primary",
                "decision": "no" if replace == "yes" else "yes",
                "rationale": "Candidate F remains primary unless v4 clears the staged replacement rule",
            },
            {
                "decision_item": "v4_becomes_refinement_only",
                "decision": "no" if replace == "yes" else "yes",
                "rationale": "v4 variants strengthen interpretation and sensitivity analysis even if not final replacement",
            },
            {
                "decision_item": "recommended_final_variant",
                "decision": final_variant,
                "rationale": "selected by staged v4 refinement rule",
            },
            {
                "decision_item": "strongest_algorithm_contribution",
                "decision": "staged_evidence_margin_reciprocal_review_control",
                "rationale": "PF-ERI is now evaluated as admissibility, confidence, reciprocal support, and workload control rather than a simple filter",
            },
            {
                "decision_item": "unresolved_risks",
                "decision": "high_false_top1_and_czechlynx_specific_thresholds",
                "rationale": "false top-1 remains high and threshold stability is CzechLynx-specific",
            },
            {
                "decision_item": "readiness_for_external_patterned_felid_access_audit",
                "decision": "yes_access_feasibility_only",
                "rationale": "ready for access and feasibility audit only, not external validation claims",
            },
            {
                "decision_item": "broader_felid_claim_boundary",
                "decision": "not_supported",
                "rationale": "no external known-ID patterned-felid benchmark was run",
            },
            {
                "decision_item": "mainland_clouded_leopard_marbled_cat_boundary",
                "decision": "motivation_only",
                "rationale": "these taxa remain future conservation motivation only",
            },
            {
                "decision_item": "best_reliability_variant",
                "decision": reliability["variant_id"],
                "rationale": f"{reliability['variant_family']} had the best reliability-focused tradeoff",
            },
        ]
    )


def recommended_assignments(assigned: pd.DataFrame, variant_id: str) -> pd.DataFrame:
    out = assigned.sort_values(["query_idx", "rank"]).reset_index(drop=True).copy()
    out["candidate_row_id"] = [f"phase8_v4_candidate_{i:05d}" for i in range(1, len(out) + 1)]
    out["recommended_variant_id"] = variant_id
    return out[
        [
            "candidate_row_id",
            "recommended_variant_id",
            "rank",
            "detailed_assignment",
            "assignment",
            "confidence_tier",
            "query_band",
            "gallery_band",
            "pair_min_score",
            "pair_mean_score",
            "megadescriptor_similarity",
            "resnet50_similarity",
            "resnet50_rank",
            "mega_reciprocal_rank",
            "resnet50_reciprocal_rank",
            "margin_confidence",
            "active_disagreement",
            "reciprocal_support_flag",
        ]
    ].rename(columns={"assignment": "final_class", "active_disagreement": "descriptor_disagreement_flag"})


def make_figures(grid: pd.DataFrame, top: pd.DataFrame, assignments: dict[str, pd.DataFrame], boot: pd.DataFrame,
                 sensitivity: pd.DataFrame, failure: pd.DataFrame) -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(8, 6))
    plt.scatter(grid["query_coverage"], grid["false_top1_rate"], s=8, alpha=0.25)
    plt.scatter(top["query_coverage"], top["false_top1_rate"], s=70, color="#CC6677")
    plt.xlabel("Query coverage")
    plt.ylabel("False top-1 rate")
    plt.title("v4 variants: coverage vs false top-1")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "phase8_v4_coverage_vs_false_top1.png", dpi=180)
    plt.close()

    plt.figure(figsize=(8, 6))
    plt.scatter(grid["reviewed_candidates_per_query"], grid["positive_retention"], s=8, alpha=0.25)
    plt.scatter(top["reviewed_candidates_per_query"], top["positive_retention"], s=70, color="#117733")
    plt.xlabel("Reviewed candidates per query")
    plt.ylabel("Positive retention")
    plt.title("v4 workload vs positive retention")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "phase8_v4_workload_vs_positive_retention.png", dpi=180)
    plt.close()

    plt.figure(figsize=(10, 5))
    plt.bar(top["selection_regime"].str.replace("_", " "), top["false_reviewed_candidates_per_query"], color="#4477AA")
    plt.xticks(rotation=35, ha="right", fontsize=8)
    plt.ylabel("False reviewed candidates/query")
    plt.title("False reviewed candidates by selected variant")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "phase8_v4_false_reviewed_candidates_by_variant.png", dpi=180)
    plt.close()

    recommended_id = top[top["selection_regime"] == "candidate_f_baseline"].iloc[0]["variant_id"]
    detail_counts = assignments[recommended_id]["detailed_assignment"].value_counts().reindex(VALID_DETAIL_CLASSES).fillna(0)
    plt.figure(figsize=(10, 5))
    plt.bar(detail_counts.index.str.replace("_", " "), detail_counts.values, color="#AA4499")
    plt.xticks(rotation=35, ha="right", fontsize=8)
    plt.ylabel("Candidate count")
    plt.title("Review tier distribution for recommended variant")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "phase8_v4_review_tier_distribution.png", dpi=180)
    plt.close()

    risk_rows = []
    for _, row in top.iterrows():
        risk_rows.append({"label": row["selection_regime"], "review_clear_risk": row["review_clear_risk"], "review_caution_risk": row["review_caution_risk"]})
    risks = pd.DataFrame(risk_rows).set_index("label")
    risks.plot(kind="bar", figsize=(10, 5), color=["#228833", "#EE7733"])
    plt.ylabel("False candidate rate")
    plt.title("Review-clear vs review-caution risk")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "phase8_v4_review_clear_vs_caution_risk.png", dpi=180)
    plt.close()

    b = boot[boot["metric"].isin(["false_top1_rate", "query_coverage", "positive_retention", "false_reviewed_candidates_per_query"])]
    plt.figure(figsize=(13, 6))
    x = np.arange(len(b))
    lower = b["estimate"] - b["ci_lower"]
    upper = b["ci_upper"] - b["estimate"]
    plt.errorbar(x, b["estimate"], yerr=[lower, upper], fmt="o", color="#332288")
    plt.xticks(x, (b["selection_regime"] + "\n" + b["metric"]).str.replace("_", " "), rotation=45, ha="right", fontsize=7)
    plt.ylabel("Metric value")
    plt.title("Bootstrap intervals for selected v4 variants")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "phase8_v4_bootstrap_intervals_top_variants.png", dpi=180)
    plt.close()

    plt.figure(figsize=(11, 5))
    plot_sens = sensitivity.groupby("variant_family")["score_range"].mean().sort_values(ascending=False)
    plt.plot(plot_sens.index.str.replace("_", " "), plot_sens.values, marker="o")
    plt.xticks(rotation=35, ha="right", fontsize=8)
    plt.ylabel("Mean selection-score range")
    plt.title("Sensitivity by variant family")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "phase8_v4_sensitivity_lineplot.png", dpi=180)
    plt.close()

    review_failure = failure[(failure["detailed_assignment"].isin(["review_clear", "review_caution"])) & failure["failure_mode"].isin(failure_flags())]
    pivot = review_failure.pivot_table(index="failure_mode", columns="detailed_assignment", values="failure_mode_rate", aggfunc="mean").fillna(0)
    pivot.plot(kind="bar", figsize=(11, 5))
    plt.ylabel("Exposure rate")
    plt.title("Failure-mode exposure among review tiers")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "phase8_v4_failure_mode_exposure_review_tiers.png", dpi=180)
    plt.close()


def run(args: argparse.Namespace) -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    metadata, similarities = align_inputs(args)
    candidates = build_mega_candidates(metadata, similarities, max_k=20)
    candidates = add_retrieval_confidence_features(candidates, similarities)
    policies = policy_grid()
    rows = []
    assigned_cache: dict[str, pd.DataFrame] = {}
    for policy in policies:
        assigned = assign_variant(candidates, policy)
        metrics = compute_metrics(assigned, policy)
        rows.append(metrics)
        assigned_cache[policy["variant_id"]] = assigned
    grid = pd.DataFrame(rows)
    grid["selection_score"] = grid.apply(selection_score, axis=1)
    top = select_top_variants(grid)
    sensitivity = sensitivity_audit(grid, top[top["selection_regime"] == "candidate_f_baseline"].iloc[0])
    boot = bootstrap_intervals(assigned_cache, top, args.bootstrap_iterations)
    failure = failure_mode_summary(assigned_cache, top)
    decision = decision_rows(top, sensitivity)
    recommended_id = decision.loc[decision["decision_item"] == "recommended_final_variant", "decision"].iloc[0]
    assignments = recommended_assignments(assigned_cache[recommended_id], recommended_id)

    grid.to_csv(POLICY_GRID_CSV, index=False)
    top.to_csv(TOP_VARIANTS_CSV, index=False)
    top.to_csv(VARIANT_COMPARISON_CSV, index=False)
    assignments.to_csv(ASSIGNMENTS_CSV, index=False)
    boot.to_csv(BOOTSTRAP_CSV, index=False)
    sensitivity.to_csv(SENSITIVITY_CSV, index=False)
    failure.to_csv(FAILURE_SUMMARY_CSV, index=False)
    decision.to_csv(ALGORITHM_DECISION_CSV, index=False)
    make_figures(grid, top, assigned_cache, boot, sensitivity, failure)

    print("PASS: Phase 8 Slice 3D PF-ERI v4 optimizer complete")
    print(f"candidate_policy_count: {len(grid)}")
    print(f"top_variant_count: {len(top)}")
    print(f"recommended_final_variant: {recommended_id}")
    print(f"v4_replaces_candidate_f: {decision.loc[decision['decision_item'] == 'v4_replaces_candidate_f', 'decision'].iloc[0]}")
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
