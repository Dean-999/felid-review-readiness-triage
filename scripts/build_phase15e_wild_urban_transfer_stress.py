#!/usr/bin/env python3
"""Apply Phase 15 evidence-routing policy to bobcat transfer stress data.

Phase 15E trains the calibrated routing score on CzechLynx known-ID candidate
pairs and applies the same score/action policy to urban/peri-urban bobcat
candidate pairs. Bobcat has no verified identity labels here, so outputs are
review-readiness and contamination-pressure diagnostics only.
"""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE14_DIR = PROJECT_ROOT / "outputs/phase14"
PHASE15_DIR = PROJECT_ROOT / "outputs/phase15"

IMAGE_EVIDENCE = PHASE14_DIR / "phase14_algorithm_inputs/phase14_2x2_image_evidence_table.csv"
EMBEDDINGS = PHASE14_DIR / "phase14_descriptor_embeddings/phase14_2x2_megadescriptor_embeddings.csv"
CZECH_ROUTING_INPUT = PHASE15_DIR / "hybrid_routing_policy/phase15_czechlynx_candidate_routing_input.csv"
CZECH_ACTION_TABLE = PHASE15_DIR / "evidence_routed_review_policy/phase15d_evidence_routed_review_table.csv"
OUT_DIR = PHASE15_DIR / "wild_urban_transfer_stress"

BOBCAT_TOPK = OUT_DIR / "phase15e_bobcat_top50_candidate_pairs.csv"
BOBCAT_ROUTING = OUT_DIR / "phase15e_bobcat_evidence_routed_review_table.csv"
BOBCAT_ACTION_SUMMARY = OUT_DIR / "phase15e_bobcat_action_summary.csv"
BOBCAT_QUERY_SUMMARY = OUT_DIR / "phase15e_bobcat_query_review_summary.csv"
WILD_URBAN_COMPARISON = OUT_DIR / "phase15e_wild_urban_action_comparison.csv"
EVIDENCE_AXIS_COMPARISON = OUT_DIR / "phase15e_evidence_axis_action_comparison.csv"
AUDIT_JSON = OUT_DIR / "phase15e_wild_urban_transfer_stress_audit.json"
REPORT_MD = OUT_DIR / "phase15e_wild_urban_transfer_stress_report.md"

TOP_K = 50
DEFAULT_SEED = 20260622
ACCEPT_COVERAGE = 0.05
REVIEW_COVERAGE = 0.20

FEATURE_COLUMNS = [
    "descriptor_similarity",
    "descriptor_rank_support_score",
    "pair_comparability_score",
    "weakest_image_utility_score",
    "mean_image_utility_score",
    "pattern_pair_score",
    "side_comparability_score",
    "body_visibility_pair_score",
    "blur_pair_score",
    "occlusion_pair_score",
    "detector_geometry_pair_score",
    "edge_touch_pair_penalty",
    "descriptor_evidence_conflict_score",
    "descriptor_evidence_support_score",
]

PAIR_SCORE_WEIGHTS = {
    "weakest_image_utility_score": 0.20,
    "side_comparability_score": 0.22,
    "pattern_pair_score": 0.18,
    "body_visibility_pair_score": 0.12,
    "blur_pair_score": 0.10,
    "occlusion_pair_score": 0.08,
    "detector_geometry_pair_score": 0.10,
}

