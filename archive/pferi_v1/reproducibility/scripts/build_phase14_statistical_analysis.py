#!/usr/bin/env python3
"""Run Phase 14 statistical analyses for the 2x2 evidence-risk design.

The analysis is intentionally conservative:

- CzechLynx known-ID pairs are used for positive/negative validation.
- Bobcat pairs are identity-unknown and are analyzed only as comparability,
  descriptor-conflict pressure, and review-burden stress evidence.
- Non-parametric tests and bootstrap confidence intervals are preferred because
  evidence scores are bounded and pair samples are reused across images.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import roc_auc_score

PROJECT_ROOT = Path(__file__).resolve().parents[1]
IMAGE_TABLE = PROJECT_ROOT / "outputs/phase14/phase14_algorithm_inputs/phase14_2x2_image_evidence_table.csv"
CONFLICT_TABLE = (
    PROJECT_ROOT / "outputs/phase14/phase14_descriptor_conflict/phase14_2x2_descriptor_evidence_conflict_table.csv"
)
OUT_DIR = PROJECT_ROOT / "outputs/phase14/phase14_statistical_analysis"
IMAGE_SUMMARY = OUT_DIR / "phase14_image_level_2x2_statistics.csv"
PAIR_SUMMARY = OUT_DIR / "phase14_pair_level_block_statistics.csv"
CZECH_VALIDATION = OUT_DIR / "phase14_czechlynx_known_id_validation_statistics.csv"
CONFLICT_ENRICHMENT = OUT_DIR / "phase14_descriptor_conflict_enrichment_statistics.csv"
REVIEW_BURDEN = OUT_DIR / "phase14_review_burden_statistics.csv"
DECISION_VALIDATION = OUT_DIR / "phase14_czechlynx_decision_validation_statistics.csv"
RISK_COVERAGE = OUT_DIR / "phase14_czechlynx_high_descriptor_risk_coverage_statistics.csv"
REPORT_MD = OUT_DIR / "phase14_statistical_analysis_report.md"
AUDIT_JSON = OUT_DIR / "phase14_statistical_analysis_audit.json"

RANDOM_SEED = 20260622
BOOTSTRAP_N = 2000


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(frame[column], errors="coerce")


def fmt(value: float | int | None, digits: int = 3) -> str:
    if value is None:
        return "NA"
    try:
        value = float(value)
    except Exception:
        return "NA"
    if not math.isfinite(value):
        return "NA"
    return f"{value:.{digits}f}"


def p_text(value: float | None) -> str:
    if value is None or not math.isfinite(float(value)):
        return "NA"
    value = float(value)
    if value < 0.001:
        return "< .001"
    return f"= {value:.3f}"


def bootstrap_ci(values: np.ndarray, statistic: str = "mean", n_boot: int = BOOTSTRAP_N) -> tuple[float, float]:
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return float("nan"), float("nan")
    rng = np.random.default_rng(RANDOM_SEED)
    sample_indices = rng.integers(0, values.size, size=(n_boot, values.size))
    samples = values[sample_indices]
    if statistic == "median":
        boot = np.median(samples, axis=1)
    else:
        boot = np.mean(samples, axis=1)
    return float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))


def bootstrap_diff_ci(a: np.ndarray, b: np.ndarray, statistic: str = "mean", n_boot: int = BOOTSTRAP_N) -> tuple[float, float]:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    a = a[np.isfinite(a)]
    b = b[np.isfinite(b)]
    if a.size == 0 or b.size == 0:
        return float("nan"), float("nan")
    rng = np.random.default_rng(RANDOM_SEED)
    ai = rng.integers(0, a.size, size=(n_boot, a.size))
    bi = rng.integers(0, b.size, size=(n_boot, b.size))
    if statistic == "median":
        boot = np.median(a[ai], axis=1) - np.median(b[bi], axis=1)
    else:
        boot = np.mean(a[ai], axis=1) - np.mean(b[bi], axis=1)
    return float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))


def cliffs_delta(a: np.ndarray, b: np.ndarray, max_pairs: int = 2_000_000) -> float:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    a = a[np.isfinite(a)]
    b = b[np.isfinite(b)]
    if a.size == 0 or b.size == 0:
        return float("nan")
    total = int(a.size * b.size)
    if total <= max_pairs:
        diff = a[:, None] - b[None, :]
        return float((np.sum(diff > 0) - np.sum(diff < 0)) / total)
    rng = np.random.default_rng(RANDOM_SEED)
    idx_a = rng.integers(0, a.size, size=max_pairs)
    idx_b = rng.integers(0, b.size, size=max_pairs)
    diff = a[idx_a] - b[idx_b]
    return float((np.sum(diff > 0) - np.sum(diff < 0)) / max_pairs)


def mann_whitney(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    a = a[np.isfinite(a)]
    b = b[np.isfinite(b)]
    if a.size == 0 or b.size == 0:
        return float("nan"), float("nan")
    result = stats.mannwhitneyu(a, b, alternative="two-sided", method="asymptotic")
    return float(result.statistic), float(result.pvalue)


def odds_ratio_ci(a: int, b: int, c: int, d: int) -> tuple[float, float, float]:
    # Haldane-Anscombe correction keeps zero-count cells reportable.
    aa, bb, cc, dd = a + 0.5, b + 0.5, c + 0.5, d + 0.5
    odds_ratio = (aa * dd) / (bb * cc)
    se = math.sqrt(1 / aa + 1 / bb + 1 / cc + 1 / dd)
    lo = math.exp(math.log(odds_ratio) - 1.96 * se)
    hi = math.exp(math.log(odds_ratio) + 1.96 * se)
    return float(odds_ratio), float(lo), float(hi)


def group_stats(frame: pd.DataFrame, group_cols: list[str], value_cols: list[str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for keys, group in frame.groupby(group_cols, dropna=False, sort=True):
        if not isinstance(keys, tuple):
            keys = (keys,)
        base = {column: value for column, value in zip(group_cols, keys)}
        base["n"] = int(len(group))
        for column in value_cols:
            values = numeric(group, column).to_numpy()
            values = values[np.isfinite(values)]
            lo, hi = bootstrap_ci(values, "mean")
            mlo, mhi = bootstrap_ci(values, "median")
            base[f"{column}_mean"] = float(np.mean(values)) if values.size else float("nan")
            base[f"{column}_mean_ci95_low"] = lo
            base[f"{column}_mean_ci95_high"] = hi
            base[f"{column}_median"] = float(np.median(values)) if values.size else float("nan")
            base[f"{column}_median_ci95_low"] = mlo
            base[f"{column}_median_ci95_high"] = mhi
            base[f"{column}_sd"] = float(np.std(values, ddof=1)) if values.size > 1 else float("nan")
        rows.append(base)
    return pd.DataFrame(rows)


def compare_two_groups(
    frame: pd.DataFrame,
    group_col: str,
    group_a: str,
    group_b: str,
    value_col: str,
    label: str,
) -> dict[str, Any]:
    a = numeric(frame[frame[group_col].astype(str).eq(group_a)], value_col).to_numpy()
    b = numeric(frame[frame[group_col].astype(str).eq(group_b)], value_col).to_numpy()
    u, p = mann_whitney(a, b)
    diff_lo, diff_hi = bootstrap_diff_ci(a, b, "mean")
    median_diff_lo, median_diff_hi = bootstrap_diff_ci(a, b, "median")
    return {
        "comparison_id": label,
        "group_column": group_col,
        "group_a": group_a,
        "group_b": group_b,
        "value": value_col,
        "n_a": int(np.isfinite(a).sum()),
        "n_b": int(np.isfinite(b).sum()),
        "mean_a": float(np.nanmean(a)),
        "mean_b": float(np.nanmean(b)),
        "mean_difference_a_minus_b": float(np.nanmean(a) - np.nanmean(b)),
        "mean_difference_ci95_low": diff_lo,
        "mean_difference_ci95_high": diff_hi,
        "median_a": float(np.nanmedian(a)),
        "median_b": float(np.nanmedian(b)),
        "median_difference_a_minus_b": float(np.nanmedian(a) - np.nanmedian(b)),
        "median_difference_ci95_low": median_diff_lo,
        "median_difference_ci95_high": median_diff_hi,
        "mann_whitney_u": u,
        "p_value": p,
        "cliffs_delta": cliffs_delta(a, b),
    }


def build_image_analysis(images: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    value_cols = [
        "image_evidence_utility_score",
        "image_evidence_risk_score",
        "detector_geometry_score",
        "visual_component_score",
        "md_area_fraction",
    ]
    summary = group_stats(images, ["environment_axis", "species_axis", "evidence_axis", "source_quadrant"], value_cols)
    comparisons = []
    for species in ["bobcat", "czechlynx"]:
        subset = images[images["species_axis"].eq(species)]
        comparisons.append(
            compare_two_groups(
                subset,
                "evidence_axis",
                "high_confidence",
                "low_evidence_stress",
                "image_evidence_utility_score",
                f"{species}_high_vs_low_image_utility",
            )
        )
    for evidence_axis in ["high_confidence", "low_evidence_stress"]:
        subset = images[images["evidence_axis"].eq(evidence_axis)].copy()
        comparisons.append(
            compare_two_groups(
                subset,
                "species_axis",
                "bobcat",
                "czechlynx",
                "image_evidence_utility_score",
                f"bobcat_vs_czechlynx_{evidence_axis}_image_utility",
            )
        )
    comparison_frame = pd.DataFrame(comparisons)
    return summary, comparison_frame


def build_pair_analysis(conflict: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    value_cols = [
        "pair_comparability_score",
        "pair_risk_score",
        "descriptor_similarity",
        "descriptor_evidence_conflict_score",
        "descriptor_evidence_support_score",
    ]
    summary = group_stats(conflict, ["species_axis", "pair_block", "pair_sampling_role"], value_cols)
    summary["high_conflict_rate"] = (
        conflict.groupby(["species_axis", "pair_block", "pair_sampling_role"])["descriptor_conflict_band"]
        .apply(lambda s: float(s.eq("high_conflict").mean()))
        .to_numpy()
    )
    comparisons = []
    for block_pair in [
        ("bobcat_high_confidence_within", "czechlynx_high_confidence_within"),
        ("bobcat_high_low_cross", "czechlynx_high_low_cross"),
        ("bobcat_low_evidence_stress_within", "czechlynx_low_evidence_stress_within"),
    ]:
        subset = conflict[conflict["pair_block"].isin(block_pair)].copy()
        comparisons.append(
            compare_two_groups(
                subset,
                "pair_block",
                block_pair[0],
                block_pair[1],
                "pair_comparability_score",
                f"{block_pair[0]}_vs_{block_pair[1]}_comparability",
            )
        )
        comparisons.append(
            compare_two_groups(
                subset,
                "pair_block",
                block_pair[0],
                block_pair[1],
                "descriptor_evidence_conflict_score",
                f"{block_pair[0]}_vs_{block_pair[1]}_conflict",
            )
        )
    return summary, pd.DataFrame(comparisons)


def build_czech_validation(conflict: pd.DataFrame) -> pd.DataFrame:
    czech = conflict[conflict["species_axis"].eq("czechlynx") & conflict["same_identity"].isin(["yes", "no"])].copy()
    czech["false_candidate_binary"] = czech["same_identity"].eq("no").astype(int)
    rows: list[dict[str, Any]] = []
    for block, group in czech.groupby("pair_block", sort=True):
        pos = group[group["same_identity"].eq("yes")]
        neg = group[group["same_identity"].eq("no")]
        row: dict[str, Any] = {
            "pair_block": block,
            "positive_n": int(len(pos)),
            "negative_n": int(len(neg)),
        }
        for value in ["descriptor_similarity", "pair_comparability_score", "descriptor_evidence_conflict_score"]:
            row[f"positive_{value}_mean"] = float(numeric(pos, value).mean())
            row[f"negative_{value}_mean"] = float(numeric(neg, value).mean())
            row[f"positive_minus_negative_{value}_mean_diff"] = row[f"positive_{value}_mean"] - row[f"negative_{value}_mean"]
            lo, hi = bootstrap_diff_ci(numeric(pos, value).to_numpy(), numeric(neg, value).to_numpy(), "mean")
            row[f"positive_minus_negative_{value}_ci95_low"] = lo
            row[f"positive_minus_negative_{value}_ci95_high"] = hi
            u, p = mann_whitney(numeric(pos, value).to_numpy(), numeric(neg, value).to_numpy())
            row[f"{value}_mann_whitney_u"] = u
            row[f"{value}_p_value"] = p
            row[f"{value}_cliffs_delta_pos_vs_neg"] = cliffs_delta(numeric(pos, value).to_numpy(), numeric(neg, value).to_numpy())
        # AUC: descriptor similarity should predict true positive; conflict is treated as risk/defer, not false-only.
        y_true_positive = group["same_identity"].eq("yes").astype(int).to_numpy()
        row["auc_descriptor_similarity_for_true_positive"] = float(
            roc_auc_score(y_true_positive, numeric(group, "descriptor_similarity").to_numpy())
        )
        row["auc_pair_comparability_for_true_positive"] = float(
            roc_auc_score(y_true_positive, numeric(group, "pair_comparability_score").to_numpy())
        )
        row["auc_conflict_score_for_true_positive"] = float(
            roc_auc_score(y_true_positive, numeric(group, "descriptor_evidence_conflict_score").to_numpy())
        )
        rows.append(row)
    return pd.DataFrame(rows)


def build_conflict_enrichment(conflict: pd.DataFrame) -> pd.DataFrame:
    czech = conflict[conflict["species_axis"].eq("czechlynx") & conflict["same_identity"].isin(["yes", "no"])].copy()
    czech["false_candidate"] = czech["same_identity"].eq("no")
    czech["high_descriptor_block"] = numeric(czech, "descriptor_similarity_percentile_block") >= 0.90
    czech["low_pair_evidence"] = numeric(czech, "pair_comparability_score") < 0.40
    czech["conflict_rule"] = czech["high_descriptor_block"] & czech["low_pair_evidence"]
    czech["supported_rule"] = czech["high_descriptor_block"] & (numeric(czech, "pair_comparability_score") >= 0.70)

    rows: list[dict[str, Any]] = []
    for block, group in czech.groupby("pair_block", sort=True):
        for rule in ["high_descriptor_block", "conflict_rule", "supported_rule"]:
            flagged = group[rule]
            a = int((flagged & group["false_candidate"]).sum())
            b = int((flagged & ~group["false_candidate"]).sum())
            c = int((~flagged & group["false_candidate"]).sum())
            d = int((~flagged & ~group["false_candidate"]).sum())
            or_value, or_lo, or_hi = odds_ratio_ci(a, b, c, d)
            rows.append(
                {
                    "pair_block": block,
                    "rule": rule,
                    "flagged_n": int(flagged.sum()),
                    "unflagged_n": int((~flagged).sum()),
                    "false_in_flagged": a,
                    "true_positive_in_flagged": b,
                    "false_rate_flagged": float(a / max(a + b, 1)),
                    "false_rate_unflagged": float(c / max(c + d, 1)),
                    "risk_difference_flagged_minus_unflagged": float(a / max(a + b, 1) - c / max(c + d, 1)),
                    "odds_ratio_false_candidate": or_value,
                    "odds_ratio_ci95_low": or_lo,
                    "odds_ratio_ci95_high": or_hi,
                    "interpretation_boundary": "CzechLynx known-ID only; conflict_rule means high descriptor with low visual pair evidence, not a false-only detector",
                }
            )
    return pd.DataFrame(rows)


def build_review_burden(conflict: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for keys, group in conflict.groupby(["species_axis", "pair_block"], sort=True):
        species, block = keys
        decisions = group["descriptor_evidence_decision"].value_counts()
        high_conflict = group["descriptor_conflict_band"].eq("high_conflict")
        rows.append(
            {
                "species_axis": species,
                "pair_block": block,
                "pair_count": int(len(group)),
                "mean_pair_comparability": float(numeric(group, "pair_comparability_score").mean()),
                "mean_conflict_score": float(numeric(group, "descriptor_evidence_conflict_score").mean()),
                "high_conflict_count": int(high_conflict.sum()),
                "high_conflict_rate": float(high_conflict.mean()),
                "defer_conflict_count": int(decisions.get("defer_descriptor_evidence_conflict", 0)),
                "defer_high_similarity_low_evidence_count": int(decisions.get("defer_high_similarity_low_evidence", 0)),
                "species_level_or_non_comparable_count": int(decisions.get("species_level_or_non_comparable", 0)),
                "descriptor_supported_review_candidate_count": int(decisions.get("descriptor_supported_review_candidate", 0)),
                "review_or_rank_by_descriptor_count": int(decisions.get("review_or_rank_by_descriptor", 0)),
            }
        )
    return pd.DataFrame(rows)


def build_czech_decision_validation(conflict: pd.DataFrame) -> pd.DataFrame:
    czech = conflict[conflict["species_axis"].eq("czechlynx") & conflict["same_identity"].isin(["yes", "no"])].copy()
    rows: list[dict[str, Any]] = []
    for keys, group in czech.groupby(["pair_block", "descriptor_evidence_decision"], sort=True):
        pair_block, decision = keys
        positive = group["same_identity"].eq("yes")
        false = group["same_identity"].eq("no")
        rows.append(
            {
                "pair_block": pair_block,
                "descriptor_evidence_decision": decision,
                "pair_count": int(len(group)),
                "positive_count": int(positive.sum()),
                "false_candidate_count": int(false.sum()),
                "positive_rate": float(positive.mean()) if len(group) else float("nan"),
                "false_candidate_rate": float(false.mean()) if len(group) else float("nan"),
                "mean_pair_comparability": float(numeric(group, "pair_comparability_score").mean()),
                "mean_descriptor_similarity": float(numeric(group, "descriptor_similarity").mean()),
                "mean_conflict_score": float(numeric(group, "descriptor_evidence_conflict_score").mean()),
            }
        )
    return pd.DataFrame(rows)


def build_czech_risk_coverage(conflict: pd.DataFrame) -> pd.DataFrame:
    czech = conflict[conflict["species_axis"].eq("czechlynx") & conflict["same_identity"].isin(["yes", "no"])].copy()
    czech["high_descriptor_block"] = numeric(czech, "descriptor_similarity_percentile_block") >= 0.90
    thresholds = [0.00, 0.20, 0.30, 0.40, 0.50, 0.55, 0.60, 0.70]
    rows: list[dict[str, Any]] = []
    for block, group in czech.groupby("pair_block", sort=True):
        base = group[group["high_descriptor_block"]].copy()
        base_positive = int(base["same_identity"].eq("yes").sum())
        base_false = int(base["same_identity"].eq("no").sum())
        for threshold in thresholds:
            retained = base[numeric(base, "pair_comparability_score") >= threshold]
            retained_positive = int(retained["same_identity"].eq("yes").sum())
            retained_false = int(retained["same_identity"].eq("no").sum())
            rows.append(
                {
                    "pair_block": block,
                    "descriptor_percentile_rule": "block_top_10_percent",
                    "pair_comparability_threshold": threshold,
                    "baseline_high_descriptor_pairs": int(len(base)),
                    "baseline_positive_count": base_positive,
                    "baseline_false_candidate_count": base_false,
                    "retained_pairs": int(len(retained)),
                    "retained_pair_coverage": float(len(retained) / max(len(base), 1)),
                    "retained_positive_count": retained_positive,
                    "retained_false_candidate_count": retained_false,
                    "positive_retention_among_high_descriptor": float(retained_positive / max(base_positive, 1)),
                    "false_retention_among_high_descriptor": float(retained_false / max(base_false, 1)),
                    "false_candidate_rate_retained": float(retained_false / max(retained_positive + retained_false, 1)),
                    "deferred_pairs": int(len(base) - len(retained)),
                }
            )
    return pd.DataFrame(rows)


def write_report(
    image_summary: pd.DataFrame,
    image_comparisons: pd.DataFrame,
    pair_summary: pd.DataFrame,
    pair_comparisons: pd.DataFrame,
    czech_validation: pd.DataFrame,
    enrichment: pd.DataFrame,
    burden: pd.DataFrame,
    decision_validation: pd.DataFrame,
    risk_coverage: pd.DataFrame,
) -> None:
    bobcat_img = image_comparisons[image_comparisons["comparison_id"].eq("bobcat_high_vs_low_image_utility")].iloc[0]
    czech_img = image_comparisons[image_comparisons["comparison_id"].eq("czechlynx_high_vs_low_image_utility")].iloc[0]
    high_env = image_comparisons[image_comparisons["comparison_id"].eq("bobcat_vs_czechlynx_high_confidence_image_utility")].iloc[0]
    low_env = image_comparisons[image_comparisons["comparison_id"].eq("bobcat_vs_czechlynx_low_evidence_stress_image_utility")].iloc[0]

    high_val = czech_validation[czech_validation["pair_block"].eq("czechlynx_high_confidence_within")].iloc[0]
    low_val = czech_validation[czech_validation["pair_block"].eq("czechlynx_low_evidence_stress_within")].iloc[0]
    cross_val = czech_validation[czech_validation["pair_block"].eq("czechlynx_high_low_cross")].iloc[0]

    bobcat_low_burden = burden[burden["pair_block"].eq("bobcat_low_evidence_stress_within")].iloc[0]
    czech_low_burden = burden[burden["pair_block"].eq("czechlynx_low_evidence_stress_within")].iloc[0]
    high_pair_cmp = pair_comparisons[pair_comparisons["comparison_id"].str.contains("high_confidence_within_vs") & pair_comparisons["comparison_id"].str.endswith("comparability")].iloc[0]
    low_pair_cmp = pair_comparisons[pair_comparisons["comparison_id"].str.contains("low_evidence_stress_within_vs") & pair_comparisons["comparison_id"].str.endswith("comparability")].iloc[0]

    high_low_decisions = decision_validation[
        decision_validation["pair_block"].eq("czechlynx_high_low_cross")
    ].sort_values("pair_count", ascending=False)
    low_stress_decisions = decision_validation[
        decision_validation["pair_block"].eq("czechlynx_low_evidence_stress_within")
    ].sort_values("pair_count", ascending=False)
    high_low_conflict = enrichment[
        enrichment["pair_block"].eq("czechlynx_high_low_cross") & enrichment["rule"].eq("conflict_rule")
    ].iloc[0]
    low_conflict = enrichment[
        enrichment["pair_block"].eq("czechlynx_low_evidence_stress_within") & enrichment["rule"].eq("conflict_rule")
    ].iloc[0]
    low_gate = risk_coverage[
        risk_coverage["pair_block"].eq("czechlynx_low_evidence_stress_within")
        & risk_coverage["pair_comparability_threshold"].eq(0.40)
    ].iloc[0]

    text = f"""# Phase 14 Statistical Analysis Report

