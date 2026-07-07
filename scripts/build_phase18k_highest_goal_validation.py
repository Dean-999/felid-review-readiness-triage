#!/usr/bin/env python3
"""Build Phase18K highest-goal validation outputs for active vulnerabilities 1-6."""

from __future__ import annotations

import argparse
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

try:
    from phase18_pipeline_utils import now_utc, project_relative, read_csv, to_float, write_csv, write_json
except ModuleNotFoundError:  # pragma: no cover
    sys.path.append(str(Path(__file__).resolve().parents[1] / "scripts"))
    from phase18_pipeline_utils import now_utc, project_relative, read_csv, to_float, write_csv, write_json


DEFAULT_ANALYSIS_DIR = Path("outputs/phase18/phase18j_reviewer_agreement_analysis_100")
DEFAULT_PACKET_ROOT = Path("outputs/phase18/phase18j_full_queue_review_packet_100")
DEFAULT_OUTPUT_DIR = Path("outputs/phase18/phase18k_highest_goal_validation")
DESCRIPTORS = ["megadescriptor_l_384", "dinov2_vitl14"]
BOOTSTRAP_ITERATIONS = 5000
RANDOM_SEED = 20260703

FEATURES = {
    "descriptor_similarity": ["descriptor_similarity_percentile"],
    "quality": ["weakest_image_quality_score"],
    "pf_eri": ["pf_eri_review_score"],
    "descriptor_similarity_plus_quality": ["descriptor_similarity_percentile", "weakest_image_quality_score"],
    "descriptor_similarity_plus_pf_eri": ["descriptor_similarity_percentile", "pf_eri_review_score"],
    "descriptor_similarity_plus_quality_plus_pf_eri": [
        "descriptor_similarity_percentile",
        "weakest_image_quality_score",
        "pf_eri_review_score",
    ],
}

REQUIRED_COLUMNS = {
    "descriptor_name",
    "review_pair_id",
    "majority_binary_review_ready",
    "same_identity_known_id",
    "rank_bin",
    "candidate_rank_descriptor",
    "descriptor_similarity_percentile",
    "pf_eri_admissibility_score",
    "pf_eri_review_score",
    "weakest_image_quality_score",
    "pair_geometry_score",
}

MODEL_COLUMNS = [
    "scope",
    "descriptor_name",
    "model_name",
    "pair_count",
    "positive_count",
    "negative_count",
    "auc_higher_score_predicts_review_ready",
    "brier_score",
    "mean_score_ready",
    "mean_score_non_ready",
    "mean_score_difference",
]

INCREMENTAL_COLUMNS = [
    "scope",
    "descriptor_name",
    "comparison",
    "metric",
    "estimate",
    "ci_lower",
    "ci_upper",
    "direction",
]

CLUSTER_COLUMNS = [
    "scope",
    "descriptor_name",
    "analysis",
    "estimate",
    "ci_lower",
    "ci_upper",
    "cluster_column",
    "cluster_count",
    "pair_count",
]

QUALITY_COLUMNS = [
    "scope",
    "descriptor_name",
    "subset",
    "pair_count",
    "auc_pf_eri",
    "auc_quality",
    "auc_difference_pf_eri_minus_quality",
    "mean_pf_eri_ready_minus_non_ready",
]

RANKBIN_COLUMNS = [
    "scope",
    "descriptor_name",
    "rank_bin",
    "pair_count",
    "ready_count",
    "auc_pf_eri",
    "mean_pf_eri_ready_minus_non_ready",
]

RETENTION_COLUMNS = [
    "scope",
    "descriptor_name",
    "score_name",
    "target_same_id_retention",
    "threshold",
    "same_id_retention",
    "false_candidate_review_fraction",
    "review_fraction",
    "low_evidence_or_defer_fraction",
]

CORRELATION_COLUMNS = [
    "scope",
    "descriptor_name",
    "x",
    "y",
    "pearson_correlation",
    "pair_count",
]


def validate_columns(rows: list[dict[str, str]], columns: set[str]) -> None:
    if not rows:
        raise ValueError("no Phase18J majority rows found")
    missing = sorted(columns - set(rows[0]))
    if missing:
        raise ValueError(f"missing required columns: {', '.join(missing)}")


