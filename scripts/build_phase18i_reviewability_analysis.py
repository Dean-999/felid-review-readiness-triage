#!/usr/bin/env python3
"""Analyze Phase18I human pair-reviewability labels."""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Any

import numpy as np

try:
    from scripts.phase18_pipeline_utils import now_utc, project_relative, read_csv, to_float, write_csv, write_json
except ImportError:  # pragma: no cover - direct script execution
    from phase18_pipeline_utils import now_utc, project_relative, read_csv, to_float, write_csv, write_json


DEFAULT_OUTPUT_ROOT = Path("outputs/phase18/phase18i_reviewability_analysis")
BOOTSTRAP_ITERATIONS = 5000
RANDOM_SEED = 20260702
ALLOWED_LABELS = {"review_ready", "low_evidence", "non_comparable", "uncertain"}

ANALYSIS_COLUMNS = [
    "review_pair_id",
    "descriptor_name",
    "reviewability_label",
    "review_ready",
    "not_review_ready",
    "reviewer_id",
    "review_timestamp",
    "sample_group",
    "same_identity_known_id",
    "candidate_rank_descriptor",
    "descriptor_similarity",
    "descriptor_similarity_percentile",
    "descriptor_evidence_conflict_score",
    "pf_eri_admissibility_score",
    "pf_eri_review_score",
    "pf_eri_route",
    "weakest_image_quality_score",
    "pair_geometry_score",
    "query_image_id",
    "candidate_image_id",
    "query_image_path",
    "candidate_image_path",
    "visibility_notes",
    "claim_boundary",
]

SUMMARY_COLUMNS = [
    "descriptor_name",
    "analysis_scope",
    "row_count",
    "completed_count",
    "missing_label_count",
    "invalid_label_count",
    "review_ready_count",
    "low_evidence_count",
    "non_comparable_count",
    "uncertain_count",
    "review_ready_rate",
    "not_review_ready_rate",
    "claim_boundary",
]

CROSSTAB_COLUMNS = [
    "descriptor_name",
    "factor",
    "level",
    "row_count",
    "review_ready_count",
    "not_review_ready_count",
    "review_ready_rate",
    "review_ready_rate_ci_lower",
    "review_ready_rate_ci_upper",
]

CONTRAST_COLUMNS = [
    "descriptor_name",
    "contrast_id",
    "group_a",
    "group_b",
    "group_a_count",
    "group_b_count",
    "group_a_review_ready_rate",
    "group_b_review_ready_rate",
    "risk_difference_a_minus_b",
    "risk_difference_ci_lower",
    "risk_difference_ci_upper",
    "odds_ratio_haldane",
    "fisher_exact_two_sided_p",
    "interpretation",
]

SCORE_COLUMNS = [
    "pf_eri_admissibility_score",
    "pf_eri_review_score",
    "descriptor_evidence_conflict_score",
    "weakest_image_quality_score",
    "pair_geometry_score",
    "descriptor_similarity_percentile",
    "candidate_rank_descriptor",
]

SCORE_CONTRAST_COLUMNS = [
    "descriptor_name",
    "score",
    "review_ready_count",
    "not_review_ready_count",
    "review_ready_mean",
    "not_review_ready_mean",
    "mean_difference_ready_minus_not_ready",
    "mean_difference_ci_lower",
    "mean_difference_ci_upper",
    "review_ready_median",
    "not_review_ready_median",
    "auc_higher_score_predicts_review_ready",
    "rank_biserial_higher_score_predicts_review_ready",
    "claim_boundary",
]


def merge_rows(working_csv: Path, full_packet_csv: Path, descriptor_name: str) -> list[dict[str, Any]]:
    working = read_csv(working_csv)
    full = {row["review_pair_id"]: row for row in read_csv(full_packet_csv)}
    if not working:
        raise ValueError("0 Phase18I working rows")
    rows = []
    for row in working:
        pair_id = row["review_pair_id"]
        if pair_id not in full:
            raise ValueError(f"working row missing from full packet: {pair_id}")
        merged = {**full[pair_id], **row}
        label = merged.get("reviewability_label", "")
        review_ready = label == "review_ready"
        merged["descriptor_name"] = descriptor_name
        merged["review_ready"] = "yes" if review_ready else "no"
        merged["not_review_ready"] = "no" if review_ready else "yes"
        merged["claim_boundary"] = (
            "Human label is pair reviewability only; known-ID truth is retained for analysis, "
            "not as a new identity annotation."
        )
        rows.append(merged)
    return rows


