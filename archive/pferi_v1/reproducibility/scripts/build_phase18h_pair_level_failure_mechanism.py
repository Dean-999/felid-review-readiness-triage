#!/usr/bin/env python3
"""Build Phase18H pair-level failure mechanism diagnostics."""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

try:
    from scripts.build_phase18e_review_router import policy_score
    from scripts.phase18_pipeline_utils import now_utc, project_relative, read_csv, to_float, write_csv, write_json
except ImportError:  # pragma: no cover - direct script execution
    from build_phase18e_review_router import policy_score
    from phase18_pipeline_utils import now_utc, project_relative, read_csv, to_float, write_csv, write_json


DEFAULT_OUTPUT_ROOT = Path("outputs/phase18/phase18h_pair_level_failure_mechanism")
RANDOM_SEED = 20260702
BOOTSTRAP_ITERATIONS = 5000

ENRICHMENT_COLUMNS = [
    "descriptor_name",
    "query_split_role",
    "signal_id",
    "population",
    "pair_count",
    "false_count",
    "false_rate",
    "odds_ratio_vs_signal_absent",
    "risk_difference_vs_signal_absent",
    "risk_difference_ci_lower",
    "risk_difference_ci_upper",
    "claim_boundary",
]

OPERATING_COLUMNS = [
    "descriptor_name",
    "query_split_role",
    "policy_id",
    "target_positive_retention",
    "threshold",
    "retained_pair_count",
    "positive_retention",
    "false_candidate_retention",
    "false_removed_fraction",
    "precision_retained",
    "claim_boundary",
]

SAMPLE_COLUMNS = [
    "descriptor_name",
    "sample_group",
    "pair_id",
    "query_image_id",
    "candidate_image_id",
    "same_identity",
    "candidate_rank_descriptor",
    "descriptor_similarity",
    "descriptor_similarity_percentile",
    "descriptor_evidence_conflict_score",
    "pf_eri_admissibility_score",
    "pf_eri_review_score",
    "pf_eri_route",
    "weakest_image_quality_score",
    "pair_geometry_score",
    "interpretation",
    "claim_boundary",
]


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    return float(np.percentile(np.asarray(values, dtype=np.float64), pct))


def signal_flags(row: dict[str, str], cutoffs: dict[str, float]) -> dict[str, bool]:
    similarity_pct = to_float(row["descriptor_similarity_percentile"])
    conflict = to_float(row["descriptor_evidence_conflict_score"])
    admissibility = to_float(row["pf_eri_admissibility_score"])
    quality = to_float(row["weakest_image_quality_score"])
    return {
        "high_similarity": similarity_pct >= 0.90,
        "high_conflict": conflict >= cutoffs["conflict_p90"],
        "low_admissibility": admissibility <= cutoffs["admissibility_p10"],
        "low_quality": quality <= cutoffs["quality_p10"],
        "high_similarity_high_conflict": similarity_pct >= 0.90 and conflict >= cutoffs["conflict_p90"],
        "high_similarity_low_admissibility": similarity_pct >= 0.90 and admissibility <= cutoffs["admissibility_p10"],
    }


def odds_ratio(signal_false: int, signal_true: int, absent_false: int, absent_true: int) -> float:
    # Haldane-Anscombe correction keeps sparse diagnostic cells finite.
    return float(((signal_false + 0.5) * (absent_true + 0.5)) / ((signal_true + 0.5) * (absent_false + 0.5)))


def bootstrap_risk_difference(signal_values: list[bool], absent_values: list[bool]) -> tuple[float, float]:
    if not signal_values or not absent_values:
        return 0.0, 0.0
    rng = np.random.default_rng(RANDOM_SEED)
    signal = np.asarray(signal_values, dtype=np.float64)
    absent = np.asarray(absent_values, dtype=np.float64)
    signal_idx = rng.integers(0, len(signal), size=(BOOTSTRAP_ITERATIONS, len(signal)))
    absent_idx = rng.integers(0, len(absent), size=(BOOTSTRAP_ITERATIONS, len(absent)))
    diffs = signal[signal_idx].mean(axis=1) - absent[absent_idx].mean(axis=1)
    return float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))


