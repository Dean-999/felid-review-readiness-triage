#!/usr/bin/env python3
"""Run Phase 7A PF-ERI Control variant search and clustered confidence audit."""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_CSV = PROJECT_ROOT / "outputs/czechlynx/phase7a/descriptor_supported_pf_eri/phase7a_descriptor_supported_pair_scores.csv"
PAIR_TABLE_CSV = PROJECT_ROOT / "outputs/czechlynx/phase7a/pair_tables/phase7a_1000_image_pair_table_v1.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase7a/pf_eri_algorithm_confidence_audit"
FIGURE_DIR = OUTPUT_DIR / "figures"

GRID_CSV = OUTPUT_DIR / "phase7a_pf_eri_algorithm_variant_grid.csv"
TOP_CANDIDATES_CSV = OUTPUT_DIR / "phase7a_pf_eri_top_candidate_rules.csv"
UNCERTAINTY_CSV = OUTPUT_DIR / "phase7a_pf_eri_clustered_uncertainty_intervals.csv"
AUC_UNCERTAINTY_CSV = OUTPUT_DIR / "phase7a_pf_eri_descriptor_auc_uncertainty.csv"
CALIBRATION_CSV = OUTPUT_DIR / "phase7a_pf_eri_calibration_bins.csv"
FAILURE_MODE_CSV = OUTPUT_DIR / "phase7a_pf_eri_failure_mode_audit.csv"
READINESS_CSV = OUTPUT_DIR / "phase7a_pf_eri_algorithm_readiness_decision.csv"

BOOTSTRAP_N = 500
RANDOM_SEED = 20260614
CLUSTER_UNIT = "image_endpoint_primary_cluster"

DESCRIPTORS = {"megadescriptor": "megadescriptor_similarity", "resnet50": "resnet50_similarity"}
VISUAL_GATES = ["none", "low_or_higher", "medium_or_higher", "high_only"]
VARIANT_ORDER = {
    "A_descriptor_only_baseline": 1,
    "B_visual_gate_megadescriptor": 2,
    "C_visual_gate_megadescriptor_failure_defer": 3,
    "D_dual_descriptor_agreement": 4,
    "E_conservative_uncertainty_ready_candidate": 5,
}


@dataclass(frozen=True)
class RuleConfig:
    variant_family: str
    descriptor_used: str
    megadescriptor_threshold: float | None
    resnet50_threshold: float | None
    visual_gate_type: str
    visual_threshold: float | None
    failure_defer_enabled: bool
    descriptor_agreement_enabled: bool


def clean_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.lower()


def quantile_thresholds(series: pd.Series, n: int = 60) -> list[float]:
    qs = np.linspace(0.0, 0.99, n)
    return sorted({round(float(series.quantile(q)), 6) for q in qs})


def rank_auc(labels: pd.Series, scores: pd.Series) -> float:
    y = labels.map({"yes": 1, "no": 0}).astype(int)
    n_pos = int(y.sum())
    n_neg = int((1 - y).sum())
    if n_pos == 0 or n_neg == 0:
        return math.nan
    ranks = scores.rank(method="average")
    rank_sum_pos = float(ranks[y == 1].sum())
    return float((rank_sum_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg))


def ci(values: list[float]) -> tuple[float, float]:
    clean = np.array([value for value in values if not math.isnan(value)], dtype=float)
    if len(clean) == 0:
        return math.nan, math.nan
    return float(np.percentile(clean, 2.5)), float(np.percentile(clean, 97.5))


def load_modeling_data(input_csv: Path, pair_table_csv: Path) -> pd.DataFrame:
    scores = pd.read_csv(input_csv)
    pairs = pd.read_csv(pair_table_csv)[
        [
            "pair_id",
            "image_id_a",
            "image_id_b",
            "pair_pattern_min",
            "pair_blur_worst",
            "pair_occlusion_worst",
            "pair_has_frontal_or_rear",
            "pair_has_partial_body",
            "pair_has_side_unknown",
        ]
    ]
    df = scores.merge(pairs, on="pair_id", how="left", validate="one_to_one")
    df["same_identity"] = clean_series(df["same_identity"])
    df["visual_band"] = clean_series(df["visual_band"])
    df["pair_side_compatible"] = clean_series(df["pair_side_compatible"])
    df["same_binary"] = (df["same_identity"] == "yes").astype(int)
    df["different_binary"] = (df["same_identity"] == "no").astype(int)
    df["megadescriptor_similarity"] = pd.to_numeric(df["megadescriptor_similarity"], errors="raise")
    df["resnet50_similarity"] = pd.to_numeric(df["resnet50_similarity"], errors="raise")
    df["visual_pf_eri_weighted"] = pd.to_numeric(df["visual_pf_eri_weighted"], errors="raise")
    df["megadescriptor_percentile"] = df["megadescriptor_similarity"].rank(method="average", pct=True)
    df["resnet50_percentile"] = df["resnet50_similarity"].rank(method="average", pct=True)
    df["descriptor_percentile_gap"] = (df["megadescriptor_percentile"] - df["resnet50_percentile"]).abs()
    df["descriptor_agreement_high"] = (
        (df["megadescriptor_percentile"] >= 0.80) & (df["resnet50_percentile"] >= 0.80)
    )
    df["descriptor_disagreement"] = df["descriptor_percentile_gap"] >= 0.35
    df["high_descriptor_low_visual"] = (
        df["any_high_descriptor_low_visual_flag"].astype(str).str.lower() == "yes"
    )
    df["side_incompatible"] = df["pair_side_compatible"] == "no"
    df["side_unknown"] = df["pair_side_compatible"] == "unknown"
    df["pattern_none"] = df["pair_pattern_min"].astype(str).str.lower() == "none"
    df["severe_blur"] = df["pair_blur_worst"].astype(str).str.lower() == "severe"
    df["major_occlusion"] = df["pair_occlusion_worst"].astype(str).str.lower() == "major"
    df["frontal_or_rear"] = df["pair_has_frontal_or_rear"].astype(str).str.lower() == "yes"
    df["silhouette_only"] = df["primary_limiting_factor_for_score"].astype(str).str.lower() == "silhouette_only"
    df["severe_visual_failure"] = (
        df["pattern_none"]
        | df["severe_blur"]
        | df["major_occlusion"]
        | df["frontal_or_rear"]
        | df["silhouette_only"]
    )
    df["low_visual_side_problem"] = df["visual_band"].isin(["low", "unusable"]) & (
        df["side_incompatible"] | df["side_unknown"]
    )
    df["endpoint_primary_cluster"] = df[["image_id_a", "image_id_b"]].min(axis=1)
    return df


