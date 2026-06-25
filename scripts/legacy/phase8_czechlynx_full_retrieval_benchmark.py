#!/usr/bin/env python3
"""Run full all-vs-all CzechLynx retrieval benchmark for Phase 8 Slice 2."""

from __future__ import annotations

import argparse
import ast
import hashlib
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MEGA_EMBEDDINGS_CSV = PROJECT_ROOT / "outputs/czechlynx/phase4/czechlynx_phase4c_megadescriptor_embeddings.csv"
RESNET_EMBEDDINGS_CSV = PROJECT_ROOT / "outputs/czechlynx/phase4/czechlynx_phase4c_resnet50_embeddings.csv"
IDENTITY_CSV = PROJECT_ROOT / "data/interim/czechlynx/czechlynx_expanded_125x4_internal_with_ids.csv"
ANNOTATION_CSV = PROJECT_ROOT / "data/labels/czechlynx/czechlynx_phase7a_1000_image_annotations_v1.csv"
SLICE1_METRICS_CSV = PROJECT_ROOT / "outputs/czechlynx/phase8/reid_tool_benchmark/phase8_czechlynx_retrieval_metrics_summary.csv"

OUTPUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase8/full_retrieval_benchmark"
FIGURE_DIR = OUTPUT_DIR / "figures"

METRICS_CSV = OUTPUT_DIR / "phase8_czechlynx_full_retrieval_metrics_summary.csv"
CMC_CSV = OUTPUT_DIR / "phase8_czechlynx_full_retrieval_cmc_table.csv"
TOPK_CSV = OUTPUT_DIR / "phase8_czechlynx_full_retrieval_topk_table.csv"
MAP_CSV = OUTPUT_DIR / "phase8_czechlynx_full_retrieval_map_summary.csv"
FILTER_COMPARISON_CSV = OUTPUT_DIR / "phase8_czechlynx_full_retrieval_pf_eri_filter_comparison.csv"
FAILURE_CASES_CSV = OUTPUT_DIR / "phase8_czechlynx_full_retrieval_failure_cases.csv"
FEASIBILITY_CSV = OUTPUT_DIR / "phase8_czechlynx_full_retrieval_feasibility_report.csv"
RANK_DISTRIBUTION_CSV = OUTPUT_DIR / "phase8_czechlynx_full_retrieval_same_identity_rank_distribution.csv"
FAILURE_MODE_SUMMARY_CSV = OUTPUT_DIR / "phase8_czechlynx_full_retrieval_failure_mode_summary.csv"

TOP_K = [1, 3, 5, 10]
FILTERS = {
    "all_images": None,
    "pf_eri_low_or_higher": "low_or_higher",
    "pf_eri_medium_or_higher": "medium_or_higher",
    "pf_eri_high_only": "high_only",
    "pf_eri_medium_or_higher_no_severe_failure": "medium_or_higher_no_severe_failure",
}

PATTERN = {"none": 0.0, "low": 1.0, "medium": 2.0, "high": 3.0}
SIDE_QUALITY = {"none": 0.0, "low": 1.0, "medium": 2.0, "high": 3.0}
BODY = {"0_25": 0.0, "26_50": 1.0, "51_75": 2.0, "76_100": 3.0, "unknown": 1.0}
BLUR = {"severe": 0.0, "moderate": 1.0, "mild": 2.0, "none": 3.0, "unknown": 1.0}
OCCLUSION = {"major": 0.0, "partial": 1.5, "none": 3.0, "unknown": 1.5}
CONTRAST = {"low": 0.0, "not_available": 1.0, "good": 2.0, "unknown": 1.0}


def clean_string(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.lower()


def token(value: object) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:12]


def band(score: float) -> str:
    if score >= 75.0:
        return "high"
    if score >= 50.0:
        return "medium"
    if score >= 25.0:
        return "low"
    return "unusable"


def parse_embedding(value: str) -> np.ndarray:
    parsed = ast.literal_eval(value)
    return np.asarray(parsed, dtype=np.float64)


def load_embeddings(path: Path) -> tuple[pd.DataFrame, np.ndarray]:
    df = pd.read_csv(path)
    vectors = np.vstack([parse_embedding(value) for value in df["embedding_vector"]])
    if not np.isfinite(vectors).all():
        raise ValueError(f"non-finite embedding values found in {path}")
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    vectors = vectors / norms
    return df[["expanded_image_id", "embedding_model", "embedding_dim"]].copy(), vectors


