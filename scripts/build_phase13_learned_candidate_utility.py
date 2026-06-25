#!/usr/bin/env python3
"""Build Phase 13 learned candidate-utility models for PF-ERI.

This phase upgrades fixed hand-written PF-ERI candidate utility into held-out
learned evidence-utility models. The evaluation unit is the query-level
candidate ranking, not only pooled candidate classification.
"""

from __future__ import annotations

import argparse
import json
import math
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE12_DIR = PROJECT_ROOT / "outputs/czechlynx/phase12"
TABLE = PHASE12_DIR / "phase12_pair_candidate_analysis_table.csv"
OUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase13/learned_candidate_utility"

TRAINING_TABLE = OUT_DIR / "phase13_candidate_utility_training_table.csv"
MODEL_RESULTS = OUT_DIR / "phase13_calibrated_utility_model_results.csv"
RISK_COVERAGE = OUT_DIR / "phase13_risk_coverage_comparison.csv"
ABLATION_SUMMARY = OUT_DIR / "phase13_model_ablation_summary.csv"
HOLDOUT_CONFIDENCE = OUT_DIR / "phase13_holdout_confidence_summary.csv"
TOP1_SELECTIONS = OUT_DIR / "phase13_top1_selection_records.csv"
SUMMARY_MD = OUT_DIR / "phase13_learned_candidate_utility_summary.md"
BUILD_AUDIT = OUT_DIR / "phase13_learned_candidate_utility_build_audit.json"

RANDOM_SEED = 20260617
BOOTSTRAP_ITERATIONS = 5000

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
    "descriptor_similarity",
    "descriptor_similarity_percentile",
    "other_descriptor_similarity",
    "reciprocal_rank_support",
    "margin_confidence",
    "margin_confidence_norm",
    "descriptor_disagreement_score",
    "side_comparability_score",
    "pattern_pair_score",
    "blur_pair_score",
    "occlusion_pair_score",
    "body_visibility_pair_score",
    "viewpoint_compatibility_score",
    "pair_reliability_score",
    "image_quality_proxy_min",
    "image_quality_proxy_mean",
    "image_utility_proxy_min",
    "image_utility_proxy_mean",
    "visual_identity_evidence_min",
    "visual_identity_evidence_mean",
    "descriptor_evidence_conflict_score",
    "descriptor_evidence_conflict_margin_score",
    "descriptor_evidence_conflict_disagreement_score",
    "candidate_utility_rq_score",
    "hard_negative_candidate",
]

BASE_FEATURES = [
    "descriptor_similarity_percentile",
    "descriptor_similarity",
    "other_descriptor_similarity",
    "reciprocal_rank_support",
    "margin_confidence_norm",
    "descriptor_disagreement_score",
]

QUALITY_FEATURES = BASE_FEATURES + [
    "image_quality_proxy_min",
    "image_quality_proxy_mean",
    "image_utility_proxy_min",
    "image_utility_proxy_mean",
    "visual_identity_evidence_min",
    "visual_identity_evidence_mean",
]

PF_ERI_FEATURES = QUALITY_FEATURES + [
    "side_comparability_score",
    "pattern_pair_score",
    "blur_pair_score",
    "occlusion_pair_score",
    "body_visibility_pair_score",
    "viewpoint_compatibility_score",
    "pair_reliability_score",
    "descriptor_evidence_conflict_score",
    "descriptor_evidence_conflict_margin_score",
    "descriptor_evidence_conflict_disagreement_score",
    "candidate_utility_rq_score",
]

INTERACTION_FEATURES = PF_ERI_FEATURES + [
    "descriptor_x_pair_reliability",
    "descriptor_x_visual_evidence",
    "descriptor_x_quality_min",
    "descriptor_x_conflict",
    "margin_x_pair_reliability",
    "reliability_minus_conflict",
]

PUBLIC_TRAINING_COLUMNS = [
    "split_id",
    "calibration_or_evaluation",
    "descriptor",
    "query_image_id",
    "candidate_image_id",
    "same_identity",
    "hard_negative_candidate",
    "gallery_positive_available",
    "query_identity_image_count",
    "candidate_rank_raw",
    "candidate_rank_pf_eri",
] + INTERACTION_FEATURES + [
    "fixed_quality_only_score",
    "fixed_conflict_penalty_score",
]


