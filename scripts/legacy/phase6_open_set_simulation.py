#!/usr/bin/env python3
"""Phase 6 simulated open-set CzechLynx validation.

This uses internal identities only to create identity-level known-gallery vs
simulated-unknown splits. Outputs are aggregate-only.
"""

from __future__ import annotations

from pathlib import Path
import re

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PAIR_SCORES = ROOT / "outputs/czechlynx/phase5/czechlynx_phase5_pair_eri_scores_internal.csv"
ID_MAPPING = ROOT / "data/interim/czechlynx/czechlynx_expanded_125x4_internal_with_ids.csv"
IDENTITY_HOLDOUT = ROOT / "outputs/czechlynx/phase6/tables/phase6_identity_holdout_validation.csv"
CALIBRATED_RISK = ROOT / "outputs/czechlynx/phase6/tables/phase6_calibrated_eri_risk_by_band.csv"
COVERAGE_POLICY = ROOT / "outputs/czechlynx/phase6/tables/phase6_coverage_at_risk_tolerance.csv"

OUT_TABLE_DIR = ROOT / "outputs/czechlynx/phase6/tables"
OUT_FIG_DIR = ROOT / "outputs/czechlynx/phase6/figures"
QC_DIR = ROOT / "outputs/czechlynx/qc"
METRICS_OUT = OUT_TABLE_DIR / "phase6_simulated_open_set_metrics.csv"
REJECTION_OUT = OUT_TABLE_DIR / "phase6_unknown_rejection_metrics.csv"
COMPARISON_OUT = OUT_TABLE_DIR / "phase6_open_set_policy_comparison.csv"
FIGURE_OUT = OUT_FIG_DIR / "phase6_open_set_risk_coverage.png"
REPORT_OUT = QC_DIR / "phase6_open_set_audit_report.txt"

SEED = 20260612
N_SPLITS = 50
UNKNOWN_FRACTION = 0.20
RISK_TOLERANCE = 0.05
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
}
SENSITIVE_VALUE_PATTERNS = ("/Users/", "data/interim", "working_individual_id", "review_image_path")
SENSITIVE_VALUE_REGEXES = (r"\blynx_\d+",)


def band_from_score(value: float) -> str:
    if value >= 75:
        return "high"
    if value >= 55:
        return "medium"
    if value >= 35:
        return "low"
    return "unusable"


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    for path in [PAIR_SCORES, ID_MAPPING, IDENTITY_HOLDOUT, CALIBRATED_RISK, COVERAGE_POLICY]:
        if not path.exists():
            raise FileNotFoundError(f"Missing required input: {path}")

    pairs = pd.read_csv(PAIR_SCORES)
    mapping = pd.read_csv(ID_MAPPING, usecols=["expanded_image_id", "working_individual_id"])
    if mapping["expanded_image_id"].duplicated().any():
        raise ValueError("Internal mapping has duplicate expanded_image_id rows.")

    lookup = mapping.set_index("expanded_image_id")["working_individual_id"]
    pairs["_identity_a"] = pairs["image_a_expanded_id"].map(lookup)
    pairs["_identity_b"] = pairs["image_b_expanded_id"].map(lookup)
    if pairs[["_identity_a", "_identity_b"]].isna().any().any():
        raise ValueError("Could not reconstruct identity grouping for all pair rows.")
    reconstructed_same = pairs["_identity_a"].eq(pairs["_identity_b"])
    if not reconstructed_same.eq(pairs["pair_type"].eq("same")).all():
        raise ValueError("Pair labels disagree with internal identity grouping.")

    coverage_policy = pd.read_csv(COVERAGE_POLICY)
    return pairs, coverage_policy


def choose_unknown_identities(identities: np.ndarray, rng: np.random.Generator) -> set[object]:
    unknown_count = max(2, int(round(len(identities) * UNKNOWN_FRACTION)))
    selected = rng.choice(identities, size=unknown_count, replace=False)
    return set(selected.tolist())