def visual_mask(df: pd.DataFrame, gate_type: str, visual_threshold: float | None = None) -> pd.Series:
    if gate_type == "none":
        return pd.Series(True, index=df.index)
    if gate_type == "low_or_higher":
        return df["visual_band"].isin(["high", "medium", "low"])
    if gate_type == "medium_or_higher":
        return df["visual_band"].isin(["high", "medium"])
    if gate_type == "high_only":
        return df["visual_band"].eq("high")
    if gate_type == "numeric_threshold":
        if visual_threshold is None:
            raise ValueError("numeric visual gate requires visual_threshold")
        return df["visual_pf_eri_weighted"] >= visual_threshold
    raise ValueError(f"unknown visual gate: {gate_type}")


def descriptor_mask(df: pd.DataFrame, config: RuleConfig) -> pd.Series:
    mask = pd.Series(True, index=df.index)
    if config.descriptor_used in {"megadescriptor", "dual"} and config.megadescriptor_threshold is not None:
        mask &= df["megadescriptor_similarity"] >= config.megadescriptor_threshold
    if config.descriptor_used in {"resnet50", "dual"} and config.resnet50_threshold is not None:
        mask &= df["resnet50_similarity"] >= config.resnet50_threshold
    if config.descriptor_agreement_enabled:
        mask &= ~df["descriptor_disagreement"]
    return mask


def base_selected_mask(df: pd.DataFrame, config: RuleConfig) -> pd.Series:
    return visual_mask(df, config.visual_gate_type, config.visual_threshold) & descriptor_mask(df, config)


def defer_mask(df: pd.DataFrame, config: RuleConfig) -> pd.Series:
    if not config.failure_defer_enabled:
        return pd.Series(False, index=df.index)
    severe = df["severe_visual_failure"]
    caution = df["high_descriptor_low_visual"] | df["low_visual_side_problem"]
    disagreement = df["descriptor_disagreement"] & df["visual_band"].isin(["low", "unusable"])
    return severe | caution | disagreement


def selected_mask(df: pd.DataFrame, config: RuleConfig) -> pd.Series:
    base = base_selected_mask(df, config)
    if config.failure_defer_enabled:
        return base & ~defer_mask(df, config)
    return base


def metric_dict(df: pd.DataFrame, config: RuleConfig, variant_id: str) -> dict[str, object]:
    base = base_selected_mask(df, config)
    defer = base & defer_mask(df, config)
    selected = selected_mask(df, config)
    excluded = base & df["severe_visual_failure"] if config.failure_defer_enabled else pd.Series(False, index=df.index)
    selected_df = df[selected]
    total = len(df)
    total_same = int((df["same_identity"] == "yes").sum())
    total_different = int((df["same_identity"] == "no").sum())
    selected_count = int(selected.sum())
    same_count = int((selected_df["same_identity"] == "yes").sum())
    different_count = int((selected_df["same_identity"] == "no").sum())
    false_rate = different_count / selected_count if selected_count else math.nan
    same_prop = same_count / selected_count if selected_count else math.nan
    interpretation = interpret_rule(selected_count, selected_count / total if total else 0.0, false_rate, config)
    return {
        "variant_id": variant_id,
        "variant_family": config.variant_family,
        "descriptor_used": config.descriptor_used,
        "megadescriptor_threshold": config.megadescriptor_threshold,
        "resnet50_threshold": config.resnet50_threshold,
        "visual_gate_type": config.visual_gate_type,
        "visual_threshold": config.visual_threshold,
        "failure_defer_enabled": "yes" if config.failure_defer_enabled else "no",
        "descriptor_agreement_enabled": "yes" if config.descriptor_agreement_enabled else "no",
        "selected_count": selected_count,
        "coverage": selected_count / total if total else math.nan,
        "selected_same_count": same_count,
        "selected_different_count": different_count,
        "selected_same_proportion": same_prop,
        "false_support_rate": false_rate,
        "same_accept_rate": same_count / total_same if total_same else math.nan,
        "different_accept_rate": different_count / total_different if total_different else math.nan,
        "high_descriptor_low_visual_selected_count": int((selected & df["high_descriptor_low_visual"]).sum()),
        "high_descriptor_low_visual_false_count": int((selected & df["high_descriptor_low_visual"] & (df["same_identity"] == "no")).sum()),
        "side_incompatible_selected_count": int((selected & df["side_incompatible"]).sum()),
        "side_unknown_selected_count": int((selected & df["side_unknown"]).sum()),
        "severe_visual_failure_selected_count": int((selected & df["severe_visual_failure"]).sum()),
        "defer_candidate_count": int(defer.sum()),
        "exclude_candidate_count": int(excluded.sum()),
        "interpretation": interpretation,
    }


