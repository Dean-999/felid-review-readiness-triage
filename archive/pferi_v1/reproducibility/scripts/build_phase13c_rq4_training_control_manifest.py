#!/usr/bin/env python3
"""Build Phase 13C RQ4 reliability-aware training-control manifest.

This phase prepares pair-level controls for metric learning. It does not train
a model. The goal is to make the next RQ4 training step auditable before any
GPU run: admissible positive weighting, unsafe hard-negative control, and
matched quality/random controls are all explicit in one table.
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
PHASE12_TABLE = PROJECT_ROOT / "outputs/czechlynx/phase12/phase12_pair_candidate_analysis_table.csv"
PHASE13_DIR = PROJECT_ROOT / "outputs/czechlynx/phase13"
OUT_DIR = PHASE13_DIR / "rq4_training_control_manifest"

PAIR_MANIFEST = OUT_DIR / "phase13c_rq4_pair_training_control_manifest.csv"
IMAGE_MANIFEST = OUT_DIR / "phase13c_rq4_image_training_roles.csv"
SUMMARY = OUT_DIR / "phase13c_rq4_control_summary.csv"
POLICY_SUMMARY = OUT_DIR / "phase13c_rq4_policy_comparison_summary.csv"
SUMMARY_MD = OUT_DIR / "phase13c_rq4_training_control_manifest_summary.md"
BUILD_AUDIT = OUT_DIR / "phase13c_rq4_training_control_manifest_build_audit.json"

RANDOM_SEED = 20260617

USECOLS = [
    "split_id",
    "calibration_or_evaluation",
    "descriptor",
    "query_image_id",
    "candidate_image_id",
    "query_identity_token",
    "candidate_identity_token",
    "same_identity",
    "candidate_rank_raw",
    "descriptor_similarity_percentile",
    "reciprocal_rank_support",
    "margin_confidence_norm",
    "descriptor_disagreement_score",
    "pair_reliability_score",
    "image_quality_proxy_min",
    "visual_identity_evidence_min",
    "descriptor_evidence_conflict_score",
    "candidate_utility_rq_score",
    "hard_negative_candidate",
]


def yes_no_to_bool(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin({"yes", "true", "1"})


def bool_to_yes_no(series: pd.Series | np.ndarray) -> np.ndarray:
    return np.where(pd.Series(series).astype(bool), "yes", "no")


def clamp01(value: pd.Series | np.ndarray | float) -> pd.Series | np.ndarray | float:
    return np.clip(value, 0.0, 1.0)


def safe_mean(values: pd.Series | np.ndarray | list[float]) -> float:
    series = pd.Series(values, dtype="float64").replace([np.inf, -np.inf], np.nan).dropna()
    return float(series.mean()) if len(series) else math.nan


def load_table(path: Path) -> pd.DataFrame:
    table = pd.read_csv(path, usecols=USECOLS)
    table["same_identity"] = yes_no_to_bool(table["same_identity"])
    table["hard_negative_candidate"] = yes_no_to_bool(table["hard_negative_candidate"])
    numeric = [col for col in USECOLS if col not in {
        "calibration_or_evaluation",
        "descriptor",
        "query_image_id",
        "candidate_image_id",
        "query_identity_token",
        "candidate_identity_token",
        "same_identity",
        "hard_negative_candidate",
    }]
    for column in numeric:
        table[column] = pd.to_numeric(table[column], errors="coerce")
    identity_sizes = (
        table[["query_image_id", "query_identity_token"]]
        .drop_duplicates()
        .groupby("query_identity_token")["query_image_id"]
        .nunique()
        .to_dict()
    )
    table["query_identity_image_count"] = table["query_identity_token"].map(identity_sizes).astype(int)
    table["candidate_identity_image_count"] = table["candidate_identity_token"].map(identity_sizes).fillna(1).astype(int)
    table["positive_pair_eligible"] = table["same_identity"] & table["query_identity_image_count"].ge(2)
    table["singleton_involved"] = table["query_identity_image_count"].eq(1) | table["candidate_identity_image_count"].eq(1)
    table["descriptor_quality_score"] = clamp01(
        0.70 * table["descriptor_similarity_percentile"] + 0.30 * table["image_quality_proxy_min"]
    )
    table["pf_eri_admissible_positive_weight"] = clamp01(
        0.45 * table["pair_reliability_score"]
        + 0.20 * table["visual_identity_evidence_min"]
        + 0.15 * table["image_quality_proxy_min"]
        + 0.10 * table["margin_confidence_norm"]
        + 0.10 * (1.0 - table["descriptor_evidence_conflict_score"])
    )
    table.loc[~table["positive_pair_eligible"], "pf_eri_admissible_positive_weight"] = 0.0
    table["quality_positive_weight"] = np.where(
        table["positive_pair_eligible"],
        clamp01(0.70 * table["image_quality_proxy_min"] + 0.30 * table["visual_identity_evidence_min"]),
        0.0,
    )
    table["uniform_positive_weight"] = np.where(table["positive_pair_eligible"], 1.0, 0.0)
    return table


def add_split_thresholds(table: pd.DataFrame) -> pd.DataFrame:
    table = table.copy()
    rows: list[pd.DataFrame] = []
    for _, frame in table.groupby(["split_id", "descriptor", "calibration_or_evaluation"], sort=True):
        positives = frame[frame["positive_pair_eligible"]]
        negatives = frame[~frame["same_identity"]]
        pos_weight = positives["pf_eri_admissible_positive_weight"]
        neg_similarity = negatives["descriptor_similarity_percentile"]
        frame = frame.copy()
        frame["positive_weight_q25"] = float(pos_weight.quantile(0.25)) if len(pos_weight) else math.nan
        frame["positive_weight_q50"] = float(pos_weight.quantile(0.50)) if len(pos_weight) else math.nan
        frame["positive_weight_q75"] = float(pos_weight.quantile(0.75)) if len(pos_weight) else math.nan
        frame["hard_negative_similarity_q90"] = float(neg_similarity.quantile(0.90)) if len(neg_similarity) else math.nan
        frame["hard_negative_similarity_q95"] = float(neg_similarity.quantile(0.95)) if len(neg_similarity) else math.nan
        frame["conflict_q75"] = float(frame["descriptor_evidence_conflict_score"].quantile(0.75))
        frame["low_reliability_q25"] = float(frame["pair_reliability_score"].quantile(0.25))
        rows.append(frame)
    out = pd.concat(rows, ignore_index=True)
    return out


def build_policy_weights(table: pd.DataFrame) -> pd.DataFrame:
    table = add_split_thresholds(table)
    table["unsafe_hard_negative"] = (
        (~table["same_identity"])
        & table["descriptor_similarity_percentile"].ge(table["hard_negative_similarity_q90"])
        & (
            table["pair_reliability_score"].le(table["low_reliability_q25"])
            | table["descriptor_evidence_conflict_score"].ge(table["conflict_q75"])
        )
    )
    table["descriptor_hard_negative"] = (
        (~table["same_identity"]) & table["descriptor_similarity_percentile"].ge(table["hard_negative_similarity_q90"])
    )
    table["conflict_hard_negative"] = (
        table["descriptor_hard_negative"]
        & table["descriptor_evidence_conflict_score"].ge(table["conflict_q75"])
    )
    table["admissible_positive_high"] = (
        table["positive_pair_eligible"] & table["pf_eri_admissible_positive_weight"].ge(table["positive_weight_q75"])
    )
    table["admissible_positive_low"] = (
        table["positive_pair_eligible"] & table["pf_eri_admissible_positive_weight"].le(table["positive_weight_q25"])
    )

    rng = np.random.default_rng(RANDOM_SEED)
    table["random_positive_weight"] = np.where(table["positive_pair_eligible"], rng.random(len(table)), 0.0)
    table["random_negative_weight"] = np.where(table["same_identity"], 0.0, 1.0)

    table["descriptor_only_positive_weight"] = table["uniform_positive_weight"]
    table["descriptor_only_negative_weight"] = np.where(table["same_identity"], 0.0, 1.0)

    table["quality_control_positive_weight"] = table["quality_positive_weight"]
    table["quality_control_negative_weight"] = np.where(table["same_identity"], 0.0, 1.0)

    table["pf_eri_positive_weight"] = table["pf_eri_admissible_positive_weight"]
    table["pf_eri_negative_weight"] = np.where(table["same_identity"], 0.0, 1.0)

    # Soft negative control: keep ordinary negatives, but reduce the influence of
    # high-similarity negatives whose visual evidence is unreliable or conflicting.
    table["pf_eri_soft_negative_weight"] = np.where(
        table["same_identity"],
        0.0,
        np.where(table["unsafe_hard_negative"], 0.35, 1.0),
    )
    table["pf_eri_conflict_aware_positive_weight"] = table["pf_eri_positive_weight"]
    table["pf_eri_conflict_aware_negative_weight"] = table["pf_eri_soft_negative_weight"]

    table["recommended_rq4_policy"] = np.select(
        [
            table["admissible_positive_high"],
            table["admissible_positive_low"],
            table["unsafe_hard_negative"],
            table["descriptor_hard_negative"],
            table["positive_pair_eligible"],
        ],
        [
            "emphasize_admissible_positive",
            "downweight_weak_positive",
            "soften_unsafe_hard_negative",
            "retain_controlled_hard_negative",
            "retain_positive",
        ],
        default="standard_negative_or_distractor",
    )
    return table


def public_pair_manifest(table: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "split_id",
        "calibration_or_evaluation",
        "descriptor",
        "query_image_id",
        "candidate_image_id",
        "same_identity",
        "positive_pair_eligible",
        "singleton_involved",
        "candidate_rank_raw",
        "descriptor_similarity_percentile",
        "reciprocal_rank_support",
        "margin_confidence_norm",
        "descriptor_disagreement_score",
        "pair_reliability_score",
        "image_quality_proxy_min",
        "visual_identity_evidence_min",
        "descriptor_evidence_conflict_score",
        "candidate_utility_rq_score",
        "descriptor_quality_score",
        "pf_eri_admissible_positive_weight",
        "quality_positive_weight",
        "uniform_positive_weight",
        "random_positive_weight",
        "descriptor_hard_negative",
        "conflict_hard_negative",
        "unsafe_hard_negative",
        "admissible_positive_high",
        "admissible_positive_low",
        "descriptor_only_positive_weight",
        "descriptor_only_negative_weight",
        "quality_control_positive_weight",
        "quality_control_negative_weight",
        "pf_eri_positive_weight",
        "pf_eri_negative_weight",
        "pf_eri_conflict_aware_positive_weight",
        "pf_eri_conflict_aware_negative_weight",
        "recommended_rq4_policy",
    ]
    out = table[cols].copy()
    for col in [
        "same_identity",
        "positive_pair_eligible",
        "singleton_involved",
        "descriptor_hard_negative",
        "conflict_hard_negative",
        "unsafe_hard_negative",
        "admissible_positive_high",
        "admissible_positive_low",
    ]:
        out[col] = bool_to_yes_no(out[col])
    return out


def build_image_manifest(table: pd.DataFrame) -> pd.DataFrame:
    query = table[["query_image_id", "query_identity_token", "query_identity_image_count"]].drop_duplicates()
    query = query.rename(
        columns={
            "query_image_id": "image_id",
            "query_identity_token": "identity_token",
            "query_identity_image_count": "identity_image_count",
        }
    )
    rows = []
    for _, row in query.iterrows():
        identity_count = int(row["identity_image_count"])
        rows.append(
            {
                "image_id": row["image_id"],
                "identity_token": row["identity_token"],
                "identity_image_count": identity_count,
                "can_form_positive_pair": "yes" if identity_count >= 2 else "no",
                "rq4_training_role": "positive_anchor_candidate" if identity_count >= 2 else "singleton_distractor_only",
                "singleton_note": "not_positive_pair_source" if identity_count < 2 else "can_contribute_positive_pairs",
            }
        )
    return pd.DataFrame(rows).sort_values(["identity_token", "image_id"])


def build_summary(table: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for keys, frame in table.groupby(["split_id", "calibration_or_evaluation", "descriptor"], sort=True):
        split_id, role, descriptor = keys
        positives = frame[frame["positive_pair_eligible"]]
        negatives = frame[~frame["same_identity"]]
        rows.append(
            {
                "split_id": int(split_id),
                "calibration_or_evaluation": role,
                "descriptor": descriptor,
                "candidate_pair_count": int(len(frame)),
                "eligible_positive_pair_count": int(len(positives)),
                "negative_or_distractor_pair_count": int(len(negatives)),
                "singleton_involved_pair_count": int(frame["singleton_involved"].sum()),
                "admissible_positive_high_count": int(frame["admissible_positive_high"].sum()),
                "admissible_positive_low_count": int(frame["admissible_positive_low"].sum()),
                "descriptor_hard_negative_count": int(frame["descriptor_hard_negative"].sum()),
                "conflict_hard_negative_count": int(frame["conflict_hard_negative"].sum()),
                "unsafe_hard_negative_count": int(frame["unsafe_hard_negative"].sum()),
                "mean_pf_eri_positive_weight": safe_mean(positives["pf_eri_positive_weight"]),
                "mean_quality_positive_weight": safe_mean(positives["quality_control_positive_weight"]),
                "mean_pf_eri_conflict_negative_weight": safe_mean(negatives["pf_eri_conflict_aware_negative_weight"]),
                "positive_weight_q25": safe_mean(frame["positive_weight_q25"]),
                "positive_weight_q75": safe_mean(frame["positive_weight_q75"]),
                "hard_negative_similarity_q90": safe_mean(frame["hard_negative_similarity_q90"]),
                "conflict_q75": safe_mean(frame["conflict_q75"]),
            }
        )
    return pd.DataFrame(rows)


def build_policy_summary(table: pd.DataFrame) -> pd.DataFrame:
    policy_cols = {
        "descriptor_only": ("descriptor_only_positive_weight", "descriptor_only_negative_weight"),
        "random_control": ("random_positive_weight", "random_negative_weight"),
        "quality_control": ("quality_control_positive_weight", "quality_control_negative_weight"),
        "pf_eri_positive": ("pf_eri_positive_weight", "pf_eri_negative_weight"),
        "pf_eri_conflict_aware": (
            "pf_eri_conflict_aware_positive_weight",
            "pf_eri_conflict_aware_negative_weight",
        ),
    }
    rows: list[dict[str, Any]] = []
    for keys, frame in table.groupby(["split_id", "calibration_or_evaluation", "descriptor"], sort=True):
        split_id, role, descriptor = keys
        positives = frame[frame["positive_pair_eligible"]]
        negatives = frame[~frame["same_identity"]]
        for policy_id, (pos_col, neg_col) in policy_cols.items():
            rows.append(
                {
                    "split_id": int(split_id),
                    "calibration_or_evaluation": role,
                    "descriptor": descriptor,
                    "policy_id": policy_id,
                    "candidate_pair_count": int(len(frame)),
                    "positive_weight_sum": float(positives[pos_col].sum()),
                    "negative_weight_sum": float(negatives[neg_col].sum()),
                    "mean_positive_weight": safe_mean(positives[pos_col]),
                    "mean_negative_weight": safe_mean(negatives[neg_col]),
                    "unsafe_hard_negative_mean_weight": safe_mean(frame.loc[frame["unsafe_hard_negative"], neg_col]),
                    "unsafe_hard_negative_weight_sum": float(frame.loc[frame["unsafe_hard_negative"], neg_col].sum()),
                }
            )
    return pd.DataFrame(rows)


def write_summary_doc(summary: pd.DataFrame, policy_summary: pd.DataFrame, image_manifest: pd.DataFrame) -> None:
    eval_summary = summary[summary["calibration_or_evaluation"].eq("evaluation")]
    lines = [
        "# Phase 13C RQ4 Training-Control Manifest",
        "",
        "Date: 2026-06-17",
        "",
        "## Purpose",
        "",
        "This phase prepares the RQ4 metric-learning control surface. It does not train a model. It defines which pairs are valid positives, which negatives are controlled hard negatives, and how descriptor-only, random, quality-control, PF-ERI-positive, and PF-ERI-conflict-aware policies differ.",
        "",
        "## Why This Is The Right Next Step",
        "",
        "Phase 13 showed that learned PF-ERI improves over fixed PF-ERI but does not consistently beat learned quality-control in reranking. Therefore the next upgrade should use PF-ERI as a training-control signal, where pair admissibility and descriptor-evidence conflict are more theoretically central.",
        "",
        "## Image Role Boundary",
        "",
        f"- images total: {image_manifest['image_id'].nunique()}",
        f"- positive-pair capable images: {(image_manifest['can_form_positive_pair'] == 'yes').sum()}",
        f"- singleton distractor-only images: {(image_manifest['can_form_positive_pair'] == 'no').sum()}",
        "",
        "Singleton identities are retained as distractors and negative context, but they are not positive-pair sources.",
        "",
        "## Evaluation Split Pair Counts",
        "",
    ]
    for _, row in eval_summary.groupby("descriptor").mean(numeric_only=True).reset_index().iterrows():
        lines.append(
            "- "
            f"{row['descriptor']}: eligible positives={row['eligible_positive_pair_count']:.1f}, "
            f"unsafe hard negatives={row['unsafe_hard_negative_count']:.1f}, "
            f"descriptor hard negatives={row['descriptor_hard_negative_count']:.1f}, "
            f"mean PF-ERI positive weight={row['mean_pf_eri_positive_weight']:.3f}, "
            f"mean quality positive weight={row['mean_quality_positive_weight']:.3f}"
        )

    lines += [
        "",
        "## RQ4 Policy Set",
        "",
        "- descriptor_only: uniform positive and negative weights.",
        "- random_control: random positive weights with ordinary negative weights.",
        "- quality_control: positive weights from image quality and visual evidence only.",
        "- pf_eri_positive: positive weights from pair reliability, visual evidence, quality, margin, and conflict penalty.",
        "- pf_eri_conflict_aware: PF-ERI positive weights plus soft down-weighting of unsafe hard negatives.",
        "",
        "## Outputs",
        "",
        f"- `{PAIR_MANIFEST.relative_to(PROJECT_ROOT)}`",
        f"- `{IMAGE_MANIFEST.relative_to(PROJECT_ROOT)}`",
        f"- `{SUMMARY.relative_to(PROJECT_ROOT)}`",
        f"- `{POLICY_SUMMARY.relative_to(PROJECT_ROOT)}`",
    ]
    SUMMARY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build(args: argparse.Namespace) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    table = build_policy_weights(load_table(args.table))
    pair_manifest = public_pair_manifest(table)
    image_manifest = build_image_manifest(table)
    summary = build_summary(table)
    policy_summary = build_policy_summary(table)

    pair_manifest.to_csv(PAIR_MANIFEST, index=False)
    image_manifest.to_csv(IMAGE_MANIFEST, index=False)
    summary.to_csv(SUMMARY, index=False)
    policy_summary.to_csv(POLICY_SUMMARY, index=False)
    write_summary_doc(summary, policy_summary, image_manifest)

    audit = {
        "input_table": str(args.table.relative_to(PROJECT_ROOT)),
        "input_rows": int(len(table)),
        "image_count": int(image_manifest["image_id"].nunique()),
        "identity_count": int(image_manifest["identity_token"].nunique()),
        "pair_manifest_rows": int(len(pair_manifest)),
        "summary_rows": int(len(summary)),
        "policy_summary_rows": int(len(policy_summary)),
        "unsafe_hard_negative_count": int(table["unsafe_hard_negative"].sum()),
        "eligible_positive_pair_count": int(table["positive_pair_eligible"].sum()),
    }
    BUILD_AUDIT.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(f"Wrote Phase 13C RQ4 training-control manifest to {OUT_DIR.relative_to(PROJECT_ROOT)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--table", type=Path, default=PHASE12_TABLE)
    return parser.parse_args()


if __name__ == "__main__":
    build(parse_args())
