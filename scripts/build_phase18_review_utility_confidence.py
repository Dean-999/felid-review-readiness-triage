#!/usr/bin/env python3
"""Build query-level paired bootstrap confidence summaries for Phase18E policies."""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

try:
    from scripts.build_phase18e_review_router import policy_score
    from scripts.phase18_pipeline_utils import average_precision, now_utc, project_relative, read_csv, write_csv, write_json
except ImportError:  # pragma: no cover - direct script execution
    from build_phase18e_review_router import policy_score
    from phase18_pipeline_utils import average_precision, now_utc, project_relative, read_csv, write_csv, write_json


COMPARISONS = [
    ("pf_eri_review_router", "descriptor_only"),
    ("conflict_penalized_descriptor", "descriptor_only"),
    ("pf_eri_admissibility", "quality_only"),
]

METRICS = [
    "average_precision_top5",
    "reciprocal_rank_top5",
    "top1_accuracy",
    "positive_present_top5",
    "false_candidates_top5",
]

OUTPUT_COLUMNS = [
    "query_split_role",
    "comparison",
    "metric",
    "estimate_delta",
    "ci_lower",
    "ci_upper",
    "direction",
    "query_count",
    "bootstrap_iterations",
    "claim_boundary",
]


def per_query_metrics(query_rows: list[dict[str, str]], policy_id: str) -> dict[str, float]:
    ranked = sorted(query_rows, key=lambda row: policy_score(row, policy_id), reverse=True)
    top = ranked[:5]
    relevance = [row["same_identity"] == "yes" for row in top]
    positives = [idx for idx, item in enumerate(relevance, start=1) if item]
    return {
        "average_precision_top5": average_precision(relevance),
        "reciprocal_rank_top5": 1.0 / positives[0] if positives else 0.0,
        "top1_accuracy": float(bool(relevance) and relevance[0]),
        "positive_present_top5": float(any(relevance)),
        "false_candidates_top5": float(sum(1 for item in relevance if not item)),
    }


def direction_for(metric: str, estimate: float, ci_lower: float, ci_upper: float) -> str:
    higher_is_better = metric != "false_candidates_top5"
    if ci_lower <= 0.0 <= ci_upper:
        return "mixed_or_uncertain"
    if higher_is_better:
        return "improves_review_utility" if estimate > 0 else "worse_than_control"
    return "improves_review_utility" if estimate < 0 else "worse_than_control"


def bootstrap_ci(values: np.ndarray, iterations: int, seed: int) -> tuple[float, float]:
    if len(values) == 0:
        return 0.0, 0.0
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(values), size=(iterations, len(values)))
    means = values[indices].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def build_phase18_review_utility_confidence(
    input_features: Path,
    output_dir: Path,
    iterations: int = 5000,
    seed: int = 20260702,
) -> dict[str, Any]:
    rows = read_csv(input_features)
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(row["query_split_role"], row["query_image_id"])].append(row)

    output_rows: list[dict[str, Any]] = []
    for split_role in ["calibration", "evaluation"]:
        query_groups = [items for (role, _), items in grouped.items() if role == split_role]
        for policy_id, control_id in COMPARISONS:
            policy_values = [per_query_metrics(items, policy_id) for items in query_groups]
            control_values = [per_query_metrics(items, control_id) for items in query_groups]
            for metric in METRICS:
                deltas = np.asarray(
                    [policy[metric] - control[metric] for policy, control in zip(policy_values, control_values)],
                    dtype=np.float64,
                )
                estimate = float(deltas.mean()) if len(deltas) else 0.0
                ci_lower, ci_upper = bootstrap_ci(deltas, iterations, seed)
                output_rows.append(
                    {
                        "query_split_role": split_role,
                        "comparison": f"{policy_id}_vs_{control_id}",
                        "metric": metric,
                        "estimate_delta": estimate,
                        "ci_lower": ci_lower,
                        "ci_upper": ci_upper,
                        "direction": direction_for(metric, estimate, ci_lower, ci_upper),
                        "query_count": len(query_groups),
                        "bootstrap_iterations": iterations,
                        "claim_boundary": (
                            "Query-level paired bootstrap for pair-level review utility; "
                            "not a descriptor-replacement claim."
                        ),
                    }
                )

    output_dir.mkdir(parents=True, exist_ok=True)
    output_csv = output_dir / "phase18_review_utility_bootstrap_confidence.csv"
    write_csv(output_csv, output_rows, OUTPUT_COLUMNS)
    evaluation_rows = [row for row in output_rows if row["query_split_role"] == "evaluation"]
    supported = [
        row for row in evaluation_rows
        if row["direction"] == "improves_review_utility"
        and row["comparison"] in {
            "pf_eri_review_router_vs_descriptor_only",
            "conflict_penalized_descriptor_vs_descriptor_only",
        }
    ]
    status = (
        "SUPPORTED_PAIR_LEVEL_REVIEW_UTILITY"
        if supported
        else "MIXED_PAIR_LEVEL_REVIEW_UTILITY"
        if evaluation_rows
        else "NOT_SUPPORTED_UNDER_STRONG_DESCRIPTOR"
    )
    audit = {
        "built_at_utc": now_utc(),
        "input_features": project_relative(input_features),
        "confidence_csv": project_relative(output_csv),
        "comparison_count": len(COMPARISONS),
        "metric_count": len(METRICS),
        "row_count": len(output_rows),
        "bootstrap_iterations": iterations,
        "seed": seed,
        "pair_level_review_utility_status": status,
        "claim_boundary": (
            "Confidence intervals evaluate pair-level review utility under a fixed "
            "candidate queue. They do not claim automatic identity assignment."
        ),
    }
    write_json(output_dir / "phase18_review_utility_confidence_audit.json", audit)
    return audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-features", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--iterations", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=20260702)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = build_phase18_review_utility_confidence(
        input_features=args.input_features,
        output_dir=args.output_dir,
        iterations=args.iterations,
        seed=args.seed,
    )
    print("PASS phase18 review utility confidence")
    print(f"row_count={audit['row_count']}")
    print(f"status={audit['pair_level_review_utility_status']}")
    print(f"WROTE {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
