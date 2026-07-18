#!/usr/bin/env python3
"""Build Issue 6 CzechLynx pre-inference evidence hygiene simulation."""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VALIDATION_TABLE_CSV = (
    PROJECT_ROOT
    / "archive/pferi_v1/outputs/modeling-validation/known-id-evidence-sufficiency-validation/known_id_reviewability_validation_table.csv"
)
ROUTES_CSV = PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/risk-calibrated-evidence-admission/risk_calibrated_pair_routes.csv"
OUTPUT_DIR = PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/story-hardening-issue6"
SIMULATION_CSV = OUTPUT_DIR / "issue6_pre_inference_evidence_hygiene_pairs.csv"
SUMMARY_CSV = OUTPUT_DIR / "issue6_pre_inference_evidence_hygiene_summary.csv"
AUDIT_JSON = OUTPUT_DIR / "issue6_pre_inference_evidence_hygiene_audit.json"
REPORT_MD = PROJECT_ROOT / "docs/modeling-validation/2026-07-09_pre_inference_evidence_hygiene_simulation.md"

ADMITTED_ROUTES = {"accept_review", "cautious_review"}
DEFERRED_ROUTES = {"conflict_review", "defer_low_evidence"}
SCOPES = ["pooled", "megadescriptor_l_384", "dinov2_vitl14"]

PAIR_COLUMNS = [
    "scope",
    "descriptor_name",
    "review_pair_id",
    "queue_rank",
    "route_label",
    "simulation_decision",
    "review_ready_label",
    "not_ready_or_uncertain_label",
    "same_identity_known_id",
    "descriptor_similarity_percentile",
    "evidence_admission_score",
    "evidence_risk_score",
    "claim_boundary",
]

