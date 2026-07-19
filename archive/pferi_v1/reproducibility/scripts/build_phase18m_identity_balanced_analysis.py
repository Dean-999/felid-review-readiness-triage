#!/usr/bin/env python3
"""Analyze Phase18M identity-balanced descriptor-controlled review labels."""

from __future__ import annotations

import argparse
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

try:
    from phase18_pipeline_utils import now_utc, project_relative, read_csv, write_csv, write_json
except ModuleNotFoundError:  # pragma: no cover
    sys.path.append(str(Path(__file__).resolve().parents[1] / "scripts"))
    from phase18_pipeline_utils import now_utc, project_relative, read_csv, write_csv, write_json


DEFAULT_PACKET_ROOT = Path("outputs/phase18/phase18m_identity_balanced_review_packet")
DEFAULT_REVIEW_ROOT = Path("outputs/phase18/phase18m_streamlit_review")
DEFAULT_OUTPUT_DIR = Path("outputs/phase18/phase18m_identity_balanced_analysis")
DESCRIPTORS = ["megadescriptor_l_384", "dinov2_vitl14"]
REVIEWERS = ["reviewer1", "reviewer2", "reviewer3"]
BOOTSTRAP_ITERATIONS = 5000
RANDOM_SEED = 20260704

DETAIL_COLUMNS = [
    "descriptor_name",
    "review_pair_id",
    "reviewer_id",
    "identity_stratum",
    "evidence_group",
    "binary_not_ready_or_uncertain",
    "reviewability_decision",
    "not_ready_reason",
    "match_group_id",
    "same_identity_known_id",
    "rank_bin",
    "descriptor_similarity_percentile",
    "similarity_match_delta",
    "pf_eri_admissibility_score",
    "pair_geometry_score",
]

MAJORITY_COLUMNS = [
    "descriptor_name",
    "review_pair_id",
    "identity_stratum",
    "evidence_group",
    "majority_decision",
    "majority_binary_not_ready_or_uncertain",
    "unanimous_decision",
    "decision_votes",
    "reason_votes",
    "match_group_id",
    "same_identity_known_id",
    "rank_bin",
    "descriptor_similarity_percentile",
    "similarity_match_delta",
    "pf_eri_admissibility_score",
    "pair_geometry_score",
]

SUMMARY_COLUMNS = [
    "scope",
    "descriptor_name",
    "identity_stratum",
    "label_scope",
    "high_pair_count",
    "low_pair_count",
    "high_uncertain_or_not_ready_rate",
    "low_uncertain_or_not_ready_rate",
    "risk_difference_low_minus_high",
    "risk_ratio_low_over_high",
    "ci_lower",
    "ci_upper",
    "fisher_exact_p_two_sided",
    "odds_ratio",
    "check_pass",
]

