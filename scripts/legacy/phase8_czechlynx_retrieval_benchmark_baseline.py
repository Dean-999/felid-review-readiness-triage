#!/usr/bin/env python3
"""Run Phase 8 CzechLynx retrieval-style Re-ID benchmark baseline."""

from __future__ import annotations

import argparse
import hashlib
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PAIR_TABLE_CSV = PROJECT_ROOT / "outputs/czechlynx/phase7a/pair_tables/phase7a_1000_image_pair_table_v1.csv"
PF_ERI_PAIR_CSV = PROJECT_ROOT / "outputs/czechlynx/phase7a/descriptor_supported_pf_eri/phase7a_descriptor_supported_pair_scores.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase8/reid_tool_benchmark"
FIGURE_DIR = OUTPUT_DIR / "figures"

METRICS_CSV = OUTPUT_DIR / "phase8_czechlynx_retrieval_metrics_summary.csv"
CMC_CSV = OUTPUT_DIR / "phase8_czechlynx_retrieval_cmc_table.csv"
TOPK_CSV = OUTPUT_DIR / "phase8_czechlynx_retrieval_topk_table.csv"
MAP_CSV = OUTPUT_DIR / "phase8_czechlynx_retrieval_map_summary.csv"
PF_ERI_COMPARISON_CSV = OUTPUT_DIR / "phase8_czechlynx_pf_eri_filtered_retrieval_comparison.csv"
FAILURE_CASES_CSV = OUTPUT_DIR / "phase8_czechlynx_retrieval_failure_case_examples.csv"
FEASIBILITY_CSV = OUTPUT_DIR / "phase8_czechlynx_retrieval_feasibility_report.csv"

DESCRIPTORS = {
    "megadescriptor": "megadescriptor_similarity",
    "resnet50": "resnet50_similarity",
}
FILTERS = {
    "all_modeling_eligible": None,
    "pf_eri_low_or_higher": "visual_gate_low_or_higher",
    "pf_eri_medium_or_higher": "visual_gate_medium_or_higher",
    "pf_eri_high_only": "visual_gate_high",
}
TOP_K = [1, 3, 5, 10]


def clean_string(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.lower()


def token(value: object) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:12]


def load_pair_data(pair_table_csv: Path, pf_eri_pair_csv: Path) -> pd.DataFrame:
    pair_cols = [
        "pair_id",
        "image_id_a",
        "image_id_b",
        "same_identity",
        "pair_label_available",
        "resnet50_similarity",
        "megadescriptor_similarity",
        "descriptor_available",
        "pair_modeling_eligible",
        "pair_pattern_min",
        "pair_blur_worst",
        "pair_occlusion_worst",
        "pair_side_compatible",
        "pair_has_side_unknown",
        "pair_has_frontal_or_rear",
        "pair_has_partial_body",
        "pair_has_night_ir_artifact",
        "pair_primary_limiting_factor_combined",
    ]
    pairs = pd.read_csv(pair_table_csv, usecols=pair_cols)
    pf_cols = [
        "pair_id",
        "visual_pf_eri_weighted",
        "visual_pf_eri_min_rule",
        "visual_band",
        "visual_gate_high",
        "visual_gate_medium_or_higher",
        "visual_gate_low_or_higher",
        "any_high_descriptor_low_visual_flag",
    ]
    pf = pd.read_csv(pf_eri_pair_csv, usecols=pf_cols)
    df = pairs.merge(pf, on="pair_id", how="inner", validate="one_to_one")
    for col in [
        "same_identity",
        "pair_label_available",
        "descriptor_available",
        "pair_modeling_eligible",
        "pair_pattern_min",
        "pair_blur_worst",
        "pair_occlusion_worst",
        "pair_side_compatible",
        "pair_has_side_unknown",
        "pair_has_frontal_or_rear",
        "pair_has_partial_body",
        "pair_has_night_ir_artifact",
        "pair_primary_limiting_factor_combined",
        "visual_band",
        "visual_gate_high",
        "visual_gate_medium_or_higher",
        "visual_gate_low_or_higher",
        "any_high_descriptor_low_visual_flag",
    ]:
        df[col] = clean_string(df[col])
    for col in ["resnet50_similarity", "megadescriptor_similarity", "visual_pf_eri_weighted"]:
        df[col] = pd.to_numeric(df[col], errors="raise")
    df = df[
        (df["pair_modeling_eligible"] == "yes")
        & (df["pair_label_available"] == "yes")
        & (df["descriptor_available"] == "yes")
        & df["same_identity"].isin(["yes", "no"])
    ].copy()
    df["is_positive"] = df["same_identity"] == "yes"
    df["pattern_none"] = df["pair_pattern_min"] == "none"
    df["severe_blur"] = df["pair_blur_worst"] == "severe"
    df["major_occlusion"] = df["pair_occlusion_worst"] == "major"
    df["side_incompatible"] = df["pair_side_compatible"] == "no"
    df["side_unknown"] = (df["pair_side_compatible"] == "unknown") | (df["pair_has_side_unknown"] == "yes")
    df["frontal_or_rear"] = df["pair_has_frontal_or_rear"] == "yes"
    df["partial_body"] = df["pair_has_partial_body"] == "yes"
    df["night_ir_artifact"] = df["pair_has_night_ir_artifact"] == "yes"
    df["high_descriptor_low_visual"] = df["any_high_descriptor_low_visual_flag"] == "yes"
    return df


