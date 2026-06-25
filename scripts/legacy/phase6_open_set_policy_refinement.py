#!/usr/bin/env python3
"""Phase 6 PF-ERI Control policy refinement.

This implements a constrained, interval-aware risk-coverage optimizer for
simulated open-set CzechLynx validation. Internal identities are used only to
construct identity-level splits. Public outputs are aggregate-only.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PAIR_SCORES = ROOT / "outputs/czechlynx/phase5/czechlynx_phase5_pair_eri_scores_internal.csv"
OPEN_SET_METRICS = ROOT / "outputs/czechlynx/phase6/tables/phase6_simulated_open_set_metrics.csv"
UNKNOWN_REJECTION = ROOT / "outputs/czechlynx/phase6/tables/phase6_unknown_rejection_metrics.csv"
OPEN_SET_COMPARISON = ROOT / "outputs/czechlynx/phase6/tables/phase6_open_set_policy_comparison.csv"
CALIBRATED_RISK = ROOT / "outputs/czechlynx/phase6/tables/phase6_calibrated_eri_risk_by_band.csv"
CLUSTERED_INTERVALS = ROOT / "outputs/czechlynx/phase6/uncertainty/phase6_clustered_bootstrap_intervals.csv"
ID_MAPPING = ROOT / "data/interim/czechlynx/czechlynx_expanded_125x4_internal_with_ids.csv"

OUT_TABLE_DIR = ROOT / "outputs/czechlynx/phase6/tables"
OUT_FIG_DIR = ROOT / "outputs/czechlynx/phase6/figures"
QC_DIR = ROOT / "outputs/czechlynx/qc"
REFINEMENT_OUT = OUT_TABLE_DIR / "phase6_pf_eri_policy_refinement.csv"
OPERATING_POINTS_OUT = OUT_TABLE_DIR / "phase6_pf_eri_operating_points.csv"
POLICY_SUMMARY_OUT = OUT_TABLE_DIR / "phase6_pf_eri_v2_policy_summary.csv"
FIGURE_OUT = OUT_FIG_DIR / "phase6_pf_eri_policy_frontier.png"
REPORT_OUT = QC_DIR / "phase6_pf_eri_policy_refinement_report.txt"

SEED = 20260612
N_SPLITS = 50
UNKNOWN_FRACTION = 0.20
RISK_TOLERANCES = [0.02, 0.05, 0.08, 0.10]
COVERAGE_FLOORS = [0.10, 0.15, 0.20, 0.25]
SIMILARITY_COLUMNS = {
    "megadescriptor": "megadescriptor_similarity",
    "resnet50": "resnet50_similarity",
}
SENSITIVE_OUTPUT_COLUMNS = {
    "unique_name",
    "working_individual_id",
    "identity",
    "internal_id",
    "review_image_path",
    "local_image_path",
    "path",
    "latitude",
    "longitude",
    "cell_code",
    "trap_id",
    "source",
    "date",
    "encounter",
    "query_image",
    "gallery_image",
    "_identity_a",
    "_identity_b",
}
SENSITIVE_VALUE_PATTERNS = (
    "/Users/",
    "data/interim",
    "working_individual_id",
    "review_image_path",
    "cell_code",
    "trap_id",
)
SENSITIVE_VALUE_REGEXES = (r"\blynx_\d+",)


@dataclass(frozen=True)
class PolicyResult:
    retained: pd.Series
    review: pd.Series
    cautious_review: pd.Series
    defer: pd.Series
    exclude: pd.Series
    policy_detail: str
    policy_stage: str


def band_from_score(value: float) -> str:
    if value >= 75:
        return "high"
    if value >= 55:
        return "medium"
    if value >= 35:
        return "low"
    return "unusable"


def require_inputs() -> None:
    required = [
        PAIR_SCORES,
        OPEN_SET_METRICS,
        UNKNOWN_REJECTION,
        OPEN_SET_COMPARISON,
        CALIBRATED_RISK,
        ID_MAPPING,
    ]
    for path in required:
        if not path.exists():
            raise FileNotFoundError(f"Missing required input: {path}")


def load_pairs() -> tuple[pd.DataFrame, bool]:
    require_inputs()
    pairs = pd.read_csv(PAIR_SCORES)
    required_cols = {
        "pair_id",
        "pair_type",
        "image_a_expanded_id",
        "image_b_expanded_id",
        "visual_only_eri",
        "model_support_score",
        "cross_model_agreement",
        "hybrid_eri",
        "visual_only_eri_band",
        "pair_side_comparable",
        "pair_any_uncertain",
        "pair_any_silhouette",
        *SIMILARITY_COLUMNS.values(),
    }
    missing = sorted(required_cols - set(pairs.columns))
    if missing:
        raise ValueError(f"Missing required pair-score columns: {missing}")

    mapping = pd.read_csv(ID_MAPPING, usecols=["expanded_image_id", "working_individual_id"])
    if mapping["expanded_image_id"].duplicated().any():
        raise ValueError("Internal mapping has duplicate expanded_image_id rows.")
    lookup = mapping.set_index("expanded_image_id")["working_individual_id"]
    pairs["_identity_a"] = pairs["image_a_expanded_id"].map(lookup)
    pairs["_identity_b"] = pairs["image_b_expanded_id"].map(lookup)
    if pairs[["_identity_a", "_identity_b"]].isna().any().any():
        raise ValueError("Could not reconstruct identity grouping for all pairs.")
    reconstructed_same = pairs["_identity_a"].eq(pairs["_identity_b"])
    if not reconstructed_same.eq(pairs["pair_type"].eq("same")).all():
        raise ValueError("Pair labels disagree with internal identity grouping.")

    clustered_available = CLUSTERED_INTERVALS.exists()
    return pairs, clustered_available


def choose_unknown_identities(identities: np.ndarray, rng: np.random.Generator) -> set[object]:
    unknown_count = max(2, int(round(len(identities) * UNKNOWN_FRACTION)))
    return set(rng.choice(identities, size=unknown_count, replace=False).tolist())


def split_candidates(pairs: pd.DataFrame, unknown_ids: set[object]) -> tuple[pd.DataFrame, pd.Series]:
    a_unknown = pairs["_identity_a"].isin(unknown_ids)
    b_unknown = pairs["_identity_b"].isin(unknown_ids)
    candidate_mask = (a_unknown ^ b_unknown) & pairs["pair_type"].eq("different")
    candidates = pairs.loc[candidate_mask].copy()
    if not candidates.empty:
        candidates["_unknown_query_key"] = np.where(
            candidates["_identity_a"].isin(unknown_ids),
            candidates["image_a_expanded_id"],
            candidates["image_b_expanded_id"],
        )
    known_known_mask = ~(a_unknown | b_unknown)
    return candidates, known_known_mask


def high_similarity_threshold(pairs: pd.DataFrame, known_known_mask: pd.Series, sim_col: str) -> float:
    train_values = pairs.loc[known_known_mask & pairs["pair_type"].eq("different"), sim_col]
    if train_values.empty:
        raise ValueError("Cannot estimate threshold from empty known-known different set.")
    return float(train_values.quantile(0.90))


def calibrated_visual_policy_by_tolerance(similarity_model: str, tau: float) -> str:
    risk = pd.read_csv(CALIBRATED_RISK)
    rows = risk[
        risk["score_name"].eq("visual_only_eri")
        & risk["similarity_model"].eq(similarity_model)
        & risk["band"].isin(["high", "medium", "low", "unusable"])
    ].copy()
    if rows.empty:
        raise ValueError(f"Missing calibrated visual-only ERI risk rows for {similarity_model}.")
    band_order = ["high", "medium", "low", "unusable"]
    rows["_band_order"] = rows["band"].map({b: i for i, b in enumerate(band_order)})
    rows = rows.sort_values("_band_order")
    total_pairs = float(rows["pair_count"].sum())
    best_policy = "exclude_all"
    best_coverage = -1.0
    for idx in range(1, len(band_order) + 1):
        keep = set(band_order[:idx])
        subset = rows[rows["band"].isin(keep)]
        coverage = float(subset["pair_count"].sum() / total_pairs) if total_pairs else 0.0
        risk_load = float(subset["high_similarity_different_pair_count"].sum() / total_pairs) if total_pairs else np.inf
        if risk_load <= tau and coverage > best_coverage:
            best_coverage = coverage
            best_policy = {
                ("high",): "keep_visual_high",
                ("high", "medium"): "keep_visual_high_medium",
                ("high", "medium", "low"): "keep_visual_high_medium_low",
                ("high", "medium", "low", "unusable"): "keep_all_visual_bands",
            }[tuple(band_order[:idx])]
    return best_policy


def empty_mask(candidates: pd.DataFrame, value: bool = False) -> pd.Series:
    return pd.Series(value, index=candidates.index)


def top_by_query(candidates: pd.DataFrame, score_col: str, base_mask: pd.Series | None = None) -> pd.Series:
    eligible = candidates if base_mask is None else candidates.loc[base_mask]
    mask = empty_mask(candidates)
    if eligible.empty:
        return mask
    top_idx = eligible.groupby("_unknown_query_key")[score_col].idxmax()
    mask.loc[top_idx] = True
    return mask


def policy_result(
    candidates: pd.DataFrame,
    policy_name: str,
    similarity_model: str,
    tau: float,
) -> PolicyResult:
    q = candidates["visual_only_eri"].astype(float)
    support = candidates["model_support_score"].astype(float)
    agreement = candidates["cross_model_agreement"].astype(float)
    hybrid = candidates["hybrid_eri"].astype(float)
    high = q.ge(75)
    medium_plus = q.ge(55)
    low = q.ge(35) & q.lt(55)
    unusable = q.lt(35)
    hard_exclude = (
        unusable
        | candidates["pair_any_silhouette"].astype(str).eq("yes")
        | candidates["visual_only_eri_band"].astype(str).eq("unusable")
    )

    if policy_name == "keep_all":
        retained = empty_mask(candidates, True)
        return PolicyResult(retained, retained.copy(), empty_mask(candidates), empty_mask(candidates), empty_mask(candidates), "review_all", "baseline")

    if policy_name == "raw_megadescriptor_top_candidate":
        retained = top_by_query(candidates, "megadescriptor_similarity")
        return PolicyResult(retained, retained.copy(), empty_mask(candidates), ~retained, empty_mask(candidates), "top_candidate_by_megadescriptor", "raw_similarity")

    if policy_name == "raw_resnet50_top_candidate":
        retained = top_by_query(candidates, "resnet50_similarity")
        return PolicyResult(retained, retained.copy(), empty_mask(candidates), ~retained, empty_mask(candidates), "top_candidate_by_resnet50", "raw_similarity")

    if policy_name == "pf_eri_high_only":
        retained = high
        return PolicyResult(retained, retained.copy(), empty_mask(candidates), ~retained & ~hard_exclude, hard_exclude & ~retained, "visual_only_eri_high", "visual_gate")

    if policy_name == "pf_eri_high_medium":
        retained = medium_plus
        return PolicyResult(retained, high, retained & ~high, low, hard_exclude, "visual_only_eri_high_or_medium", "visual_gate")

    if policy_name == "pf_eri_gate_then_megadescriptor_ranking":
        retained = top_by_query(candidates, "megadescriptor_similarity", medium_plus)
        return PolicyResult(retained, retained & high, retained & ~high, ~retained & ~hard_exclude, hard_exclude & ~retained, "qv_ge_55_then_top_megadescriptor", "visual_gate_then_model_support")

    if policy_name == "pf_eri_gate_then_resnet50_ranking":
        retained = top_by_query(candidates, "resnet50_similarity", medium_plus)
        return PolicyResult(retained, retained & high, retained & ~high, ~retained & ~hard_exclude, hard_exclude & ~retained, "qv_ge_55_then_top_resnet50", "visual_gate_then_model_support")

    if policy_name == "pf_eri_gate_then_hybrid_prioritization":
        retained = top_by_query(candidates, "hybrid_eri", medium_plus)
        return PolicyResult(retained, retained & high, retained & ~high, ~retained & ~hard_exclude, hard_exclude & ~retained, "qv_ge_55_then_top_hybrid_priority", "visual_gate_then_secondary_priority")

    if policy_name == "pf_eri_gate_then_cross_model_agreement":
        retained = medium_plus & agreement.ge(75)
        return PolicyResult(retained, retained & high, retained & ~high, ~retained & ~hard_exclude, hard_exclude & ~retained, "qv_ge_55_and_agreement_ge_75", "visual_gate_then_uncertainty_filter")

    if policy_name == "pf_eri_gate_then_calibrated_risk_tolerance":
        calibrated_policy = calibrated_visual_policy_by_tolerance(similarity_model, tau)
        keep_bands = {
            "exclude_all": set(),
            "keep_visual_high": {"high"},
            "keep_visual_high_medium": {"high", "medium"},
            "keep_visual_high_medium_low": {"high", "medium", "low"},
            "keep_all_visual_bands": {"high", "medium", "low", "unusable"},
        }[calibrated_policy]
        retained = candidates["visual_only_eri_band"].isin(keep_bands)
        return PolicyResult(retained, retained & high, retained & ~high, ~retained & ~hard_exclude, hard_exclude & ~retained, calibrated_policy, "visual_gate_then_calibrated_risk")

    if policy_name == "pf_eri_control_v2_staged_policy":
        review = high & support.ge(60) & agreement.ge(50)
        cautious = medium_plus & ~review & support.ge(40)
        retained = review | cautious
        defer = ~retained & ~hard_exclude
        exclude = hard_exclude & ~retained
        return PolicyResult(retained, review, cautious, defer, exclude, "review_high_support_else_cautious_medium_defer_exclude", "final_staged_policy")

    raise ValueError(f"Unknown policy: {policy_name}")


def evaluate_split_policy(
    split_id: str,
    candidates: pd.DataFrame,
    policy_name: str,
    similarity_model: str,
    sim_col: str,
    threshold: float,
    tau: float,
) -> dict[str, object]:
    result = policy_result(candidates, policy_name, similarity_model, tau)
    retained = candidates.loc[result.retained]
    original_count = int(len(candidates))
    retained_count = int(result.retained.sum())
    review_count = int(result.review.sum())
    cautious_count = int(result.cautious_review.sum())
    defer_count = int(result.defer.sum())
    exclude_count = int(result.exclude.sum())
    forced_mask = retained[sim_col].ge(threshold)
    forced_count = int(forced_mask.sum())
    query_count = int(candidates["_unknown_query_key"].nunique())
    retained_queries = int(retained["_unknown_query_key"].nunique()) if retained_count else 0
    forced_queries = int(retained.loc[forced_mask, "_unknown_query_key"].nunique()) if forced_count else 0
    sparse = original_count < 100 or query_count < 20 or retained_count < 20
    return {
        "split_id": split_id,
        "validation_name": "simulated_open_set_czechlynx_validation",
        "policy_name": policy_name,
        "policy_detail": result.policy_detail,
        "policy_stage": result.policy_stage,
        "risk_tolerance_context": tau,
        "similarity_model": similarity_model,
        "high_similarity_threshold": threshold,
        "unknown_query_count": query_count,
        "unknown_query_candidate_count": original_count,
        "retained_candidate_count": retained_count,
        "review_candidate_count": review_count,
        "cautious_review_candidate_count": cautious_count,
        "deferred_candidate_count": defer_count,
        "excluded_candidate_count": exclude_count,
        "retained_evidence_coverage": retained_count / original_count if original_count else np.nan,
        "defer_rate": defer_count / original_count if original_count else np.nan,
        "exclude_rate": exclude_count / original_count if original_count else np.nan,
        "evidence_removed": original_count - retained_count,
        "forced_match_proxy_count": forced_count,
        "forced_match_proxy_rate_among_retained": forced_count / retained_count if retained_count else np.nan,
        "total_risk_load": forced_count / original_count if original_count else np.nan,
        "query_with_retained_candidate_count": retained_queries,
        "query_rejected_or_deferred_count": query_count - retained_queries,
        "unknown_rejection_or_defer_rate": (query_count - retained_queries) / query_count if query_count else np.nan,
        "query_with_forced_match_proxy_count": forced_queries,
        "query_forced_match_proxy_rate": forced_queries / query_count if query_count else np.nan,
        "sparse_fold_caveat": "sparse_retained_or_candidate_pool" if sparse else "",
    }


def ci(values: pd.Series) -> tuple[float, float]:
    vals = values.dropna().to_numpy(dtype=float)
    if len(vals) == 0:
        return np.nan, np.nan
    if len(vals) == 1:
        return float(vals[0]), float(vals[0])
    return float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))


def summarize_refinement(rows: pd.DataFrame) -> pd.DataFrame:
    key_cols = ["policy_name", "policy_detail", "policy_stage", "similarity_model", "risk_tolerance_context"]
    keep = rows[rows["policy_name"].eq("keep_all")].set_index(["split_id", "similarity_model", "risk_tolerance_context"])
    raw_mega = rows[rows["policy_name"].eq("raw_megadescriptor_top_candidate")].set_index(["split_id", "similarity_model", "risk_tolerance_context"])
    raw_resnet = rows[rows["policy_name"].eq("raw_resnet50_top_candidate")].set_index(["split_id", "similarity_model", "risk_tolerance_context"])
    out_rows = []
    for keys, group in rows.groupby(key_cols, dropna=False):
        policy_name, policy_detail, policy_stage, sim_name, tau = keys
        indexed = group.set_index(["split_id", "similarity_model", "risk_tolerance_context"])
        base = indexed.join(
            keep[["forced_match_proxy_count", "retained_candidate_count", "total_risk_load"]],
            rsuffix="_keep_all",
        )
        base = base.join(
            raw_mega[["forced_match_proxy_count", "total_risk_load"]],
            rsuffix="_raw_megadescriptor",
        )
        base = base.join(
            raw_resnet[["forced_match_proxy_count", "total_risk_load"]],
            rsuffix="_raw_resnet50",
        )
        evidence_removed = base["retained_candidate_count_keep_all"] - base["retained_candidate_count"]
        risk_reduced = base["forced_match_proxy_count_keep_all"] - base["forced_match_proxy_count"]
        efficiency = np.where(evidence_removed > 0, risk_reduced / evidence_removed, np.nan)
        cov_low, cov_high = ci(group["retained_evidence_coverage"])
        risk_low, risk_high = ci(group["total_risk_load"])
        retained_risk_low, retained_risk_high = ci(group["forced_match_proxy_rate_among_retained"])
        out_rows.append(
            {
                "policy_name": policy_name,
                "policy_detail": policy_detail,
                "policy_stage": policy_stage,
                "similarity_model": sim_name,
                "risk_tolerance_context": tau,
                "split_count": int(group["split_id"].nunique()),
                "mean_unknown_query_candidate_count": float(group["unknown_query_candidate_count"].mean()),
                "mean_retained_candidate_count": float(group["retained_candidate_count"].mean()),
                "mean_review_candidate_count": float(group["review_candidate_count"].mean()),
                "mean_cautious_review_candidate_count": float(group["cautious_review_candidate_count"].mean()),
                "mean_deferred_candidate_count": float(group["deferred_candidate_count"].mean()),
                "mean_excluded_candidate_count": float(group["excluded_candidate_count"].mean()),
                "mean_coverage": float(group["retained_evidence_coverage"].mean()),
                "coverage_ci_lower_95": cov_low,
                "coverage_ci_upper_95": cov_high,
                "mean_forced_match_proxy_count": float(group["forced_match_proxy_count"].mean()),
                "mean_forced_match_proxy_rate_among_retained": float(group["forced_match_proxy_rate_among_retained"].mean(skipna=True)),
                "retained_risk_ci_lower_95": retained_risk_low,
                "retained_risk_ci_upper_95": retained_risk_high,
                "mean_total_risk_load": float(group["total_risk_load"].mean()),
                "risk_load_ci_lower_95": risk_low,
                "risk_load_ci_upper_95": risk_high,
                "mean_evidence_removed": float(group["evidence_removed"].mean()),
                "mean_risk_reduction_vs_keep_all": float(risk_reduced.mean()),
                "mean_risk_reduction_per_evidence_removed": float(np.nanmean(efficiency)) if np.isfinite(efficiency).any() else np.nan,
                "mean_risk_delta_vs_raw_megadescriptor_count": float((base["forced_match_proxy_count_raw_megadescriptor"] - base["forced_match_proxy_count"]).mean()),
                "mean_risk_delta_vs_raw_resnet50_count": float((base["forced_match_proxy_count_raw_resnet50"] - base["forced_match_proxy_count"]).mean()),
                "mean_risk_load_delta_vs_raw_megadescriptor": float((base["total_risk_load_raw_megadescriptor"] - base["total_risk_load"]).mean()),
                "mean_risk_load_delta_vs_raw_resnet50": float((base["total_risk_load_raw_resnet50"] - base["total_risk_load"]).mean()),
                "mean_unknown_rejection_or_defer_rate": float(group["unknown_rejection_or_defer_rate"].mean()),
                "mean_query_forced_match_proxy_rate": float(group["query_forced_match_proxy_rate"].mean()),
                "sparse_split_count": int(group["sparse_fold_caveat"].astype(bool).sum()),
            }
        )
    return pd.DataFrame(out_rows)


def operating_points(refinement: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in refinement.iterrows():
        tau = float(row["risk_tolerance_context"])
        for c_min in COVERAGE_FLOORS:
            point_feasible = bool(row["mean_total_risk_load"] <= tau and row["mean_coverage"] >= c_min)
            interval_feasible = bool(row["risk_load_ci_upper_95"] <= tau and row["coverage_ci_lower_95"] >= c_min)
            if interval_feasible:
                label = "accepted"
            elif point_feasible:
                label = "tentative"
            else:
                label = "rejected"
            rows.append(
                {
                    "policy_name": row["policy_name"],
                    "policy_detail": row["policy_detail"],
                    "policy_stage": row["policy_stage"],
                    "similarity_model": row["similarity_model"],
                    "risk_tolerance": tau,
                    "coverage_floor": c_min,
                    "coverage": row["mean_coverage"],
                    "coverage_ci_lower_95": row["coverage_ci_lower_95"],
                    "coverage_ci_upper_95": row["coverage_ci_upper_95"],
                    "retained_candidate_count": row["mean_retained_candidate_count"],
                    "deferred_candidate_count": row["mean_deferred_candidate_count"],
                    "excluded_candidate_count": row["mean_excluded_candidate_count"],
                    "forced_match_proxy_count": row["mean_forced_match_proxy_count"],
                    "forced_match_proxy_rate_among_retained": row["mean_forced_match_proxy_rate_among_retained"],
                    "total_risk_load": row["mean_total_risk_load"],
                    "risk_load_ci_lower_95": row["risk_load_ci_lower_95"],
                    "risk_load_ci_upper_95": row["risk_load_ci_upper_95"],
                    "risk_reduction_vs_keep_all": row["mean_risk_reduction_vs_keep_all"],
                    "evidence_removed": row["mean_evidence_removed"],
                    "risk_reduction_per_evidence_removed": row["mean_risk_reduction_per_evidence_removed"],
                    "coverage_at_risk_tolerance": row["mean_coverage"] if row["mean_total_risk_load"] <= tau else np.nan,
                    "risk_at_coverage_floor": row["mean_total_risk_load"] if row["mean_coverage"] >= c_min else np.nan,
                    "point_estimate_feasible": point_feasible,
                    "interval_aware_feasible": interval_feasible,
                    "acceptance_label": label,
                    "risk_delta_vs_raw_megadescriptor_count": row["mean_risk_delta_vs_raw_megadescriptor_count"],
                    "risk_delta_vs_raw_resnet50_count": row["mean_risk_delta_vs_raw_resnet50_count"],
                    "sparse_split_count": row["sparse_split_count"],
                }
            )
    return pd.DataFrame(rows)


def choose_best_operating_points(ops: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (sim_name, tau, c_min), group in ops.groupby(["similarity_model", "risk_tolerance", "coverage_floor"]):
        accepted = group[group["acceptance_label"].eq("accepted")]
        tentative = group[group["acceptance_label"].eq("tentative")]
        if not accepted.empty:
            selected = accepted.sort_values(["coverage", "total_risk_load"], ascending=[False, True]).iloc[0]
            status = "strictly_feasible_policy_found"
        elif not tentative.empty:
            selected = tentative.sort_values(["coverage", "total_risk_load"], ascending=[False, True]).iloc[0]
            status = "no_strict_policy_tentative_point_feasible"
        else:
            scored = group.copy()
            scored["_risk_violation"] = (scored["total_risk_load"] - tau).clip(lower=0)
            scored["_coverage_violation"] = (c_min - scored["coverage"]).clip(lower=0)
            selected = scored.sort_values(["_risk_violation", "_coverage_violation", "coverage"], ascending=[True, True, False]).iloc[0]
            status = "no_feasible_policy_closest_tradeoff"
        selected_dict = selected.to_dict()
        selected_dict["selection_status"] = status
        rows.append(selected_dict)
    return pd.DataFrame(rows)


def write_figure(refinement: pd.DataFrame) -> str:
    try:
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover
        return f"Figure skipped: matplotlib unavailable ({exc})"

    plot_df = refinement.drop_duplicates(["policy_name", "similarity_model", "risk_tolerance_context"]).copy()
    fig, ax = plt.subplots(figsize=(9, 6))
    markers = {"megadescriptor": "o", "resnet50": "s"}
    for sim_name, group in plot_df.groupby("similarity_model"):
        ax.errorbar(
            group["mean_coverage"],
            group["mean_total_risk_load"],
            xerr=[
                group["mean_coverage"] - group["coverage_ci_lower_95"],
                group["coverage_ci_upper_95"] - group["mean_coverage"],
            ],
            yerr=[
                group["mean_total_risk_load"] - group["risk_load_ci_lower_95"],
                group["risk_load_ci_upper_95"] - group["mean_total_risk_load"],
            ],
            fmt=markers.get(sim_name, "o"),
            capsize=2,
            alpha=0.75,
            label=sim_name,
        )
    for _, row in plot_df.iterrows():
        if row["risk_tolerance_context"] == RISK_TOLERANCES[0]:
            label = row["policy_name"].replace("pf_eri_", "").replace("_", " ")
            ax.annotate(label, (row["mean_coverage"], row["mean_total_risk_load"]), fontsize=7, alpha=0.8)
    for tau in RISK_TOLERANCES:
        ax.axhline(tau, color="0.6", linewidth=0.7, linestyle="--", alpha=0.5)
    ax.set_xlabel("Retained evidence coverage")
    ax.set_ylabel("Forced-match proxy risk load")
    ax.set_title("PF-ERI Control simulated open-set risk-coverage frontier")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGURE_OUT, dpi=180)
    plt.close(fig)
    return "Figure written"


def audit_outputs(*dfs: pd.DataFrame) -> list[str]:
    issues: list[str] = []
    for df in dfs:
        lower_cols = {str(col).lower() for col in df.columns}
        leaked_cols = sorted(lower_cols & SENSITIVE_OUTPUT_COLUMNS)
        if leaked_cols:
            issues.append(f"sensitive_columns_present={','.join(leaked_cols)}")
    text = "\n".join(df.astype(str).to_string(index=False) for df in dfs)
    for pattern in SENSITIVE_VALUE_PATTERNS:
        if pattern in text:
            issues.append(f"sensitive_value_pattern_present={pattern}")
    for regex in SENSITIVE_VALUE_REGEXES:
        if re.search(regex, text):
            issues.append(f"sensitive_value_pattern_present={regex}")
    return issues


def main() -> None:
    OUT_TABLE_DIR.mkdir(parents=True, exist_ok=True)
    OUT_FIG_DIR.mkdir(parents=True, exist_ok=True)
    QC_DIR.mkdir(parents=True, exist_ok=True)

    pairs, clustered_available = load_pairs()
    identities = np.array(sorted(pd.concat([pairs["_identity_a"], pairs["_identity_b"]]).unique()), dtype=object)
    rng = np.random.default_rng(SEED)
    policies = [
        "keep_all",
        "raw_megadescriptor_top_candidate",
        "raw_resnet50_top_candidate",
        "pf_eri_high_only",
        "pf_eri_high_medium",
        "pf_eri_gate_then_megadescriptor_ranking",
        "pf_eri_gate_then_resnet50_ranking",
        "pf_eri_gate_then_hybrid_prioritization",
        "pf_eri_gate_then_cross_model_agreement",
        "pf_eri_gate_then_calibrated_risk_tolerance",
        "pf_eri_control_v2_staged_policy",
    ]

    rows: list[dict[str, object]] = []
    failures: list[str] = []
    for split_idx in range(N_SPLITS):
        split_id = f"split_{split_idx + 1:02d}"
        unknown_ids = choose_unknown_identities(identities, rng)
        candidates, known_known_mask = split_candidates(pairs, unknown_ids)
        if candidates.empty:
            failures.append(f"{split_id}: no unknown-known candidate pairs")
            continue
        if candidates["_identity_a"].isin(unknown_ids).eq(candidates["_identity_b"].isin(unknown_ids)).any():
            failures.append(f"{split_id}: identity leak in candidate split")
            continue
        for sim_name, sim_col in SIMILARITY_COLUMNS.items():
            threshold = high_similarity_threshold(pairs, known_known_mask, sim_col)
            for tau in RISK_TOLERANCES:
                for policy in policies:
                    rows.append(evaluate_split_policy(split_id, candidates, policy, sim_name, sim_col, threshold, tau))

    if failures:
        raise SystemExit("Policy refinement split failures: " + "; ".join(failures[:5]))

    split_metrics = pd.DataFrame(rows)
    refinement = summarize_refinement(split_metrics)
    ops = operating_points(refinement)
    summary = choose_best_operating_points(ops)
    issues = audit_outputs(refinement, ops, summary)

    refinement.to_csv(REFINEMENT_OUT, index=False)
    ops.to_csv(OPERATING_POINTS_OUT, index=False)
    summary.to_csv(POLICY_SUMMARY_OUT, index=False)
    figure_status = write_figure(refinement)

    strict_count = int(ops["acceptance_label"].eq("accepted").sum())
    tentative_count = int(ops["acceptance_label"].eq("tentative").sum())
    rejected_count = int(ops["acceptance_label"].eq("rejected").sum())
    selected_cols = [
        "similarity_model",
        "risk_tolerance",
        "coverage_floor",
        "policy_name",
        "policy_stage",
        "coverage",
        "total_risk_load",
        "risk_load_ci_upper_95",
        "coverage_ci_lower_95",
        "acceptance_label",
        "selection_status",
    ]
    status = "PASS" if not issues else "FAIL"
    REPORT_OUT.write_text(
        "\n".join(
            [
                "Phase 6 PF-ERI Control policy refinement audit",
                f"Status: {status}",
                f"Seed: {SEED}",
                f"Identity-level simulated open-set splits: {N_SPLITS}",
                "Objective: maximize coverage subject to risk_load <= tau and coverage >= c_min.",
                "Interval rule: accepted only when upper_CI_95(risk_load) <= tau and lower_CI_95(coverage) >= c_min.",
                "Uncertainty: split-level intervals across identity-level simulated open-set splits.",
                f"Clustered bootstrap interval input available: {clustered_available}; not policy-specific, so not used as formal acceptance evidence.",
                "Interpretation boundary: simulated open-set CzechLynx validation, not field deployment and not conformal risk control.",
                f"Operating point labels: accepted={strict_count}, tentative={tentative_count}, rejected={rejected_count}",
                f"Figure status: {figure_status}",
                "Selected operating points:",
                summary[selected_cols].to_string(index=False),
                "Audit issues:",
                *(issues if issues else ["None"]),
                "",
            ]
        )
    )
    if issues:
        raise SystemExit("PF-ERI policy refinement audit failed: " + "; ".join(issues))
    print(f"PASS: wrote {REFINEMENT_OUT}")
    print(f"PASS: wrote {OPERATING_POINTS_OUT}")
    print(f"PASS: wrote {POLICY_SUMMARY_OUT}")
    print(f"PASS: wrote {FIGURE_OUT}")
    print(f"PASS: wrote {REPORT_OUT}")


if __name__ == "__main__":
    main()