def yes_no_to_bool(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin({"yes", "true", "1"})


def bool_to_yes_no(series: pd.Series) -> pd.Series:
    return np.where(series.astype(bool), "yes", "no")


def safe_mean(values: pd.Series | np.ndarray | list[float]) -> float:
    series = pd.Series(values, dtype="float64").replace([np.inf, -np.inf], np.nan).dropna()
    return float(series.mean()) if len(series) else math.nan


def metric_or_nan(func, y_true: np.ndarray, score: np.ndarray) -> float:
    try:
        if len(np.unique(y_true)) < 2:
            return math.nan
        return float(func(y_true, score))
    except ValueError:
        return math.nan


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
    table["same_identity"] = yes_no_to_bool(table["same_identity"])
    table["hard_negative_candidate"] = yes_no_to_bool(table["hard_negative_candidate"])

    numeric = [column for column in USECOLS if column not in {
        "calibration_or_evaluation",
        "descriptor",
        "query_image_id",
        "candidate_image_id",
        "query_identity_token",
        "candidate_identity_token",
        "same_identity",
        "hard_negative_candidate",
    }]
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

    table["descriptor_x_pair_reliability"] = table["descriptor_similarity_percentile"] * table["pair_reliability_score"]
    table["descriptor_x_visual_evidence"] = table["descriptor_similarity_percentile"] * table["visual_identity_evidence_min"]
    table["descriptor_x_quality_min"] = table["descriptor_similarity_percentile"] * table["image_quality_proxy_min"]
    table["descriptor_x_conflict"] = table["descriptor_similarity_percentile"] * table["descriptor_evidence_conflict_score"]
    table["margin_x_pair_reliability"] = table["margin_confidence_norm"] * table["pair_reliability_score"]
    table["reliability_minus_conflict"] = table["pair_reliability_score"] - table["descriptor_evidence_conflict_score"]
    table["fixed_quality_only_score"] = (
        0.70 * table["descriptor_similarity_percentile"] + 0.30 * table["image_quality_proxy_min"]
    )
    table["fixed_conflict_penalty_score"] = (
        0.65 * table["descriptor_similarity_percentile"]
        + 0.20 * table["pair_reliability_score"]
        + 0.10 * table["image_quality_proxy_min"]
        + 0.05 * table["margin_confidence_norm"]
        - 0.15 * table["descriptor_evidence_conflict_score"]
        - 0.10 * table["descriptor_disagreement_score"]
    )

    return table


def write_training_table(table: pd.DataFrame) -> None:
    public = table[PUBLIC_TRAINING_COLUMNS].copy()
    public["same_identity"] = bool_to_yes_no(public["same_identity"])
    public["hard_negative_candidate"] = bool_to_yes_no(public["hard_negative_candidate"])
    public["gallery_positive_available"] = bool_to_yes_no(public["gallery_positive_available"])
    public.to_csv(TRAINING_TABLE, index=False)


def make_logistic(feature_cols: list[str]) -> Pipeline:
    return Pipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            (
                "model",
                LogisticRegression(
                    solver="liblinear",
                    max_iter=2000,
                    C=0.5,
                    class_weight="balanced",
                    random_state=RANDOM_SEED,
                ),
            ),
        ]
    )


