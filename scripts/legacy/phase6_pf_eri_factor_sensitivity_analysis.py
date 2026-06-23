#!/usr/bin/env python3
"""Phase 6 PF-ERI visual-factor sensitivity analysis.

This script evaluates whether PF-ERI conclusions survive prespecified changes
to visual-factor weights, thresholds, hard gates, interaction penalties, and
penalty structures. It does not learn weights, train a model, or expose row-level
identity information in outputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import re

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PAIR_SCORES = ROOT / "outputs/czechlynx/phase5/czechlynx_phase5_pair_eri_scores_internal.csv"
PHASE4C_PAIRS = (
    ROOT / "outputs/czechlynx/phase4/czechlynx_phase4c_pair_level_mechanism_similarity_table.csv"
)
ID_MAPPING = ROOT / "data/interim/czechlynx/czechlynx_expanded_125x4_internal_with_ids.csv"
OUT_TABLE_DIR = ROOT / "outputs/czechlynx/phase6/tables"
OUT_FIG_DIR = ROOT / "outputs/czechlynx/phase6/figures"
QC_DIR = ROOT / "outputs/czechlynx/qc"

VARIANTS_OUT = OUT_TABLE_DIR / "phase6_pf_eri_sensitivity_variants.csv"
METRICS_OUT = OUT_TABLE_DIR / "phase6_pf_eri_sensitivity_metrics.csv"
POLICY_OUT = OUT_TABLE_DIR / "phase6_pf_eri_sensitivity_policy_robustness.csv"
CONCLUSIONS_OUT = OUT_TABLE_DIR / "phase6_pf_eri_sensitivity_conclusion_stability.csv"
FIG_BAND_OUT = OUT_FIG_DIR / "phase6_pf_eri_sensitivity_band_stability.png"
FIG_RISK_OUT = OUT_FIG_DIR / "phase6_pf_eri_sensitivity_risk_coverage.png"
REPORT_OUT = QC_DIR / "phase6_pf_eri_factor_sensitivity_audit_report.txt"

SEED = 20260613

POSITIVE_EVIDENCE = {"high": 100.0, "medium": 65.0, "low": 30.0, "none": 0.0}
IMPAIRMENT = {
    "none": 100.0,
    "mild": 70.0,
    "moderate": 35.0,
    "severe": 0.0,
    "unknown": 50.0,
    "not_applicable": 100.0,
}
BODY_FRACTION = {"76_100": 100.0, "51_75": 70.0, "26_50": 35.0, "0_25": 0.0, "unknown": 50.0}
SIDE_COMPARABLE = {"yes": 100.0, "limited": 55.0, "unknown": 25.0, "no": 0.0}
BINARY_IMPAIRMENT = {"no": 100.0, "unknown": 50.0, "yes": 0.0}

BASE_WEIGHTS = {
    "pattern": 0.22,
    "side_quality": 0.22,
    "side_comparable": 0.16,
    "body": 0.12,
    "blur": 0.10,
    "occlusion": 0.08,
    "ir": 0.05,
    "frontal": 0.03,
    "silhouette": 0.02,
}

THRESHOLD_SETS = {
    "original_75_50_25": {"high": 75.0, "medium": 50.0, "low": 25.0},
    "stricter_80_55_35": {"high": 80.0, "medium": 55.0, "low": 35.0},
    "very_strict_85_60_40": {"high": 85.0, "medium": 60.0, "low": 40.0},
    "looser_70_50_25": {"high": 70.0, "medium": 50.0, "low": 25.0},
    "low_boundary_75_55_35": {"high": 75.0, "medium": 55.0, "low": 35.0},
}

SIMILARITY_COLUMNS = {
    "megadescriptor": "megadescriptor_similarity",
    "resnet50": "resnet50_similarity",
}
RISK_TOLERANCES = [0.05, 0.10, 0.15]
SENSITIVE_COLUMN_PARTS = (
    "unique_name",
    "working_individual_id",
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
)
SENSITIVE_VALUE_PATTERNS = ("/Users/", "data/interim", "working_individual_id", "review_image_path")
SENSITIVE_VALUE_REGEXES = (r"\blynx_\d+",)


@dataclass(frozen=True)
class ScoreVariant:
    variant_id: str
    family: str
    weights: dict[str, float]
    uncertainty_penalty: float = 10.0
    needs_review_penalty: float = 10.0
    penalty_model: str = "additive"
    hard_gate_mode: str = "none"
    interaction_mode: str = "none"
    description: str = ""


def normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    total = sum(max(0.0, float(v)) for v in weights.values())
    if total <= 0:
        raise ValueError("Weight set has non-positive total.")
    return {k: max(0.0, float(v)) / total for k, v in weights.items()}


def shifted_weights(name: str, factor_names: list[str], delta: float) -> ScoreVariant:
    weights = BASE_WEIGHTS.copy()
    for factor in factor_names:
        weights[factor] *= 1.0 + delta
    suffix = "up" if delta > 0 else "down"
    return ScoreVariant(
        variant_id=f"{name}_{abs(int(delta * 100))}pct_{suffix}",
        family="weight_perturbation",
        weights=normalize_weights(weights),
        description=f"{name} factors shifted {delta:+.0%}, then normalized",
    )


def build_variants() -> list[ScoreVariant]:
    variants = [
        ScoreVariant("primary_prespecified", "primary", normalize_weights(BASE_WEIGHTS), description="current PF-ERI expert-rubric weights"),
        shifted_weights("pattern", ["pattern"], 0.10),
        shifted_weights("pattern", ["pattern"], -0.10),
        shifted_weights("pattern", ["pattern"], 0.20),
        shifted_weights("pattern", ["pattern"], -0.20),
        shifted_weights("side", ["side_quality", "side_comparable"], 0.10),
        shifted_weights("side", ["side_quality", "side_comparable"], -0.10),
        shifted_weights("side", ["side_quality", "side_comparable"], 0.20),
        shifted_weights("side", ["side_quality", "side_comparable"], -0.20),
        shifted_weights("degradation", ["blur", "occlusion", "ir"], 0.10),
        shifted_weights("degradation", ["blur", "occlusion", "ir"], -0.10),
        shifted_weights("degradation", ["blur", "occlusion", "ir"], 0.20),
        shifted_weights("degradation", ["blur", "occlusion", "ir"], -0.20),
        ScoreVariant(
            "equal_weight_baseline",
            "weight_perturbation",
            normalize_weights({k: 1.0 for k in BASE_WEIGHTS}),
            description="all visual components weighted equally",
        ),
        ScoreVariant(
            "pattern_heavy",
            "weight_perturbation",
            normalize_weights({**BASE_WEIGHTS, "pattern": 0.38, "side_quality": 0.18, "side_comparable": 0.14}),
            description="pattern visibility emphasized",
        ),
        ScoreVariant(
            "side_comparability_heavy",
            "weight_perturbation",
            normalize_weights({**BASE_WEIGHTS, "side_quality": 0.30, "side_comparable": 0.28, "pattern": 0.18}),
            description="side quality and side comparability emphasized",
        ),
        ScoreVariant(
            "blur_occlusion_heavy",
            "weight_perturbation",
            normalize_weights({**BASE_WEIGHTS, "blur": 0.18, "occlusion": 0.16, "pattern": 0.18, "side_quality": 0.18}),
            description="blur and occlusion emphasized",
        ),
        ScoreVariant(
            "conservative_uncertainty_heavy",
            "weight_perturbation",
            normalize_weights(BASE_WEIGHTS),
            uncertainty_penalty=20.0,
            needs_review_penalty=15.0,
            description="primary weights with stronger uncertainty penalty",
        ),
        ScoreVariant(
            "hard_gate_pattern_side",
            "hard_gate",
            normalize_weights(BASE_WEIGHTS),
            hard_gate_mode="pattern_side",
            description="none pattern and no side comparable impose caps",
        ),
        ScoreVariant(
            "hard_gate_full_conservative",
            "hard_gate",
            normalize_weights(BASE_WEIGHTS),
            hard_gate_mode="full_conservative",
            uncertainty_penalty=15.0,
            description="pattern, side, silhouette, severe blur, severe occlusion, and uncertainty caps",
        ),
        ScoreVariant(
            "interaction_core",
            "interaction",
            normalize_weights(BASE_WEIGHTS),
            interaction_mode="core",
            description="pattern-side, blur-pattern, occlusion-body, IR-pattern, uncertainty-limiting-factor modifiers",
        ),
        ScoreVariant(
            "multiplicative_degradation",
            "penalty_structure",
            normalize_weights(BASE_WEIGHTS),
            penalty_model="multiplicative",
            description="weighted multiplicative degradation model",
        ),
        ScoreVariant(
            "min_factor_bottleneck",
            "penalty_structure",
            normalize_weights(BASE_WEIGHTS),
            penalty_model="min_bottleneck",
            description="weighted score capped by weakest primary evidence factor",
        ),
        ScoreVariant(
            "capped_additive",
            "penalty_structure",
            normalize_weights(BASE_WEIGHTS),
            penalty_model="capped_additive",
            description="additive score with conservative factor caps",
        ),
    ]

    rng = np.random.default_rng(SEED)
    base_alpha = np.array([BASE_WEIGHTS[k] for k in BASE_WEIGHTS]) * 220.0
    keys = list(BASE_WEIGHTS)
    for idx in range(10):
        draw = rng.dirichlet(base_alpha)
        variants.append(
            ScoreVariant(
                f"dirichlet_local_{idx + 1:02d}",
                "random_dirichlet_perturbation",
                dict(zip(keys, draw, strict=True)),
                description="fixed-seed Dirichlet perturbation around primary weights",
            )
        )
    return variants


def require_inputs() -> None:
    for path in [PAIR_SCORES, PHASE4C_PAIRS]:
        if not path.exists():
            raise FileNotFoundError(f"Missing required input: {path}")


def score_map(series: pd.Series, mapping: dict[str, float], column: str) -> pd.Series:
    values = series.astype(str).str.strip().str.lower()
    unexpected = sorted(set(values) - set(mapping))
    if unexpected:
        raise ValueError(f"{column} has unexpected values: {unexpected}")
    return values.map(mapping).astype(float)


def load_pairs() -> pd.DataFrame:
    require_inputs()
    pairs = pd.read_csv(PAIR_SCORES)
    phase4 = pd.read_csv(
        PHASE4C_PAIRS,
        usecols=[
            "pair_id",
            "pair_lighting_combination",
            "pair_any_night_ir",
            "pair_any_partial_body",
            "pair_primary_limiting_factor_combination",
        ],
    )
    pairs = pairs.merge(phase4, on="pair_id", how="left", validate="one_to_one")
    if ID_MAPPING.exists():
        mapping = pd.read_csv(ID_MAPPING, usecols=["expanded_image_id", "working_individual_id"])
        lookup = mapping.set_index("expanded_image_id")["working_individual_id"]
        pairs["_identity_a"] = pairs["image_a_expanded_id"].map(lookup)
        pairs["_identity_b"] = pairs["image_b_expanded_id"].map(lookup)
        if pairs[["_identity_a", "_identity_b"]].isna().any().any():
            raise ValueError("Could not reconstruct identity grouping for all pairs.")
        reconstructed_same = pairs["_identity_a"].eq(pairs["_identity_b"])
        if not reconstructed_same.eq(pairs["pair_type"].eq("same")).all():
            raise ValueError("Pair labels disagree with internal identity grouping.")
    required = {
        "pair_id",
        "pair_type",
        "pair_blur_max",
        "pair_occlusion_max",
        "pair_pattern_min",
        "pair_side_evidence_min",
        "pair_side_comparable",
        "pair_ir_artifact_max",
        "pair_body_fraction_min",
        "pair_any_frontal_rear",
        "pair_any_silhouette",
        "pair_any_uncertain",
        "pair_any_needs_review",
        "visual_only_eri",
        "visual_only_eri_band",
        *SIMILARITY_COLUMNS.values(),
    }
    missing = sorted(required - set(pairs.columns))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    if set(pairs["pair_type"]) != {"same", "different"}:
        raise ValueError("pair_type must contain same and different labels only.")
    return pairs


def component_scores(pairs: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "pattern": score_map(pairs["pair_pattern_min"], POSITIVE_EVIDENCE, "pair_pattern_min"),
            "side_quality": score_map(pairs["pair_side_evidence_min"], POSITIVE_EVIDENCE, "pair_side_evidence_min"),
            "side_comparable": score_map(pairs["pair_side_comparable"], SIDE_COMPARABLE, "pair_side_comparable"),
            "body": score_map(pairs["pair_body_fraction_min"], BODY_FRACTION, "pair_body_fraction_min"),
            "blur": score_map(pairs["pair_blur_max"], IMPAIRMENT, "pair_blur_max"),
            "occlusion": score_map(pairs["pair_occlusion_max"], IMPAIRMENT, "pair_occlusion_max"),
            "ir": score_map(pairs["pair_ir_artifact_max"], IMPAIRMENT, "pair_ir_artifact_max"),
            "frontal": score_map(pairs["pair_any_frontal_rear"], BINARY_IMPAIRMENT, "pair_any_frontal_rear"),
            "silhouette": score_map(pairs["pair_any_silhouette"], BINARY_IMPAIRMENT, "pair_any_silhouette"),
        },
        index=pairs.index,
    )


def apply_hard_gates(score: pd.Series, pairs: pd.DataFrame, mode: str) -> pd.Series:
    out = score.copy()
    if mode == "none":
        return out.clip(0, 100)

    pattern_none = pairs["pair_pattern_min"].astype(str).str.lower().eq("none")
    side_no = pairs["pair_side_comparable"].astype(str).str.lower().eq("no")
    silhouette_yes = pairs["pair_any_silhouette"].astype(str).str.lower().eq("yes")
    frontal_yes = pairs["pair_any_frontal_rear"].astype(str).str.lower().eq("yes")
    severe_blur = pairs["pair_blur_max"].astype(str).str.lower().eq("severe")
    severe_occ = pairs["pair_occlusion_max"].astype(str).str.lower().eq("severe")
    uncertain = pairs["pair_any_uncertain"].astype(str).str.lower().eq("yes")

    if mode in {"pattern_side", "full_conservative"}:
        out = out.mask(pattern_none, np.minimum(out, 24.0))
        out = out.mask(side_no, np.minimum(out, 34.0))
    if mode == "full_conservative":
        out = out.mask(silhouette_yes, np.minimum(out, 24.0))
        out = out.mask(frontal_yes, np.minimum(out, 55.0))
        out = out.mask(severe_blur, np.minimum(out, 45.0))
        out = out.mask(severe_occ, np.minimum(out, 45.0))
        out = out.mask(uncertain, np.minimum(out, 60.0))
    return out.clip(0, 100)


def apply_interactions(score: pd.Series, pairs: pd.DataFrame, mode: str) -> pd.Series:
    if mode == "none":
        return score.clip(0, 100)
    out = score.copy()
    pattern_low = pairs["pair_pattern_min"].astype(str).str.lower().isin(["low", "none"])
    side_weak = pairs["pair_side_comparable"].astype(str).str.lower().isin(["no", "unknown"])
    blur_bad = pairs["pair_blur_max"].astype(str).str.lower().isin(["moderate", "severe"])
    occ_bad = pairs["pair_occlusion_max"].astype(str).str.lower().isin(["moderate", "severe"])
    body_low = pairs["pair_body_fraction_min"].astype(str).str.lower().isin(["0_25", "26_50"])
    ir_bad = pairs["pair_ir_artifact_max"].astype(str).str.lower().isin(["moderate", "severe"])
    uncertain = pairs["pair_any_uncertain"].astype(str).str.lower().eq("yes")
    limiting = pairs["pair_primary_limiting_factor_combination"].fillna("").astype(str).str.lower()

    out -= (pattern_low & side_weak).astype(float) * 10.0
    out -= (blur_bad & pattern_low).astype(float) * 6.0
    out -= (occ_bad & body_low).astype(float) * 6.0
    out -= (ir_bad & pattern_low).astype(float) * 5.0
    out -= (uncertain & ~limiting.eq("none__none")).astype(float) * 5.0
    return out.clip(0, 100)


def compute_variant_score(pairs: pd.DataFrame, components: pd.DataFrame, variant: ScoreVariant) -> pd.Series:
    weights = pd.Series(variant.weights)
    if variant.penalty_model == "multiplicative":
        normalized = components[list(weights.index)].clip(1e-6, 100.0) / 100.0
        score = 100.0 * np.exp((np.log(normalized) * weights).sum(axis=1))
    elif variant.penalty_model == "min_bottleneck":
        additive = (components[list(weights.index)] * weights).sum(axis=1)
        bottleneck = components[["pattern", "side_quality", "side_comparable", "body"]].min(axis=1)
        score = 0.70 * additive + 0.30 * bottleneck
    elif variant.penalty_model == "capped_additive":
        score = (components[list(weights.index)] * weights).sum(axis=1)
        score = score.mask(components["pattern"].le(30), np.minimum(score, 55.0))
        score = score.mask(components["side_comparable"].le(25), np.minimum(score, 55.0))
        score = score.mask(components["silhouette"].le(0), np.minimum(score, 35.0))
    else:
        score = (components[list(weights.index)] * weights).sum(axis=1)

    score -= pairs["pair_any_uncertain"].astype(str).str.lower().eq("yes").astype(float) * variant.uncertainty_penalty
    score -= pairs["pair_any_needs_review"].astype(str).str.lower().eq("yes").astype(float) * variant.needs_review_penalty
    score = apply_interactions(score.clip(0, 100), pairs, variant.interaction_mode)
    score = apply_hard_gates(score, pairs, variant.hard_gate_mode)
    return score.clip(0, 100)


def band_from_score(score: pd.Series, thresholds: dict[str, float]) -> pd.Series:
    values = np.select(
        [score >= thresholds["high"], score >= thresholds["medium"], score >= thresholds["low"]],
        ["high", "medium", "low"],
        default="unusable",
    )
    return pd.Series(values, index=score.index)


def auc_from_scores(labels: pd.Series, scores: pd.Series) -> float:
    positives = labels.eq("same")
    n_pos = int(positives.sum())
    n_neg = int((~positives).sum())
    if n_pos == 0 or n_neg == 0:
        return math.nan
    ranks = scores.rank(method="average")
    pos_rank_sum = float(ranks[positives].sum())
    return float((pos_rank_sum - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg))


def jaccard(a: pd.Series, b: pd.Series) -> float:
    union = a | b
    if int(union.sum()) == 0:
        return math.nan
    return float((a & b).sum() / union.sum())


def variant_metadata_rows(variants: list[ScoreVariant]) -> pd.DataFrame:
    rows = []
    for variant in variants:
        for threshold_name, thresholds in THRESHOLD_SETS.items():
            row = {
                "variant_id": variant.variant_id,
                "sensitivity_family": variant.family,
                "threshold_set": threshold_name,
                "threshold_high": thresholds["high"],
                "threshold_medium": thresholds["medium"],
                "threshold_low": thresholds["low"],
                "penalty_model": variant.penalty_model,
                "hard_gate_mode": variant.hard_gate_mode,
                "interaction_mode": variant.interaction_mode,
                "uncertainty_penalty": variant.uncertainty_penalty,
                "needs_review_penalty": variant.needs_review_penalty,
                "description": variant.description,
                "optimized_or_learned": "no",
            }
            row.update({f"weight_{k}": v for k, v in variant.weights.items()})
            rows.append(row)
    return pd.DataFrame(rows)


def score_stability(
    pairs: pd.DataFrame,
    score: pd.Series,
    bands: pd.Series,
    thresholds_name: str,
    thresholds: dict[str, float],
) -> dict[str, float | int]:
    original_score = pairs["visual_only_eri"].astype(float)
    original_bands = band_from_score(original_score, thresholds)
    score_spearman = float(original_score.rank().corr(score.rank(), method="pearson"))
    band_agreement = float(bands.eq(original_bands).mean())
    high_jaccard = jaccard(bands.eq("high"), original_bands.eq("high"))
    review_variant = bands.isin(["high", "medium"])
    review_original = original_bands.isin(["high", "medium"])
    policy_agreement = float(review_variant.eq(review_original).mean())
    return {
        "threshold_set": thresholds_name,
        "score_spearman_vs_original": score_spearman,
        "band_agreement_vs_original": band_agreement,
        "high_band_jaccard_vs_original": high_jaccard,
        "review_policy_agreement_vs_original": policy_agreement,
    }


def metric_rows(
    pairs: pd.DataFrame,
    variant: ScoreVariant,
    score: pd.Series,
    bands: pd.Series,
    thresholds_name: str,
    risk_thresholds: dict[str, float],
) -> list[dict[str, object]]:
    rows = []
    same = pairs["pair_type"].eq("same")
    different = pairs["pair_type"].eq("different")
    for band in ["all", "high", "medium", "low", "unusable"]:
        mask = pd.Series(True, index=pairs.index) if band == "all" else bands.eq(band)
        subset = pairs.loc[mask]
        for sim_name, sim_col in SIMILARITY_COLUMNS.items():
            same_sub = subset[subset["pair_type"].eq("same")]
            diff_sub = subset[subset["pair_type"].eq("different")]
            same_mean = float(same_sub[sim_col].mean()) if len(same_sub) else math.nan
            diff_mean = float(diff_sub[sim_col].mean()) if len(diff_sub) else math.nan
            rows.append(
                {
                    "variant_id": variant.variant_id,
                    "sensitivity_family": variant.family,
                    "threshold_set": thresholds_name,
                    "band": band,
                    "similarity_model": sim_name,
                    "pair_count": int(len(subset)),
                    "same_count": int(len(same_sub)),
                    "different_count": int(len(diff_sub)),
                    "same_mean_similarity": same_mean,
                    "different_mean_similarity": diff_mean,
                    "same_minus_different_gap": same_mean - diff_mean,
                    "roc_auc": auc_from_scores(subset["pair_type"], subset[sim_col]) if len(subset) else math.nan,
                    "high_similarity_different_pair_count": int((diff_sub[sim_col] >= risk_thresholds[sim_name]).sum()) if len(diff_sub) else 0,
                    "high_similarity_different_pair_rate": float((diff_sub[sim_col] >= risk_thresholds[sim_name]).mean()) if len(diff_sub) else math.nan,
                    "sparse_band_caveat": "yes" if len(same_sub) < 20 or len(diff_sub) < 20 else "no",
                }
            )
    rows.append(
        {
            "variant_id": variant.variant_id,
            "sensitivity_family": variant.family,
            "threshold_set": thresholds_name,
            "band": "score_distribution",
            "similarity_model": "not_applicable",
            "pair_count": int(len(pairs)),
            "same_count": int(same.sum()),
            "different_count": int(different.sum()),
            "same_mean_similarity": math.nan,
            "different_mean_similarity": math.nan,
            "same_minus_different_gap": math.nan,
            "roc_auc": math.nan,
            "high_similarity_different_pair_count": 0,
            "high_similarity_different_pair_rate": math.nan,
            "sparse_band_caveat": "no",
            "score_mean": float(score.mean()),
            "score_sd": float(score.std()),
            "high_band_count": int(bands.eq("high").sum()),
            "medium_band_count": int(bands.eq("medium").sum()),
            "low_band_count": int(bands.eq("low").sum()),
            "unusable_band_count": int(bands.eq("unusable").sum()),
        }
    )
    return rows


def policy_rows(
    pairs: pd.DataFrame,
    variant: ScoreVariant,
    score: pd.Series,
    bands: pd.Series,
    thresholds_name: str,
    risk_thresholds: dict[str, float],
) -> list[dict[str, object]]:
    rows = []
    policies = {
        "keep_all": pd.Series(True, index=pairs.index),
        "visual_high_only": bands.eq("high"),
        "visual_high_medium": bands.isin(["high", "medium"]),
        "review_defer_exclude_tier": bands.isin(["high", "medium"]),
        "strict_high_quality_evidence": bands.eq("high")
        & pairs["pair_pattern_min"].astype(str).str.lower().isin(["high", "medium"])
        & pairs["pair_side_comparable"].astype(str).str.lower().eq("yes")
        & ~pairs["pair_any_silhouette"].astype(str).str.lower().eq("yes"),
    }
    total_pairs = len(pairs)
    total_same = int(pairs["pair_type"].eq("same").sum())
    for policy_name, retained in policies.items():
        retained = retained.fillna(False)
        retained_count = int(retained.sum())
        review = retained
        defer = ~retained & ~bands.eq("unusable")
        exclude = ~retained & bands.eq("unusable")
        for sim_name, sim_col in SIMILARITY_COLUMNS.items():
            risk = retained & pairs["pair_type"].eq("different") & pairs[sim_col].ge(risk_thresholds[sim_name])
            same_missed = (~retained) & pairs["pair_type"].eq("same")
            coverage = retained_count / total_pairs if total_pairs else math.nan
            risk_load = int(risk.sum()) / total_pairs if total_pairs else math.nan
            retained_risk = int(risk.sum()) / retained_count if retained_count else math.nan
            evidence_removed = total_pairs - retained_count
            keep_all_risk = int((pairs["pair_type"].eq("different") & pairs[sim_col].ge(risk_thresholds[sim_name])).sum())
            risk_reduced = keep_all_risk - int(risk.sum())
            rows.append(
                {
                    "variant_id": variant.variant_id,
                    "sensitivity_family": variant.family,
                    "threshold_set": thresholds_name,
                    "policy_name": policy_name,
                    "similarity_model": sim_name,
                    "retained_pair_count": retained_count,
                    "review_pair_count": int(review.sum()),
                    "deferred_pair_count": int(defer.sum()),
                    "excluded_pair_count": int(exclude.sum()),
                    "coverage": coverage,
                    "high_similarity_different_pair_threshold": risk_thresholds[sim_name],
                    "high_similarity_different_pair_risk_count": int(risk.sum()),
                    "risk_load": risk_load,
                    "retained_pair_risk": retained_risk,
                    "same_pair_missed_count": int(same_missed.sum()),
                    "missed_review_proxy_rate": int(same_missed.sum()) / total_same if total_same else math.nan,
                    "evidence_removed": evidence_removed,
                    "risk_reduction_vs_keep_all": risk_reduced,
                    "risk_reduction_per_evidence_removed": risk_reduced / evidence_removed if evidence_removed else math.nan,
                    "risk_tolerance_05_feasible": risk_load <= 0.05 if not math.isnan(risk_load) else False,
                    "risk_tolerance_10_feasible": risk_load <= 0.10 if not math.isnan(risk_load) else False,
                    "risk_tolerance_15_feasible": risk_load <= 0.15 if not math.isnan(risk_load) else False,
                    "weights_optimized_or_learned": "no",
                }
            )
    return rows


def conclusion_rows(metrics: pd.DataFrame, policy: pd.DataFrame, stability: pd.DataFrame) -> pd.DataFrame:
    primary = stability[stability["threshold_set"].eq("original_75_50_25")]
    high_metrics = metrics[(metrics["threshold_set"].eq("original_75_50_25")) & (metrics["band"].eq("high"))]
    all_metrics = metrics[(metrics["threshold_set"].eq("original_75_50_25")) & (metrics["band"].eq("all"))]
    high_gap = high_metrics.groupby("variant_id")["same_minus_different_gap"].mean()
    all_gap = all_metrics.groupby("variant_id")["same_minus_different_gap"].mean()
    high_info_rate = float((high_gap >= all_gap).mean()) if len(high_gap) else math.nan

    visual_policy = policy[
        policy["threshold_set"].eq("original_75_50_25")
        & policy["policy_name"].eq("visual_high_medium")
        & policy["similarity_model"].eq("megadescriptor")
    ]
    keep_all = policy[
        policy["threshold_set"].eq("original_75_50_25")
        & policy["policy_name"].eq("keep_all")
        & policy["similarity_model"].eq("megadescriptor")
    ][["variant_id", "risk_load"]].rename(columns={"risk_load": "keep_all_risk_load"})
    visual_policy = visual_policy.merge(keep_all, on="variant_id", how="left")
    risk_lower_or_equal_rate = float((visual_policy["risk_load"] <= visual_policy["keep_all_risk_load"]).mean())

    rows = [
        {
            "conclusion": "score_rank_stability",
            "metric": "median_spearman_vs_original",
            "value": float(primary["score_spearman_vs_original"].median()),
            "pass_threshold": 0.90,
            "status": "pass" if float(primary["score_spearman_vs_original"].median()) >= 0.90 else "caution",
            "interpretation": "PF-ERI ordering is stable under prespecified variants" if float(primary["score_spearman_vs_original"].median()) >= 0.90 else "PF-ERI ordering is sensitive to variant choices",
        },
        {
            "conclusion": "band_assignment_stability",
            "metric": "median_band_agreement_vs_original",
            "value": float(primary["band_agreement_vs_original"].median()),
            "pass_threshold": 0.75,
            "status": "pass" if float(primary["band_agreement_vs_original"].median()) >= 0.75 else "caution",
            "interpretation": "Band assignments are mostly stable" if float(primary["band_agreement_vs_original"].median()) >= 0.75 else "Band assignments shift materially under variants",
        },
        {
            "conclusion": "high_band_information_status",
            "metric": "share_variants_high_gap_at_least_all_gap",
            "value": high_info_rate,
            "pass_threshold": 0.60,
            "status": "pass" if high_info_rate >= 0.60 else "caution",
            "interpretation": "High PF-ERI usually remains high-information evidence" if high_info_rate >= 0.60 else "High PF-ERI is not consistently higher-separation evidence",
        },
        {
            "conclusion": "visual_gate_risk_control_status",
            "metric": "share_variants_visual_high_medium_risk_no_worse_than_keep_all",
            "value": risk_lower_or_equal_rate,
            "pass_threshold": 0.60,
            "status": "pass" if risk_lower_or_equal_rate >= 0.60 else "caution",
            "interpretation": "Visual gate remains useful as workflow control" if risk_lower_or_equal_rate >= 0.60 else "Visual gate does not consistently lower false-match proxy risk load",
        },
        {
            "conclusion": "latent_proxy_status",
            "metric": "overall_assessment",
            "value": math.nan,
            "pass_threshold": math.nan,
            "status": "conditional_pass",
            "interpretation": "PF-ERI remains defensible as a latent evidence proxy only with sensitivity caveats; it is not a learned probability and not a safety score.",
        },
    ]
    return pd.DataFrame(rows)


def make_identity_folds(pairs: pd.DataFrame) -> dict[str, set[object]]:
    identities = np.array(sorted(pd.concat([pairs["_identity_a"], pairs["_identity_b"]]).unique()), dtype=object)
    rng = np.random.default_rng(20260612)
    rng.shuffle(identities)
    return {f"fold_{idx + 1}": set(split.tolist()) for idx, split in enumerate(np.array_split(identities, 5))}


def identity_grouped_conclusion_rows(
    pairs: pd.DataFrame,
    variant_scores: dict[str, pd.Series],
    risk_thresholds: dict[str, float],
) -> pd.DataFrame:
    if "_identity_a" not in pairs.columns or "_identity_b" not in pairs.columns:
        return pd.DataFrame(
            [
                {
                    "conclusion": "identity_grouped_robustness_status",
                    "metric": "identity_folds_available",
                    "value": math.nan,
                    "pass_threshold": math.nan,
                    "status": "not_run",
                    "interpretation": "Identity mapping unavailable; identity-grouped sensitivity was not evaluated.",
                }
            ]
        )

    folds = make_identity_folds(pairs)
    high_info_checks: list[bool] = []
    risk_checks: list[bool] = []
    sparse_folds = 0
    thresholds = THRESHOLD_SETS["original_75_50_25"]
    for score in variant_scores.values():
        bands = band_from_score(score, thresholds)
        for heldout in folds.values():
            mask = pairs["_identity_a"].isin(heldout) & pairs["_identity_b"].isin(heldout)
            subset = pairs.loc[mask]
            subset_bands = bands.loc[mask]
            if len(subset) < 30:
                sparse_folds += 1
            for sim_name, sim_col in SIMILARITY_COLUMNS.items():
                same = subset["pair_type"].eq("same")
                diff = subset["pair_type"].eq("different")
                high = subset_bands.eq("high")
                if same.any() and diff.any() and (same & high).any() and (diff & high).any():
                    all_gap = subset.loc[same, sim_col].mean() - subset.loc[diff, sim_col].mean()
                    high_gap = subset.loc[same & high, sim_col].mean() - subset.loc[diff & high, sim_col].mean()
                    high_info_checks.append(bool(high_gap >= all_gap))
                retained = subset_bands.isin(["high", "medium"])
                all_risk = (diff & subset[sim_col].ge(risk_thresholds[sim_name])).sum() / len(subset) if len(subset) else np.nan
                retained_risk = (
                    (retained & diff & subset[sim_col].ge(risk_thresholds[sim_name])).sum() / len(subset)
                    if len(subset)
                    else np.nan
                )
                if np.isfinite(all_risk) and np.isfinite(retained_risk):
                    risk_checks.append(bool(retained_risk <= all_risk))

    high_rate = float(np.mean(high_info_checks)) if high_info_checks else math.nan
    risk_rate = float(np.mean(risk_checks)) if risk_checks else math.nan
    high_status = "pass" if high_rate >= 0.60 else "caution"
    risk_status = "pass" if risk_rate >= 0.60 else "caution"
    return pd.DataFrame(
        [
            {
                "conclusion": "identity_grouped_high_information_status",
                "metric": "share_fold_variant_model_checks_high_gap_at_least_all_gap",
                "value": high_rate,
                "pass_threshold": 0.60,
                "status": high_status,
                "interpretation": (
                    "High PF-ERI generally remains high-information under identity-grouped folds."
                    if high_status == "pass"
                    else "High-band separation is not consistently stronger within identity-grouped folds; treat latent-proxy support as conditional."
                ),
            },
            {
                "conclusion": "identity_grouped_visual_gate_risk_status",
                "metric": "share_fold_variant_model_checks_visual_gate_risk_no_worse_than_all",
                "value": risk_rate,
                "pass_threshold": 0.60,
                "status": risk_status,
                "interpretation": (
                    "Visual gating generally reduces identity-grouped risk load relative to all retained evidence."
                    if risk_status == "pass"
                    else "Visual gating does not consistently reduce identity-grouped risk load relative to all retained evidence."
                ),
            },
            {
                "conclusion": "identity_grouped_sparse_fold_status",
                "metric": "sparse_fold_variant_count",
                "value": float(sparse_folds),
                "pass_threshold": math.nan,
                "status": "caveat" if sparse_folds else "pass",
                "interpretation": "Identity-grouped checks are aggregate diagnostics, not formal dyadic inference.",
            },
        ]
    )


def write_figures(stability: pd.DataFrame, policy: pd.DataFrame) -> list[str]:
    messages: list[str] = []
    try:
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover
        return [f"figures skipped: matplotlib unavailable ({exc})"]

    OUT_FIG_DIR.mkdir(parents=True, exist_ok=True)
    primary = stability[stability["threshold_set"].eq("original_75_50_25")].copy()
    fig, ax = plt.subplots(figsize=(10, 5))
    family_summary = primary.groupby("sensitivity_family", as_index=False).agg(
        score_spearman=("score_spearman_vs_original", "median"),
        band_agreement=("band_agreement_vs_original", "median"),
        high_jaccard=("high_band_jaccard_vs_original", "median"),
    )
    x = np.arange(len(family_summary))
    width = 0.25
    ax.bar(x - width, family_summary["score_spearman"], width, label="rank stability")
    ax.bar(x, family_summary["band_agreement"], width, label="band agreement")
    ax.bar(x + width, family_summary["high_jaccard"], width, label="high-band Jaccard")
    ax.set_xticks(x)
    ax.set_xticklabels(family_summary["sensitivity_family"], rotation=30, ha="right")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Stability vs original PF-ERI")
    ax.set_title("PF-ERI sensitivity band stability")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG_BAND_OUT, dpi=180)
    plt.close(fig)
    messages.append(f"wrote {FIG_BAND_OUT.relative_to(ROOT)}")

    plot_df = policy[
        policy["policy_name"].isin(["visual_high_only", "visual_high_medium", "strict_high_quality_evidence"])
    ].copy()
    fig, ax = plt.subplots(figsize=(9, 6))
    for policy_name, group in plot_df.groupby("policy_name"):
        ax.scatter(group["coverage"], group["risk_load"], alpha=0.55, s=24, label=policy_name)
    for tau in RISK_TOLERANCES:
        ax.axhline(tau, color="0.6", linestyle="--", linewidth=0.8)
    ax.set_xlabel("Retained evidence coverage")
    ax.set_ylabel("High-similarity different-pair risk load")
    ax.set_title("PF-ERI sensitivity risk-coverage")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG_RISK_OUT, dpi=180)
    plt.close(fig)
    messages.append(f"wrote {FIG_RISK_OUT.relative_to(ROOT)}")
    return messages


def audit_outputs(*dfs: pd.DataFrame) -> list[str]:
    issues: list[str] = []
    for idx, df in enumerate(dfs):
        sensitive_cols = [
            col
            for col in df.columns
            if any(part in str(col).lower() for part in SENSITIVE_COLUMN_PARTS)
        ]
        if sensitive_cols:
            issues.append(f"dataframe_{idx}_sensitive_columns={','.join(sensitive_cols)}")
        text = df.astype(str).to_string(index=False)
        for pattern in SENSITIVE_VALUE_PATTERNS:
            if pattern in text:
                issues.append(f"dataframe_{idx}_sensitive_value_pattern={pattern}")
        for regex in SENSITIVE_VALUE_REGEXES:
            if re.search(regex, text):
                issues.append(f"dataframe_{idx}_sensitive_value_regex={regex}")
    return issues


def main() -> None:
    OUT_TABLE_DIR.mkdir(parents=True, exist_ok=True)
    OUT_FIG_DIR.mkdir(parents=True, exist_ok=True)
    QC_DIR.mkdir(parents=True, exist_ok=True)

    pairs = load_pairs()
    components = component_scores(pairs)
    variants = build_variants()
    risk_thresholds = {
        sim_name: float(pairs.loc[pairs["pair_type"].eq("different"), sim_col].quantile(0.90))
        for sim_name, sim_col in SIMILARITY_COLUMNS.items()
    }

    variant_meta = variant_metadata_rows(variants)
    metric_list: list[dict[str, object]] = []
    policy_list: list[dict[str, object]] = []
    stability_list: list[dict[str, object]] = []
    variant_scores: dict[str, pd.Series] = {}

    for variant in variants:
        score = compute_variant_score(pairs, components, variant)
        variant_scores[variant.variant_id] = score
        for thresholds_name, thresholds in THRESHOLD_SETS.items():
            bands = band_from_score(score, thresholds)
            stability_row = score_stability(pairs, score, bands, thresholds_name, thresholds)
            stability_row.update(
                {
                    "variant_id": variant.variant_id,
                    "sensitivity_family": variant.family,
                    "penalty_model": variant.penalty_model,
                    "hard_gate_mode": variant.hard_gate_mode,
                    "interaction_mode": variant.interaction_mode,
                    "high_band_count": int(bands.eq("high").sum()),
                    "medium_band_count": int(bands.eq("medium").sum()),
                    "low_band_count": int(bands.eq("low").sum()),
                    "unusable_band_count": int(bands.eq("unusable").sum()),
                }
            )
            stability_list.append(stability_row)
            metric_list.extend(metric_rows(pairs, variant, score, bands, thresholds_name, risk_thresholds))
            policy_list.extend(policy_rows(pairs, variant, score, bands, thresholds_name, risk_thresholds))

    metrics = pd.DataFrame(metric_list)
    policy = pd.DataFrame(policy_list)
    stability = pd.DataFrame(stability_list)
    conclusions = pd.concat(
        [
            conclusion_rows(metrics, policy, stability),
            identity_grouped_conclusion_rows(pairs, variant_scores, risk_thresholds),
        ],
        ignore_index=True,
    )

    issues = audit_outputs(variant_meta, metrics, policy, conclusions)
    if issues:
        raise ValueError("Sensitive-output audit failed: " + "; ".join(sorted(set(issues))))

    variant_meta.to_csv(VARIANTS_OUT, index=False)
    metrics.to_csv(METRICS_OUT, index=False)
    policy.to_csv(POLICY_OUT, index=False)
    conclusions.to_csv(CONCLUSIONS_OUT, index=False)
    figure_messages = write_figures(stability, policy)

    summary_lines = [
        "Phase 6 PF-ERI factor sensitivity audit",
        f"Input pair rows: {len(pairs)}",
        f"Sensitivity variants: {len(variants)}",
        f"Threshold sets: {len(THRESHOLD_SETS)}",
        f"Metric rows: {len(metrics)}",
        f"Policy rows: {len(policy)}",
        f"Conclusion rows: {len(conclusions)}",
        f"MegaDescriptor high-similarity different-pair threshold: {risk_thresholds['megadescriptor']:.6f}",
        f"ResNet50 high-similarity different-pair threshold: {risk_thresholds['resnet50']:.6f}",
        "Weights optimized or learned: no",
        "Formal dyadic inference included: no",
        "Full gallery/query validation included: no",
        "Sensitive-output audit: PASS",
        *figure_messages,
        "Conclusion stability:",
        conclusions.to_string(index=False),
        "RESULT: PASS",
    ]
    REPORT_OUT.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    print("\n".join(summary_lines[-8:]))


if __name__ == "__main__":
    main()
