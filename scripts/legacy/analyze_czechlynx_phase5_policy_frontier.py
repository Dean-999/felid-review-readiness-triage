#!/usr/bin/env python3
"""Build Phase 5 ERI-ReID policy frontier and baseline comparisons."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCORES_CSV = (
    PROJECT_ROOT
    / "outputs"
    / "czechlynx"
    / "phase5"
    / "czechlynx_phase5_pair_eri_scores_internal.csv"
)
TABLE_DIR = PROJECT_ROOT / "outputs" / "czechlynx" / "phase5" / "tables"
FIGURE_DIR = PROJECT_ROOT / "outputs" / "czechlynx" / "phase5" / "figures"
POLICY_FRONTIER_CSV = TABLE_DIR / "czechlynx_phase5_policy_frontier.csv"
BASELINE_CSV = TABLE_DIR / "czechlynx_phase5_eri_vs_similarity_baselines.csv"

SIMILARITY_COLUMNS = ["megadescriptor_similarity", "resnet50_similarity"]


def fail(message: str) -> int:
    print(f"FAIL: {message}")
    return 1


def auc_from_scores(labels: pd.Series, scores: pd.Series) -> float | None:
    positives = labels == "same"
    n_pos = int(positives.sum())
    n_neg = int((~positives).sum())
    if n_pos == 0 or n_neg == 0:
        return None
    ranks = scores.rank(method="average")
    pos_rank_sum = float(ranks[positives].sum())
    return float((pos_rank_sum - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg))


def policy_masks(df: pd.DataFrame) -> dict[str, pd.Series]:
    return {
        "keep_all": pd.Series(True, index=df.index),
        "strict_high_quality_evidence": (
            (df["pair_pattern_min"] == "high")
            & (df["pair_side_evidence_min"] == "high")
            & (df["pair_side_comparable"] == "yes")
            & (~df["pair_blur_max"].isin(["moderate", "severe"]))
            & (~df["pair_occlusion_max"].isin(["moderate", "severe"]))
            & (df["pair_any_silhouette"] == "no")
        ),
        "remove_severe_blur": df["pair_blur_max"] != "severe",
        "remove_low_none_pattern": ~df["pair_pattern_min"].isin(["low", "none"]),
        "remove_side_not_comparable": df["pair_side_comparable"] == "yes",
        "visual_only_eri_high": df["visual_only_eri_band"] == "high",
        "visual_only_eri_high_medium": df["visual_only_eri_band"].isin(["high", "medium"]),
        "hybrid_eri_high": df["hybrid_eri_band"] == "high",
        "hybrid_eri_high_medium": df["hybrid_eri_band"].isin(["high", "medium"]),
    }


def metric_row(
    df: pd.DataFrame,
    retained: pd.DataFrame,
    policy: str,
    policy_family: str,
    similarity_col: str,
    keep_all_auc: float | None,
    keep_all_gap: float,
    risk_threshold: float,
) -> dict[str, object]:
    same = retained[retained["pair_type"] == "same"]
    different = retained[retained["pair_type"] == "different"]
    same_mean = float(same[similarity_col].mean()) if len(same) else math.nan
    different_mean = float(different[similarity_col].mean()) if len(different) else math.nan
    gap = same_mean - different_mean
    auc = auc_from_scores(retained["pair_type"], retained[similarity_col])
    false_match_proxy = int(
        ((retained["pair_type"] == "different") & (retained[similarity_col] >= risk_threshold)).sum()
    )
    total_false_match_proxy = int(
        ((df["pair_type"] == "different") & (df[similarity_col] >= risk_threshold)).sum()
    )
    removed_rate = 1.0 - (len(retained) / len(df))
    return {
        "policy": policy,
        "policy_family": policy_family,
        "similarity_model": similarity_col.replace("_similarity", ""),
        "retained_pair_count": int(len(retained)),
        "removed_pair_count": int(len(df) - len(retained)),
        "retention_rate": float(len(retained) / len(df)),
        "removed_rate": float(removed_rate),
        "n_same_retained": int(len(same)),
        "n_different_retained": int(len(different)),
        "same_mean": same_mean,
        "different_mean": different_mean,
        "separation_gap": gap,
        "roc_auc": auc,
        "auc_gain_vs_keep_all": None if auc is None or keep_all_auc is None else auc - keep_all_auc,
        "separation_gap_gain_vs_keep_all": gap - keep_all_gap,
        "false_match_risk_proxy_count": false_match_proxy,
        "false_match_risk_proxy_reduction": total_false_match_proxy - false_match_proxy,
        "risk_proxy_reduction_rate": (
            None
            if total_false_match_proxy == 0
            else (total_false_match_proxy - false_match_proxy) / total_false_match_proxy
        ),
        "auc_gain_per_removed_rate": (
            None
            if auc is None or keep_all_auc is None or removed_rate == 0
            else (auc - keep_all_auc) / removed_rate
        ),
        "gap_gain_per_removed_rate": None if removed_rate == 0 else (gap - keep_all_gap) / removed_rate,
        "sparse_policy_caveat": "yes" if len(same) < 20 or len(different) < 20 else "no",
    }


def build_policy_frontier(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    masks = policy_masks(df)
    for similarity_col in SIMILARITY_COLUMNS:
        keep_all = df.copy()
        keep_same = keep_all[keep_all["pair_type"] == "same"]
        keep_diff = keep_all[keep_all["pair_type"] == "different"]
        keep_all_gap = float(keep_same[similarity_col].mean() - keep_diff[similarity_col].mean())
        keep_all_auc = auc_from_scores(keep_all["pair_type"], keep_all[similarity_col])
        risk_threshold = float(df[similarity_col].quantile(0.90))
        for policy, mask in masks.items():
            family = (
                "eri_retention"
                if "eri" in policy
                else "simple_visual_policy"
                if policy != "keep_all"
                else "baseline"
            )
            retained = df[mask].copy()
            rows.append(
                metric_row(
                    df,
                    retained,
                    policy,
                    family,
                    similarity_col,
                    keep_all_auc,
                    keep_all_gap,
                    risk_threshold,
                )
            )
    return pd.DataFrame(rows)


def build_raw_similarity_baselines(df: pd.DataFrame, frontier: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    targets = (
        frontier[
            (frontier["similarity_model"] == "megadescriptor")
            & (frontier["policy"].isin(["visual_only_eri_high", "visual_only_eri_high_medium", "hybrid_eri_high", "hybrid_eri_high_medium"]))
        ][["policy", "retained_pair_count"]]
        .drop_duplicates()
        .sort_values(["retained_pair_count", "policy"])
    )
    target_counts = [(row.policy, int(row.retained_pair_count)) for row in targets.itertuples()]
    for raw_col in SIMILARITY_COLUMNS:
        model_name = raw_col.replace("_similarity", "")
        keep_all_auc = auc_from_scores(df["pair_type"], df[raw_col])
        keep_same = df[df["pair_type"] == "same"]
        keep_diff = df[df["pair_type"] == "different"]
        keep_gap = float(keep_same[raw_col].mean() - keep_diff[raw_col].mean())
        risk_threshold = float(df[raw_col].quantile(0.90))
        for matched_policy, count in target_counts:
            if count <= 0:
                continue
            retained = df.sort_values(raw_col, ascending=False).head(count).copy()
            rows.append(
                metric_row(
                    df,
                    retained,
                    f"raw_{model_name}_ranking_matched_to_{matched_policy}",
                    "raw_similarity_ranking",
                    raw_col,
                    keep_all_auc,
                    keep_gap,
                    risk_threshold,
                )
            )
        for rate in [0.25, 0.50, 0.75]:
            count = max(1, int(round(len(df) * rate)))
            retained = df.sort_values(raw_col, ascending=False).head(count).copy()
            rows.append(
                metric_row(
                    df,
                    retained,
                    f"raw_{model_name}_ranking_top_{int(rate * 100)}pct",
                    "raw_similarity_ranking",
                    raw_col,
                    keep_all_auc,
                    keep_gap,
                    risk_threshold,
                )
            )
    return pd.DataFrame(rows)


def write_figures(frontier: pd.DataFrame) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception as exc:  # noqa: BLE001
        print(f"WARNING: matplotlib unavailable; skipping figures: {exc}")
        return

    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    for model in ["megadescriptor", "resnet50"]:
        subset = frontier[frontier["similarity_model"] == model].copy()
        fig, ax = plt.subplots(figsize=(8, 5))
        colors = {
            "baseline": "black",
            "simple_visual_policy": "tab:blue",
            "eri_retention": "tab:green",
        }
        for family, fam_df in subset.groupby("policy_family"):
            ax.scatter(
                fam_df["retention_rate"],
                fam_df["roc_auc"],
                label=family,
                color=colors.get(family, "gray"),
            )
            for row in fam_df.itertuples():
                ax.annotate(row.policy, (row.retention_rate, row.roc_auc), fontsize=6)
        ax.axhline(0.5, color="gray", linewidth=0.8)
        ax.set_xlabel("Retention rate")
        ax.set_ylabel("ROC-AUC")
        ax.set_title(f"Phase 5 reliability-retention frontier ({model})")
        ax.legend()
        plt.tight_layout()
        plt.savefig(FIGURE_DIR / f"phase5_reliability_retention_frontier_{model}.png", dpi=200)
        plt.close()


def main() -> int:
    if not SCORES_CSV.exists():
        return fail(f"ERI score file not found: {SCORES_CSV}")
    df = pd.read_csv(SCORES_CSV)
    required = {
        "pair_type",
        "pair_pattern_min",
        "pair_side_evidence_min",
        "pair_side_comparable",
        "pair_blur_max",
        "pair_occlusion_max",
        "pair_any_silhouette",
        "visual_only_eri_band",
        "hybrid_eri_band",
        *SIMILARITY_COLUMNS,
    }
    missing = sorted(required - set(df.columns))
    if missing:
        return fail("score file missing required column(s): " + ", ".join(missing))
    for col in SIMILARITY_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="raise")

    frontier = build_policy_frontier(df)
    baselines = build_raw_similarity_baselines(df, frontier)

    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    frontier.to_csv(POLICY_FRONTIER_CSV, index=False)
    baselines.to_csv(BASELINE_CSV, index=False)
    write_figures(frontier)

    print("CzechLynx Phase 5 ERI-ReID policy frontier")
    print(f"Input rows: {len(df)}")
    print(f"Policy frontier CSV: {POLICY_FRONTIER_CSV}")
    print(f"Baseline comparison CSV: {BASELINE_CSV}")
    print(f"Policy rows: {len(frontier)}")
    print(f"Baseline rows: {len(baselines)}")
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