ACTION_ORDER = {
    "accept": 0,
    "review": 1,
    "defer": 2,
    "species_level_only": 3,
    "non_comparable": 4,
}


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def numeric_frame(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = frame[columns].apply(pd.to_numeric, errors="coerce")
    return out.fillna(out.median(numeric_only=True)).fillna(0.0)


def parse_vector(value: object) -> np.ndarray:
    text = str(value).strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    return np.fromstring(text.replace(",", " "), sep=" ", dtype=np.float32)


def load_bobcat_embeddings(image: pd.DataFrame, embeddings_path: Path) -> tuple[pd.DataFrame, np.ndarray]:
    bobcat = image[image["species_axis"].eq("bobcat")].copy()
    embeddings = pd.read_csv(embeddings_path, low_memory=False)
    merged = bobcat.merge(embeddings, on="phase14_image_evidence_id", how="inner")
    if len(merged) != len(bobcat):
        missing = len(bobcat) - len(merged)
        raise ValueError(f"Missing bobcat embeddings for {missing} images")
    vectors = np.vstack([parse_vector(value) for value in merged["embedding_vector"]]).astype(np.float32)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    vectors = vectors / np.maximum(norms, 1e-12)
    return merged.reset_index(drop=True), vectors


def build_topk_candidates(images: pd.DataFrame, vectors: np.ndarray, top_k: int) -> pd.DataFrame:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*encountered in matmul")
        sims = vectors.astype(np.float64) @ vectors.astype(np.float64).T
    if not np.isfinite(sims).all():
        bad = int((~np.isfinite(sims)).sum())
        raise ValueError(f"Non-finite descriptor similarities after matrix multiplication: {bad}")
    np.fill_diagonal(sims, -np.inf)
    rows: list[dict[str, Any]] = []
    ids = images["phase14_image_evidence_id"].to_numpy()
    for i in range(len(images)):
        candidate_idx = np.argpartition(-sims[i], kth=top_k - 1)[:top_k]
        candidate_idx = candidate_idx[np.argsort(-sims[i, candidate_idx])]
        for rank, j in enumerate(candidate_idx, start=1):
            rows.append(
                {
                    "query_image_evidence_id": ids[i],
                    "candidate_image_evidence_id": ids[j],
                    "rank": rank,
                    "descriptor_similarity": float(sims[i, j]),
                    "same_identity": "unknown",
                    "query_identity_label": "unknown",
                    "candidate_identity_label": "unknown",
                }
            )
    return pd.DataFrame(rows)


def side_direction_compatibility(left: object, right: object) -> float:
    a = str(left).strip().lower()
    b = str(right).strip().lower()
    strong = {"left", "right", "both", "side"}
    weak = {"unknown", "", "nan", "<na>"}
    front_rear = {"frontal", "rear", "front", "back"}
    if a == b and a in strong:
        return 1.0
    if a == "both" and b in strong:
        return 0.90
    if b == "both" and a in strong:
        return 0.90
    if a in {"left", "right"} and b in {"left", "right"}:
        return 0.45
    if a in weak or b in weak:
        return 0.65
    if a in front_rear or b in front_rear:
        return 0.25
    return 0.50


def pair_band(score: float) -> str:
    if score >= 0.80:
        return "high_comparability"
    if score >= 0.55:
        return "reviewable_comparability"
    if score >= 0.30:
        return "low_comparability"
    return "non_comparable"


def route_decision(pair_score: float, weakest_quality: float, conflict: float) -> str:
    if pair_score >= 0.80 and weakest_quality >= 0.60 and conflict < 0.40:
        return "accept"
    if pair_score >= 0.55 and weakest_quality >= 0.45 and conflict < 0.70:
        return "review"
    if pair_score >= 0.30 and weakest_quality >= 0.30:
        return "defer"
    if weakest_quality < 0.25:
        return "species_level_only"
    return "non_comparable"


def primary_reason(row: pd.Series) -> str:
    if float(row["descriptor_evidence_conflict_score"]) >= 0.70:
        return "high_descriptor_evidence_conflict"
    if float(row["side_comparability_score"]) < 0.35:
        return "side_or_flank_not_comparable"
    if float(row["pattern_pair_score"]) < 0.35:
        return "weak_pattern_evidence"
    if float(row["weakest_image_utility_score"]) < 0.30:
        return "weakest_image_low_evidence"
    if float(row["detector_geometry_pair_score"]) < 0.35:
        return "animal_too_small_or_poor_detection_geometry"
    if float(row["pair_comparability_score"]) >= 0.55:
        return "evidence_comparable"
    return "low_pair_admissibility"


def add_pair_features(topk: pd.DataFrame, image: pd.DataFrame) -> pd.DataFrame:
    feature_cols = [
        "phase14_image_evidence_id",
        "environment_axis",
        "species_axis",
        "evidence_axis",
        "source_quadrant",
        "image_path",
        "image_evidence_utility_score",
        "pattern_evidence_score",
        "side_flank_evidence_score",
        "side_flank_visibility_raw",
        "body_visibility_score",
        "blur_evidence_score",
        "occlusion_evidence_score",
        "detector_geometry_score",
        "md_edge_touch",
    ]
    q = image[feature_cols].add_prefix("query_")
    c = image[feature_cols].add_prefix("candidate_")
    out = topk.merge(q, left_on="query_image_evidence_id", right_on="query_phase14_image_evidence_id", how="left")
    out = out.merge(c, left_on="candidate_image_evidence_id", right_on="candidate_phase14_image_evidence_id", how="left")
    missing = out["query_species_axis"].isna() | out["candidate_species_axis"].isna()
    if missing.any():
        raise ValueError(f"Missing image evidence features for {int(missing.sum())} pairs")

    side_direction = np.array(
        [
            side_direction_compatibility(left, right)
            for left, right in zip(out["query_side_flank_visibility_raw"], out["candidate_side_flank_visibility_raw"])
        ],
        dtype=np.float32,
    )
    out["query_evidence_axis"] = out["query_evidence_axis"].astype(str)
    out["candidate_evidence_axis"] = out["candidate_evidence_axis"].astype(str)
    out["pair_evidence_axis_relation"] = np.where(
        out["query_evidence_axis"].eq(out["candidate_evidence_axis"]), "same_axis", "mixed_axis"
    )
    out["query_image_utility_score"] = numeric(out["query_image_evidence_utility_score"])
    out["candidate_image_utility_score"] = numeric(out["candidate_image_evidence_utility_score"])
    out["weakest_image_utility_score"] = np.minimum(
        out["query_image_utility_score"], out["candidate_image_utility_score"]
    )
    out["mean_image_utility_score"] = (out["query_image_utility_score"] + out["candidate_image_utility_score"]) / 2
    out["pattern_pair_score"] = np.minimum(
        numeric(out["query_pattern_evidence_score"]), numeric(out["candidate_pattern_evidence_score"])
    )
    out["side_direction_compatibility"] = side_direction
    out["side_comparability_score"] = np.minimum(
        numeric(out["query_side_flank_evidence_score"]), numeric(out["candidate_side_flank_evidence_score"])
    ) * side_direction
    out["body_visibility_pair_score"] = np.minimum(
        numeric(out["query_body_visibility_score"]), numeric(out["candidate_body_visibility_score"])
    )
    out["blur_pair_score"] = np.minimum(numeric(out["query_blur_evidence_score"]), numeric(out["candidate_blur_evidence_score"]))
    out["occlusion_pair_score"] = np.minimum(
        numeric(out["query_occlusion_evidence_score"]), numeric(out["candidate_occlusion_evidence_score"])
    )
    out["detector_geometry_pair_score"] = np.minimum(
        numeric(out["query_detector_geometry_score"]), numeric(out["candidate_detector_geometry_score"])
    )
    edge_touch = out["query_md_edge_touch"].astype(str).str.lower().eq("yes") | out[
        "candidate_md_edge_touch"
    ].astype(str).str.lower().eq("yes")
    out["edge_touch_pair_penalty"] = edge_touch.astype(float)
    score = sum(float(weight) * out[column].astype(float) for column, weight in PAIR_SCORE_WEIGHTS.items())
    out["pair_comparability_score"] = (score - 0.08 * out["edge_touch_pair_penalty"].astype(float)).clip(0, 1)
    out["pair_risk_score"] = 1 - out["pair_comparability_score"]
    out["pair_admissibility_band"] = out["pair_comparability_score"].map(pair_band)
    out["descriptor_rank_support_score"] = ((TOP_K + 1 - numeric(out["rank"])) / TOP_K).clip(0, 1)
    out["descriptor_evidence_conflict_score"] = (
        out["descriptor_rank_support_score"] * (1 - out["pair_comparability_score"])
    ).clip(0, 1)
    out["descriptor_evidence_support_score"] = (
        out["descriptor_rank_support_score"] * out["pair_comparability_score"]
    ).clip(0, 1)
    out["evidence_route_decision"] = [
        route_decision(float(pair), float(quality), float(conflict))
        for pair, quality, conflict in zip(
            out["pair_comparability_score"],
            out["weakest_image_utility_score"],
            out["descriptor_evidence_conflict_score"],
        )
    ]
    out["primary_failure_reason"] = out.apply(primary_reason, axis=1)

    keep = [
        "query_image_evidence_id",
        "candidate_image_evidence_id",
        "rank",
        "descriptor_similarity",
        "descriptor_rank_support_score",
        "same_identity",
        "query_identity_label",
        "candidate_identity_label",
        "query_evidence_axis",
        "candidate_evidence_axis",
        "pair_evidence_axis_relation",
        "query_source_quadrant",
        "candidate_source_quadrant",
        "query_image_utility_score",
        "candidate_image_utility_score",
        "weakest_image_utility_score",
        "mean_image_utility_score",
        "pattern_pair_score",
        "side_comparability_score",
        "body_visibility_pair_score",
        "blur_pair_score",
        "occlusion_pair_score",
        "detector_geometry_pair_score",
        "edge_touch_pair_penalty",
        "pair_comparability_score",
        "pair_risk_score",
        "pair_admissibility_band",
        "descriptor_evidence_conflict_score",
        "descriptor_evidence_support_score",
        "evidence_route_decision",
        "primary_failure_reason",
        "query_image_path",
        "candidate_image_path",
    ]
    return out[keep].copy()


def fit_czech_model(czech_routing: pd.DataFrame, seed: int) -> tuple[HistGradientBoostingClassifier, dict[str, float]]:
    train = czech_routing[czech_routing["same_identity"].isin(["yes", "no"])].copy()
    x_train = numeric_frame(train, FEATURE_COLUMNS)
    y_train = train["same_identity"].eq("yes").astype(int).to_numpy()
    model = HistGradientBoostingClassifier(
        max_iter=160,
        learning_rate=0.05,
        l2_regularization=0.05,
        random_state=seed,
    )
    model.fit(x_train, y_train)
    czech_scores = model.predict_proba(x_train)[:, 1]
    thresholds = {
        "hgb_accept_score_threshold_czech_top5pct": float(np.quantile(czech_scores, 1 - ACCEPT_COVERAGE)),
        "hgb_review_score_threshold_czech_top20pct": float(np.quantile(czech_scores, 1 - REVIEW_COVERAGE)),
    }
    return model, thresholds


def assign_actions(frame: pd.DataFrame, model: HistGradientBoostingClassifier, thresholds: dict[str, float]) -> pd.DataFrame:
    out = frame.copy()
    x = numeric_frame(out, FEATURE_COLUMNS)
    out["phase15e_transfer_hgb_score"] = model.predict_proba(x)[:, 1]
    pair_comparability = numeric(out["pair_comparability_score"]).fillna(0.0)
    weakest_utility = numeric(out["weakest_image_utility_score"]).fillna(0.0)
    conflict = numeric(out["descriptor_evidence_conflict_score"]).fillna(0.0)
    score = numeric(out["phase15e_transfer_hgb_score"]).fillna(0.0)

    species_level = (
        out["evidence_route_decision"].eq("species_level_only")
        | ((weakest_utility < 0.25) & (pair_comparability < 0.30))
    )
    non_comparable = (
        ~species_level
        & (
            out["pair_admissibility_band"].eq("non_comparable")
            | out["evidence_route_decision"].eq("non_comparable")
            | (pair_comparability < 0.15)
        )
    )
    accept = (
        ~non_comparable
        & ~species_level
        & (score >= thresholds["hgb_accept_score_threshold_czech_top5pct"])
        & (pair_comparability >= 0.65)
        & (weakest_utility >= 0.55)
        & (conflict < 0.50)
    )
    review = (
        ~non_comparable
        & ~species_level
        & ~accept
        & (score >= thresholds["hgb_review_score_threshold_czech_top20pct"])
        & (pair_comparability >= 0.45)
        & (weakest_utility >= 0.35)
    )
    out["phase15e_review_action"] = np.select(
        [non_comparable, species_level, accept, review],
        ["non_comparable", "species_level_only", "accept", "review"],
        default="defer",
    )
    out["phase15e_action_rank"] = out["phase15e_review_action"].map(ACTION_ORDER)
    out["phase15e_claim_boundary"] = (
        "Bobcat identity labels unavailable; action is transfer stress/review-readiness only, not identity accuracy."
    )
    return out


def summarize_actions(frame: pd.DataFrame, action_col: str, context: str) -> pd.DataFrame:
    rows = []
    total = max(len(frame), 1)
    total_queries = max(frame["query_image_evidence_id"].nunique(), 1)
    for action, part in frame.groupby(action_col, sort=False):
        rows.append(
            {
                "dataset_context": context,
                "review_action": action,
                "action_rank": ACTION_ORDER[action],
                "pairs": int(len(part)),
                "pair_fraction": float(len(part) / total),
                "queries_with_action": int(part["query_image_evidence_id"].nunique()),
                "query_fraction_with_action": float(part["query_image_evidence_id"].nunique() / total_queries),
                "mean_pair_comparability": float(numeric(part["pair_comparability_score"]).mean()),
                "mean_weakest_image_utility": float(numeric(part["weakest_image_utility_score"]).mean()),
                "mean_conflict": float(numeric(part["descriptor_evidence_conflict_score"]).mean()),
            }
        )
    return pd.DataFrame(rows).sort_values("action_rank")


def summarize_queries(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for query_id, part in frame.groupby("query_image_evidence_id", sort=False):
        counts = part["phase15e_review_action"].value_counts().to_dict()
        best = part.sort_values(
            ["phase15e_action_rank", "phase15e_transfer_hgb_score", "descriptor_similarity"],
            ascending=[True, False, False],
        ).iloc[0]
        rows.append(
            {
                "query_image_evidence_id": query_id,
                "query_evidence_axis": best["query_evidence_axis"],
                "query_source_quadrant": best["query_source_quadrant"],
                "best_candidate_image_evidence_id": best["candidate_image_evidence_id"],
                "best_review_action": best["phase15e_review_action"],
                "best_transfer_hgb_score": float(best["phase15e_transfer_hgb_score"]),
                "best_descriptor_similarity": float(best["descriptor_similarity"]),
                "accept_pairs": int(counts.get("accept", 0)),
                "review_pairs": int(counts.get("review", 0)),
                "defer_pairs": int(counts.get("defer", 0)),
                "species_level_only_pairs": int(counts.get("species_level_only", 0)),
                "non_comparable_pairs": int(counts.get("non_comparable", 0)),
            }
        )
    return pd.DataFrame(rows)


def compare_with_czech(czech_action_path: Path, bobcat: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    czech = pd.read_csv(czech_action_path, low_memory=False)
    czech_compare = czech.rename(columns={"phase15d_review_action": "review_action"}).copy()
    czech_compare["dataset_context"] = "wild_czechlynx_known_id"
    czech_compare["transfer_scope"] = "known_id_validation"
    czech_compare["score_column_used"] = "phase15d_action_score"
    bobcat_compare = bobcat.rename(columns={"phase15e_review_action": "review_action"}).copy()
    bobcat_compare["dataset_context"] = "urban_bobcat_identity_unknown"
    bobcat_compare["transfer_scope"] = "review_readiness_stress_only"
    bobcat_compare["score_column_used"] = "phase15e_transfer_hgb_score"
    combined = pd.concat([czech_compare, bobcat_compare], ignore_index=True, sort=False)

    overall = (
        combined.groupby(["dataset_context", "review_action"], as_index=False)
        .agg(
            pairs=("review_action", "size"),
            queries_with_action=("query_image_evidence_id", "nunique"),
            mean_pair_comparability=("pair_comparability_score", "mean"),
            mean_weakest_image_utility=("weakest_image_utility_score", "mean"),
            mean_conflict=("descriptor_evidence_conflict_score", "mean"),
        )
        .sort_values(["dataset_context", "review_action"])
    )
    total_pairs = overall.groupby("dataset_context")["pairs"].transform("sum")
    total_queries = combined.groupby("dataset_context")["query_image_evidence_id"].transform("nunique")
    query_totals = combined[["dataset_context", "query_image_evidence_id"]].drop_duplicates().groupby(
        "dataset_context"
    ).size()
    overall["pair_fraction"] = overall["pairs"] / total_pairs
    overall["query_fraction_with_action"] = [
        row.queries_with_action / query_totals.loc[row.dataset_context] for row in overall.itertuples()
    ]

    by_axis = (
        combined.groupby(["dataset_context", "query_evidence_axis", "review_action"], as_index=False)
        .agg(
            pairs=("review_action", "size"),
            queries_with_action=("query_image_evidence_id", "nunique"),
            mean_pair_comparability=("pair_comparability_score", "mean"),
            mean_weakest_image_utility=("weakest_image_utility_score", "mean"),
            mean_conflict=("descriptor_evidence_conflict_score", "mean"),
        )
        .sort_values(["dataset_context", "query_evidence_axis", "review_action"])
    )
    axis_pair_totals = by_axis.groupby(["dataset_context", "query_evidence_axis"])["pairs"].transform("sum")
    by_axis["pair_fraction_within_axis"] = by_axis["pairs"] / axis_pair_totals
    return overall, by_axis


def write_report(
    bobcat_summary: pd.DataFrame,
    comparison: pd.DataFrame,
    axis_comparison: pd.DataFrame,
    thresholds: dict[str, float],
    audit: dict[str, Any],
) -> None:
    lines = [
        "# Phase 15E Wild-to-Urban Transfer Stress Test",
        "",
        "Phase 15E applies the CzechLynx-calibrated evidence-routing policy to urban/peri-urban bobcat candidate pairs.",
        "",
        "## Boundary",
        "",
        "Bobcat individual identities are unavailable in this dataset. These outputs measure review-readiness, non-comparable pressure, species-level-only pressure, and descriptor-evidence conflict pressure. They do not measure bobcat false-match accuracy.",
        "",
        "## Czech-Calibrated Score Thresholds",
        "",
        f"- Accept score threshold from Czech top 5%: {thresholds['hgb_accept_score_threshold_czech_top5pct']:.6f}",
        f"- Review score threshold from Czech top 20%: {thresholds['hgb_review_score_threshold_czech_top20pct']:.6f}",
        "",
        "## Bobcat Action Summary",
        "",
        "| Action | Pairs | Pair fraction | Query fraction | Mean comparability | Mean conflict |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for _, row in bobcat_summary.iterrows():
        lines.append(
            f"| {row['review_action']} | {int(row['pairs'])} | {row['pair_fraction']:.3f} | "
            f"{row['query_fraction_with_action']:.3f} | {row['mean_pair_comparability']:.3f} | "
            f"{row['mean_conflict']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Wild vs Urban Action Distribution",
            "",
            "| Dataset | Action | Pair fraction | Query fraction | Mean conflict |",
            "|---|---|---:|---:|---:|",
        ]
    )
    for _, row in comparison.sort_values(["dataset_context", "review_action"]).iterrows():
        lines.append(
            f"| {row['dataset_context']} | {row['review_action']} | {row['pair_fraction']:.3f} | "
            f"{row['query_fraction_with_action']:.3f} | {row['mean_conflict']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This transfer result is a stress test, not identity validation. In the current run, bobcat does not simply look worse on every evidence route. Its main pressure appears as a large defer band: many urban/peri-urban candidate pairs have some evidence support, but not enough to be accepted or prioritized for confident review under the Czech-calibrated policy.",
            "",
            "This is a useful diagnostic result. It suggests that the wild-to-urban shift may be a routing-threshold and ambiguity-pressure problem, not only a low-quality or non-comparable-image problem.",
            "",
            "The scientific role is to complete the project chain:",
            "",
            "```text",
            "image-level evidence shift -> pair-level comparability shift -> retrieval/review contamination pressure",
            "```",
            "",
            "## Outputs",
            "",
            f"- Bobcat top-k candidates: `{audit['outputs']['bobcat_topk']}`",
            f"- Bobcat routing table: `{audit['outputs']['bobcat_routing']}`",
            f"- Bobcat action summary: `{audit['outputs']['bobcat_action_summary']}`",
            f"- Wild/urban comparison: `{audit['outputs']['wild_urban_comparison']}`",
            f"- Evidence-axis comparison: `{audit['outputs']['evidence_axis_comparison']}`",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    image = pd.read_csv(args.image_evidence, low_memory=False)
    czech_routing = pd.read_csv(args.czech_routing_input, low_memory=False)
    model, thresholds = fit_czech_model(czech_routing, args.seed)
    bobcat_images, vectors = load_bobcat_embeddings(image, args.embeddings)
    topk = build_topk_candidates(bobcat_images, vectors, TOP_K)
    bobcat_routing = add_pair_features(topk, image)
    bobcat_routing = assign_actions(bobcat_routing, model, thresholds)
    bobcat_summary = summarize_actions(bobcat_routing, "phase15e_review_action", "urban_bobcat_identity_unknown")
    bobcat_query_summary = summarize_queries(bobcat_routing)
    comparison, axis_comparison = compare_with_czech(args.czech_action_table, bobcat_routing)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    topk.to_csv(BOBCAT_TOPK, index=False)
    bobcat_routing.to_csv(BOBCAT_ROUTING, index=False)
    bobcat_summary.to_csv(BOBCAT_ACTION_SUMMARY, index=False)
    bobcat_query_summary.to_csv(BOBCAT_QUERY_SUMMARY, index=False)
    comparison.to_csv(WILD_URBAN_COMPARISON, index=False)
    axis_comparison.to_csv(EVIDENCE_AXIS_COMPARISON, index=False)

    audit = {
        "status": "pass",
        "script": rel(Path(__file__)),
        "image_evidence": rel(args.image_evidence),
        "embeddings": rel(args.embeddings),
        "czech_routing_input": rel(args.czech_routing_input),
        "czech_action_table": rel(args.czech_action_table),
        "output_dir": rel(args.output_dir),
        "top_k": TOP_K,
        "bobcat_images": int(len(bobcat_images)),
        "bobcat_candidate_pairs": int(len(bobcat_routing)),
        "bobcat_queries": int(bobcat_routing["query_image_evidence_id"].nunique()),
        "bobcat_action_counts": bobcat_routing["phase15e_review_action"].value_counts().to_dict(),
        "thresholds": thresholds,
        "outputs": {
            "bobcat_topk": rel(BOBCAT_TOPK),
            "bobcat_routing": rel(BOBCAT_ROUTING),
            "bobcat_action_summary": rel(BOBCAT_ACTION_SUMMARY),
            "bobcat_query_summary": rel(BOBCAT_QUERY_SUMMARY),
            "wild_urban_comparison": rel(WILD_URBAN_COMPARISON),
            "evidence_axis_comparison": rel(EVIDENCE_AXIS_COMPARISON),
            "report": rel(REPORT_MD),
        },
        "claim_boundary": (
            "Bobcat identity labels unavailable; outputs are transfer stress, review-readiness, "
            "non-comparable pressure, species-level-only pressure, and descriptor-evidence conflict diagnostics only."
        ),
    }
    AUDIT_JSON.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    write_report(bobcat_summary, comparison, axis_comparison, thresholds, audit)
    return audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image-evidence", type=Path, default=IMAGE_EVIDENCE)
    parser.add_argument("--embeddings", type=Path, default=EMBEDDINGS)
    parser.add_argument("--czech-routing-input", type=Path, default=CZECH_ROUTING_INPUT)
    parser.add_argument("--czech-action-table", type=Path, default=CZECH_ACTION_TABLE)
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    return parser.parse_args()


def main() -> int:
    audit = run(parse_args())
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