def policy_mask(
    candidates: pd.DataFrame,
    policy_name: str,
    similarity_model: str,
    sim_col: str,
    calibrated_policy: str,
) -> tuple[pd.Series, str]:
    if policy_name == "keep_all":
        return pd.Series(True, index=candidates.index), "review"

    if policy_name == "raw_megadescriptor_top_similarity_candidates":
        if similarity_model != "megadescriptor":
            return pd.Series(False, index=candidates.index), "not_applicable"
        top_idx = candidates.groupby("_unknown_query_key")["megadescriptor_similarity"].idxmax()
        return candidates.index.to_series().isin(top_idx), "review"

    if policy_name == "raw_resnet50_top_similarity_candidates":
        if similarity_model != "resnet50":
            return pd.Series(False, index=candidates.index), "not_applicable"
        top_idx = candidates.groupby("_unknown_query_key")["resnet50_similarity"].idxmax()
        return candidates.index.to_series().isin(top_idx), "review"

    if policy_name == "visual_only_eri_high_only":
        return candidates["visual_only_eri"].ge(75), "review_high_only"

    if policy_name == "hybrid_eri_high_only":
        return candidates["hybrid_eri"].ge(75), "review_high_only"

    if policy_name == "calibrated_hybrid_eri_tolerance_0_05":
        bands = candidates["hybrid_eri"].map(band_from_score)
        keep_bands = {
            "keep_all": {"high", "medium", "low", "unusable"},
            "keep_high": {"high"},
            "keep_high_medium": {"high", "medium"},
            "keep_high_medium_low": {"high", "medium", "low"},
        }.get(calibrated_policy)
        if keep_bands is None:
            raise ValueError(f"Unknown calibrated policy: {calibrated_policy}")
        return bands.isin(keep_bands), calibrated_policy

    if policy_name == "review_defer_exclude_tier_policy":
        tiers = candidates["hybrid_review_tier"].astype(str)
        return tiers.eq("high_confidence_candidate_review"), "review_high_defer_low_exclude_unusable"

    raise ValueError(f"Unknown policy: {policy_name}")


def threshold_for_split(pairs: pd.DataFrame, known_known_mask: pd.Series, sim_col: str) -> float:
    train_values = pairs.loc[known_known_mask & pairs["pair_type"].eq("different"), sim_col]
    if train_values.empty:
        raise ValueError("Cannot estimate high-similarity threshold from empty known-known different set.")
    return float(train_values.quantile(0.90))


def split_candidates(pairs: pd.DataFrame, unknown_ids: set[object]) -> tuple[pd.DataFrame, pd.Series]:
    a_unknown = pairs["_identity_a"].isin(unknown_ids)
    b_unknown = pairs["_identity_b"].isin(unknown_ids)
    cross_unknown_known = a_unknown ^ b_unknown
    candidate_mask = cross_unknown_known & pairs["pair_type"].eq("different")
    candidates = pairs.loc[candidate_mask].copy()
    if candidates.empty:
        return candidates, ~(a_unknown | b_unknown)

    candidates["_unknown_query_key"] = np.where(
        candidates["_identity_a"].isin(unknown_ids),
        candidates["image_a_expanded_id"],
        candidates["image_b_expanded_id"],
    )
    known_known_mask = ~(a_unknown | b_unknown)
    return candidates, known_known_mask