SUMMARY_COLUMNS = [
    "scope",
    "simulation_decision",
    "pair_count",
    "pair_fraction",
    "review_ready_count",
    "not_ready_or_uncertain_count",
    "review_ready_rate",
    "not_ready_or_uncertain_rate",
    "same_id_count",
    "different_id_count",
    "same_id_retention",
    "false_candidate_burden_rate",
    "mean_descriptor_similarity_percentile",
    "mean_evidence_admission_score",
    "accept_review_count",
    "cautious_review_count",
    "conflict_review_count",
    "defer_low_evidence_count",
    "interpretation",
    "claim_boundary",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def project_relative(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        text = str(value).strip()
        if not text:
            return default
        return float(text)
    except (TypeError, ValueError):
        return default


def mean(rows: list[dict[str, Any]], column: str) -> float | str:
    if not rows:
        return ""
    return sum(to_float(row.get(column)) for row in rows) / len(rows)


def simulation_decision(route_label: str) -> str:
    if route_label in ADMITTED_ROUTES:
        return "admitted_pre_inference"
    if route_label in DEFERRED_ROUTES:
        return "deferred_pre_inference"
    return "unmapped_route"


def merge_rows() -> list[dict[str, Any]]:
    routes = {(row["descriptor_name"], row["review_pair_id"]): row for row in read_csv(ROUTES_CSV)}
    rows = []
    for row in read_csv(VALIDATION_TABLE_CSV):
        route = routes[(row["descriptor_name"], row["review_pair_id"])]
        rows.append({**row, **route})
    return sorted(
        rows,
        key=lambda row: (
            -to_float(row["evidence_admission_score"]),
            -to_float(row["descriptor_similarity_percentile"]),
            row["review_pair_id"],
        ),
    )


def scoped_rows(rows: list[dict[str, Any]], scope: str) -> list[dict[str, Any]]:
    if scope == "pooled":
        return rows
    return [row for row in rows if row["descriptor_name"] == scope]


def build_pair_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for scope in SCOPES:
        subset = scoped_rows(rows, scope)
        for rank, row in enumerate(subset, start=1):
            output.append(
                {
                    "scope": scope,
                    "descriptor_name": row["descriptor_name"],
                    "review_pair_id": row["review_pair_id"],
                    "queue_rank": rank,
                    "route_label": row["route_label"],
                    "simulation_decision": simulation_decision(row["route_label"]),
                    "review_ready_label": row["review_ready_label"],
                    "not_ready_or_uncertain_label": row["not_ready_or_uncertain_label"],
                    "same_identity_known_id": row["same_identity_known_id"],
                    "descriptor_similarity_percentile": row["descriptor_similarity_percentile"],
                    "evidence_admission_score": row["evidence_admission_score"],
                    "evidence_risk_score": row["evidence_risk_score"],
                    "claim_boundary": "Pre-inference evidence hygiene simulation only; not identity accuracy.",
                }
            )
    return output


def summary_for_group(scope: str, decision: str, group: list[dict[str, Any]], total_rows: list[dict[str, Any]]) -> dict[str, Any]:
    total_same = sum(1 for row in total_rows if row["same_identity_known_id"] == "yes")
    route_counts = Counter(row["route_label"] for row in group)
    ready = sum(int(row["review_ready_label"]) for row in group)
    not_ready = sum(int(row["not_ready_or_uncertain_label"]) for row in group)
    same = sum(1 for row in group if row["same_identity_known_id"] == "yes")
    count = len(group)
    if decision == "admitted_pre_inference":
        interpretation = "Pairs allowed forward for review/evidence use before downstream inference."
    elif decision == "deferred_pre_inference":
        interpretation = "Pairs held back because evidence is conflict-prone or low-readiness."
    else:
        interpretation = "Route not mapped by the simulation policy."
    return {
        "scope": scope,
        "simulation_decision": decision,
        "pair_count": count,
        "pair_fraction": count / len(total_rows) if total_rows else "",
        "review_ready_count": ready,
        "not_ready_or_uncertain_count": not_ready,
        "review_ready_rate": ready / count if count else "",
        "not_ready_or_uncertain_rate": not_ready / count if count else "",
        "same_id_count": same,
        "different_id_count": count - same,
        "same_id_retention": same / total_same if total_same else "",
        "false_candidate_burden_rate": (count - same) / count if count else "",
        "mean_descriptor_similarity_percentile": mean(group, "descriptor_similarity_percentile"),
        "mean_evidence_admission_score": mean(group, "evidence_admission_score"),
        "accept_review_count": route_counts["accept_review"],
        "cautious_review_count": route_counts["cautious_review"],
        "conflict_review_count": route_counts["conflict_review"],
        "defer_low_evidence_count": route_counts["defer_low_evidence"],
        "interpretation": interpretation,
        "claim_boundary": "Pre-inference evidence hygiene only; false-candidate burden is review burden, not identity accuracy.",
    }


def build_summary_rows(pair_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for scope in SCOPES:
        total = [row for row in pair_rows if row["scope"] == scope]
        decisions = ["admitted_pre_inference", "deferred_pre_inference"]
        for decision in decisions:
            group = [row for row in total if row["simulation_decision"] == decision]
            output.append(summary_for_group(scope, decision, group, total))
    return output


def fmt(value: Any) -> str:
    if value == "":
        return "not estimable"
    return f"{to_float(value):.3f}"


def write_report(summary_rows: list[dict[str, Any]], audit: dict[str, Any]) -> None:
    admitted = next(row for row in summary_rows if row["scope"] == "pooled" and row["simulation_decision"] == "admitted_pre_inference")
    deferred = next(row for row in summary_rows if row["scope"] == "pooled" and row["simulation_decision"] == "deferred_pre_inference")
    lines = [
        "# Pre-Inference Evidence Hygiene Simulation",
        "",
        "Date: 2026-07-09",
        "",
        f"Status: `{audit['status']}`",
        "",
        "This simulation applies the PF-ERI review route as a pre-inference evidence gate on the CzechLynx reviewed candidate-pair table. The simulated workflow begins with a descriptor-retrieved candidate queue, assigns each pair to an admitted or deferred evidence state, and then audits the consequences using human reviewability and known-ID same/different labels. The simulation is deliberately placed before expert review or ecological inference; it is not a population estimate, a validated ecological outcome, or an automatic identity assignment.",
        "",
        f"In the pooled queue, {admitted['pair_count']} pairs were admitted before inference and {deferred['pair_count']} were deferred. The admitted set had review-ready rate {fmt(admitted['review_ready_rate'])} and not-ready/uncertain rate {fmt(admitted['not_ready_or_uncertain_rate'])}, whereas the deferred set had review-ready rate {fmt(deferred['review_ready_rate'])} and not-ready/uncertain rate {fmt(deferred['not_ready_or_uncertain_rate'])}. Same-ID candidate retention in the admitted set was {fmt(admitted['same_id_retention'])}. These values show how PF-ERI changes what evidence is allowed to proceed, not whether the system can identify individuals by itself.",
        "",
        f"The deferred set concentrated {deferred['not_ready_or_uncertain_count']} not-ready or uncertain pairs, compared with {admitted['not_ready_or_uncertain_count']} in the admitted set. This is the central applied value of the simulation: pairs with weaker, conflicted, or lower-readiness evidence are moved out of the immediate evidence-use path. Different-ID pairs are reported as review burden rather than errors, because many different-ID pairs can still be review-ready when the reviewer can confidently reject them.",
        "",
        "The result should be interpreted as a CzechLynx known-ID evidence-hygiene demonstration. It supports the claim that PF-ERI can structure the candidate queue before inference, preserving a more review-ready admitted set and concentrating lower-readiness pairs into deferral. It does not support Bobcat identity accuracy, population-level ecological inference, top-k identity improvement, mAP, MRR, or automatic individual recognition.",
        "",
        "## Artifact Links",
        "",
        f"The pair-level simulation table is `{audit['outputs']['simulation_csv']}`. The summary table is `{audit['outputs']['summary_csv']}`. The audit file is `{audit['outputs']['audit_json']}`.",
    ]
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build() -> dict[str, Any]:
    rows = merge_rows()
    pair_rows = build_pair_rows(rows)
    summary_rows = build_summary_rows(pair_rows)
    pooled_admitted = next(row for row in summary_rows if row["scope"] == "pooled" and row["simulation_decision"] == "admitted_pre_inference")
    pooled_deferred = next(row for row in summary_rows if row["scope"] == "pooled" and row["simulation_decision"] == "deferred_pre_inference")
    status = (
        "PASS"
        if to_float(pooled_admitted["review_ready_rate"]) > to_float(pooled_deferred["review_ready_rate"])
        and to_float(pooled_admitted["not_ready_or_uncertain_rate"]) < to_float(pooled_deferred["not_ready_or_uncertain_rate"])
        else "FAIL_NO_EVIDENCE_HYGIENE_CONCENTRATION"
    )
    audit = {
        "built_at_utc": utc_now(),
        "status": status,
        "input_validation_table_csv": project_relative(VALIDATION_TABLE_CSV),
        "input_routes_csv": project_relative(ROUTES_CSV),
        "row_count": len(rows),
        "admitted_routes": sorted(ADMITTED_ROUTES),
        "deferred_routes": sorted(DEFERRED_ROUTES),
        "outputs": {
            "simulation_csv": project_relative(SIMULATION_CSV),
            "summary_csv": project_relative(SUMMARY_CSV),
            "audit_json": project_relative(AUDIT_JSON),
            "report_md": project_relative(REPORT_MD),
        },
        "claim_boundary": "CzechLynx pre-inference evidence hygiene simulation only; no identity accuracy or ecological inference claim.",
    }
    write_csv(SIMULATION_CSV, pair_rows, PAIR_COLUMNS)
    write_csv(SUMMARY_CSV, summary_rows, SUMMARY_COLUMNS)
    write_json(AUDIT_JSON, audit)
    write_report(summary_rows, audit)
    return audit


def main() -> int:
    audit = build()
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