def ci_percentile(values: np.ndarray) -> tuple[float, float]:
    return float(np.percentile(values, 2.5)), float(np.percentile(values, 97.5))


def bootstrap_rate(values: list[int], iterations: int) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    rng = np.random.default_rng(RANDOM_SEED)
    arr = np.asarray(values, dtype=np.float64)
    idx = rng.integers(0, len(arr), size=(iterations, len(arr)))
    return ci_percentile(arr[idx].mean(axis=1))


def bootstrap_difference(a: list[float], b: list[float], iterations: int) -> tuple[float, float]:
    if not a or not b:
        return 0.0, 0.0
    rng = np.random.default_rng(RANDOM_SEED)
    aa = np.asarray(a, dtype=np.float64)
    bb = np.asarray(b, dtype=np.float64)
    a_idx = rng.integers(0, len(aa), size=(iterations, len(aa)))
    b_idx = rng.integers(0, len(bb), size=(iterations, len(bb)))
    return ci_percentile(aa[a_idx].mean(axis=1) - bb[b_idx].mean(axis=1))


def odds_ratio(a_ready: int, a_not: int, b_ready: int, b_not: int) -> float:
    return float(((a_ready + 0.5) * (b_not + 0.5)) / ((a_not + 0.5) * (b_ready + 0.5)))


def hypergeom_prob(x: int, row1: int, row2: int, col1: int, total: int) -> float:
    return math.comb(row1, x) * math.comb(row2, col1 - x) / math.comb(total, col1)


def fisher_exact_two_sided(a_ready: int, a_not: int, b_ready: int, b_not: int) -> float:
    row1 = a_ready + a_not
    row2 = b_ready + b_not
    col1 = a_ready + b_ready
    total = row1 + row2
    observed = hypergeom_prob(a_ready, row1, row2, col1, total)
    low = max(0, col1 - row2)
    high = min(row1, col1)
    p = 0.0
    for x in range(low, high + 1):
        prob = hypergeom_prob(x, row1, row2, col1, total)
        if prob <= observed + 1e-15:
            p += prob
    return float(min(1.0, p))


def auc_higher_score_positive(pos: list[float], neg: list[float]) -> tuple[float, float]:
    if not pos or not neg:
        return 0.0, 0.0
    wins = 0.0
    total = len(pos) * len(neg)
    for a in pos:
        for b in neg:
            if a > b:
                wins += 1.0
            elif a == b:
                wins += 0.5
    auc = wins / total
    return float(auc), float(2.0 * auc - 1.0)


def build_summary(rows: list[dict[str, Any]], descriptor_name: str) -> dict[str, Any]:
    labels = [row.get("reviewability_label", "") for row in rows]
    missing = sum(label == "" for label in labels)
    invalid = sum(label not in ALLOWED_LABELS and label != "" for label in labels)
    ready = sum(label == "review_ready" for label in labels)
    not_ready = len(rows) - ready
    return {
        "descriptor_name": descriptor_name,
        "analysis_scope": "Phase18I targeted MegaDescriptor/DINOv2 reviewability sample if completed",
        "row_count": len(rows),
        "completed_count": len(rows) - missing,
        "missing_label_count": missing,
        "invalid_label_count": invalid,
        "review_ready_count": ready,
        "low_evidence_count": sum(label == "low_evidence" for label in labels),
        "non_comparable_count": sum(label == "non_comparable" for label in labels),
        "uncertain_count": sum(label == "uncertain" for label in labels),
        "review_ready_rate": ready / len(rows) if rows else 0.0,
        "not_review_ready_rate": not_ready / len(rows) if rows else 0.0,
        "claim_boundary": "Reviewability labels are human audit labels, not identity labels.",
    }