def interpret_rule(selected_count: int, coverage: float, false_rate: float, config: RuleConfig) -> str:
    if selected_count == 0:
        return "no selected pairs; not useful as a candidate rule"
    if coverage < 0.03:
        return "trivial coverage; do not select solely on low false-support rate"
    if false_rate <= 0.30:
        target = "strict exploratory target met"
    elif false_rate <= 0.40:
        target = "moderate exploratory target met"
    elif false_rate <= 0.50:
        target = "exploratory target met with strong caveat"
    else:
        target = "false-support rate remains high"
    if config.variant_family.startswith("A_"):
        return f"{target}; descriptor-only baseline, not PF-ERI Control"
    if config.failure_defer_enabled:
        return f"{target}; staged PF-ERI with failure-mode defer"
    return f"{target}; staged PF-ERI candidate without explicit failure defer"


def make_configs(df: pd.DataFrame) -> list[RuleConfig]:
    mega_thresholds = quantile_thresholds(df["megadescriptor_similarity"], 60)
    resnet_thresholds = quantile_thresholds(df["resnet50_similarity"], 60)
    visual_thresholds = quantile_thresholds(df["visual_pf_eri_weighted"], 12)
    agreement_resnet_thresholds = quantile_thresholds(df["resnet50_similarity"], 8)
    configs: list[RuleConfig] = []
    for threshold in mega_thresholds:
        configs.append(RuleConfig("A_descriptor_only_baseline", "megadescriptor", threshold, None, "none", None, False, False))
    for threshold in resnet_thresholds:
        configs.append(RuleConfig("A_descriptor_only_baseline", "resnet50", None, threshold, "none", None, False, False))
    for threshold in mega_thresholds:
        for gate in VISUAL_GATES:
            configs.append(RuleConfig("B_visual_gate_megadescriptor", "megadescriptor", threshold, None, gate, None, False, False))
        for visual_threshold in visual_thresholds:
            configs.append(
                RuleConfig(
                    "B_visual_gate_megadescriptor",
                    "megadescriptor",
                    threshold,
                    None,
                    "numeric_threshold",
                    visual_threshold,
                    False,
                    False,
                )
            )
    for threshold in mega_thresholds:
        for gate in ["low_or_higher", "medium_or_higher", "high_only"]:
            configs.append(RuleConfig("C_visual_gate_megadescriptor_failure_defer", "megadescriptor", threshold, None, gate, None, True, False))
        for visual_threshold in visual_thresholds[3:]:
            configs.append(
                RuleConfig(
                    "C_visual_gate_megadescriptor_failure_defer",
                    "megadescriptor",
                    threshold,
                    None,
                    "numeric_threshold",
                    visual_threshold,
                    True,
                    False,
                )
            )
    for mega_threshold in mega_thresholds:
        for resnet_threshold in agreement_resnet_thresholds:
            for gate in ["low_or_higher", "medium_or_higher", "high_only"]:
                configs.append(
                    RuleConfig(
                        "D_dual_descriptor_agreement",
                        "dual",
                        mega_threshold,
                        resnet_threshold,
                        gate,
                        None,
                        True,
                        True,
                    )
                )
    for mega_threshold in mega_thresholds:
        for gate in ["medium_or_higher", "low_or_higher"]:
            configs.append(
                RuleConfig(
                    "E_conservative_uncertainty_ready_candidate",
                    "dual",
                    mega_threshold,
                    float(df["resnet50_similarity"].quantile(0.70)),
                    gate,
                    None,
                    True,
                    True,
                )
            )
    return configs