def build_enrichment_rows(rows: list[dict[str, str]], descriptor_name: str) -> list[dict[str, Any]]:
    cutoffs = {
        "conflict_p90": percentile([to_float(row["descriptor_evidence_conflict_score"]) for row in rows], 90),
        "admissibility_p10": percentile([to_float(row["pf_eri_admissibility_score"]) for row in rows], 10),
        "quality_p10": percentile([to_float(row["weakest_image_quality_score"]) for row in rows], 10),
    }
    output: list[dict[str, Any]] = []
    for split_role in ["calibration", "evaluation"]:
        scoped = [row for row in rows if row["query_split_role"] == split_role]
        flags_by_row = [(row, signal_flags(row, cutoffs)) for row in scoped]
        for signal_id in [
            "high_similarity",
            "high_conflict",
            "low_admissibility",
            "low_quality",
            "high_similarity_high_conflict",
            "high_similarity_low_admissibility",
        ]:
            signal_rows = [row for row, flags in flags_by_row if flags[signal_id]]
            absent_rows = [row for row, flags in flags_by_row if not flags[signal_id]]
            signal_false = sum(row["same_identity"] == "no" for row in signal_rows)
            signal_true = sum(row["same_identity"] == "yes" for row in signal_rows)
            absent_false = sum(row["same_identity"] == "no" for row in absent_rows)
            absent_true = sum(row["same_identity"] == "yes" for row in absent_rows)
            signal_false_values = [row["same_identity"] == "no" for row in signal_rows]
            absent_false_values = [row["same_identity"] == "no" for row in absent_rows]
            signal_rate = signal_false / len(signal_rows) if signal_rows else 0.0
            absent_rate = absent_false / len(absent_rows) if absent_rows else 0.0
            ci_lower, ci_upper = bootstrap_risk_difference(signal_false_values, absent_false_values)
            output.append(
                {
                    "descriptor_name": descriptor_name,
                    "query_split_role": split_role,
                    "signal_id": signal_id,
                    "population": "signal_present",
                    "pair_count": len(signal_rows),
                    "false_count": signal_false,
                    "false_rate": signal_rate,
                    "odds_ratio_vs_signal_absent": odds_ratio(signal_false, signal_true, absent_false, absent_true),
                    "risk_difference_vs_signal_absent": signal_rate - absent_rate,
                    "risk_difference_ci_lower": ci_lower,
                    "risk_difference_ci_upper": ci_upper,
                    "claim_boundary": "Mechanism diagnostic only; not an automatic identity-assignment claim.",
                }
            )
    return output


def operating_row(
    rows: list[dict[str, str]],
    descriptor_name: str,
    split_role: str,
    policy_id: str,
    target_positive_retention: float,
) -> dict[str, Any]:
    scoped = [row for row in rows if row["query_split_role"] == split_role]
    total_positive = sum(row["same_identity"] == "yes" for row in scoped)
    total_false = sum(row["same_identity"] == "no" for row in scoped)
    scored = sorted(
        [(policy_score(row, policy_id), row) for row in scoped],
        key=lambda item: item[0],
        reverse=True,
    )
    positives_seen = 0
    threshold = 1.0
    retained: list[dict[str, str]] = []
    for score, row in scored:
        retained.append(row)
        if row["same_identity"] == "yes":
            positives_seen += 1
        threshold = score
        if total_positive and positives_seen / total_positive >= target_positive_retention:
            break
    positives = sum(row["same_identity"] == "yes" for row in retained)
    false = sum(row["same_identity"] == "no" for row in retained)
    false_retention = false / total_false if total_false else 0.0
    return {
        "descriptor_name": descriptor_name,
        "query_split_role": split_role,
        "policy_id": policy_id,
        "target_positive_retention": target_positive_retention,
        "threshold": threshold,
        "retained_pair_count": len(retained),
        "positive_retention": positives / total_positive if total_positive else 0.0,
        "false_candidate_retention": false_retention,
        "false_removed_fraction": 1.0 - false_retention,
        "precision_retained": positives / len(retained) if retained else 0.0,
        "claim_boundary": "Operating point fixes positive retention and measures false-candidate burden.",
    }


def build_operating_rows(rows: list[dict[str, str]], descriptor_name: str) -> list[dict[str, Any]]:
    output = []
    for split_role in ["calibration", "evaluation"]:
        for policy_id in ["descriptor_only", "pf_eri_review_router", "conflict_penalized_descriptor"]:
            for target in [0.90, 0.95, 0.99]:
                output.append(operating_row(rows, descriptor_name, split_role, policy_id, target))
    return output