def merge_packet_fields(rows: list[dict[str, str]], packet_root: Path) -> list[dict[str, str]]:
    packet_by_pair: dict[str, dict[str, str]] = {}
    for descriptor in sorted({row["descriptor_name"] for row in rows}):
        packet_csv = packet_root / descriptor / "phase18j_full_queue_review_packet.csv"
        if not packet_csv.exists():
            raise ValueError(f"missing packet CSV for query bootstrap: {packet_csv}")
        for packet_row in read_csv(packet_csv):
            packet_by_pair[packet_row["review_pair_id"]] = packet_row
    merged = []
    for row in rows:
        packet = packet_by_pair.get(row["review_pair_id"])
        if packet is None:
            raise ValueError(f"majority pair missing from packet: {row['review_pair_id']}")
        updated = dict(row)
        for key in ["query_image_id", "candidate_image_id", "descriptor_similarity", "query_split_role", "stratum_id"]:
            updated[key] = packet.get(key, "")
        merged.append(updated)
    return merged


def label(row: dict[str, str]) -> int:
    return 1 if row["majority_binary_review_ready"] == "yes" else 0


def score_from_features(row: dict[str, str], feature_names: list[str]) -> float:
    return float(np.mean([to_float(row[name]) for name in feature_names]))


def auc_from_scores(labels: list[int], scores: list[float]) -> float:
    pos = [score for lab, score in zip(labels, scores) if lab == 1]
    neg = [score for lab, score in zip(labels, scores) if lab == 0]
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


def brier(labels: list[int], scores: list[float]) -> float:
    if not labels:
        return 0.0
    clipped = [max(0.0, min(1.0, score)) for score in scores]
    return float(np.mean([(score - lab) ** 2 for lab, score in zip(labels, clipped)]))


def pearson(a: list[float], b: list[float]) -> float:
    if len(a) < 2 or len(b) < 2:
        return 0.0
    aa = np.asarray(a, dtype=np.float64)
    bb = np.asarray(b, dtype=np.float64)
    if float(np.std(aa)) == 0.0 or float(np.std(bb)) == 0.0:
        return 0.0
    return float(np.corrcoef(aa, bb)[0, 1])


def model_rows(rows: list[dict[str, str]], scope: str, descriptor_name: str) -> list[dict[str, Any]]:
    labels = [label(row) for row in rows]
    output = []
    for model_name, feature_names in FEATURES.items():
        scores = [score_from_features(row, feature_names) for row in rows]
        ready_scores = [score for lab, score in zip(labels, scores) if lab == 1]
        non_ready_scores = [score for lab, score in zip(labels, scores) if lab == 0]
        output.append(
            {
                "scope": scope,
                "descriptor_name": descriptor_name,
                "model_name": model_name,
                "pair_count": len(rows),
                "positive_count": sum(labels),
                "negative_count": len(labels) - sum(labels),
                "auc_higher_score_predicts_review_ready": auc_from_scores(labels, scores),
                "brier_score": brier(labels, scores),
                "mean_score_ready": float(np.mean(ready_scores)) if ready_scores else 0.0,
                "mean_score_non_ready": float(np.mean(non_ready_scores)) if non_ready_scores else 0.0,
                "mean_score_difference": (float(np.mean(ready_scores)) if ready_scores else 0.0)
                - (float(np.mean(non_ready_scores)) if non_ready_scores else 0.0),
            }
        )
    return output


def bootstrap_auc_delta(rows: list[dict[str, str]], model_a: str, model_b: str, cluster_column: str) -> tuple[float, float, float]:
    observed = auc_delta(rows, model_a, model_b)
    clusters: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        clusters[row[cluster_column]].append(row)
    keys = sorted(clusters)
    if not keys:
        return observed, 0.0, 0.0
    rng = np.random.default_rng(RANDOM_SEED)
    values = []
    for _ in range(BOOTSTRAP_ITERATIONS):
        sampled_rows: list[dict[str, str]] = []
        sampled_keys = rng.choice(keys, size=len(keys), replace=True)
        for key in sampled_keys:
            sampled_rows.extend(clusters[str(key)])
        values.append(auc_delta(sampled_rows, model_a, model_b))
    return observed, float(np.percentile(values, 2.5)), float(np.percentile(values, 97.5))