def build_crosstabs(rows: list[dict[str, Any]], descriptor_name: str) -> list[dict[str, Any]]:
    output = []
    for factor in ["same_identity_known_id", "sample_group", "pf_eri_route"]:
        levels = sorted({row.get(factor, "") for row in rows})
        for level in levels:
            scoped = [row for row in rows if row.get(factor, "") == level]
            values = [1 if row["reviewability_label"] == "review_ready" else 0 for row in scoped]
            ci_lower, ci_upper = bootstrap_rate(values, BOOTSTRAP_ITERATIONS)
            output.append(
                {
                    "descriptor_name": descriptor_name,
                    "factor": factor,
                    "level": level,
                    "row_count": len(scoped),
                    "review_ready_count": sum(values),
                    "not_review_ready_count": len(values) - sum(values),
                    "review_ready_rate": sum(values) / len(values) if values else 0.0,
                    "review_ready_rate_ci_lower": ci_lower,
                    "review_ready_rate_ci_upper": ci_upper,
                }
            )
    return output


def binary_contrast(
    rows: list[dict[str, Any]],
    descriptor_name: str,
    contrast_id: str,
    factor: str,
    group_a: str,
    group_b: str,
    interpretation: str,
) -> dict[str, Any]:
    a = [row for row in rows if row.get(factor, "") == group_a]
    b = [row for row in rows if row.get(factor, "") == group_b]
    a_values = [1 if row["reviewability_label"] == "review_ready" else 0 for row in a]
    b_values = [1 if row["reviewability_label"] == "review_ready" else 0 for row in b]
    a_ready = sum(a_values)
    b_ready = sum(b_values)
    a_not = len(a_values) - a_ready
    b_not = len(b_values) - b_ready
    ci_lower, ci_upper = bootstrap_difference(a_values, b_values, BOOTSTRAP_ITERATIONS)
    return {
        "descriptor_name": descriptor_name,
        "contrast_id": contrast_id,
        "group_a": group_a,
        "group_b": group_b,
        "group_a_count": len(a_values),
        "group_b_count": len(b_values),
        "group_a_review_ready_rate": a_ready / len(a_values) if a_values else 0.0,
        "group_b_review_ready_rate": b_ready / len(b_values) if b_values else 0.0,
        "risk_difference_a_minus_b": (a_ready / len(a_values) if a_values else 0.0)
        - (b_ready / len(b_values) if b_values else 0.0),
        "risk_difference_ci_lower": ci_lower,
        "risk_difference_ci_upper": ci_upper,
        "odds_ratio_haldane": odds_ratio(a_ready, a_not, b_ready, b_not),
        "fisher_exact_two_sided_p": fisher_exact_two_sided(a_ready, a_not, b_ready, b_not)
        if a_values and b_values
        else 1.0,
        "interpretation": interpretation,
    }


def build_score_contrasts(rows: list[dict[str, Any]], descriptor_name: str) -> list[dict[str, Any]]:
    ready_rows = [row for row in rows if row["reviewability_label"] == "review_ready"]
    not_ready_rows = [row for row in rows if row["reviewability_label"] != "review_ready"]
    output = []
    for score in SCORE_COLUMNS:
        ready_values = [to_float(row.get(score, "")) for row in ready_rows]
        not_ready_values = [to_float(row.get(score, "")) for row in not_ready_rows]
        ci_lower, ci_upper = bootstrap_difference(ready_values, not_ready_values, BOOTSTRAP_ITERATIONS)
        auc, rank_biserial = auc_higher_score_positive(ready_values, not_ready_values)
        output.append(
            {
                "descriptor_name": descriptor_name,
                "score": score,
                "review_ready_count": len(ready_values),
                "not_review_ready_count": len(not_ready_values),
                "review_ready_mean": float(np.mean(ready_values)) if ready_values else 0.0,
                "not_review_ready_mean": float(np.mean(not_ready_values)) if not_ready_values else 0.0,
                "mean_difference_ready_minus_not_ready": (float(np.mean(ready_values)) if ready_values else 0.0)
                - (float(np.mean(not_ready_values)) if not_ready_values else 0.0),
                "mean_difference_ci_lower": ci_lower,
                "mean_difference_ci_upper": ci_upper,
                "review_ready_median": float(np.median(ready_values)) if ready_values else 0.0,
                "not_review_ready_median": float(np.median(not_ready_values)) if not_ready_values else 0.0,
                "auc_higher_score_predicts_review_ready": auc,
                "rank_biserial_higher_score_predicts_review_ready": rank_biserial,
                "claim_boundary": "Exploratory score-label association in targeted Phase18I sample.",
            }
        )
    return output


