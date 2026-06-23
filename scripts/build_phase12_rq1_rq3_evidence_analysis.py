#!/usr/bin/env python3
"""Build Phase 12B evidence analyses for RQ1-RQ3.

This script consumes the Phase 12A pair/candidate table. It does not rebuild
descriptors or change PF-ERI scores.
"""

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
OUT_DIR = PHASE12_DIR / "rq1_rq3_evidence_analysis"

BAND_SUMMARY = OUT_DIR / "phase12b_rq1_admissibility_band_summary.csv"
PREDICTOR_SUMMARY = OUT_DIR / "phase12b_rq1_predictor_diagnostic_summary.csv"
CONFLICT_SUMMARY = OUT_DIR / "phase12b_rq2_conflict_group_summary.csv"
RISK_COVERAGE = OUT_DIR / "phase12b_rq3_risk_coverage_curve.csv"
METHOD_SUMMARY = OUT_DIR / "phase12b_rq3_method_summary.csv"
RESEARCH_SUMMARY = OUT_DIR / "phase12b_research_evidence_summary.md"
BUILD_AUDIT = OUT_DIR / "phase12b_evidence_analysis_build_audit.json"

USECOLS = [
    "split_id",
    "calibration_or_evaluation",
    "descriptor",
    "query_image_id",
    "candidate_image_id",
    "same_identity",
    "candidate_rank_raw",
    "candidate_rank_pf_eri",
    "is_top1_raw",
    "is_top1_pf_eri",
    "false_candidate",
    "false_top1_raw",
    "false_top1_pf_eri",
    "descriptor_similarity",
    "descriptor_similarity_percentile",
    "margin_confidence_norm",
    "descriptor_disagreement_score",
    "pair_reliability_score",
    "image_quality_proxy_min",
    "image_quality_proxy_mean",
    "visual_identity_evidence_min",
    "descriptor_evidence_conflict_score",
    "conflict_band",
    "admissibility_band",
    "candidate_utility_rq_score",
    "hard_negative_candidate",
    "review_decision",
]

BOOLEAN_COLUMNS = [
    "same_identity",
    "is_top1_raw",
    "is_top1_pf_eri",
    "false_candidate",
    "false_top1_raw",
    "false_top1_pf_eri",
    "hard_negative_candidate",
]

METHOD_SPECS = {
    "raw_descriptor_top1": {
        "score": "descriptor_similarity_percentile",
        "rank_column": "candidate_rank_raw",
    },
    "pf_eri_candidate_utility_top1": {
        "score": "candidate_utility_rq_score",
        "rank_column": "candidate_rank_pf_eri",
    },
    "quality_only_rerank_top1": {
        "score": "quality_only_rerank_score",
        "rank_column": "quality_only_rank",
    },
    "pair_reliability_rerank_top1": {
        "score": "pair_reliability_rerank_score",
        "rank_column": "pair_reliability_rank",
    },
}


