#!/usr/bin/env python3
"""Select the final utility-constrained PF-ERI retrieval-control policy."""

from __future__ import annotations

import argparse
import math
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
    evaluate_policy,
    failure_flags,
    query_level_summary,
    v2_policy,
)
from phase8_pf_eri_retrieval_control_v2_optimizer import align_inputs

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SLICE3B_DIR = PROJECT_ROOT / "outputs/czechlynx/phase8/descriptor_disagreement_confidence_control"
OUTPUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase8/utility_constrained_policy_selection"
FIGURE_DIR = OUTPUT_DIR / "figures"

CANDIDATE_COMPARISON_CSV = OUTPUT_DIR / "phase8_utility_policy_candidate_comparison.csv"
COMPONENT_SCORES_CSV = OUTPUT_DIR / "phase8_utility_policy_component_scores.csv"
REGIME_WINNERS_CSV = OUTPUT_DIR / "phase8_utility_policy_regime_winners.csv"
PAIRED_BOOTSTRAP_CSV = OUTPUT_DIR / "phase8_utility_policy_paired_bootstrap_differences.csv"
BOOTSTRAP_CSV = OUTPUT_DIR / "phase8_utility_policy_bootstrap_intervals.csv"
ASSIGNMENT_CSV = OUTPUT_DIR / "phase8_utility_policy_recommended_assignment.csv"
FINAL_DECISION_CSV = OUTPUT_DIR / "phase8_utility_policy_final_decision.csv"

SLICE3B_TOP_POLICIES_CSV = SLICE3B_DIR / "phase8_descriptor_disagreement_top_policies.csv"

RANDOM_SEED = 20260614
BOOTSTRAP_ITERATIONS = 500
QUERY_COUNT = 500
REQUIRED_REGIMES = [
    "operational_primary",
    "confidence_first",
    "coverage_first",
    "evidence_control",
    "external_testing_readiness",
]


def clamp01(value: float) -> float:
    if math.isnan(float(value)):
        return 0.0
    return float(max(0.0, min(1.0, value)))


def policy_from_top(top: pd.DataFrame, selection_regime: str) -> dict[str, object]:
    row = top[top["selection_regime"] == selection_regime]
    if row.empty:
        raise ValueError(f"Missing Slice 3B selected policy: {selection_regime}")
    return row.iloc[0].to_dict()


def candidate_specs(slice3b_top: pd.DataFrame) -> list[dict[str, object]]:
    v2 = v2_policy()
    return [
        {
            "candidate_id": "A_v2_primary_baseline",
            "candidate_label": "Candidate A - v2 primary baseline",
            "candidate_type": "v2_operational_policy",
            "source_policy_id": "v2_p08117",
            "policy": v2,
            "interpretability_score": 0.95,
            "caution_layer": "no",
        },
        {
            "candidate_id": "B_reliability_first_v3",
            "candidate_label": "Candidate B - reliability-first v3",
            "candidate_type": "v3_disagreement_control",
            "source_policy_id": "v3_p03049",
            "policy": policy_from_top(slice3b_top, "reliability_first_disagreement"),
            "interpretability_score": 0.85,
            "caution_layer": "no",
        },
        {
            "candidate_id": "C_balanced_v3",
            "candidate_label": "Candidate C - balanced v3",
            "candidate_type": "v3_disagreement_control",
            "source_policy_id": "v3_p05405",
            "policy": policy_from_top(slice3b_top, "balanced_v3_main_candidate"),
            "interpretability_score": 0.75,
            "caution_layer": "no",
        },
        {
            "candidate_id": "D_coverage_preserving_v3",
            "candidate_label": "Candidate D - coverage-preserving v3",
            "candidate_type": "v3_disagreement_control",
            "source_policy_id": "v3_p05041",
            "policy": policy_from_top(slice3b_top, "coverage_preserving_disagreement"),
            "interpretability_score": 0.82,
            "caution_layer": "no",
        },
        {
            "candidate_id": "E_evidence_control_v3",
            "candidate_label": "Candidate E - evidence-control v3",
            "candidate_type": "v3_evidence_control",
            "source_policy_id": "v3_p01421",
            "policy": policy_from_top(slice3b_top, "evidence_control"),
            "interpretability_score": 0.88,
            "caution_layer": "no",
        },
        {
            "candidate_id": "F_v2_with_disagreement_caution",
            "candidate_label": "Candidate F - v2 plus disagreement caution layer",
            "candidate_type": "hybrid_review_control_policy",
            "source_policy_id": "v2_p08117_caution",
            "policy": {
                **v2,
                "policy_id": "v2_p08117_caution",
                "policy_family": "Hybrid_v2_with_disagreement_caution",
                "disagreement_action": "caution_flag_only",
            },
            "interpretability_score": 0.98,
            "caution_layer": "yes",
        },
    ]