def sample_rows(rows: list[dict[str, str]], descriptor_name: str, limit: int) -> list[dict[str, Any]]:
    evaluation = [row for row in rows if row["query_split_role"] == "evaluation"]
    high_conflict_false = sorted(
        [
            row for row in evaluation
            if row["same_identity"] == "no" and to_float(row["descriptor_similarity_percentile"]) >= 0.90
        ],
        key=lambda row: (
            to_float(row["descriptor_evidence_conflict_score"]),
            to_float(row["descriptor_similarity_percentile"]),
        ),
        reverse=True,
    )[:limit]
    matched_controls = sorted(
        [
            row for row in evaluation
            if row["same_identity"] == "yes" and to_float(row["descriptor_similarity_percentile"]) >= 0.90
        ],
        key=lambda row: (
            to_float(row["pf_eri_review_score"]),
            to_float(row["descriptor_similarity_percentile"]),
        ),
        reverse=True,
    )[:limit]
    output = []
    for group, items, interpretation in [
        ("high_similarity_false_high_conflict", high_conflict_false, "High-similarity false candidate prioritized for mechanism review."),
        ("high_similarity_same_identity_control", matched_controls, "High-similarity same-ID control for matched review context."),
    ]:
        for row in items:
            output.append(
                {
                    "descriptor_name": descriptor_name,
                    "sample_group": group,
                    "pair_id": row["pair_id"],
                    "query_image_id": row["query_image_id"],
                    "candidate_image_id": row["candidate_image_id"],
                    "same_identity": row["same_identity"],
                    "candidate_rank_descriptor": row["candidate_rank_descriptor"],
                    "descriptor_similarity": row["descriptor_similarity"],
                    "descriptor_similarity_percentile": row["descriptor_similarity_percentile"],
                    "descriptor_evidence_conflict_score": row["descriptor_evidence_conflict_score"],
                    "pf_eri_admissibility_score": row["pf_eri_admissibility_score"],
                    "pf_eri_review_score": row["pf_eri_review_score"],
                    "pf_eri_route": row["pf_eri_route"],
                    "weakest_image_quality_score": row["weakest_image_quality_score"],
                    "pair_geometry_score": row["pair_geometry_score"],
                    "interpretation": interpretation,
                    "claim_boundary": "Failure sample for review and explanation only; not a new label source.",
                }
            )
    return output


def build_phase18h_pair_level_failure_mechanism(
    descriptor_name: str,
    input_features: Path,
    output_dir: Path,
    sample_limit: int = 50,
) -> dict[str, Any]:
    rows = read_csv(input_features)
    if not rows:
        raise ValueError("0 Phase18D feature rows")
    output_dir.mkdir(parents=True, exist_ok=True)
    enrichment = build_enrichment_rows(rows, descriptor_name)
    operating = build_operating_rows(rows, descriptor_name)
    samples = sample_rows(rows, descriptor_name, sample_limit)

    enrichment_csv = output_dir / "phase18h_conflict_enrichment.csv"
    operating_csv = output_dir / "phase18h_fixed_positive_retention_operating_points.csv"
    sample_csv = output_dir / "phase18h_failure_case_sample.csv"
    write_csv(enrichment_csv, enrichment, ENRICHMENT_COLUMNS)
    write_csv(operating_csv, operating, OPERATING_COLUMNS)
    write_csv(sample_csv, samples, SAMPLE_COLUMNS)

    evaluation_enrichment = [
        row for row in enrichment
        if row["query_split_role"] == "evaluation"
        and row["signal_id"] in {"high_conflict", "high_similarity_high_conflict", "high_similarity_low_admissibility"}
    ]
    false_risk_signals = [
        row for row in enrichment
        if row["query_split_role"] == "evaluation" and float(row["risk_difference_vs_signal_absent"]) > 0.0
    ]
    strongest_risk = max(false_risk_signals, key=lambda row: float(row["risk_difference_vs_signal_absent"])) if false_risk_signals else {}
    strongest_abs = max(evaluation_enrichment, key=lambda row: abs(float(row["risk_difference_vs_signal_absent"])))
    audit = {
        "built_at_utc": now_utc(),
        "descriptor_name": descriptor_name,
        "input_features": project_relative(input_features),
        "enrichment_csv": project_relative(enrichment_csv),
        "operating_csv": project_relative(operating_csv),
        "sample_csv": project_relative(sample_csv),
        "input_pair_rows": len(rows),
        "enrichment_rows": len(enrichment),
        "operating_rows": len(operating),
        "sample_rows": len(samples),
        "bootstrap_iterations": BOOTSTRAP_ITERATIONS,
        "strongest_evaluation_false_risk_signal": strongest_risk,
        "strongest_absolute_evaluation_signal": strongest_abs,
        "status": "PASS",
        "claim_boundary": (
            "Phase18H tests pair-level failure mechanisms in strong descriptor "
            "queues. It supports explanation and review design, not automatic ID."
        ),
    }
    write_json(output_dir / "phase18h_pair_level_failure_mechanism_audit.json", audit)
    (output_dir / "README.md").write_text(
        f"# Phase18H Pair-Level Failure Mechanism: {descriptor_name}\n\n"
        "Mechanism diagnostics for conflict enrichment, fixed positive-retention "
        "operating points, and representative failure/control samples.\n",
        encoding="utf-8",
    )
    return audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--descriptor-name", required=True)
    parser.add_argument("--input-features", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--sample-limit", type=int, default=50)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir or DEFAULT_OUTPUT_ROOT / args.descriptor_name
    audit = build_phase18h_pair_level_failure_mechanism(
        descriptor_name=args.descriptor_name,
        input_features=args.input_features,
        output_dir=output_dir,
        sample_limit=args.sample_limit,
    )
    print("PASS phase18h pair-level failure mechanism")
    print(f"descriptor_name={audit['descriptor_name']}")
    print(f"input_pair_rows={audit['input_pair_rows']}")
    print(f"sample_rows={audit['sample_rows']}")
    print(f"WROTE {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