def evaluate_policy(
    split_id: str,
    candidates: pd.DataFrame,
    policy_name: str,
    similarity_model: str,
    sim_col: str,
    threshold: float,
    calibrated_policy: str,
) -> tuple[dict[str, object], dict[str, object]]:
    retain_mask, policy_detail = policy_mask(candidates, policy_name, similarity_model, sim_col, calibrated_policy)
    if policy_detail == "not_applicable":
        retained = candidates.iloc[0:0]
    else:
        retained = candidates.loc[retain_mask]

    original_count = int(len(candidates))
    retained_count = int(len(retained))
    deferred_count = original_count - retained_count
    forced_mask = retained[sim_col].ge(threshold)
    forced_count = int(forced_mask.sum())
    query_count = int(candidates["_unknown_query_key"].nunique())
    retained_queries = int(retained["_unknown_query_key"].nunique()) if retained_count else 0
    forced_queries = int(retained.loc[forced_mask, "_unknown_query_key"].nunique()) if forced_count else 0
    sparse = original_count < 100 or query_count < 20

    metrics = {
        "split_id": split_id,
        "validation_name": "simulated_open_set_czechlynx-validation",
        "simulation_scope": "pair_table_unknown_to_known_candidates",
        "unknown_identity_count": np.nan,
        "known_gallery_identity_count": np.nan,
        "unknown_query_count": query_count,
        "policy_name": policy_name,
        "policy_detail": policy_detail,
        "similarity_model": similarity_model,
        "high_similarity_threshold": threshold,
        "unknown_query_candidate_count": original_count,
        "retained_candidate_count": retained_count,
        "retained_evidence_coverage": retained_count / original_count if original_count else np.nan,
        "defer_rate": deferred_count / original_count if original_count else np.nan,
        "forced_match_proxy_count": forced_count,
        "forced_match_proxy_rate_among_retained": forced_count / retained_count if retained_count else np.nan,
        "risk_load_relative_to_original_candidate_pool": forced_count / original_count if original_count else np.nan,
        "sparse_fold_caveat": "sparse_candidate_pool" if sparse else "",
    }
    rejection = {
        "split_id": split_id,
        "validation_name": "simulated_open_set_czechlynx-validation",
        "policy_name": policy_name,
        "policy_detail": policy_detail,
        "similarity_model": similarity_model,
        "unknown_query_count": query_count,
        "query_with_retained_candidate_count": retained_queries,
        "query_rejected_or_deferred_count": query_count - retained_queries,
        "unknown_rejection_or_defer_rate": (query_count - retained_queries) / query_count if query_count else np.nan,
        "query_with_forced_match_proxy_count": forced_queries,
        "query_forced_match_proxy_rate": forced_queries / query_count if query_count else np.nan,
        "sparse_fold_caveat": "sparse_candidate_pool" if sparse else "",
    }
    return metrics, rejection


def add_split_counts(rows: list[dict[str, object]], unknown_count: int, known_count: int) -> None:
    for row in rows:
        row["unknown_identity_count"] = unknown_count
        row["known_gallery_identity_count"] = known_count


def calibrated_policy_for_model(coverage_policy: pd.DataFrame, similarity_model: str) -> str:
    rows = coverage_policy[
        coverage_policy["score_name"].eq("hybrid_eri")
        & coverage_policy["similarity_model"].eq(similarity_model)
        & coverage_policy["risk_tolerance"].eq(RISK_TOLERANCE)
    ]
    if rows.empty:
        raise ValueError(f"Missing calibrated hybrid ERI policy for {similarity_model} at {RISK_TOLERANCE}.")
    return str(rows.iloc[0]["selected_policy"])