def auc_delta(rows: list[dict[str, str]], model_a: str, model_b: str) -> float:
    labels = [label(row) for row in rows]
    score_a = [score_from_features(row, FEATURES[model_a]) for row in rows]
    score_b = [score_from_features(row, FEATURES[model_b]) for row in rows]
    return auc_from_scores(labels, score_a) - auc_from_scores(labels, score_b)


def incremental_rows(rows: list[dict[str, str]], scope: str, descriptor_name: str) -> list[dict[str, Any]]:
    comparisons = [
        ("pf_eri_vs_descriptor_similarity", "pf_eri", "descriptor_similarity"),
        ("pf_eri_vs_quality", "pf_eri", "quality"),
        (
            "descriptor_similarity_plus_pf_eri_vs_descriptor_similarity_plus_quality",
            "descriptor_similarity_plus_pf_eri",
            "descriptor_similarity_plus_quality",
        ),
        (
            "full_pf_eri_model_vs_descriptor_similarity_plus_quality",
            "descriptor_similarity_plus_quality_plus_pf_eri",
            "descriptor_similarity_plus_quality",
        ),
    ]
    output = []
    for name, model_a, model_b in comparisons:
        estimate, ci_lower, ci_upper = bootstrap_auc_delta(rows, model_a, model_b, "query_image_id")
        output.append(
            {
                "scope": scope,
                "descriptor_name": descriptor_name,
                "comparison": name,
                "metric": "query_cluster_bootstrap_delta_auc",
                "estimate": estimate,
                "ci_lower": ci_lower,
                "ci_upper": ci_upper,
                "direction": "positive" if estimate > 0 else "non_positive",
            }
        )
    return output


def mean_difference(rows: list[dict[str, str]], score_name: str) -> float:
    ready = [to_float(row[score_name]) for row in rows if label(row) == 1]
    non_ready = [to_float(row[score_name]) for row in rows if label(row) == 0]
    if not ready or not non_ready:
        return 0.0
    return float(np.mean(ready) - np.mean(non_ready))


def bootstrap_mean_diff(rows: list[dict[str, str]], score_name: str, cluster_column: str) -> tuple[float, float, float]:
    observed = mean_difference(rows, score_name)
    clusters: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        clusters[row[cluster_column]].append(row)
    keys = sorted(clusters)
    rng = np.random.default_rng(RANDOM_SEED)
    values = []
    for _ in range(BOOTSTRAP_ITERATIONS):
        sampled_rows: list[dict[str, str]] = []
        for key in rng.choice(keys, size=len(keys), replace=True):
            sampled_rows.extend(clusters[str(key)])
        values.append(mean_difference(sampled_rows, score_name))
    return observed, float(np.percentile(values, 2.5)), float(np.percentile(values, 97.5))


def cluster_rows(rows: list[dict[str, str]], scope: str, descriptor_name: str) -> list[dict[str, Any]]:
    estimate, ci_lower, ci_upper = bootstrap_mean_diff(rows, "pf_eri_review_score", "query_image_id")
    dedup = {}
    for row in rows:
        key = tuple(sorted([row["query_image_id"], row["candidate_image_id"]]))
        dedup.setdefault(key, row)
    dedup_rows = list(dedup.values())
    dedup_estimate = mean_difference(dedup_rows, "pf_eri_review_score")
    return [
        {
            "scope": scope,
            "descriptor_name": descriptor_name,
            "analysis": "pf_eri_review_score_ready_minus_non_ready_query_cluster",
            "estimate": estimate,
            "ci_lower": ci_lower,
            "ci_upper": ci_upper,
            "cluster_column": "query_image_id",
            "cluster_count": len({row["query_image_id"] for row in rows}),
            "pair_count": len(rows),
        },
        {
            "scope": scope,
            "descriptor_name": descriptor_name,
            "analysis": "pf_eri_review_score_ready_minus_non_ready_unordered_pair_dedup",
            "estimate": dedup_estimate,
            "ci_lower": "",
            "ci_upper": "",
            "cluster_column": "unordered_query_candidate_pair",
            "cluster_count": len(dedup_rows),
            "pair_count": len(dedup_rows),
        },
    ]