def build_grid(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    configs = make_configs(df)
    for idx, config in enumerate(configs, start=1):
        prefix = chr(ord("A") + VARIANT_ORDER[config.variant_family] - 1)
        variant_id = f"{prefix}_{idx:05d}"
        rows.append(metric_dict(df, config, variant_id))
    return pd.DataFrame(rows)


def select_top_candidates(grid: pd.DataFrame) -> pd.DataFrame:
    candidates = grid[grid["selected_count"] >= 75].copy()
    candidates = candidates[candidates["coverage"] >= 0.03].copy()
    candidates = candidates.sort_values(
        [
            "false_support_rate",
            "coverage",
            "high_descriptor_low_visual_selected_count",
            "severe_visual_failure_selected_count",
        ],
        ascending=[True, False, True, True],
    )
    diversified: list[pd.Series] = []
    seen_families: set[str] = set()
    for _, row in candidates.iterrows():
        if row["variant_family"] not in seen_families:
            diversified.append(row)
            seen_families.add(str(row["variant_family"]))
        if len(diversified) >= 5:
            break
    for _, row in candidates.iterrows():
        if row["variant_id"] not in {r["variant_id"] for r in diversified}:
            diversified.append(row)
        if len(diversified) >= 12:
            break
    rows = []
    for rank, row in enumerate(diversified, start=1):
        concern = concern_level(row)
        rows.append(
            {
                "candidate_rank": rank,
                "variant_id": row["variant_id"],
                "variant_family": row["variant_family"],
                "reason_selected": selection_reason(row),
                "coverage": row["coverage"],
                "false_support_rate": row["false_support_rate"],
                "selected_same_proportion": row["selected_same_proportion"],
                "selected_count": row["selected_count"],
                "failure_mode_counts": (
                    f"high_descriptor_low_visual={row['high_descriptor_low_visual_selected_count']}; "
                    f"side_incompatible={row['side_incompatible_selected_count']}; "
                    f"side_unknown={row['side_unknown_selected_count']}; "
                    f"severe_visual_failure={row['severe_visual_failure_selected_count']}"
                ),
                "concern_level": concern,
                "recommended_next_status": recommended_status(row, concern),
            }
        )
    return pd.DataFrame(rows)


def concern_level(row: pd.Series) -> str:
    if row["coverage"] < 0.05:
        return "high_tiny_coverage"
    if row["false_support_rate"] > 0.50:
        return "high_false_support"
    if row["false_support_rate"] > 0.40:
        return "moderate_false_support"
    if row["high_descriptor_low_visual_selected_count"] > 0 or row["severe_visual_failure_selected_count"] > 0:
        return "moderate_failure_mode_residual"
    return "lower_with_current_data"


def selection_reason(row: pd.Series) -> str:
    if str(row["variant_family"]).startswith("A_"):
        return "best descriptor-only baseline retained for comparison, not final algorithm"
    if str(row["variant_family"]).startswith("C_"):
        return "failure-mode defer rule with competitive risk-coverage behavior"
    if str(row["variant_family"]).startswith("D_"):
        return "dual-descriptor agreement candidate for robustness comparison"
    if str(row["variant_family"]).startswith("E_"):
        return "conservative readiness candidate for later policy optimization"
    return "visual-gated staged PF-ERI candidate with nontrivial coverage"


def recommended_status(row: pd.Series, concern: str) -> str:
    if concern in {"high_tiny_coverage", "high_false_support"}:
        return "do_not_optimize_as_final; retain as diagnostic"
    if str(row["variant_family"]).startswith("A_"):
        return "baseline_only"
    return "carry_to_slice7_policy_optimization_after_uncertainty_review"


def row_metric_values(df: pd.DataFrame, row: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    config = RuleConfig(
        variant_family=str(row["variant_family"]),
        descriptor_used=str(row["descriptor_used"]),
        megadescriptor_threshold=None if pd.isna(row["megadescriptor_threshold"]) else float(row["megadescriptor_threshold"]),
        resnet50_threshold=None if pd.isna(row["resnet50_threshold"]) else float(row["resnet50_threshold"]),
        visual_gate_type=str(row["visual_gate_type"]),
        visual_threshold=None if pd.isna(row["visual_threshold"]) else float(row["visual_threshold"]),
        failure_defer_enabled=str(row["failure_defer_enabled"]) == "yes",
        descriptor_agreement_enabled=str(row["descriptor_agreement_enabled"]) == "yes",
    )
    base = base_selected_mask(df, config)
    defer = base & defer_mask(df, config)
    selected = selected_mask(df, config)
    return selected, defer, base


def metrics_for_mask(df: pd.DataFrame, selected: pd.Series) -> dict[str, float]:
    selected_df = df[selected]
    selected_count = int(selected.sum())
    same = int((selected_df["same_identity"] == "yes").sum())
    different = int((selected_df["same_identity"] == "no").sum())
    total_same = int((df["same_identity"] == "yes").sum())
    return {
        "coverage": selected_count / len(df) if len(df) else math.nan,
        "false_support_rate": different / selected_count if selected_count else math.nan,
        "selected_same_proportion": same / selected_count if selected_count else math.nan,
        "same_accept_rate": same / total_same if total_same else math.nan,
        "high_descriptor_low_visual_false_case_rate": int((selected & df["high_descriptor_low_visual"] & (df["same_identity"] == "no")).sum()) / selected_count
        if selected_count
        else math.nan,
    }


def bootstrap_cluster_samples(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    clusters = df["endpoint_primary_cluster"].dropna().unique()
    sampled = rng.choice(clusters, size=len(clusters), replace=True)
    parts = []
    for cluster in sampled:
        parts.append(df[df["endpoint_primary_cluster"] == cluster])
    return pd.concat(parts, ignore_index=True)


def clustered_uncertainty(df: pd.DataFrame, grid: pd.DataFrame, top: pd.DataFrame, bootstrap_n: int) -> pd.DataFrame:
    rng = np.random.default_rng(RANDOM_SEED)
    top_rows = grid[grid["variant_id"].isin(top["variant_id"])].copy()
    estimates: dict[str, dict[str, float]] = {}
    for _, row in top_rows.iterrows():
        selected, _, _ = row_metric_values(df, row)
        estimates[str(row["variant_id"])] = metrics_for_mask(df, selected)
    boot_values: dict[tuple[str, str], list[float]] = {
        (variant_id, metric): [] for variant_id in estimates for metric in estimates[variant_id]
    }
    for _ in range(bootstrap_n):
        sample = bootstrap_cluster_samples(df, rng)
        for _, row in top_rows.iterrows():
            selected, _, _ = row_metric_values(sample, row)
            values = metrics_for_mask(sample, selected)
            for metric, value in values.items():
                boot_values[(str(row["variant_id"]), metric)].append(value)
    rows = []
    for variant_id, metric_values in estimates.items():
        for metric, estimate in metric_values.items():
            lower, upper = ci(boot_values[(variant_id, metric)])
            rows.append(
                {
                    "variant_id": variant_id,
                    "metric": metric,
                    "estimate": estimate,
                    "ci_lower": lower,
                    "ci_upper": upper,
                    "bootstrap_n": bootstrap_n,
                    "cluster_unit": CLUSTER_UNIT,
                    "interpretation": uncertainty_interpretation(metric, estimate, lower, upper),
                }
            )
    return pd.DataFrame(rows)


def uncertainty_interpretation(metric: str, estimate: float, lower: float, upper: float) -> str:
    if metric == "false_support_rate":
        if math.isnan(upper):
            return "not estimable"
        if upper <= 0.30:
            return "strict exploratory target stable under clustered bootstrap"
        if upper <= 0.40:
            return "moderate exploratory target stable under clustered bootstrap"
        if upper <= 0.50:
            return "only exploratory target stable; strong caveat"
        return "clustered interval remains above exploratory risk targets"
    if metric == "coverage" and estimate < 0.05:
        return "coverage is small; avoid threshold overinterpretation"
    return "clustered interval reported for confidence audit"


def auc_uncertainty(df: pd.DataFrame, bootstrap_n: int) -> pd.DataFrame:
    rng = np.random.default_rng(RANDOM_SEED + 1)
    estimates = {
        descriptor: rank_auc(df["same_identity"], df[column]) for descriptor, column in DESCRIPTORS.items()
    }
    boot = {descriptor: [] for descriptor in DESCRIPTORS}
    for _ in range(bootstrap_n):
        sample = bootstrap_cluster_samples(df, rng)
        for descriptor, column in DESCRIPTORS.items():
            boot[descriptor].append(rank_auc(sample["same_identity"], sample[column]))
    rows = []
    for descriptor in ["megadescriptor", "resnet50"]:
        lower, upper = ci(boot[descriptor])
        other = "resnet50" if descriptor == "megadescriptor" else "megadescriptor"
        comparison = estimates[descriptor] - estimates[other]
        rows.append(
            {
                "descriptor": descriptor,
                "AUC_estimate": estimates[descriptor],
                "CI_lower": lower,
                "CI_upper": upper,
                "bootstrap_n": bootstrap_n,
                "cluster_unit": CLUSTER_UNIT,
                "comparison_to_other_descriptor": f"AUC difference vs {other}: {comparison:.4f}",
            }
        )
    diffs = np.array(boot["megadescriptor"]) - np.array(boot["resnet50"])
    lower, upper = ci(diffs.tolist())
    rows.append(
        {
            "descriptor": "megadescriptor_minus_resnet50",
            "AUC_estimate": estimates["megadescriptor"] - estimates["resnet50"],
            "CI_lower": lower,
            "CI_upper": upper,
            "bootstrap_n": bootstrap_n,
            "cluster_unit": CLUSTER_UNIT,
            "comparison_to_other_descriptor": "positive values favor MegaDescriptor",
        }
    )
    return pd.DataFrame(rows)


def calibration_bins(df: pd.DataFrame, top_grid: pd.DataFrame) -> pd.DataFrame:
    rows = []
    variants = [
        ("MegaDescriptor descriptor-only", "megadescriptor", df.index.to_series().map(lambda _: True), df["megadescriptor_similarity"]),
        (
            "Visual gate + MegaDescriptor",
            "megadescriptor",
            df["visual_band"].isin(["high", "medium"]),
            df["megadescriptor_similarity"],
        ),
        (
            "Visual gate + MegaDescriptor + failure-mode defer",
            "megadescriptor",
            df["visual_band"].isin(["high", "medium"]) & ~defer_mask(
                df,
                RuleConfig("C_visual_gate_megadescriptor_failure_defer", "megadescriptor", None, None, "medium_or_higher", None, True, False),
            ),
            df["megadescriptor_similarity"],
        ),
        (
            "Dual-descriptor agreement variant",
            "dual",
            df["visual_band"].isin(["high", "medium"]) & ~df["descriptor_disagreement"],
            (df["megadescriptor_percentile"] + df["resnet50_percentile"]) / 2,
        ),
    ]
    for family, descriptor, eligible_mask, score in variants:
        subset = df[eligible_mask].copy()
        subset["_calibration_score"] = score[eligible_mask]
        if subset.empty:
            continue
        try:
            subset["_bin"] = pd.qcut(subset["_calibration_score"], q=8, duplicates="drop")
        except ValueError:
            continue
        for bin_id, (interval, group) in enumerate(subset.groupby("_bin", observed=True), start=1):
            same = int((group["same_identity"] == "yes").sum())
            different = int((group["same_identity"] == "no").sum())
            count = len(group)
            rows.append(
                {
                    "variant_family": family,
                    "descriptor_used": descriptor,
                    "bin_id": bin_id,
                    "bin_lower": float(interval.left),
                    "bin_upper": float(interval.right),
                    "pair_count": count,
                    "same_count": same,
                    "different_count": different,
                    "observed_same_proportion": same / count if count else math.nan,
                    "observed_false_support_rate": different / count if count else math.nan,
                    "mean_MegaDescriptor_similarity": group["megadescriptor_similarity"].mean(),
                    "mean_visual_PF_ERI": group["visual_pf_eri_weighted"].mean(),
                    "sparse_bin_flag": "yes" if count < 30 else "no",
                    "interpretation": "empirical calibration bin only; not deployment probability",
                }
            )
    return pd.DataFrame(rows)


def failure_mode_audit(df: pd.DataFrame, top_grid: pd.DataFrame, bootstrap_n: int) -> pd.DataFrame:
    selected_union = pd.Series(False, index=df.index)
    for _, row in top_grid.iterrows():
        selected, _, _ = row_metric_values(df, row)
        selected_union |= selected
    modes = {
        "high_descriptor_low_visual": df["high_descriptor_low_visual"],
        "side_incompatible": df["side_incompatible"],
        "side_unknown": df["side_unknown"],
        "frontal_or_rear": df["frontal_or_rear"],
        "pattern_none": df["pattern_none"],
        "severe_blur": df["severe_blur"],
        "major_occlusion": df["major_occlusion"],
        "silhouette_only": df["silhouette_only"],
        "descriptor_disagreement": df["descriptor_disagreement"],
    }
    rng = np.random.default_rng(RANDOM_SEED + 2)
    boot_rates: dict[str, list[float]] = {mode: [] for mode in modes}
    for _ in range(min(bootstrap_n, 300)):
        sample = bootstrap_cluster_samples(df, rng)
        # Reconstruct selected union for the sampled rows using the same top rules.
        sample_selected = pd.Series(False, index=sample.index)
        for _, row in top_grid.iterrows():
            selected, _, _ = row_metric_values(sample, row)
            sample_selected |= selected
        for mode in modes:
            mode_mask = make_failure_mode_mask(sample, mode)
            denom = int((sample_selected & mode_mask).sum())
            value = (
                int((sample_selected & mode_mask & (sample["same_identity"] == "no")).sum()) / denom
                if denom
                else math.nan
            )
            boot_rates[mode].append(value)
    rows = []
    for mode, mask in modes.items():
        pair_count = int(mask.sum())
        selected_count = int((selected_union & mask).sum())
        different = int((selected_union & mask & (df["same_identity"] == "no")).sum())
        false_rate = different / selected_count if selected_count else math.nan
        lower, upper = ci(boot_rates[mode])
        rows.append(
            {
                "failure_mode": mode,
                "pair_count": pair_count,
                "selected_count_under_top_rules": selected_count,
                "false_support_rate": false_rate,
                "ci_lower": lower,
                "ci_upper": upper,
                "bootstrap_n": min(bootstrap_n, 300),
                "cluster_unit": CLUSTER_UNIT,
                "recommendation": failure_recommendation(mode, pair_count, selected_count, false_rate, upper),
            }
        )
    return pd.DataFrame(rows)


def make_failure_mode_mask(df: pd.DataFrame, mode: str) -> pd.Series:
    return {
        "high_descriptor_low_visual": df["high_descriptor_low_visual"],
        "side_incompatible": df["side_incompatible"],
        "side_unknown": df["side_unknown"],
        "frontal_or_rear": df["frontal_or_rear"],
        "pattern_none": df["pattern_none"],
        "severe_blur": df["severe_blur"],
        "major_occlusion": df["major_occlusion"],
        "silhouette_only": df["silhouette_only"],
        "descriptor_disagreement": df["descriptor_disagreement"],
    }[mode]


def failure_recommendation(mode: str, pair_count: int, selected_count: int, false_rate: float, upper: float) -> str:
    if pair_count < 30:
        return "needs more data"
    if mode in {"pattern_none", "severe_blur", "major_occlusion", "silhouette_only"}:
        return "defer_or_exclude"
    if selected_count == 0:
        return "defer"
    if not math.isnan(upper) and upper > 0.50:
        return "defer"
    return "allow_with_caution"


def readiness_decision(
    grid: pd.DataFrame,
    top: pd.DataFrame,
    uncertainty: pd.DataFrame,
    auc_df: pd.DataFrame,
    calibration: pd.DataFrame,
    failure_modes: pd.DataFrame,
) -> pd.DataFrame:
    auc_diff = auc_df[auc_df["descriptor"] == "megadescriptor_minus_resnet50"].iloc[0]
    best = top.iloc[0]
    false_ci = uncertainty[(uncertainty["variant_id"] == best["variant_id"]) & (uncertainty["metric"] == "false_support_rate")]
    false_ci_text = "not available" if false_ci.empty else f"{false_ci.iloc[0]['ci_lower']:.3f}-{false_ci.iloc[0]['ci_upper']:.3f}"
    sparse_bins = int((calibration["sparse_bin_flag"] == "yes").sum()) if not calibration.empty else 0
    rows = [
        {
            "decision_area": "evidence that MegaDescriptor is primary descriptor support",
            "result": "supported",
            "evidence": f"AUC difference MegaDescriptor-ResNet50={auc_diff['AUC_estimate']:.3f}, CI={auc_diff['CI_lower']:.3f}-{auc_diff['CI_upper']:.3f}",
            "concern_level": "low_to_moderate",
            "next_step": "use MegaDescriptor as primary fixed descriptor support while retaining ResNet50 as baseline/agreement signal",
        },
        {
            "decision_area": "evidence that ResNet50 should remain baseline/agreement signal",
            "result": "supported_as_secondary",
            "evidence": "ResNet50 has weaker AUC but provides disagreement and comparison signal",
            "concern_level": "moderate",
            "next_step": "keep ResNet50 for agreement diagnostics, not primary thresholding",
        },
        {
            "decision_area": "value of visual gate",
            "result": "supported_for_review_control_not_as_standalone_risk_reduction",
            "evidence": "visual gates structure reviewability and failure modes, but prior Slice 5 showed no uniform false-support reduction at matched coverage",
            "concern_level": "moderate",
            "next_step": "retain visual PF-ERI as first-stage evidence gate",
        },
        {
            "decision_area": "value of failure-mode defer",
            "result": "supported_for_algorithm_originality_and_caution",
            "evidence": "failure-defer variants explicitly remove high-descriptor low-visual and severe visual failure cases from automatic support",
            "concern_level": "moderate",
            "next_step": "carry failure-mode defer families into Slice 7 candidate optimization",
        },
        {
            "decision_area": "confidence interval stability",
            "result": "conditional",
            "evidence": f"top candidate false-support clustered CI={false_ci_text}",
            "concern_level": "moderate_to_high",
            "next_step": "use clustered intervals as hard reporting constraint in final policy optimization",
        },
        {
            "decision_area": "calibration adequacy",
            "result": "exploratory_only",
            "evidence": f"empirical bins generated; sparse bins={sparse_bins}",
            "concern_level": "moderate",
            "next_step": "do not claim calibrated deployment probability; use bins to guide policy diagnostics",
        },
        {
            "decision_area": "readiness for final policy optimization",
            "result": "conditional_go",
            "evidence": "candidate rule families are concrete and uncertainty intervals are available, but thresholds are not final",
            "concern_level": "moderate",
            "next_step": "proceed to Slice 7 final policy optimization only with CI-aware constraints",
        },
        {
            "decision_area": "need for open-set stress test",
            "result": "required_before_stronger_claims",
            "evidence": "current validation is closed-set same/different pair evidence",
            "concern_level": "high_for_transfer_claims",
            "next_step": "run open-set stress testing before conservation transfer claims",
        },
        {
            "decision_area": "need for targeted expansion to 1500/2000",
            "result": "not_immediate_for_global_rule_comparison",
            "evidence": "2619 eligible pairs support first-pass rule comparison, but rare failure modes remain sparse",
            "concern_level": "moderate_for_subgroups",
            "next_step": "targeted expansion only if Slice 7 requires rare failure-mode precision",
        },
        {
            "decision_area": "final recommended algorithm family",
            "result": "staged_visual_gate_plus_megadescriptor_plus_failure_defer_with_resnet50_agreement_diagnostics",
            "evidence": "best balance of interpretability, descriptor support, and explicit failure-mode control",
            "concern_level": "moderate",
            "next_step": "optimize review/defer/exclude candidates in Slice 7 without transfer or field-use claims",
        },
    ]
    return pd.DataFrame(rows)


def save_figures(
    grid: pd.DataFrame,
    top: pd.DataFrame,
    uncertainty: pd.DataFrame,
    auc_df: pd.DataFrame,
    calibration: pd.DataFrame,
    failure_modes: pd.DataFrame,
    df: pd.DataFrame,
) -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(9, 6))
    for family, group in grid.groupby("variant_family"):
        plt.scatter(group["coverage"], group["false_support_rate"], s=10, alpha=0.4, label=family.replace("_", " "))
    plt.xlabel("Coverage")
    plt.ylabel("False-support rate")
    plt.title("Risk-coverage frontier by PF-ERI variant family")
    plt.legend(fontsize=7)
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "risk_coverage_frontier_by_variant_family.png", dpi=160)
    plt.close()

    plt.figure(figsize=(10, 5))
    plt.bar(top["candidate_rank"].astype(str), top["false_support_rate"], color="#4C78A8")
    plt.xlabel("Candidate rank")
    plt.ylabel("False-support rate")
    plt.title("Top candidate rule comparison")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "top_candidate_rule_comparison.png", dpi=160)
    plt.close()

    false_ci = uncertainty[uncertainty["metric"] == "false_support_rate"].merge(top[["variant_id", "candidate_rank"]], on="variant_id")
    plt.figure(figsize=(10, 5))
    y = false_ci["candidate_rank"].astype(str)
    plt.errorbar(false_ci["estimate"], y, xerr=[false_ci["estimate"] - false_ci["ci_lower"], false_ci["ci_upper"] - false_ci["estimate"]], fmt="o")
    plt.xlabel("False-support rate")
    plt.ylabel("Candidate rank")
    plt.title("Clustered bootstrap intervals for false-support rate")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "clustered_bootstrap_false_support_intervals.png", dpi=160)
    plt.close()

    auc_only = auc_df[auc_df["descriptor"].isin(["megadescriptor", "resnet50"])]
    plt.figure(figsize=(7, 5))
    plt.errorbar(
        auc_only["descriptor"],
        auc_only["AUC_estimate"],
        yerr=[auc_only["AUC_estimate"] - auc_only["CI_lower"], auc_only["CI_upper"] - auc_only["AUC_estimate"]],
        fmt="o",
        capsize=5,
    )
    plt.ylim(0.45, 0.8)
    plt.ylabel("Rank AUC")
    plt.title("MegaDescriptor vs ResNet50 clustered AUC intervals")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "descriptor_auc_clustered_intervals.png", dpi=160)
    plt.close()

    plt.figure(figsize=(8, 5))
    for family, group in calibration.groupby("variant_family"):
        plt.plot(group["mean_MegaDescriptor_similarity"], group["observed_same_proportion"], marker="o", label=family)
    plt.xlabel("Mean MegaDescriptor similarity")
    plt.ylabel("Observed same-pair proportion")
    plt.title("Empirical calibration bins")
    plt.legend(fontsize=7)
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "calibration_reliability_top_variants.png", dpi=160)
    plt.close()

    plt.figure(figsize=(9, 5))
    plt.bar(failure_modes["failure_mode"], failure_modes["false_support_rate"].fillna(0.0), color="#E15759")
    plt.xticks(rotation=35, ha="right")
    plt.ylabel("False-support rate under top rules")
    plt.title("Failure-mode audit")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "high_descriptor_low_visual_failure_mode_plot.png", dpi=160)
    plt.close()

    comp = grid[grid["variant_family"].isin(["A_descriptor_only_baseline", "B_visual_gate_megadescriptor"])].copy()
    comp = comp[comp["descriptor_used"].isin(["megadescriptor"])]
    plt.figure(figsize=(8, 5))
    for label, group in comp.groupby("visual_gate_type"):
        plt.scatter(group["coverage"], group["false_support_rate"], s=12, alpha=0.5, label=label)
    plt.xlabel("Coverage")
    plt.ylabel("False-support rate")
    plt.title("Visual gate vs descriptor-only comparison")
    plt.legend(fontsize=7)
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "visual_gate_vs_descriptor_only_with_ci_context.png", dpi=160)
    plt.close()

    plt.figure(figsize=(8, 5))
    plt.scatter(grid["coverage"], grid["false_support_rate"], s=8, alpha=0.35, c=grid["selected_count"], cmap="viridis")
    plt.colorbar(label="Selected count")
    plt.xlabel("Coverage")
    plt.ylabel("False-support rate")
    plt.title("Coverage vs false-support rate for all candidate rules")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "coverage_vs_false_support_all_candidate_rules.png", dpi=160)
    plt.close()