def score_image_visual(row: pd.Series) -> dict[str, object]:
    pattern = PATTERN[str(row["pattern_visibility"])]
    side = SIDE_QUALITY[str(row["side_evidence_quality"])]
    body = BODY[str(row["body_fraction_visible"])]
    blur = BLUR[str(row["blur_level"])]
    occlusion = OCCLUSION[str(row["occlusion_level"])]
    contrast = CONTRAST[str(row["contrast_level"])]
    frontal_penalty = 8.0 if row["frontal_or_rear_view"] == "yes" else 3.0 if row["frontal_or_rear_view"] == "unknown" else 0.0
    silhouette_penalty = 12.0 if row["silhouette_only"] == "yes" else 0.0
    partial_penalty = 6.0 if row["partial_body"] == "yes" else 0.0
    uncertainty_penalty = 5.0 if row["uncertainty_flag"] == "yes" else 0.0
    night_ir_penalty = 4.0 if row["night_ir_artifact"] == "yes" else 0.0
    weighted = 100.0 * (
        0.26 * (pattern / 3.0)
        + 0.24 * (side / 3.0)
        + 0.16 * (body / 3.0)
        + 0.14 * (blur / 3.0)
        + 0.10 * (occlusion / 3.0)
        + 0.05 * (contrast / 2.0)
    )
    weighted = max(0.0, min(100.0, weighted - frontal_penalty - silhouette_penalty - partial_penalty - uncertainty_penalty - night_ir_penalty))
    components = {
        "pattern_visibility": pattern / 3.0,
        "side_evidence_quality": side / 3.0,
        "body_fraction_visible": body / 3.0,
        "blur_level": blur / 3.0,
        "occlusion_level": occlusion / 3.0,
    }
    if row["contrast_level"] != "not_available":
        components["contrast_level"] = contrast / 2.0
    primary = min(components.items(), key=lambda item: item[1])[0]
    severe_failure = (
        row["pattern_visibility"] == "none"
        or row["blur_level"] == "severe"
        or row["occlusion_level"] == "major"
        or row["silhouette_only"] == "yes"
        or row["frontal_or_rear_view"] == "yes"
    )
    return {
        "visual_pf_eri_image_weighted": weighted,
        "visual_pf_eri_image_band": band(weighted),
        "primary_limiting_factor_image": primary,
        "severe_visual_failure_image": "yes" if severe_failure else "no",
    }


def load_metadata(identity_csv: Path, annotation_csv: Path, embedding_ids: set[str]) -> pd.DataFrame:
    ids = pd.read_csv(identity_csv)[["expanded_image_id", "working_individual_id"]].copy()
    annotations = pd.read_csv(annotation_csv)
    visual_cols = [
        "expanded_image_id",
        "pattern_visibility",
        "side_evidence_quality",
        "body_fraction_visible",
        "partial_body",
        "frontal_or_rear_view",
        "silhouette_only",
        "blur_level",
        "occlusion_level",
        "lighting_condition",
        "night_ir_artifact",
        "contrast_level",
        "primary_limiting_factor",
        "uncertainty_flag",
        "annotation_status",
    ]
    annotations = annotations[visual_cols].copy()
    for col in visual_cols:
        if col != "expanded_image_id":
            annotations[col] = clean_string(annotations[col])
    metadata = ids.merge(annotations, on="expanded_image_id", how="inner", validate="one_to_one")
    metadata = metadata[metadata["expanded_image_id"].isin(embedding_ids)].copy()
    scored = metadata.apply(score_image_visual, axis=1, result_type="expand")
    metadata = pd.concat([metadata.reset_index(drop=True), scored.reset_index(drop=True)], axis=1)
    metadata["query_token"] = metadata["expanded_image_id"].map(token)
    metadata["identity_token"] = metadata["working_individual_id"].map(token)
    return metadata


def filter_mask(metadata: pd.DataFrame, filter_name: str) -> np.ndarray:
    if filter_name == "all_images":
        return np.ones(len(metadata), dtype=bool)
    band_values = metadata["visual_pf_eri_image_band"]
    if filter_name == "pf_eri_low_or_higher":
        return band_values.isin(["low", "medium", "high"]).to_numpy()
    if filter_name == "pf_eri_medium_or_higher":
        return band_values.isin(["medium", "high"]).to_numpy()
    if filter_name == "pf_eri_high_only":
        return band_values.eq("high").to_numpy()
    if filter_name == "pf_eri_medium_or_higher_no_severe_failure":
        return (band_values.isin(["medium", "high"]) & metadata["severe_visual_failure_image"].eq("no")).to_numpy()
    raise ValueError(f"unknown filter: {filter_name}")