def build_directed_candidates(pairs: pd.DataFrame) -> pd.DataFrame:
    forward = pairs.rename(columns={"image_id_a": "query_internal_id", "image_id_b": "gallery_internal_id"}).copy()
    reverse = pairs.rename(columns={"image_id_b": "query_internal_id", "image_id_a": "gallery_internal_id"}).copy()
    directed = pd.concat([forward, reverse], ignore_index=True)
    directed["query_token"] = directed["query_internal_id"].map(token)
    directed["gallery_token"] = directed["gallery_internal_id"].map(token)
    return directed


def average_precision(relevance: np.ndarray) -> float:
    positives = int(relevance.sum())
    if positives == 0:
        return math.nan
    cumulative = np.cumsum(relevance)
    precision_at_hits = cumulative[relevance == 1] / (np.flatnonzero(relevance == 1) + 1)
    return float(precision_at_hits.mean())


def evaluate_retrieval(directed: pd.DataFrame, descriptor_name: str, score_col: str, filter_name: str, filter_col: str | None) -> dict[str, object]:
    if filter_col is None:
        subset = directed.copy()
    else:
        subset = directed[directed[filter_col] == "yes"].copy()
    all_queries = directed["query_token"].nunique()
    queries_with_positive_in_full_graph = directed.groupby("query_token")["is_positive"].any()
    positive_query_count_full = int(queries_with_positive_in_full_graph.sum())

    query_groups = subset.groupby("query_token", sort=False)
    evaluable_queries = []
    ap_values = []
    reciprocal_ranks = []
    topk_hits = {k: [] for k in TOP_K}
    candidate_counts = []
    positive_counts = []
    false_top1_rows = []

    for query_token, group in query_groups:
        group = group.sort_values(score_col, ascending=False).reset_index(drop=True)
        relevance = group["is_positive"].astype(int).to_numpy()
        candidate_counts.append(len(group))
        positive_counts.append(int(relevance.sum()))
        if relevance.sum() == 0:
            continue
        evaluable_queries.append(query_token)
        ap_values.append(average_precision(relevance))
        first_positive_rank = int(np.flatnonzero(relevance == 1)[0]) + 1
        reciprocal_ranks.append(1.0 / first_positive_rank)
        for k in TOP_K:
            topk_hits[k].append(int(relevance[: min(k, len(relevance))].max()))
        top1 = group.iloc[0]
        if not bool(top1["is_positive"]):
            false_top1_rows.append(top1)

    query_count = subset["query_token"].nunique()
    evaluable_count = len(evaluable_queries)
    metrics: dict[str, object] = {
        "descriptor": descriptor_name,
        "filter_name": filter_name,
        "candidate_pair_count": int(len(subset)),
        "directed_candidate_count": int(len(subset)),
        "query_count_with_candidates": int(query_count),
        "all_query_count": int(all_queries),
        "query_coverage": query_count / all_queries if all_queries else math.nan,
        "positive_query_count_full_graph": positive_query_count_full,
        "positive_query_count_after_filter": int((subset.groupby("query_token")["is_positive"].any()).sum()) if len(subset) else 0,
        "evaluable_positive_query_count": evaluable_count,
        "evaluable_positive_query_coverage": evaluable_count / positive_query_count_full if positive_query_count_full else math.nan,
        "mean_candidates_per_query": float(np.mean(candidate_counts)) if candidate_counts else math.nan,
        "median_candidates_per_query": float(np.median(candidate_counts)) if candidate_counts else math.nan,
        "mean_positive_candidates_per_query": float(np.mean(positive_counts)) if positive_counts else math.nan,
        "mAP": float(np.nanmean(ap_values)) if ap_values else math.nan,
        "mean_reciprocal_rank": float(np.nanmean(reciprocal_ranks)) if reciprocal_ranks else math.nan,
        "false_top1_count": len(false_top1_rows),
        "false_top1_rate_among_evaluable": len(false_top1_rows) / evaluable_count if evaluable_count else math.nan,
        "benchmark_scope": "directed_candidate_pair_graph_not_full_all_vs_all_gallery",
    }
    for k in TOP_K:
        metrics[f"top{k}_accuracy"] = float(np.mean(topk_hits[k])) if topk_hits[k] else math.nan
    return metrics