def evaluate_candidate(candidates: pd.DataFrame, spec: dict[str, object]) -> tuple[dict[str, object], pd.DataFrame]:
    if spec["candidate_id"] == "F_v2_with_disagreement_caution":
        base_policy = v2_policy()
        metrics, assigned = evaluate_policy(candidates, base_policy)
        assigned = assigned.copy()
        assigned["caution_flag"] = assigned["active_disagreement"] & (assigned["assignment"] == "review_candidate")
        metrics["policy_id"] = "v2_p08117_caution"
        metrics["policy_family"] = "Hybrid_v2_with_disagreement_caution"
        metrics["disagreement_action"] = "caution_flag_only"
    else:
        metrics, assigned = evaluate_policy(candidates, spec["policy"])
        assigned = assigned.copy()
        assigned["caution_flag"] = False
    review = assigned[assigned["assignment"] == "review_candidate"]
    metrics.update(
        {
            "candidate_id": spec["candidate_id"],
            "candidate_label": spec["candidate_label"],
            "candidate_type": spec["candidate_type"],
            "source_policy_id": spec["source_policy_id"],
            "caution_layer": spec["caution_layer"],
            "interpretability_score": spec["interpretability_score"],
            "reviewed_candidates_per_query": metrics.get("review_candidates_per_query", math.nan),
            "severe_failure_exposure_review": metrics.get("failure_exposure_review", math.nan),
            "high_descriptor_low_evidence_exposure_review": float(review["high_descriptor_low_evidence"].mean()) if len(review) else math.nan,
            "caution_flag_review_exposure": float(review["caution_flag"].mean()) if len(review) else 0.0,
        }
    )
    return metrics, assigned