def average_precision(relevance: np.ndarray) -> float:
    positives = int(relevance.sum())
    if positives == 0:
        return math.nan
    cumulative = np.cumsum(relevance)
    precision_at_hits = cumulative[relevance == 1] / (np.flatnonzero(relevance == 1) + 1)
    return float(precision_at_hits.mean())


def evaluate_descriptor(metadata: pd.DataFrame, similarity: np.ndarray, descriptor: str, filter_name: str) -> tuple[dict[str, object], list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    admissible = filter_mask(metadata, filter_name)
    identities = metadata["working_individual_id"].astype(str).to_numpy()
    tokens = metadata["query_token"].to_numpy()
    rows = np.arange(len(metadata))
    full_positive_query_count = int(sum(((identities == identities[i]) & (rows != i)).any() for i in rows))

    ap_values: list[float] = []
    rr_values: list[float] = []
    top_hits = {k: [] for k in TOP_K}
    positive_ranks: list[int] = []
    false_cases: list[dict[str, object]] = []
    evaluable_count = 0
    query_count = 0
    positive_query_after_filter = 0
    same_gallery_counts: list[int] = []
    gallery_counts: list[int] = []

    for i in rows:
        if not admissible[i]:
            continue
        gallery_mask = admissible.copy()
        gallery_mask[i] = False
        gallery_indices = rows[gallery_mask]
        if len(gallery_indices) == 0:
            continue
        query_count += 1
        scores = similarity[i, gallery_indices]
        order = np.argsort(-scores)
        ranked_indices = gallery_indices[order]
        relevance = (identities[ranked_indices] == identities[i]).astype(int)
        gallery_counts.append(len(ranked_indices))
        same_gallery_counts.append(int(relevance.sum()))
        if relevance.sum() == 0:
            continue
        positive_query_after_filter += 1
        evaluable_count += 1
        ap_values.append(average_precision(relevance))
        first_rank = int(np.flatnonzero(relevance == 1)[0]) + 1
        positive_ranks.append(first_rank)
        rr_values.append(1.0 / first_rank)
        for k in TOP_K:
            top_hits[k].append(int(relevance[: min(k, len(relevance))].max()))
        top1_index = ranked_indices[0]
        if identities[top1_index] != identities[i]:
            false_cases.append(false_case_row(metadata, descriptor, filter_name, i, top1_index, ranked_indices, scores[order]))

    metric = {
        "descriptor": descriptor,
        "filter_name": filter_name,
        "query_count": query_count,
        "gallery_count": int(admissible.sum()),
        "all_image_count": len(metadata),
        "identity_count_safe": int(metadata.loc[admissible, "identity_token"].nunique()),
        "query_coverage": query_count / len(metadata) if len(metadata) else math.nan,
        "positive_query_count_full": full_positive_query_count,
        "positive_query_count_after_filter": positive_query_after_filter,
        "positive_query_coverage": positive_query_after_filter / full_positive_query_count if full_positive_query_count else math.nan,
        "mean_gallery_size": float(np.mean(gallery_counts)) if gallery_counts else math.nan,
        "mean_same_identity_gallery_size": float(np.mean(same_gallery_counts)) if same_gallery_counts else math.nan,
        "mAP": float(np.mean(ap_values)) if ap_values else math.nan,
        "mean_reciprocal_rank": float(np.mean(rr_values)) if rr_values else math.nan,
        "median_first_same_identity_rank": float(np.median(positive_ranks)) if positive_ranks else math.nan,
        "false_top1_count": len(false_cases),
        "false_top1_rate": len(false_cases) / evaluable_count if evaluable_count else math.nan,
        "self_matches_excluded": "yes",
        "benchmark_scope": "full_all_vs_all_czechlynx_500_image_closed_set",
    }
    for k in TOP_K:
        metric[f"top{k}_accuracy"] = float(np.mean(top_hits[k])) if top_hits[k] else math.nan

    cmc_rows = [
        {
            "descriptor": descriptor,
            "filter_name": filter_name,
            "rank_k": k,
            "cmc": float(np.mean([rank <= k for rank in positive_ranks])) if positive_ranks else math.nan,
            "evaluable_positive_query_count": evaluable_count,
        }
        for k in range(1, 51)
    ]
    topk_rows = [
        {
            "descriptor": descriptor,
            "filter_name": filter_name,
            "k": k,
            "topk_accuracy": metric[f"top{k}_accuracy"],
            "positive_query_coverage": metric["positive_query_coverage"],
            "query_coverage": metric["query_coverage"],
        }
        for k in TOP_K
    ]
    rank_rows = [
        {
            "descriptor": descriptor,
            "filter_name": filter_name,
            "first_same_identity_rank": rank,
        }
        for rank in positive_ranks
    ]
    return metric, cmc_rows, topk_rows, rank_rows + false_cases


def false_case_row(metadata: pd.DataFrame, descriptor: str, filter_name: str, query_idx: int, top1_idx: int, ranked_indices: np.ndarray, ranked_scores: np.ndarray) -> dict[str, object]:
    identities = metadata["working_individual_id"].astype(str).to_numpy()
    positive_positions = np.flatnonzero(identities[ranked_indices] == identities[query_idx])
    best_positive_rank = int(positive_positions[0]) + 1 if len(positive_positions) else math.nan
    best_positive_score = float(ranked_scores[positive_positions[0]]) if len(positive_positions) else math.nan
    query = metadata.iloc[query_idx]
    top1 = metadata.iloc[top1_idx]
    return {
        "row_type": "false_top1_case",
        "descriptor": descriptor,
        "filter_name": filter_name,
        "query_token": query["query_token"],
        "top1_gallery_token": top1["query_token"],
        "top1_similarity": float(ranked_scores[0]),
        "best_positive_rank": best_positive_rank,
        "best_positive_similarity": best_positive_score,
        "similarity_gap_top1_minus_best_positive": float(ranked_scores[0] - best_positive_score) if not math.isnan(best_positive_score) else math.nan,
        "query_visual_band": query["visual_pf_eri_image_band"],
        "top1_visual_band": top1["visual_pf_eri_image_band"],
        "query_primary_limiting_factor": query["primary_limiting_factor_image"],
        "top1_primary_limiting_factor": top1["primary_limiting_factor_image"],
        "query_severe_visual_failure": query["severe_visual_failure_image"],
        "top1_severe_visual_failure": top1["severe_visual_failure_image"],
        "query_frontal_or_rear": query["frontal_or_rear_view"],
        "top1_frontal_or_rear": top1["frontal_or_rear_view"],
        "query_pattern_visibility": query["pattern_visibility"],
        "top1_pattern_visibility": top1["pattern_visibility"],
        "interpretation": "false nearest neighbor under full all-vs-all retrieval; anonymized tokens only",
    }


def failure_cases_frame(rows: list[dict[str, object]]) -> pd.DataFrame:
    cases = [row for row in rows if row.get("row_type") == "false_top1_case"]
    if not cases:
        return pd.DataFrame()
    df = pd.DataFrame(cases)
    return df.sort_values(["descriptor", "filter_name", "similarity_gap_top1_minus_best_positive"], ascending=[True, True, False]).groupby(["descriptor", "filter_name"]).head(40)


def failure_mode_summary_frame(rows: list[dict[str, object]]) -> pd.DataFrame:
    cases = [row for row in rows if row.get("row_type") == "false_top1_case"]
    if not cases:
        return pd.DataFrame()
    df = pd.DataFrame(cases)
    summary_rows = []
    fields = [
        "query_visual_band",
        "top1_visual_band",
        "query_primary_limiting_factor",
        "top1_primary_limiting_factor",
        "query_severe_visual_failure",
        "top1_severe_visual_failure",
        "query_frontal_or_rear",
        "top1_frontal_or_rear",
        "query_pattern_visibility",
        "top1_pattern_visibility",
    ]
    for (descriptor, filter_name), group in df.groupby(["descriptor", "filter_name"]):
        total = len(group)
        for field in fields:
            for value, count in group[field].value_counts(dropna=False).items():
                summary_rows.append(
                    {
                        "descriptor": descriptor,
                        "filter_name": filter_name,
                        "failure_mode_field": field,
                        "failure_mode_value": value,
                        "false_top1_count": int(count),
                        "false_top1_share": count / total if total else math.nan,
                    }
                )
    return pd.DataFrame(summary_rows)


def rank_distribution_frame(rows: list[dict[str, object]]) -> pd.DataFrame:
    rank_rows = [row for row in rows if "first_same_identity_rank" in row]
    return pd.DataFrame(rank_rows)


def feasibility_frame(metadata: pd.DataFrame, mega_meta: pd.DataFrame, resnet_meta: pd.DataFrame) -> pd.DataFrame:
    counts = metadata["working_individual_id"].value_counts()
    return pd.DataFrame(
        [
            {
                "item": "phase8_slice2_full_retrieval_feasibility",
                "status": "feasible",
                "aligned_image_count": len(metadata),
                "megadescriptor_embedding_count": len(mega_meta),
                "resnet50_embedding_count": len(resnet_meta),
                "identity_count_safe": int(metadata["identity_token"].nunique()),
                "min_images_per_identity": int(counts.min()),
                "median_images_per_identity": float(counts.median()),
                "max_images_per_identity": int(counts.max()),
                "annotation_complete_count": int((metadata["annotation_status"] == "complete").sum()),
                "self_matches_excluded": "yes",
                "identity_label_use": "evaluation_only_not_retrieval_scoring",
                "scope": "czechlynx_only_full_all_vs_all_500_image_closed_set",
            }
        ]
    )


def make_figures(metrics: pd.DataFrame, cmc: pd.DataFrame, topk: pd.DataFrame) -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(9, 6))
    for (descriptor, filter_name), group in cmc.groupby(["descriptor", "filter_name"]):
        if filter_name not in {"all_images", "pf_eri_medium_or_higher", "pf_eri_high_only"}:
            continue
        plt.plot(group["rank_k"], group["cmc"], marker="o", markersize=2, label=f"{descriptor} / {filter_name}")
    plt.xlabel("Rank k")
    plt.ylabel("CMC")
    plt.title("Full all-vs-all CzechLynx CMC")
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "phase8_full_retrieval_cmc_curves.png", dpi=180)
    plt.close()

    def bar_metric(metric_name: str, filename: str, ylabel: str) -> None:
        plt.figure(figsize=(10, 6))
        labels = metrics["descriptor"] + "\n" + metrics["filter_name"].str.replace("_", " ")
        plt.bar(np.arange(len(metrics)), metrics[metric_name], color=["#4477AA" if d == "megadescriptor" else "#CC6677" for d in metrics["descriptor"]])
        plt.xticks(np.arange(len(metrics)), labels, rotation=45, ha="right", fontsize=7)
        plt.ylabel(ylabel)
        plt.title(ylabel)
        plt.tight_layout()
        plt.savefig(FIGURE_DIR / filename, dpi=180)
        plt.close()

    bar_metric("mAP", "phase8_full_retrieval_map_comparison.png", "mAP")
    bar_metric("top1_accuracy", "phase8_full_retrieval_top1_comparison.png", "Top-1 accuracy")
    bar_metric("false_top1_rate", "phase8_full_retrieval_false_top1_comparison.png", "False top-1 rate")

    plt.figure(figsize=(8, 6))
    for descriptor, group in metrics.groupby("descriptor"):
        plt.plot(group["query_coverage"], group["mAP"], marker="o", label=descriptor)
    plt.xlabel("Query coverage")
    plt.ylabel("mAP")
    plt.title("PF-ERI coverage/reliability tradeoff")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "phase8_full_retrieval_query_coverage_vs_map.png", dpi=180)
    plt.close()

    plt.figure(figsize=(8, 6))
    for descriptor, group in metrics.groupby("descriptor"):
        plt.plot(group["query_coverage"], group["false_top1_rate"], marker="o", label=descriptor)
    plt.xlabel("Query coverage")
    plt.ylabel("False top-1 rate")
    plt.title("PF-ERI filter tradeoff")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "phase8_full_retrieval_pf_eri_filter_tradeoff.png", dpi=180)
    plt.close()

    plt.figure(figsize=(9, 6))
    subset = topk[topk["filter_name"].isin(["all_images", "pf_eri_high_only"])]
    for (descriptor, filter_name), group in subset.groupby(["descriptor", "filter_name"]):
        plt.plot(group["k"], group["topk_accuracy"], marker="o", label=f"{descriptor} / {filter_name}")
    plt.xlabel("k")
    plt.ylabel("Top-k accuracy")
    plt.title("Top-k comparison")
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "phase8_full_retrieval_topk_comparison.png", dpi=180)
    plt.close()