## Scope

This report analyzes the Phase 14 2x2 evidence-risk design:

- environment axis: urban/peri-urban bobcat vs wild CzechLynx;
- evidence axis: high-confidence evidence vs low-evidence stress;
- mechanism chain: image-level evidence shift -> pair-level comparability shift -> descriptor-evidence conflict/review burden.

Scientific boundary: CzechLynx known-ID pairs support same/different validation. Bobcat pairs remain identity-unknown and support only comparability, conflict-pressure, and review-burden stress analysis.

## Statistical Method

Scores are bounded and non-Gaussian by construction, so the main comparisons use Mann-Whitney U tests, Cliff's delta, and bootstrap 95% confidence intervals for mean/median differences. Pair-level results are interpreted cautiously because pairs reuse images; large N is not treated as independent biological replication.

## 1. Image-Level Evidence Shift

Bobcat high-confidence images had higher evidence utility than bobcat low-evidence images, M_diff = {fmt(bobcat_img['mean_difference_a_minus_b'])}, 95% CI [{fmt(bobcat_img['mean_difference_ci95_low'])}, {fmt(bobcat_img['mean_difference_ci95_high'])}], U = {fmt(bobcat_img['mann_whitney_u'], 1)}, p {p_text(bobcat_img['p_value'])}, Cliff's delta = {fmt(bobcat_img['cliffs_delta'])}.