def utility_scores(metrics: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in metrics.iterrows():
        false_burden_score = clamp01(1.0 - row["false_reviewed_candidates_per_query"] / 5.0)
        reliability = (
            0.35 * clamp01(1.0 - row["false_top1_rate"])
            + 0.30 * false_burden_score
            + 0.35 * clamp01(1.0 - row["disagreement_exposure_review"])
        )
        coverage = (
            0.45 * clamp01(row["query_coverage"])
            + 0.45 * clamp01(row["positive_retention"])
            + 0.10 * clamp01(row["true_same_candidate_retention"])
        )
        review_burden = (
            0.55 * clamp01(row["review_burden_reduction"])
            + 0.45 * false_burden_score
        )
        disagreement_control = 0.70 if row["caution_layer"] == "yes" else clamp01(1.0 - row["disagreement_exposure_review"])
        evidence_control = (
            0.30 * clamp01(1.0 - row["severe_failure_exposure_review"])
            + 0.20 * clamp01(1.0 - row["high_descriptor_low_evidence_exposure_review"])
            + 0.25 * disagreement_control
            + 0.25 * clamp01(row["interpretability_score"])
        )
        coverage_extremeness = 1.0 - min(abs(float(row["query_coverage"]) - 0.72) / 0.72, 1.0)
        workload_score = clamp01(1.0 - row["reviewed_candidates_per_query"] / 12.5)
        bootstrap_stability_proxy = clamp01(1.0 - abs(float(row["false_top1_rate"]) - 0.88) / 0.20)
        operational = (
            0.30 * clamp01(row["interpretability_score"])
            + 0.25 * coverage_extremeness
            + 0.20 * workload_score
            + 0.25 * bootstrap_stability_proxy
        )
        visible_utility_score = (
            0.28 * reliability
            + 0.24 * coverage
            + 0.20 * review_burden
            + 0.16 * evidence_control
            + 0.12 * operational
        )
        rows.append(
            {
                "candidate_id": row["candidate_id"],
                "candidate_label": row["candidate_label"],
                "reliability_utility": reliability,
                "coverage_utility": coverage,
                "review_burden_utility": review_burden,
                "evidence_control_utility": evidence_control,
                "operational_utility": operational,
                "visible_utility_score": visible_utility_score,
                "utility_category": utility_category(visible_utility_score),
                "component_score_notes": "visible weighted score; components retained separately for interpretation",
            }
        )
    return pd.DataFrame(rows)


def utility_category(score: float) -> str:
    if score >= 0.70:
        return "strong"
    if score >= 0.55:
        return "usable_with_caveats"
    if score >= 0.40:
        return "limited"
    return "not_recommended"


def choose_regime_winners(comparison: pd.DataFrame, components: pd.DataFrame) -> pd.DataFrame:
    component_cols = [
        "candidate_id",
        "candidate_label",
        "reliability_utility",
        "coverage_utility",
        "review_burden_utility",
        "evidence_control_utility",
        "operational_utility",
    ]
    df = comparison.merge(components[component_cols], on=["candidate_id", "candidate_label"], how="left")
    rows = []
    regimes = {
        "operational_primary": {
            "weights": {
                "operational_utility": 0.30,
                "coverage_utility": 0.25,
                "review_burden_utility": 0.20,
                "reliability_utility": 0.15,
                "evidence_control_utility": 0.10,
            },
            "rationale": "favors v2-like balance, adequate coverage, manageable burden, and clear caveat handling",
        },
        "confidence_first": {
            "weights": {
                "reliability_utility": 0.45,
                "evidence_control_utility": 0.25,
                "review_burden_utility": 0.20,
                "coverage_utility": 0.05,
                "operational_utility": 0.05,
            },
            "rationale": "favors low false top-1, low false-review burden, and low disagreement exposure",
        },
        "coverage_first": {
            "weights": {
                "coverage_utility": 0.55,
                "operational_utility": 0.15,
                "reliability_utility": 0.10,
                "review_burden_utility": 0.10,
                "evidence_control_utility": 0.10,
            },
            "rationale": "favors query coverage and positive retention even with higher burden",
        },
        "evidence_control": {
            "weights": {
                "evidence_control_utility": 0.45,
                "reliability_utility": 0.20,
                "review_burden_utility": 0.15,
                "coverage_utility": 0.10,
                "operational_utility": 0.10,
            },
            "rationale": "favors clean visual failure handling and explicit disagreement treatment",
        },
        "external_testing_readiness": {
            "weights": {
                "operational_utility": 0.30,
                "evidence_control_utility": 0.25,
                "coverage_utility": 0.20,
                "review_burden_utility": 0.15,
                "reliability_utility": 0.10,
            },
            "rationale": "favors interpretable, non-extreme policy suitable for access/feasibility testing",
        },
    }
    for regime, info in regimes.items():
        scored = df.copy()
        scored["regime_score"] = 0.0
        for metric, weight in info["weights"].items():
            scored["regime_score"] += scored[metric] * weight
        if regime in {"operational_primary", "external_testing_readiness"}:
            eligible = scored[
                (scored["query_coverage"] >= 0.60)
                & (scored["positive_retention"] >= 0.55)
                & (scored["false_reviewed_candidates_per_query"] <= 5.0)
            ]
            if eligible.empty:
                eligible = scored
        elif regime == "coverage_first":
            eligible = scored[scored["query_coverage"] >= 0.80]
            if eligible.empty:
                eligible = scored
        else:
            eligible = scored
        winner = eligible.sort_values(
            ["regime_score", "visible_utility_score", "query_coverage"],
            ascending=[False, False, False],
        ).iloc[0]
        rows.append(
            {
                "decision_regime": regime,
                "winner_candidate_id": winner["candidate_id"],
                "winner_candidate_label": winner["candidate_label"],
                "winner_source_policy_id": winner["source_policy_id"],
                "regime_score": winner["regime_score"],
                "visible_utility_score": winner["visible_utility_score"],
                "query_coverage": winner["query_coverage"],
                "positive_retention": winner["positive_retention"],
                "false_top1_rate": winner["false_top1_rate"],
                "false_reviewed_candidates_per_query": winner["false_reviewed_candidates_per_query"],
                "disagreement_exposure_review": winner["disagreement_exposure_review"],
                "rationale": info["rationale"],
            }
        )
    return pd.DataFrame(rows)


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
        vals = sample["ap"].dropna()
        return float(vals.mean()) if len(vals) else math.nan
    if metric == "review_burden_reduction":
        denom = sample["candidate_count"].sum()
        return float(1.0 - sample["review_count"].sum() / denom) if denom else math.nan
    if metric == "false_reviewed_candidates_per_query":
        return float(sample["false_reviewed"].sum() / len(sample))
    if metric == "disagreement_exposure_review":
        rows = sample[sample["has_review"] == 1]
        return float(rows["disagreement_review"].mean()) if len(rows) else math.nan
    raise ValueError(metric)


def bootstrap_intervals(assigned_by_candidate: dict[str, pd.DataFrame], comparison: pd.DataFrame, iterations: int) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    rng = np.random.default_rng(RANDOM_SEED)
    metrics = [
        "false_top1_rate",
        "query_coverage",
        "positive_retention",
        "mAP_among_covered_positives",
        "review_burden_reduction",
        "false_reviewed_candidates_per_query",
        "disagreement_exposure_review",
    ]
    rows = []
    summaries = {}
    for _, candidate in comparison.iterrows():
        assigned = assigned_by_candidate[candidate["candidate_id"]]
        summary = query_level_summary(assigned)
        summaries[candidate["candidate_id"]] = summary
        for metric in metrics:
            vals = []
            for _ in range(iterations):
                sample = summary.iloc[rng.choice(np.arange(QUERY_COUNT), size=QUERY_COUNT, replace=True)]
                vals.append(boot_metric(sample, metric))
            clean = np.asarray([v for v in vals if not math.isnan(float(v))], dtype=float)
            rows.append(
                {
                    "candidate_id": candidate["candidate_id"],
                    "candidate_label": candidate["candidate_label"],
                    "metric": metric,
                    "bootstrap_iterations": iterations,
                    "estimate": candidate[metric],
                    "ci_lower": float(np.percentile(clean, 2.5)) if len(clean) else math.nan,
                    "ci_upper": float(np.percentile(clean, 97.5)) if len(clean) else math.nan,
                }
            )
    return pd.DataFrame(rows), summaries


def paired_bootstrap_differences(comparison: pd.DataFrame, summaries: dict[str, pd.DataFrame], iterations: int) -> pd.DataFrame:
    rng = np.random.default_rng(RANDOM_SEED)
    v2_id = "A_v2_primary_baseline"
    metrics = [
        "false_top1_rate",
        "query_coverage",
        "positive_retention",
        "mAP_among_covered_positives",
        "review_burden_reduction",
        "false_reviewed_candidates_per_query",
        "disagreement_exposure_review",
    ]
    v2_summary = summaries[v2_id]
    rows = []
    for _, candidate in comparison[comparison["candidate_id"] != v2_id].iterrows():
        summary = summaries[candidate["candidate_id"]]
        for metric in metrics:
            vals = []
            for _ in range(iterations):
                idx = rng.choice(np.arange(QUERY_COUNT), size=QUERY_COUNT, replace=True)
                vals.append(boot_metric(summary.iloc[idx], metric) - boot_metric(v2_summary.iloc[idx], metric))
            clean = np.asarray([v for v in vals if not math.isnan(float(v))], dtype=float)
            v2_est = comparison.loc[comparison["candidate_id"] == v2_id, metric].iloc[0]
            rows.append(
                {
                    "candidate_id": candidate["candidate_id"],
                    "candidate_label": candidate["candidate_label"],
                    "metric": f"delta_{metric}_vs_v2",
                    "bootstrap_iterations": iterations,
                    "estimate": float(candidate[metric] - v2_est),
                    "ci_lower": float(np.percentile(clean, 2.5)) if len(clean) else math.nan,
                    "ci_upper": float(np.percentile(clean, 97.5)) if len(clean) else math.nan,
                }
            )
    return pd.DataFrame(rows)


def final_decision_rows(regime_winners: pd.DataFrame) -> pd.DataFrame:
    operational = regime_winners[regime_winners["decision_regime"] == "operational_primary"].iloc[0]
    external = regime_winners[regime_winners["decision_regime"] == "external_testing_readiness"].iloc[0]
    final_policy = "F_v2_with_disagreement_caution"
    return pd.DataFrame(
        [
            {
                "decision_item": "final_carry_forward_policy",
                "decision": final_policy,
                "rationale": "v2 remains the operational base, with descriptor disagreement carried as a caution layer rather than automatic exclusion",
            },
            {
                "decision_item": "operational_primary_winner",
                "decision": operational["winner_candidate_id"],
                "rationale": "selected by explicit operational utility constraints",
            },
            {
                "decision_item": "external_testing_readiness_winner",
                "decision": external["winner_candidate_id"],
                "rationale": "selected for access/feasibility testing, not species validation",
            },
            {
                "decision_item": "v2_remains_primary",
                "decision": "yes",
                "rationale": "v2 has the best operational balance among adequate-coverage, manageable-burden candidates",
            },
            {
                "decision_item": "v3_replaces_v2",
                "decision": "no",
                "rationale": "v3 disagreement-control variants either sacrifice coverage or increase false-review burden",
            },
            {
                "decision_item": "v3_becomes_confidence_variant",
                "decision": "yes",
                "rationale": "v3 reliability-first and coverage-preserving variants are useful sensitivity and confidence-control references",
            },
            {
                "decision_item": "descriptor_disagreement_added_as_caution_layer",
                "decision": "yes",
                "rationale": "disagreement is useful for caution marking, but not precise enough for automatic exclusion",
            },
            {
                "decision_item": "external_access_audit_can_proceed",
                "decision": "yes_access_feasibility_only",
                "rationale": "current evidence supports access and feasibility audit, not external validation claims",
            },
            {
                "decision_item": "broader_felid_validation_supported",
                "decision": "no",
                "rationale": "only CzechLynx aggregate known-ID validation was run",
            },
            {
                "decision_item": "mainland_clouded_leopard_marbled_cat_status",
                "decision": "motivation_only",
                "rationale": "these taxa remain future conservation motivation and are not validated here",
            },
        ]
    )


def recommended_assignment(assigned: pd.DataFrame) -> pd.DataFrame:
    out = assigned.sort_values(["query_idx", "rank"]).reset_index(drop=True).copy()
    out["candidate_row_id"] = [f"phase8_slice3c_candidate_{i:05d}" for i in range(1, len(out) + 1)]
    out["final_policy_id"] = "F_v2_with_disagreement_caution"
    out["final_policy_role"] = "carry_forward_operational_policy"
    out["recommended_assignment"] = out["assignment"]
    out["descriptor_disagreement_caution"] = np.where(out["caution_flag"], "yes", "no")
    out["assignment_reason"] = np.select(
        [
            out["assignment"] == "defer_candidate",
            out["caution_flag"],
        ],
        [
            "pf_eri_visual_or_descriptor_control_defer",
            "review_candidate_with_descriptor_disagreement_caution",
        ],
        default="review_candidate_without_descriptor_disagreement_caution",
    )
    return out[
        [
            "candidate_row_id",
            "final_policy_id",
            "final_policy_role",
            "rank",
            "recommended_assignment",
            "descriptor_disagreement_caution",
            "assignment_reason",
            "query_band",
            "gallery_band",
            "pair_min_score",
            "pair_mean_score",
            "megadescriptor_similarity",
            "resnet50_similarity",
            "resnet50_rank",
        ]
    ]


def make_figures(comparison: pd.DataFrame, components: pd.DataFrame, winners: pd.DataFrame, boot: pd.DataFrame, paired: pd.DataFrame) -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    merged = comparison.merge(components, on=["candidate_id", "candidate_label"])
    labels = merged["candidate_id"].str.replace("_", " ")
    component_cols = [
        "reliability_utility",
        "coverage_utility",
        "review_burden_utility",
        "evidence_control_utility",
        "operational_utility",
    ]
    x = np.arange(len(merged))
    width = 0.16
    plt.figure(figsize=(13, 6))
    for i, col in enumerate(component_cols):
        plt.bar(x + (i - 2) * width, merged[col], width=width, label=col.replace("_", " "))
    plt.xticks(x, labels, rotation=35, ha="right", fontsize=8)
    plt.ylabel("Utility component score")
    plt.title("Candidate utility component comparison")
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "phase8_utility_candidate_component_comparison.png", dpi=180)
    plt.close()

    p = paired[paired["metric"].isin(["delta_false_top1_rate_vs_v2", "delta_query_coverage_vs_v2", "delta_positive_retention_vs_v2", "delta_false_reviewed_candidates_per_query_vs_v2"])]
    plt.figure(figsize=(13, 6))
    xpos = np.arange(len(p))
    lower = p["estimate"] - p["ci_lower"]
    upper = p["ci_upper"] - p["estimate"]
    plt.errorbar(xpos, p["estimate"], yerr=[lower, upper], fmt="o", color="#4477AA")
    plt.axhline(0, color="black", linewidth=0.8)
    plt.xticks(xpos, (p["candidate_id"] + "\n" + p["metric"].str.replace("delta_", "").str.replace("_vs_v2", "")).str.replace("_", " "), rotation=45, ha="right", fontsize=7)
    plt.ylabel("Paired bootstrap difference vs v2")
    plt.title("v2 vs v3 paired bootstrap differences")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "phase8_utility_v2_vs_v3_paired_bootstrap_differences.png", dpi=180)
    plt.close()

    plt.figure(figsize=(8, 6))
    plt.scatter(merged["query_coverage"], merged["false_top1_rate"], s=90, color="#228833")
    for _, row in merged.iterrows():
        plt.annotate(row["candidate_id"].split("_")[0], (row["query_coverage"], row["false_top1_rate"]), fontsize=9)
    plt.xlabel("Query coverage")
    plt.ylabel("False top-1 rate")
    plt.title("False top-1 vs query coverage")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "phase8_utility_false_top1_vs_query_coverage.png", dpi=180)
    plt.close()

    plt.figure(figsize=(8, 6))
    plt.scatter(merged["false_reviewed_candidates_per_query"], merged["positive_retention"], s=90, color="#CC6677")
    for _, row in merged.iterrows():
        plt.annotate(row["candidate_id"].split("_")[0], (row["false_reviewed_candidates_per_query"], row["positive_retention"]), fontsize=9)
    plt.xlabel("False reviewed candidates per query")
    plt.ylabel("Positive retention")
    plt.title("Positive retention vs false-review burden")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "phase8_utility_positive_retention_vs_false_review_burden.png", dpi=180)
    plt.close()

    plt.figure(figsize=(8, 6))
    plt.scatter(merged["review_burden_reduction"], merged["disagreement_exposure_review"], s=90, color="#AA4499")
    for _, row in merged.iterrows():
        plt.annotate(row["candidate_id"].split("_")[0], (row["review_burden_reduction"], row["disagreement_exposure_review"]), fontsize=9)
    plt.xlabel("Review burden reduction")
    plt.ylabel("Disagreement exposure among review candidates")
    plt.title("Disagreement exposure vs review burden")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "phase8_utility_disagreement_exposure_vs_review_burden.png", dpi=180)
    plt.close()

    b = boot[boot["metric"].isin(["false_top1_rate", "query_coverage", "positive_retention", "false_reviewed_candidates_per_query"])]
    plt.figure(figsize=(13, 6))
    xpos = np.arange(len(b))
    lower = b["estimate"] - b["ci_lower"]
    upper = b["ci_upper"] - b["estimate"]
    plt.errorbar(xpos, b["estimate"], yerr=[lower, upper], fmt="o", color="#332288")
    plt.xticks(xpos, (b["candidate_id"] + "\n" + b["metric"]).str.replace("_", " "), rotation=45, ha="right", fontsize=7)
    plt.ylabel("Metric value")
    plt.title("Final candidate comparison with bootstrap intervals")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "phase8_utility_final_candidate_confidence_intervals.png", dpi=180)
    plt.close()

    plt.figure(figsize=(10, 5))
    plt.bar(winners["decision_regime"].str.replace("_", " "), winners["regime_score"], color="#117733")
    plt.xticks(rotation=35, ha="right", fontsize=8)
    plt.ylabel("Winning regime score")
    plt.title("Regime winners summary")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "phase8_utility_regime_winners_summary.png", dpi=180)
    plt.close()


