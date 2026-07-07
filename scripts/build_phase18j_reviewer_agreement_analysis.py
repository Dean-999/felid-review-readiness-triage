#!/usr/bin/env python3
"""Analyze Phase18J multi-reviewer full-queue reviewability labels."""

from __future__ import annotations

import argparse
import csv
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

try:
    from scripts.phase18_pipeline_utils import now_utc, project_relative, read_csv, to_float, write_csv, write_json
except ImportError:  # pragma: no cover - direct script execution
    from phase18_pipeline_utils import now_utc, project_relative, read_csv, to_float, write_csv, write_json


DEFAULT_PACKET_ROOT = Path("outputs/phase18/phase18j_full_queue_review_packet_100")
DEFAULT_REVIEW_ROOT = Path("outputs/phase18/phase18j_streamlit_review_100")
DEFAULT_OUTPUT_DIR = Path("outputs/phase18/phase18j_reviewer_agreement_analysis_100")
DESCRIPTORS = ["megadescriptor_l_384", "dinov2_vitl14"]
REVIEWERS = ["reviewer1", "reviewer2", "reviewer3"]
BOOTSTRAP_ITERATIONS = 5000
RANDOM_SEED = 20260703

DETAIL_COLUMNS = [
    "descriptor_name",
    "review_pair_id",
    "reviewer_id",
    "reviewability_decision",
    "binary_review_ready",
    "not_ready_reason",
    "same_identity_known_id",
    "rank_bin",
    "admissibility_tertile",
    "candidate_rank_descriptor",
    "descriptor_similarity_percentile",
    "pf_eri_admissibility_score",
    "pf_eri_review_score",
    "weakest_image_quality_score",
    "pair_geometry_score",
    "pf_eri_route",
]

PAIR_COLUMNS = [
    "descriptor_name",
    "review_pair_id",
    "reviewer_count",
    "majority_decision",
    "majority_binary_review_ready",
    "unanimous_decision",
    "decision_votes",
    "reason_votes",
    "same_identity_known_id",
    "rank_bin",
    "admissibility_tertile",
    "candidate_rank_descriptor",
    "descriptor_similarity_percentile",
    "pf_eri_admissibility_score",
    "pf_eri_review_score",
    "weakest_image_quality_score",
    "pair_geometry_score",
    "pf_eri_route",
]

AGREEMENT_COLUMNS = [
    "descriptor_name",
    "reviewer_a",
    "reviewer_b",
    "label_scope",
    "pair_count",
    "percent_agreement",
    "cohen_kappa",
]

SUMMARY_COLUMNS = [
    "descriptor_name",
    "scope",
    "pair_count",
    "review_ready_count",
    "not_review_ready_count",
    "uncertain_count",
    "low_evidence_count",
    "non_comparable_count",
    "review_ready_rate",
    "same_id_review_ready_rate",
    "false_candidate_review_ready_rate",
    "risk_difference_same_id_minus_false",
    "risk_difference_ci_lower",
    "risk_difference_ci_upper",
]

SCORE_COLUMNS = [
    "pf_eri_admissibility_score",
    "pf_eri_review_score",
    "weakest_image_quality_score",
    "pair_geometry_score",
    "descriptor_similarity_percentile",
]

SCORE_CONTRAST_COLUMNS = [
    "descriptor_name",
    "scope",
    "score",
    "review_ready_mean",
    "non_ready_mean",
    "mean_difference_ready_minus_non_ready",
    "mean_difference_ci_lower",
    "mean_difference_ci_upper",
    "auc_higher_score_predicts_review_ready",
]


def binary_ready(decision: str) -> str:
    return "yes" if decision == "review_ready" else "no"


def cohen_kappa(labels_a: list[str], labels_b: list[str]) -> float:
    if len(labels_a) != len(labels_b) or not labels_a:
        return 0.0
    total = len(labels_a)
    observed = sum(a == b for a, b in zip(labels_a, labels_b)) / total
    counts_a = Counter(labels_a)
    counts_b = Counter(labels_b)
    expected = sum((counts_a[label] / total) * (counts_b[label] / total) for label in set(counts_a) | set(counts_b))
    if expected >= 1.0:
        return 1.0
    return (observed - expected) / (1.0 - expected)