def yes_no_to_bool(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin({"yes", "true", "1"})


def safe_mean(series: pd.Series) -> float:
    if len(series) == 0:
        return math.nan
    return float(pd.to_numeric(series, errors="coerce").mean())


def auc_from_scores(score: pd.Series, positive: pd.Series) -> float:
    """Rank AUC without sklearn.

    `positive=True` means the risk event being predicted. Ties are handled via
    average ranks, matching the Mann-Whitney interpretation of AUC.
    """

    frame = pd.DataFrame({"score": pd.to_numeric(score, errors="coerce"), "positive": positive.astype(bool)}).dropna()
    n_pos = int(frame["positive"].sum())
    n_neg = int((~frame["positive"]).sum())
    if n_pos == 0 or n_neg == 0:
        return math.nan
    ranks = frame["score"].rank(method="average")
    rank_sum_pos = float(ranks[frame["positive"]].sum())
    return float((rank_sum_pos - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def load_table(path: Path) -> pd.DataFrame:
    table = pd.read_csv(path, usecols=USECOLS)
    for column in BOOLEAN_COLUMNS:
        table[column] = yes_no_to_bool(table[column])
    numeric = [
        "candidate_rank_raw",
        "candidate_rank_pf_eri",
        "descriptor_similarity",
        "descriptor_similarity_percentile",
        "margin_confidence_norm",
        "descriptor_disagreement_score",
        "pair_reliability_score",
        "image_quality_proxy_min",
        "image_quality_proxy_mean",
        "visual_identity_evidence_min",
        "descriptor_evidence_conflict_score",
        "candidate_utility_rq_score",
    ]
    for column in numeric:
        table[column] = pd.to_numeric(table[column], errors="coerce")
    table["quality_only_rerank_score"] = (
        0.70 * table["descriptor_similarity_percentile"] + 0.30 * table["image_quality_proxy_min"]
    )
    table["pair_reliability_rerank_score"] = (
        0.70 * table["descriptor_similarity_percentile"] + 0.30 * table["pair_reliability_score"]
    )
    group_cols = ["split_id", "calibration_or_evaluation", "descriptor", "query_image_id"]
    table["quality_only_rank"] = table.groupby(group_cols)["quality_only_rerank_score"].rank(method="first", ascending=False)
    table["pair_reliability_rank"] = table.groupby(group_cols)["pair_reliability_rerank_score"].rank(method="first", ascending=False)
    return table


def build_rq1_band_summary(table: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    group_cols = ["split_id", "calibration_or_evaluation", "descriptor", "admissibility_band"]
    for keys, frame in table.groupby(group_cols, dropna=False):
        split_id, role, descriptor, band = keys
        same = frame["same_identity"]
        false = frame["false_candidate"]
        rows.append(
            {
                "split_id": int(split_id),
                "calibration_or_evaluation": role,
                "descriptor": descriptor,
                "admissibility_band": band,
                "candidate_count": int(len(frame)),
                "query_count": int(frame["query_image_id"].nunique()),
                "same_identity_candidate_count": int(same.sum()),
                "false_candidate_count": int(false.sum()),
                "false_candidate_rate": float(false.mean()) if len(frame) else math.nan,
                "same_identity_candidate_rate": float(same.mean()) if len(frame) else math.nan,
                "mean_pair_reliability_score": safe_mean(frame["pair_reliability_score"]),
                "mean_image_quality_proxy_min": safe_mean(frame["image_quality_proxy_min"]),
                "mean_candidate_utility_rq_score": safe_mean(frame["candidate_utility_rq_score"]),
                "hard_negative_count": int(frame["hard_negative_candidate"].sum()),
            }
        )
    return pd.DataFrame(rows)


def build_rq1_predictor_summary(table: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    predictors = {
        "pf_eri_pair_reliability_risk": 1.0 - table["pair_reliability_score"],
        "image_quality_min_risk": 1.0 - table["image_quality_proxy_min"],
        "image_quality_mean_risk": 1.0 - table["image_quality_proxy_mean"],
        "descriptor_confidence_risk_inverse": 1.0 - table["descriptor_similarity_percentile"],
        "candidate_utility_risk_inverse": 1.0 - table["candidate_utility_rq_score"],
        "descriptor_evidence_conflict_score": table["descriptor_evidence_conflict_score"],
    }
    for (split_id, role, descriptor), frame in table.groupby(["split_id", "calibration_or_evaluation", "descriptor"]):
        false_event = frame["false_candidate"]
        hard_event = frame["hard_negative_candidate"]
        for name in predictors:
            score = predictors[name].loc[frame.index]
            rows.append(
                {
                    "split_id": int(split_id),
                    "calibration_or_evaluation": role,
                    "descriptor": descriptor,
                    "predictor": name,
                    "auc_for_false_candidate_risk": auc_from_scores(score, false_event),
                    "auc_for_hard_negative_risk": auc_from_scores(score, hard_event),
                    "mean_score_same_identity": safe_mean(score[frame["same_identity"]]),
                    "mean_score_false_candidate": safe_mean(score[frame["false_candidate"]]),
                }
            )
    return pd.DataFrame(rows)


def conflict_group(row: pd.Series) -> str:
    high_sim = row["descriptor_similarity_percentile"] >= 0.90
    low_adm = row["pair_reliability_score"] <= 0.40
    high_adm = row["pair_reliability_score"] >= 0.70
    if high_sim and low_adm:
        return "high_similarity_low_admissibility_conflict"
    if high_sim and high_adm:
        return "high_similarity_high_admissibility"
    if high_sim:
        return "high_similarity_intermediate_admissibility"
    return "not_high_similarity"


def build_rq2_conflict_summary(table: pd.DataFrame) -> pd.DataFrame:
    frame = table.copy()
    frame["conflict_group"] = frame.apply(conflict_group, axis=1)
    rows: list[dict[str, Any]] = []
    group_cols = ["split_id", "calibration_or_evaluation", "descriptor", "conflict_group"]
    for keys, part in frame.groupby(group_cols, dropna=False):
        split_id, role, descriptor, group = keys
        top1_raw = part["is_top1_raw"]
        top1_pf = part["is_top1_pf_eri"]
        rows.append(
            {
                "split_id": int(split_id),
                "calibration_or_evaluation": role,
                "descriptor": descriptor,
                "conflict_group": group,
                "candidate_count": int(len(part)),
                "query_count": int(part["query_image_id"].nunique()),
                "false_candidate_count": int(part["false_candidate"].sum()),
                "false_candidate_rate": float(part["false_candidate"].mean()) if len(part) else math.nan,
                "same_identity_candidate_count": int(part["same_identity"].sum()),
                "hard_negative_count": int(part["hard_negative_candidate"].sum()),
                "hard_negative_rate": float(part["hard_negative_candidate"].mean()) if len(part) else math.nan,
                "raw_top1_count": int(top1_raw.sum()),
                "raw_false_top1_count": int((top1_raw & part["false_candidate"]).sum()),
                "raw_false_top1_rate_within_group": float((top1_raw & part["false_candidate"]).sum() / top1_raw.sum()) if top1_raw.sum() else math.nan,
                "pf_eri_top1_count": int(top1_pf.sum()),
                "pf_eri_false_top1_count": int((top1_pf & part["false_candidate"]).sum()),
                "pf_eri_false_top1_rate_within_group": float((top1_pf & part["false_candidate"]).sum() / top1_pf.sum()) if top1_pf.sum() else math.nan,
                "mean_descriptor_similarity_percentile": safe_mean(part["descriptor_similarity_percentile"]),
                "mean_pair_reliability_score": safe_mean(part["pair_reliability_score"]),
                "mean_conflict_score": safe_mean(part["descriptor_evidence_conflict_score"]),
            }
        )
    return pd.DataFrame(rows)


def top1_frame_for_method(table: pd.DataFrame, method_id: str) -> pd.DataFrame:
    spec = METHOD_SPECS[method_id]
    selected = table[table[spec["rank_column"]].eq(1)].copy()
    selected["method_id"] = method_id
    selected["method_confidence_score"] = selected[spec["score"]]
    return selected


def build_rq3_risk_coverage(table: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    top1_parts = [top1_frame_for_method(table, method_id) for method_id in METHOD_SPECS]
    top1 = pd.concat(top1_parts, ignore_index=True)
    thresholds = np.round(np.linspace(0.0, 1.0, 21), 2)
    rows: list[dict[str, Any]] = []
    for keys, frame in top1.groupby(["split_id", "calibration_or_evaluation", "descriptor", "method_id"]):
        split_id, role, descriptor, method_id = keys
        total_queries = int(frame["query_image_id"].nunique())
        for threshold in thresholds:
            kept = frame[frame["method_confidence_score"] >= threshold]
            kept_queries = int(kept["query_image_id"].nunique())
            false_top1 = int(kept["false_candidate"].sum())
            true_top1 = int(kept["same_identity"].sum())
            rows.append(
                {
                    "split_id": int(split_id),
                    "calibration_or_evaluation": role,
                    "descriptor": descriptor,
                    "method_id": method_id,
                    "threshold": float(threshold),
                    "total_queries": total_queries,
                    "covered_queries": kept_queries,
                    "coverage": kept_queries / total_queries if total_queries else math.nan,
                    "false_top1_count": false_top1,
                    "true_top1_count": true_top1,
                    "false_top1_rate_among_covered": false_top1 / kept_queries if kept_queries else math.nan,
                    "true_top1_rate_among_covered": true_top1 / kept_queries if kept_queries else math.nan,
                }
            )
    curve = pd.DataFrame(rows)
    summary_rows: list[dict[str, Any]] = []
    for keys, frame in curve.groupby(["calibration_or_evaluation", "descriptor", "method_id"]):
        role, descriptor, method_id = keys
        full = frame[frame["threshold"].eq(0.0)]
        high_cov = frame[frame["coverage"] >= 0.80]
        low_risk = frame[frame["false_top1_rate_among_covered"] <= 0.20]
        summary_rows.append(
            {
                "calibration_or_evaluation": role,
                "descriptor": descriptor,
                "method_id": method_id,
                "mean_full_coverage_false_top1_rate": safe_mean(full["false_top1_rate_among_covered"]),
                "mean_full_coverage_true_top1_rate": safe_mean(full["true_top1_rate_among_covered"]),
                "best_mean_false_top1_rate_at_coverage_ge_0_80": safe_mean(
                    high_cov.groupby(["split_id"])["false_top1_rate_among_covered"].min()
                )
                if len(high_cov)
                else math.nan,
                "best_mean_coverage_at_false_top1_rate_le_0_20": safe_mean(
                    low_risk.groupby(["split_id"])["coverage"].max()
                )
                if len(low_risk)
                else math.nan,
            }
        )
    return curve, pd.DataFrame(summary_rows)


def compact_mean(frame: pd.DataFrame, filter_col: str, filter_value: str, metric: str) -> float:
    part = frame[frame[filter_col].eq(filter_value)]
    if part.empty:
        return math.nan
    return float(part[metric].mean())


def write_research_summary(
    band_summary: pd.DataFrame,
    predictor_summary: pd.DataFrame,
    conflict_summary: pd.DataFrame,
    method_summary: pd.DataFrame,
    table: pd.DataFrame,
) -> None:
    eval_bands = band_summary[band_summary["calibration_or_evaluation"].eq("evaluation")]
    eval_predictors = predictor_summary[predictor_summary["calibration_or_evaluation"].eq("evaluation")]
    eval_conflicts = conflict_summary[conflict_summary["calibration_or_evaluation"].eq("evaluation")]
    eval_methods = method_summary[method_summary["calibration_or_evaluation"].eq("evaluation")]

    high_false = compact_mean(eval_bands, "admissibility_band", "high", "false_candidate_rate")
    unusable_false = compact_mean(eval_bands, "admissibility_band", "unusable", "false_candidate_rate")
    conflict_false = compact_mean(
        eval_conflicts,
        "conflict_group",
        "high_similarity_low_admissibility_conflict",
        "false_candidate_rate",
    )
    high_high_false = compact_mean(
        eval_conflicts,
        "conflict_group",
        "high_similarity_high_admissibility",
        "false_candidate_rate",
    )

    predictor_auc = (
        eval_predictors.groupby("predictor")["auc_for_false_candidate_risk"].mean().sort_values(ascending=False)
    )
    method_lines = []
    for _, row in eval_methods.sort_values(["descriptor", "method_id"]).iterrows():
        method_lines.append(
            "- "
            f"{row['descriptor']} / {row['method_id']}: "
            f"full-risk={row['mean_full_coverage_false_top1_rate']:.3f}, "
            f"best-risk@coverage>=0.80={row['best_mean_false_top1_rate_at_coverage_ge_0_80']:.3f}, "
            f"best-coverage@risk<=0.20={row['best_mean_coverage_at_false_top1_rate_le_0_20']:.3f}"
        )

    lines = [
        "# Phase 12B RQ1-RQ3 Evidence Summary",
        "",
        "Date: 2026-06-17",
        "",
        "Input table:",
        "",
        f"- rows: `{len(table)}`",
        f"- query images: `{table['query_image_id'].nunique()}`",
        f"- descriptors: `{', '.join(sorted(table['descriptor'].astype(str).unique()))}`",
        "",
        "## RQ1 Evidence Admissibility",
        "",
        f"Evaluation high-admissibility mean false-candidate rate: `{high_false:.3f}`.",
        f"Evaluation unusable-admissibility mean false-candidate rate: `{unusable_false:.3f}`.",
        "",
        "Mean AUC for false-candidate risk by predictor on evaluation splits:",
        "",
    ]
    for name, value in predictor_auc.items():
        lines.append(f"- `{name}`: `{value:.3f}`")
    lines += [
        "",
        "Interpretation: AUC values above 0.5 indicate the score ranks false candidates above same-identity candidates as riskier. This is diagnostic evidence, not a calibrated probability claim.",
        "",
        "## RQ2 Descriptor-Evidence Conflict",
        "",
        f"Evaluation high-similarity/low-admissibility conflict false-candidate rate: `{conflict_false:.3f}`.",
        f"Evaluation high-similarity/high-admissibility false-candidate rate: `{high_high_false:.3f}`.",
        "",
        "Interpretation: the conflict group is useful if it concentrates false candidates or hard negatives beyond high-similarity/high-admissibility candidates.",
        "",
        "## RQ3 Risk-Coverage Tradeoff",
        "",
        *method_lines,
        "",
        "Interpretation: compare methods at matched coverage or matched risk; do not treat full-coverage top-1 accuracy alone as the main endpoint.",
        "",
        "## Output Tables",
        "",
        f"- `{BAND_SUMMARY.relative_to(PROJECT_ROOT)}`",
        f"- `{PREDICTOR_SUMMARY.relative_to(PROJECT_ROOT)}`",
        f"- `{CONFLICT_SUMMARY.relative_to(PROJECT_ROOT)}`",
        f"- `{RISK_COVERAGE.relative_to(PROJECT_ROOT)}`",
        f"- `{METHOD_SUMMARY.relative_to(PROJECT_ROOT)}`",
    ]
    RESEARCH_SUMMARY.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build(args: argparse.Namespace) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    table = load_table(args.table)
    band_summary = build_rq1_band_summary(table)
    predictor_summary = build_rq1_predictor_summary(table)
    conflict_summary = build_rq2_conflict_summary(table)
    risk_coverage, method_summary = build_rq3_risk_coverage(table)

    band_summary.to_csv(BAND_SUMMARY, index=False)
    predictor_summary.to_csv(PREDICTOR_SUMMARY, index=False)
    conflict_summary.to_csv(CONFLICT_SUMMARY, index=False)
    risk_coverage.to_csv(RISK_COVERAGE, index=False)
    method_summary.to_csv(METHOD_SUMMARY, index=False)
    write_research_summary(band_summary, predictor_summary, conflict_summary, method_summary, table)

    audit = {
        "input_table": str(args.table.relative_to(PROJECT_ROOT)),
        "input_rows": int(len(table)),
        "input_query_images": int(table["query_image_id"].nunique()),
        "descriptor_values": sorted(table["descriptor"].astype(str).unique()),
        "band_summary_rows": int(len(band_summary)),
        "predictor_summary_rows": int(len(predictor_summary)),
        "conflict_summary_rows": int(len(conflict_summary)),
        "risk_coverage_rows": int(len(risk_coverage)),
        "method_summary_rows": int(len(method_summary)),
        "outputs": [
            str(BAND_SUMMARY.relative_to(PROJECT_ROOT)),
            str(PREDICTOR_SUMMARY.relative_to(PROJECT_ROOT)),
            str(CONFLICT_SUMMARY.relative_to(PROJECT_ROOT)),
            str(RISK_COVERAGE.relative_to(PROJECT_ROOT)),
            str(METHOD_SUMMARY.relative_to(PROJECT_ROOT)),
            str(RESEARCH_SUMMARY.relative_to(PROJECT_ROOT)),
        ],
    }
    BUILD_AUDIT.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(f"Wrote Phase 12B evidence analysis to {OUT_DIR.relative_to(PROJECT_ROOT)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--table", type=Path, default=TABLE)
    return parser.parse_args()


if __name__ == "__main__":
    build(parse_args())