CzechLynx high-confidence images also exceeded CzechLynx low-evidence images, M_diff = {fmt(czech_img['mean_difference_a_minus_b'])}, 95% CI [{fmt(czech_img['mean_difference_ci95_low'])}, {fmt(czech_img['mean_difference_ci95_high'])}], U = {fmt(czech_img['mann_whitney_u'], 1)}, p {p_text(czech_img['p_value'])}, Cliff's delta = {fmt(czech_img['cliffs_delta'])}.

For high-confidence images, bobcat and CzechLynx utility was similar in magnitude, M_diff bobcat-CzechLynx = {fmt(high_env['mean_difference_a_minus_b'])}, 95% CI [{fmt(high_env['mean_difference_ci95_low'])}, {fmt(high_env['mean_difference_ci95_high'])}]. For low-evidence stress images, bobcat utility was higher than CzechLynx, M_diff = {fmt(low_env['mean_difference_a_minus_b'])}, 95% CI [{fmt(low_env['mean_difference_ci95_low'])}, {fmt(low_env['mean_difference_ci95_high'])}]. This means the stress sets are not symmetric; CzechLynx low-evidence is more severe.

## 2. Pair-Level Evidence Propagation

High-confidence within-context pair comparability differed between bobcat and CzechLynx by M_diff bobcat-CzechLynx = {fmt(high_pair_cmp['mean_difference_a_minus_b'])}, 95% CI [{fmt(high_pair_cmp['mean_difference_ci95_low'])}, {fmt(high_pair_cmp['mean_difference_ci95_high'])}], Cliff's delta = {fmt(high_pair_cmp['cliffs_delta'])}.

