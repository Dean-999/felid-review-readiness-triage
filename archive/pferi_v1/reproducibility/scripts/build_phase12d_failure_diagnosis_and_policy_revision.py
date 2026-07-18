#!/usr/bin/env python3
"""Diagnose Phase 12 limitations and test calibrated policy revisions.

The goal is not to tune on the evaluation queries. For each split and
descriptor, policy weights are selected only on calibration queries and then
applied to evaluation queries.
"""

from __future__ import annotations

import argparse
import json
import math
from itertools import product
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE12_DIR = PROJECT_ROOT / "outputs/czechlynx/phase12"
TABLE = PHASE12_DIR / "phase12_pair_candidate_analysis_table.csv"
OUT_DIR = PHASE12_DIR / "rq_failure_diagnosis_policy_revision"

QUERY_DIFFICULTY = OUT_DIR / "phase12d_query_difficulty_and_ceiling.csv"
SCORE_SEPARATION = OUT_DIR / "phase12d_score_separation_diagnostics.csv"
FAILURE_MODES = OUT_DIR / "phase12d_false_top1_failure_modes.csv"
CALIBRATED_POLICIES = OUT_DIR / "phase12d_calibrated_policy_grid_selection.csv"
CALIBRATED_EVAL = OUT_DIR / "phase12d_calibrated_policy_evaluation.csv"
SUMMARY_MD = OUT_DIR / "phase12d_failure_diagnosis_and_revision_summary.md"
BUILD_AUDIT = OUT_DIR / "phase12d_failure_diagnosis_build_audit.json"

USECOLS = [
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
    "descriptor_similarity_percentile",
    "margin_confidence_norm",
    "descriptor_disagreement_score",
    "pair_reliability_score",
    "image_quality_proxy_min",
    "visual_identity_evidence_min",
    "descriptor_evidence_conflict_score",
    "candidate_utility_rq_score",
    "hard_negative_candidate",
    "admissibility_band",
    "conflict_band",
]

RANDOM_SEED = 20260617
BOOTSTRAP_ITERATIONS = 5000