def bootstrap_difference(a: list[float], b: list[float]) -> tuple[float, float]:
    if not a or not b:
        return 0.0, 0.0
    rng = np.random.default_rng(RANDOM_SEED)
    aa = np.asarray(a, dtype=np.float64)
    bb = np.asarray(b, dtype=np.float64)
    ai = rng.integers(0, len(aa), size=(BOOTSTRAP_ITERATIONS, len(aa)))
    bi = rng.integers(0, len(bb), size=(BOOTSTRAP_ITERATIONS, len(bb)))
    diff = aa[ai].mean(axis=1) - bb[bi].mean(axis=1)
    return float(np.percentile(diff, 2.5)), float(np.percentile(diff, 97.5))


def auc_higher_score_positive(pos: list[float], neg: list[float]) -> float:
    if not pos or not neg:
        return 0.0
    wins = 0.0
    for a in pos:
        for b in neg:
            if a > b:
                wins += 1.0
            elif a == b:
                wins += 0.5
    return wins / (len(pos) * len(neg))


def load_descriptor(packet_root: Path, review_root: Path, descriptor_name: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    full = {row["review_pair_id"]: row for row in read_csv(packet_root / descriptor_name / "phase18j_full_queue_review_packet.csv")}
    detail = []
    by_pair: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for reviewer_id in REVIEWERS:
        working_csv = review_root / reviewer_id / descriptor_name / "phase18j_full_queue_review_working.csv"
        if not working_csv.exists():
            raise ValueError(f"missing reviewer working CSV: {working_csv}")
        for row in read_csv(working_csv):
            pair_id = row["review_pair_id"]
            if pair_id not in full:
                raise ValueError(f"working pair missing from packet: {pair_id}")
            source = full[pair_id]
            decision = row["reviewability_decision"]
            record = {
                "descriptor_name": descriptor_name,
                "review_pair_id": pair_id,
                "reviewer_id": reviewer_id,
                "reviewability_decision": decision,
                "binary_review_ready": binary_ready(decision),
                "not_ready_reason": row["not_ready_reason"],
                "same_identity_known_id": source["same_identity_known_id"],
                "rank_bin": source["rank_bin"],
                "admissibility_tertile": source["admissibility_tertile"],
                "candidate_rank_descriptor": source["candidate_rank_descriptor"],
                "descriptor_similarity_percentile": source["descriptor_similarity_percentile"],
                "pf_eri_admissibility_score": source["pf_eri_admissibility_score"],
                "pf_eri_review_score": source["pf_eri_review_score"],
                "weakest_image_quality_score": source["weakest_image_quality_score"],
                "pair_geometry_score": source["pair_geometry_score"],
                "pf_eri_route": source["pf_eri_route"],
            }
            detail.append(record)
            by_pair[pair_id].append(record)
    pairs = []
    for pair_id, votes in sorted(by_pair.items()):
        source = full[pair_id]
        decisions = [vote["reviewability_decision"] for vote in votes]
        reasons = [vote["not_ready_reason"] for vote in votes if vote["not_ready_reason"]]
        decision_counts = Counter(decisions)
        reason_counts = Counter(reasons)
        majority_decision = decision_counts.most_common(1)[0][0]
        pairs.append(
            {
                "descriptor_name": descriptor_name,
                "review_pair_id": pair_id,
                "reviewer_count": len(votes),
                "majority_decision": majority_decision,
                "majority_binary_review_ready": binary_ready(majority_decision),
                "unanimous_decision": "yes" if len(decision_counts) == 1 else "no",
                "decision_votes": ";".join(f"{key}:{value}" for key, value in sorted(decision_counts.items())),
                "reason_votes": ";".join(f"{key}:{value}" for key, value in sorted(reason_counts.items())),
                "same_identity_known_id": source["same_identity_known_id"],
                "rank_bin": source["rank_bin"],
                "admissibility_tertile": source["admissibility_tertile"],
                "candidate_rank_descriptor": source["candidate_rank_descriptor"],
                "descriptor_similarity_percentile": source["descriptor_similarity_percentile"],
                "pf_eri_admissibility_score": source["pf_eri_admissibility_score"],
                "pf_eri_review_score": source["pf_eri_review_score"],
                "weakest_image_quality_score": source["weakest_image_quality_score"],
                "pair_geometry_score": source["pair_geometry_score"],
                "pf_eri_route": source["pf_eri_route"],
            }
        )
    return detail, pairs


def agreement_rows(detail: list[dict[str, Any]], descriptor_name: str) -> list[dict[str, Any]]:
    rows = []
    for i, reviewer_a in enumerate(REVIEWERS):
        for reviewer_b in REVIEWERS[i + 1 :]:
            a_rows = {row["review_pair_id"]: row for row in detail if row["descriptor_name"] == descriptor_name and row["reviewer_id"] == reviewer_a}
            b_rows = {row["review_pair_id"]: row for row in detail if row["descriptor_name"] == descriptor_name and row["reviewer_id"] == reviewer_b}
            common = sorted(set(a_rows) & set(b_rows))
            for scope, column in [("three_class_decision", "reviewability_decision"), ("binary_review_ready", "binary_review_ready")]:
                labels_a = [a_rows[pair_id][column] for pair_id in common]
                labels_b = [b_rows[pair_id][column] for pair_id in common]
                rows.append(
                    {
                        "descriptor_name": descriptor_name,
                        "reviewer_a": reviewer_a,
                        "reviewer_b": reviewer_b,
                        "label_scope": scope,
                        "pair_count": len(common),
                        "percent_agreement": sum(a == b for a, b in zip(labels_a, labels_b)) / len(common) if common else 0.0,
                        "cohen_kappa": cohen_kappa(labels_a, labels_b),
                    }
                )
    return rows


def summary_row(rows: list[dict[str, Any]], descriptor_name: str, scope: str, decision_col: str) -> dict[str, Any]:
    ready = [1 if row[decision_col] == "yes" or row[decision_col] == "review_ready" else 0 for row in rows]
    same = [value for value, row in zip(ready, rows) if row["same_identity_known_id"] == "yes"]
    false = [value for value, row in zip(ready, rows) if row["same_identity_known_id"] == "no"]
    ci_lower, ci_upper = bootstrap_difference(same, false)
    labels = [row.get("majority_decision", row.get("reviewability_decision", "")) for row in rows]
    reasons = [row.get("not_ready_reason", "") for row in rows]
    if scope == "majority_vote":
        reasons = [row.get("reason_votes", "") for row in rows]
    return {
        "descriptor_name": descriptor_name,
        "scope": scope,
        "pair_count": len(rows),
        "review_ready_count": sum(ready),
        "not_review_ready_count": sum(label == "not_review_ready" for label in labels),
        "uncertain_count": sum(label == "uncertain" for label in labels),
        "low_evidence_count": sum("low_evidence" in reason for reason in reasons),
        "non_comparable_count": sum("non_comparable" in reason for reason in reasons),
        "review_ready_rate": sum(ready) / len(ready) if ready else 0.0,
        "same_id_review_ready_rate": sum(same) / len(same) if same else 0.0,
        "false_candidate_review_ready_rate": sum(false) / len(false) if false else 0.0,
        "risk_difference_same_id_minus_false": (sum(same) / len(same) if same else 0.0) - (sum(false) / len(false) if false else 0.0),
        "risk_difference_ci_lower": ci_lower,
        "risk_difference_ci_upper": ci_upper,
    }


def score_rows(rows: list[dict[str, Any]], descriptor_name: str, scope: str, decision_col: str) -> list[dict[str, Any]]:
    output = []
    for score in SCORE_COLUMNS:
        ready_values = [to_float(row[score]) for row in rows if row[decision_col] == "yes" or row[decision_col] == "review_ready"]
        non_ready_values = [to_float(row[score]) for row in rows if not (row[decision_col] == "yes" or row[decision_col] == "review_ready")]
        ci_lower, ci_upper = bootstrap_difference(ready_values, non_ready_values)
        output.append(
            {
                "descriptor_name": descriptor_name,
                "scope": scope,
                "score": score,
                "review_ready_mean": float(np.mean(ready_values)) if ready_values else 0.0,
                "non_ready_mean": float(np.mean(non_ready_values)) if non_ready_values else 0.0,
                "mean_difference_ready_minus_non_ready": (float(np.mean(ready_values)) if ready_values else 0.0)
                - (float(np.mean(non_ready_values)) if non_ready_values else 0.0),
                "mean_difference_ci_lower": ci_lower,
                "mean_difference_ci_upper": ci_upper,
                "auc_higher_score_predicts_review_ready": auc_higher_score_positive(ready_values, non_ready_values),
            }
        )
    return output


def build_phase18j_reviewer_agreement_analysis(
    packet_root: Path = DEFAULT_PACKET_ROOT,
    review_root: Path = DEFAULT_REVIEW_ROOT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    all_detail = []
    all_pairs = []
    all_agreement = []
    for descriptor_name in DESCRIPTORS:
        detail, pairs = load_descriptor(packet_root, review_root, descriptor_name)
        all_detail.extend(detail)
        all_pairs.extend(pairs)
        all_agreement.extend(agreement_rows(detail, descriptor_name))
    summaries = []
    scores = []
    for descriptor_name in DESCRIPTORS:
        descriptor_detail = [row for row in all_detail if row["descriptor_name"] == descriptor_name]
        descriptor_pairs = [row for row in all_pairs if row["descriptor_name"] == descriptor_name]
        summaries.append(summary_row(descriptor_pairs, descriptor_name, "majority_vote", "majority_binary_review_ready"))
        scores.extend(score_rows(descriptor_pairs, descriptor_name, "majority_vote", "majority_binary_review_ready"))
        for reviewer_id in REVIEWERS:
            reviewer_rows = [row for row in descriptor_detail if row["reviewer_id"] == reviewer_id]
            summaries.append(summary_row(reviewer_rows, descriptor_name, reviewer_id, "reviewability_decision"))
            scores.extend(score_rows(reviewer_rows, descriptor_name, reviewer_id, "reviewability_decision"))
    write_csv(output_dir / "phase18j_reviewer_label_detail.csv", all_detail, DETAIL_COLUMNS)
    write_csv(output_dir / "phase18j_pair_majority_labels.csv", all_pairs, PAIR_COLUMNS)
    write_csv(output_dir / "phase18j_reviewer_agreement.csv", all_agreement, AGREEMENT_COLUMNS)
    write_csv(output_dir / "phase18j_reviewability_summary.csv", summaries, SUMMARY_COLUMNS)
    write_csv(output_dir / "phase18j_score_contrasts.csv", scores, SCORE_CONTRAST_COLUMNS)
    audit = {
        "built_at_utc": now_utc(),
        "packet_root": project_relative(packet_root),
        "review_root": project_relative(review_root),
        "output_dir": project_relative(output_dir),
        "detail_rows": len(all_detail),
        "majority_pair_rows": len(all_pairs),
        "agreement_rows": len(all_agreement),
        "reviewers": REVIEWERS,
        "descriptors": DESCRIPTORS,
        "status": "PASS",
        "claim_boundary": "Phase18J analyzes human reviewability labels, not identity labels.",
    }
    write_json(output_dir / "phase18j_reviewer_agreement_analysis_audit.json", audit)
    return audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet-root", type=Path, default=DEFAULT_PACKET_ROOT)
    parser.add_argument("--review-root", type=Path, default=DEFAULT_REVIEW_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = build_phase18j_reviewer_agreement_analysis(args.packet_root, args.review_root, args.output_dir)
    print("PASS phase18j reviewer agreement analysis")
    print(f"detail_rows={audit['detail_rows']}")
    print(f"majority_pair_rows={audit['majority_pair_rows']}")
    print(f"WROTE {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