def monotonic_constraints(feature_cols: list[str]) -> list[int]:
    positive = {
        "descriptor_similarity_percentile",
        "descriptor_similarity",
        "other_descriptor_similarity",
        "reciprocal_rank_support",
        "margin_confidence_norm",
        "image_quality_proxy_min",
        "image_quality_proxy_mean",
        "image_utility_proxy_min",
        "image_utility_proxy_mean",
        "visual_identity_evidence_min",
        "visual_identity_evidence_mean",
        "side_comparability_score",
        "pattern_pair_score",
        "blur_pair_score",
        "occlusion_pair_score",
        "body_visibility_pair_score",
        "viewpoint_compatibility_score",
        "pair_reliability_score",
        "candidate_utility_rq_score",
        "descriptor_x_pair_reliability",
        "descriptor_x_visual_evidence",
        "descriptor_x_quality_min",
        "margin_x_pair_reliability",
        "reliability_minus_conflict",
    }
    negative = {
        "descriptor_disagreement_score",
        "descriptor_evidence_conflict_score",
        "descriptor_evidence_conflict_margin_score",
        "descriptor_evidence_conflict_disagreement_score",
        "descriptor_x_conflict",
    }
    constraints: list[int] = []
    for column in feature_cols:
        if column in positive:
            constraints.append(1)
        elif column in negative:
            constraints.append(-1)
        else:
            constraints.append(0)
    return constraints


def fit_hgb(train: pd.DataFrame, feature_cols: list[str]) -> Pipeline:
    return Pipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            (
                "model",
                HistGradientBoostingClassifier(
                    learning_rate=0.05,
                    max_iter=160,
                    max_leaf_nodes=15,
                    min_samples_leaf=40,
                    l2_regularization=0.05,
                    class_weight="balanced",
                    monotonic_cst=monotonic_constraints(feature_cols),
                    random_state=RANDOM_SEED,
                ),
            ),
        ]
    ).fit(train[feature_cols], train["same_identity"].astype(int))


def model_specs() -> list[dict[str, Any]]:
    return [
        {"method_id": "learned_descriptor_logistic", "family": "learned", "feature_cols": BASE_FEATURES, "model_type": "logistic"},
        {"method_id": "learned_quality_control_logistic", "family": "learned", "feature_cols": QUALITY_FEATURES, "model_type": "logistic"},
        {"method_id": "learned_pf_eri_full_logistic", "family": "learned", "feature_cols": PF_ERI_FEATURES, "model_type": "logistic"},
        {"method_id": "learned_pf_eri_interaction_logistic", "family": "learned", "feature_cols": INTERACTION_FEATURES, "model_type": "logistic"},
        {"method_id": "learned_pf_eri_monotonic_hgb", "family": "learned", "feature_cols": INTERACTION_FEATURES, "model_type": "monotonic_hgb"},
    ]


def fixed_score(frame: pd.DataFrame, method_id: str) -> np.ndarray:
    if method_id == "raw_descriptor":
        return frame["descriptor_similarity_percentile"].to_numpy(dtype=np.float64)
    if method_id == "fixed_pf_eri_candidate_utility":
        return frame["candidate_utility_rq_score"].to_numpy(dtype=np.float64)
    if method_id == "fixed_quality_only":
        return frame["fixed_quality_only_score"].to_numpy(dtype=np.float64)
    if method_id == "fixed_conflict_penalty":
        return frame["fixed_conflict_penalty_score"].to_numpy(dtype=np.float64)
    raise ValueError(f"unknown fixed method: {method_id}")


def topk_by_score(frame: pd.DataFrame, score: np.ndarray, method_id: str, top_k: int = 5) -> tuple[pd.DataFrame, pd.DataFrame]:
    scored = frame.copy()
    scored["_score"] = score
    scored["_rank"] = scored.groupby("query_image_id")["_score"].rank(method="first", ascending=False)
    selected = scored[scored["_rank"].le(top_k)].copy()
    top1 = selected[selected["_rank"].eq(1)].copy()
    selected["method_id"] = method_id
    top1["method_id"] = method_id
    return top1, selected


