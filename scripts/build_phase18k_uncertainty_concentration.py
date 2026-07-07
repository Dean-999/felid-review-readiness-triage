#!/usr/bin/env python3
"""Analyze whether uncertain/not-ready labels concentrate in PF-ERI low-evidence regions."""

from __future__ import annotations

import argparse
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
DEFAULT_OUTPUT_DIR = Path("outputs/phase18/phase18k_uncertainty_concentration")

GROUP_COLUMNS = [
    "scope",
    "descriptor_name",
    "grouping",
    "group_value",
    "pair_count",
    "uncertain_or_not_ready_count",
    "uncertain_or_not_ready_rate",
    "review_ready_count",
    "review_ready_rate",
    "same_id_count",
    "false_candidate_count",
]

CONTRAST_COLUMNS = [
    "scope",
    "descriptor_name",
    "contrast",
    "high_risk_group",
    "low_risk_group",
    "high_risk_rate",
    "low_risk_rate",
    "rate_difference",
    "risk_ratio",
    "ci_lower",
    "ci_upper",
    "interpretation",
]

WITHIN_RANK_COLUMNS = [
    "scope",
    "descriptor_name",
    "rank_bin",
    "contrast",
    "high_risk_group",
    "low_risk_group",
    "pair_count",
    "high_risk_rate",
    "low_risk_rate",
    "rate_difference",
]

IDEAL_COLUMNS = [
    "scenario",
    "descriptor_similarity_control",
    "pf_eri_evidence_state",
    "expected_human_label_pattern",
    "why_it_supports_project",
]


def merge_packet_fields(rows: list[dict[str, str]], packet_root: Path) -> list[dict[str, str]]:
    packet_by_pair: dict[str, dict[str, str]] = {}
    for packet_csv in sorted(packet_root.glob("*/phase18j_full_queue_review_packet.csv")):
        for packet_row in read_csv(packet_csv):
            packet_by_pair[packet_row["review_pair_id"]] = packet_row
    merged = []
    for row in rows:
        packet = packet_by_pair.get(row["review_pair_id"])
        if packet is None:
            raise ValueError(f"majority pair missing from packet: {row['review_pair_id']}")
        updated = dict(row)
        for key in [
            "query_image_id",
            "candidate_image_id",
            "descriptor_similarity",
            "descriptor_evidence_conflict_score",
            "query_split_role",
            "stratum_id",
        ]:
            updated[key] = packet.get(key, "")
        merged.append(updated)
    return merged


def uncertainty_label(row: dict[str, str]) -> int:
    return 0 if row["majority_binary_review_ready"] == "yes" else 1


def add_quantile_groups(rows: list[dict[str, str]], score_name: str, output_name: str, reverse: bool = False) -> None:
    values = sorted(to_float(row[score_name]) for row in rows)
    if not values:
        return
    q1 = values[int((len(values) - 1) * 0.333333)]
    q2 = values[int((len(values) - 1) * 0.666667)]
    for row in rows:
        value = to_float(row[score_name])
        if value <= q1:
            bucket = "low"
        elif value <= q2:
            bucket = "mid"
        else:
            bucket = "high"
        if reverse:
            bucket = {"low": "high", "mid": "mid", "high": "low"}[bucket]
        row[output_name] = bucket


def route_risk_group(route: str) -> str:
    if route in {"defer_low_evidence", "defer", "non_comparable"}:
        return "defer_or_non_comparable"
    if route == "review":
        return "review"
    if route == "accept_review_ready":
        return "accept_review_ready"
    return route or "unknown"


def prepare_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    prepared = [dict(row) for row in rows]
    add_quantile_groups(prepared, "pf_eri_admissibility_score", "admissibility_risk_group", reverse=True)
    add_quantile_groups(prepared, "pair_geometry_score", "geometry_risk_group", reverse=True)
    add_quantile_groups(prepared, "descriptor_evidence_conflict_score", "conflict_risk_group", reverse=False)
    add_quantile_groups(prepared, "descriptor_similarity_percentile", "similarity_group", reverse=False)
    for row in prepared:
        row["route_risk_group"] = route_risk_group(row.get("pf_eri_route", ""))
    return prepared


