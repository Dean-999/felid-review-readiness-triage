#!/usr/bin/env python3
"""Build Phase 15 PF-ERI/quality hybrid routing policies.

Input is the Phase 15 CzechLynx fixed-descriptor top-k benchmark. This script
adds pair-level evidence features and evaluates routing policies over the same
candidate lists. No model is trained.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE14_DIR = PROJECT_ROOT / "outputs/phase14"
PHASE15_DIR = PROJECT_ROOT / "outputs/phase15"
IMAGE_EVIDENCE = PHASE14_DIR / "phase14_algorithm_inputs/phase14_2x2_image_evidence_table.csv"
QUERY_DIR = PHASE15_DIR / "query_level_benchmark"
TOPK_INPUT = QUERY_DIR / "phase15_czechlynx_query_topk_candidates.csv"
OUT_DIR = PHASE15_DIR / "hybrid_routing_policy"
ROUTING_INPUT = OUT_DIR / "phase15_czechlynx_candidate_routing_input.csv"
POLICY_EVAL = OUT_DIR / "phase15_czechlynx_hybrid_policy_evaluation.csv"
PARETO_TABLE = OUT_DIR / "phase15_czechlynx_hybrid_policy_pareto.csv"
AUDIT_JSON = OUT_DIR / "phase15_hybrid_routing_policy_audit.json"
REPORT_MD = OUT_DIR / "phase15_hybrid_routing_policy_report.md"

PAIR_SCORE_WEIGHTS = {
    "weakest_image_utility_score": 0.20,
    "side_comparability_score": 0.22,
    "pattern_pair_score": 0.18,
    "body_visibility_pair_score": 0.12,
    "blur_pair_score": 0.10,
    "occlusion_pair_score": 0.08,
    "detector_geometry_pair_score": 0.10,
}
QUALITY_THRESHOLDS = [0.20, 0.30, 0.40, 0.50, 0.60, 0.70]
PF_ERI_THRESHOLDS = [0.20, 0.30, 0.40, 0.50, 0.60, 0.70]
CONFLICT_THRESHOLDS = [0.40, 0.55, 0.70, 0.85]
SUMMARY_K = [1, 5, 10, 20, 50]
HYBRID_RANK_CUTOFFS = [5, 10, 20, 50]
RERANK_CONFIGS = {
    "rerank_descriptor_dominant": {
        "descriptor": 0.75,
        "pair": 0.10,
        "quality": 0.10,
        "conflict": 0.10,
    },
    "rerank_balanced": {
        "descriptor": 0.60,
        "pair": 0.20,
        "quality": 0.15,
        "conflict": 0.15,
    },
    "rerank_evidence_conservative": {
        "descriptor": 0.50,
        "pair": 0.25,
        "quality": 0.20,
        "conflict": 0.20,
    },
    "rerank_conflict_aware": {
        "descriptor": 0.65,
        "pair": 0.15,
        "quality": 0.10,
        "conflict": 0.25,
    },
}

REQUIRED_TOPK_COLUMNS = {
    "query_image_evidence_id",
    "candidate_image_evidence_id",
    "rank",
    "descriptor_similarity",
    "same_identity",
}
REQUIRED_IMAGE_COLUMNS = {
    "phase14_image_evidence_id",
    "environment_axis",
    "species_axis",
    "evidence_axis",
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
}


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def require_columns(frame: pd.DataFrame, required: set[str], source: Path) -> None:
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"{rel(source)} missing required columns: {missing}")


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


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


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    topk = pd.read_csv(TOPK_INPUT, low_memory=False)
    image = pd.read_csv(IMAGE_EVIDENCE, low_memory=False)
    require_columns(topk, REQUIRED_TOPK_COLUMNS, TOPK_INPUT)
    require_columns(image, REQUIRED_IMAGE_COLUMNS, IMAGE_EVIDENCE)
    image = image[image["species_axis"].eq("czechlynx")].copy()
    if image["phase14_image_evidence_id"].duplicated().any():
        raise ValueError("Duplicate phase14_image_evidence_id in image evidence table")
    return topk, image


def build_routing_input(topk: pd.DataFrame, image: pd.DataFrame) -> pd.DataFrame:
    recomputed_columns = [
        "query_evidence_axis",
        "candidate_evidence_axis",
        "pair_evidence_axis_relation",
        "query_source_quadrant",
        "candidate_source_quadrant",
        "query_image_utility_score",
        "candidate_image_utility_score",
        "weakest_image_utility_score",
        "query_md_confidence",
        "candidate_md_confidence",
        "query_md_area_fraction",
        "candidate_md_area_fraction",
        "query_detector_geometry_score",
        "candidate_detector_geometry_score",
    ]
    topk = topk.drop(columns=[column for column in recomputed_columns if column in topk.columns]).copy()
    feature_cols = [
        "phase14_image_evidence_id",
        "environment_axis",
        "species_axis",
        "evidence_axis",
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
        raise ValueError(f"Missing image evidence features for {int(missing.sum())} candidate pairs")

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
    out["evidence_axis_mismatch"] = np.where(out["pair_evidence_axis_relation"].eq("same_axis"), "no", "yes")
    out["query_image_utility_score"] = numeric(out["query_image_evidence_utility_score"])
    out["candidate_image_utility_score"] = numeric(out["candidate_image_evidence_utility_score"])
    out["weakest_image_utility_score"] = np.minimum(
        out["query_image_utility_score"], out["candidate_image_utility_score"]
    )
    out["mean_image_utility_score"] = (out["query_image_utility_score"] + out["candidate_image_utility_score"]) / 2
    out["query_pattern_score"] = numeric(out["query_pattern_evidence_score"])
    out["candidate_pattern_score"] = numeric(out["candidate_pattern_evidence_score"])
    out["pattern_pair_score"] = np.minimum(out["query_pattern_score"], out["candidate_pattern_score"])
    out["query_side_score"] = numeric(out["query_side_flank_evidence_score"])
    out["candidate_side_score"] = numeric(out["candidate_side_flank_evidence_score"])
    out["side_direction_compatibility"] = side_direction
    out["side_comparability_score"] = np.minimum(out["query_side_score"], out["candidate_side_score"]) * side_direction
    out["query_body_score"] = numeric(out["query_body_visibility_score"])
    out["candidate_body_score"] = numeric(out["candidate_body_visibility_score"])
    out["body_visibility_pair_score"] = np.minimum(out["query_body_score"], out["candidate_body_score"])
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
    score = (score - 0.08 * out["edge_touch_pair_penalty"].astype(float)).clip(0, 1)
    out["pair_comparability_score"] = score
    out["pair_risk_score"] = 1 - score
    out["pair_admissibility_band"] = out["pair_comparability_score"].map(pair_band)
    out["descriptor_rank_support_score"] = ((51 - numeric(out["rank"])) / 50).clip(0, 1)
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
    return out[keep]


def summarize_policy(policy_id: str, policy_family: str, frame: pd.DataFrame, retain_mask: pd.Series, note: str) -> dict[str, Any]:
    eligible_queries = frame["query_image_evidence_id"].nunique()
    retained = frame[retain_mask].copy()
    per_query = retained.groupby("query_image_evidence_id")["same_identity"].agg(
        retained_pairs="size",
        retained_positive=lambda s: int(s.eq("yes").sum()),
        retained_false=lambda s: int(s.eq("no").sum()),
    )
    all_queries = pd.DataFrame(index=frame["query_image_evidence_id"].drop_duplicates())
    per_query = all_queries.join(per_query).fillna(0)
    hit = per_query["retained_positive"] > 0
    return {
        "policy_id": policy_id,
        "policy_family": policy_family,
        "eligible_queries": int(eligible_queries),
        "retained_pairs": int(len(retained)),
        "retained_pair_coverage": float(len(retained) / max(len(frame), 1)),
        "query_coverage": float((per_query["retained_pairs"] > 0).mean()) if len(per_query) else np.nan,
        "queries_with_positive_retained": int(hit.sum()),
        "hit_rate": float(hit.mean()) if len(hit) else np.nan,
        "mean_retained_pairs_per_query": float(per_query["retained_pairs"].mean()) if len(per_query) else np.nan,
        "mean_false_retained_per_query": float(per_query["retained_false"].mean()) if len(per_query) else np.nan,
        "median_false_retained_per_query": float(per_query["retained_false"].median()) if len(per_query) else np.nan,
        "mean_positive_retained_per_query": float(per_query["retained_positive"].mean()) if len(per_query) else np.nan,
        "false_rate_among_retained": float(retained["same_identity"].eq("no").mean()) if len(retained) else np.nan,
        "mean_pair_comparability_retained": float(retained["pair_comparability_score"].mean()) if len(retained) else np.nan,
        "mean_conflict_retained": float(retained["descriptor_evidence_conflict_score"].mean()) if len(retained) else np.nan,
        "note": note,
    }


def evaluate_policies(routing: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for k in SUMMARY_K:
        mask = numeric(routing["rank"]) <= k
        rows.append(
            summarize_policy(
                f"descriptor_top_{k}",
                "descriptor_only",
                routing,
                mask,
                f"Raw descriptor top-{k} reference.",
            )
        )

    for threshold in QUALITY_THRESHOLDS:
        mask = numeric(routing["weakest_image_utility_score"]) >= threshold
        rows.append(
            summarize_policy(
                f"quality_weakest_ge_{threshold:.2f}",
                "quality_only",
                routing,
                mask,
                "Retain candidates by weakest-image evidence utility only.",
            )
        )

    for threshold in PF_ERI_THRESHOLDS:
        mask = numeric(routing["pair_comparability_score"]) >= threshold
        rows.append(
            summarize_policy(
                f"pf_eri_pair_ge_{threshold:.2f}",
                "pf_eri_only",
                routing,
                mask,
                "Retain candidates by PF-ERI pair comparability only.",
            )
        )

    for rank_cutoff in HYBRID_RANK_CUTOFFS:
        rank_mask = numeric(routing["rank"]) <= rank_cutoff
        for pair_threshold in PF_ERI_THRESHOLDS:
            for quality_threshold in QUALITY_THRESHOLDS:
                for conflict_threshold in CONFLICT_THRESHOLDS:
                    mask = (
                        rank_mask
                        & (numeric(routing["pair_comparability_score"]) >= pair_threshold)
                        & (numeric(routing["weakest_image_utility_score"]) >= quality_threshold)
                        & (numeric(routing["descriptor_evidence_conflict_score"]) <= conflict_threshold)
                    )
                    rows.append(
                        summarize_policy(
                            f"hybrid_top_{rank_cutoff}_pair_{pair_threshold:.2f}_quality_{quality_threshold:.2f}_conflict_le_{conflict_threshold:.2f}",
                            "pf_eri_quality_hybrid",
                            routing,
                            mask,
                            "Retain descriptor-top candidates only when pair comparability and weakest-image quality pass and descriptor-evidence conflict is controlled.",
                    )
                )

    for config_id, weights in RERANK_CONFIGS.items():
        score = (
            weights["descriptor"] * numeric(routing["descriptor_rank_support_score"])
            + weights["pair"] * numeric(routing["pair_comparability_score"])
            + weights["quality"] * numeric(routing["weakest_image_utility_score"])
            - weights["conflict"] * numeric(routing["descriptor_evidence_conflict_score"])
        )
        rerank = score.groupby(routing["query_image_evidence_id"]).rank(method="first", ascending=False)
        for k in SUMMARY_K:
            mask = rerank <= k
            rows.append(
                summarize_policy(
                    f"{config_id}_top_{k}",
                    "pf_eri_quality_rerank",
                    routing,
                    mask,
                    "Rerank descriptor top-50 candidates using descriptor support, PF-ERI pair comparability, weakest-image quality, and conflict penalty.",
                )
            )
    return pd.DataFrame(rows)


def pareto_frontier(policy: pd.DataFrame) -> pd.DataFrame:
    candidates = policy[policy["query_coverage"] > 0].copy()
    candidates = candidates.sort_values(
        ["hit_rate", "mean_false_retained_per_query", "retained_pair_coverage"],
        ascending=[False, True, True],
    )
    keep = []
    best_false = float("inf")
    best_coverage = float("inf")
    for idx, row in candidates.iterrows():
        false_burden = float(row["mean_false_retained_per_query"])
        coverage = float(row["retained_pair_coverage"])
        if false_burden <= best_false or coverage <= best_coverage:
            keep.append(idx)
            best_false = min(best_false, false_burden)
            best_coverage = min(best_coverage, coverage)
    return candidates.loc[keep].reset_index(drop=True)


def write_report(policy: pd.DataFrame, pareto: pd.DataFrame, audit: dict[str, Any]) -> None:
    def best(family: str) -> pd.Series:
        frame = policy[policy["policy_family"].eq(family)].copy()
        frame = frame[frame["query_coverage"] >= 0.10]
        if frame.empty:
            return pd.Series(dtype=object)
        return frame.sort_values(["hit_rate", "mean_false_retained_per_query"], ascending=[False, True]).iloc[0]

    lines = [
        "# Phase 15 Hybrid Routing Policy",
        "",
        "This evaluates descriptor-only, quality-only, PF-ERI-only, and PF-ERI plus quality hybrid routing over the same CzechLynx top-50 descriptor candidate lists. No model is trained.",
        "",
        "## Audit",
        "",
        f"- Routing input rows: {audit['routing_input_rows']}",
        f"- Queries: {audit['queries']}",
        f"- Positive candidate rows: {audit['positive_candidate_rows']}",
        f"- False candidate rows: {audit['false_candidate_rows']}",
        "",
        "## Best Policy By Family",
        "",
        "| Family | Policy | query coverage | hit rate | mean false/query | retained coverage |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for family in [
        "descriptor_only",
        "quality_only",
        "pf_eri_only",
        "pf_eri_quality_hybrid",
        "pf_eri_quality_rerank",
    ]:
        row = best(family)
        if row.empty:
            continue
        lines.append(
            f"| {family} | `{row['policy_id']}` | {float(row['query_coverage']):.3f} | "
            f"{float(row['hit_rate']):.3f} | {float(row['mean_false_retained_per_query']):.3f} | "
            f"{float(row['retained_pair_coverage']):.3f} |"
        )

    lines.extend(
        [
            "",
            "## Same-K Rerank Check",
            "",
            "| k | descriptor hit | best rerank hit | descriptor false/query | best rerank false/query |",
            "|---:|---:|---:|---:|---:|",
        ]
    )
    for k in [1, 5, 10, 20]:
        descriptor = policy[policy["policy_id"].eq(f"descriptor_top_{k}")].iloc[0]
        rerank = (
            policy[
                policy["policy_family"].eq("pf_eri_quality_rerank")
                & policy["policy_id"].str.endswith(f"_top_{k}")
            ]
            .sort_values(["hit_rate", "mean_false_retained_per_query"], ascending=[False, True])
            .iloc[0]
        )
        lines.append(
            f"| {k} | {float(descriptor['hit_rate']):.3f} | {float(rerank['hit_rate']):.3f} | "
            f"{float(descriptor['mean_false_retained_per_query']):.3f} | "
            f"{float(rerank['mean_false_retained_per_query']):.3f} |"
        )
    lines.extend(
        [
            "",
            "## Technical Interpretation",
            "",
            "Fixed hand-written evidence gates are not strong enough to replace descriptor top-k. Evidence-aware reranking gives only small gains in some mid-k settings and hurts top-1 when evidence weights are too strong. The next defensible upgrade is a held-out query-split calibrated learning-to-rank model or constrained monotonic tabular model, compared against descriptor-only, quality-only, PF-ERI-only, and random/coverage-matched controls.",
            "",
            "## Interpretation Boundary",
            "",
            "This is CzechLynx known-ID query-level routing. It validates false-candidate burden and positive retention for CzechLynx only. Bobcat transfer remains review-pressure stress testing until identity or audited pair labels exist.",
            "",
            f"Pareto candidate policies written: {len(pareto)}",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    topk, image = load_inputs()
    routing = build_routing_input(topk, image)
    policy = evaluate_policies(routing)
    pareto = pareto_frontier(policy)

    routing.to_csv(ROUTING_INPUT, index=False)
    policy.to_csv(POLICY_EVAL, index=False)
    pareto.to_csv(PARETO_TABLE, index=False)
    audit = {
        "status": "pass",
        "script": rel(Path(__file__)),
        "topk_input": rel(TOPK_INPUT),
        "image_evidence_table": rel(IMAGE_EVIDENCE),
        "routing_input": rel(ROUTING_INPUT),
        "policy_evaluation": rel(POLICY_EVAL),
        "pareto_table": rel(PARETO_TABLE),
        "routing_input_rows": int(len(routing)),
        "queries": int(routing["query_image_evidence_id"].nunique()),
        "positive_candidate_rows": int(routing["same_identity"].eq("yes").sum()),
        "false_candidate_rows": int(routing["same_identity"].eq("no").sum()),
        "policy_rows": int(len(policy)),
        "pareto_rows": int(len(pareto)),
        "claim_boundary": "CzechLynx known-ID routing policy; no model training; no bobcat identity validation.",
    }
    AUDIT_JSON.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    write_report(policy, pareto, audit)
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
