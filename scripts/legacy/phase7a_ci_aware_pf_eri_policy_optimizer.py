#!/usr/bin/env python3
"""Optimize CI-aware PF-ERI Control review/defer/exclude policies."""

from __future__ import annotations

import argparse
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCORES_CSV = PROJECT_ROOT / "outputs/czechlynx/phase7a/descriptor_supported_pf_eri/phase7a_descriptor_supported_pair_scores.csv"
PAIR_TABLE_CSV = PROJECT_ROOT / "outputs/czechlynx/phase7a/pair_tables/phase7a_1000_image_pair_table_v1.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase7a/pf_eri_policy_optimization"
FIGURE_DIR = OUTPUT_DIR / "figures"

GRID_CSV = OUTPUT_DIR / "phase7a_pf_eri_policy_candidate_grid.csv"
TOP_CANDIDATES_CSV = OUTPUT_DIR / "phase7a_pf_eri_policy_top_candidates.csv"
ASSIGNMENT_TOP_CSV = OUTPUT_DIR / "phase7a_pf_eri_policy_assignment_top.csv"
REGIME_SUMMARY_CSV = OUTPUT_DIR / "phase7a_pf_eri_policy_regime_summary.csv"
FAILURE_MODE_SUMMARY_CSV = OUTPUT_DIR / "phase7a_pf_eri_policy_failure_mode_summary.csv"
CONFIDENCE_DECISION_CSV = OUTPUT_DIR / "phase7a_pf_eri_policy_confidence_decision.csv"

RANDOM_SEED = 20260614
BOOTSTRAP_N = 500
CLUSTER_UNIT = "image_endpoint_primary_cluster"

ASSIGNMENTS = ("review_candidate", "defer_candidate", "exclude_candidate")
REGIMES = {
    "strict": {"max_false": 0.30, "max_ci_upper": 0.40, "min_coverage": 0.03},
    "moderate": {"max_false": 0.40, "max_ci_upper": 0.50, "min_coverage": 0.05},
    "balanced": {"max_false": 0.45, "max_ci_upper": 0.55, "min_coverage": 0.08},
    "exploratory": {"max_false": 0.50, "max_ci_upper": 0.60, "min_coverage": 0.10},
}


@dataclass(frozen=True)
class PolicyConfig:
    policy_id: str
    policy_family: str
    visual_gate_type: str
    visual_threshold: float | None
    mega_threshold: float | None
    resnet_threshold: float | None
    descriptor_agreement_rule: str
    side_rule: str
    high_descriptor_low_visual_action: str
    severe_failure_action: str
    pattern_none_action: str
    severe_blur_action: str
    major_occlusion_action: str
    uncertainty_action: str
    needs_review_action: str
    review_requires_resnet: str


