#!/usr/bin/env python3
"""Evaluate descriptor-supported staged PF-ERI risk-coverage baselines."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_CSV = PROJECT_ROOT / "outputs/czechlynx/phase7a/visual_only_pf_eri/phase7a_visual_only_pf_eri_pair_scores.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase7a/descriptor_supported_pf_eri"
FIGURE_DIR = OUTPUT_DIR / "figures"

PAIR_SCORES_CSV = OUTPUT_DIR / "phase7a_descriptor_supported_pair_scores.csv"
SEPARATION_CSV = OUTPUT_DIR / "phase7a_descriptor_separation_summary.csv"
RISK_COVERAGE_CSV = OUTPUT_DIR / "phase7a_descriptor_risk_coverage_thresholds.csv"
COMPARISON_CSV = OUTPUT_DIR / "phase7a_visual_gate_vs_descriptor_only_comparison.csv"
HIGH_DESC_LOW_VISUAL_CSV = OUTPUT_DIR / "phase7a_high_descriptor_low_visual_cases.csv"

DESCRIPTORS = {
    "resnet50": "resnet50_similarity",
    "megadescriptor": "megadescriptor_similarity",
}

SOURCE_DESCRIPTOR_COLUMNS = {
    "resnet50": "resnet50_similarity_reference_only",
    "megadescriptor": "megadescriptor_similarity_reference_only",
}

VISUAL_BANDS = ["high", "medium", "low", "unusable"]
VALID_LABELS = {"yes", "no"}
VALID_BANDS = set(VISUAL_BANDS)
THRESHOLD_QUANTILES = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 0.99]

REQUIRED_COLUMNS = [
    "pair_id",
    "same_identity",
    "pair_modeling_eligible",
    "visual_pf_eri_weighted",
    "visual_pf_eri_min_rule",
    "visual_pf_eri_band",
    "pair_side_compatible",
    "pair_primary_limiting_factor_combined",
    "primary_limiting_factor_for_score",
    "resnet50_similarity_reference_only",
    "megadescriptor_similarity_reference_only",
]


def clean_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.lower()


def cohen_d(positive: pd.Series, negative: pd.Series) -> float:
    n_pos = len(positive)
    n_neg = len(negative)
    if n_pos < 2 or n_neg < 2:
        return math.nan
    var_pos = positive.var(ddof=1)
    var_neg = negative.var(ddof=1)
    pooled = ((n_pos - 1) * var_pos + (n_neg - 1) * var_neg) / (n_pos + n_neg - 2)
    if pooled <= 0:
        return math.nan
    return float((positive.mean() - negative.mean()) / math.sqrt(pooled))


def rank_auc(labels: pd.Series, scores: pd.Series) -> float:
    y = labels.map({"yes": 1, "no": 0}).astype(int)
    n_pos = int(y.sum())
    n_neg = int((1 - y).sum())
    if n_pos == 0 or n_neg == 0:
        return math.nan
    ranks = scores.rank(method="average")
    rank_sum_pos = float(ranks[y == 1].sum())
    auc = (rank_sum_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)
    return float(auc)


def interpretation_for_separation(auc: float, d_value: float) -> str:
    if math.isnan(auc):
        return "insufficient same/different pairs for ranking interpretation"
    if auc >= 0.80:
        strength = "strong"
    elif auc >= 0.70:
        strength = "moderate"
    elif auc >= 0.60:
        strength = "weak_to_moderate"
    elif auc >= 0.55:
        strength = "weak"
    else:
        strength = "minimal"
    return f"{strength} descriptor ranking support; Cohen_d={d_value:.3f}"


def visual_gate_mask(df: pd.DataFrame, gate: str) -> pd.Series:
    if gate == "descriptor_only_all_visual_bands":
        return pd.Series(True, index=df.index)
    if gate == "high_visual_only":
        return df["visual_band"] == "high"
    if gate == "medium_or_higher_visual":
        return df["visual_band"].isin(["high", "medium"])
    if gate == "low_or_higher_visual":
        return df["visual_band"].isin(["high", "medium", "low"])
    if gate == "stratum_high":
        return df["visual_band"] == "high"
    if gate == "stratum_medium":
        return df["visual_band"] == "medium"
    if gate == "stratum_low":
        return df["visual_band"] == "low"
    if gate == "stratum_unusable":
        return df["visual_band"] == "unusable"
    raise ValueError(f"unknown visual gate: {gate}")


def gate_interpretation(gate: str) -> str:
    return {
        "descriptor_only_all_visual_bands": "descriptor thresholding without visual evidence gate",
        "high_visual_only": "descriptor support after strict high visual PF-ERI gate",
        "medium_or_higher_visual": "descriptor support after high/medium visual PF-ERI gate",
        "low_or_higher_visual": "descriptor support after excluding unusable visual evidence",
        "stratum_high": "within high visual PF-ERI stratum",
        "stratum_medium": "within medium visual PF-ERI stratum",
        "stratum_low": "within low visual PF-ERI stratum",
        "stratum_unusable": "within unusable visual PF-ERI stratum",
    }[gate]


def threshold_grid(values: pd.Series) -> list[float]:
    thresholds = sorted({round(float(values.quantile(q)), 6) for q in THRESHOLD_QUANTILES})
    return thresholds


def risk_coverage_rows(df: pd.DataFrame) -> pd.DataFrame:
    total_pairs = len(df)
    total_same = int((df["same_identity"] == "yes").sum())
    total_different = int((df["same_identity"] == "no").sum())
    rows: list[dict[str, object]] = []
    gates = [
        "descriptor_only_all_visual_bands",
        "high_visual_only",
        "medium_or_higher_visual",
        "low_or_higher_visual",
        "stratum_high",
        "stratum_medium",
        "stratum_low",
        "stratum_unusable",
    ]
    for descriptor, column in DESCRIPTORS.items():
        for threshold in threshold_grid(df[column]):
            descriptor_mask = df[column] >= threshold
            for gate in gates:
                gate_mask = visual_gate_mask(df, gate)
                selected = df[descriptor_mask & gate_mask]
                selected_count = len(selected)
                selected_same = int((selected["same_identity"] == "yes").sum())
                selected_different = int((selected["same_identity"] == "no").sum())
                rows.append(
                    {
                        "descriptor": descriptor,
                        "threshold": threshold,
                        "visual_gate": gate,
                        "selected_count": selected_count,
                        "coverage": selected_count / total_pairs if total_pairs else math.nan,
                        "selected_same_count": selected_same,
                        "selected_different_count": selected_different,
                        "selected_same_proportion": selected_same / selected_count if selected_count else math.nan,
                        "false_support_rate": selected_different / selected_count if selected_count else math.nan,
                        "same_accept_rate": selected_same / total_same if total_same else math.nan,
                        "different_accept_rate": selected_different / total_different if total_different else math.nan,
                        "interpretation": gate_interpretation(gate),
                    }
                )
    return pd.DataFrame(rows)


def separation_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    subsets = [("overall", df)] + [(f"visual_band_{band}", df[df["visual_band"] == band]) for band in VISUAL_BANDS]
    for descriptor, column in DESCRIPTORS.items():
        for subset_name, subset in subsets:
            same = subset[subset["same_identity"] == "yes"][column]
            different = subset[subset["same_identity"] == "no"][column]
            d_value = cohen_d(same, different)
            auc = rank_auc(subset["same_identity"], subset[column])
            rows.append(
                {
                    "descriptor": descriptor,
                    "subset": subset_name,
                    "pair_count": len(subset),
                    "same_count": len(same),
                    "different_count": len(different),
                    "mean_same_similarity": same.mean() if len(same) else math.nan,
                    "mean_different_similarity": different.mean() if len(different) else math.nan,
                    "same_minus_different": same.mean() - different.mean() if len(same) and len(different) else math.nan,
                    "approximate_cohens_d": d_value,
                    "auc_rank_based": auc,
                    "interpretation": interpretation_for_separation(auc, d_value),
                }
            )
    return pd.DataFrame(rows)


def comparison_rows(risk_df: pd.DataFrame) -> pd.DataFrame:
    comparison_gates = [
        ("descriptor_only_thresholding", "descriptor_only_all_visual_bands"),
        ("high_visual_gate_then_descriptor", "high_visual_only"),
        ("medium_or_higher_visual_gate_then_descriptor", "medium_or_higher_visual"),
        ("low_or_higher_visual_gate_then_descriptor", "low_or_higher_visual"),
        ("unusable_included_descriptor_thresholding", "descriptor_only_all_visual_bands"),
    ]
    target_coverages = [0.05, 0.10, 0.20, 0.30, 0.50]
    rows: list[dict[str, object]] = []
    for descriptor in DESCRIPTORS:
        descriptor_df = risk_df[risk_df["descriptor"] == descriptor]
        for strategy, gate in comparison_gates:
            gate_df = descriptor_df[descriptor_df["visual_gate"] == gate].copy()
            if gate_df.empty:
                continue
            for target in target_coverages:
                gate_df["coverage_gap"] = (gate_df["coverage"] - target).abs()
                best = gate_df.sort_values(["coverage_gap", "false_support_rate", "threshold"]).iloc[0]
                rows.append(
                    {
                        "descriptor": descriptor,
                        "strategy": strategy,
                        "target_coverage": target,
                        "threshold": best["threshold"],
                        "selected_count": int(best["selected_count"]),
                        "coverage": best["coverage"],
                        "selected_same_count": int(best["selected_same_count"]),
                        "selected_different_count": int(best["selected_different_count"]),
                        "selected_same_proportion": best["selected_same_proportion"],
                        "false_support_rate": best["false_support_rate"],
                        "same_accept_rate": best["same_accept_rate"],
                        "different_accept_rate": best["different_accept_rate"],
                        "interpretation": gate_interpretation(gate),
                    }
                )
    return pd.DataFrame(rows)


def high_descriptor_low_visual_cases(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    low_visual = df["visual_band"].isin(["low", "unusable"])
    for descriptor, column in DESCRIPTORS.items():
        top_decile_threshold = float(df[column].quantile(0.90))
        flagged = df[low_visual & (df[column] >= top_decile_threshold)].copy()
        flagged["descriptor"] = descriptor
        flagged["descriptor_top_decile_threshold"] = top_decile_threshold
        flagged["flagged_descriptor_similarity"] = flagged[column]
        flagged["interpretation"] = (
            "high descriptor similarity with low/unusable visual PF-ERI; treat as staged review failure mode, not automatic support"
        )
        rows.append(
            flagged[
                [
                    "descriptor",
                    "pair_id",
                    "same_identity",
                    "visual_pf_eri_weighted",
                    "visual_band",
                    "resnet50_similarity",
                    "megadescriptor_similarity",
                    "flagged_descriptor_similarity",
                    "descriptor_top_decile_threshold",
                    "pair_side_compatible",
                    "pair_primary_limiting_factor_combined",
                    "primary_limiting_factor_for_score",
                    "interpretation",
                ]
            ]
        )
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def add_staged_flags(df: pd.DataFrame) -> pd.DataFrame:
    output = df.copy()
    output["visual_gate_high"] = output["visual_band"].eq("high").map({True: "yes", False: "no"})
    output["visual_gate_medium_or_higher"] = output["visual_band"].isin(["high", "medium"]).map({True: "yes", False: "no"})
    output["visual_gate_low_or_higher"] = output["visual_band"].isin(["high", "medium", "low"]).map({True: "yes", False: "no"})
    for descriptor, column in DESCRIPTORS.items():
        q90 = float(output[column].quantile(0.90))
        q95 = float(output[column].quantile(0.95))
        output[f"{descriptor}_top_decile_support"] = (output[column] >= q90).map({True: "yes", False: "no"})
        output[f"{descriptor}_top_5pct_support"] = (output[column] >= q95).map({True: "yes", False: "no"})
        output[f"{descriptor}_high_descriptor_low_visual_flag"] = (
            output[column].ge(q90) & output["visual_band"].isin(["low", "unusable"])
        ).map({True: "yes", False: "no"})
    output["any_high_descriptor_low_visual_flag"] = (
        output["resnet50_high_descriptor_low_visual_flag"].eq("yes")
        | output["megadescriptor_high_descriptor_low_visual_flag"].eq("yes")
    ).map({True: "yes", False: "no"})
    return output


def prepare_input(input_csv: Path) -> pd.DataFrame:
    df = pd.read_csv(input_csv)
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError("input missing required column(s): " + ", ".join(missing))
    df["same_identity"] = clean_series(df["same_identity"])
    df["pair_modeling_eligible"] = clean_series(df["pair_modeling_eligible"])
    df["visual_band"] = clean_series(df["visual_pf_eri_band"])
    df = df[df["pair_modeling_eligible"].eq("yes")].copy()
    if not set(df["same_identity"]).issubset(VALID_LABELS):
        raise ValueError("same_identity must contain only yes/no values")
    if not set(df["visual_band"]).issubset(VALID_BANDS):
        raise ValueError("visual_pf_eri_band contains invalid values")
    for descriptor, output_column in DESCRIPTORS.items():
        source_column = SOURCE_DESCRIPTOR_COLUMNS[descriptor]
        df[output_column] = pd.to_numeric(df[source_column], errors="raise")
    df["visual_pf_eri_weighted"] = pd.to_numeric(df["visual_pf_eri_weighted"], errors="raise")
    df["visual_pf_eri_min_rule"] = pd.to_numeric(df["visual_pf_eri_min_rule"], errors="raise")
    return df


def save_figures(df: pd.DataFrame, separation_df: pd.DataFrame, risk_df: pd.DataFrame, comparison_df: pd.DataFrame) -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    for descriptor, column in DESCRIPTORS.items():
        data = [
            df[df["same_identity"] == "yes"][column],
            df[df["same_identity"] == "no"][column],
        ]
        plt.figure(figsize=(7, 5))
        plt.boxplot(data, tick_labels=["same", "different"], showmeans=True)
        plt.ylabel(f"{descriptor} similarity")
        plt.title(f"{descriptor} same vs different similarity")
        plt.tight_layout()
        plt.savefig(FIGURE_DIR / f"{descriptor}_same_vs_different_boxplot.png", dpi=160)
        plt.close()

    plt.figure(figsize=(8, 5))
    for descriptor in DESCRIPTORS:
        subset = separation_df[(separation_df["descriptor"] == descriptor) & separation_df["subset"].str.startswith("visual_band_")]
        plt.plot(
            subset["subset"].str.replace("visual_band_", "", regex=False),
            subset["auc_rank_based"],
            marker="o",
            label=descriptor,
        )
    plt.ylim(0.45, 1.0)
    plt.xlabel("Visual PF-ERI band")
    plt.ylabel("Rank-based AUC")
    plt.title("Descriptor separation by visual evidence stratum")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "descriptor_auc_by_visual_band.png", dpi=160)
    plt.close()

    plt.figure(figsize=(8, 5))
    for descriptor in DESCRIPTORS:
        for gate, style in [
            ("descriptor_only_all_visual_bands", "-"),
            ("high_visual_only", "--"),
            ("medium_or_higher_visual", ":"),
        ]:
            subset = risk_df[(risk_df["descriptor"] == descriptor) & (risk_df["visual_gate"] == gate)]
            plt.plot(subset["coverage"], subset["false_support_rate"], linestyle=style, marker="o", markersize=3, label=f"{descriptor}: {gate}")
    plt.xlabel("Coverage")
    plt.ylabel("False-support rate among selected pairs")
    plt.title("Descriptor-supported staged risk-coverage baseline")
    plt.legend(fontsize=7)
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "descriptor_risk_coverage_curves.png", dpi=160)
    plt.close()

    plot_subset = comparison_df[comparison_df["target_coverage"].isin([0.1, 0.2, 0.5])]
    labels = [f"{row.descriptor}\n{row.strategy}\n{row.target_coverage:.0%}" for row in plot_subset.itertuples()]
    plt.figure(figsize=(12, 5))
    plt.bar(range(len(plot_subset)), plot_subset["false_support_rate"], color="#4C78A8")
    plt.xticks(range(len(plot_subset)), labels, rotation=75, ha="right", fontsize=7)
    plt.ylabel("False-support rate")
    plt.title("Descriptor-only vs visual-gated threshold comparison")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "visual_gate_vs_descriptor_only_comparison.png", dpi=160)
    plt.close()

    plt.figure(figsize=(8, 5))
    colors = df["same_identity"].map({"yes": "#4C78A8", "no": "#E15759"})
    plt.scatter(df["visual_pf_eri_weighted"], df["megadescriptor_similarity"], c=colors, s=12, alpha=0.55)
    plt.xlabel("Visual-only PF-ERI weighted score")
    plt.ylabel("MegaDescriptor similarity")
    plt.title("Visual score vs MegaDescriptor similarity by reference label")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "visual_score_vs_megadescriptor_by_label.png", dpi=160)
    plt.close()

    plt.figure(figsize=(8, 5))
    colors = df["any_high_descriptor_low_visual_flag"].map({"yes": "#E15759", "no": "#BAB0AC"})
    plt.scatter(df["visual_pf_eri_weighted"], df["resnet50_similarity"], c=colors, s=12, alpha=0.55, label="ResNet50")
    plt.scatter(df["visual_pf_eri_weighted"], df["megadescriptor_similarity"], c=colors, s=12, alpha=0.35, marker="x", label="MegaDescriptor")
    plt.xlabel("Visual-only PF-ERI weighted score")
    plt.ylabel("Descriptor similarity")
    plt.title("High-descriptor low-visual failure-mode flags")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "high_descriptor_low_visual_scatter.png", dpi=160)
    plt.close()


def build(input_csv: Path, output_dir: Path) -> dict[str, object]:
    df = prepare_input(input_csv)
    scored = add_staged_flags(df)
    risk_df = risk_coverage_rows(scored)
    separation_df = separation_summary(scored)
    comparison_df = comparison_rows(risk_df)
    failure_df = high_descriptor_low_visual_cases(scored)

    output_dir.mkdir(parents=True, exist_ok=True)
    pair_columns = [
        "pair_id",
        "same_identity",
        "visual_pf_eri_weighted",
        "visual_pf_eri_min_rule",
        "visual_band",
        "resnet50_similarity",
        "megadescriptor_similarity",
        "pair_side_compatible",
        "pair_primary_limiting_factor_combined",
        "primary_limiting_factor_for_score",
        "visual_gate_high",
        "visual_gate_medium_or_higher",
        "visual_gate_low_or_higher",
        "resnet50_top_decile_support",
        "resnet50_top_5pct_support",
        "resnet50_high_descriptor_low_visual_flag",
        "megadescriptor_top_decile_support",
        "megadescriptor_top_5pct_support",
        "megadescriptor_high_descriptor_low_visual_flag",
        "any_high_descriptor_low_visual_flag",
    ]
    scored[pair_columns].to_csv(PAIR_SCORES_CSV, index=False)
    separation_df.to_csv(SEPARATION_CSV, index=False)
    risk_df.to_csv(RISK_COVERAGE_CSV, index=False)
    comparison_df.to_csv(COMPARISON_CSV, index=False)
    failure_df.to_csv(HIGH_DESC_LOW_VISUAL_CSV, index=False)
    save_figures(scored, separation_df, risk_df, comparison_df)

    overall = separation_df[separation_df["subset"] == "overall"].set_index("descriptor")
    return {
        "eligible_pair_count": len(scored),
        "same_count": int((scored["same_identity"] == "yes").sum()),
        "different_count": int((scored["same_identity"] == "no").sum()),
        "resnet50_overall_auc": round(float(overall.loc["resnet50", "auc_rank_based"]), 4),
        "megadescriptor_overall_auc": round(float(overall.loc["megadescriptor", "auc_rank_based"]), 4),
        "high_descriptor_low_visual_case_rows": len(failure_df),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-csv", type=Path, default=INPUT_CSV)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = build(args.input_csv.resolve(), args.output_dir.resolve())
    print("Phase 7A descriptor-supported PF-ERI risk-coverage baseline complete")
    for key, value in summary.items():
        print(f"{key}: {value}")
    print(f"output_dir: {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
