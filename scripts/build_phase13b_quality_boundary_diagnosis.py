#!/usr/bin/env python3
"""Diagnose when learned PF-ERI helps beyond learned quality control.

Phase 13 showed that learned PF-ERI is a clear upgrade over fixed PF-ERI but
mixed against a learned quality-control baseline. This script turns that mixed
result into a boundary diagnosis instead of treating it as a final negative.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE13_DIR = PROJECT_ROOT / "outputs/czechlynx/phase13/learned_candidate_utility"
TOP1 = PHASE13_DIR / "phase13_top1_selection_records.csv"
TRAINING_TABLE = PHASE13_DIR / "phase13_candidate_utility_training_table.csv"
RISK_COVERAGE = PHASE13_DIR / "phase13_risk_coverage_comparison.csv"
OUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase13/quality_boundary_diagnosis"

QUERY_OUTCOME = OUT_DIR / "phase13b_query_level_rescue_harm.csv"
FEATURE_CONTRAST = OUT_DIR / "phase13b_rescue_harm_feature_contrast.csv"
RISK_CONTRAST = OUT_DIR / "phase13b_risk_coverage_boundary_contrast.csv"
SUMMARY_MD = OUT_DIR / "phase13b_quality_boundary_diagnosis_summary.md"
BUILD_AUDIT = OUT_DIR / "phase13b_quality_boundary_diagnosis_build_audit.json"

COMPARISONS = [
    ("learned_pf_eri_full_logistic", "learned_quality_control_logistic", "pf_eri_full_vs_quality_control"),
    ("learned_pf_eri_interaction_logistic", "learned_quality_control_logistic", "pf_eri_interaction_vs_quality_control"),
    ("learned_pf_eri_monotonic_hgb", "learned_quality_control_logistic", "pf_eri_monotonic_vs_quality_control"),
    ("learned_pf_eri_full_logistic", "fixed_pf_eri_candidate_utility", "pf_eri_full_vs_fixed_pf_eri"),
]

FEATURES = [
    "descriptor_similarity_percentile",
    "margin_confidence_norm",
    "descriptor_disagreement_score",
    "image_quality_proxy_min",
    "visual_identity_evidence_min",
    "pair_reliability_score",
    "descriptor_evidence_conflict_score",
    "candidate_utility_rq_score",
    "descriptor_x_pair_reliability",
    "descriptor_x_conflict",
    "reliability_minus_conflict",
]


def yes_no_to_bool(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin({"yes", "true", "1"})


def safe_mean(values: pd.Series | np.ndarray | list[float]) -> float:
    series = pd.Series(values, dtype="float64").replace([np.inf, -np.inf], np.nan).dropna()
    return float(series.mean()) if len(series) else math.nan


def load_top1(path: Path) -> pd.DataFrame:
    top1 = pd.read_csv(path)
    for col in ["same_identity", "hard_negative_candidate", "gallery_positive_available"]:
        top1[col] = yes_no_to_bool(top1[col])
    return top1


def load_features(path: Path) -> pd.DataFrame:
    usecols = [
        "split_id",
        "descriptor",
        "query_image_id",
        "candidate_image_id",
        "same_identity",
        "hard_negative_candidate",
        "gallery_positive_available",
    ] + FEATURES
    features = pd.read_csv(path, usecols=usecols)
    for col in ["same_identity", "hard_negative_candidate", "gallery_positive_available"]:
        features[col] = yes_no_to_bool(features[col])
    return features


def attach_features(top1: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
    top1 = top1.drop(columns=[column for column in FEATURES if column in top1.columns])
    keep = ["split_id", "descriptor", "query_image_id", "candidate_image_id"] + FEATURES
    return top1.merge(
        features[keep],
        on=["split_id", "descriptor", "query_image_id", "candidate_image_id"],
        how="left",
        validate="many_to_one",
    )


def build_query_outcomes(top1: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for method_id, baseline_id, comparison_id in COMPARISONS:
        method = top1[top1["method_id"].eq(method_id)].copy()
        baseline = top1[top1["method_id"].eq(baseline_id)].copy()
        merged = baseline.merge(
            method,
            on=["split_id", "descriptor", "query_image_id"],
            suffixes=("_baseline", "_method"),
            validate="one_to_one",
        )
        merged["outcome_class"] = np.select(
            [
                (~merged["same_identity_baseline"]) & merged["same_identity_method"],
                merged["same_identity_baseline"] & (~merged["same_identity_method"]),
                merged["same_identity_baseline"] & merged["same_identity_method"],
            ],
            ["rescue", "harm", "both_true"],
            default="both_false",
        )
        for (split_id, descriptor), frame in merged.groupby(["split_id", "descriptor"]):
            rows.append(
                {
                    "comparison_id": comparison_id,
                    "method_id": method_id,
                    "baseline_method_id": baseline_id,
                    "split_id": int(split_id),
                    "descriptor": descriptor,
                    "query_count": int(len(frame)),
                    "baseline_true_top1_rate": float(frame["same_identity_baseline"].mean()),
                    "method_true_top1_rate": float(frame["same_identity_method"].mean()),
                    "net_true_top1_gain": float(frame["same_identity_method"].mean() - frame["same_identity_baseline"].mean()),
                    "rescue_count": int(frame["outcome_class"].eq("rescue").sum()),
                    "harm_count": int(frame["outcome_class"].eq("harm").sum()),
                    "both_true_count": int(frame["outcome_class"].eq("both_true").sum()),
                    "both_false_count": int(frame["outcome_class"].eq("both_false").sum()),
                    "baseline_hard_negative_top1_rate": float(frame["hard_negative_candidate_baseline"].mean()),
                    "method_hard_negative_top1_rate": float(frame["hard_negative_candidate_method"].mean()),
                    "hard_negative_top1_reduction": float(frame["hard_negative_candidate_baseline"].mean() - frame["hard_negative_candidate_method"].mean()),
                    "mean_method_score_when_rescue": safe_mean(frame.loc[frame["outcome_class"].eq("rescue"), "_score_method"]),
                    "mean_method_score_when_harm": safe_mean(frame.loc[frame["outcome_class"].eq("harm"), "_score_method"]),
                    "mean_baseline_score_when_rescue": safe_mean(frame.loc[frame["outcome_class"].eq("rescue"), "_score_baseline"]),
                    "mean_baseline_score_when_harm": safe_mean(frame.loc[frame["outcome_class"].eq("harm"), "_score_baseline"]),
                }
            )
    return pd.DataFrame(rows)


def build_feature_contrast(top1: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for method_id, baseline_id, comparison_id in COMPARISONS:
        method = top1[top1["method_id"].eq(method_id)].copy()
        baseline = top1[top1["method_id"].eq(baseline_id)].copy()
        merged = baseline.merge(
            method,
            on=["split_id", "descriptor", "query_image_id"],
            suffixes=("_baseline", "_method"),
            validate="one_to_one",
        )
        merged["outcome_class"] = np.select(
            [
                (~merged["same_identity_baseline"]) & merged["same_identity_method"],
                merged["same_identity_baseline"] & (~merged["same_identity_method"]),
                merged["same_identity_baseline"] & merged["same_identity_method"],
            ],
            ["rescue", "harm", "both_true"],
            default="both_false",
        )
        for descriptor, frame in merged.groupby("descriptor"):
            for feature in FEATURES:
                for side in ["method", "baseline"]:
                    col = f"{feature}_{side}"
                    rescue = frame.loc[frame["outcome_class"].eq("rescue"), col]
                    harm = frame.loc[frame["outcome_class"].eq("harm"), col]
                    both_false = frame.loc[frame["outcome_class"].eq("both_false"), col]
                    rows.append(
                        {
                            "comparison_id": comparison_id,
                            "method_id": method_id,
                            "baseline_method_id": baseline_id,
                            "descriptor": descriptor,
                            "selected_side": side,
                            "feature": feature,
                            "mean_rescue": safe_mean(rescue),
                            "mean_harm": safe_mean(harm),
                            "mean_both_false": safe_mean(both_false),
                            "rescue_minus_harm": safe_mean(rescue) - safe_mean(harm),
                            "rescue_count": int(rescue.notna().sum()),
                            "harm_count": int(harm.notna().sum()),
                            "both_false_count": int(both_false.notna().sum()),
                        }
                    )
    return pd.DataFrame(rows)


def build_risk_contrast(risk: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for method_id, baseline_id, comparison_id in COMPARISONS:
        method = risk[risk["method_id"].eq(method_id)].copy()
        baseline = risk[risk["method_id"].eq(baseline_id)].copy()
        merged = baseline.merge(
            method,
            on=["split_id", "descriptor", "coverage"],
            suffixes=("_baseline", "_method"),
            validate="one_to_one",
        )
        for (descriptor, coverage), frame in merged.groupby(["descriptor", "coverage"]):
            rows.append(
                {
                    "comparison_id": comparison_id,
                    "method_id": method_id,
                    "baseline_method_id": baseline_id,
                    "descriptor": descriptor,
                    "coverage": float(coverage),
                    "mean_true_top1_rate_eligible_gain": safe_mean(frame["true_top1_rate_eligible_method"] - frame["true_top1_rate_eligible_baseline"]),
                    "mean_false_top1_rate_eligible_reduction": safe_mean(frame["false_top1_rate_eligible_baseline"] - frame["false_top1_rate_eligible_method"]),
                    "mean_hard_negative_top1_rate_reduction": safe_mean(frame["hard_negative_top1_rate_baseline"] - frame["hard_negative_top1_rate_method"]),
                    "split_count": int(len(frame)),
                }
            )
    return pd.DataFrame(rows)


def write_summary(query_outcome: pd.DataFrame, feature_contrast: pd.DataFrame, risk_contrast: pd.DataFrame) -> None:
    lines = [
        "# Phase 13B Quality Boundary Diagnosis",
        "",
        "Date: 2026-06-17",
        "",
        "## Is Phase 13 Good Or Bad?",
        "",
        "It is a good update with an important boundary. Learned PF-ERI is clearly better than fixed PF-ERI, so the upgrade from hand-written utility to learned evidence utility is justified. However, learned PF-ERI does not consistently beat learned quality-control, so the final claim cannot be that PF-ERI reranking alone is a general breakthrough.",
        "",
        "The correct interpretation is: PF-ERI contains useful signal, but part of that signal overlaps with image-quality and utility proxies. The next scientific move is to identify where PF-ERI contributes beyond quality, especially descriptor-evidence conflict and unreliable hard-negative control.",
        "",
        "## Query-Level Rescue/Harm Balance",
        "",
    ]
    focus = query_outcome[query_outcome["comparison_id"].isin(["pf_eri_full_vs_quality_control", "pf_eri_full_vs_fixed_pf_eri"])]
    summary = focus.groupby(["comparison_id", "descriptor"])[
        ["net_true_top1_gain", "rescue_count", "harm_count", "hard_negative_top1_reduction"]
    ].mean().reset_index()
    for _, row in summary.sort_values(["comparison_id", "descriptor"]).iterrows():
        lines.append(
            "- "
            f"{row['comparison_id']} / {row['descriptor']}: "
            f"net top-1 gain={row['net_true_top1_gain']:.4f}, "
            f"mean rescues={row['rescue_count']:.1f}, "
            f"mean harms={row['harm_count']:.1f}, "
            f"hard-negative reduction={row['hard_negative_top1_reduction']:.4f}"
        )

    lines += [
        "",
        "## Boundary Features To Inspect",
        "",
        "The feature-contrast table reports whether rescues have higher pair reliability, lower conflict, stronger descriptor support, or better visual evidence than harms. This is the main diagnostic for turning the mixed Phase 13 result into a sharper RQ4 training-weight design.",
        "",
        "Most relevant external guidance aligns with this direction: hard negatives can improve contrastive learning when controlled; noisy samples and unreliable pseudo-labels need filtering or down-weighting; animal Re-ID benchmarks increasingly emphasize split design and fair controls rather than raw accuracy only.",
        "",
        "## Next Upgrade",
        "",
        "Phase 13C should not keep adding generic reranking models. It should use PF-ERI as a training-control signal:",
        "",
        "1. reliability-weighted positive pairs only where identities have at least two images;",
        "2. soft down-weighting or exclusion of high-similarity low-admissibility hard negatives;",
        "3. conflict-aware loss terms that separate descriptor similarity from evidence admissibility;",
        "4. matched quality-control and random-control training runs to prove the PF-ERI signal is not just quality filtering.",
        "",
        "## Outputs",
        "",
        f"- `{QUERY_OUTCOME.relative_to(PROJECT_ROOT)}`",
        f"- `{FEATURE_CONTRAST.relative_to(PROJECT_ROOT)}`",
        f"- `{RISK_CONTRAST.relative_to(PROJECT_ROOT)}`",
    ]
    SUMMARY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build(args: argparse.Namespace) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    top1 = attach_features(load_top1(args.top1), load_features(args.training_table))
    risk = pd.read_csv(args.risk_coverage)
    query_outcome = build_query_outcomes(top1)
    feature_contrast = build_feature_contrast(top1)
    risk_contrast = build_risk_contrast(risk)

    query_outcome.to_csv(QUERY_OUTCOME, index=False)
    feature_contrast.to_csv(FEATURE_CONTRAST, index=False)
    risk_contrast.to_csv(RISK_CONTRAST, index=False)
    write_summary(query_outcome, feature_contrast, risk_contrast)

    audit = {
        "top1_records": int(len(top1)),
        "query_outcome_rows": int(len(query_outcome)),
        "feature_contrast_rows": int(len(feature_contrast)),
        "risk_contrast_rows": int(len(risk_contrast)),
        "comparisons": [item[2] for item in COMPARISONS],
    }
    BUILD_AUDIT.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(f"Wrote Phase 13B quality-boundary diagnosis to {OUT_DIR.relative_to(PROJECT_ROOT)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top1", type=Path, default=TOP1)
    parser.add_argument("--training-table", type=Path, default=TRAINING_TABLE)
    parser.add_argument("--risk-coverage", type=Path, default=RISK_COVERAGE)
    return parser.parse_args()


if __name__ == "__main__":
    build(parse_args())