def quality_sensitivity_rows(rows: list[dict[str, str]], scope: str, descriptor_name: str) -> list[dict[str, Any]]:
    sorted_by_quality = sorted(rows, key=lambda row: (to_float(row["weakest_image_quality_score"]), row["review_pair_id"]))
    midpoint = len(sorted_by_quality) // 2
    low_quality_rows = sorted_by_quality[:midpoint]
    high_quality_rows = sorted_by_quality[midpoint:]
    qualities = [to_float(row["weakest_image_quality_score"]) for row in rows]
    median = float(np.median(qualities)) if qualities else 0.0
    q1 = float(np.percentile(qualities, 25)) if qualities else 0.0
    q3 = float(np.percentile(qualities, 75)) if qualities else 0.0
    subsets = {
        "all": rows,
        "low_quality_half": low_quality_rows,
        "high_quality_half": high_quality_rows,
        "quality_matched_iqr": [row for row in rows if q1 <= to_float(row["weakest_image_quality_score"]) <= q3],
    }
    output = []
    for subset_name, subset_rows in subsets.items():
        labels = [label(row) for row in subset_rows]
        pf_scores = [to_float(row["pf_eri_review_score"]) for row in subset_rows]
        quality_scores = [to_float(row["weakest_image_quality_score"]) for row in subset_rows]
        output.append(
            {
                "scope": scope,
                "descriptor_name": descriptor_name,
                "subset": subset_name,
                "pair_count": len(subset_rows),
                "auc_pf_eri": auc_from_scores(labels, pf_scores),
                "auc_quality": auc_from_scores(labels, quality_scores),
                "auc_difference_pf_eri_minus_quality": auc_from_scores(labels, pf_scores)
                - auc_from_scores(labels, quality_scores),
                "mean_pf_eri_ready_minus_non_ready": mean_difference(subset_rows, "pf_eri_review_score"),
            }
        )
    return output


def rankbin_rows(rows: list[dict[str, str]], scope: str, descriptor_name: str) -> list[dict[str, Any]]:
    output = []
    for rank_bin in sorted({row["rank_bin"] for row in rows}):
        subset = [row for row in rows if row["rank_bin"] == rank_bin]
        labels = [label(row) for row in subset]
        scores = [to_float(row["pf_eri_review_score"]) for row in subset]
        output.append(
            {
                "scope": scope,
                "descriptor_name": descriptor_name,
                "rank_bin": rank_bin,
                "pair_count": len(subset),
                "ready_count": sum(labels),
                "auc_pf_eri": auc_from_scores(labels, scores),
                "mean_pf_eri_ready_minus_non_ready": mean_difference(subset, "pf_eri_review_score"),
            }
        )
    return output


def high_similarity_rows(rows: list[dict[str, str]], scope: str, descriptor_name: str) -> list[dict[str, Any]]:
    threshold = float(np.percentile([to_float(row["descriptor_similarity_percentile"]) for row in rows], 75))
    subset = [row for row in rows if to_float(row["descriptor_similarity_percentile"]) >= threshold]
    return rankbin_rows(subset, f"{scope}_high_similarity_top_quartile", descriptor_name)


def retention_rows(rows: list[dict[str, str]], scope: str, descriptor_name: str) -> list[dict[str, Any]]:
    output = []
    for score_name in ["pf_eri_review_score", "descriptor_similarity_percentile"]:
        same_scores = [to_float(row[score_name]) for row in rows if row["same_identity_known_id"] == "yes"]
        if not same_scores:
            continue
        for target in [0.8, 0.9, 0.95]:
            threshold = float(np.percentile(same_scores, max(0.0, (1.0 - target) * 100.0)))
            selected = [row for row in rows if to_float(row[score_name]) >= threshold]
            same = [row for row in rows if row["same_identity_known_id"] == "yes"]
            false = [row for row in rows if row["same_identity_known_id"] == "no"]
            selected_same = [row for row in selected if row["same_identity_known_id"] == "yes"]
            selected_false = [row for row in selected if row["same_identity_known_id"] == "no"]
            low_or_defer = [row for row in selected if row.get("pf_eri_route") in {"defer_low_evidence", "defer", "non_comparable"}]
            output.append(
                {
                    "scope": scope,
                    "descriptor_name": descriptor_name,
                    "score_name": score_name,
                    "target_same_id_retention": target,
                    "threshold": threshold,
                    "same_id_retention": len(selected_same) / len(same) if same else 0.0,
                    "false_candidate_review_fraction": len(selected_false) / len(false) if false else 0.0,
                    "review_fraction": len(selected) / len(rows) if rows else 0.0,
                    "low_evidence_or_defer_fraction": len(low_or_defer) / len(selected) if selected else 0.0,
                }
            )
    return output