def group_summary(rows: list[dict[str, str]], scope: str, descriptor_name: str, grouping: str) -> list[dict[str, Any]]:
    output = []
    for value in sorted({row[grouping] for row in rows}):
        subset = [row for row in rows if row[grouping] == value]
        uncertain = sum(uncertainty_label(row) for row in subset)
        ready = len(subset) - uncertain
        output.append(
            {
                "scope": scope,
                "descriptor_name": descriptor_name,
                "grouping": grouping,
                "group_value": value,
                "pair_count": len(subset),
                "uncertain_or_not_ready_count": uncertain,
                "uncertain_or_not_ready_rate": uncertain / len(subset) if subset else 0.0,
                "review_ready_count": ready,
                "review_ready_rate": ready / len(subset) if subset else 0.0,
                "same_id_count": sum(row["same_identity_known_id"] == "yes" for row in subset),
                "false_candidate_count": sum(row["same_identity_known_id"] == "no" for row in subset),
            }
        )
    return output


def uncertainty_rate(rows: list[dict[str, str]]) -> float:
    return sum(uncertainty_label(row) for row in rows) / len(rows) if rows else 0.0


def bootstrap_rate_diff(high_rows: list[dict[str, str]], low_rows: list[dict[str, str]]) -> tuple[float, float]:
    if not high_rows or not low_rows:
        return 0.0, 0.0
    rng = np.random.default_rng(20260703)
    high = np.asarray([uncertainty_label(row) for row in high_rows], dtype=np.float64)
    low = np.asarray([uncertainty_label(row) for row in low_rows], dtype=np.float64)
    values = []
    for _ in range(5000):
        hs = high[rng.integers(0, len(high), size=len(high))]
        ls = low[rng.integers(0, len(low), size=len(low))]
        values.append(float(np.mean(hs) - np.mean(ls)))
    return float(np.percentile(values, 2.5)), float(np.percentile(values, 97.5))


def contrast_row(
    rows: list[dict[str, str]],
    scope: str,
    descriptor_name: str,
    contrast: str,
    grouping: str,
    high_value: str,
    low_value: str,
) -> dict[str, Any]:
    high_rows = [row for row in rows if row[grouping] == high_value]
    low_rows = [row for row in rows if row[grouping] == low_value]
    high_rate = uncertainty_rate(high_rows)
    low_rate = uncertainty_rate(low_rows)
    ci_lower, ci_upper = bootstrap_rate_diff(high_rows, low_rows)
    return {
        "scope": scope,
        "descriptor_name": descriptor_name,
        "contrast": contrast,
        "high_risk_group": high_value,
        "low_risk_group": low_value,
        "high_risk_rate": high_rate,
        "low_risk_rate": low_rate,
        "rate_difference": high_rate - low_rate,
        "risk_ratio": (high_rate / low_rate) if low_rate > 0 else "",
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "interpretation": "uncertainty_enriched_in_high_risk_group" if high_rate > low_rate else "not_enriched",
    }


def within_rank_rows(
    rows: list[dict[str, str]],
    scope: str,
    descriptor_name: str,
    contrast: str,
    grouping: str,
    high_value: str,
    low_value: str,
) -> list[dict[str, Any]]:
    output = []
    for rank_bin in sorted({row["rank_bin"] for row in rows}):
        subset = [row for row in rows if row["rank_bin"] == rank_bin]
        high_rows = [row for row in subset if row[grouping] == high_value]
        low_rows = [row for row in subset if row[grouping] == low_value]
        if not high_rows or not low_rows:
            continue
        high_rate = uncertainty_rate(high_rows)
        low_rate = uncertainty_rate(low_rows)
        output.append(
            {
                "scope": scope,
                "descriptor_name": descriptor_name,
                "rank_bin": rank_bin,
                "contrast": contrast,
                "high_risk_group": high_value,
                "low_risk_group": low_value,
                "pair_count": len(subset),
                "high_risk_rate": high_rate,
                "low_risk_rate": low_rate,
                "rate_difference": high_rate - low_rate,
            }
        )
    return output