def build(input_csv: Path, pair_table_csv: Path, output_dir: Path, bootstrap_n: int) -> dict[str, object]:
    df = load_modeling_data(input_csv, pair_table_csv)
    grid = build_grid(df)
    top = select_top_candidates(grid)
    top_grid = grid[grid["variant_id"].isin(top["variant_id"])]
    uncertainty = clustered_uncertainty(df, grid, top, bootstrap_n)
    auc_df = auc_uncertainty(df, bootstrap_n)
    calibration = calibration_bins(df, top_grid)
    failure_modes = failure_mode_audit(df, top_grid, bootstrap_n)
    readiness = readiness_decision(grid, top, uncertainty, auc_df, calibration, failure_modes)
    output_dir.mkdir(parents=True, exist_ok=True)
    grid.to_csv(GRID_CSV, index=False)
    top.to_csv(TOP_CANDIDATES_CSV, index=False)
    uncertainty.to_csv(UNCERTAINTY_CSV, index=False)
    auc_df.to_csv(AUC_UNCERTAINTY_CSV, index=False)
    calibration.to_csv(CALIBRATION_CSV, index=False)
    failure_modes.to_csv(FAILURE_MODE_CSV, index=False)
    readiness.to_csv(READINESS_CSV, index=False)
    save_figures(grid, top, uncertainty, auc_df, calibration, failure_modes, df)
    return {
        "eligible_pair_count": len(df),
        "candidate_rule_count": len(grid),
        "top_candidate_count": len(top),
        "cluster_unit": CLUSTER_UNIT,
        "bootstrap_n": bootstrap_n,
        "best_variant_id": top.iloc[0]["variant_id"] if len(top) else "",
        "best_false_support_rate": round(float(top.iloc[0]["false_support_rate"]), 4) if len(top) else math.nan,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-csv", type=Path, default=INPUT_CSV)
    parser.add_argument("--pair-table-csv", type=Path, default=PAIR_TABLE_CSV)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--bootstrap-n", type=int, default=BOOTSTRAP_N)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = build(args.input_csv.resolve(), args.pair_table_csv.resolve(), args.output_dir.resolve(), args.bootstrap_n)
    print("Phase 7A PF-ERI algorithm variant confidence audit complete")
    for key, value in summary.items():
        print(f"{key}: {value}")
    print(f"output_dir: {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