def summarize_policy_comparison(metrics: pd.DataFrame) -> pd.DataFrame:
    group_cols = ["policy_name", "policy_detail", "similarity_model"]
    rows = []
    keep_all = metrics[metrics["policy_name"].eq("keep_all")].copy()
    raw_policy = {
        "megadescriptor": "raw_megadescriptor_top_similarity_candidates",
        "resnet50": "raw_resnet50_top_similarity_candidates",
    }

    for keys, group in metrics.groupby(group_cols, dropna=False):
        policy_name, policy_detail, sim_name = keys
        if group["retained_candidate_count"].sum() == 0 and policy_detail == "not_applicable":
            continue
        base = keep_all[keep_all["similarity_model"].eq(sim_name)].set_index("split_id")
        raw = metrics[
            metrics["similarity_model"].eq(sim_name) & metrics["policy_name"].eq(raw_policy[sim_name])
        ].set_index("split_id")
        joined_base = group.set_index("split_id").join(
            base[["forced_match_proxy_count", "retained_candidate_count"]],
            rsuffix="_keep_all",
        )
        joined_raw = group.set_index("split_id").join(
            raw[["forced_match_proxy_count", "retained_candidate_count"]],
            rsuffix="_raw_top",
        )

        removed_vs_keep_all = (
            joined_base["retained_candidate_count_keep_all"] - joined_base["retained_candidate_count"]
        )
        risk_reduced_vs_keep_all = (
            joined_base["forced_match_proxy_count_keep_all"] - joined_base["forced_match_proxy_count"]
        )
        risk_reduction_per_evidence_removed = np.where(
            removed_vs_keep_all > 0,
            risk_reduced_vs_keep_all / removed_vs_keep_all,
            np.nan,
        )
        finite_efficiency = risk_reduction_per_evidence_removed[
            np.isfinite(risk_reduction_per_evidence_removed)
        ]
        raw_risk_delta = joined_raw["forced_match_proxy_count_raw_top"] - joined_raw["forced_match_proxy_count"]

        rows.append(
            {
                "policy_name": policy_name,
                "policy_detail": policy_detail,
                "similarity_model": sim_name,
                "split_count": int(group["split_id"].nunique()),
                "mean_unknown_query_candidate_count": float(group["unknown_query_candidate_count"].mean()),
                "mean_retained_candidate_count": float(group["retained_candidate_count"].mean()),
                "mean_retained_evidence_coverage": float(group["retained_evidence_coverage"].mean()),
                "mean_defer_rate": float(group["defer_rate"].mean()),
                "mean_forced_match_proxy_count": float(group["forced_match_proxy_count"].mean()),
                "mean_forced_match_proxy_rate_among_retained": float(
                    group["forced_match_proxy_rate_among_retained"].mean(skipna=True)
                ),
                "mean_risk_load_relative_to_original_candidate_pool": float(
                    group["risk_load_relative_to_original_candidate_pool"].mean()
                ),
                "mean_risk_reduction_vs_keep_all": float(risk_reduced_vs_keep_all.mean()),
                "mean_risk_reduction_vs_raw_top_similarity": float(raw_risk_delta.mean()),
                "mean_risk_reduction_per_evidence_removed_vs_keep_all": float(finite_efficiency.mean())
                if len(finite_efficiency)
                else np.nan,
                "sparse_split_count": int(group["sparse_fold_caveat"].astype(bool).sum()),
            }
        )
    return pd.DataFrame(rows)


def write_figure(comparison: pd.DataFrame) -> str:
    try:
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover
        return f"Figure skipped: matplotlib unavailable ({exc})"

    plot_df = comparison.copy()
    fig, ax = plt.subplots(figsize=(8, 5))
    markers = {"megadescriptor": "o", "resnet50": "s"}
    for sim_name, group in plot_df.groupby("similarity_model"):
        ax.scatter(
            group["mean_retained_evidence_coverage"],
            group["mean_risk_load_relative_to_original_candidate_pool"],
            label=sim_name,
            marker=markers.get(sim_name, "o"),
            s=55,
        )
        for _, row in group.iterrows():
            label = row["policy_name"].replace("_", " ")
            ax.annotate(label, (row["mean_retained_evidence_coverage"], row["mean_risk_load_relative_to_original_candidate_pool"]), fontsize=7)
    ax.set_xlabel("Mean retained evidence coverage")
    ax.set_ylabel("Mean forced-match proxy load")
    ax.set_title("Simulated open-set CzechLynx risk-coverage")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGURE_OUT, dpi=180)
    plt.close(fig)
    return "Figure written"