def cmc_rows(directed: pd.DataFrame, descriptor_name: str, score_col: str, filter_name: str, filter_col: str | None) -> list[dict[str, object]]:
    subset = directed if filter_col is None else directed[directed[filter_col] == "yes"]
    ranks = []
    for _, group in subset.groupby("query_token", sort=False):
        group = group.sort_values(score_col, ascending=False).reset_index(drop=True)
        relevance = group["is_positive"].astype(int).to_numpy()
        if relevance.sum() == 0:
            continue
        ranks.append(int(np.flatnonzero(relevance == 1)[0]) + 1)
    rows = []
    for k in range(1, 13):
        rows.append(
            {
                "descriptor": descriptor_name,
                "filter_name": filter_name,
                "rank_k": k,
                "cmc": float(np.mean([rank <= k for rank in ranks])) if ranks else math.nan,
                "evaluable_positive_query_count": len(ranks),
            }
        )
    return rows


def topk_rows(metrics: list[dict[str, object]]) -> list[dict[str, object]]:
    rows = []
    for metric in metrics:
        for k in TOP_K:
            rows.append(
                {
                    "descriptor": metric["descriptor"],
                    "filter_name": metric["filter_name"],
                    "k": k,
                    "topk_accuracy": metric[f"top{k}_accuracy"],
                    "evaluable_positive_query_count": metric["evaluable_positive_query_count"],
                    "query_coverage": metric["query_coverage"],
                }
            )
    return rows


def failure_case_examples(directed: pd.DataFrame, limit_per_descriptor: int = 40) -> pd.DataFrame:
    rows = []
    for descriptor, score_col in DESCRIPTORS.items():
        for _, group in directed.groupby("query_token", sort=False):
            group = group.sort_values(score_col, ascending=False).reset_index(drop=True)
            if not group["is_positive"].any():
                continue
            top1 = group.iloc[0]
            if bool(top1["is_positive"]):
                continue
            best_positive = group[group["is_positive"]].iloc[0]
            rows.append(
                {
                    "descriptor": descriptor,
                    "query_token": top1["query_token"],
                    "top1_pair_id": top1["pair_id"],
                    "top1_gallery_token": top1["gallery_token"],
                    "top1_similarity": top1[score_col],
                    "best_positive_pair_id": best_positive["pair_id"],
                    "best_positive_gallery_token": best_positive["gallery_token"],
                    "best_positive_similarity": best_positive[score_col],
                    "similarity_gap_top1_minus_positive": top1[score_col] - best_positive[score_col],
                    "top1_visual_band": top1["visual_band"],
                    "top1_visual_pf_eri_weighted": top1["visual_pf_eri_weighted"],
                    "top1_pair_side_compatible": top1["pair_side_compatible"],
                    "top1_pattern_none_flag": "yes" if top1["pattern_none"] else "no",
                    "top1_severe_blur_flag": "yes" if top1["severe_blur"] else "no",
                    "top1_major_occlusion_flag": "yes" if top1["major_occlusion"] else "no",
                    "top1_frontal_or_rear_flag": "yes" if top1["frontal_or_rear"] else "no",
                    "top1_high_descriptor_low_visual_flag": "yes" if top1["high_descriptor_low_visual"] else "no",
                    "interpretation": "false nearest-neighbor in sampled candidate graph; anonymized tokens only",
                }
            )
    return pd.DataFrame(rows).sort_values(["descriptor", "similarity_gap_top1_minus_positive"], ascending=[True, False]).groupby("descriptor").head(limit_per_descriptor)


def feasibility_report(pairs: pd.DataFrame, directed: pd.DataFrame) -> pd.DataFrame:
    query_group = directed.groupby("query_token")
    return pd.DataFrame(
        [
            {
                "item": "phase8_slice1_feasibility",
                "status": "feasible_with_scope_caveat",
                "available_pair_count": int(len(pairs)),
                "directed_candidate_count": int(len(directed)),
                "unique_endpoint_count": int(directed["query_token"].nunique()),
                "queries_with_any_positive_candidate": int(query_group["is_positive"].any().sum()),
                "min_candidates_per_query": int(query_group.size().min()),
                "median_candidates_per_query": float(query_group.size().median()),
                "max_candidates_per_query": int(query_group.size().max()),
                "descriptor_columns_available": ",".join(DESCRIPTORS.values()),
                "pf_eri_filter_columns_available": ",".join([v for v in FILTERS.values() if v is not None]),
                "limitation": "existing data support sampled candidate-pair retrieval, not full all-vs-all query-gallery retrieval",
            }
        ]
    )