def clean_string(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.lower()


def quantile_thresholds(series: pd.Series, n: int, q_min: float = 0.0, q_max: float = 0.995) -> list[float]:
    qs = np.linspace(q_min, q_max, n)
    return sorted({round(float(series.quantile(q)), 6) for q in qs})


def ci(values: list[float]) -> tuple[float, float]:
    clean = np.array([v for v in values if not math.isnan(v)], dtype=float)
    if len(clean) == 0:
        return math.nan, math.nan
    return float(np.percentile(clean, 2.5)), float(np.percentile(clean, 97.5))


def load_data(scores_csv: Path, pair_table_csv: Path) -> pd.DataFrame:
    scores = pd.read_csv(scores_csv)
    pair_cols = [
        "pair_id",
        "image_id_a",
        "image_id_b",
        "source_phase_a",
        "source_phase_b",
        "pair_pattern_min",
        "pair_blur_worst",
        "pair_occlusion_worst",
        "pair_has_frontal_or_rear",
        "pair_has_partial_body",
        "pair_has_side_unknown",
        "pair_has_needs_review",
        "pair_has_uncertainty",
        "pair_modeling_eligible",
        "pair_exclusion_reason",
    ]
    pairs = pd.read_csv(pair_table_csv, usecols=pair_cols)
    df = scores.merge(pairs, on="pair_id", how="left", validate="one_to_one")

    for col in ["same_identity", "visual_band", "pair_side_compatible", "pair_primary_limiting_factor_combined"]:
        df[col] = clean_string(df[col])
    for col in [
        "pair_pattern_min",
        "pair_blur_worst",
        "pair_occlusion_worst",
        "pair_has_frontal_or_rear",
        "pair_has_partial_body",
        "pair_has_side_unknown",
        "pair_has_needs_review",
        "pair_has_uncertainty",
        "pair_modeling_eligible",
        "pair_exclusion_reason",
        "primary_limiting_factor_for_score",
    ]:
        df[col] = clean_string(df[col])

    numeric_cols = ["visual_pf_eri_weighted", "resnet50_similarity", "megadescriptor_similarity"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="raise")

    df["same_binary"] = (df["same_identity"] == "yes").astype(int)
    df["different_binary"] = (df["same_identity"] == "no").astype(int)
    df["megadescriptor_percentile"] = df["megadescriptor_similarity"].rank(method="average", pct=True)
    df["resnet50_percentile"] = df["resnet50_similarity"].rank(method="average", pct=True)
    df["descriptor_percentile_gap"] = (df["megadescriptor_percentile"] - df["resnet50_percentile"]).abs()
    df["descriptor_disagreement_moderate"] = df["descriptor_percentile_gap"] >= 0.30
    df["descriptor_disagreement_strict"] = df["descriptor_percentile_gap"] >= 0.40
    df["high_descriptor_low_visual"] = clean_string(df["any_high_descriptor_low_visual_flag"]) == "yes"
    df["side_incompatible"] = df["pair_side_compatible"] == "no"
    df["side_unknown"] = (df["pair_side_compatible"] == "unknown") | (df["pair_has_side_unknown"] == "yes")
    df["pattern_none"] = df["pair_pattern_min"] == "none"
    df["severe_blur"] = df["pair_blur_worst"] == "severe"
    df["major_occlusion"] = df["pair_occlusion_worst"] == "major"
    df["frontal_or_rear"] = df["pair_has_frontal_or_rear"] == "yes"
    df["partial_body"] = df["pair_has_partial_body"] == "yes"
    df["silhouette_only"] = df["primary_limiting_factor_for_score"] == "silhouette_only"
    df["uncertainty_flag"] = df["pair_has_uncertainty"] == "yes"
    df["needs_review_flag"] = df["pair_has_needs_review"] == "yes"
    df["modeling_eligible"] = df["pair_modeling_eligible"] == "yes"
    df["severe_visual_failure_core"] = df["pattern_none"] | df["severe_blur"] | df["major_occlusion"] | df["silhouette_only"]
    df["severe_visual_failure_with_view"] = df["severe_visual_failure_core"] | df["frontal_or_rear"]
    df["image_endpoint_primary_cluster"] = df[["image_id_a", "image_id_b"]].min(axis=1)
    return df


def visual_gate(df: pd.DataFrame, gate_type: str, threshold: float | None) -> pd.Series:
    if gate_type == "none":
        return pd.Series(True, index=df.index)
    if gate_type == "low_or_higher":
        return df["visual_band"].isin(["low", "medium", "high"])
    if gate_type == "medium_or_higher":
        return df["visual_band"].isin(["medium", "high"])
    if gate_type == "high_only":
        return df["visual_band"] == "high"
    if gate_type == "numeric_threshold":
        if threshold is None:
            raise ValueError("numeric_threshold requires a visual threshold")
        return df["visual_pf_eri_weighted"] >= threshold
    raise ValueError(f"unknown visual gate type: {gate_type}")


def descriptor_support(df: pd.DataFrame, config: PolicyConfig) -> pd.Series:
    support = pd.Series(True, index=df.index)
    if config.mega_threshold is not None:
        support &= df["megadescriptor_similarity"] >= config.mega_threshold
    if config.review_requires_resnet == "yes" and config.resnet_threshold is not None:
        support &= df["resnet50_similarity"] >= config.resnet_threshold
    if config.descriptor_agreement_rule == "moderate_gap_defer":
        support &= ~df["descriptor_disagreement_moderate"]
    elif config.descriptor_agreement_rule == "strict_gap_defer":
        support &= ~df["descriptor_disagreement_strict"]
    elif config.descriptor_agreement_rule == "resnet_floor" and config.resnet_threshold is not None:
        support &= df["resnet50_similarity"] >= config.resnet_threshold
    elif config.descriptor_agreement_rule != "none":
        raise ValueError(f"unknown descriptor agreement rule: {config.descriptor_agreement_rule}")
    return support


def action_mask(flags: pd.Series, action: str, assignment: str) -> pd.Series:
    if action == assignment:
        return flags
    if action in {"allow", "defer", "exclude"}:
        return pd.Series(False, index=flags.index)
    raise ValueError(f"unknown action: {action}")


def policy_assignment(df: pd.DataFrame, config: PolicyConfig) -> pd.DataFrame:
    gate = visual_gate(df, config.visual_gate_type, config.visual_threshold)
    support = descriptor_support(df, config)
    review_base = gate & support

    exclude = pd.Series(False, index=df.index)
    defer = pd.Series(False, index=df.index)

    core_failure = df["severe_visual_failure_core"]
    view_failure = df["frontal_or_rear"]
    severe_failure = core_failure | view_failure if config.severe_failure_action != "allow" else core_failure

    exclude |= action_mask(severe_failure, config.severe_failure_action, "exclude")
    defer |= action_mask(severe_failure, config.severe_failure_action, "defer")
    exclude |= action_mask(df["pattern_none"], config.pattern_none_action, "exclude")
    defer |= action_mask(df["pattern_none"], config.pattern_none_action, "defer")
    exclude |= action_mask(df["severe_blur"], config.severe_blur_action, "exclude")
    defer |= action_mask(df["severe_blur"], config.severe_blur_action, "defer")
    exclude |= action_mask(df["major_occlusion"], config.major_occlusion_action, "exclude")
    defer |= action_mask(df["major_occlusion"], config.major_occlusion_action, "defer")
    exclude |= action_mask(df["high_descriptor_low_visual"], config.high_descriptor_low_visual_action, "exclude")
    defer |= action_mask(df["high_descriptor_low_visual"], config.high_descriptor_low_visual_action, "defer")
    exclude |= action_mask(df["uncertainty_flag"], config.uncertainty_action, "exclude")
    defer |= action_mask(df["uncertainty_flag"], config.uncertainty_action, "defer")
    exclude |= action_mask(df["needs_review_flag"], config.needs_review_action, "exclude")
    defer |= action_mask(df["needs_review_flag"], config.needs_review_action, "defer")

    if config.side_rule == "allow_all":
        side_defer = pd.Series(False, index=df.index)
    elif config.side_rule == "defer_incompatible":
        side_defer = df["side_incompatible"]
    elif config.side_rule == "defer_unknown":
        side_defer = df["side_unknown"]
    elif config.side_rule == "defer_incompatible_and_unknown":
        side_defer = df["side_incompatible"] | df["side_unknown"]
    else:
        raise ValueError(f"unknown side rule: {config.side_rule}")
    defer |= side_defer

    if config.descriptor_agreement_rule == "moderate_gap_defer":
        defer |= df["descriptor_disagreement_moderate"] & df["visual_band"].isin(["low", "unusable"])
    elif config.descriptor_agreement_rule == "strict_gap_defer":
        defer |= df["descriptor_disagreement_strict"] & df["visual_band"].isin(["low", "unusable"])
    elif config.descriptor_agreement_rule == "resnet_floor" and config.resnet_threshold is not None:
        defer |= (df["resnet50_similarity"] < config.resnet_threshold) & review_base

    assignment = pd.Series("defer_candidate", index=df.index)
    assignment[exclude] = "exclude_candidate"
    review = review_base & ~defer & ~exclude
    assignment[review] = "review_candidate"

    reason = pd.Series("below_descriptor_or_visual_gate", index=df.index)
    reason[~gate] = "visual_gate_not_met"
    reason[gate & ~support] = "descriptor_support_not_met"
    reason[review] = "passes_visual_gate_and_descriptor_support"
    reason[defer & review_base] = "deferred_by_caution_rule"
    reason[exclude] = "excluded_by_severe_visual_failure_rule"
    return pd.DataFrame({"assignment": assignment, "assignment_reason": reason})


def policy_metrics(df: pd.DataFrame, assignment: pd.Series) -> dict[str, float | int]:
    total = len(df)
    review = assignment == "review_candidate"
    defer = assignment == "defer_candidate"
    exclude = assignment == "exclude_candidate"
    reviewed = df[review]
    review_count = int(review.sum())
    defer_count = int(defer.sum())
    exclude_count = int(exclude.sum())
    same_review = int((reviewed["same_identity"] == "yes").sum())
    different_review = int((reviewed["same_identity"] == "no").sum())
    same_total = int((df["same_identity"] == "yes").sum())
    different_total = int((df["same_identity"] == "no").sum())
    removed = max(total - review_count, 1)
    false_support = different_review / review_count if review_count else math.nan
    original_false_rate = different_total / total if total else math.nan
    risk_reduction = original_false_rate - false_support if not math.isnan(false_support) else math.nan
    hdlv_review = int((review & df["high_descriptor_low_visual"]).sum())
    hdlv_false = int((review & df["high_descriptor_low_visual"] & (df["same_identity"] == "no")).sum())
    failure_review = int((review & df["severe_visual_failure_core"]).sum())
    return {
        "candidate_pair_count": total,
        "review_candidate_count": review_count,
        "defer_candidate_count": defer_count,
        "exclude_candidate_count": exclude_count,
        "review_coverage": review_count / total if total else math.nan,
        "defer_rate": defer_count / total if total else math.nan,
        "exclude_rate": exclude_count / total if total else math.nan,
        "review_same_count": same_review,
        "review_different_count": different_review,
        "review_same_proportion": same_review / review_count if review_count else math.nan,
        "review_false_support_rate": false_support,
        "same_accept_rate": same_review / same_total if same_total else math.nan,
        "different_accept_rate": different_review / different_total if different_total else math.nan,
        "risk_load_relative_to_original_pool": different_review / different_total if different_total else math.nan,
        "risk_reduction_per_evidence_removed": risk_reduction / removed if removed else math.nan,
        "high_descriptor_low_visual_review_count": hdlv_review,
        "high_descriptor_low_visual_false_rate_among_reviewed": hdlv_false / review_count if review_count else math.nan,
        "severe_visual_failure_review_count": failure_review,
        "pattern_none_review_count": int((review & df["pattern_none"]).sum()),
        "severe_blur_review_count": int((review & df["severe_blur"]).sum()),
        "major_occlusion_review_count": int((review & df["major_occlusion"]).sum()),
        "side_incompatible_review_count": int((review & df["side_incompatible"]).sum()),
        "side_unknown_review_count": int((review & df["side_unknown"]).sum()),
        "descriptor_disagreement_review_count": int((review & df["descriptor_disagreement_moderate"]).sum()),
    }


def score_policy(metrics: dict[str, float | int], family: str) -> float:
    false_rate = float(metrics["review_false_support_rate"]) if not math.isnan(float(metrics["review_false_support_rate"])) else 1.0
    coverage = float(metrics["review_coverage"])
    hdlv = float(metrics["high_descriptor_low_visual_review_count"]) / max(float(metrics["review_candidate_count"]), 1.0)
    severe = float(metrics["severe_visual_failure_review_count"]) / max(float(metrics["review_candidate_count"]), 1.0)
    family_bonus = 0.0
    if "visual_gate_megadescriptor_failure_defer" in family:
        family_bonus = 0.04
    elif "dual_descriptor_agreement" in family:
        family_bonus = 0.03
    elif "conservative" in family:
        family_bonus = 0.02
    elif "descriptor_only" in family:
        family_bonus = -0.08
    return (1.0 - false_rate) + 0.45 * coverage - 0.15 * hdlv - 0.20 * severe + family_bonus


def make_policy_configs(df: pd.DataFrame) -> list[PolicyConfig]:
    mega_all = quantile_thresholds(df["megadescriptor_similarity"], 70, 0.50, 0.995)
    mega_high = quantile_thresholds(df["megadescriptor_similarity"], 45, 0.70, 0.995)
    resnet_support = quantile_thresholds(df["resnet50_similarity"], 10, 0.55, 0.95)
    visual_thresholds = quantile_thresholds(df["visual_pf_eri_weighted"], 12, 0.15, 0.95)
    configs: list[PolicyConfig] = []

    def add(policy_family: str, visual_gate_type: str, visual_threshold: float | None, mega: float | None,
            resnet: float | None, agreement: str, side_rule: str, hdlv: str, severe: str,
            pattern: str, blur: str, occlusion: str, uncertainty: str = "defer",
            needs_review: str = "defer", requires_resnet: str = "no") -> None:
        policy_id = f"P_{len(configs) + 1:05d}"
        configs.append(
            PolicyConfig(
                policy_id,
                policy_family,
                visual_gate_type,
                visual_threshold,
                mega,
                resnet,
                agreement,
                side_rule,
                hdlv,
                severe,
                pattern,
                blur,
                occlusion,
                uncertainty,
                needs_review,
                requires_resnet,
            )
        )

    for mega in mega_all:
        add("A_descriptor_only_baseline", "none", None, mega, None, "none", "allow_all", "allow", "allow", "allow", "allow", "allow")

    visual_gates = ["low_or_higher", "medium_or_higher", "high_only"]
    for mega in mega_all:
        for gate in visual_gates:
            for side in ["allow_all", "defer_incompatible", "defer_incompatible_and_unknown"]:
                add("B_visual_gate_megadescriptor", gate, None, mega, None, "none", side, "allow", "allow", "allow", "allow", "allow")
        for vt in visual_thresholds:
            add("B_visual_gate_megadescriptor", "numeric_threshold", vt, mega, None, "none", "allow_all", "allow", "allow", "allow", "allow", "allow")

    for mega in mega_all:
        for gate in ["low_or_higher", "medium_or_higher", "high_only"]:
            for side in ["defer_incompatible", "defer_incompatible_and_unknown"]:
                for hdlv in ["defer", "exclude"]:
                    for severe in ["defer", "exclude"]:
                        for pattern in ["defer", "exclude"]:
                            add(
                                "C_visual_gate_megadescriptor_failure_defer",
                                gate,
                                None,
                                mega,
                                None,
                                "none",
                                side,
                                hdlv,
                                severe,
                                pattern,
                                severe,
                                severe,
                            )
        for vt in visual_thresholds[3:]:
            for side in ["defer_incompatible", "defer_incompatible_and_unknown"]:
                for hdlv in ["defer", "exclude"]:
                    for severe in ["defer", "exclude"]:
                        add(
                            "C_visual_gate_megadescriptor_failure_defer",
                            "numeric_threshold",
                            vt,
                            mega,
                            None,
                            "none",
                            side,
                            hdlv,
                            severe,
                            severe,
                            severe,
                            severe,
                        )

    for mega in mega_high:
        for resnet in resnet_support:
            for gate in ["low_or_higher", "medium_or_higher", "high_only"]:
                for side in ["defer_incompatible", "defer_incompatible_and_unknown"]:
                    for agreement in ["moderate_gap_defer", "strict_gap_defer", "resnet_floor"]:
                        add(
                            "D_dual_descriptor_agreement_caution",
                            gate,
                            None,
                            mega,
                            resnet,
                            agreement,
                            side,
                            "defer",
                            "defer",
                            "defer",
                            "defer",
                            "defer",
                            requires_resnet="yes" if agreement == "resnet_floor" else "no",
                        )

    for mega in mega_high:
        for resnet in resnet_support[3:]:
            for side in ["defer_incompatible", "defer_incompatible_and_unknown"]:
                add(
                    "E_conservative_high_confidence_policy",
                    "medium_or_higher",
                    None,
                    mega,
                    resnet,
                    "resnet_floor",
                    side,
                    "exclude",
                    "exclude",
                    "exclude",
                    "exclude",
                    "exclude",
                    requires_resnet="yes",
                )
                add(
                    "E_conservative_high_confidence_policy",
                    "high_only",
                    None,
                    mega,
                    resnet,
                    "strict_gap_defer",
                    side,
                    "exclude",
                    "exclude",
                    "exclude",
                    "exclude",
                    "exclude",
                    requires_resnet="no",
                )

    for mega in mega_all:
        for gate in ["low_or_higher", "medium_or_higher"]:
            for side in ["allow_all", "defer_incompatible", "defer_incompatible_and_unknown"]:
                for hdlv in ["allow", "defer"]:
                    for agreement in ["none", "moderate_gap_defer"]:
                        add(
                            "F_balanced_review_policy",
                            gate,
                            None,
                            mega,
                            None,
                            agreement,
                            side,
                            hdlv,
                            "defer",
                            "defer",
                            "defer",
                            "defer",
                        )

    return configs


def build_candidate_grid(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, PolicyConfig]]:
    rows: list[dict[str, object]] = []
    configs = make_policy_configs(df)
    config_map = {config.policy_id: config for config in configs}
    for config in configs:
        assignment = policy_assignment(df, config)["assignment"]
        metrics = policy_metrics(df, assignment)
        row = {**asdict(config), **metrics}
        row["ranking_score"] = score_policy(metrics, config.policy_family)
        for regime, spec in REGIMES.items():
            passes_point = (
                row["review_candidate_count"] > 0
                and row["review_coverage"] >= spec["min_coverage"]
                and row["review_false_support_rate"] <= spec["max_false"]
            )
            row[f"{regime}_point_pass"] = "yes" if passes_point else "no"
        rows.append(row)
    grid = pd.DataFrame(rows)
    return grid, config_map