def build_phase18i_reviewability_analysis(
    descriptor_name: str,
    working_csv: Path,
    full_packet_csv: Path,
    output_dir: Path,
) -> dict[str, Any]:
    rows = merge_rows(working_csv, full_packet_csv, descriptor_name)
    output_dir.mkdir(parents=True, exist_ok=True)
    analysis_csv = output_dir / "phase18i_reviewability_analysis_ready.csv"
    summary_csv = output_dir / "phase18i_reviewability_summary.csv"
    crosstab_csv = output_dir / "phase18i_reviewability_crosstabs.csv"
    contrast_csv = output_dir / "phase18i_reviewability_binary_contrasts.csv"
    score_csv = output_dir / "phase18i_reviewability_score_contrasts.csv"

    summary = build_summary(rows, descriptor_name)
    crosstabs = build_crosstabs(rows, descriptor_name)
    contrasts = [
        binary_contrast(
            rows,
            descriptor_name,
            "same_id_controls_vs_false_candidates",
            "same_identity_known_id",
            "yes",
            "no",
            "Same-ID controls should remain review-ready if PF-ERI reviewability is not simply rejecting true matches.",
        ),
        binary_contrast(
            rows,
            descriptor_name,
            "same_id_sample_group_vs_false_sample_group",
            "sample_group",
            "high_similarity_same_identity_control",
            "high_similarity_false_high_conflict",
            "Targeted visual reviewability difference between same-ID controls and high-similarity false candidates.",
        ),
    ]
    score_contrasts = build_score_contrasts(rows, descriptor_name)

    write_csv(analysis_csv, rows, ANALYSIS_COLUMNS)
    write_csv(summary_csv, [summary], SUMMARY_COLUMNS)
    write_csv(crosstab_csv, crosstabs, CROSSTAB_COLUMNS)
    write_csv(contrast_csv, contrasts, CONTRAST_COLUMNS)
    write_csv(score_csv, score_contrasts, SCORE_CONTRAST_COLUMNS)

    low_evidence_count = int(summary["low_evidence_count"])
    non_comparable_count = int(summary["non_comparable_count"])
    audit = {
        "built_at_utc": now_utc(),
        "descriptor_name": descriptor_name,
        "working_csv": project_relative(working_csv),
        "full_packet_csv": project_relative(full_packet_csv),
        "analysis_csv": project_relative(analysis_csv),
        "summary_csv": project_relative(summary_csv),
        "crosstab_csv": project_relative(crosstab_csv),
        "contrast_csv": project_relative(contrast_csv),
        "score_contrast_csv": project_relative(score_csv),
        "bootstrap_iterations": BOOTSTRAP_ITERATIONS,
        "random_seed": RANDOM_SEED,
        "summary": summary,
        "status": "PASS" if summary["missing_label_count"] == 0 and summary["invalid_label_count"] == 0 else "WARN_INCOMPLETE",
        "claim_caution": (
            "No low_evidence/non_comparable labels were observed; interpret non-ready labels as uncertainty, "
            "not confirmed low-evidence/non-comparable mechanism."
            if low_evidence_count == 0 and non_comparable_count == 0
            else "Reviewability labels include explicit low-evidence or non-comparable outcomes."
        ),
        "claim_boundary": "Phase18I analyzes targeted human reviewability labels only.",
    }
    write_json(output_dir / "phase18i_reviewability_analysis_audit.json", audit)
    return audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--descriptor-name", required=True)
    parser.add_argument("--working-csv", type=Path, required=True)
    parser.add_argument("--full-packet-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir or DEFAULT_OUTPUT_ROOT / args.descriptor_name
    audit = build_phase18i_reviewability_analysis(
        descriptor_name=args.descriptor_name,
        working_csv=args.working_csv,
        full_packet_csv=args.full_packet_csv,
        output_dir=output_dir,
    )
    print(f"{audit['status']} phase18i reviewability analysis")
    print(f"descriptor_name={audit['descriptor_name']}")
    print(f"row_count={audit['summary']['row_count']}")
    print(f"review_ready_count={audit['summary']['review_ready_count']}")
    print(f"uncertain_count={audit['summary']['uncertain_count']}")
    print(f"WROTE {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
