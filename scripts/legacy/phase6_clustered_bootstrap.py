#!/usr/bin/env python3
"""Clustered bootstrap uncertainty for Phase 6 ERI-ReID validation."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PAIR_SCORES = ROOT / "outputs/czechlynx/phase5/czechlynx_phase5_pair_eri_scores_internal.csv"
ID_MAPPING = ROOT / "data/interim/czechlynx/czechlynx_expanded_125x4_internal_with_ids.csv"
OUT_DIR = ROOT / "outputs/czechlynx/phase6/uncertainty"
QC_DIR = ROOT / "outputs/czechlynx/qc"
INTERVALS_OUT = OUT_DIR / "phase6_clustered_bootstrap_intervals.csv"
REPORT_OUT = QC_DIR / "phase6_clustered_bootstrap_report.txt"

SEED = 20260612
BOOTSTRAP_REPS = 500
SCORE_COLUMNS = {
    "visual_only_eri": "visual_only_eri",
    "hybrid_eri": "hybrid_eri",
}
SIMILARITY_COLUMNS = {
    "megadescriptor": "megadescriptor_similarity",
    "resnet50": "resnet50_similarity",
}
SENSITIVE_VALUE_PATTERNS = ("working_individual_id", "lynx_", "/Users/", "data/interim")


def load_pairs() -> pd.DataFrame:
    pairs = pd.read_csv(PAIR_SCORES)
    mapping = pd.read_csv(ID_MAPPING, usecols=["expanded_image_id", "working_individual_id"])
    lookup = mapping.set_index("expanded_image_id")["working_individual_id"]
    pairs["_identity_a"] = pairs["image_a_expanded_id"].map(lookup)
    pairs["_identity_b"] = pairs["image_b_expanded_id"].map(lookup)
    if pairs[["_identity_a", "_identity_b"]].isna().any().any():
        raise ValueError("Could not map all pairs to internal identities.")
    reconstructed_same = pairs["_identity_a"].eq(pairs["_identity_b"])
    if not reconstructed_same.eq(pairs["pair_type"].eq("same")).all():
        raise ValueError("Pair labels disagree with internal identity mapping.")
    return pairs


def band_from_score(value: float) -> str:
    if value >= 75:
        return "high"
    if value >= 55:
        return "medium"
    if value >= 35:
        return "low"
    return "unusable"


def weighted_mean(values: pd.Series, weights: np.ndarray) -> float:
    valid = np.isfinite(values.to_numpy(dtype=float)) & np.isfinite(weights) & (weights > 0)
    if not valid.any():
        return np.nan
    return float(np.average(values.to_numpy(dtype=float)[valid], weights=weights[valid]))


def weighted_auc(labels: pd.Series, scores: pd.Series, weights: np.ndarray) -> float:
    y = labels.to_numpy(dtype=int)
    s = scores.to_numpy(dtype=float)
    w = weights.astype(float)
    valid = np.isfinite(s) & np.isfinite(w) & (w > 0)
    y = y[valid]
    s = s[valid]
    w = w[valid]
    if len(np.unique(y)) != 2:
        return np.nan
    order = np.argsort(s, kind="mergesort")
    s = s[order]
    y = y[order]
    w = w[order]
    total_pos = float(w[y == 1].sum())
    total_neg = float(w[y == 0].sum())
    if total_pos <= 0 or total_neg <= 0:
        return np.nan
    numerator = 0.0
    cum_neg = 0.0
    start = 0
    while start < len(s):
        end = start + 1
        while end < len(s) and s[end] == s[start]:
            end += 1
        group_y = y[start:end]
        group_w = w[start:end]
        pos_w = float(group_w[group_y == 1].sum())
        neg_w = float(group_w[group_y == 0].sum())
        numerator += pos_w * (cum_neg + 0.5 * neg_w)
        cum_neg += neg_w
        start = end
    return numerator / (total_pos * total_neg)


def metric_rows(pairs: pd.DataFrame, weights: np.ndarray, thresholds: dict[str, float]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    total_weight = float(weights.sum())
    same = pairs["pair_type"].eq("same")
    diff = ~same
    for sim_name, sim_col in SIMILARITY_COLUMNS.items():
        rows.extend(
            [
                {
                    "score_name": "all_pairs",
                    "band_or_policy": "all",
                    "similarity_model": sim_name,
                    "metric": "roc_auc",
                    "value": weighted_auc(same.astype(int), pairs[sim_col], weights),
                },
                {
                    "score_name": "all_pairs",
                    "band_or_policy": "all",
                    "similarity_model": sim_name,
                    "metric": "same_minus_different_gap",
                    "value": weighted_mean(pairs.loc[same, sim_col], weights[same.to_numpy()])
                    - weighted_mean(pairs.loc[diff, sim_col], weights[diff.to_numpy()]),
                },
            ]
        )

    for score_name, score_col in SCORE_COLUMNS.items():
        bands = pairs[score_col].map(band_from_score)
        for sim_name, sim_col in SIMILARITY_COLUMNS.items():
            band_metrics: dict[str, dict[str, float]] = {}
            for band in ["high", "medium", "low", "unusable"]:
                mask = bands.eq(band).to_numpy()
                band_weights = weights[mask]
                band_pairs = pairs.loc[mask]
                if len(band_pairs) == 0 or band_weights.sum() <= 0:
                    auc = np.nan
                    gap = np.nan
                else:
                    band_same = band_pairs["pair_type"].eq("same")
                    band_diff = ~band_same
                    auc = weighted_auc(band_same.astype(int), band_pairs[sim_col], band_weights)
                    gap = weighted_mean(band_pairs.loc[band_same, sim_col], band_weights[band_same.to_numpy()]) - weighted_mean(
                        band_pairs.loc[band_diff, sim_col], band_weights[band_diff.to_numpy()]
                    )
                band_metrics[band] = {"auc": auc, "gap": gap}
                rows.append(
                    {
                        "score_name": score_name,
                        "band_or_policy": band,
                        "similarity_model": sim_name,
                        "metric": "roc_auc",
                        "value": auc,
                    }
                )
                rows.append(
                    {
                        "score_name": score_name,
                        "band_or_policy": band,
                        "similarity_model": sim_name,
                        "metric": "same_minus_different_gap",
                        "value": gap,
                    }
                )

            for metric_name, key in [("auc_high_minus_low", "auc"), ("gap_high_minus_low", "gap")]:
                rows.append(
                    {
                        "score_name": score_name,
                        "band_or_policy": "high_minus_low",
                        "similarity_model": sim_name,
                        "metric": metric_name,
                        "value": band_metrics["high"][key] - band_metrics["low"][key],
                    }
                )

            for policy_name, keep_bands in {
                "keep_high": {"high"},
                "keep_high_medium": {"high", "medium"},
            }.items():
                mask = bands.isin(keep_bands).to_numpy()
                retained_weight = float(weights[mask].sum())
                risk_mask = diff.to_numpy() & pairs[sim_col].ge(thresholds[sim_name]).to_numpy() & mask
                rows.append(
                    {
                        "score_name": score_name,
                        "band_or_policy": policy_name,
                        "similarity_model": sim_name,
                        "metric": "retention_rate",
                        "value": retained_weight / total_weight if total_weight else np.nan,
                    }
                )
                rows.append(
                    {
                        "score_name": score_name,
                        "band_or_policy": policy_name,
                        "similarity_model": sim_name,
                        "metric": "risk_proxy_rate_among_retained",
                        "value": float(weights[risk_mask].sum() / retained_weight) if retained_weight else np.nan,
                    }
                )
    return rows


def bootstrap_weights(pairs: pd.DataFrame, identities: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    counts = Counter(rng.choice(identities, size=len(identities), replace=True).tolist())
    count_a = pairs["_identity_a"].map(counts).fillna(0).to_numpy(dtype=int)
    count_b = pairs["_identity_b"].map(counts).fillna(0).to_numpy(dtype=int)
    same_identity = pairs["_identity_a"].eq(pairs["_identity_b"]).to_numpy()
    return np.where(same_identity, count_a, count_a * count_b).astype(float)


def make_intervals(full_rows: pd.DataFrame, replicate_rows: pd.DataFrame) -> pd.DataFrame:
    key_cols = ["score_name", "band_or_policy", "similarity_model", "metric"]
    rows = []
    for keys, full_group in full_rows.groupby(key_cols, dropna=False):
        score_name, band_or_policy, sim_name, metric = keys
        reps = replicate_rows
        for col, value in zip(key_cols, keys):
            reps = reps[reps[col].eq(value)]
        values = reps["value"].dropna().to_numpy(dtype=float)
        full_value = float(full_group["value"].iloc[0])
        caveats = []
        if len(values) < BOOTSTRAP_REPS * 0.8:
            caveats.append("many_invalid_replicates")
        if len(values) == 0:
            lower = upper = mean = np.nan
        else:
            lower, upper = np.percentile(values, [2.5, 97.5])
            mean = float(np.mean(values))
        rows.append(
            {
                "score_name": score_name,
                "band_or_policy": band_or_policy,
                "similarity_model": sim_name,
                "metric": metric,
                "estimate_from_full_data": full_value,
                "bootstrap_mean": mean,
                "ci_lower_2_5": float(lower) if np.isfinite(lower) else np.nan,
                "ci_upper_97_5": float(upper) if np.isfinite(upper) else np.nan,
                "valid_replicates": int(len(values)),
                "bootstrap_replicates": BOOTSTRAP_REPS,
                "caveat": ";".join(caveats),
            }
        )
    return pd.DataFrame(rows)


def audit_output(df: pd.DataFrame) -> list[str]:
    text = df.astype(str).to_string(index=False)
    return [f"sensitive_value_pattern_present={pattern}" for pattern in SENSITIVE_VALUE_PATTERNS if pattern in text]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    QC_DIR.mkdir(parents=True, exist_ok=True)
    pairs = load_pairs()
    identities = pd.concat([pairs["_identity_a"], pairs["_identity_b"]]).unique()
    if len(identities) < 30:
        raise ValueError("Too few identities for clustered bootstrap.")
    thresholds = {name: float(pairs[col].quantile(0.90)) for name, col in SIMILARITY_COLUMNS.items()}

    full_weights = np.ones(len(pairs), dtype=float)
    full_rows = pd.DataFrame(metric_rows(pairs, full_weights, thresholds))
    rng = np.random.default_rng(SEED)
    replicate_parts = []
    invalid_reps = 0
    for rep in range(BOOTSTRAP_REPS):
        weights = bootstrap_weights(pairs, identities, rng)
        if weights.sum() <= 0:
            invalid_reps += 1
            continue
        rep_rows = pd.DataFrame(metric_rows(pairs, weights, thresholds))
        rep_rows["replicate"] = rep + 1
        replicate_parts.append(rep_rows)

    if not replicate_parts:
        raise ValueError("No valid clustered bootstrap replicates produced.")
    replicate_rows = pd.concat(replicate_parts, ignore_index=True)
    intervals = make_intervals(full_rows, replicate_rows)
    issues = audit_output(intervals)
    intervals.to_csv(INTERVALS_OUT, index=False)
    status = "PASS" if not issues else "FAIL"
    headline = intervals[
        intervals["score_name"].eq("all_pairs") & intervals["metric"].eq("roc_auc")
    ][["similarity_model", "estimate_from_full_data", "ci_lower_2_5", "ci_upper_97_5"]]
    REPORT_OUT.write_text(
        "\n".join(
            [
                "Phase 6 clustered bootstrap audit",
                f"Status: {status}",
                f"Seed: {SEED}",
                f"Bootstrap replicates requested: {BOOTSTRAP_REPS}",
                f"Invalid empty replicates: {invalid_reps}",
                f"Identity clusters: {len(identities)}",
                "Bootstrap rule: sample identities with replacement; same-identity pairs receive sampled identity weight; different-identity pairs receive product of sampled endpoint weights.",
                "Headline overall AUC intervals:",
                headline.to_string(index=False),
                "Audit issues:",
                *(issues if issues else ["None"]),
                "Caveat: pair rows are dyadic, so these intervals are descriptive clustered uncertainty estimates, not a full multiway dependence model.",
                "",
            ]
        )
    )
    if issues:
        raise SystemExit("Phase 6 clustered bootstrap audit failed: " + "; ".join(issues))


if __name__ == "__main__":
    main()