def select_bootstrap_candidates(grid: pd.DataFrame) -> pd.DataFrame:
    eligible = grid[grid["review_candidate_count"] >= 30].copy()
    if eligible.empty:
        return grid.sort_values("ranking_score", ascending=False).head(20).copy()
    selected_ids: list[str] = []
    for regime, spec in REGIMES.items():
        subset = eligible[
            (eligible["review_coverage"] >= spec["min_coverage"])
            & (eligible["review_false_support_rate"] <= spec["max_ci_upper"])
        ].copy()
        if subset.empty:
            subset = eligible[eligible["review_coverage"] >= spec["min_coverage"]].copy()
        subset = subset.sort_values(["ranking_score", "review_false_support_rate", "review_coverage"], ascending=[False, True, False])
        selected_ids.extend(subset["policy_id"].head(6).tolist())
    for family, subset in eligible.groupby("policy_family"):
        selected_ids.extend(
            subset.sort_values(["ranking_score", "review_false_support_rate"], ascending=[False, True])["policy_id"].head(2).tolist()
        )
    selected = list(dict.fromkeys(selected_ids))
    return grid[grid["policy_id"].isin(selected)].copy().head(36)


def clustered_sample(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    clusters = df[CLUSTER_UNIT].dropna().unique()
    sampled = rng.choice(clusters, size=len(clusters), replace=True)
    return pd.concat([df[df[CLUSTER_UNIT] == cluster] for cluster in sampled], ignore_index=True)


def bootstrap_top_candidates(
    df: pd.DataFrame, top: pd.DataFrame, config_map: dict[str, PolicyConfig], bootstrap_n: int
) -> pd.DataFrame:
    metrics = [
        "review_coverage",
        "review_false_support_rate",
        "review_same_proportion",
        "same_accept_rate",
        "high_descriptor_low_visual_false_rate_among_reviewed",
        "severe_visual_failure_review_count",
        "pattern_none_review_count",
        "severe_blur_review_count",
        "major_occlusion_review_count",
        "side_incompatible_review_count",
        "side_unknown_review_count",
        "descriptor_disagreement_review_count",
    ]
    estimates = {}
    for _, row in top.iterrows():
        config = config_map[str(row["policy_id"])]
        assignment = policy_assignment(df, config)["assignment"]
        estimates[str(row["policy_id"])] = policy_metrics(df, assignment)

    boot_values = {(policy_id, metric): [] for policy_id in estimates for metric in metrics}
    rng = np.random.default_rng(RANDOM_SEED)
    for _ in range(bootstrap_n):
        sample = clustered_sample(df, rng)
        for policy_id in estimates:
            config = config_map[policy_id]
            assignment = policy_assignment(sample, config)["assignment"]
            values = policy_metrics(sample, assignment)
            for metric in metrics:
                boot_values[(policy_id, metric)].append(float(values[metric]))

    ci_rows = []
    for policy_id in estimates:
        for metric in metrics:
            estimate = float(estimates[policy_id][metric])
            lower, upper = ci(boot_values[(policy_id, metric)])
            ci_rows.append(
                {
                    "policy_id": policy_id,
                    "metric": metric,
                    "estimate": estimate,
                    "ci_lower": lower,
                    "ci_upper": upper,
                    "bootstrap_n": bootstrap_n,
                    "cluster_unit": CLUSTER_UNIT,
                }
            )
    ci_df = pd.DataFrame(ci_rows)
    enriched = top.copy()
    for metric in metrics:
        metric_ci = ci_df[ci_df["metric"] == metric][["policy_id", "ci_lower", "ci_upper"]].rename(
            columns={"ci_lower": f"{metric}_ci_lower", "ci_upper": f"{metric}_ci_upper"}
        )
        enriched = enriched.merge(metric_ci, on="policy_id", how="left")
    enriched["bootstrap_n"] = bootstrap_n
    enriched["cluster_unit"] = CLUSTER_UNIT
    for regime, spec in REGIMES.items():
        enriched[f"{regime}_ci_pass"] = np.where(
            (enriched["review_coverage"] >= spec["min_coverage"])
            & (enriched["review_false_support_rate"] <= spec["max_false"])
            & (enriched["review_false_support_rate_ci_upper"] <= spec["max_ci_upper"]),
            "yes",
            "no",
        )
    return enriched


def choose_recommended_policy(top: pd.DataFrame) -> pd.Series:
    for regime in ["moderate", "balanced", "strict", "exploratory"]:
        subset = top[(top[f"{regime}_ci_pass"] == "yes") & ~top["policy_family"].str.startswith("A_")].copy()
        if not subset.empty:
            return subset.sort_values(["ranking_score", "review_coverage"], ascending=[False, False]).iloc[0]
    subset = top[~top["policy_family"].str.startswith("A_")].copy()
    if subset.empty:
        subset = top.copy()
    return subset.sort_values(["ranking_score", "review_false_support_rate"], ascending=[False, True]).iloc[0]


def regime_summary(top: pd.DataFrame, recommended_policy_id: str) -> pd.DataFrame:
    rows = []
    for regime, spec in REGIMES.items():
        passed = top[top[f"{regime}_ci_pass"] == "yes"].copy()
        nonbaseline = passed[~passed["policy_family"].str.startswith("A_")]
        best = nonbaseline if not nonbaseline.empty else passed
        best = best.sort_values(["ranking_score", "review_coverage"], ascending=[False, False]) if not best.empty else best
        if best.empty:
            rows.append(
                {
                    "regime": regime,
                    "point_false_support_limit": spec["max_false"],
                    "ci_upper_false_support_limit": spec["max_ci_upper"],
                    "coverage_floor": spec["min_coverage"],
                    "passing_policy_count": 0,
                    "best_policy_id": "",
                    "best_policy_family": "",
                    "best_review_coverage": math.nan,
                    "best_review_false_support_rate": math.nan,
                    "best_review_false_support_ci_upper": math.nan,
                    "recommended_policy_flag": "no",
                    "interpretation": "no bootstrapped top candidate satisfied this regime",
                }
            )
            continue
        row = best.iloc[0]
        rows.append(
            {
                "regime": regime,
                "point_false_support_limit": spec["max_false"],
                "ci_upper_false_support_limit": spec["max_ci_upper"],
                "coverage_floor": spec["min_coverage"],
                "passing_policy_count": len(passed),
                "best_policy_id": row["policy_id"],
                "best_policy_family": row["policy_family"],
                "best_review_coverage": row["review_coverage"],
                "best_review_false_support_rate": row["review_false_support_rate"],
                "best_review_false_support_ci_upper": row["review_false_support_rate_ci_upper"],
                "recommended_policy_flag": "yes" if row["policy_id"] == recommended_policy_id else "no",
                "interpretation": "comparison regime satisfied under clustered uncertainty; not a biological deployment tolerance",
            }
        )
    return pd.DataFrame(rows)


def assignment_output(df: pd.DataFrame, config: PolicyConfig) -> pd.DataFrame:
    assignment = policy_assignment(df, config)
    out = pd.DataFrame(
        {
            "pair_id": df["pair_id"],
            "assignment": assignment["assignment"],
            "assignment_reason": assignment["assignment_reason"],
            "visual_pf_eri_weighted": df["visual_pf_eri_weighted"],
            "visual_band": df["visual_band"],
            "megadescriptor_similarity": df["megadescriptor_similarity"],
            "resnet50_similarity": df["resnet50_similarity"],
            "pair_side_compatible": df["pair_side_compatible"],
            "same_identity_validation_label": df["same_identity"],
            "high_descriptor_low_visual_flag": np.where(df["high_descriptor_low_visual"], "yes", "no"),
            "pattern_none_flag": np.where(df["pattern_none"], "yes", "no"),
            "severe_blur_flag": np.where(df["severe_blur"], "yes", "no"),
            "major_occlusion_flag": np.where(df["major_occlusion"], "yes", "no"),
            "frontal_or_rear_flag": np.where(df["frontal_or_rear"], "yes", "no"),
            "side_unknown_flag": np.where(df["side_unknown"], "yes", "no"),
            "descriptor_disagreement_flag": np.where(df["descriptor_disagreement_moderate"], "yes", "no"),
            "source_phase_a": df["source_phase_a"],
            "source_phase_b": df["source_phase_b"],
        }
    )
    return out.sort_values(["assignment", "megadescriptor_similarity"], ascending=[True, False])


def failure_mode_summary(df: pd.DataFrame, top: pd.DataFrame, config_map: dict[str, PolicyConfig]) -> pd.DataFrame:
    modes = {
        "high_descriptor_low_visual": "high_descriptor_low_visual",
        "pattern_none": "pattern_none",
        "severe_blur": "severe_blur",
        "major_occlusion": "major_occlusion",
        "frontal_or_rear": "frontal_or_rear",
        "side_incompatible": "side_incompatible",
        "side_unknown": "side_unknown",
        "descriptor_disagreement_moderate": "descriptor_disagreement_moderate",
    }
    rows = []
    for _, top_row in top.iterrows():
        config = config_map[str(top_row["policy_id"])]
        assignment = policy_assignment(df, config)["assignment"]
        review = assignment == "review_candidate"
        for mode_name, col in modes.items():
            count = int((review & df[col]).sum())
            rows.append(
                {
                    "policy_id": top_row["policy_id"],
                    "policy_family": top_row["policy_family"],
                    "failure_mode": mode_name,
                    "review_count_with_mode": count,
                    "review_rate_with_mode": count / max(int(review.sum()), 1),
                    "all_pair_count_with_mode": int(df[col].sum()),
                    "policy_action_context": mode_action_context(config, mode_name),
                }
            )
    return pd.DataFrame(rows)


def mode_action_context(config: PolicyConfig, mode_name: str) -> str:
    if mode_name == "high_descriptor_low_visual":
        return config.high_descriptor_low_visual_action
    if mode_name == "pattern_none":
        return config.pattern_none_action
    if mode_name == "severe_blur":
        return config.severe_blur_action
    if mode_name == "major_occlusion":
        return config.major_occlusion_action
    if mode_name in {"side_incompatible", "side_unknown"}:
        return config.side_rule
    if mode_name == "descriptor_disagreement_moderate":
        return config.descriptor_agreement_rule
    return config.severe_failure_action


def confidence_decision(top: pd.DataFrame, recommended: pd.Series, grid_count: int) -> pd.DataFrame:
    strict_count = int((top["strict_ci_pass"] == "yes").sum())
    moderate_count = int((top["moderate_ci_pass"] == "yes").sum())
    balanced_count = int((top["balanced_ci_pass"] == "yes").sum())
    exploratory_count = int((top["exploratory_ci_pass"] == "yes").sum())
    if moderate_count > 0 and not str(recommended["policy_family"]).startswith("A_"):
        status = "conditional_go_for_policy_interpretation"
        next_step = "interpret recommended staged PF-ERI policy; do not claim field deployment"
    elif exploratory_count > 0:
        status = "diagnostic_only_until_more_evidence"
        next_step = "report sparse-confidence caveat and consider evidence expansion before stronger policy claims"
    else:
        status = "no_go_for_policy_claim"
        next_step = "do not optimize further until evidence or annotation coverage improves"
    return pd.DataFrame(
        [
            {
                "decision_area": "ci_aware_pf_eri_policy_optimization",
                "status": status,
                "candidate_policy_count": grid_count,
                "bootstrapped_top_policy_count": len(top),
                "bootstrap_n": int(recommended["bootstrap_n"]),
                "cluster_unit": recommended["cluster_unit"],
                "recommended_policy_id": recommended["policy_id"],
                "recommended_policy_family": recommended["policy_family"],
                "recommended_review_coverage": recommended["review_coverage"],
                "recommended_review_coverage_ci_lower": recommended["review_coverage_ci_lower"],
                "recommended_review_coverage_ci_upper": recommended["review_coverage_ci_upper"],
                "recommended_false_support_rate": recommended["review_false_support_rate"],
                "recommended_false_support_ci_lower": recommended["review_false_support_rate_ci_lower"],
                "recommended_false_support_ci_upper": recommended["review_false_support_rate_ci_upper"],
                "strict_passing_top_policy_count": strict_count,
                "moderate_passing_top_policy_count": moderate_count,
                "balanced_passing_top_policy_count": balanced_count,
                "exploratory_passing_top_policy_count": exploratory_count,
                "same_different_label_use": "validation_metrics_only_not_policy_inputs",
                "descriptor_role": "fixed_descriptor_support_not_a_new_reid_model",
                "field_claim_boundary": "simulated_czechlynx_validation_only",
                "recommended_next_step": next_step.replace("field deployment", "field-use readiness"),
            }
        ]
    )


def save_figures(df: pd.DataFrame, grid: pd.DataFrame, top: pd.DataFrame, regime: pd.DataFrame, failure: pd.DataFrame) -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid")

    def save(name: str) -> None:
        plt.tight_layout()
        plt.savefig(FIGURE_DIR / name, dpi=180)
        plt.close()

    plt.figure(figsize=(9, 6))
    for family, group in grid.groupby("policy_family"):
        plt.scatter(group["review_coverage"], group["review_false_support_rate"], s=10, alpha=0.45, label=family.replace("_", " "))
    plt.xlabel("review coverage")
    plt.ylabel("false-support rate among review candidates")
    plt.title("PF-ERI policy risk-coverage grid")
    plt.legend(fontsize=7)
    save("phase7a_policy_risk_coverage_frontier.png")

    plt.figure(figsize=(9, 6))
    shown = top.sort_values("ranking_score", ascending=False).head(16)
    plt.barh(shown["policy_id"], shown["review_false_support_rate"], xerr=[
        shown["review_false_support_rate"] - shown["review_false_support_rate_ci_lower"],
        shown["review_false_support_rate_ci_upper"] - shown["review_false_support_rate"],
    ])
    plt.gca().invert_yaxis()
    plt.xlabel("false-support rate with clustered CI")
    plt.title("Top policy false-support uncertainty")
    save("phase7a_top_policy_false_support_ci.png")

    plt.figure(figsize=(9, 6))
    shown = top.sort_values("ranking_score", ascending=False).head(16)
    plt.barh(shown["policy_id"], shown["review_coverage"], xerr=[
        shown["review_coverage"] - shown["review_coverage_ci_lower"],
        shown["review_coverage_ci_upper"] - shown["review_coverage"],
    ], color="#4477AA")
    plt.gca().invert_yaxis()
    plt.xlabel("review coverage with clustered CI")
    plt.title("Top policy coverage uncertainty")
    save("phase7a_top_policy_coverage_ci.png")

    plt.figure(figsize=(9, 6))
    family_summary = grid.groupby("policy_family")[["review_coverage", "review_false_support_rate"]].median().reset_index()
    x = np.arange(len(family_summary))
    plt.bar(x - 0.18, family_summary["review_coverage"], width=0.36, label="median coverage")
    plt.bar(x + 0.18, family_summary["review_false_support_rate"], width=0.36, label="median false-support")
    plt.xticks(x, family_summary["policy_family"].str.replace("_", " "), rotation=35, ha="right")
    plt.title("Median behavior by policy family")
    plt.legend()
    save("phase7a_policy_family_median_comparison.png")

    plt.figure(figsize=(8, 5))
    pass_counts = [int((top[f"{r}_ci_pass"] == "yes").sum()) for r in REGIMES]
    plt.bar(list(REGIMES), pass_counts, color="#228833")
    plt.ylabel("bootstrapped top policies passing")
    plt.title("CI-aware pass counts by comparison regime")
    save("phase7a_regime_pass_counts.png")

    plt.figure(figsize=(9, 6))
    failure_pivot = failure.pivot_table(index="failure_mode", values="review_rate_with_mode", aggfunc="median").sort_values("review_rate_with_mode")
    plt.barh(failure_pivot.index, failure_pivot["review_rate_with_mode"], color="#CC6677")
    plt.xlabel("median reviewed-pair exposure rate")
    plt.title("Failure-mode exposure among reviewed candidates")
    save("phase7a_failure_mode_review_exposure.png")

    plt.figure(figsize=(8, 5))
    plt.hist(grid["ranking_score"], bins=45, color="#66CCEE", edgecolor="white")
    plt.xlabel("policy ranking score")
    plt.ylabel("candidate policy count")
    plt.title("Policy ranking score distribution")
    save("phase7a_policy_ranking_score_distribution.png")

    plt.figure(figsize=(8, 5))
    plt.scatter(df["megadescriptor_similarity"], df["resnet50_similarity"], c=df["visual_pf_eri_weighted"], s=12, alpha=0.65, cmap="viridis")
    plt.xlabel("MegaDescriptor similarity")
    plt.ylabel("ResNet50 similarity")
    plt.colorbar(label="visual PF-ERI")
    plt.title("Descriptor support context colored by visual gate")
    save("phase7a_descriptor_support_context.png")

    plt.figure(figsize=(8, 5))
    plt.scatter(grid["review_coverage"], grid["risk_load_relative_to_original_pool"], s=10, alpha=0.45, color="#AA4499")
    plt.xlabel("review coverage")
    plt.ylabel("risk load relative to original pool")
    plt.title("Risk load retained by candidate policies")
    save("phase7a_risk_load_relative_to_pool.png")


def run(args: argparse.Namespace) -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    df = load_data(args.scores_csv, args.pair_table_csv)
    grid, config_map = build_candidate_grid(df)
    bootstrap_pool = select_bootstrap_candidates(grid)
    top = bootstrap_top_candidates(df, bootstrap_pool, config_map, args.bootstrap_n)
    top = top.sort_values(["ranking_score", "review_false_support_rate", "review_coverage"], ascending=[False, True, False])
    recommended = choose_recommended_policy(top)
    recommended_config = config_map[str(recommended["policy_id"])]
    assignments = assignment_output(df, recommended_config)
    regime = regime_summary(top, str(recommended["policy_id"]))
    failure = failure_mode_summary(df, top, config_map)
    decision = confidence_decision(top, recommended, len(grid))

    grid.to_csv(GRID_CSV, index=False)
    top.to_csv(TOP_CANDIDATES_CSV, index=False)
    assignments.to_csv(ASSIGNMENT_TOP_CSV, index=False)
    regime.to_csv(REGIME_SUMMARY_CSV, index=False)
    failure.to_csv(FAILURE_MODE_SUMMARY_CSV, index=False)
    decision.to_csv(CONFIDENCE_DECISION_CSV, index=False)
    save_figures(df, grid, top, regime, failure)

    print("PASS: Phase 7A CI-aware PF-ERI policy optimization complete")
    print(f"candidate_policy_count: {len(grid)}")
    print(f"bootstrapped_top_policy_count: {len(top)}")
    print(f"bootstrap_n: {args.bootstrap_n}")
    print(f"cluster_unit: {CLUSTER_UNIT}")
    print(f"recommended_policy_id: {recommended['policy_id']}")
    print(f"recommended_policy_family: {recommended['policy_family']}")
    print(f"recommended_review_coverage: {recommended['review_coverage']:.4f}")
    print(f"recommended_false_support_rate: {recommended['review_false_support_rate']:.4f}")
    print(f"recommended_false_support_ci: {recommended['review_false_support_rate_ci_lower']:.4f}-{recommended['review_false_support_rate_ci_upper']:.4f}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scores-csv", type=Path, default=SCORES_CSV)
    parser.add_argument("--pair-table-csv", type=Path, default=PAIR_TABLE_CSV)
    parser.add_argument("--bootstrap-n", type=int, default=BOOTSTRAP_N)
    return parser.parse_args()


def main() -> int:
    return run(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
