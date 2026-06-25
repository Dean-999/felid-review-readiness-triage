#!/usr/bin/env python3
"""Build Phase 12C confidence evidence with paired intervals and controls."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE12_DIR = PROJECT_ROOT / "outputs/czechlynx/phase12"
TABLE = PHASE12_DIR / "phase12_pair_candidate_analysis_table.csv"
OUT_DIR = PHASE12_DIR / "rq_confidence_evidence"

TOP1_SPLIT = OUT_DIR / "phase12c_top1_split_metrics.csv"
TOP1_PAIRED = OUT_DIR / "phase12c_top1_paired_confidence.csv"
TOPK_BURDEN = OUT_DIR / "phase12c_topk_false_burden_positive_retention.csv"
RELIABILITY_THRESHOLD = OUT_DIR / "phase12c_reliability_threshold_curve.csv"
CONFLICT_ENRICHMENT = OUT_DIR / "phase12c_conflict_enrichment.csv"
RANDOM_CONTROL = OUT_DIR / "phase12c_random_top20_control.csv"
SUMMARY_MD = OUT_DIR / "phase12c_confidence_evidence_summary.md"
BUILD_AUDIT = OUT_DIR / "phase12c_confidence_evidence_build_audit.json"

USECOLS = [
    "split_id",
    "calibration_or_evaluation",
    "descriptor",
    "query_image_id",
    "candidate_image_id",
    "same_identity",
    "candidate_rank_raw",
    "candidate_rank_pf_eri",
    "descriptor_similarity_percentile",
    "pair_reliability_score",
    "image_quality_proxy_min",
    "candidate_utility_rq_score",
    "descriptor_evidence_conflict_score",
    "hard_negative_candidate",
]

RANDOM_SEED = 20260617
BOOTSTRAP_ITERATIONS = 5000
RANDOM_CONTROL_ITERATIONS = 200


def yes_no_to_bool(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin({"yes", "true", "1"})


def safe_mean(values: pd.Series | np.ndarray | list[float]) -> float:
    series = pd.Series(values, dtype="float64").dropna()
    return float(series.mean()) if len(series) else math.nan


def ci_from_values(values: np.ndarray) -> dict[str, float]:
    values = values[np.isfinite(values)]
    if len(values) == 0:
        return {"mean": math.nan, "ci_low": math.nan, "ci_high": math.nan, "p_direction_gt_0": math.nan}
    return {
        "mean": float(np.mean(values)),
        "ci_low": float(np.quantile(values, 0.025)),
        "ci_high": float(np.quantile(values, 0.975)),
        "p_direction_gt_0": float(np.mean(values > 0)),
    }


def paired_bootstrap(values: np.ndarray, rng: np.random.Generator, iterations: int) -> dict[str, float]:
    values = values[np.isfinite(values)]
    if len(values) == 0:
        return ci_from_values(values)
    draws = np.empty(iterations, dtype=np.float64)
    for i in range(iterations):
        sample = rng.choice(values, size=len(values), replace=True)
        draws[i] = float(np.mean(sample))
    result = ci_from_values(draws)
    result["split_pair_count"] = int(len(values))
    result["observed_mean"] = float(np.mean(values))
    return result


def load_table(path: Path) -> pd.DataFrame:
    table = pd.read_csv(path, usecols=USECOLS)
    table["same_identity"] = yes_no_to_bool(table["same_identity"])
    table["hard_negative_candidate"] = yes_no_to_bool(table["hard_negative_candidate"])
    numeric = [
        "split_id",
        "candidate_rank_raw",
        "candidate_rank_pf_eri",
        "descriptor_similarity_percentile",
        "pair_reliability_score",
        "image_quality_proxy_min",
        "candidate_utility_rq_score",
        "descriptor_evidence_conflict_score",
    ]
    for column in numeric:
        table[column] = pd.to_numeric(table[column], errors="coerce")
    group_cols = ["split_id", "calibration_or_evaluation", "descriptor", "query_image_id"]
    table["quality_only_score"] = 0.70 * table["descriptor_similarity_percentile"] + 0.30 * table["image_quality_proxy_min"]
    table["pair_reliability_score_for_rank"] = 0.70 * table["descriptor_similarity_percentile"] + 0.30 * table["pair_reliability_score"]
    table["quality_only_rank"] = table.groupby(group_cols)["quality_only_score"].rank(method="first", ascending=False)
    table["pair_reliability_rank"] = table.groupby(group_cols)["pair_reliability_score_for_rank"].rank(method="first", ascending=False)
    return table


def method_top1(table: pd.DataFrame, method_id: str) -> pd.DataFrame:
    if method_id == "raw_descriptor":
        selected = table[table["candidate_rank_raw"].eq(1)].copy()
        selected["confidence_score"] = selected["descriptor_similarity_percentile"]
    elif method_id == "pf_eri_candidate_utility":
        selected = table[table["candidate_rank_pf_eri"].eq(1)].copy()
        selected["confidence_score"] = selected["candidate_utility_rq_score"]
    elif method_id == "quality_only":
        selected = table[table["quality_only_rank"].eq(1)].copy()
        selected["confidence_score"] = selected["quality_only_score"]
    elif method_id == "pair_reliability":
        selected = table[table["pair_reliability_rank"].eq(1)].copy()
        selected["confidence_score"] = selected["pair_reliability_score_for_rank"]
    else:
        raise ValueError(f"unknown method_id: {method_id}")
    selected["method_id"] = method_id
    return selected


def build_top1_split_metrics(table: pd.DataFrame) -> pd.DataFrame:
    methods = ["raw_descriptor", "pf_eri_candidate_utility", "quality_only", "pair_reliability"]
    rows: list[dict[str, Any]] = []
    for method_id in methods:
        top1 = method_top1(table, method_id)
        for keys, frame in top1.groupby(["split_id", "calibration_or_evaluation", "descriptor"]):
            split_id, role, descriptor = keys
            query_count = int(frame["query_image_id"].nunique())
            false_count = int((~frame["same_identity"]).sum())
            true_count = int(frame["same_identity"].sum())
            rows.append(
                {
                    "split_id": int(split_id),
                    "calibration_or_evaluation": role,
                    "descriptor": descriptor,
                    "method_id": method_id,
                    "query_count": query_count,
                    "false_top1_count": false_count,
                    "true_top1_count": true_count,
                    "false_top1_rate": false_count / query_count if query_count else math.nan,
                    "true_top1_rate": true_count / query_count if query_count else math.nan,
                    "mean_confidence_score": safe_mean(frame["confidence_score"]),
                    "mean_pair_reliability_score": safe_mean(frame["pair_reliability_score"]),
                    "mean_hard_negative_rate": float(frame["hard_negative_candidate"].mean()) if len(frame) else math.nan,
                }
            )
    return pd.DataFrame(rows)


def build_top1_paired_confidence(split_metrics: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(RANDOM_SEED)
    rows: list[dict[str, Any]] = []
    baseline = split_metrics[split_metrics["method_id"].eq("raw_descriptor")]
    for method_id in ["pf_eri_candidate_utility", "quality_only", "pair_reliability"]:
        current = split_metrics[split_metrics["method_id"].eq(method_id)]
        merged = baseline.merge(
            current,
            on=["split_id", "calibration_or_evaluation", "descriptor"],
            suffixes=("_raw", "_method"),
            validate="one_to_one",
        )
        for keys, frame in merged.groupby(["calibration_or_evaluation", "descriptor"]):
            role, descriptor = keys
            risk_reduction = frame["false_top1_rate_raw"].to_numpy() - frame["false_top1_rate_method"].to_numpy()
            true_gain = frame["true_top1_rate_method"].to_numpy() - frame["true_top1_rate_raw"].to_numpy()
            hard_negative_reduction = frame["mean_hard_negative_rate_raw"].to_numpy() - frame["mean_hard_negative_rate_method"].to_numpy()
            for metric_name, values in [
                ("false_top1_risk_reduction_vs_raw", risk_reduction),
                ("true_top1_rate_gain_vs_raw", true_gain),
                ("hard_negative_top1_rate_reduction_vs_raw", hard_negative_reduction),
            ]:
                stats = paired_bootstrap(values, rng, BOOTSTRAP_ITERATIONS)
                rows.append(
                    {
                        "calibration_or_evaluation": role,
                        "descriptor": descriptor,
                        "method_id": method_id,
                        "metric": metric_name,
                        **stats,
                    }
                )
    return pd.DataFrame(rows)


def build_topk_burden(table: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    specs = {
        "raw_descriptor_top5": "candidate_rank_raw",
        "pf_eri_candidate_utility_top5": "candidate_rank_pf_eri",
        "quality_only_top5": "quality_only_rank",
        "pair_reliability_top5": "pair_reliability_rank",
    }
    for method_id, rank_col in specs.items():
        kept = table[table[rank_col] <= 5].copy()
        for keys, frame in kept.groupby(["split_id", "calibration_or_evaluation", "descriptor"]):
            split_id, role, descriptor = keys
            per_query = frame.groupby("query_image_id").agg(
                false_candidates_top5=("same_identity", lambda s: int((~s).sum())),
                true_candidates_top5=("same_identity", lambda s: int(s.sum())),
                hard_negatives_top5=("hard_negative_candidate", "sum"),
            )
            rows.append(
                {
                    "split_id": int(split_id),
                    "calibration_or_evaluation": role,
                    "descriptor": descriptor,
                    "method_id": method_id,
                    "query_count": int(len(per_query)),
                    "mean_false_candidates_per_query_top5": safe_mean(per_query["false_candidates_top5"]),
                    "mean_true_candidates_per_query_top5": safe_mean(per_query["true_candidates_top5"]),
                    "positive_present_top5_rate": float((per_query["true_candidates_top5"] > 0).mean()) if len(per_query) else math.nan,
                    "mean_hard_negatives_per_query_top5": safe_mean(per_query["hard_negatives_top5"]),
                }
            )
    return pd.DataFrame(rows)


def build_reliability_threshold_curve(table: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    thresholds = np.round(np.linspace(0.0, 1.0, 21), 2)
    grouped = table.groupby(["split_id", "calibration_or_evaluation", "descriptor"])
    for keys, frame in grouped:
        split_id, role, descriptor = keys
        total_queries = int(frame["query_image_id"].nunique())
        total_same = int(frame["same_identity"].sum())
        total_false = int((~frame["same_identity"]).sum())
        for threshold in thresholds:
            kept = frame[frame["pair_reliability_score"] >= threshold]
            rows.append(
                {
                    "split_id": int(split_id),
                    "calibration_or_evaluation": role,
                    "descriptor": descriptor,
                    "pair_reliability_threshold": float(threshold),
                    "retained_candidate_count": int(len(kept)),
                    "query_coverage": kept["query_image_id"].nunique() / total_queries if total_queries else math.nan,
                    "positive_retention": int(kept["same_identity"].sum()) / total_same if total_same else math.nan,
                    "false_candidate_retention": int((~kept["same_identity"]).sum()) / total_false if total_false else math.nan,
                    "false_candidate_rate_retained": float((~kept["same_identity"]).mean()) if len(kept) else math.nan,
                    "hard_negative_retention": int(kept["hard_negative_candidate"].sum()) / int(frame["hard_negative_candidate"].sum()) if int(frame["hard_negative_candidate"].sum()) else math.nan,
                }
            )
    return pd.DataFrame(rows)


def build_conflict_enrichment(table: pd.DataFrame) -> pd.DataFrame:
    frame = table.copy()
    frame["conflict_flag"] = (frame["descriptor_similarity_percentile"] >= 0.90) & (frame["pair_reliability_score"] <= 0.40)
    frame["high_similarity_flag"] = frame["descriptor_similarity_percentile"] >= 0.90
    rows: list[dict[str, Any]] = []
    for keys, part in frame.groupby(["split_id", "calibration_or_evaluation", "descriptor"]):
        split_id, role, descriptor = keys
        for population_name, population in [
            ("all_candidates", part),
            ("high_similarity_candidates", part[part["high_similarity_flag"]]),
            ("false_candidates", part[~part["same_identity"]]),
            ("same_identity_candidates", part[part["same_identity"]]),
            ("hard_negative_candidates", part[part["hard_negative_candidate"]]),
        ]:
            rows.append(
                {
                    "split_id": int(split_id),
                    "calibration_or_evaluation": role,
                    "descriptor": descriptor,
                    "population": population_name,
                    "candidate_count": int(len(population)),
                    "conflict_count": int(population["conflict_flag"].sum()) if len(population) else 0,
                    "conflict_rate": float(population["conflict_flag"].mean()) if len(population) else math.nan,
                    "mean_conflict_score": safe_mean(population["descriptor_evidence_conflict_score"]) if len(population) else math.nan,
                    "mean_pair_reliability_score": safe_mean(population["pair_reliability_score"]) if len(population) else math.nan,
                }
            )
    return pd.DataFrame(rows)


def build_random_top20_control(table: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(RANDOM_SEED)
    group_cols = ["split_id", "calibration_or_evaluation", "descriptor", "query_image_id"]
    rows: list[dict[str, Any]] = []
    ordered = table.sort_values(group_cols + ["candidate_rank_raw"]).copy()
    ordered["candidate_position"] = ordered.groupby(group_cols).cumcount()
    group_meta = ordered.drop_duplicates(group_cols)[group_cols].reset_index(drop=True)
    n_groups = len(group_meta)
    max_candidates = int(ordered["candidate_position"].max()) + 1
    if max_candidates != 20:
        raise ValueError(f"random control expects 20 candidates per query group, found {max_candidates}")

    same = ordered["same_identity"].to_numpy(dtype=bool).reshape(n_groups, max_candidates)
    reliability = ordered["pair_reliability_score"].to_numpy(dtype=np.float64).reshape(n_groups, max_candidates)
    index_frame = group_meta[["split_id", "calibration_or_evaluation", "descriptor"]].copy()

    for iteration in range(RANDOM_CONTROL_ITERATIONS):
        picks = rng.integers(0, max_candidates, size=n_groups)
        selected = index_frame.copy()
        selected["same_identity"] = same[np.arange(n_groups), picks]
        selected["pair_reliability_score"] = reliability[np.arange(n_groups), picks]
        for keys, frame in selected.groupby(["split_id", "calibration_or_evaluation", "descriptor"]):
            split_id, role, descriptor = keys
            rows.append(
                {
                    "iteration": iteration,
                    "split_id": int(split_id),
                    "calibration_or_evaluation": role,
                    "descriptor": descriptor,
                    "method_id": "random_top20_candidate",
                    "query_count": int(len(frame)),
                    "false_top1_rate": float((~frame["same_identity"]).mean()),
                    "true_top1_rate": float(frame["same_identity"].mean()),
                    "mean_pair_reliability_score": safe_mean(frame["pair_reliability_score"]),
                }
            )
    return pd.DataFrame(rows)


def write_summary(
    top1_paired: pd.DataFrame,
    topk_burden: pd.DataFrame,
    threshold_curve: pd.DataFrame,
    conflict: pd.DataFrame,
    random_control: pd.DataFrame,
    table: pd.DataFrame,
) -> None:
    eval_paired = top1_paired[top1_paired["calibration_or_evaluation"].eq("evaluation")]
    eval_topk = topk_burden[topk_burden["calibration_or_evaluation"].eq("evaluation")]
    eval_threshold = threshold_curve[threshold_curve["calibration_or_evaluation"].eq("evaluation")]
    eval_conflict = conflict[conflict["calibration_or_evaluation"].eq("evaluation")]
    eval_random = random_control[random_control["calibration_or_evaluation"].eq("evaluation")]

    lines = [
        "# Phase 12C Confidence Evidence Summary",
        "",
        "Date: 2026-06-17",
        "",
        "Purpose: provide split-paired uncertainty estimates and controls for the 1000-image Phase 12A table.",
        "",
        "## Input",
        "",
        f"- Candidate rows: `{len(table)}`",
        f"- Query images: `{table['query_image_id'].nunique()}`",
        f"- Descriptors: `{', '.join(sorted(table['descriptor'].astype(str).unique()))}`",
        f"- Bootstrap iterations: `{BOOTSTRAP_ITERATIONS}`",
        f"- Random control iterations: `{RANDOM_CONTROL_ITERATIONS}`",
        "",
        "## Top-1 Paired Confidence",
        "",
    ]
    key_rows = eval_paired[
        eval_paired["metric"].isin(
            [
                "false_top1_risk_reduction_vs_raw",
                "true_top1_rate_gain_vs_raw",
                "hard_negative_top1_rate_reduction_vs_raw",
            ]
        )
    ].sort_values(["descriptor", "method_id", "metric"])
    for _, row in key_rows.iterrows():
        lines.append(
            "- "
            f"{row['descriptor']} / {row['method_id']} / {row['metric']}: "
            f"mean={row['observed_mean']:.4f}, "
            f"95% CI={row['ci_low']:.4f} to {row['ci_high']:.4f}, "
            f"P(>0)={row['p_direction_gt_0']:.3f}, "
            f"split-pairs={int(row['split_pair_count'])}"
        )

    lines += [
        "",
        "## Top-5 False Burden",
        "",
    ]
    topk_mean = (
        eval_topk.groupby(["descriptor", "method_id"])[
            ["mean_false_candidates_per_query_top5", "positive_present_top5_rate", "mean_hard_negatives_per_query_top5"]
        ]
        .mean()
        .reset_index()
        .sort_values(["descriptor", "method_id"])
    )
    for _, row in topk_mean.iterrows():
        lines.append(
            "- "
            f"{row['descriptor']} / {row['method_id']}: "
            f"false@5/query={row['mean_false_candidates_per_query_top5']:.3f}, "
            f"positive-present@5={row['positive_present_top5_rate']:.3f}, "
            f"hard-neg@5/query={row['mean_hard_negatives_per_query_top5']:.3f}"
        )

    lines += [
        "",
        "## Reliability Thresholds",
        "",
    ]
    threshold_focus = eval_threshold[eval_threshold["pair_reliability_threshold"].isin([0.25, 0.50, 0.75])]
    threshold_mean = (
        threshold_focus.groupby(["descriptor", "pair_reliability_threshold"])[
            ["query_coverage", "positive_retention", "false_candidate_retention", "hard_negative_retention"]
        ]
        .mean()
        .reset_index()
        .sort_values(["descriptor", "pair_reliability_threshold"])
    )
    for _, row in threshold_mean.iterrows():
        lines.append(
            "- "
            f"{row['descriptor']} / R>={row['pair_reliability_threshold']:.2f}: "
            f"query-coverage={row['query_coverage']:.3f}, "
            f"positive-retention={row['positive_retention']:.3f}, "
            f"false-retention={row['false_candidate_retention']:.3f}, "
            f"hard-negative-retention={row['hard_negative_retention']:.3f}"
        )

    lines += [
        "",
        "## Conflict Enrichment",
        "",
    ]
    conflict_mean = (
        eval_conflict.groupby(["descriptor", "population"])[["conflict_rate", "mean_conflict_score"]]
        .mean()
        .reset_index()
        .sort_values(["descriptor", "population"])
    )
    for _, row in conflict_mean.iterrows():
        lines.append(
            "- "
            f"{row['descriptor']} / {row['population']}: "
            f"conflict-rate={row['conflict_rate']:.3f}, "
            f"mean-conflict-score={row['mean_conflict_score']:.3f}"
        )

    random_mean = (
        eval_random.groupby("descriptor")[["false_top1_rate", "true_top1_rate", "mean_pair_reliability_score"]]
        .mean()
        .reset_index()
    )
    lines += ["", "## Random Top-20 Control", ""]
    for _, row in random_mean.iterrows():
        lines.append(
            "- "
            f"{row['descriptor']}: random false-rate={row['false_top1_rate']:.3f}, "
            f"random true-rate={row['true_top1_rate']:.3f}, "
            f"random mean R={row['mean_pair_reliability_score']:.3f}"
        )

    lines += [
        "",
        "## Interpretation Rules",
        "",
        "- Treat split-paired CIs crossing zero as weak or unstable evidence.",
        "- Treat high P(>0) with small absolute gains as stable but modest engineering evidence.",
        "- Use top-5 burden and reliability-threshold retention to support RQ1/RQ2 more than pooled candidate false rates.",
        "- Keep RQ4 positive-pair learning restricted to identities with at least two images; singleton identities remain useful as distractors and hard negatives.",
        "",
        "## Outputs",
        "",
        f"- `{TOP1_SPLIT.relative_to(PROJECT_ROOT)}`",
        f"- `{TOP1_PAIRED.relative_to(PROJECT_ROOT)}`",
        f"- `{TOPK_BURDEN.relative_to(PROJECT_ROOT)}`",
        f"- `{RELIABILITY_THRESHOLD.relative_to(PROJECT_ROOT)}`",
        f"- `{CONFLICT_ENRICHMENT.relative_to(PROJECT_ROOT)}`",
        f"- `{RANDOM_CONTROL.relative_to(PROJECT_ROOT)}`",
    ]
    SUMMARY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build(args: argparse.Namespace) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    table = load_table(args.table)
    top1_split = build_top1_split_metrics(table)
    top1_paired = build_top1_paired_confidence(top1_split)
    topk_burden = build_topk_burden(table)
    reliability_curve = build_reliability_threshold_curve(table)
    conflict = build_conflict_enrichment(table)
    random_control = build_random_top20_control(table)

    top1_split.to_csv(TOP1_SPLIT, index=False)
    top1_paired.to_csv(TOP1_PAIRED, index=False)
    topk_burden.to_csv(TOPK_BURDEN, index=False)
    reliability_curve.to_csv(RELIABILITY_THRESHOLD, index=False)
    conflict.to_csv(CONFLICT_ENRICHMENT, index=False)
    random_control.to_csv(RANDOM_CONTROL, index=False)
    write_summary(top1_paired, topk_burden, reliability_curve, conflict, random_control, table)

    audit = {
        "input_table": str(args.table.relative_to(PROJECT_ROOT)),
        "input_rows": int(len(table)),
        "input_query_images": int(table["query_image_id"].nunique()),
        "bootstrap_iterations": BOOTSTRAP_ITERATIONS,
        "random_control_iterations": RANDOM_CONTROL_ITERATIONS,
        "output_rows": {
            "top1_split": int(len(top1_split)),
            "top1_paired": int(len(top1_paired)),
            "topk_burden": int(len(topk_burden)),
            "reliability_threshold": int(len(reliability_curve)),
            "conflict_enrichment": int(len(conflict)),
            "random_control": int(len(random_control)),
        },
    }
    BUILD_AUDIT.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(f"Wrote Phase 12C confidence evidence to {OUT_DIR.relative_to(PROJECT_ROOT)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--table", type=Path, default=TABLE)
    return parser.parse_args()


if __name__ == "__main__":
    build(parse_args())