def run(args: argparse.Namespace) -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    mega_meta, mega_vectors = load_embeddings(args.megadescriptor_embeddings_csv)
    resnet_meta, resnet_vectors = load_embeddings(args.resnet50_embeddings_csv)
    common_ids = set(mega_meta["expanded_image_id"]) & set(resnet_meta["expanded_image_id"])
    metadata = load_metadata(args.identity_csv, args.annotation_csv, common_ids)
    metadata = metadata.sort_values("expanded_image_id").reset_index(drop=True)

    mega_order = mega_meta.set_index("expanded_image_id").loc[metadata["expanded_image_id"]].index
    resnet_order = resnet_meta.set_index("expanded_image_id").loc[metadata["expanded_image_id"]].index
    if list(mega_order) != list(metadata["expanded_image_id"]) or list(resnet_order) != list(metadata["expanded_image_id"]):
        raise ValueError("embedding order alignment failed")
    mega_lookup = {image_id: idx for idx, image_id in enumerate(mega_meta["expanded_image_id"])}
    resnet_lookup = {image_id: idx for idx, image_id in enumerate(resnet_meta["expanded_image_id"])}
    ordered_mega = mega_vectors[[mega_lookup[x] for x in metadata["expanded_image_id"]]]
    ordered_resnet = resnet_vectors[[resnet_lookup[x] for x in metadata["expanded_image_id"]]]

    similarities = {
        "megadescriptor": np.einsum("ik,jk->ij", ordered_mega, ordered_mega, optimize=True),
        "resnet50": np.einsum("ik,jk->ij", ordered_resnet, ordered_resnet, optimize=True),
    }
    all_metrics: list[dict[str, object]] = []
    all_cmc: list[dict[str, object]] = []
    all_topk: list[dict[str, object]] = []
    aux_rows: list[dict[str, object]] = []
    for descriptor, sim in similarities.items():
        for filter_name in FILTERS:
            metric, cmc_rows, topk_rows, rank_and_failure_rows = evaluate_descriptor(metadata, sim, descriptor, filter_name)
            all_metrics.append(metric)
            all_cmc.extend(cmc_rows)
            all_topk.extend(topk_rows)
            aux_rows.extend(rank_and_failure_rows)

    metrics = pd.DataFrame(all_metrics)
    cmc = pd.DataFrame(all_cmc)
    topk = pd.DataFrame(all_topk)
    map_summary = metrics[[
        "descriptor",
        "filter_name",
        "mAP",
        "mean_reciprocal_rank",
        "median_first_same_identity_rank",
        "query_coverage",
        "positive_query_coverage",
        "benchmark_scope",
    ]].copy()
    failure_cases = failure_cases_frame(aux_rows)
    failure_summary = failure_mode_summary_frame(aux_rows)
    rank_distribution = rank_distribution_frame(aux_rows)
    feasibility = feasibility_frame(metadata, mega_meta, resnet_meta)

    metrics.to_csv(METRICS_CSV, index=False)
    cmc.to_csv(CMC_CSV, index=False)
    topk.to_csv(TOPK_CSV, index=False)
    map_summary.to_csv(MAP_CSV, index=False)
    metrics.to_csv(FILTER_COMPARISON_CSV, index=False)
    failure_cases.to_csv(FAILURE_CASES_CSV, index=False)
    failure_summary.to_csv(FAILURE_MODE_SUMMARY_CSV, index=False)
    feasibility.to_csv(FEASIBILITY_CSV, index=False)
    rank_distribution.to_csv(RANK_DISTRIBUTION_CSV, index=False)
    make_figures(metrics, cmc, topk)

    print("PASS: Phase 8 full all-vs-all CzechLynx retrieval benchmark complete")
    print(f"query_count: {len(metadata)}")
    print(f"gallery_count: {len(metadata)}")
    print(f"identity_count_safe: {metadata['identity_token'].nunique()}")
    for _, row in metrics.sort_values(["filter_name", "descriptor"]).iterrows():
        print(
            f"{row['descriptor']} / {row['filter_name']}: "
            f"mAP={row['mAP']:.4f}, top1={row['top1_accuracy']:.4f}, "
            f"top5={row['top5_accuracy']:.4f}, false_top1={row['false_top1_rate']:.4f}, "
            f"query_coverage={row['query_coverage']:.4f}"
        )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--megadescriptor-embeddings-csv", type=Path, default=MEGA_EMBEDDINGS_CSV)
    parser.add_argument("--resnet50-embeddings-csv", type=Path, default=RESNET_EMBEDDINGS_CSV)
    parser.add_argument("--identity-csv", type=Path, default=IDENTITY_CSV)
    parser.add_argument("--annotation-csv", type=Path, default=ANNOTATION_CSV)
    return parser.parse_args()


def main() -> int:
    return run(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
