#!/usr/bin/env python3
"""Analyze descriptor disagreement and optimize PF-ERI confidence control."""

from __future__ import annotations

import argparse
import math
from itertools import product
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from phase8_pf_eri_retrieval_control_v2_optimizer import (
    ANNOTATION_CSV,
    IDENTITY_CSV,
    MEGA_EMBEDDINGS_CSV,
    RESNET_EMBEDDINGS_CSV,
    THRESHOLDS,
    align_inputs,
    average_precision,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase8/descriptor_disagreement_confidence_control"
FIGURE_DIR = OUTPUT_DIR / "figures"

DEFINITION_AUDIT_CSV = OUTPUT_DIR / "phase8_descriptor_disagreement_definition_audit.csv"
POLICY_GRID_CSV = OUTPUT_DIR / "phase8_descriptor_disagreement_policy_grid.csv"
TOP_POLICIES_CSV = OUTPUT_DIR / "phase8_descriptor_disagreement_top_policies.csv"
COMPARISON_CSV = OUTPUT_DIR / "phase8_descriptor_disagreement_v2_vs_v3_comparison.csv"
ASSIGNMENTS_CSV = OUTPUT_DIR / "phase8_descriptor_disagreement_recommended_assignments.csv"
FAILURE_SUMMARY_CSV = OUTPUT_DIR / "phase8_descriptor_disagreement_failure_mode_summary.csv"
BOOTSTRAP_CSV = OUTPUT_DIR / "phase8_descriptor_disagreement_bootstrap_intervals.csv"
PAIRED_BOOTSTRAP_CSV = OUTPUT_DIR / "phase8_descriptor_disagreement_paired_bootstrap_differences.csv"
READINESS_CSV = OUTPUT_DIR / "phase8_descriptor_disagreement_readiness_decision.csv"

RANDOM_SEED = 20260614
BOOTSTRAP_ITERATIONS = 300
TOP_K_VALUES = [3, 5, 10, 20]
DISAGREEMENT_DEFINITIONS = [
    "rank_high_resnet_low",
    "similarity_high_resnet_low",
    "absent_resnet_top5",
    "absent_resnet_top10",
    "rank_gap_ge_10",
    "percentile_gap_ge_0_35",
    "mega_top1_not_resnet_top5",
    "mega_top1_not_resnet_top10",
]
POLICY_DISAGREEMENT_DEFINITIONS = [
    "rank_high_resnet_low",
    "similarity_high_resnet_low",
    "absent_resnet_top5",
    "absent_resnet_top10",
    "rank_gap_ge_10",
]
VALID_ASSIGNMENTS = ["review_candidate", "defer_candidate", "exclude_candidate"]


def threshold_value(name: str) -> float:
    return THRESHOLDS[name]


def build_mega_candidates(metadata: pd.DataFrame, similarities: dict[str, np.ndarray], max_k: int = 20) -> pd.DataFrame:
    mega = similarities["megadescriptor"]
    resnet = similarities["resnet50"]
    identities = metadata["working_individual_id"].astype(str).to_numpy()
    rows: list[dict[str, object]] = []
    n = len(metadata)
    for query_idx, query in metadata.iterrows():
        q = int(query_idx)
        mega_scores = mega[q].copy()
        resnet_scores = resnet[q].copy()
        mega_scores[q] = -np.inf
        resnet_scores[q] = -np.inf
        mega_order = np.argsort(-mega_scores)
        resnet_order = np.argsort(-resnet_scores)
        resnet_rank = np.empty(n, dtype=int)
        resnet_rank[resnet_order] = np.arange(1, n + 1)
        for rank, gallery_idx in enumerate(mega_order[:max_k], start=1):
            gallery = metadata.iloc[int(gallery_idx)]
            r_rank = int(resnet_rank[int(gallery_idx)])
            q_score = float(query["visual_pf_eri_score"])
            g_score = float(gallery["visual_pf_eri_score"])
            rows.append(
                {
                    "descriptor": "megadescriptor",
                    "query_idx": q,
                    "gallery_idx": int(gallery_idx),
                    "query_token": query["image_token"],
                    "gallery_token": gallery["image_token"],
                    "rank": rank,
                    "megadescriptor_rank": rank,
                    "resnet50_rank": r_rank,
                    "rank_gap": r_rank - rank,
                    "megadescriptor_similarity": float(mega[q, int(gallery_idx)]),
                    "resnet50_similarity": float(resnet[q, int(gallery_idx)]),
                    "megadescriptor_percentile": 1.0 - ((rank - 1) / (n - 2)),
                    "resnet50_percentile": 1.0 - ((r_rank - 1) / (n - 2)),
                    "same_identity": bool(identities[q] == identities[int(gallery_idx)]),
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
                    "uncertainty_flag": query["uncertainty_flag"] == "yes" or gallery["uncertainty_flag"] == "yes",
                    "severe_visual_failure": bool(query["severe_visual_failure"]) or bool(gallery["severe_visual_failure"]),
                }
            )
    df = pd.DataFrame(rows)
    df["high_descriptor_low_evidence"] = (df["megadescriptor_similarity"] >= 0.80) & (df["pair_min_score"] < 50.0)
    df["rank_high_resnet_low"] = (df["megadescriptor_rank"] <= 5) & (df["resnet50_rank"] > 10)
    df["similarity_high_resnet_low"] = (df["megadescriptor_percentile"] >= 0.985) & (df["resnet50_percentile"] < 0.95)
    df["absent_resnet_top5"] = df["resnet50_rank"] > 5
    df["absent_resnet_top10"] = df["resnet50_rank"] > 10
    df["rank_gap_ge_10"] = df["rank_gap"] >= 10
    df["percentile_gap_ge_0_35"] = (df["megadescriptor_percentile"] - df["resnet50_percentile"]) >= 0.35
    df["mega_top1_not_resnet_top5"] = (df["megadescriptor_rank"] == 1) & (df["resnet50_rank"] > 5)
    df["mega_top1_not_resnet_top10"] = (df["megadescriptor_rank"] == 1) & (df["resnet50_rank"] > 10)
    return df


def v2_policy() -> dict[str, object]:
    return {
        "policy_id": "v2_p08117",
        "policy_family": "A_v2_baseline_reproduction",
        "top_k": 5,
        "query_threshold": "low_or_higher",
        "gallery_threshold": "medium_or_higher",
        "pair_evidence_rule": "min_score",
        "disagreement_definition": "rank_gap_ge_10",
        "disagreement_action": "allow",
        "strictness": "standard",
    }


def policy_grid() -> list[dict[str, object]]:
    policies = [v2_policy()]
    pid = 1
    family_actions = {
        "B_disagreement_defer": ["defer"],
        "C_agreement_required_review": ["defer"],
        "D_soft_disagreement_penalty": ["defer_if_visual_weak"],
        "E_evidence_rescued_disagreement": ["defer_unless_visual_high"],
        "F_reliability_first_disagreement_control": ["defer", "exclude_severe_only"],
        "G_balanced_v3_disagreement_control": ["defer", "defer_if_visual_weak"],
    }
    for family, actions in family_actions.items():
        strictness_values = ["standard", "reliability_first"] if family != "G_balanced_v3_disagreement_control" else ["lenient", "standard"]
        for top_k, q_thr, g_thr, pair_rule, definition, action, strictness in product(
            TOP_K_VALUES,
            ["low_or_higher", "medium_or_higher", "high_only"],
            ["low_or_higher", "medium_or_higher", "high_only"],
            ["min_score", "mean_score"],
            POLICY_DISAGREEMENT_DEFINITIONS,
            actions,
            strictness_values,
        ):
            policies.append(
                {
                    "policy_id": f"v3_p{pid:05d}",
                    "policy_family": family,
                    "top_k": top_k,
                    "query_threshold": q_thr,
                    "gallery_threshold": g_thr,
                    "pair_evidence_rule": pair_rule,
                    "disagreement_definition": definition,
                    "disagreement_action": action,
                    "strictness": strictness,
                }
            )
            pid += 1
    return policies


def assign_policy(candidates: pd.DataFrame, policy: dict[str, object]) -> pd.Series:
    assignment = pd.Series(np.repeat("review_candidate", len(candidates)), index=candidates.index, dtype=object)
    q_pass = candidates["query_score"] >= threshold_value(str(policy["query_threshold"]))
    g_pass = candidates["gallery_score"] >= threshold_value(str(policy["gallery_threshold"]))
    if str(policy["pair_evidence_rule"]) == "mean_score":
        pair_pass = candidates["pair_mean_score"] >= min(threshold_value(str(policy["query_threshold"])), threshold_value(str(policy["gallery_threshold"])))
    else:
        pair_pass = candidates["pair_min_score"] >= min(threshold_value(str(policy["query_threshold"])), threshold_value(str(policy["gallery_threshold"])))
    evidence_pass = q_pass & g_pass & pair_pass
    assignment[~evidence_pass] = "defer_candidate"
    severe = candidates["pattern_none"] | candidates["severe_blur"] | candidates["major_occlusion"] | candidates["frontal_rear"]
    if str(policy["strictness"]) in {"strict", "reliability_first"}:
        assignment[severe] = "exclude_candidate" if str(policy["strictness"]) == "reliability_first" else "defer_candidate"
    elif str(policy["strictness"]) == "standard":
        assignment[severe] = "defer_candidate"
    disagreement = candidates[str(policy["disagreement_definition"])]
    visual_weak = candidates["pair_min_score"] < 75.0
    visual_high_clean = (candidates["query_score"] >= 75.0) & (candidates["gallery_score"] >= 75.0) & ~severe
    action = str(policy["disagreement_action"])
    if action == "defer":
        assignment[disagreement & (assignment == "review_candidate")] = "defer_candidate"
    elif action == "defer_if_visual_weak":
        assignment[disagreement & visual_weak & (assignment == "review_candidate")] = "defer_candidate"
    elif action == "defer_unless_visual_high":
        assignment[disagreement & ~visual_high_clean & (assignment == "review_candidate")] = "defer_candidate"
    elif action == "exclude_severe_only":
        assignment[disagreement & severe] = "exclude_candidate"
        assignment[disagreement & ~severe & visual_weak & (assignment == "review_candidate")] = "defer_candidate"
    return assignment


def average_precision_from_relevance(relevance: np.ndarray) -> float:
    return average_precision(relevance)


def compute_metrics(assigned: pd.DataFrame, policy: dict[str, object]) -> dict[str, object]:
    review = assigned[assigned["assignment"] == "review_candidate"].copy()
    review_count = int(len(review))
    defer_count = int((assigned["assignment"] == "defer_candidate").sum())
    exclude_count = int((assigned["assignment"] == "exclude_candidate").sum())
    covered = int(review["query_idx"].nunique())
    true_total = int(assigned["same_identity"].sum())
    true_review = int(review["same_identity"].sum())
    per_query = query_level_summary(assigned)
    false_top1 = per_query["false_top1"].sum() / per_query["has_review"].sum() if per_query["has_review"].sum() else math.nan
    ap = per_query["ap"].replace(0, np.nan).dropna()
    rr = per_query["rr"].replace(0, np.nan).dropna()
    top1 = per_query.loc[per_query["has_positive_review"] == 1, "top1"].mean()
    top3 = per_query.loc[per_query["has_positive_review"] == 1, "top3"].mean()
    top5 = per_query.loc[per_query["has_positive_review"] == 1, "top5"].mean()
    flags = failure_flags()
    disagreement = assigned[str(policy["disagreement_definition"])]
    review_dis = review[str(policy["disagreement_definition"])] if review_count else pd.Series(dtype=bool)
    false_review = review[~review["same_identity"]]
    dis_false_review = false_review[str(policy["disagreement_definition"])] if len(false_review) else pd.Series(dtype=bool)
    dis_review = review[review[str(policy["disagreement_definition"])]] if review_count else pd.DataFrame()
    return {
        **policy,
        "query_count": 500,
        "covered_query_count": covered,
        "query_coverage": covered / 500,
        "positive_query_coverage": float(per_query["has_positive_review"].sum() / 500),
        "review_candidate_count": review_count,
        "defer_candidate_count": defer_count,
        "exclude_candidate_count": exclude_count,
        "review_candidates_per_query": review_count / 500,
        "false_reviewed_candidates_per_query": int((~review["same_identity"]).sum()) / 500 if review_count else 0.0,
        "review_burden_reduction": 1.0 - review_count / len(assigned) if len(assigned) else math.nan,
        "false_top1_rate": float(false_top1),
        "top1_success": float(top1) if not math.isnan(top1) else math.nan,
        "top3_success": float(top3) if not math.isnan(top3) else math.nan,
        "top5_success": float(top5) if not math.isnan(top5) else math.nan,
        "mAP_among_covered_positives": float(ap.mean()) if len(ap) else math.nan,
        "MRR_among_covered_positives": float(rr.mean()) if len(rr) else math.nan,
        "positive_retention": true_review / true_total if true_total else math.nan,
        "true_same_candidate_retention": true_review / true_total if true_total else math.nan,
        "false_reviewed_candidate_rate": 1.0 - true_review / review_count if review_count else math.nan,
        "disagreement_exposure_review": float(review_dis.mean()) if review_count else math.nan,
        "disagreement_exposure_defer": float(assigned.loc[assigned["assignment"] == "defer_candidate", str(policy["disagreement_definition"])].mean()) if defer_count else math.nan,
        "disagreement_exposure_false_review": float(dis_false_review.mean()) if len(false_review) else math.nan,
        "same_candidate_rate_disagreement_review": float(dis_review["same_identity"].mean()) if len(dis_review) else math.nan,
        "false_candidate_rate_disagreement_review": float((~dis_review["same_identity"]).mean()) if len(dis_review) else math.nan,
        "failure_exposure_review": float(review[flags].any(axis=1).mean()) if review_count else math.nan,
    }


def query_level_summary(assigned: pd.DataFrame) -> pd.DataFrame:
    assigned = assigned.sort_values(["query_idx", "rank"])
    k = int(len(assigned) / 500)
    review = (assigned["assignment"].to_numpy() == "review_candidate").reshape(500, k)
    same = assigned["same_identity"].to_numpy(dtype=bool).reshape(500, k)
    disagree = assigned["active_disagreement"].to_numpy(dtype=bool).reshape(500, k)
    rows = []
    for query_idx in range(500):
        review_mask = review[query_idx]
        relevance = same[query_idx][review_mask].astype(int)
        has_review = bool(review_mask.any())
        has_positive = bool(relevance.sum() > 0) if has_review else False
        first_positive = int(np.flatnonzero(relevance == 1)[0]) + 1 if has_positive else 0
        rows.append(
            {
                "query_idx": query_idx,
                "candidate_count": k,
                "review_count": int(review_mask.sum()),
                "has_review": int(has_review),
                "has_positive_review": int(has_positive),
                "false_top1": int(has_review and relevance[0] == 0),
                "top1": int(has_positive and relevance[0] == 1),
                "top3": int(has_positive and relevance[: min(3, len(relevance))].max() == 1),
                "top5": int(has_positive and relevance[: min(5, len(relevance))].max() == 1),
                "ap": average_precision_from_relevance(relevance) if has_positive else math.nan,
                "rr": 1.0 / first_positive if first_positive else math.nan,
                "true_total": int(same[query_idx].sum()),
                "true_reviewed": int(relevance.sum()) if has_review else 0,
                "disagreement_review": float(disagree[query_idx][review_mask].mean()) if has_review else math.nan,
                "false_reviewed": int((1 - relevance).sum()) if has_review else 0,
            }
        )
    return pd.DataFrame(rows)


def evaluate_policy(candidates: pd.DataFrame, policy: dict[str, object]) -> tuple[dict[str, object], pd.DataFrame]:
    subset = candidates[candidates["rank"] <= int(policy["top_k"])].copy().sort_values(["query_idx", "rank"]).reset_index(drop=True)
    subset["active_disagreement"] = subset[str(policy["disagreement_definition"])]
    subset["assignment"] = assign_policy(subset, policy)
    return compute_metrics(subset, policy), subset


def failure_flags() -> list[str]:
    return [
        "pattern_none",
        "low_pattern_visibility",
        "severe_blur",
        "major_occlusion",
        "frontal_rear",
        "weak_side_evidence",
        "uncertainty_flag",
        "high_descriptor_low_evidence",
        "active_disagreement",
    ]


def disagreement_definition_audit(candidates: pd.DataFrame, v2_assigned: pd.DataFrame) -> pd.DataFrame:
    rows = []
    rng = np.random.default_rng(RANDOM_SEED)
    candidates = candidates.sort_values(["query_idx", "rank"]).reset_index(drop=True)
    same_matrix = candidates["same_identity"].to_numpy(dtype=bool).reshape(500, 20)
    for definition in DISAGREEMENT_DEFINITIONS:
        flag = candidates[definition]
        exposed = candidates[flag]
        unexposed = candidates[~flag]
        false_rate_exposed = 1.0 - exposed["same_identity"].mean() if len(exposed) else math.nan
        false_rate_unexposed = 1.0 - unexposed["same_identity"].mean() if len(unexposed) else math.nan
        risk_ratio = false_rate_exposed / false_rate_unexposed if false_rate_unexposed and not math.isnan(false_rate_unexposed) else math.nan
        flag_matrix = flag.to_numpy(dtype=bool).reshape(500, 20)
        exposed_count = flag_matrix.sum(axis=1)
        exposed_false = (flag_matrix & ~same_matrix).sum(axis=1)
        unexposed_count = (~flag_matrix).sum(axis=1)
        unexposed_false = ((~flag_matrix) & ~same_matrix).sum(axis=1)
        boot = []
        for _ in range(BOOTSTRAP_ITERATIONS):
            idx = rng.choice(np.arange(500), size=500, replace=True)
            e_count = exposed_count[idx].sum()
            u_count = unexposed_count[idx].sum()
            if e_count and u_count:
                fr_e = exposed_false[idx].sum() / e_count
                fr_u = unexposed_false[idx].sum() / u_count
                boot.append(fr_e / fr_u if fr_u else math.nan)
        clean = np.asarray([x for x in boot if not math.isnan(float(x))], dtype=float)
        v2_review = v2_assigned[v2_assigned["assignment"] == "review_candidate"]
        rows.append(
            {
                "disagreement_definition": definition,
                "candidate_count": int(flag.sum()),
                "query_coverage": candidates.loc[flag, "query_idx"].nunique() / 500 if flag.any() else 0.0,
                "same_candidate_rate": float(exposed["same_identity"].mean()) if len(exposed) else math.nan,
                "false_candidate_rate": false_rate_exposed,
                "false_candidate_rate_unexposed": false_rate_unexposed,
                "risk_ratio_false_candidate": risk_ratio,
                "risk_ratio_ci_lower": float(np.percentile(clean, 2.5)) if len(clean) else math.nan,
                "risk_ratio_ci_upper": float(np.percentile(clean, 97.5)) if len(clean) else math.nan,
                "v2_review_candidate_exposure": float(v2_review[definition].mean()) if len(v2_review) else math.nan,
                "stability_interpretation": "stable_common_risk_signal" if len(clean) and np.percentile(clean, 2.5) > 1.0 else "not_stable_or_weak_signal",
            }
        )
    return pd.DataFrame(rows)


def select_top_policies(grid: pd.DataFrame) -> pd.DataFrame:
    v2 = grid[grid["policy_family"] == "A_v2_baseline_reproduction"].iloc[0]
    selected = []
    reliability = grid[
        (grid["policy_family"].str.startswith("F_"))
        & (grid["query_coverage"] >= 0.20)
        & grid["false_top1_rate"].notna()
    ].sort_values(["false_top1_rate", "disagreement_exposure_review", "query_coverage"], ascending=[True, True, False]).head(1)
    balanced = grid[
        (grid["policy_family"] == "G_balanced_v3_disagreement_control")
        & (grid["query_coverage"] >= 0.55)
        & (grid["positive_retention"] >= 0.45)
        & (grid["review_burden_reduction"] >= float(v2["review_burden_reduction"]) - 0.05)
        & (grid["disagreement_exposure_review"] < float(v2["disagreement_exposure_review"]))
        & grid["false_top1_rate"].notna()
    ].sort_values(["disagreement_exposure_review", "positive_retention", "query_coverage"], ascending=[True, False, False]).head(1)
    if balanced.empty:
        balanced = grid[
            (grid["policy_family"] == "G_balanced_v3_disagreement_control")
            & (grid["query_coverage"] >= 0.45)
            & grid["false_top1_rate"].notna()
        ].sort_values(["disagreement_exposure_review", "positive_retention", "query_coverage"], ascending=[True, False, False]).head(1)
    coverage = grid[
        (grid["query_coverage"] >= 0.70)
        & (grid["disagreement_exposure_review"] < float(v2["disagreement_exposure_review"]))
        & grid["false_top1_rate"].notna()
    ].sort_values(["query_coverage", "disagreement_exposure_review"], ascending=[False, True]).head(1)
    evidence = grid[
        (grid["policy_family"].isin(["C_agreement_required_review", "E_evidence_rescued_disagreement"]))
        & (grid["failure_exposure_review"] <= 0.10)
        & grid["false_top1_rate"].notna()
    ].sort_values(["failure_exposure_review", "disagreement_exposure_review", "query_coverage"], ascending=[True, True, False]).head(1)
    for regime, frame in [
        ("v2_baseline", grid[grid["policy_family"] == "A_v2_baseline_reproduction"].head(1)),
        ("reliability_first_disagreement", reliability),
        ("balanced_v3_main_candidate", balanced),
        ("coverage_preserving_disagreement", coverage),
        ("evidence_control", evidence),
    ]:
        if not frame.empty:
            row = frame.iloc[0].to_dict()
            row["selection_regime"] = regime
            selected.append(row)
    return pd.DataFrame(selected)


def query_boot_metrics(assigned: pd.DataFrame, policy: dict[str, object], iterations: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(RANDOM_SEED)
    per_query = query_level_summary(assigned)
    estimates = compute_metrics(assigned, policy)
    metrics = [
        "false_top1_rate",
        "query_coverage",
        "positive_retention",
        "mAP_among_covered_positives",
        "review_burden_reduction",
        "disagreement_exposure_review",
        "false_reviewed_candidates_per_query",
    ]
    rows = []
    for metric in metrics:
        vals = []
        for _ in range(iterations):
            sample = per_query.iloc[rng.choice(np.arange(500), size=500, replace=True)]
            vals.append(boot_metric(sample, metric))
        clean = np.asarray([v for v in vals if not math.isnan(float(v))], dtype=float)
        rows.append(
            {
                "policy_id": policy["policy_id"],
                "selection_regime": policy.get("selection_regime", ""),
                "metric": metric,
                "bootstrap_iterations": iterations,
                "estimate": estimates[metric],
                "ci_lower": float(np.percentile(clean, 2.5)) if len(clean) else math.nan,
                "ci_upper": float(np.percentile(clean, 97.5)) if len(clean) else math.nan,
            }
        )
    return pd.DataFrame(rows), per_query


def boot_metric(sample: pd.DataFrame, metric: str) -> float:
    if metric == "false_top1_rate":
        denom = sample["has_review"].sum()
        return float(sample["false_top1"].sum() / denom) if denom else math.nan
    if metric == "query_coverage":
        return float(sample["has_review"].mean())
    if metric == "positive_retention":
        denom = sample["true_total"].sum()
        return float(sample["true_reviewed"].sum() / denom) if denom else math.nan
    if metric == "mAP_among_covered_positives":
        vals = sample["ap"].replace(0, np.nan).dropna()
        return float(vals.mean()) if len(vals) else math.nan
    if metric == "review_burden_reduction":
        denom = sample["candidate_count"].sum()
        return float(1.0 - sample["review_count"].sum() / denom) if denom else math.nan
    if metric == "disagreement_exposure_review":
        rows = sample[sample["has_review"] == 1]
        return float(rows["disagreement_review"].mean()) if len(rows) else math.nan
    if metric == "false_reviewed_candidates_per_query":
        return float(sample["false_reviewed"].sum() / len(sample))
    raise ValueError(metric)


def paired_bootstrap(v2_summary: pd.DataFrame, top_summaries: dict[str, pd.DataFrame], top: pd.DataFrame, iterations: int) -> pd.DataFrame:
    rng = np.random.default_rng(RANDOM_SEED)
    metrics = ["disagreement_exposure_review", "positive_retention", "query_coverage", "false_top1_rate", "review_burden_reduction"]
    rows = []
    for _, policy in top[top["policy_id"] != "v2_p08117"].iterrows():
        summary = top_summaries[policy["policy_id"]]
        for metric in metrics:
            vals = []
            for _ in range(iterations):
                idx = rng.choice(np.arange(500), size=500, replace=True)
                vals.append(boot_metric(summary.iloc[idx], metric) - boot_metric(v2_summary.iloc[idx], metric))
            clean = np.asarray([v for v in vals if not math.isnan(float(v))], dtype=float)
            rows.append(
                {
                    "policy_id": policy["policy_id"],
                    "selection_regime": policy["selection_regime"],
                    "metric": f"delta_{metric}_vs_v2",
                    "bootstrap_iterations": iterations,
                    "estimate": float(policy[metric] - top[top["policy_id"] == "v2_p08117"].iloc[0][metric]),
                    "ci_lower": float(np.percentile(clean, 2.5)) if len(clean) else math.nan,
                    "ci_upper": float(np.percentile(clean, 97.5)) if len(clean) else math.nan,
                }
            )
    return pd.DataFrame(rows)


def failure_summary(assigned_by_policy: dict[str, pd.DataFrame], top: pd.DataFrame) -> pd.DataFrame:
    rows = []
    flags = failure_flags()
    for _, policy in top.iterrows():
        assigned = assigned_by_policy[policy["policy_id"]]
        for assignment, group in assigned.groupby("assignment"):
            for flag in flags:
                rows.append(
                    {
                        "policy_id": policy["policy_id"],
                        "selection_regime": policy["selection_regime"],
                        "assignment": assignment,
                        "failure_mode": flag,
                        "candidate_count": int(len(group)),
                        "failure_mode_count": int(group[flag].sum()),
                        "failure_mode_rate": float(group[flag].mean()) if len(group) else math.nan,
                    }
                )
    return pd.DataFrame(rows)


def comparison_table(top: pd.DataFrame) -> pd.DataFrame:
    v2 = top[top["policy_id"] == "v2_p08117"].iloc[0]
    rows = []
    for _, row in top.iterrows():
        rows.append(
            {
                "policy_id": row["policy_id"],
                "selection_regime": row["selection_regime"],
                "policy_family": row["policy_family"],
                "top_k": row["top_k"],
                "false_top1_rate": row["false_top1_rate"],
                "query_coverage": row["query_coverage"],
                "mAP_among_covered_positives": row["mAP_among_covered_positives"],
                "positive_retention": row["positive_retention"],
                "review_burden_reduction": row["review_burden_reduction"],
                "disagreement_exposure_review": row["disagreement_exposure_review"],
                "false_reviewed_candidates_per_query": row["false_reviewed_candidates_per_query"],
                "delta_false_top1_vs_v2": row["false_top1_rate"] - v2["false_top1_rate"],
                "delta_query_coverage_vs_v2": row["query_coverage"] - v2["query_coverage"],
                "delta_mAP_vs_v2": row["mAP_among_covered_positives"] - v2["mAP_among_covered_positives"],
                "delta_positive_retention_vs_v2": row["positive_retention"] - v2["positive_retention"],
                "delta_review_burden_reduction_vs_v2": row["review_burden_reduction"] - v2["review_burden_reduction"],
                "delta_disagreement_exposure_vs_v2": row["disagreement_exposure_review"] - v2["disagreement_exposure_review"],
                "delta_false_reviewed_candidates_per_query_vs_v2": row["false_reviewed_candidates_per_query"] - v2["false_reviewed_candidates_per_query"],
            }
        )
    return pd.DataFrame(rows)


def readiness(def_audit: pd.DataFrame, top: pd.DataFrame, paired: pd.DataFrame) -> pd.DataFrame:
    stable = bool((def_audit["risk_ratio_ci_lower"] > 1.0).any())
    balanced = top[top["selection_regime"] == "balanced_v3_main_candidate"].iloc[0]
    v2 = top[top["policy_id"] == "v2_p08117"].iloc[0]
    improves_disagreement = balanced["disagreement_exposure_review"] < v2["disagreement_exposure_review"]
    retention_ok = balanced["positive_retention"] >= 0.45
    false_burden_increase = (
        balanced["false_reviewed_candidates_per_query"]
        > v2["false_reviewed_candidates_per_query"] + 1.0
    )
    map_loss = balanced["mAP_among_covered_positives"] < v2["mAP_among_covered_positives"] - 0.05
    false_top1_not_clearly_better = balanced["false_top1_rate"] >= v2["false_top1_rate"]
    replace = (
        "no_v2_remains_primary_v3_confidence_variant"
        if false_burden_increase or map_loss or false_top1_not_clearly_better
        else "yes_with_caution"
    )
    return pd.DataFrame(
        [
            {
                "decision_item": "descriptor_disagreement_stable_risk_signal",
                "decision": "mixed_or_common_noise" if not stable else "yes_for_some_definitions",
                "rationale": "risk-ratio bootstrap intervals determine whether disagreement definitions are stable risk signals",
            },
            {
                "decision_item": "v3_improves_confidence_over_v2",
                "decision": "yes_for_disagreement_exposure" if improves_disagreement and retention_ok else "mixed",
                "rationale": "balanced v3 is judged by disagreement exposure, retention, coverage, and paired bootstrap differences",
            },
            {
                "decision_item": "v3_should_replace_v2",
                "decision": replace,
                "rationale": "v3 should replace v2 only if disagreement gains do not create higher reviewed false-candidate burden, lower mAP, or weaker false-top1 control",
            },
            {
                "decision_item": "v2_remains_better_balanced",
                "decision": "yes" if replace.startswith("no") else "no",
                "rationale": "v2 is retained if v3 improves disagreement confidence but weakens broader review-control balance",
            },
            {
                "decision_item": "external_patterned_felid_access_audit_next",
                "decision": "yes_access_audit_only",
                "rationale": "CzechLynx confidence refinement is enough for an access/license audit, not validation claims",
            },
            {
                "decision_item": "broader_felid_claim_supported",
                "decision": "no",
                "rationale": "no external known-ID patterned-felid benchmark was run",
            },
            {
                "decision_item": "mainland_clouded_leopard_marbled_cat_status",
                "decision": "motivation_only",
                "rationale": "these taxa remain future conservation motivation only",
            },
        ]
    )


def make_figures(def_audit: pd.DataFrame, grid: pd.DataFrame, top: pd.DataFrame, comparison: pd.DataFrame, boot: pd.DataFrame,
                 paired: pd.DataFrame, failure: pd.DataFrame) -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(8, 6))
    plt.scatter(grid["disagreement_exposure_review"], grid["false_top1_rate"], s=6, alpha=0.25)
    plt.scatter(top["disagreement_exposure_review"], top["false_top1_rate"], s=70, color="#CC6677")
    plt.xlabel("Disagreement exposure among review candidates")
    plt.ylabel("False top-1 rate")
    plt.title("Descriptor disagreement vs false top-1")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "phase8_disagreement_exposure_vs_false_top1.png", dpi=180)
    plt.close()

    metrics = ["false_top1_rate", "query_coverage", "positive_retention", "review_burden_reduction", "disagreement_exposure_review"]
    labels = comparison["selection_regime"].str.replace("_", " ")
    plt.figure(figsize=(11, 6))
    x = np.arange(len(comparison))
    width = 0.15
    for i, metric in enumerate(metrics):
        plt.bar(x + i * width, comparison[metric], width=width, label=metric)
    plt.xticks(x + width * 2, labels, rotation=35, ha="right", fontsize=8)
    plt.legend(fontsize=7)
    plt.title("v2 vs selected v3 metrics")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "phase8_v2_vs_v3_metric_comparison.png", dpi=180)
    plt.close()

    b = boot[boot["selection_regime"] == "balanced_v3_main_candidate"].copy()
    plt.figure(figsize=(10, 5))
    x = np.arange(len(b))
    plt.errorbar(x, b["estimate"], yerr=[b["estimate"] - b["ci_lower"], b["ci_upper"] - b["estimate"]], fmt="o")
    plt.xticks(x, b["metric"].str.replace("_", " "), rotation=40, ha="right", fontsize=8)
    plt.title("Bootstrap intervals for balanced v3")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "phase8_bootstrap_intervals_selected_policies.png", dpi=180)
    plt.close()

    plt.figure(figsize=(10, 5))
    p = paired[paired["selection_regime"] == "balanced_v3_main_candidate"].copy()
    x = np.arange(len(p))
    plt.axhline(0, color="black", linewidth=0.8)
    plt.errorbar(x, p["estimate"], yerr=[p["estimate"] - p["ci_lower"], p["ci_upper"] - p["estimate"]], fmt="o")
    plt.xticks(x, p["metric"].str.replace("_", " "), rotation=40, ha="right", fontsize=8)
    plt.title("Paired bootstrap differences vs v2")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "phase8_paired_bootstrap_differences_vs_v2.png", dpi=180)
    plt.close()

    assign = failure.groupby(["assignment", "failure_mode"], as_index=False)["failure_mode_rate"].mean()
    dis = assign[assign["failure_mode"] == "active_disagreement"]
    plt.figure(figsize=(7, 5))
    plt.bar(dis["assignment"], dis["failure_mode_rate"], color="#4477AA")
    plt.ylabel("Disagreement exposure")
    plt.title("Disagreement exposure by assignment")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "phase8_disagreement_exposure_by_assignment.png", dpi=180)
    plt.close()

    v2_dis = float(top[top["policy_id"] == "v2_p08117"]["disagreement_exposure_review"].iloc[0])
    grid = grid.copy()
    grid["disagreement_reduction_vs_v2"] = v2_dis - grid["disagreement_exposure_review"]
    plt.figure(figsize=(8, 6))
    plt.scatter(grid["query_coverage"], grid["disagreement_reduction_vs_v2"], s=6, alpha=0.25)
    plt.xlabel("Query coverage")
    plt.ylabel("Disagreement exposure reduction vs v2")
    plt.title("Coverage vs disagreement reduction")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "phase8_coverage_vs_disagreement_reduction.png", dpi=180)
    plt.close()

    plt.figure(figsize=(8, 6))
    plt.scatter(grid["positive_retention"], grid["disagreement_reduction_vs_v2"], s=6, alpha=0.25)
    plt.xlabel("Positive retention")
    plt.ylabel("Disagreement exposure reduction vs v2")
    plt.title("Positive retention vs disagreement reduction")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "phase8_positive_retention_vs_disagreement_reduction.png", dpi=180)
    plt.close()

    review_failure = failure[(failure["assignment"] == "review_candidate") & (failure["selection_regime"] == "balanced_v3_main_candidate")].sort_values("failure_mode_rate", ascending=False)
    plt.figure(figsize=(10, 5))
    plt.bar(review_failure["failure_mode"].str.replace("_", " "), review_failure["failure_mode_rate"], color="#AA4499")
    plt.xticks(rotation=45, ha="right", fontsize=8)
    plt.ylabel("Failure-mode exposure")
    plt.title("Failure exposure among balanced-v3 reviewed candidates")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "phase8_failure_mode_exposure_review_candidates.png", dpi=180)
    plt.close()


