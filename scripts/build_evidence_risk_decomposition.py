#!/usr/bin/env python3
"""Decompose PF-ERI evidence risk into interpretable component families."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VALIDATION_TABLE_CSV = (
    PROJECT_ROOT
    / "archive/pferi_v1/outputs/modeling-validation/known-id-evidence-sufficiency-validation/known_id_reviewability_validation_table.csv"
)
ROUTES_CSV = PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/risk-calibrated-evidence-admission/risk_calibrated_pair_routes.csv"
MAJORITY_LABELS_CSV = (
    PROJECT_ROOT
    / "archive/pferi_v1/outputs/modeling-validation/pair-level-validation/identity-balanced-analysis/legacy-code18m_pair_majority_labels.csv"
)
OUTPUT_DIR = PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/evidence-risk-decomposition"
DECOMPOSITION_CSV = OUTPUT_DIR / "pair_evidence_risk_decomposition.csv"
SUMMARY_CSV = OUTPUT_DIR / "risk_family_summary.csv"
ENRICHMENT_CSV = OUTPUT_DIR / "reason_label_enrichment_needs.csv"
AUDIT_JSON = OUTPUT_DIR / "evidence_risk_decomposition_audit.json"
REPORT_MD = OUTPUT_DIR / "README.md"

RISK_FAMILIES = [
    "image_evidence_deficit",
    "pair_non_comparability",
    "descriptor_evidence_conflict",
    "domain_source_stress",
]

DECOMPOSITION_COLUMNS = [
    "descriptor_name",
    "review_pair_id",
    "majority_decision",
    "not_ready_or_uncertain_label",
    "route_label",
    "evidence_risk_score",
    "image_evidence_deficit_risk",
    "pair_non_comparability_risk",
    "descriptor_evidence_conflict_risk",
    "domain_source_stress_risk",
    "dominant_risk_family",
    "dominant_risk_share",
    "human_reason_votes",
    "human_reason_support",
    "needs_reason_label_enrichment",
    "claim_boundary",
]

SUMMARY_COLUMNS = ["risk_family", "pair_count", "not_ready_or_uncertain_count", "mean_component_risk", "human_supported_count"]
ENRICHMENT_COLUMNS = ["reason_family", "needed", "available_support_count", "notes"]


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


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def component_risks(row: dict[str, str]) -> dict[str, float]:
    visible = to_float(row["visible_pattern_area_score"])
    overlap = to_float(row["body_part_overlap_score"])
    side = to_float(row["viewpoint_side_compatibility"])
    blur = to_float(row["night_or_motion_blur_risk"])
    descriptor_agreement = to_float(row["cross_descriptor_agreement_score"], 0.5)
    descriptor_similarity = to_float(row["descriptor_similarity_percentile"])
    domain_shift = to_float(row["source_domain_shift_score"])
    image_risk = clamp01(0.65 * (1.0 - visible) + 0.35 * blur)
    pair_risk = clamp01(0.60 * (1.0 - overlap) + 0.40 * (1.0 - side))
    conflict_risk = clamp01(max(0.0, descriptor_similarity - 0.70) * 1.8 + max(0.0, 0.55 - descriptor_agreement))
    return {
        "image_evidence_deficit": round(image_risk, 6),
        "pair_non_comparability": round(pair_risk, 6),
        "descriptor_evidence_conflict": round(conflict_risk, 6),
        "domain_source_stress": round(domain_shift, 6),
    }


def reason_support(family: str, reason_votes: str, route_reason: str) -> str:
    text = f"{reason_votes};{route_reason}".lower()
    if family == "image_evidence_deficit" and ("low_evidence" in text or "blur" in text or "visibility" in text):
        return "human_or_route_supported"
    if family == "pair_non_comparability" and ("non_comparable" in text or "partial" in text or "occlusion" in text):
        return "human_or_route_supported"
    if family == "descriptor_evidence_conflict" and "conflict" in text:
        return "route_supported_feature_conflict"
    if family == "domain_source_stress" and "domain" in text:
        return "route_supported_domain_stress"
    return "component_attribution_only"


def build() -> dict[str, Any]:
    validation_rows = {(row["descriptor_name"], row["review_pair_id"]): row for row in read_csv(VALIDATION_TABLE_CSV)}
    route_rows = {(row["descriptor_name"], row["review_pair_id"]): row for row in read_csv(ROUTES_CSV)}
    majority_rows = {(row["descriptor_name"], row["review_pair_id"]): row for row in read_csv(MAJORITY_LABELS_CSV)}
    rows = []
    for key, validation in sorted(validation_rows.items()):
        route = route_rows[key]
        majority = majority_rows[key]
        risks = component_risks(validation)
        total = sum(risks.values()) or 1.0
        dominant = max(risks, key=risks.get)
        support = reason_support(dominant, majority.get("reason_votes", ""), route.get("route_reason", ""))
        rows.append(
            {
                "descriptor_name": key[0],
                "review_pair_id": key[1],
                "majority_decision": validation["majority_decision"],
                "not_ready_or_uncertain_label": validation["not_ready_or_uncertain_label"],
                "route_label": route["route_label"],
                "evidence_risk_score": route["evidence_risk_score"],
                "image_evidence_deficit_risk": risks["image_evidence_deficit"],
                "pair_non_comparability_risk": risks["pair_non_comparability"],
                "descriptor_evidence_conflict_risk": risks["descriptor_evidence_conflict"],
                "domain_source_stress_risk": risks["domain_source_stress"],
                "dominant_risk_family": dominant,
                "dominant_risk_share": round(risks[dominant] / total, 6),
                "human_reason_votes": majority.get("reason_votes", ""),
                "human_reason_support": support,
                "needs_reason_label_enrichment": "yes" if support == "component_attribution_only" else "no",
                "claim_boundary": "Risk decomposition is component attribution unless human reason labels support a reason class.",
            }
        )
    summary = []
    for family in RISK_FAMILIES:
        column = f"{family}_risk"
        summary.append(
            {
                "risk_family": family,
                "pair_count": len(rows),
                "not_ready_or_uncertain_count": sum(row["not_ready_or_uncertain_label"] == "1" for row in rows),
                "mean_component_risk": sum(to_float(row[column]) for row in rows) / len(rows) if rows else 0.0,
                "human_supported_count": sum(row["dominant_risk_family"] == family and row["human_reason_support"] != "component_attribution_only" for row in rows),
            }
        )
    supported_counts = Counter(row["dominant_risk_family"] for row in rows if row["human_reason_support"] != "component_attribution_only")
    enrichment = [
        {
            "reason_family": family,
            "needed": "yes" if supported_counts[family] < 20 else "no",
            "available_support_count": supported_counts[family],
            "notes": "Add explicit not-ready reason labels if support is sparse.",
        }
        for family in RISK_FAMILIES
    ]
    audit = {
        "built_at_utc": utc_now(),
        "status": "PASS" if rows and len(summary) == 4 else "FAIL",
        "input_validation_table_csv": project_relative(VALIDATION_TABLE_CSV),
        "input_routes_csv": project_relative(ROUTES_CSV),
        "decomposition_csv": project_relative(DECOMPOSITION_CSV),
        "summary_csv": project_relative(SUMMARY_CSV),
        "enrichment_csv": project_relative(ENRICHMENT_CSV),
        "pair_rows": len(rows),
        "dominant_risk_family_counts": dict(sorted(Counter(row["dominant_risk_family"] for row in rows).items())),
        "reason_support_counts": dict(sorted(Counter(row["human_reason_support"] for row in rows).items())),
        "reason_label_enrichment_needed": any(row["needed"] == "yes" for row in enrichment),
        "claim_boundary": "Component risk attribution; latent reason classes require human reason-label support.",
    }
    write_csv(DECOMPOSITION_CSV, rows, DECOMPOSITION_COLUMNS)
    write_csv(SUMMARY_CSV, summary, SUMMARY_COLUMNS)
    write_csv(ENRICHMENT_CSV, enrichment, ENRICHMENT_COLUMNS)
    write_json(AUDIT_JSON, audit)
    write_report(audit)
    return audit


def write_report(audit: dict[str, Any]) -> None:
    lines = [
        "# Evidence Risk Decomposition",
        "",
        f"Status: `{audit['status']}`",
        "",
        "This module decomposes pair-level evidence risk into image evidence",
        "deficit, pair non-comparability, descriptor-evidence conflict, and",
        "domain/source stress components.",
        "",
        "## Outputs",
        "",
        f"- Pair decomposition: `{audit['decomposition_csv']}`",
        f"- Family summary: `{audit['summary_csv']}`",
        f"- Reason-label enrichment needs: `{audit['enrichment_csv']}`",
        "",
        "## Boundary",
        "",
        audit["claim_boundary"],
    ]
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    audit = build()
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