MATCHED_COLUMNS = [
    "descriptor_name",
    "identity_stratum",
    "match_group_id",
    "high_uncertain_or_not_ready",
    "low_uncertain_or_not_ready",
    "matched_difference_low_minus_high",
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

GATE_COLUMNS = ["check_name", "status", "detail"]


def binary_uncertain(decision: str) -> int:
    return 0 if decision == "review_ready" else 1


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


def fisher_exact_two_sided(a: int, b: int, c: int, d: int) -> tuple[float, float]:
    row1 = a + b
    row2 = c + d
    col1 = a + c
    total = row1 + row2

    def hypergeom_probability(x: int) -> float:
        return math.comb(col1, x) * math.comb(total - col1, row1 - x) / math.comb(total, row1)

    observed = hypergeom_probability(a)
    min_x = max(0, row1 - (total - col1))
    max_x = min(row1, col1)
    p_value = sum(
        probability
        for x in range(min_x, max_x + 1)
        for probability in [hypergeom_probability(x)]
        if probability <= observed + 1e-12
    )
    odds = ((a + 0.5) * (d + 0.5)) / ((b + 0.5) * (c + 0.5))
    return float(odds), min(1.0, float(p_value))


def bootstrap_rate_diff(high_values: list[int], low_values: list[int]) -> tuple[float, float]:
    if not high_values or not low_values:
        return 0.0, 0.0
    rng = np.random.default_rng(RANDOM_SEED)
    high = np.asarray(high_values, dtype=np.float64)
    low = np.asarray(low_values, dtype=np.float64)
    values = []
    for _ in range(BOOTSTRAP_ITERATIONS):
        hs = high[rng.integers(0, len(high), size=len(high))]
        ls = low[rng.integers(0, len(low), size=len(low))]
        values.append(float(np.mean(ls) - np.mean(hs)))
    return float(np.percentile(values, 2.5)), float(np.percentile(values, 97.5))


def load_descriptor(descriptor_name: str, packet_root: Path, review_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    full = {
        row["review_pair_id"]: row
        for row in read_csv(packet_root / descriptor_name / "phase18m_identity_balanced_review_packet.csv")
    }
    detail = []
    by_pair: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for reviewer_id in REVIEWERS:
        working_csv = review_root / reviewer_id / descriptor_name / "phase18m_identity_balanced_review_working.csv"
        if not working_csv.exists():
            raise ValueError(f"missing reviewer working CSV: {working_csv}")
        for row in read_csv(working_csv):
            pair_id = row["review_pair_id"]
            source = full[pair_id]
            decision = row["reviewability_decision"]
            if decision not in {"review_ready", "not_review_ready", "uncertain"}:
                raise ValueError(f"incomplete label: {working_csv} {pair_id}")
            record = {
                "descriptor_name": descriptor_name,
                "review_pair_id": pair_id,
                "reviewer_id": reviewer_id,
                "identity_stratum": source["identity_stratum"],
                "evidence_group": source["evidence_group"],
                "binary_not_ready_or_uncertain": binary_uncertain(decision),
                "reviewability_decision": decision,
                "not_ready_reason": row["not_ready_reason"],
                "match_group_id": source["match_group_id"],
                "same_identity_known_id": source["same_identity_known_id"],
                "rank_bin": source["rank_bin"],
                "descriptor_similarity_percentile": source["descriptor_similarity_percentile"],
                "similarity_match_delta": source["similarity_match_delta"],
                "pf_eri_admissibility_score": source["pf_eri_admissibility_score"],
                "pair_geometry_score": source["pair_geometry_score"],
            }
            detail.append(record)
            by_pair[pair_id].append(record)

    majority = []
    for pair_id, votes in sorted(by_pair.items()):
        source = full[pair_id]
        decisions = [vote["reviewability_decision"] for vote in votes]
        reasons = [vote["not_ready_reason"] for vote in votes if vote["not_ready_reason"]]
        decision_counts = Counter(decisions)
        reason_counts = Counter(reasons)
        majority_decision = decision_counts.most_common(1)[0][0]
        majority.append(
            {
                "descriptor_name": descriptor_name,
                "review_pair_id": pair_id,
                "identity_stratum": source["identity_stratum"],
                "evidence_group": source["evidence_group"],
                "majority_decision": majority_decision,
                "majority_binary_not_ready_or_uncertain": binary_uncertain(majority_decision),
                "unanimous_decision": "yes" if len(decision_counts) == 1 else "no",
                "decision_votes": ";".join(f"{key}:{value}" for key, value in sorted(decision_counts.items())),
                "reason_votes": ";".join(f"{key}:{value}" for key, value in sorted(reason_counts.items())),
                "match_group_id": source["match_group_id"],
                "same_identity_known_id": source["same_identity_known_id"],
                "rank_bin": source["rank_bin"],
                "descriptor_similarity_percentile": source["descriptor_similarity_percentile"],
                "similarity_match_delta": source["similarity_match_delta"],
                "pf_eri_admissibility_score": source["pf_eri_admissibility_score"],
                "pair_geometry_score": source["pair_geometry_score"],
            }
        )
    return detail, majority


def summary_row(rows: list[dict[str, Any]], scope: str, descriptor_name: str, identity_stratum: str, label_scope: str, value_column: str) -> dict[str, Any]:
    high = [int(row[value_column]) for row in rows if row["evidence_group"] == "high_admissibility"]
    low = [int(row[value_column]) for row in rows if row["evidence_group"] == "low_admissibility"]
    high_rate = sum(high) / len(high) if high else 0.0
    low_rate = sum(low) / len(low) if low else 0.0
    ci_lower, ci_upper = bootstrap_rate_diff(high, low)
    odds, p_value = fisher_exact_two_sided(sum(low), len(low) - sum(low), sum(high), len(high) - sum(high))
    diff = low_rate - high_rate
    return {
        "scope": scope,
        "descriptor_name": descriptor_name,
        "identity_stratum": identity_stratum,
        "label_scope": label_scope,
        "high_pair_count": len(high),
        "low_pair_count": len(low),
        "high_uncertain_or_not_ready_rate": high_rate,
        "low_uncertain_or_not_ready_rate": low_rate,
        "risk_difference_low_minus_high": diff,
        "risk_ratio_low_over_high": (low_rate / high_rate) if high_rate > 0 else "",
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "fisher_exact_p_two_sided": p_value,
        "odds_ratio": odds,
        "check_pass": "yes" if diff > 0 and ci_lower > 0 else "no",
    }


def agreement_rows(detail: list[dict[str, Any]], descriptor_name: str) -> list[dict[str, Any]]:
    rows = []
    for i, reviewer_a in enumerate(REVIEWERS):
        for reviewer_b in REVIEWERS[i + 1 :]:
            a_rows = {row["review_pair_id"]: row for row in detail if row["descriptor_name"] == descriptor_name and row["reviewer_id"] == reviewer_a}
            b_rows = {row["review_pair_id"]: row for row in detail if row["descriptor_name"] == descriptor_name and row["reviewer_id"] == reviewer_b}
            common = sorted(set(a_rows) & set(b_rows))
            for label_scope, column in [
                ("three_class_decision", "reviewability_decision"),
                ("binary_uncertain_or_not_ready", "binary_not_ready_or_uncertain"),
            ]:
                labels_a = [str(a_rows[pair_id][column]) for pair_id in common]
                labels_b = [str(b_rows[pair_id][column]) for pair_id in common]
                rows.append(
                    {
                        "descriptor_name": descriptor_name,
                        "reviewer_a": reviewer_a,
                        "reviewer_b": reviewer_b,
                        "label_scope": label_scope,
                        "pair_count": len(common),
                        "percent_agreement": sum(a == b for a, b in zip(labels_a, labels_b)) / len(common) if common else 0.0,
                        "cohen_kappa": cohen_kappa(labels_a, labels_b),
                    }
                )
    return rows


def matched_rows(majority_rows: list[dict[str, Any]], descriptor_name: str) -> list[dict[str, Any]]:
    output = []
    by_group: dict[str, dict[str, Any]] = defaultdict(dict)
    for row in majority_rows:
        by_group[row["match_group_id"]][row["evidence_group"]] = row
    for match_group_id, group in sorted(by_group.items()):
        if "high_admissibility" not in group or "low_admissibility" not in group:
            continue
        high = int(group["high_admissibility"]["majority_binary_not_ready_or_uncertain"])
        low = int(group["low_admissibility"]["majority_binary_not_ready_or_uncertain"])
        output.append(
            {
                "descriptor_name": descriptor_name,
                "identity_stratum": group["high_admissibility"]["identity_stratum"],
                "match_group_id": match_group_id,
                "high_uncertain_or_not_ready": high,
                "low_uncertain_or_not_ready": low,
                "matched_difference_low_minus_high": low - high,
            }
        )
    return output


def gate_rows(summaries: list[dict[str, Any]], agreements: list[dict[str, Any]]) -> tuple[str, list[dict[str, str]]]:
    rows = []
    primary = [
        row
        for row in summaries
        if row["scope"] == "descriptor_identity_specific" and row["label_scope"] == "majority_vote"
    ]
    for row in primary:
        rows.append(
            {
                "check_name": f"{row['descriptor_name']}:{row['identity_stratum']}:majority_effect",
                "status": "PASS" if row["check_pass"] == "yes" else "NEEDS_MORE_EVIDENCE",
                "detail": f"risk_difference={float(row['risk_difference_low_minus_high']):+.3f}; ci=[{float(row['ci_lower']):+.3f},{float(row['ci_upper']):+.3f}]",
            }
        )
    binary_agreements = [row for row in agreements if row["label_scope"] == "binary_uncertain_or_not_ready"]
    min_kappa = min((float(row["cohen_kappa"]) for row in binary_agreements), default=0.0)
    rows.append(
        {
            "check_name": "reviewer_reliability_binary_kappa_floor",
            "status": "PASS" if min_kappa >= 0.20 else "NEEDS_MORE_EVIDENCE",
            "detail": f"minimum_pairwise_kappa={min_kappa:.3f}",
        }
    )
    status = "PASS" if all(row["status"] == "PASS" for row in rows) else "NEEDS_MORE_EVIDENCE"
    return status, rows


def write_report(output_dir: Path, summaries: list[dict[str, Any]], gate_status: str) -> None:
    majority = [row for row in summaries if row["label_scope"] == "majority_vote"]
    lines = [
        "# Phase18M Identity-Balanced Review Analysis",
        "",
        "Date: 2026-07-04",
        "",
        "## Question",
        "",
        "Does PF-ERI admissibility predict human reviewability after fixing descriptor family, high descriptor similarity, and known same/different identity stratum?",
        "",
        "## Gate",
        "",
        f"- Status: `{gate_status}`",
        "",
        "## Majority-Vote Effects",
        "",
        "| Scope | Descriptor | Identity stratum | High risk rate | Low risk rate | Difference | 95% CI | Fisher p | Pass |",
        "| --- | --- | --- | ---: | ---: | ---: | --- | ---: | --- |",
    ]
    for row in majority:
        lines.append(
            f"| {row['scope']} | {row['descriptor_name']} | {row['identity_stratum']} | "
            f"{float(row['high_uncertain_or_not_ready_rate']):.3f} | {float(row['low_uncertain_or_not_ready_rate']):.3f} | "
            f"{float(row['risk_difference_low_minus_high']):+.3f} | "
            f"[{float(row['ci_lower']):+.3f}, {float(row['ci_upper']):+.3f}] | "
            f"{float(row['fisher_exact_p_two_sided']):.3g} | {row['check_pass']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "This phase is a confirmatory reviewability test, not identity accuracy and not a universal-threshold claim.",
            "A pass requires the low-admissibility effect to survive within same-identity and different-identity strata for each descriptor.",
        ]
    )
    output_dir.joinpath("README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_phase18m_identity_balanced_analysis(
    packet_root: Path = DEFAULT_PACKET_ROOT,
    review_root: Path = DEFAULT_REVIEW_ROOT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    all_detail = []
    all_majority = []
    all_agreement = []
    all_matched = []
    for descriptor in DESCRIPTORS:
        detail, majority = load_descriptor(descriptor, packet_root, review_root)
        all_detail.extend(detail)
        all_majority.extend(majority)
        all_agreement.extend(agreement_rows(detail, descriptor))
        all_matched.extend(matched_rows(majority, descriptor))
    summaries = []
    for descriptor in DESCRIPTORS:
        descriptor_rows = [row for row in all_majority if row["descriptor_name"] == descriptor]
        for identity_stratum in ["same_identity", "different_identity"]:
            summaries.append(
                summary_row(
                    [row for row in descriptor_rows if row["identity_stratum"] == identity_stratum],
                    "descriptor_identity_specific",
                    descriptor,
                    identity_stratum,
                    "majority_vote",
                    "majority_binary_not_ready_or_uncertain",
                )
            )
    for identity_stratum in ["same_identity", "different_identity"]:
        summaries.append(
            summary_row(
                [row for row in all_majority if row["identity_stratum"] == identity_stratum],
                "pooled_identity_specific",
                "pooled",
                identity_stratum,
                "majority_vote",
                "majority_binary_not_ready_or_uncertain",
            )
        )
    summaries.append(summary_row(all_majority, "pooled", "pooled", "all", "majority_vote", "majority_binary_not_ready_or_uncertain"))
    gate_status, gate = gate_rows(summaries, all_agreement)
    write_csv(output_dir / "phase18m_reviewer_label_detail.csv", all_detail, DETAIL_COLUMNS)
    write_csv(output_dir / "phase18m_pair_majority_labels.csv", all_majority, MAJORITY_COLUMNS)
    write_csv(output_dir / "phase18m_identity_stratified_summary.csv", summaries, SUMMARY_COLUMNS)
    write_csv(output_dir / "phase18m_matched_pair_sensitivity.csv", all_matched, MATCHED_COLUMNS)
    write_csv(output_dir / "phase18m_reviewer_agreement.csv", all_agreement, AGREEMENT_COLUMNS)
    write_csv(output_dir / "phase18m_claim_gate.csv", gate, GATE_COLUMNS)
    audit = {
        "built_at_utc": now_utc(),
        "packet_root": project_relative(packet_root),
        "review_root": project_relative(review_root),
        "output_dir": project_relative(output_dir),
        "detail_rows": len(all_detail),
        "majority_pair_rows": len(all_majority),
        "matched_pair_rows": len(all_matched),
        "reviewers": REVIEWERS,
        "descriptors": DESCRIPTORS,
        "status": gate_status,
        "claim_boundary": "Identity-balanced descriptor-controlled reviewability analysis; not identity accuracy.",
    }
    write_json(output_dir / "phase18m_identity_balanced_analysis_audit.json", audit)
    write_report(output_dir, summaries, gate_status)
    return audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet-root", type=Path, default=DEFAULT_PACKET_ROOT)
    parser.add_argument("--review-root", type=Path, default=DEFAULT_REVIEW_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = build_phase18m_identity_balanced_analysis(args.packet_root, args.review_root, args.output_dir)
    print(f"{audit['status']} phase18m identity-balanced analysis")
    print(f"majority_pair_rows={audit['majority_pair_rows']}")
    print(f"WROTE {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
