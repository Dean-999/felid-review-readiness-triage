#!/usr/bin/env python3
"""Calibrate descriptive ERI risk proxies for Phase 6."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PAIR_SCORES = ROOT / "outputs/czechlynx/phase5/czechlynx_phase5_pair_eri_scores_internal.csv"
OUT_TABLE_DIR = ROOT / "outputs/czechlynx/phase6/tables"
OUT_FIG_DIR = ROOT / "outputs/czechlynx/phase6/figures"
QC_DIR = ROOT / "outputs/czechlynx/qc"
BAND_RISK_OUT = OUT_TABLE_DIR / "phase6_calibrated_eri_risk_by_band.csv"
COVERAGE_OUT = OUT_TABLE_DIR / "phase6_coverage_at_risk_tolerance.csv"
FIGURE_OUT = OUT_FIG_DIR / "phase6_eri_reliability_diagram.png"
REPORT_OUT = QC_DIR / "phase6_calibrated_eri_risk_report.txt"

SCORE_COLUMNS = {
    "visual_only_eri": "visual_only_eri",
    "hybrid_eri": "hybrid_eri",
}
SIMILARITY_COLUMNS = {
    "megadescriptor": "megadescriptor_similarity",
    "resnet50": "resnet50_similarity",
}
RISK_TOLERANCES = [0.02, 0.05, 0.10, 0.15, 0.20]
SENSITIVE_VALUE_PATTERNS = ("working_individual_id", "lynx_", "/Users/", "data/interim", "review_image_path")


def band_from_score(value: float) -> str:
    if value >= 75:
        return "high"
    if value >= 55:
        return "medium"
    if value >= 35:
        return "low"
    return "unusable"


def load_pairs() -> pd.DataFrame:
    pairs = pd.read_csv(PAIR_SCORES)
    required = {"pair_type", *SCORE_COLUMNS.values(), *SIMILARITY_COLUMNS.values()}
    missing = sorted(required - set(pairs.columns))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    return pairs


def risk_target(pairs: pd.DataFrame, sim_col: str) -> pd.Series:
    threshold = float(pairs[sim_col].quantile(0.90))
    return pairs["pair_type"].eq("different") & pairs[sim_col].ge(threshold)


def band_risk_table(pairs: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for score_name, score_col in SCORE_COLUMNS.items():
        bands = pairs[score_col].map(band_from_score)
        score = pairs[score_col].astype(float)
        for sim_name, sim_col in SIMILARITY_COLUMNS.items():
            target = risk_target(pairs, sim_col)
            threshold = float(pairs[sim_col].quantile(0.90))
            for band in ["high", "medium", "low", "unusable", "all"]:
                mask = pd.Series(True, index=pairs.index) if band == "all" else bands.eq(band)
                subset = pairs[mask]
                target_subset = target[mask]
                diff_mask = subset["pair_type"].eq("different")
                n = int(len(subset))
                false_count = int(target_subset.sum())
                rows.append(
                    {
                        "score_name": score_name,
                        "band": band,
                        "similarity_model": sim_name,
                        "pair_count": n,
                        "same_pair_count": int(subset["pair_type"].eq("same").sum()),
                        "different_pair_count": int(diff_mask.sum()),
                        "mean_eri_score": float(score[mask].mean()) if n else np.nan,
                        "high_similarity_threshold_90th_percentile": threshold,
                        "high_similarity_different_pair_count": false_count,
                        "risk_proxy_rate_among_pairs": float(false_count / n) if n else np.nan,
                        "risk_proxy_rate_among_different": float(false_count / diff_mask.sum())
                        if diff_mask.sum()
                        else np.nan,
                        "predicted_risk_proxy_mean": float((1.0 - score[mask] / 100.0).clip(0, 1).mean())
                        if n
                        else np.nan,
                        "caveat": "sparse_bin" if n < 100 else "",
                    }
                )
    return pd.DataFrame(rows)


def coverage_table(pairs: pd.DataFrame) -> pd.DataFrame:
    policies = {
        "keep_high": {"high"},
        "keep_high_medium": {"high", "medium"},
        "keep_high_medium_low": {"high", "medium", "low"},
        "keep_all": {"high", "medium", "low", "unusable"},
    }
    rows = []
    for score_name, score_col in SCORE_COLUMNS.items():
        bands = pairs[score_col].map(band_from_score)
        for sim_name, sim_col in SIMILARITY_COLUMNS.items():
            target = risk_target(pairs, sim_col)
            candidates = []
            for policy_name, keep_bands in policies.items():
                mask = bands.isin(keep_bands)
                n = int(mask.sum())
                false_count = int(target[mask].sum())
                risk = float(false_count / n) if n else np.nan
                risk_load = float(false_count / len(pairs))
                candidates.append(
                    {
                        "policy": policy_name,
                        "retained_pair_count": n,
                        "coverage": float(n / len(pairs)),
                        "risk_proxy_rate_among_pairs": risk,
                        "risk_proxy_load_rate_original_pairs": risk_load,
                        "high_similarity_different_pair_count": false_count,
                    }
                )
            candidate_df = pd.DataFrame(candidates)
            for tolerance in RISK_TOLERANCES:
                feasible = candidate_df[candidate_df["risk_proxy_load_rate_original_pairs"].le(tolerance)].copy()
                if feasible.empty:
                    choice = candidate_df.sort_values(
                        ["risk_proxy_load_rate_original_pairs", "coverage"], ascending=[True, False]
                    ).iloc[0]
                    met = False
                else:
                    choice = feasible.sort_values(
                        ["coverage", "risk_proxy_load_rate_original_pairs"], ascending=[False, True]
                    ).iloc[0]
                    met = True
                rows.append(
                    {
                        "score_name": score_name,
                        "similarity_model": sim_name,
                        "risk_tolerance": tolerance,
                        "selected_policy": choice["policy"],
                        "tolerance_met": bool(met),
                        "retained_pair_count": int(choice["retained_pair_count"]),
                        "coverage": float(choice["coverage"]),
                        "risk_proxy_rate_among_pairs": float(choice["risk_proxy_rate_among_pairs"]),
                        "risk_proxy_load_rate_original_pairs": float(choice["risk_proxy_load_rate_original_pairs"]),
                        "high_similarity_different_pair_count": int(choice["high_similarity_different_pair_count"]),
                    }
                )
    return pd.DataFrame(rows)


def calibration_diagnostics(pairs: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    rows = []
    caveats = []
    for score_name, score_col in SCORE_COLUMNS.items():
        score = pairs[score_col].astype(float)
        predicted_risk = (1.0 - score / 100.0).clip(0, 1)
        bins = pd.cut(score, bins=np.linspace(0, 100, 11), include_lowest=True)
        for sim_name, sim_col in SIMILARITY_COLUMNS.items():
            target = risk_target(pairs, sim_col).astype(int)
            brier = float(np.mean((predicted_risk - target) ** 2))
            ece_parts = []
            sparse_bins = 0
            for _, idx in pairs.groupby(bins, observed=False).groups.items():
                idx = list(idx)
                if len(idx) == 0:
                    continue
                if len(idx) < 100:
                    sparse_bins += 1
                empirical = float(target.iloc[idx].mean())
                predicted = float(predicted_risk.iloc[idx].mean())
                ece_parts.append((len(idx) / len(pairs)) * abs(empirical - predicted))
            if sparse_bins:
                caveats.append(f"{score_name}/{sim_name}: {sparse_bins} sparse calibration bins")
            rows.append(
                {
                    "score_name": score_name,
                    "similarity_model": sim_name,
                    "descriptive_brier_score": brier,
                    "descriptive_ece": float(np.sum(ece_parts)),
                    "sparse_bin_count": sparse_bins,
                    "caveat": "predicted risk uses 1 - ERI/100 as a descriptive proxy, not a learned probability",
                }
            )
    return pd.DataFrame(rows), caveats


def write_figure(pairs: pd.DataFrame) -> str:
    try:
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover - depends on local env
        return f"Figure skipped: matplotlib unavailable ({exc})"

    sim_name = "megadescriptor"
    sim_col = SIMILARITY_COLUMNS[sim_name]
    target = risk_target(pairs, sim_col).astype(int)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for ax, (score_name, score_col) in zip(axes, SCORE_COLUMNS.items()):
        score = pairs[score_col].astype(float)
        predicted_risk = (1.0 - score / 100.0).clip(0, 1)
        bins = pd.cut(score, bins=np.linspace(0, 100, 11), include_lowest=True)
        plot_rows = []
        for _, idx in pairs.groupby(bins, observed=False).groups.items():
            idx = list(idx)
            if not idx:
                continue
            plot_rows.append(
                {
                    "mean_predicted_risk": float(predicted_risk.iloc[idx].mean()),
                    "empirical_risk": float(target.iloc[idx].mean()),
                    "pair_count": len(idx),
                }
            )
        plot_df = pd.DataFrame(plot_rows)
        ax.plot(plot_df["mean_predicted_risk"], plot_df["empirical_risk"], marker="o")
        ax.plot([0, 1], [0, 1], linestyle="--", color="0.5", linewidth=1)
        ax.set_title(score_name)
        ax.set_xlabel("Descriptive predicted risk proxy")
        ax.grid(True, alpha=0.3)
    axes[0].set_ylabel("Empirical high-similarity different-pair rate")
    fig.suptitle("Phase 6 ERI risk proxy calibration (MegaDescriptor)")
    fig.tight_layout()
    fig.savefig(FIGURE_OUT, dpi=180)
    plt.close(fig)
    return "Figure written"


def audit_output(*dfs: pd.DataFrame) -> list[str]:
    text = "\n".join(df.astype(str).to_string(index=False) for df in dfs)
    return [f"sensitive_value_pattern_present={pattern}" for pattern in SENSITIVE_VALUE_PATTERNS if pattern in text]


def main() -> None:
    OUT_TABLE_DIR.mkdir(parents=True, exist_ok=True)
    OUT_FIG_DIR.mkdir(parents=True, exist_ok=True)
    QC_DIR.mkdir(parents=True, exist_ok=True)
    pairs = load_pairs()
    band_risk = band_risk_table(pairs)
    coverage = coverage_table(pairs)
    diagnostics, caveats = calibration_diagnostics(pairs)
    figure_status = write_figure(pairs)
    issues = audit_output(band_risk, coverage, diagnostics)

    band_risk.to_csv(BAND_RISK_OUT, index=False)
    coverage.to_csv(COVERAGE_OUT, index=False)

    status = "PASS" if not issues else "FAIL"
    REPORT_OUT.write_text(
        "\n".join(
            [
                "Phase 6 calibrated ERI risk audit",
                f"Status: {status}",
                "Risk target: different pair with similarity at or above model-specific 90th percentile.",
                "Risk-tolerance selection uses high-similarity different-pair load divided by the original pair count; retained-pair risk is reported separately.",
                "Scores calibrated: visual_only_eri and hybrid_eri.",
                "Probability caveat: values are empirical CzechLynx risk proxies, not deployment probabilities.",
                "Diagnostics:",
                diagnostics.to_string(index=False),
                f"Figure status: {figure_status}",
                "Sparse-bin caveats:",
                *(caveats if caveats else ["None"]),
                "Audit issues:",
                *(issues if issues else ["None"]),
                "",
            ]
        )
    )
    if issues:
        raise SystemExit("Phase 6 calibrated ERI risk audit failed: " + "; ".join(issues))


if __name__ == "__main__":
    main()