def make_figures(cmc: pd.DataFrame, comparison: pd.DataFrame, metrics: pd.DataFrame) -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid")

    plt.figure(figsize=(8, 5))
    for (descriptor, filter_name), group in cmc.groupby(["descriptor", "filter_name"]):
        if filter_name not in {"all_modeling_eligible", "pf_eri_medium_or_higher"}:
            continue
        plt.plot(group["rank_k"], group["cmc"], marker="o", label=f"{descriptor} / {filter_name}")
    plt.xlabel("rank k")
    plt.ylabel("CMC")
    plt.title("CzechLynx candidate-graph CMC")
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "phase8_czechlynx_candidate_graph_cmc.png", dpi=180)
    plt.close()

    plt.figure(figsize=(8, 5))
    subset = comparison[comparison["filter_name"].isin(["all_modeling_eligible", "pf_eri_low_or_higher", "pf_eri_medium_or_higher", "pf_eri_high_only"])]
    labels = subset["descriptor"] + "\n" + subset["filter_name"].str.replace("_", " ")
    plt.bar(np.arange(len(subset)), subset["mAP"], color="#4477AA")
    plt.xticks(np.arange(len(subset)), labels, rotation=45, ha="right", fontsize=7)
    plt.ylabel("mAP")
    plt.title("PF-ERI filtering comparison")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "phase8_czechlynx_pf_eri_filter_map_comparison.png", dpi=180)
    plt.close()

    plt.figure(figsize=(8, 5))
    labels = metrics["descriptor"] + "\n" + metrics["filter_name"].str.replace("_", " ")
    plt.bar(np.arange(len(metrics)), metrics["false_top1_rate_among_evaluable"], color="#CC6677")
    plt.xticks(np.arange(len(metrics)), labels, rotation=45, ha="right", fontsize=7)
    plt.ylabel("false top-1 rate")
    plt.title("False nearest-neighbor rate by filter")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "phase8_czechlynx_false_top1_rate_by_filter.png", dpi=180)
    plt.close()


def run(args: argparse.Namespace) -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pairs = load_pair_data(args.pair_table_csv, args.pf_eri_pair_csv)
    directed = build_directed_candidates(pairs)

    metrics = []
    cmc = []
    for descriptor, score_col in DESCRIPTORS.items():
        for filter_name, filter_col in FILTERS.items():
            metric = evaluate_retrieval(directed, descriptor, score_col, filter_name, filter_col)
            metrics.append(metric)
            cmc.extend(cmc_rows(directed, descriptor, score_col, filter_name, filter_col))

    metrics_df = pd.DataFrame(metrics)
    cmc_df = pd.DataFrame(cmc)
    topk_df = pd.DataFrame(topk_rows(metrics))
    map_df = metrics_df[
        [
            "descriptor",
            "filter_name",
            "mAP",
            "mean_reciprocal_rank",
            "evaluable_positive_query_count",
            "query_coverage",
            "benchmark_scope",
        ]
    ].copy()
    comparison_df = metrics_df.copy()
    failure_df = failure_case_examples(directed)
    feasibility_df = feasibility_report(pairs, directed)

    metrics_df.to_csv(METRICS_CSV, index=False)
    cmc_df.to_csv(CMC_CSV, index=False)
    topk_df.to_csv(TOPK_CSV, index=False)
    map_df.to_csv(MAP_CSV, index=False)
    comparison_df.to_csv(PF_ERI_COMPARISON_CSV, index=False)
    failure_df.to_csv(FAILURE_CASES_CSV, index=False)
    feasibility_df.to_csv(FEASIBILITY_CSV, index=False)
    make_figures(cmc_df, comparison_df, metrics_df)

    best = metrics_df.sort_values(["filter_name", "descriptor"]).copy()
    print("PASS: Phase 8 CzechLynx retrieval-style benchmark complete")
    print(f"available_pair_count: {len(pairs)}")
    print(f"directed_candidate_count: {len(directed)}")
    print(f"query_count: {directed['query_token'].nunique()}")
    for _, row in best.iterrows():
        print(
            f"{row['descriptor']} / {row['filter_name']}: "
            f"mAP={row['mAP']:.4f}, top1={row['top1_accuracy']:.4f}, "
            f"query_coverage={row['query_coverage']:.4f}, "
            f"false_top1={row['false_top1_rate_among_evaluable']:.4f}"
        )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair-table-csv", type=Path, default=PAIR_TABLE_CSV)
    parser.add_argument("--pf-eri-pair-csv", type=Path, default=PF_ERI_PAIR_CSV)
    return parser.parse_args()


def main() -> int:
    return run(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