def audit_outputs(*dfs: pd.DataFrame) -> list[str]:
    issues: list[str] = []
    for df in dfs:
        lower_cols = {col.lower() for col in df.columns}
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

    pairs, coverage_policy = load_inputs()
    identities = np.array(sorted(pd.concat([pairs["_identity_a"], pairs["_identity_b"]]).unique()), dtype=object)
    rng = np.random.default_rng(SEED)
    policies = [
        "keep_all",
        "raw_megadescriptor_top_similarity_candidates",
        "raw_resnet50_top_similarity_candidates",
        "visual_only_eri_high_only",
        "hybrid_eri_high_only",
        "calibrated_hybrid_eri_tolerance_0_05",
        "review_defer_exclude_tier_policy",
    ]

    metric_rows: list[dict[str, object]] = []
    rejection_rows: list[dict[str, object]] = []
    split_failures: list[str] = []
    for split_idx in range(N_SPLITS):
        split_id = f"split_{split_idx + 1:02d}"
        unknown_ids = choose_unknown_identities(identities, rng)
        known_count = len(identities) - len(unknown_ids)
        candidates, known_known_mask = split_candidates(pairs, unknown_ids)
        if candidates.empty:
            split_failures.append(f"{split_id}: no unknown-known candidate pairs")
            continue
        if candidates["_identity_a"].isin(unknown_ids).eq(candidates["_identity_b"].isin(unknown_ids)).any():
            split_failures.append(f"{split_id}: invalid candidate split")
            continue

        split_metric_rows: list[dict[str, object]] = []
        split_rejection_rows: list[dict[str, object]] = []
        for sim_name, sim_col in SIMILARITY_COLUMNS.items():
            threshold = threshold_for_split(pairs, known_known_mask, sim_col)
            calibrated_policy = calibrated_policy_for_model(coverage_policy, sim_name)
            for policy in policies:
                metrics, rejection = evaluate_policy(
                    split_id,
                    candidates,
                    policy,
                    sim_name,
                    sim_col,
                    threshold,
                    calibrated_policy,
                )
                split_metric_rows.append(metrics)
                split_rejection_rows.append(rejection)

        add_split_counts(split_metric_rows, len(unknown_ids), known_count)
        metric_rows.extend(split_metric_rows)
        rejection_rows.extend(split_rejection_rows)

    if split_failures:
        raise SystemExit("Open-set split failures: " + "; ".join(split_failures[:5]))
    metrics = pd.DataFrame(metric_rows)
    rejection = pd.DataFrame(rejection_rows)
    comparison = summarize_policy_comparison(metrics)
    issues = audit_outputs(metrics, rejection, comparison)

    metrics.to_csv(METRICS_OUT, index=False)
    rejection.to_csv(REJECTION_OUT, index=False)
    comparison.to_csv(COMPARISON_OUT, index=False)
    figure_status = write_figure(comparison)

    status = "PASS" if not issues else "FAIL"
    headline = comparison[
        comparison["policy_name"].isin(
            [
                "keep_all",
                "raw_megadescriptor_top_similarity_candidates",
                "raw_resnet50_top_similarity_candidates",
                "visual_only_eri_high_only",
                "hybrid_eri_high_only",
                "calibrated_hybrid_eri_tolerance_0_05",
                "review_defer_exclude_tier_policy",
            ]
        )
    ][
        [
            "policy_name",
            "policy_detail",
            "similarity_model",
            "mean_retained_evidence_coverage",
            "mean_forced_match_proxy_rate_among_retained",
            "mean_risk_load_relative_to_original_candidate_pool",
            "mean_risk_reduction_vs_keep_all",
        ]
    ]
    REPORT_OUT.write_text(
        "\n".join(
            [
                "Phase 6 simulated open-set CzechLynx validation audit",
                f"Status: {status}",
                f"Seed: {SEED}",
                f"Splits: {N_SPLITS}",
                f"Unknown identity fraction per split: {UNKNOWN_FRACTION}",
                "Design: identity-level simulated unknown identities; existing pair-table unknown-to-known candidates only.",
                "Interpretation boundary: simulated open-set CzechLynx validation, not true open-set field deployment.",
                f"Figure status: {figure_status}",
                "Headline policy comparison:",
                headline.to_string(index=False),
                "Audit issues:",
                *(issues if issues else ["None"]),
                "Caveat: candidate pairs come from the existing Phase 5 pair table, not exhaustive gallery retrieval.",
                "",
            ]
        )
    )
    if issues:
        raise SystemExit("Phase 6 open-set audit failed: " + "; ".join(issues))


if __name__ == "__main__":
    main()