Low-evidence within-context pair comparability differed more strongly, M_diff bobcat-CzechLynx = {fmt(low_pair_cmp['mean_difference_a_minus_b'])}, 95% CI [{fmt(low_pair_cmp['mean_difference_ci95_low'])}, {fmt(low_pair_cmp['mean_difference_ci95_high'])}], Cliff's delta = {fmt(low_pair_cmp['cliffs_delta'])}. This supports the propagation claim: image-level stress becomes pair-level non-comparability.

## 3. CzechLynx Known-ID Validation

In high-confidence CzechLynx pairs, descriptor similarity separated known positives from known negatives: positive M = {fmt(high_val['positive_descriptor_similarity_mean'])}, negative M = {fmt(high_val['negative_descriptor_similarity_mean'])}, AUC = {fmt(high_val['auc_descriptor_similarity_for_true_positive'])}. Pair comparability alone did not strongly distinguish identity in this clean block, AUC = {fmt(high_val['auc_pair_comparability_for_true_positive'])}, which is expected because comparability measures evidence admissibility, not identity.

In CzechLynx low-evidence stress pairs, descriptor similarity still separated positives from negatives, AUC = {fmt(low_val['auc_descriptor_similarity_for_true_positive'])}, but conflict score was also higher for positives, AUC conflict-for-positive = {fmt(low_val['auc_conflict_score_for_true_positive'])}. This is the important caution: descriptor-evidence conflict is not a false-only detector. It flags high descriptor support under weak visual admissibility, including true same-identity pairs that should be reviewed rather than automatically accepted.

