#!/usr/bin/env python3
"""Evaluate Phase18E conservative review-router policies."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

try:
    from scripts.phase18_pipeline_utils import (
        PHASE18D_FEATURES,
        PHASE18E_DIR,
        average_precision,
        now_utc,
        project_relative,
        read_csv,
        to_float,
        write_csv,
        write_json,
    )
except ImportError:  # pragma: no cover - direct script execution
    from phase18_pipeline_utils import (
        PHASE18D_FEATURES,
        PHASE18E_DIR,
        average_precision,
        now_utc,
        project_relative,
        read_csv,
        to_float,
        write_csv,
        write_json,
    )


METRIC_COLUMNS = [
    "policy_id",
    "query_split_role",
    "query_count",
    "mAP_at_k",
    "MRR_at_k",
    "top1_accuracy",
    "positive_present_top5_rate",
    "mean_false_candidates_top5",
    "mean_review_ready_pairs_top5",
    "claim_boundary",
]

THRESHOLD_COLUMNS = [
    "policy_id",
    "query_split_role",
    "threshold",
    "retained_pair_count",
    "positive_retention",
    "false_candidate_retention",
    "precision_retained",
]


def policy_score(row: dict[str, str], policy_id: str) -> float:
    descriptor = to_float(row["descriptor_similarity_percentile"])
    quality = to_float(row["weakest_image_quality_score"])
    admissibility = to_float(row["pf_eri_admissibility_score"])
    review = to_float(row["pf_eri_review_score"])
    conflict = to_float(row["descriptor_evidence_conflict_score"])
    if policy_id == "descriptor_only":
        return descriptor
    if policy_id == "quality_only":
        return quality
    if policy_id == "pf_eri_admissibility":
        return admissibility
    if policy_id == "pf_eri_review_router":
        return review
    if policy_id == "conflict_penalized_descriptor":
        return max(0.0, descriptor - 0.35 * conflict)
    raise ValueError(policy_id)


def evaluate_group(rows: list[dict[str, str]], policy_id: str, split_role: str) -> dict[str, Any]:
    by_query: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row["query_split_role"] == split_role:
            by_query[row["query_image_id"]].append(row)
    ap_values: list[float] = []
    rr_values: list[float] = []
    top1: list[int] = []
    top5_positive: list[int] = []
    false_top5: list[int] = []
    review_ready_top5: list[int] = []
    for query_rows in by_query.values():
        ranked = sorted(query_rows, key=lambda row: policy_score(row, policy_id), reverse=True)
        top = ranked[:5]
        relevance = [row["same_identity"] == "yes" for row in top]
        ap_values.append(average_precision(relevance))
        positives = [idx for idx, item in enumerate(relevance, start=1) if item]
        rr_values.append(1.0 / positives[0] if positives else 0.0)
        top1.append(int(bool(relevance) and relevance[0]))
        top5_positive.append(int(any(relevance)))
        false_top5.append(sum(1 for item in relevance if not item))
        review_ready_top5.append(sum(1 for row in top if row["pf_eri_route"] in {"accept_review_ready", "review"}))
    return {
        "policy_id": policy_id,
        "query_split_role": split_role,
        "query_count": len(by_query),
        "mAP_at_k": float(np.mean(ap_values)) if ap_values else 0.0,
        "MRR_at_k": float(np.mean(rr_values)) if rr_values else 0.0,
        "top1_accuracy": float(np.mean(top1)) if top1 else 0.0,
        "positive_present_top5_rate": float(np.mean(top5_positive)) if top5_positive else 0.0,
        "mean_false_candidates_top5": float(np.mean(false_top5)) if false_top5 else 0.0,
        "mean_review_ready_pairs_top5": float(np.mean(review_ready_top5)) if review_ready_top5 else 0.0,
        "claim_boundary": "No-training deterministic router evaluation on Phase18 pair features.",
    }


def threshold_rows(rows: list[dict[str, str]], policy_id: str, split_role: str) -> list[dict[str, Any]]:
    scoped = [row for row in rows if row["query_split_role"] == split_role]
    total_positive = sum(row["same_identity"] == "yes" for row in scoped)
    total_false = sum(row["same_identity"] == "no" for row in scoped)
    output = []
    for threshold in np.linspace(0.0, 1.0, 11):
        retained = [row for row in scoped if policy_score(row, policy_id) >= threshold]
        positives = sum(row["same_identity"] == "yes" for row in retained)
        false = sum(row["same_identity"] == "no" for row in retained)
        output.append(
            {
                "policy_id": policy_id,
                "query_split_role": split_role,
                "threshold": round(float(threshold), 2),
                "retained_pair_count": len(retained),
                "positive_retention": positives / total_positive if total_positive else 0.0,
                "false_candidate_retention": false / total_false if total_false else 0.0,
                "precision_retained": positives / len(retained) if retained else 0.0,
            }
        )
    return output


def build_phase18e(input_features: Path, output_dir: Path) -> dict[str, Any]:
    rows = read_csv(input_features)
    policies = [
        "descriptor_only",
        "quality_only",
        "pf_eri_admissibility",
        "pf_eri_review_router",
        "conflict_penalized_descriptor",
    ]
    metrics: list[dict[str, Any]] = []
    thresholds: list[dict[str, Any]] = []
    for policy_id in policies:
        for split_role in ["calibration", "evaluation"]:
            metrics.append(evaluate_group(rows, policy_id, split_role))
            thresholds.extend(threshold_rows(rows, policy_id, split_role))
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_csv = output_dir / "phase18e_review_router_metrics.csv"
    thresholds_csv = output_dir / "phase18e_review_router_threshold_curves.csv"
    write_csv(metrics_csv, metrics, METRIC_COLUMNS)
    write_csv(thresholds_csv, thresholds, THRESHOLD_COLUMNS)
    evaluation = [row for row in metrics if row["query_split_role"] == "evaluation"]
    best_by_map = max(evaluation, key=lambda row: row["mAP_at_k"]) if evaluation else {}
    audit = {
        "built_at_utc": now_utc(),
        "input_features": project_relative(input_features),
        "metrics_csv": project_relative(metrics_csv),
        "thresholds_csv": project_relative(thresholds_csv),
        "input_pair_rows": len(rows),
        "policy_count": len(policies),
        "metric_rows": len(metrics),
        "threshold_rows": len(thresholds),
        "best_evaluation_policy_by_mAP": best_by_map,
        "claim_boundary": "Router metrics are pair-level review-utility diagnostics, not final identity-assignment claims.",
    }
    write_json(output_dir / "phase18e_review_router_audit.json", audit)
    (output_dir / "README.md").write_text(
        "# Phase18E Review Router\n\n"
        "Evaluates deterministic no-training review-routing policies over Phase18D "
        "pair features. This is the first automated router gate, not a final "
        "scientific claim.\n",
        encoding="utf-8",
    )
    return audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-features", type=Path, default=PHASE18D_FEATURES)
    parser.add_argument("--output-dir", type=Path, default=PHASE18E_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = build_phase18e(args.input_features, args.output_dir)
    print("PASS phase18e review router")
    print(f"metric_rows={audit['metric_rows']}")
    print(f"WROTE {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