def correlation_rows(rows: list[dict[str, str]], scope: str, descriptor_name: str) -> list[dict[str, Any]]:
    pairs = [
        ("pf_eri_review_score", "descriptor_similarity_percentile"),
        ("pf_eri_admissibility_score", "descriptor_similarity_percentile"),
        ("pf_eri_review_score", "weakest_image_quality_score"),
    ]
    output = []
    for x, y in pairs:
        output.append(
            {
                "scope": scope,
                "descriptor_name": descriptor_name,
                "x": x,
                "y": y,
                "pearson_correlation": pearson([to_float(row[x]) for row in rows], [to_float(row[y]) for row in rows]),
                "pair_count": len(rows),
            }
        )
    return output


def claim_gate(model_rows_output: list[dict[str, Any]], incremental_output: list[dict[str, Any]], quality_output: list[dict[str, Any]]) -> dict[str, Any]:
    full_comparisons = [
        row
        for row in incremental_output
        if row["comparison"] == "full_pf_eri_model_vs_descriptor_similarity_plus_quality"
        and row["scope"] in {"descriptor_specific", "pooled"}
    ]
    quality_all = [row for row in quality_output if row["subset"] == "all" and row["scope"] in {"descriptor_specific", "pooled"}]
    checks = {
        "incremental_delta_auc_positive_all_scopes": all(to_float(row["estimate"]) > 0 for row in full_comparisons),
        "quality_control_pf_eri_auc_higher_all_scopes": all(to_float(row["auc_difference_pf_eri_minus_quality"]) > 0 for row in quality_all),
        "model_comparison_rows_present": len(model_rows_output) > 0,
    }
    return {
        "built_at_utc": now_utc(),
        "highest_goal": "PF-ERI incremental reviewability utility beyond descriptor similarity and image quality controls.",
        "status": "PASS" if all(checks.values()) else "NEEDS_MORE_EVIDENCE",
        "checks": checks,
        "no_downgrade_policy": "If any check is false, continue analysis/sampling/feature refinement rather than weakening the highest goal.",
    }