For high-low CzechLynx pairs, descriptor AUC was {fmt(cross_val['auc_descriptor_similarity_for_true_positive'])}, while conflict AUC-for-positive was {fmt(cross_val['auc_conflict_score_for_true_positive'])}. This supports the review-control framing more than a simple false-match classifier framing.

## 4. Descriptor-Evidence Conflict and Review Burden

Bobcat low-evidence stress pairs had high-conflict rate {fmt(bobcat_low_burden['high_conflict_rate'])}; CzechLynx low-evidence stress pairs had high-conflict rate {fmt(czech_low_burden['high_conflict_rate'])}. Because bobcat identity is unknown, this is evidence of conflict pressure and review burden, not false-match accuracy.

The CzechLynx conflict rule did not enrich false candidates. In high-low CzechLynx pairs, conflict-rule flagged false rate = {fmt(high_low_conflict['false_rate_flagged'])}, unflagged false rate = {fmt(high_low_conflict['false_rate_unflagged'])}, risk difference = {fmt(high_low_conflict['risk_difference_flagged_minus_unflagged'])}, OR = {fmt(high_low_conflict['odds_ratio_false_candidate'])}. In low-evidence CzechLynx pairs, conflict-rule flagged false rate = {fmt(low_conflict['false_rate_flagged'])}, unflagged false rate = {fmt(low_conflict['false_rate_unflagged'])}, risk difference = {fmt(low_conflict['risk_difference_flagged_minus_unflagged'])}. This result blocks any claim that conflict is a direct false-positive detector.