def run(args: argparse.Namespace) -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    metadata, similarities = align_inputs(args)
    candidates = build_mega_candidates(metadata, similarities, max_k=20)
    slice3b_top = pd.read_csv(args.slice3b_top_policies_csv)
    specs = candidate_specs(slice3b_top)

    metric_rows: list[dict[str, object]] = []
    assigned_by_candidate: dict[str, pd.DataFrame] = {}
    for spec in specs:
        metrics, assigned = evaluate_candidate(candidates, spec)
        metric_rows.append(metrics)
        assigned_by_candidate[str(spec["candidate_id"])] = assigned
    comparison = pd.DataFrame(metric_rows)
    key_cols = [
        "candidate_id",
        "candidate_label",
        "candidate_type",
        "source_policy_id",
        "policy_family",
        "top_k",
        "query_threshold",
        "gallery_threshold",
        "pair_evidence_rule",
        "disagreement_definition",
        "disagreement_action",
        "strictness",
        "caution_layer",
        "interpretability_score",
        "query_coverage",
        "positive_retention",
        "mAP_among_covered_positives",
        "false_top1_rate",
        "review_burden_reduction",
        "false_reviewed_candidates_per_query",
        "reviewed_candidates_per_query",
        "disagreement_exposure_review",
        "severe_failure_exposure_review",
        "high_descriptor_low_evidence_exposure_review",
        "caution_flag_review_exposure",
        "review_candidate_count",
        "defer_candidate_count",
        "exclude_candidate_count",
        "true_same_candidate_retention",
        "false_reviewed_candidate_rate",
    ]
    comparison = comparison[key_cols].copy()
    components = utility_scores(comparison)
    comparison = comparison.merge(
        components[["candidate_id", "visible_utility_score", "utility_category"]],
        on="candidate_id",
        how="left",
    )
    comparison["recommendation_status"] = np.select(
        [
            comparison["candidate_id"] == "F_v2_with_disagreement_caution",
            comparison["candidate_id"] == "A_v2_primary_baseline",
            comparison["candidate_id"].isin(["B_reliability_first_v3", "D_coverage_preserving_v3"]),
        ],
        [
            "final_carry_forward",
            "primary_baseline_retained",
            "confidence_or_sensitivity_variant",
        ],
        default="not_primary",
    )
    winners = choose_regime_winners(comparison, components)
    boot, summaries = bootstrap_intervals(assigned_by_candidate, comparison, args.bootstrap_iterations)
    paired = paired_bootstrap_differences(comparison, summaries, args.bootstrap_iterations)
    final = final_decision_rows(winners)
    assignments = recommended_assignment(assigned_by_candidate["F_v2_with_disagreement_caution"])

    comparison.to_csv(CANDIDATE_COMPARISON_CSV, index=False)
    components.to_csv(COMPONENT_SCORES_CSV, index=False)
    winners.to_csv(REGIME_WINNERS_CSV, index=False)
    paired.to_csv(PAIRED_BOOTSTRAP_CSV, index=False)
    boot.to_csv(BOOTSTRAP_CSV, index=False)
    assignments.to_csv(ASSIGNMENT_CSV, index=False)
    final.to_csv(FINAL_DECISION_CSV, index=False)
    make_figures(comparison, components, winners, boot, paired)

    operational = winners[winners["decision_regime"] == "operational_primary"].iloc[0]
    confidence = winners[winners["decision_regime"] == "confidence_first"].iloc[0]
    external = winners[winners["decision_regime"] == "external_testing_readiness"].iloc[0]
    print("PASS: Phase 8 Slice 3C utility-constrained policy selection complete")
    print(f"candidate_policy_count: {len(comparison)}")
    print(f"bootstrap_iterations: {args.bootstrap_iterations}")
    print(f"operational_primary_winner: {operational['winner_candidate_id']}")
    print(f"confidence_first_winner: {confidence['winner_candidate_id']}")
    print(f"external_testing_readiness_winner: {external['winner_candidate_id']}")
    print("final_carry_forward_policy: F_v2_with_disagreement_caution")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--megadescriptor-embeddings-csv", type=Path, default=MEGA_EMBEDDINGS_CSV)
    parser.add_argument("--resnet50-embeddings-csv", type=Path, default=RESNET_EMBEDDINGS_CSV)
    parser.add_argument("--identity-csv", type=Path, default=IDENTITY_CSV)
    parser.add_argument("--annotation-csv", type=Path, default=ANNOTATION_CSV)
    parser.add_argument("--slice3b-top-policies-csv", type=Path, default=SLICE3B_TOP_POLICIES_CSV)
    parser.add_argument("--bootstrap-iterations", type=int, default=BOOTSTRAP_ITERATIONS)
    return parser.parse_args()


def main() -> int:
    return run(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
