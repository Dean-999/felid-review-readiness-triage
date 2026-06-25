#!/usr/bin/env python3
"""Phase 6 identity-holdout validation for ERI-ReID.

This script uses internal known-ID labels only to create grouped validation
folds. Outputs are aggregate-only and must not expose identity labels or
sensitive source metadata.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PAIR_SCORES = ROOT / "outputs/czechlynx/phase5/czechlynx_phase5_pair_eri_scores_internal.csv"
ID_MAPPING = ROOT / "data/interim/czechlynx/czechlynx_expanded_125x4_internal_with_ids.csv"
OUT_DIR = ROOT / "outputs/czechlynx/phase6/tables"
QC_DIR = ROOT / "outputs/czechlynx/qc"
METRICS_OUT = OUT_DIR / "phase6_identity_holdout_validation.csv"
SUMMARY_OUT = OUT_DIR / "phase6_identity_holdout_summary.csv"
REPORT_OUT = QC_DIR / "phase6_identity_holdout_validation_report.txt"

SEED = 20260612
N_FOLDS = 5
SCORE_COLUMNS = {
    "visual_only_eri": "visual_only_eri",
    "model_support_score": "model_support_score",
    "hybrid_eri": "hybrid_eri",
}
SIMILARITY_COLUMNS = {
    "megadescriptor": "megadescriptor_similarity",
    "resnet50": "resnet50_similarity",
}
SENSITIVE_COLUMNS = {
    "unique_name",
    "working_individual_id",
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
}
SENSITIVE_VALUE_PATTERNS = ("lynx_", "/Users/", "data/interim", "review_image_path")


def auc_binary(labels: pd.Series, scores: pd.Series) -> float:
    y = labels.to_numpy()
    s = scores.to_numpy(dtype=float)
    valid = np.isfinite(s)
    y = y[valid]
    s = s[valid]
    if len(np.unique(y)) != 2:
        return np.nan
    order = np.argsort(s, kind="mergesort")
    sorted_s = s[order]
    sorted_y = y[order]
    total_pos = float((sorted_y == 1).sum())
    total_neg = float((sorted_y == 0).sum())
    numerator = 0.0
    cum_neg = 0.0
    start = 0
    while start < len(sorted_s):
        end = start + 1
        while end < len(sorted_s) and sorted_s[end] == sorted_s[start]:
            end += 1
        group_y = sorted_y[start:end]
        pos = float((group_y == 1).sum())
        neg = float((group_y == 0).sum())
        numerator += pos * (cum_neg + 0.5 * neg)
        cum_neg += neg
        start = end
    return numerator / (total_pos * total_neg)


def band_from_score(value: float) -> str:
    if value >= 75:
        return "high"
    if value >= 55:
        return "medium"
    if value >= 35:
        return "low"
    return "unusable"


def load_inputs() -> pd.DataFrame:
    if not PAIR_SCORES.exists():
        raise FileNotFoundError(f"Missing Phase 5 score table: {PAIR_SCORES}")
    if not ID_MAPPING.exists():
        raise FileNotFoundError(f"Missing internal ID mapping: {ID_MAPPING}")

    pairs = pd.read_csv(PAIR_SCORES)
    mapping = pd.read_csv(ID_MAPPING, usecols=["expanded_image_id", "working_individual_id"])
    if mapping["expanded_image_id"].duplicated().any():
        raise ValueError("Internal mapping has duplicate expanded_image_id rows.")

    identity_lookup = mapping.set_index("expanded_image_id")["working_individual_id"]
    pairs["_identity_a"] = pairs["image_a_expanded_id"].map(identity_lookup)
    pairs["_identity_b"] = pairs["image_b_expanded_id"].map(identity_lookup)
    if pairs[["_identity_a", "_identity_b"]].isna().any().any():
        raise ValueError("Could not map all pair images to internal identities.")

    reconstructed_same = pairs["_identity_a"].eq(pairs["_identity_b"])
    declared_same = pairs["pair_type"].eq("same")
    if not reconstructed_same.eq(declared_same).all():
        mismatch = int((~reconstructed_same.eq(declared_same)).sum())
        raise ValueError(f"Pair labels disagree with internal identity mapping for {mismatch} rows.")

    return pairs


def make_folds(identities: np.ndarray) -> dict[str, set[str]]:
    rng = np.random.default_rng(SEED)
    shuffled = np.array(sorted(identities), dtype=object)
    rng.shuffle(shuffled)
    splits = np.array_split(shuffled, N_FOLDS)
    folds = {f"fold_{idx + 1}": set(split.tolist()) for idx, split in enumerate(splits)}
    if sum(len(v) for v in folds.values()) != len(set(identities)):
        raise ValueError("Identity folds are not a partition.")
    return folds


def evaluate_subset(
    subset: pd.DataFrame,
    fold_id: str,
    heldout_count: int,
    score_name: str,
    score_column: str,
    band: str,
    sim_name: str,
    sim_column: str,
    risk_threshold: float,
) -> dict[str, object]:
    if band == "all":
        rows = subset
    else:
        rows = subset[subset["_band"].eq(band)]

    same_mask = rows["pair_type"].eq("same")
    diff_mask = rows["pair_type"].eq("different")
    same_count = int(same_mask.sum())
    diff_count = int(diff_mask.sum())
    risk_mask = diff_mask & rows[sim_column].ge(risk_threshold)
    auc = auc_binary(same_mask.astype(int), rows[sim_column]) if same_count and diff_count else np.nan
    same_mean = float(rows.loc[same_mask, sim_column].mean()) if same_count else np.nan
    diff_mean = float(rows.loc[diff_mask, sim_column].mean()) if diff_count else np.nan
    gap = same_mean - diff_mean if np.isfinite(same_mean) and np.isfinite(diff_mean) else np.nan
    score_mean = float(rows[score_column].mean()) if len(rows) else np.nan
    caveats = []
    if same_count == 0 or diff_count == 0:
        caveats.append("single_class_metric_not_reported")
    if len(rows) < 30:
        caveats.append("sparse_band")

    return {
        "fold_id": fold_id,
        "heldout_identity_count": heldout_count,
        "validation_scope": "both_images_heldout_identities",
        "score_name": score_name,
        "band": band,
        "similarity_model": sim_name,
        "retained_pair_count": int(len(rows)),
        "same_pair_count": same_count,
        "different_pair_count": diff_count,
        "retention_rate_within_fold": float(len(rows) / len(subset)) if len(subset) else np.nan,
        "mean_score": score_mean,
        "same_similarity_mean": same_mean,
        "different_similarity_mean": diff_mean,
        "same_minus_different_gap": gap,
        "roc_auc": auc,
        "train_90th_percentile_similarity_threshold": float(risk_threshold),
        "high_similarity_different_pair_count": int(risk_mask.sum()),
        "risk_proxy_rate_among_retained": float(risk_mask.sum() / len(rows)) if len(rows) else np.nan,
        "risk_proxy_rate_among_different": float(risk_mask.sum() / diff_count) if diff_count else np.nan,
        "caveat": ";".join(caveats) if caveats else "",
    }


def summarize(metrics: pd.DataFrame) -> pd.DataFrame:
    group_cols = ["score_name", "band", "similarity_model"]
    rows = []
    for keys, group in metrics.groupby(group_cols, dropna=False):
        score_name, band, sim_name = keys
        rows.append(
            {
                "score_name": score_name,
                "band": band,
                "similarity_model": sim_name,
                "fold_count": int(group["fold_id"].nunique()),
                "total_retained_pair_count": int(group["retained_pair_count"].sum()),
                "total_same_pair_count": int(group["same_pair_count"].sum()),
                "total_different_pair_count": int(group["different_pair_count"].sum()),
                "mean_retention_rate_within_fold": float(group["retention_rate_within_fold"].mean()),
                "mean_same_minus_different_gap": float(group["same_minus_different_gap"].mean(skipna=True)),
                "mean_roc_auc": float(group["roc_auc"].mean(skipna=True)),
                "mean_risk_proxy_rate_among_retained": float(
                    group["risk_proxy_rate_among_retained"].mean(skipna=True)
                ),
                "mean_risk_proxy_rate_among_different": float(
                    group["risk_proxy_rate_among_different"].mean(skipna=True)
                ),
                "sparse_or_single_class_fold_count": int(group["caveat"].astype(bool).sum()),
            }
        )
    return pd.DataFrame(rows)


def audit_output(df: pd.DataFrame) -> list[str]:
    issues: list[str] = []
    lower_cols = {col.lower() for col in df.columns}
    leaked_cols = sorted(lower_cols & SENSITIVE_COLUMNS)
    if leaked_cols:
        issues.append(f"sensitive_columns_present={','.join(leaked_cols)}")
    text = df.astype(str).to_string(index=False)
    for pattern in SENSITIVE_VALUE_PATTERNS:
        if pattern in text:
            issues.append(f"sensitive_value_pattern_present={pattern}")
    return issues


def write_report(metrics: pd.DataFrame, summary: pd.DataFrame, issues: list[str]) -> None:
    all_rows = summary[summary["band"].eq("all")]
    best_lines = []
    for _, row in all_rows.iterrows():
        best_lines.append(
            "- {score}/{model}: mean AUC={auc:.3f}, mean gap={gap:.3f}, "
            "risk among retained={risk:.3f}".format(
                score=row["score_name"],
                model=row["similarity_model"],
                auc=row["mean_roc_auc"],
                gap=row["mean_same_minus_different_gap"],
                risk=row["mean_risk_proxy_rate_among_retained"],
            )
        )
    status = "PASS" if not issues else "FAIL"
    REPORT_OUT.write_text(
        "\n".join(
            [
                "Phase 6 identity-holdout validation audit",
                f"Status: {status}",
                f"Seed: {SEED}",
                f"Folds: {N_FOLDS}",
                f"Metric rows: {len(metrics)}",
                f"Summary rows: {len(summary)}",
                "Validation scope: both images belong to held-out identities.",
                "Identity labels were used only in memory and are not written to output tables.",
                "Headline all-band metrics:",
                *best_lines,
                "Audit issues:",
                *(issues if issues else ["None"]),
                "Caveat: high-similarity different pairs are a validation proxy, not a field false-match rate.",
                "",
            ]
        )
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    QC_DIR.mkdir(parents=True, exist_ok=True)
    pairs = load_inputs()
    identities = pd.concat([pairs["_identity_a"], pairs["_identity_b"]]).unique()
    folds = make_folds(identities)

    rows: list[dict[str, object]] = []
    for fold_id, heldout in folds.items():
        heldout_mask = pairs["_identity_a"].isin(heldout) & pairs["_identity_b"].isin(heldout)
        train_mask = ~pairs["_identity_a"].isin(heldout) & ~pairs["_identity_b"].isin(heldout)
        heldout_pairs = pairs[heldout_mask].copy()
        train_pairs = pairs[train_mask].copy()
        if heldout_pairs.empty or train_pairs.empty:
            raise ValueError(f"{fold_id} produced empty heldout or train-like subset.")

        for score_name, score_column in SCORE_COLUMNS.items():
            heldout_pairs["_band"] = heldout_pairs[score_column].map(band_from_score)
            for sim_name, sim_column in SIMILARITY_COLUMNS.items():
                threshold = float(train_pairs[sim_column].quantile(0.90))
                for band in ["all", "high", "medium", "low", "unusable"]:
                    rows.append(
                        evaluate_subset(
                            heldout_pairs,
                            fold_id,
                            len(heldout),
                            score_name,
                            score_column,
                            band,
                            sim_name,
                            sim_column,
                            threshold,
                        )
                    )

    metrics = pd.DataFrame(rows)
    summary = summarize(metrics)
    issues = audit_output(metrics) + audit_output(summary)
    metrics.to_csv(METRICS_OUT, index=False)
    summary.to_csv(SUMMARY_OUT, index=False)
    write_report(metrics, summary, issues)
    if issues:
        raise SystemExit("Phase 6 identity-holdout validation audit failed: " + "; ".join(issues))


if __name__ == "__main__":
    main()