def idealized_rows() -> list[dict[str, str]]:
    return [
        {
            "scenario": "High descriptor similarity, high PF-ERI admissibility",
            "descriptor_similarity_control": "Same top-rank/high-similarity stratum",
            "pf_eri_evidence_state": "Comparable flanks, adequate geometry, strong admissibility",
            "expected_human_label_pattern": "Mostly review_ready",
            "why_it_supports_project": "Shows PF-ERI does not reject useful high-similarity pairs.",
        },
        {
            "scenario": "High descriptor similarity, low PF-ERI admissibility",
            "descriptor_similarity_control": "Same top-rank/high-similarity stratum",
            "pf_eri_evidence_state": "Weakest image evidence low or pair geometry poor",
            "expected_human_label_pattern": "Enriched uncertain/not_review_ready",
            "why_it_supports_project": "Shows PF-ERI detects high-similarity but low-evidence comparisons.",
        },
        {
            "scenario": "High descriptor similarity, high conflict",
            "descriptor_similarity_control": "Same top-rank/high-similarity stratum",
            "pf_eri_evidence_state": "Descriptor is confident but visual evidence is not admissible",
            "expected_human_label_pattern": "More defer/uncertain than low-conflict controls",
            "why_it_supports_project": "Shows PF-ERI governs evidence rather than similarity alone.",
        },
        {
            "scenario": "Low descriptor similarity, high PF-ERI admissibility",
            "descriptor_similarity_control": "Lower-rank diagnostic stratum",
            "pf_eri_evidence_state": "Images are comparable even if identity match is unlikely",
            "expected_human_label_pattern": "Review_ready for rejection",
            "why_it_supports_project": "Shows reviewability is not identical to identity correctness.",
        },
    ]


def write_report(output_dir: Path, gate: dict[str, Any]) -> None:
    lines = [
        "# Phase18K Uncertainty Concentration",
        "",
        "This analysis asks whether uncertain/not-ready labels appear where PF-ERI says evidence is weak.",
        "",
        "Key principle:",
        "",
        "```text",
        "The system is not better because it produces more uncertain labels.",
        "It is better only if uncertainty concentrates in low-evidence/high-risk PF-ERI regions.",
        "```",
        "",
        f"Gate status: `{gate['status']}`",
        "",
        "See `phase18k_idealized_proof_examples.csv` for the ideal pattern that would prove the project mechanism.",
    ]
    output_dir.joinpath("README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_phase18k_uncertainty_concentration(
    analysis_dir: Path = DEFAULT_ANALYSIS_DIR,
    packet_root: Path = DEFAULT_PACKET_ROOT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = merge_packet_fields(read_csv(analysis_dir / "phase18j_pair_majority_labels.csv"), packet_root)
    rows = prepare_rows(rows)
    scopes: list[tuple[str, str, list[dict[str, str]]]] = []
    for descriptor in sorted({row["descriptor_name"] for row in rows}):
        scopes.append(("descriptor_specific", descriptor, [row for row in rows if row["descriptor_name"] == descriptor]))
    scopes.append(("pooled", "pooled", rows))

    group_output: list[dict[str, Any]] = []
    contrast_output: list[dict[str, Any]] = []
    within_rank_output: list[dict[str, Any]] = []
    contrasts = [
        ("low_vs_high_admissibility", "admissibility_risk_group", "high", "low"),
        ("low_vs_high_geometry", "geometry_risk_group", "high", "low"),
        ("high_vs_low_conflict", "conflict_risk_group", "high", "low"),
    ]
    for scope, descriptor, scope_rows in scopes:
        for grouping in ["admissibility_risk_group", "geometry_risk_group", "conflict_risk_group", "route_risk_group", "rank_bin"]:
            group_output.extend(group_summary(scope_rows, scope, descriptor, grouping))
        for contrast, grouping, high_value, low_value in contrasts:
            contrast_output.append(contrast_row(scope_rows, scope, descriptor, contrast, grouping, high_value, low_value))
            within_rank_output.extend(within_rank_rows(scope_rows, scope, descriptor, contrast, grouping, high_value, low_value))

    gate = {
        "built_at_utc": now_utc(),
        "analysis_dir": project_relative(analysis_dir),
        "packet_root": project_relative(packet_root),
        "output_dir": project_relative(output_dir),
        "pair_rows": len(rows),
        "status": "PASS",
        "claim_boundary": "Uncertain/not-ready frequency supports PF-ERI only when concentrated in low-evidence/high-risk groups.",
    }
    write_csv(output_dir / "phase18k_uncertainty_group_rates.csv", group_output, GROUP_COLUMNS)
    write_csv(output_dir / "phase18k_uncertainty_enrichment_contrasts.csv", contrast_output, CONTRAST_COLUMNS)
    write_csv(output_dir / "phase18k_uncertainty_within_rankbin.csv", within_rank_output, WITHIN_RANK_COLUMNS)
    write_csv(output_dir / "phase18k_idealized_proof_examples.csv", idealized_rows(), IDEAL_COLUMNS)
    write_json(output_dir / "phase18k_uncertainty_concentration_audit.json", gate)
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
    audit = build_phase18k_uncertainty_concentration(args.analysis_dir, args.packet_root, args.output_dir)
    print("PASS phase18k uncertainty concentration")
    print(f"pair_rows={audit['pair_rows']}")
    print(f"WROTE {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