The useful interpretation is stronger and more precise: conflict marks high descriptor support under weak visual admissibility. For low-evidence CzechLynx high-descriptor pairs, applying a pair-comparability threshold of 0.40 retained {fmt(low_gate['retained_pair_coverage'])} of high-descriptor pairs, retained {fmt(low_gate['positive_retention_among_high_descriptor'])} of high-descriptor positives, and retained {fmt(low_gate['false_retention_among_high_descriptor'])} of high-descriptor false candidates. This quantifies the review-coverage tradeoff rather than pretending the rule automatically detects false matches.

## Interpretation

The results support a stronger version of the project logic than image filtering alone. The useful contribution is not simply selecting clear photos. The contribution is modeling how evidence utility changes from image level to pair comparability, then identifying where fixed descriptor support conflicts with weak visual admissibility.

The main limitation is also clear and scientifically useful: conflict should not be described as a direct false-positive detector. In low-evidence known-ID CzechLynx, true positive pairs can have high conflict because descriptor similarity remains high while visual evidence is weak. The defensible claim is therefore risk-controlled review routing: accept/review/defer/species-level, not automatic identity classification.

## Output Tables

- `{rel(IMAGE_SUMMARY)}`
- `{rel(PAIR_SUMMARY)}`
- `{rel(CZECH_VALIDATION)}`
- `{rel(CONFLICT_ENRICHMENT)}`
- `{rel(REVIEW_BURDEN)}`
- `{rel(DECISION_VALIDATION)}`
- `{rel(RISK_COVERAGE)}`
"""
    REPORT_MD.write_text(text, encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not IMAGE_TABLE.exists():
        raise FileNotFoundError(f"Missing image table: {IMAGE_TABLE}")
    if not CONFLICT_TABLE.exists():
        raise FileNotFoundError(f"Missing conflict table: {CONFLICT_TABLE}")

    images = pd.read_csv(IMAGE_TABLE, low_memory=False)
    conflict = pd.read_csv(CONFLICT_TABLE, low_memory=False)

    image_summary, image_comparisons = build_image_analysis(images)
    image_out = image_summary.merge(pd.DataFrame(), how="cross") if False else image_summary
    image_out.to_csv(IMAGE_SUMMARY, index=False)
    image_comparisons.to_csv(OUT_DIR / "phase14_image_level_2x2_comparisons.csv", index=False)

    pair_summary, pair_comparisons = build_pair_analysis(conflict)
    pair_summary.to_csv(PAIR_SUMMARY, index=False)
    pair_comparisons.to_csv(OUT_DIR / "phase14_pair_level_block_comparisons.csv", index=False)

    czech_validation = build_czech_validation(conflict)
    czech_validation.to_csv(CZECH_VALIDATION, index=False)

    enrichment = build_conflict_enrichment(conflict)
    enrichment.to_csv(CONFLICT_ENRICHMENT, index=False)

    burden = build_review_burden(conflict)
    burden.to_csv(REVIEW_BURDEN, index=False)

    decision_validation = build_czech_decision_validation(conflict)
    decision_validation.to_csv(DECISION_VALIDATION, index=False)

    risk_coverage = build_czech_risk_coverage(conflict)
    risk_coverage.to_csv(RISK_COVERAGE, index=False)

    write_report(
        image_summary,
        image_comparisons,
        pair_summary,
        pair_comparisons,
        czech_validation,
        enrichment,
        burden,
        decision_validation,
        risk_coverage,
    )

    audit = {
        "status": "complete",
        "inputs": {
            "image_table": rel(IMAGE_TABLE),
            "descriptor_conflict_table": rel(CONFLICT_TABLE),
        },
        "outputs": {
            "image_summary": rel(IMAGE_SUMMARY),
            "image_comparisons": rel(OUT_DIR / "phase14_image_level_2x2_comparisons.csv"),
            "pair_summary": rel(PAIR_SUMMARY),
            "pair_comparisons": rel(OUT_DIR / "phase14_pair_level_block_comparisons.csv"),
            "czech_validation": rel(CZECH_VALIDATION),
            "conflict_enrichment": rel(CONFLICT_ENRICHMENT),
            "review_burden": rel(REVIEW_BURDEN),
            "decision_validation": rel(DECISION_VALIDATION),
            "risk_coverage": rel(RISK_COVERAGE),
            "report": rel(REPORT_MD),
            "audit": rel(AUDIT_JSON),
        },
        "row_counts": {
            "image_table": int(len(images)),
            "descriptor_conflict_table": int(len(conflict)),
            "image_summary": int(len(image_summary)),
            "image_comparisons": int(len(image_comparisons)),
            "pair_summary": int(len(pair_summary)),
            "pair_comparisons": int(len(pair_comparisons)),
            "czech_validation": int(len(czech_validation)),
            "conflict_enrichment": int(len(enrichment)),
            "review_burden": int(len(burden)),
            "decision_validation": int(len(decision_validation)),
            "risk_coverage": int(len(risk_coverage)),
        },
        "method": {
            "bootstrap_iterations": BOOTSTRAP_N,
            "random_seed": RANDOM_SEED,
            "primary_tests": ["Mann-Whitney U", "Cliff's delta", "bootstrap 95% CI", "ROC AUC", "odds ratio"],
            "pair_independence_warning": "pair rows reuse images; pair-level p-values should not be interpreted as independent biological replication",
        },
        "scientific_boundary": {
            "bobcat": "identity_unknown; comparability/conflict-pressure/review-burden only",
            "czechlynx": "known-ID validation available for sampled same/different pairs",
        },
    }
    AUDIT_JSON.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