def yes_no_to_bool(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin({"yes", "true", "1"})


def safe_mean(values: pd.Series | np.ndarray | list[float]) -> float:
    series = pd.Series(values, dtype="float64").dropna()
    return float(series.mean()) if len(series) else math.nan


def auc_from_scores(score: pd.Series, positive: pd.Series) -> float:
    frame = pd.DataFrame({"score": pd.to_numeric(score, errors="coerce"), "positive": positive.astype(bool)}).dropna()
    n_pos = int(frame["positive"].sum())
    n_neg = int((~frame["positive"]).sum())
    if n_pos == 0 or n_neg == 0:
        return math.nan
    ranks = frame["score"].rank(method="average")
    rank_sum_pos = float(ranks[frame["positive"]].sum())
    return float((rank_sum_pos - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def paired_bootstrap(values: np.ndarray) -> dict[str, float]:
    values = values[np.isfinite(values)]
    if len(values) == 0:
        return {"observed_mean": math.nan, "ci_low": math.nan, "ci_high": math.nan, "p_gt_0": math.nan, "n": 0}
    rng = np.random.default_rng(RANDOM_SEED)
    draws = np.empty(BOOTSTRAP_ITERATIONS, dtype=np.float64)
    for i in range(BOOTSTRAP_ITERATIONS):
        draws[i] = float(np.mean(rng.choice(values, size=len(values), replace=True)))
    return {
        "observed_mean": float(np.mean(values)),
        "ci_low": float(np.quantile(draws, 0.025)),
        "ci_high": float(np.quantile(draws, 0.975)),
        "p_gt_0": float(np.mean(draws > 0)),
        "n": int(len(values)),
    }


def load_table(path: Path) -> pd.DataFrame:
    table = pd.read_csv(path, usecols=USECOLS)
    for column in ["same_identity", "hard_negative_candidate"]:
        table[column] = yes_no_to_bool(table[column])
    numeric = [
        "split_id",
        "candidate_rank_raw",
        "candidate_rank_pf_eri",
        "descriptor_similarity_percentile",
        "margin_confidence_norm",
        "descriptor_disagreement_score",
        "pair_reliability_score",
        "image_quality_proxy_min",
        "visual_identity_evidence_min",
        "descriptor_evidence_conflict_score",
        "candidate_utility_rq_score",
    ]
    for column in numeric:
        table[column] = pd.to_numeric(table[column], errors="coerce")

    identity_sizes = (
        table[["query_image_id", "query_identity_token"]]
        .drop_duplicates()
        .groupby("query_identity_token")["query_image_id"]
        .nunique()
        .to_dict()
    )
    table["query_identity_image_count"] = table["query_identity_token"].map(identity_sizes).astype(int)
    table["gallery_positive_available"] = table["query_identity_image_count"] > 1
    return table


def top1_by_rank(table: pd.DataFrame, rank_column: str, method_id: str) -> pd.DataFrame:
    out = table[table[rank_column].eq(1)].copy()
    out["method_id"] = method_id
    return out


def top1_by_score(frame: pd.DataFrame, score: np.ndarray, method_id: str) -> pd.DataFrame:
    scored = frame.copy()
    scored["_score"] = score
    idx = scored.groupby(["query_image_id"])["_score"].idxmax()
    out = scored.loc[idx].drop(columns=["_score"]).copy()
    out["method_id"] = method_id
    return out


def method_metrics(top1: pd.DataFrame) -> dict[str, Any]:
    query_count = int(top1["query_image_id"].nunique())
    eligible = top1[top1["gallery_positive_available"]]
    ineligible = top1[~top1["gallery_positive_available"]]
    return {
        "query_count": query_count,
        "eligible_query_count": int(eligible["query_image_id"].nunique()),
        "singleton_or_no_gallery_positive_query_count": int(ineligible["query_image_id"].nunique()),
        "false_top1_rate_all": float((~top1["same_identity"]).mean()) if len(top1) else math.nan,
        "true_top1_rate_all": float(top1["same_identity"].mean()) if len(top1) else math.nan,
        "false_top1_rate_eligible": float((~eligible["same_identity"]).mean()) if len(eligible) else math.nan,
        "true_top1_rate_eligible": float(eligible["same_identity"].mean()) if len(eligible) else math.nan,
        "hard_negative_top1_rate": float(top1["hard_negative_candidate"].mean()) if len(top1) else math.nan,
        "mean_pair_reliability_top1": safe_mean(top1["pair_reliability_score"]),
        "mean_conflict_score_top1": safe_mean(top1["descriptor_evidence_conflict_score"]),
    }


def build_query_difficulty(table: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    raw = top1_by_rank(table, "candidate_rank_raw", "raw_descriptor")
    pf = top1_by_rank(table, "candidate_rank_pf_eri", "pf_eri_candidate_utility")
    for keys, frame in table.groupby(["split_id", "calibration_or_evaluation", "descriptor"]):
        split_id, role, descriptor = keys
        per_query = frame.groupby("query_image_id").agg(
            query_identity_image_count=("query_identity_image_count", "first"),
            gallery_positive_available=("gallery_positive_available", "first"),
            positives_in_top20=("same_identity", "sum"),
            hard_negatives_in_top20=("hard_negative_candidate", "sum"),
            max_descriptor_similarity=("descriptor_similarity_percentile", "max"),
            max_pair_reliability=("pair_reliability_score", "max"),
        )
        raw_part = raw[
            raw["split_id"].eq(split_id)
            & raw["calibration_or_evaluation"].eq(role)
            & raw["descriptor"].eq(descriptor)
        ]
        pf_part = pf[
            pf["split_id"].eq(split_id)
            & pf["calibration_or_evaluation"].eq(role)
            & pf["descriptor"].eq(descriptor)
        ]
        rows.append(
            {
                "split_id": int(split_id),
                "calibration_or_evaluation": role,
                "descriptor": descriptor,
                "query_count": int(len(per_query)),
                "gallery_positive_available_rate": float(per_query["gallery_positive_available"].mean()),
                "singleton_or_no_gallery_positive_rate": float((~per_query["gallery_positive_available"]).mean()),
                "any_positive_in_top20_rate": float((per_query["positives_in_top20"] > 0).mean()),
                "mean_positives_in_top20": safe_mean(per_query["positives_in_top20"]),
                "mean_hard_negatives_in_top20": safe_mean(per_query["hard_negatives_in_top20"]),
                "raw_true_top1_rate": float(raw_part["same_identity"].mean()),
                "pf_eri_true_top1_rate": float(pf_part["same_identity"].mean()),
                "oracle_top20_true_rate_ceiling": float((per_query["positives_in_top20"] > 0).mean()),
                "descriptor_ceiling_gap_raw_to_oracle": float((per_query["positives_in_top20"] > 0).mean() - raw_part["same_identity"].mean()),
                "pf_eri_gap_raw": float(pf_part["same_identity"].mean() - raw_part["same_identity"].mean()),
            }
        )
    return pd.DataFrame(rows)


def build_score_separation(table: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    score_cols = [
        "descriptor_similarity_percentile",
        "pair_reliability_score",
        "image_quality_proxy_min",
        "visual_identity_evidence_min",
        "descriptor_evidence_conflict_score",
        "candidate_utility_rq_score",
    ]
    for keys, frame in table.groupby(["split_id", "calibration_or_evaluation", "descriptor"]):
        split_id, role, descriptor = keys
        for score_col in score_cols:
            rows.append(
                {
                    "split_id": int(split_id),
                    "calibration_or_evaluation": role,
                    "descriptor": descriptor,
                    "score": score_col,
                    "auc_for_same_identity": auc_from_scores(frame[score_col], frame["same_identity"]),
                    "auc_for_false_candidate_risk": auc_from_scores(frame[score_col], ~frame["same_identity"]),
                    "mean_same_identity": safe_mean(frame.loc[frame["same_identity"], score_col]),
                    "mean_false_candidate": safe_mean(frame.loc[~frame["same_identity"], score_col]),
                    "mean_hard_negative": safe_mean(frame.loc[frame["hard_negative_candidate"], score_col]),
                }
            )
    return pd.DataFrame(rows)


def build_failure_modes(table: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    raw = top1_by_rank(table, "candidate_rank_raw", "raw_descriptor")
    pf = top1_by_rank(table, "candidate_rank_pf_eri", "pf_eri_candidate_utility")
    merged = raw.merge(
        pf[
            [
                "split_id",
                "calibration_or_evaluation",
                "descriptor",
                "query_image_id",
                "candidate_image_id",
                "same_identity",
                "hard_negative_candidate",
                "pair_reliability_score",
                "descriptor_evidence_conflict_score",
            ]
        ],
        on=["split_id", "calibration_or_evaluation", "descriptor", "query_image_id"],
        suffixes=("_raw", "_pf"),
        validate="one_to_one",
    )
    for keys, frame in merged.groupby(["split_id", "calibration_or_evaluation", "descriptor"]):
        split_id, role, descriptor = keys
        raw_false = ~frame["same_identity_raw"]
        pf_false = ~frame["same_identity_pf"]
        rows.append(
            {
                "split_id": int(split_id),
                "calibration_or_evaluation": role,
                "descriptor": descriptor,
                "query_count": int(len(frame)),
                "raw_false_pf_true_rescue_count": int((raw_false & frame["same_identity_pf"]).sum()),
                "raw_true_pf_false_harm_count": int((frame["same_identity_raw"] & pf_false).sum()),
                "both_false_count": int((raw_false & pf_false).sum()),
                "both_true_count": int((frame["same_identity_raw"] & frame["same_identity_pf"]).sum()),
                "raw_hard_negative_top1_count": int(frame["hard_negative_candidate_raw"].sum()),
                "pf_hard_negative_top1_count": int(frame["hard_negative_candidate_pf"].sum()),
                "mean_raw_top1_reliability_when_false": safe_mean(frame.loc[raw_false, "pair_reliability_score_raw"]),
                "mean_pf_top1_reliability_when_false": safe_mean(frame.loc[pf_false, "pair_reliability_score_pf"]),
                "mean_raw_top1_conflict_when_false": safe_mean(frame.loc[raw_false, "descriptor_evidence_conflict_score_raw"]),
                "mean_pf_top1_conflict_when_false": safe_mean(frame.loc[pf_false, "descriptor_evidence_conflict_score_pf"]),
            }
        )
    return pd.DataFrame(rows)


def candidate_score(frame: pd.DataFrame, weights: dict[str, float]) -> np.ndarray:
    return (
        weights["descriptor"] * frame["descriptor_similarity_percentile"].to_numpy()
        + weights["reliability"] * frame["pair_reliability_score"].to_numpy()
        + weights["quality"] * frame["image_quality_proxy_min"].to_numpy()
        + weights["margin"] * frame["margin_confidence_norm"].to_numpy()
        - weights["conflict_penalty"] * frame["descriptor_evidence_conflict_score"].to_numpy()
        - weights["disagreement_penalty"] * frame["descriptor_disagreement_score"].to_numpy()
    )


def policy_grid() -> list[dict[str, float]]:
    return [
        {"policy_family": "descriptor_only", "descriptor": 1.00, "reliability": 0.00, "quality": 0.00, "margin": 0.00, "conflict_penalty": 0.00, "disagreement_penalty": 0.00},
        {"policy_family": "current_pf_eri_like", "descriptor": 0.60, "reliability": 0.25, "quality": 0.10, "margin": 0.05, "conflict_penalty": 0.00, "disagreement_penalty": 0.00},
        {"policy_family": "quality_only_augmented", "descriptor": 0.70, "reliability": 0.00, "quality": 0.30, "margin": 0.00, "conflict_penalty": 0.00, "disagreement_penalty": 0.00},
        {"policy_family": "reliability_light", "descriptor": 0.75, "reliability": 0.15, "quality": 0.05, "margin": 0.05, "conflict_penalty": 0.00, "disagreement_penalty": 0.00},
        {"policy_family": "reliability_heavy", "descriptor": 0.55, "reliability": 0.35, "quality": 0.05, "margin": 0.05, "conflict_penalty": 0.00, "disagreement_penalty": 0.00},
        {"policy_family": "conflict_penalty_light", "descriptor": 0.75, "reliability": 0.15, "quality": 0.05, "margin": 0.05, "conflict_penalty": 0.10, "disagreement_penalty": 0.00},
        {"policy_family": "conflict_penalty_heavy", "descriptor": 0.75, "reliability": 0.15, "quality": 0.05, "margin": 0.05, "conflict_penalty": 0.25, "disagreement_penalty": 0.00},
        {"policy_family": "disagreement_penalty", "descriptor": 0.75, "reliability": 0.15, "quality": 0.05, "margin": 0.05, "conflict_penalty": 0.10, "disagreement_penalty": 0.10},
    ]


def evaluate_policy(frame: pd.DataFrame, weights: dict[str, float], method_id: str) -> dict[str, Any]:
    top1 = top1_by_score(frame, candidate_score(frame, weights), method_id)
    return method_metrics(top1)


def build_calibrated_policy_revision(table: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows_selected: list[dict[str, Any]] = []
    rows_eval: list[dict[str, Any]] = []
    grid = policy_grid()
    raw = top1_by_rank(table, "candidate_rank_raw", "raw_descriptor")
    pf = top1_by_rank(table, "candidate_rank_pf_eri", "pf_eri_candidate_utility")

    for (split_id, descriptor), split_frame in table.groupby(["split_id", "descriptor"]):
        calibration = split_frame[split_frame["calibration_or_evaluation"].eq("calibration")]
        evaluation = split_frame[split_frame["calibration_or_evaluation"].eq("evaluation")]
        scored_rows: list[dict[str, Any]] = []
        for i, weights in enumerate(grid):
            metrics = evaluate_policy(calibration, weights, f"calibrated_grid_{i}")
            scored_rows.append({"policy_index": i, **weights, **metrics})
        scored = pd.DataFrame(scored_rows)
        scored = scored.sort_values(
            ["true_top1_rate_eligible", "hard_negative_top1_rate", "false_top1_rate_eligible", "false_top1_rate_all"],
            ascending=[False, True, True, True],
        ).reset_index(drop=True)
        selected = scored.iloc[0].to_dict()
        weights = {key: float(selected[key]) for key in ["descriptor", "reliability", "quality", "margin", "conflict_penalty", "disagreement_penalty"]}
        rows_selected.append(
            {
                "split_id": int(split_id),
                "descriptor_name": descriptor,
                "selected_policy_index": int(selected["policy_index"]),
                **weights,
                "calibration_true_top1_rate_eligible": float(selected["true_top1_rate_eligible"]),
                "calibration_false_top1_rate_eligible": float(selected["false_top1_rate_eligible"]),
                "calibration_hard_negative_top1_rate": float(selected["hard_negative_top1_rate"]),
            }
        )

        for method_id, top1 in [
            ("raw_descriptor", raw),
            ("current_pf_eri_candidate_utility", pf),
        ]:
            part = top1[
                top1["split_id"].eq(split_id)
                & top1["descriptor"].eq(descriptor)
                & top1["calibration_or_evaluation"].eq("evaluation")
            ]
            rows_eval.append(
                {
                    "split_id": int(split_id),
                    "descriptor": descriptor,
                    "method_id": method_id,
                    **method_metrics(part),
                }
            )
        calibrated_metrics = evaluate_policy(evaluation, weights, "calibrated_policy")
        rows_eval.append(
            {
                "split_id": int(split_id),
                "descriptor": descriptor,
                "method_id": "calibrated_policy",
                **calibrated_metrics,
            }
        )
    return pd.DataFrame(rows_selected), pd.DataFrame(rows_eval)


def summarize_policy_eval(eval_frame: pd.DataFrame) -> pd.DataFrame:
    baseline = eval_frame[eval_frame["method_id"].eq("raw_descriptor")]
    rows: list[dict[str, Any]] = []
    for method_id in ["current_pf_eri_candidate_utility", "calibrated_policy"]:
        current = eval_frame[eval_frame["method_id"].eq(method_id)]
        merged = baseline.merge(current, on=["split_id", "descriptor"], suffixes=("_raw", "_method"), validate="one_to_one")
        for descriptor, frame in merged.groupby("descriptor"):
            for metric_col, direction in [
                ("true_top1_rate_eligible", "gain"),
                ("false_top1_rate_eligible", "reduction"),
                ("hard_negative_top1_rate", "reduction"),
            ]:
                if direction == "gain":
                    values = frame[f"{metric_col}_method"].to_numpy() - frame[f"{metric_col}_raw"].to_numpy()
                else:
                    values = frame[f"{metric_col}_raw"].to_numpy() - frame[f"{metric_col}_method"].to_numpy()
                stats = paired_bootstrap(values)
                rows.append(
                    {
                        "descriptor": descriptor,
                        "method_id": method_id,
                        "metric": f"{metric_col}_{direction}_vs_raw",
                        **stats,
                    }
                )
    return pd.DataFrame(rows)


def write_summary(
    query_difficulty: pd.DataFrame,
    score_separation: pd.DataFrame,
    failure_modes: pd.DataFrame,
    selected_policies: pd.DataFrame,
    policy_eval: pd.DataFrame,
    policy_eval_summary: pd.DataFrame,
    table: pd.DataFrame,
) -> None:
    eval_query = query_difficulty[query_difficulty["calibration_or_evaluation"].eq("evaluation")]
    eval_sep = score_separation[score_separation["calibration_or_evaluation"].eq("evaluation")]
    eval_fail = failure_modes[failure_modes["calibration_or_evaluation"].eq("evaluation")]
    eval_policy = policy_eval[policy_eval["method_id"].isin(["raw_descriptor", "current_pf_eri_candidate_utility", "calibrated_policy"])]

    lines = [
        "# Phase 12D Failure Diagnosis and Policy Revision",
        "",
        "Date: 2026-06-17",
        "",
        "## Why Current Results Are Modest",
        "",
        "### 1. The descriptor retrieval ceiling is the first bottleneck.",
        "",
    ]
    query_mean = eval_query.groupby("descriptor")[
        ["gallery_positive_available_rate", "any_positive_in_top20_rate", "raw_true_top1_rate", "oracle_top20_true_rate_ceiling", "descriptor_ceiling_gap_raw_to_oracle"]
    ].mean()
    for descriptor, row in query_mean.iterrows():
        lines.append(
            "- "
            f"{descriptor}: gallery-positive available={row['gallery_positive_available_rate']:.3f}, "
            f"positive-in-top20 ceiling={row['oracle_top20_true_rate_ceiling']:.3f}, "
            f"raw top1 true={row['raw_true_top1_rate']:.3f}, "
            f"raw-to-oracle gap={row['descriptor_ceiling_gap_raw_to_oracle']:.3f}"
        )

    lines += [
        "",
        "PF-ERI can rerank or filter the candidate pool, but it cannot recover positives that the descriptor failed to place in top-20.",
        "",
        "### 2. Pair reliability is weak as a same-identity discriminator.",
        "",
    ]
    sep_mean = eval_sep.groupby(["descriptor", "score"])[["auc_for_same_identity", "mean_same_identity", "mean_false_candidate"]].mean().reset_index()
    focus_scores = ["descriptor_similarity_percentile", "pair_reliability_score", "candidate_utility_rq_score", "descriptor_evidence_conflict_score"]
    for _, row in sep_mean[sep_mean["score"].isin(focus_scores)].sort_values(["descriptor", "score"]).iterrows():
        lines.append(
            "- "
            f"{row['descriptor']} / {row['score']}: "
            f"AUC(same)={row['auc_for_same_identity']:.3f}, "
            f"mean_same={row['mean_same_identity']:.3f}, "
            f"mean_false={row['mean_false_candidate']:.3f}"
        )

    lines += [
        "",
        "This explains why reliability bands alone do not strongly reduce pooled false-candidate rate: reliable images can still be reliable but wrong candidates.",
        "",
        "### 3. Fixed hand-written utility weights are not guaranteed optimal.",
        "",
    ]
    eval_policy_mean = eval_policy.groupby(["descriptor", "method_id"])[
        ["true_top1_rate_eligible", "false_top1_rate_eligible", "hard_negative_top1_rate"]
    ].mean().reset_index()
    for _, row in eval_policy_mean.sort_values(["descriptor", "method_id"]).iterrows():
        lines.append(
            "- "
            f"{row['descriptor']} / {row['method_id']}: "
            f"eligible true top1={row['true_top1_rate_eligible']:.3f}, "
            f"eligible false top1={row['false_top1_rate_eligible']:.3f}, "
            f"hard-negative top1={row['hard_negative_top1_rate']:.3f}"
        )

    lines += [
        "",
        "## Calibrated Policy Test",
        "",
        "Policies were selected on calibration queries within each split and descriptor, then evaluated on evaluation queries. This is a stronger test than choosing weights on all data.",
        "",
    ]
    for _, row in policy_eval_summary.sort_values(["descriptor", "method_id", "metric"]).iterrows():
        lines.append(
            "- "
            f"{row['descriptor']} / {row['method_id']} / {row['metric']}: "
            f"mean={row['observed_mean']:.4f}, "
            f"95% CI={row['ci_low']:.4f} to {row['ci_high']:.4f}, "
            f"P(>0)={row['p_gt_0']:.3f}"
        )

    selected_mean = selected_policies.groupby("descriptor_name")[
        ["descriptor", "reliability", "quality", "margin", "conflict_penalty", "disagreement_penalty"]
    ].mean()
    lines += ["", "Mean selected calibrated weights:", ""]
    for descriptor, row in selected_mean.iterrows():
        lines.append(
            "- "
            f"{descriptor}: descriptor={row['descriptor']:.3f}, reliability={row['reliability']:.3f}, "
            f"quality={row['quality']:.3f}, margin={row['margin']:.3f}, "
            f"conflict_penalty={row['conflict_penalty']:.3f}, disagreement_penalty={row['disagreement_penalty']:.3f}"
        )

    lines += [
        "",
        "## What We Need To Modify",
        "",
        "1. Revise RQ1 endpoint from pooled candidate false-rate to query-level review burden, positive retention, and eligible-query top-1 risk.",
        "2. Keep PF-ERI as a candidate utility/risk-control layer, not as a standalone identity classifier.",
        "3. Replace fixed global utility weights with calibration-selected weights or a constrained monotonic model.",
        "4. Separate eligible queries from singleton/no-gallery-positive queries in all top-1 claims.",
        "5. For RQ4, train positives only from identities with at least two images; use singleton identities as distractors/hard negatives.",
        "",
        "## Next Build Step",
        "",
        "Phase 12E should produce publication-ready figures and update the paper draft using the revised endpoints.",
        "",
        "## Outputs",
        "",
        f"- `{QUERY_DIFFICULTY.relative_to(PROJECT_ROOT)}`",
        f"- `{SCORE_SEPARATION.relative_to(PROJECT_ROOT)}`",
        f"- `{FAILURE_MODES.relative_to(PROJECT_ROOT)}`",
        f"- `{CALIBRATED_POLICIES.relative_to(PROJECT_ROOT)}`",
        f"- `{CALIBRATED_EVAL.relative_to(PROJECT_ROOT)}`",
    ]
    SUMMARY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build(args: argparse.Namespace) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    table = load_table(args.table)
    query_difficulty = build_query_difficulty(table)
    score_separation = build_score_separation(table)
    failure_modes = build_failure_modes(table)
    selected_policies, policy_eval = build_calibrated_policy_revision(table)
    policy_eval_summary = summarize_policy_eval(policy_eval)

    query_difficulty.to_csv(QUERY_DIFFICULTY, index=False)
    score_separation.to_csv(SCORE_SEPARATION, index=False)
    failure_modes.to_csv(FAILURE_MODES, index=False)
    selected_policies.to_csv(CALIBRATED_POLICIES, index=False)
    policy_eval.to_csv(CALIBRATED_EVAL, index=False)
    policy_eval_summary.to_csv(OUT_DIR / "phase12d_calibrated_policy_paired_confidence.csv", index=False)
    write_summary(query_difficulty, score_separation, failure_modes, selected_policies, policy_eval, policy_eval_summary, table)

    audit = {
        "input_table": str(args.table.relative_to(PROJECT_ROOT)),
        "input_rows": int(len(table)),
        "input_query_images": int(table["query_image_id"].nunique()),
        "policy_grid_size": int(len(policy_grid())),
        "output_rows": {
            "query_difficulty": int(len(query_difficulty)),
            "score_separation": int(len(score_separation)),
            "failure_modes": int(len(failure_modes)),
            "selected_policies": int(len(selected_policies)),
            "policy_eval": int(len(policy_eval)),
            "policy_eval_summary": int(len(policy_eval_summary)),
        },
    }
    BUILD_AUDIT.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(f"Wrote Phase 12D diagnosis and policy revision to {OUT_DIR.relative_to(PROJECT_ROOT)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--table", type=Path, default=TABLE)
    return parser.parse_args()


if __name__ == "__main__":
    build(parse_args())