def evaluate_ranked(top1: pd.DataFrame, top5: pd.DataFrame, candidate_frame: pd.DataFrame, score: np.ndarray) -> dict[str, Any]:
    query_count = int(top1["query_image_id"].nunique())
    eligible = top1[top1["gallery_positive_available"]]
    top5_query = top5.groupby("query_image_id").agg(
        false_candidates_top5=("same_identity", lambda s: int((~s).sum())),
        true_candidates_top5=("same_identity", lambda s: int(s.sum())),
        hard_negatives_top5=("hard_negative_candidate", "sum"),
    )
    y_true = candidate_frame["same_identity"].astype(int).to_numpy()
    return {
        "query_count": query_count,
        "eligible_query_count": int(eligible["query_image_id"].nunique()),
        "candidate_count": int(len(candidate_frame)),
        "positive_candidate_count": int(candidate_frame["same_identity"].sum()),
        "candidate_roc_auc": metric_or_nan(roc_auc_score, y_true, score),
        "candidate_average_precision": metric_or_nan(average_precision_score, y_true, score),
        "true_top1_rate_all": float(top1["same_identity"].mean()) if len(top1) else math.nan,
        "false_top1_rate_all": float((~top1["same_identity"]).mean()) if len(top1) else math.nan,
        "true_top1_rate_eligible": float(eligible["same_identity"].mean()) if len(eligible) else math.nan,
        "false_top1_rate_eligible": float((~eligible["same_identity"]).mean()) if len(eligible) else math.nan,
        "hard_negative_top1_rate": float(top1["hard_negative_candidate"].mean()) if len(top1) else math.nan,
        "positive_present_top5_rate": float((top5_query["true_candidates_top5"] > 0).mean()) if len(top5_query) else math.nan,
        "mean_true_candidates_per_query_top5": safe_mean(top5_query["true_candidates_top5"]),
        "mean_false_candidates_per_query_top5": safe_mean(top5_query["false_candidates_top5"]),
        "mean_hard_negatives_per_query_top5": safe_mean(top5_query["hard_negatives_top5"]),
        "mean_top1_score": safe_mean(top1["_score"]),
        "mean_top1_pair_reliability": safe_mean(top1["pair_reliability_score"]),
        "mean_top1_conflict": safe_mean(top1["descriptor_evidence_conflict_score"]),
    }


def risk_coverage_curve(top1: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    coverage_grid = [0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 1.00]
    ordered = top1.sort_values("_score", ascending=False).reset_index(drop=True)
    n = len(ordered)
    for coverage in coverage_grid:
        keep_n = max(1, int(math.ceil(n * coverage))) if n else 0
        kept = ordered.iloc[:keep_n]
        eligible = kept[kept["gallery_positive_available"]]
        rows.append(
            {
                "coverage": coverage,
                "covered_query_count": int(len(kept)),
                "eligible_covered_query_count": int(len(eligible)),
                "false_top1_rate_all": float((~kept["same_identity"]).mean()) if len(kept) else math.nan,
                "true_top1_rate_all": float(kept["same_identity"].mean()) if len(kept) else math.nan,
                "false_top1_rate_eligible": float((~eligible["same_identity"]).mean()) if len(eligible) else math.nan,
                "true_top1_rate_eligible": float(eligible["same_identity"].mean()) if len(eligible) else math.nan,
                "hard_negative_top1_rate": float(kept["hard_negative_candidate"].mean()) if len(kept) else math.nan,
                "score_threshold_min": float(kept["_score"].min()) if len(kept) else math.nan,
            }
        )
    return pd.DataFrame(rows)


def score_learned_model(train: pd.DataFrame, evaluation: pd.DataFrame, spec: dict[str, Any]) -> np.ndarray:
    feature_cols = spec["feature_cols"]
    y_train = train["same_identity"].astype(int)
    if y_train.nunique() < 2:
        return np.full(len(evaluation), np.nan)
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=ConvergenceWarning)
        warnings.filterwarnings("ignore", category=RuntimeWarning)
        if spec["model_type"] == "logistic":
            model = make_logistic(feature_cols).fit(train[feature_cols], y_train)
        elif spec["model_type"] == "monotonic_hgb":
            model = fit_hgb(train, feature_cols)
        else:
            raise ValueError(f"unknown model type: {spec['model_type']}")
    return model.predict_proba(evaluation[feature_cols])[:, 1]