def run(args: argparse.Namespace) -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    metadata, similarities = align_inputs(args)
    candidates = build_mega_candidates(metadata, similarities, max_k=20)
    policies = policy_grid()
    metrics: list[dict[str, object]] = []
    assigned_cache: dict[str, pd.DataFrame] = {}
    for policy in policies:
        metric, assigned = evaluate_policy(candidates, policy)
        metrics.append(metric)
        if policy["policy_id"] == "v2_p08117":
            assigned_cache[policy["policy_id"]] = assigned
    grid = pd.DataFrame(metrics)
    top = select_top_policies(grid)
    for _, policy in top.iterrows():
        if policy["policy_id"] not in assigned_cache:
            _, assigned_cache[policy["policy_id"]] = evaluate_policy(candidates, policy.to_dict())
    def_audit = disagreement_definition_audit(candidates, assigned_cache["v2_p08117"])
    boot_frames = []
    summaries: dict[str, pd.DataFrame] = {}
    for _, policy in top.iterrows():
        boot, summary = query_boot_metrics(assigned_cache[policy["policy_id"]], policy.to_dict(), args.bootstrap_iterations)
        boot_frames.append(boot)
        summaries[policy["policy_id"]] = summary
    boot = pd.concat(boot_frames, ignore_index=True)
    paired = paired_bootstrap(summaries["v2_p08117"], summaries, top, args.bootstrap_iterations)
    failure = failure_summary(assigned_cache, top)
    comparison = comparison_table(top)
    ready = readiness(def_audit, top, paired)
    recommended = top[top["selection_regime"] == "balanced_v3_main_candidate"].iloc[0]
    assignments = assigned_cache[recommended["policy_id"]].copy()
    assignments["assignment_reason"] = np.where(assignments["active_disagreement"], "descriptor_disagreement_control_applied", "pf_eri_visual_evidence_control")
    assignment_cols = [
        "query_token",
        "gallery_token",
        "descriptor",
        "rank",
        "assignment",
        "assignment_reason",
        "active_disagreement",
        "query_band",
        "gallery_band",
        "pair_min_score",
        "pair_mean_score",
        "megadescriptor_similarity",
        "resnet50_similarity",
        "resnet50_rank",
    ]
    assignments[assignment_cols].rename(columns={"assignment": "recommended_assignment", "active_disagreement": "disagreement_flag"}).to_csv(ASSIGNMENTS_CSV, index=False)
    def_audit.to_csv(DEFINITION_AUDIT_CSV, index=False)
    grid.to_csv(POLICY_GRID_CSV, index=False)
    top.to_csv(TOP_POLICIES_CSV, index=False)
    comparison.to_csv(COMPARISON_CSV, index=False)
    failure.to_csv(FAILURE_SUMMARY_CSV, index=False)
    boot.to_csv(BOOTSTRAP_CSV, index=False)
    paired.to_csv(PAIRED_BOOTSTRAP_CSV, index=False)
    ready.to_csv(READINESS_CSV, index=False)
    make_figures(def_audit, grid, top, comparison, boot, paired, failure)

    print("PASS: Phase 8 Slice 3B descriptor-disagreement confidence control complete")
    print(f"candidate_v3_policy_count: {len(grid)}")
    print(f"disagreement_definitions_tested: {len(DISAGREEMENT_DEFINITIONS)}")
    print(
        "balanced_v3: "
        f"{recommended['policy_id']} / {recommended['policy_family']} / top_k={recommended['top_k']} / "
        f"false_top1={recommended['false_top1_rate']:.4f} / query_coverage={recommended['query_coverage']:.4f} / "
        f"positive_retention={recommended['positive_retention']:.4f} / disagreement_exposure={recommended['disagreement_exposure_review']:.4f}"
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