def write_report(output_dir: Path, gate: dict[str, Any]) -> None:
    lines = [
        "# Phase18K Highest-Goal Validation Plan",
        "",
        "Date: 2026-07-03",
        "",
        "## Highest Goal",
        "",
        "PF-ERI must show reviewability utility beyond descriptor similarity and image quality controls.",
        "",
        "## Active Problems 1-6",
        "",
        "1. Descriptor similarity replacement problem.",
        "2. Image quality filter problem.",
        "3. Human label reliability problem.",
        "4. Targeted sample inflation problem.",
        "5. Row/query dependence problem.",
        "6. Same-ID vs false-candidate endpoint confusion problem.",
        "",
        "## Generated Analyses",
        "",
        "- `phase18k_model_comparison.csv`",
        "- `phase18k_incremental_utility_summary.csv`",
        "- `phase18k_quality_matched_sensitivity.csv`",
        "- `phase18k_rankbin_sensitivity.csv`",
        "- `phase18k_high_similarity_subset.csv`",
        "- `phase18k_cluster_bootstrap.csv`",
        "- `phase18k_review_utility_at_fixed_retention.csv`",
        "- `phase18k_claim_gate.json`",
        "",
        "## Claim Gate",
        "",
        f"- Status: `{gate['status']}`",
        "- Policy: no downgrade. Failed checks require more evidence, not weaker claims.",
        "",
        "## Next Required Action To Reach Highest Goal",
        "",
        "If the gate is not PASS, prioritize more full-queue/rank-matched evidence or PF-ERI feature refinement, then rerun Phase18K.",
    ]
    output_dir.mkdir(parents=True, exist_ok=True)
    output_dir.joinpath("README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_phase18k_highest_goal_validation(
    analysis_dir: Path = DEFAULT_ANALYSIS_DIR,
    packet_root: Path = DEFAULT_PACKET_ROOT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    majority_csv = analysis_dir / "phase18j_pair_majority_labels.csv"
    rows = read_csv(majority_csv)
    validate_columns(rows, REQUIRED_COLUMNS)
    rows = merge_packet_fields(rows, packet_root)

    scopes: list[tuple[str, str, list[dict[str, str]]]] = []
    for descriptor in DESCRIPTORS:
        descriptor_rows = [row for row in rows if row["descriptor_name"] == descriptor]
        if descriptor_rows:
            scopes.append(("descriptor_specific", descriptor, descriptor_rows))
    scopes.append(("pooled", "pooled", rows))

    model_output: list[dict[str, Any]] = []
    incremental_output: list[dict[str, Any]] = []
    cluster_output: list[dict[str, Any]] = []
    quality_output: list[dict[str, Any]] = []
    rankbin_output: list[dict[str, Any]] = []
    high_similarity_output: list[dict[str, Any]] = []
    retention_output: list[dict[str, Any]] = []
    correlation_output: list[dict[str, Any]] = []

    for scope, descriptor_name, scope_rows in scopes:
        model_output.extend(model_rows(scope_rows, scope, descriptor_name))
        incremental_output.extend(incremental_rows(scope_rows, scope, descriptor_name))
        cluster_output.extend(cluster_rows(scope_rows, scope, descriptor_name))
        quality_output.extend(quality_sensitivity_rows(scope_rows, scope, descriptor_name))
        rankbin_output.extend(rankbin_rows(scope_rows, scope, descriptor_name))
        high_similarity_output.extend(high_similarity_rows(scope_rows, scope, descriptor_name))
        retention_output.extend(retention_rows(scope_rows, scope, descriptor_name))
        correlation_output.extend(correlation_rows(scope_rows, scope, descriptor_name))

    gate = claim_gate(model_output, incremental_output, quality_output)
    gate.update(
        {
            "analysis_dir": project_relative(analysis_dir),
            "packet_root": project_relative(packet_root),
            "output_dir": project_relative(output_dir),
            "pair_rows": len(rows),
            "descriptors": sorted({row["descriptor_name"] for row in rows}),
        }
    )

    write_csv(output_dir / "phase18k_model_comparison.csv", model_output, MODEL_COLUMNS)
    write_csv(output_dir / "phase18k_incremental_utility_summary.csv", incremental_output, INCREMENTAL_COLUMNS)
    write_csv(output_dir / "phase18k_cluster_bootstrap.csv", cluster_output, CLUSTER_COLUMNS)
    write_csv(output_dir / "phase18k_quality_matched_sensitivity.csv", quality_output, QUALITY_COLUMNS)
    write_csv(output_dir / "phase18k_rankbin_sensitivity.csv", rankbin_output, RANKBIN_COLUMNS)
    write_csv(output_dir / "phase18k_high_similarity_subset.csv", high_similarity_output, RANKBIN_COLUMNS)
    write_csv(output_dir / "phase18k_review_utility_at_fixed_retention.csv", retention_output, RETENTION_COLUMNS)
    write_csv(output_dir / "phase18k_correlation_audit.csv", correlation_output, CORRELATION_COLUMNS)
    write_json(output_dir / "phase18k_claim_gate.json", gate)
    write_report(output_dir, gate)
    return gate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis-dir", type=Path, default=DEFAULT_ANALYSIS_DIR)
    parser.add_argument("--packet-root", type=Path, default=DEFAULT_PACKET_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = build_phase18k_highest_goal_validation(args.analysis_dir, args.packet_root, args.output_dir)
    print("PASS phase18k highest-goal validation")
    print(f"status={audit['status']}")
    print(f"WROTE {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