def evaluate_all(table: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    result_rows: list[dict[str, Any]] = []
    risk_rows: list[pd.DataFrame] = []
    top1_rows: list[pd.DataFrame] = []
    fixed_methods = [
        "raw_descriptor",
        "fixed_pf_eri_candidate_utility",
        "fixed_quality_only",
        "fixed_conflict_penalty",
    ]
    learned_specs = model_specs()

    for (split_id, descriptor), split_frame in table.groupby(["split_id", "descriptor"], sort=True):
        calibration = split_frame[split_frame["calibration_or_evaluation"].eq("calibration")].copy()
        evaluation = split_frame[split_frame["calibration_or_evaluation"].eq("evaluation")].copy()
        if calibration.empty or evaluation.empty:
            continue

        method_scores: list[tuple[str, str, np.ndarray, str, int]] = []
        for method_id in fixed_methods:
            method_scores.append((method_id, "fixed", fixed_score(evaluation, method_id), "fixed_formula", 0))
        for spec in learned_specs:
            score = score_learned_model(calibration, evaluation, spec)
            method_scores.append((spec["method_id"], spec["family"], score, spec["model_type"], len(spec["feature_cols"])))

        for method_id, family, score, model_type, feature_count in method_scores:
            if np.isnan(score).all():
                continue
            top1, top5 = topk_by_score(evaluation, score, method_id, top_k=5)
            metrics = evaluate_ranked(top1, top5, evaluation, score)
            result_rows.append(
                {
                    "split_id": int(split_id),
                    "descriptor": descriptor,
                    "method_id": method_id,
                    "method_family": family,
                    "model_type": model_type,
                    "feature_count": int(feature_count),
                    **metrics,
                }
            )
            curve = risk_coverage_curve(top1)
            curve.insert(0, "method_id", method_id)
            curve.insert(0, "descriptor", descriptor)
            curve.insert(0, "split_id", int(split_id))
            risk_rows.append(curve)
            keep_cols = [
                "split_id",
                "descriptor",
                "query_image_id",
                "candidate_image_id",
                "same_identity",
                "hard_negative_candidate",
                "gallery_positive_available",
                "_score",
                "pair_reliability_score",
                "descriptor_evidence_conflict_score",
            ]
            top1_out = top1[keep_cols].copy()
            top1_out.insert(2, "method_id", method_id)
            top1_rows.append(top1_out)

    results = pd.DataFrame(result_rows)
    risk = pd.concat(risk_rows, ignore_index=True) if risk_rows else pd.DataFrame()
    top1_records = pd.concat(top1_rows, ignore_index=True) if top1_rows else pd.DataFrame()
    return results, risk, top1_records


def build_ablation_summary(results: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    metrics = [
        ("true_top1_rate_eligible", "gain"),
        ("false_top1_rate_eligible", "reduction"),
        ("hard_negative_top1_rate", "reduction"),
        ("positive_present_top5_rate", "gain"),
        ("mean_false_candidates_per_query_top5", "reduction"),
        ("candidate_average_precision", "gain"),
    ]
    comparisons = [
        ("fixed_pf_eri_candidate_utility", "raw_descriptor"),
        ("fixed_quality_only", "raw_descriptor"),
        ("fixed_conflict_penalty", "raw_descriptor"),
        ("learned_descriptor_logistic", "raw_descriptor"),
        ("learned_quality_control_logistic", "learned_descriptor_logistic"),
        ("learned_pf_eri_full_logistic", "learned_quality_control_logistic"),
        ("learned_pf_eri_interaction_logistic", "learned_pf_eri_full_logistic"),
        ("learned_pf_eri_monotonic_hgb", "learned_pf_eri_interaction_logistic"),
        ("learned_pf_eri_full_logistic", "fixed_pf_eri_candidate_utility"),
        ("learned_pf_eri_interaction_logistic", "fixed_pf_eri_candidate_utility"),
        ("learned_pf_eri_monotonic_hgb", "fixed_pf_eri_candidate_utility"),
    ]
    for method_id, baseline_id in comparisons:
        left = results[results["method_id"].eq(method_id)]
        right = results[results["method_id"].eq(baseline_id)]
        if left.empty or right.empty:
            continue
        merged = right.merge(left, on=["split_id", "descriptor"], suffixes=("_baseline", "_method"), validate="one_to_one")
        for descriptor, frame in merged.groupby("descriptor"):
            for metric, direction in metrics:
                if direction == "gain":
                    values = frame[f"{metric}_method"].to_numpy() - frame[f"{metric}_baseline"].to_numpy()
                else:
                    values = frame[f"{metric}_baseline"].to_numpy() - frame[f"{metric}_method"].to_numpy()
                rows.append(
                    {
                        "descriptor": descriptor,
                        "method_id": method_id,
                        "baseline_method_id": baseline_id,
                        "metric": f"{metric}_{direction}",
                        **paired_bootstrap(values),
                    }
                )
    return pd.DataFrame(rows)


def build_holdout_confidence(results: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    metric_cols = [
        "candidate_roc_auc",
        "candidate_average_precision",
        "true_top1_rate_eligible",
        "false_top1_rate_eligible",
        "hard_negative_top1_rate",
        "positive_present_top5_rate",
        "mean_false_candidates_per_query_top5",
    ]
    for (descriptor, method_id), frame in results.groupby(["descriptor", "method_id"]):
        for metric in metric_cols:
            values = frame[metric].to_numpy(dtype=np.float64)
            values = values[np.isfinite(values)]
            if len(values) == 0:
                observed = math.nan
                ci_low = math.nan
                ci_high = math.nan
            else:
                rng = np.random.default_rng(RANDOM_SEED)
                draws = np.array([np.mean(rng.choice(values, size=len(values), replace=True)) for _ in range(BOOTSTRAP_ITERATIONS)])
                observed = float(np.mean(values))
                ci_low = float(np.quantile(draws, 0.025))
                ci_high = float(np.quantile(draws, 0.975))
            rows.append(
                {
                    "descriptor": descriptor,
                    "method_id": method_id,
                    "metric": metric,
                    "observed_mean": observed,
                    "ci_low": ci_low,
                    "ci_high": ci_high,
                    "split_count": int(len(values)),
                }
            )
    return pd.DataFrame(rows)


def best_increment(ablation: pd.DataFrame, method_id: str, baseline_id: str, metric: str) -> str:
    part = ablation[
        ablation["method_id"].eq(method_id)
        & ablation["baseline_method_id"].eq(baseline_id)
        & ablation["metric"].eq(metric)
    ]
    if part.empty:
        return "not available"
    bits = []
    for _, row in part.sort_values("descriptor").iterrows():
        bits.append(
            f"{row['descriptor']}: mean={row['observed_mean']:.4f}, "
            f"95% CI={row['ci_low']:.4f} to {row['ci_high']:.4f}, P(>0)={row['p_gt_0']:.3f}"
        )
    return "; ".join(bits)


def write_summary(results: pd.DataFrame, ablation: pd.DataFrame, holdout: pd.DataFrame) -> None:
    lines = [
        "# Phase 13 Learned Candidate Utility",
        "",
        "Date: 2026-06-17",
        "",
        "## Purpose",
        "",
        "Phase 13 upgrades fixed PF-ERI candidate utility into held-out learned evidence-utility models. The evaluation target is query-level candidate reranking: eligible-query top-1 risk, top-5 positive retention, false-candidate burden, hard-negative exposure, and risk-coverage behavior.",
        "",
        "## Models",
        "",
        "- raw descriptor ranking: descriptor percentile only.",
        "- fixed PF-ERI candidate utility: Phase 12 hand-written candidate utility.",
        "- fixed quality-only control: descriptor plus image-quality proxy.",
        "- learned descriptor logistic: descriptor-support variables only.",
        "- learned quality-control logistic: descriptor-support plus image/image-utility variables.",
        "- learned PF-ERI full logistic: quality-control plus pair admissibility and conflict variables.",
        "- learned PF-ERI interaction logistic: full PF-ERI plus evidence-conflict interactions.",
        "- learned PF-ERI monotonic HGB: constrained nonlinear model with reliability features increasing utility and conflict/disagreement decreasing utility.",
        "",
        "## Key Held-Out Comparisons",
        "",
        "Learned PF-ERI full vs quality-control, eligible true top-1 gain:",
        "",
        f"- {best_increment(ablation, 'learned_pf_eri_full_logistic', 'learned_quality_control_logistic', 'true_top1_rate_eligible_gain')}",
        "",
        "Learned PF-ERI full vs quality-control, eligible false top-1 reduction:",
        "",
        f"- {best_increment(ablation, 'learned_pf_eri_full_logistic', 'learned_quality_control_logistic', 'false_top1_rate_eligible_reduction')}",
        "",
        "Learned interaction PF-ERI vs fixed PF-ERI candidate utility, eligible false top-1 reduction:",
        "",
        f"- {best_increment(ablation, 'learned_pf_eri_interaction_logistic', 'fixed_pf_eri_candidate_utility', 'false_top1_rate_eligible_reduction')}",
        "",
        "Monotonic nonlinear PF-ERI vs fixed PF-ERI candidate utility, eligible false top-1 reduction:",
        "",
        f"- {best_increment(ablation, 'learned_pf_eri_monotonic_hgb', 'fixed_pf_eri_candidate_utility', 'false_top1_rate_eligible_reduction')}",
        "",
        "## Interpretation Rule",
        "",
        "A strong Phase 13 result requires learned PF-ERI to beat descriptor-only and quality-control learned baselines, not merely raw descriptor ranking. If the gain is weak, the diagnosis should be used to upgrade RQ4 pair-weighted metric learning rather than downgrade the project claim immediately.",
        "",
        "## Outputs",
        "",
        f"- `{TRAINING_TABLE.relative_to(PROJECT_ROOT)}`",
        f"- `{MODEL_RESULTS.relative_to(PROJECT_ROOT)}`",
        f"- `{RISK_COVERAGE.relative_to(PROJECT_ROOT)}`",
        f"- `{ABLATION_SUMMARY.relative_to(PROJECT_ROOT)}`",
        f"- `{HOLDOUT_CONFIDENCE.relative_to(PROJECT_ROOT)}`",
        f"- `{TOP1_SELECTIONS.relative_to(PROJECT_ROOT)}`",
    ]
    SUMMARY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build(args: argparse.Namespace) -> None:
    warnings.filterwarnings("ignore", category=RuntimeWarning, module=r"sklearn\..*")
    warnings.filterwarnings("ignore", message=r"Could not find the number of physical cores.*")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    table = load_table(args.table)
    write_training_table(table)
    results, risk, top1_records = evaluate_all(table)
    ablation = build_ablation_summary(results)
    holdout = build_holdout_confidence(results)

    for frame in [top1_records]:
        if not frame.empty:
            frame["same_identity"] = bool_to_yes_no(frame["same_identity"])
            frame["hard_negative_candidate"] = bool_to_yes_no(frame["hard_negative_candidate"])
            frame["gallery_positive_available"] = bool_to_yes_no(frame["gallery_positive_available"])

    results.to_csv(MODEL_RESULTS, index=False)
    risk.to_csv(RISK_COVERAGE, index=False)
    ablation.to_csv(ABLATION_SUMMARY, index=False)
    holdout.to_csv(HOLDOUT_CONFIDENCE, index=False)
    top1_records.to_csv(TOP1_SELECTIONS, index=False)
    write_summary(results, ablation, holdout)

    audit = {
        "input_table": str(args.table.relative_to(PROJECT_ROOT)),
        "input_rows": int(len(table)),
        "input_query_images": int(table["query_image_id"].nunique()),
        "output_rows": {
            "training_table": int(len(table)),
            "model_results": int(len(results)),
            "risk_coverage": int(len(risk)),
            "ablation_summary": int(len(ablation)),
            "holdout_confidence": int(len(holdout)),
            "top1_records": int(len(top1_records)),
        },
        "learned_model_count": int(len(model_specs())),
        "fixed_method_count": 4,
    }
    BUILD_AUDIT.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(f"Wrote Phase 13 learned candidate utility outputs to {OUT_DIR.relative_to(PROJECT_ROOT)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--table", type=Path, default=TABLE)
    return parser.parse_args()


if __name__ == "__main__":
    build(parse_args())
