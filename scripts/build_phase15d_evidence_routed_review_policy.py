#!/usr/bin/env python3
"""Build Phase 15D evidence-routed review policy tables.

This script turns Phase 15C repeated validation into an operational review
routing table. It fits a final CzechLynx calibrated ranker on all available
known-ID candidate pairs for score export only. Validation evidence still comes
from Phase 15C repeated held-out query splits.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_CSV = PROJECT_ROOT / "outputs/phase15/hybrid_routing_policy/phase15_czechlynx_candidate_routing_input.csv"
PHASE15C_RISK = PROJECT_ROOT / "outputs/phase15/repeated_ranker_validation/phase15c_risk_coverage_curve.csv"
OUT_DIR = PROJECT_ROOT / "outputs/phase15/evidence_routed_review_policy"

ROUTING_TABLE = OUT_DIR / "phase15d_evidence_routed_review_table.csv"
ACTION_SUMMARY = OUT_DIR / "phase15d_review_action_summary.csv"
QUERY_SUMMARY = OUT_DIR / "phase15d_query_review_summary.csv"
OPERATING_POINTS = OUT_DIR / "phase15d_operating_points_from_phase15c.csv"
AUDIT_JSON = OUT_DIR / "phase15d_evidence_routed_review_policy_audit.json"
REPORT_MD = OUT_DIR / "phase15d_evidence_routed_review_policy_report.md"

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

ACTION_ORDER = {
    "accept": 0,
    "review": 1,
    "defer": 2,
    "species_level_only": 3,
    "non_comparable": 4,
}

DEFAULT_SEED = 20260622
ACCEPT_COVERAGE = 0.05
REVIEW_COVERAGE = 0.20


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def numeric_frame(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = frame[columns].apply(pd.to_numeric, errors="coerce")
    return out.fillna(out.median(numeric_only=True)).fillna(0.0)


def load_operating_points(risk_path: Path) -> pd.DataFrame:
    risk = pd.read_csv(risk_path)
    wanted = risk[
        risk["policy_id"].isin(["descriptor_only", "logistic_calibrated_ranker", "hist_gradient_boosting_ranker"])
        & risk["target_pair_coverage"].isin([ACCEPT_COVERAGE, REVIEW_COVERAGE])
    ].copy()
    grouped = (
        wanted.groupby(["policy_id", "target_pair_coverage"], as_index=False)
        .agg(
            hit_rate_mean=("hit_rate", "mean"),
            hit_rate_ci95_low=("hit_rate", lambda s: float(s.quantile(0.025))),
            hit_rate_ci95_high=("hit_rate", lambda s: float(s.quantile(0.975))),
            query_coverage_mean=("query_coverage", "mean"),
            mean_false_retained_per_query_mean=("mean_false_retained_per_query", "mean"),
            mean_positive_retained_per_query_mean=("mean_positive_retained_per_query", "mean"),
            repeated_score_threshold_mean=("score_threshold", "mean"),
            repeated_score_threshold_ci95_low=("score_threshold", lambda s: float(s.quantile(0.025))),
            repeated_score_threshold_ci95_high=("score_threshold", lambda s: float(s.quantile(0.975))),
            repeats=("split_id", "nunique"),
        )
        .sort_values(["policy_id", "target_pair_coverage"])
    )
    return grouped


def add_scores(data: pd.DataFrame, seed: int) -> pd.DataFrame:
    out = data.copy()
    out["label"] = out["same_identity"].eq("yes").astype(int)
    out["descriptor_only_score"] = pd.to_numeric(out["descriptor_similarity"], errors="coerce").fillna(0.0)
    x = numeric_frame(out, FEATURE_COLUMNS)
    y = out["label"].to_numpy()
    model = HistGradientBoostingClassifier(
        max_iter=160,
        learning_rate=0.05,
        l2_regularization=0.05,
        random_state=seed,
    )
    model.fit(x, y)
    out["hist_gradient_boosting_ranker_score"] = model.predict_proba(x)[:, 1]
    return out


def quantile_threshold(frame: pd.DataFrame, score_column: str, coverage: float) -> float:
    return float(frame[score_column].quantile(1.0 - coverage))


def assign_actions(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, float]]:
    out = frame.copy()
    score = "hist_gradient_boosting_ranker_score"
    accept_threshold = quantile_threshold(out, score, ACCEPT_COVERAGE)
    review_threshold = quantile_threshold(out, score, REVIEW_COVERAGE)

    pair_comparability = pd.to_numeric(out["pair_comparability_score"], errors="coerce").fillna(0.0)
    weakest_utility = pd.to_numeric(out["weakest_image_utility_score"], errors="coerce").fillna(0.0)
    conflict = pd.to_numeric(out["descriptor_evidence_conflict_score"], errors="coerce").fillna(0.0)
    hgb_score = pd.to_numeric(out[score], errors="coerce").fillna(0.0)

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
        & (hgb_score >= accept_threshold)
        & (pair_comparability >= 0.65)
        & (weakest_utility >= 0.55)
        & (conflict < 0.50)
    )
    review = (
        ~non_comparable
        & ~species_level
        & ~accept
        & (hgb_score >= review_threshold)
        & (pair_comparability >= 0.45)
        & (weakest_utility >= 0.35)
    )

    action = np.select(
        [non_comparable, species_level, accept, review],
        ["non_comparable", "species_level_only", "accept", "review"],
        default="defer",
    )
    out["phase15d_review_action"] = action
    out["phase15d_action_rank"] = out["phase15d_review_action"].map(ACTION_ORDER)
    out["phase15d_action_score"] = hgb_score
    out["phase15d_accept_score_threshold"] = accept_threshold
    out["phase15d_review_score_threshold"] = review_threshold
    out["phase15d_action_claim_boundary"] = (
        "CzechLynx score export from all-data fit; validation evidence comes from Phase 15C repeated query splits."
    )
    thresholds = {
        "hgb_accept_score_threshold_top5pct_full_fit": accept_threshold,
        "hgb_review_score_threshold_top20pct_full_fit": review_threshold,
    }
    return out, thresholds


def summarize_actions(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    total_rows = max(len(frame), 1)
    total_queries = max(frame["query_image_evidence_id"].nunique(), 1)
    for action, part in frame.groupby("phase15d_review_action", sort=False):
        per_query = part.groupby("query_image_evidence_id")["same_identity"].agg(
            retained_pairs="size",
            retained_positive=lambda s: int(s.eq("yes").sum()),
            retained_false=lambda s: int(s.eq("no").sum()),
        )
        rows.append(
            {
                "phase15d_review_action": action,
                "action_rank": ACTION_ORDER[action],
                "pairs": int(len(part)),
                "pair_fraction": float(len(part) / total_rows),
                "queries_with_action": int(part["query_image_evidence_id"].nunique()),
                "query_fraction_with_action": float(part["query_image_evidence_id"].nunique() / total_queries),
                "positive_pairs": int(part["same_identity"].eq("yes").sum()),
                "false_pairs": int(part["same_identity"].eq("no").sum()),
                "positive_pair_rate": float(part["same_identity"].eq("yes").mean()),
                "mean_positive_per_query_with_action": float(per_query["retained_positive"].mean()),
                "mean_false_per_query_with_action": float(per_query["retained_false"].mean()),
                "mean_hgb_score": float(part["hist_gradient_boosting_ranker_score"].mean()),
                "mean_pair_comparability": float(pd.to_numeric(part["pair_comparability_score"], errors="coerce").mean()),
                "mean_weakest_image_utility": float(pd.to_numeric(part["weakest_image_utility_score"], errors="coerce").mean()),
                "mean_conflict": float(pd.to_numeric(part["descriptor_evidence_conflict_score"], errors="coerce").mean()),
            }
        )
    return pd.DataFrame(rows).sort_values("action_rank")


def summarize_queries(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for query_id, part in frame.groupby("query_image_evidence_id", sort=False):
        action_counts = part["phase15d_review_action"].value_counts().to_dict()
        best = part.sort_values(
            ["phase15d_action_rank", "phase15d_action_score", "descriptor_similarity"],
            ascending=[True, False, False],
        ).iloc[0]
        rows.append(
            {
                "query_image_evidence_id": query_id,
                "query_identity_label": best["query_identity_label"],
                "query_evidence_axis": best["query_evidence_axis"],
                "best_candidate_image_evidence_id": best["candidate_image_evidence_id"],
                "best_candidate_identity_label": best["candidate_identity_label"],
                "best_same_identity": best["same_identity"],
                "best_review_action": best["phase15d_review_action"],
                "best_hgb_score": float(best["hist_gradient_boosting_ranker_score"]),
                "best_descriptor_similarity": float(best["descriptor_similarity"]),
                "accept_pairs": int(action_counts.get("accept", 0)),
                "review_pairs": int(action_counts.get("review", 0)),
                "defer_pairs": int(action_counts.get("defer", 0)),
                "species_level_only_pairs": int(action_counts.get("species_level_only", 0)),
                "non_comparable_pairs": int(action_counts.get("non_comparable", 0)),
            }
        )
    return pd.DataFrame(rows)


def write_report(
    action_summary: pd.DataFrame,
    operating_points: pd.DataFrame,
    thresholds: dict[str, float],
    audit: dict[str, Any],
) -> None:
    lines = [
        "# Phase 15D Evidence-Routed Review Policy",
        "",
        "Phase 15D converts repeated validation evidence into an operational review-routing table.",
        "",
        "## Boundary",
        "",
        "The final HGB/logistic scores in the routing table are fit on all CzechLynx known-ID candidate pairs for score export. They are not a new held-out validation result. Validation evidence comes from Phase 15C repeated held-out query splits.",
        "",
        "The action `accept` means a high-priority candidate pair with strong evidence support for expert review. It is not automatic identity assignment.",
        "",
        "## Full-Fit Score Thresholds",
        "",
        f"- HGB top 5% accept threshold: {thresholds['hgb_accept_score_threshold_top5pct_full_fit']:.6f}",
        f"- HGB top 20% review threshold: {thresholds['hgb_review_score_threshold_top20pct_full_fit']:.6f}",
        "",
        "## Action Summary",
        "",
        "| Action | Pairs | Pair fraction | Positive pair rate | Mean false/query with action | Mean HGB score |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for _, row in action_summary.iterrows():
        lines.append(
            f"| {row['phase15d_review_action']} | {int(row['pairs'])} | "
            f"{row['pair_fraction']:.3f} | {row['positive_pair_rate']:.3f} | "
            f"{row['mean_false_per_query_with_action']:.3f} | {row['mean_hgb_score']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Phase 15C Operating Point Evidence",
            "",
            "| Policy | Coverage | Hit rate | Query coverage | False/query | Threshold mean |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for _, row in operating_points.iterrows():
        lines.append(
            f"| {row['policy_id']} | {row['target_pair_coverage']:.2f} | "
            f"{row['hit_rate_mean']:.3f} | {row['query_coverage_mean']:.3f} | "
            f"{row['mean_false_retained_per_query_mean']:.3f} | "
            f"{row['repeated_score_threshold_mean']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This is the first usable version of the PF-ERI Evidence-Routed Review Layer. It should be evaluated as a review-risk routing module after strong descriptor retrieval, not as a replacement Re-ID descriptor.",
            "",
            "The strongest current claim remains: PF-ERI/quality/conflict features provide stable candidate-reliability signal and can route candidate pairs into accept, review, defer, species-level-only, or non-comparable actions under explicit risk-coverage tradeoffs.",
            "",
            "## Outputs",
            "",
            f"- Routing table: `{audit['outputs']['routing_table']}`",
            f"- Action summary: `{audit['outputs']['action_summary']}`",
            f"- Query summary: `{audit['outputs']['query_summary']}`",
            f"- Operating points: `{audit['outputs']['operating_points']}`",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    data = pd.read_csv(args.input, low_memory=False)
    missing = sorted(set(FEATURE_COLUMNS) - set(data.columns))
    if missing:
        raise ValueError(f"Missing feature columns: {missing}")
    data = data[data["same_identity"].isin(["yes", "no"])].copy()

    scored = add_scores(data, args.seed)
    routed, thresholds = assign_actions(scored)
    action_summary = summarize_actions(routed)
    query_summary = summarize_queries(routed)
    operating_points = load_operating_points(args.phase15c_risk)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    routed.to_csv(ROUTING_TABLE, index=False)
    action_summary.to_csv(ACTION_SUMMARY, index=False)
    query_summary.to_csv(QUERY_SUMMARY, index=False)
    operating_points.to_csv(OPERATING_POINTS, index=False)

    audit = {
        "status": "pass",
        "script": rel(Path(__file__)),
        "input": rel(args.input),
        "phase15c_risk_input": rel(args.phase15c_risk),
        "output_dir": rel(args.output_dir),
        "rows": int(len(routed)),
        "queries": int(routed["query_image_evidence_id"].nunique()),
        "seed": int(args.seed),
        "feature_columns": FEATURE_COLUMNS,
        "action_counts": routed["phase15d_review_action"].value_counts().to_dict(),
        "thresholds": thresholds,
        "outputs": {
            "routing_table": rel(ROUTING_TABLE),
            "action_summary": rel(ACTION_SUMMARY),
            "query_summary": rel(QUERY_SUMMARY),
            "operating_points": rel(OPERATING_POINTS),
            "report": rel(REPORT_MD),
        },
        "claim_boundary": (
            "CzechLynx known-ID operational routing export; validation evidence remains Phase 15C repeated query splits; no bobcat identity validation."
        ),
        "accept_definition": "High-priority candidate for expert review, not automatic identity assignment.",
    }
    AUDIT_JSON.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    write_report(action_summary, operating_points, thresholds, audit)
    return audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=INPUT_CSV)
    parser.add_argument("--phase15c-risk", type=Path, default=PHASE15C_RISK)
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    return parser.parse_args()


def main() -> int:
    audit = run(parse_args())
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
