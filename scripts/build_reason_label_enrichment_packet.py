#!/usr/bin/env python3
"""Build a reason-label enrichment packet from existing reviewed pair databases."""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LEGACY_PROJECT_PATH_RELOCATIONS = (
    ("outputs/final_freeze/", "data/frozen/pferi_v2/"),
)
OUTPUT_DIR = PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/reason-label-enrichment"
QUEUE_CSV = OUTPUT_DIR / "reason_label_enrichment_queue.csv"
REVIEW_FORM_CSV = OUTPUT_DIR / "reason_label_enrichment_review_form.csv"
CODEBOOK_CSV = OUTPUT_DIR / "reason_label_codebook.csv"
AUDIT_JSON = OUTPUT_DIR / "reason_label_enrichment_packet_audit.json"
REPORT_MD = OUTPUT_DIR / "README.md"

SOURCES = [
    {
        "source_id": "phase18m_identity_balanced",
        "majority_csv": PROJECT_ROOT
        / "archive/pferi_v1/outputs/modeling-validation/pair-level-validation/identity-balanced-analysis/legacy-code18m_pair_majority_labels.csv",
        "detail_csv": PROJECT_ROOT
        / "archive/pferi_v1/outputs/modeling-validation/pair-level-validation/identity-balanced-analysis/legacy-code18m_reviewer_label_detail.csv",
        "packet_template": PROJECT_ROOT
        / "archive/pferi_v1/outputs/modeling-validation/pair-level-validation/identity-balanced-review-packet/{descriptor}/legacy-code18m_identity_balanced_review_packet.csv",
        "binary_not_ready_column": "majority_binary_not_ready_or_uncertain",
        "majority_ready_column": "",
        "priority": 1,
    },
    {
        "source_id": "phase18l_descriptor_controlled",
        "majority_csv": PROJECT_ROOT
        / "archive/pferi_v1/outputs/modeling-validation/pair-level-validation/descriptor-controlled-analysis/legacy-code18l_pair_majority_labels.csv",
        "detail_csv": PROJECT_ROOT
        / "archive/pferi_v1/outputs/modeling-validation/pair-level-validation/descriptor-controlled-analysis/legacy-code18l_reviewer_label_detail.csv",
        "packet_template": PROJECT_ROOT
        / "archive/pferi_v1/outputs/modeling-validation/pair-level-validation/descriptor-controlled-review-packet/{descriptor}/legacy-code18l_descriptor_controlled_review_packet.csv",
        "binary_not_ready_column": "majority_binary_not_ready_or_uncertain",
        "majority_ready_column": "",
        "priority": 2,
    },
    {
        "source_id": "phase18j_full_queue_100",
        "majority_csv": PROJECT_ROOT
        / "archive/pferi_v1/outputs/modeling-validation/pair-level-validation/reviewer-agreement-analysis-100/legacy-code18j_pair_majority_labels.csv",
        "detail_csv": PROJECT_ROOT
        / "archive/pferi_v1/outputs/modeling-validation/pair-level-validation/reviewer-agreement-analysis-100/legacy-code18j_reviewer_label_detail.csv",
        "packet_template": PROJECT_ROOT
        / "archive/pferi_v1/outputs/modeling-validation/pair-level-validation/full-queue-review-packet-100/{descriptor}/legacy-code18j_full_queue_review_packet.csv",
        "binary_not_ready_column": "",
        "majority_ready_column": "majority_binary_review_ready",
        "priority": 3,
    },
]

DECOMPOSITION_CSV = (
    PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/evidence-risk-decomposition/pair_evidence_risk_decomposition.csv"
)
IMAGE_INDEX_CSV = (
    PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/final-modeling-bootstrap/final_modeling_image_index.csv"
)

TARGET_TOTAL_REVIEW_ROWS = 300
REASON_OPTIONS = [
    ("low_image_evidence", "Single-image evidence is too weak for individual review."),
    ("motion_or_blur", "Animal body or markings are blurred/moving/soft."),
    ("night_or_low_light", "Night, IR, glare, or low exposure blocks reliable comparison."),
    ("subject_too_small", "Animal is too small in frame even if visible."),
    ("partial_body", "Body is incomplete or critical pattern area is absent."),
    ("occlusion", "Occlusion blocks comparable body/marking evidence."),
    ("non_comparable_viewpoint", "Pair viewpoints/poses are not meaningfully comparable."),
    ("non_overlapping_body_region", "The two images show different body regions."),
    ("descriptor_evidence_conflict", "Descriptor similarity is high but visual evidence is weak/conflicting."),
    ("source_domain_stress", "Source/context shift creates review risk."),
    ("other", "Reason exists but is outside the predefined schema."),
]

QUEUE_COLUMNS = [
    "enrichment_id",
    "annotation_role",
    "source_id",
    "descriptor_name",
    "review_pair_id",
    "majority_decision",
    "not_ready_or_uncertain_label",
    "unanimous_decision",
    "decision_votes",
    "existing_reason_votes",
    "existing_reason_vote_count",
    "suggested_reason_proxy",
    "proxy_reason_confidence",
    "dominant_risk_family",
    "evidence_risk_score",
    "image_evidence_deficit_risk",
    "pair_non_comparability_risk",
    "descriptor_evidence_conflict_risk",
    "domain_source_stress_risk",
    "same_identity_known_id",
    "rank_bin",
    "evidence_group",
    "descriptor_similarity_percentile",
    "pf_eri_admissibility_score",
    "pair_geometry_score",
    "weakest_image_quality_score",
    "query_image_id",
    "candidate_image_id",
    "query_image_path",
    "candidate_image_path",
    "query_image_exists",
    "candidate_image_exists",
    "target_primary_reason",
    "target_secondary_reason",
    "target_body_region_visible",
    "target_notes",
    "claim_boundary",
]

REVIEW_COLUMNS = [
    "enrichment_id",
    "query_image_path",
    "candidate_image_path",
    "majority_decision",
    "suggested_reason_proxy",
    "target_primary_reason",
    "target_secondary_reason",
    "target_body_region_visible",
    "target_notes",
]

CODEBOOK_COLUMNS = ["reason_label", "description"]


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


def reason_vote_count(reason_votes: str) -> int:
    if not reason_votes.strip():
        return 0
    total = 0
    for part in reason_votes.split(";"):
        if ":" not in part:
            continue
        _, count = part.rsplit(":", 1)
        try:
            total += int(count)
        except ValueError:
            continue
    return total


def is_not_ready_or_uncertain(row: dict[str, str], source: dict[str, Any]) -> bool:
    binary_col = source["binary_not_ready_column"]
    ready_col = source["majority_ready_column"]
    if binary_col:
        return str(row.get(binary_col, "")).strip() == "1"
    if ready_col:
        return str(row.get(ready_col, "")).strip().lower() == "no"
    return str(row.get("majority_decision", "")).strip() in {"uncertain", "not_review_ready"}


def packet_lookup(source: dict[str, Any]) -> dict[tuple[str, str], dict[str, str]]:
    lookup = {}
    descriptors = sorted({row["descriptor_name"] for row in read_csv(source["majority_csv"])})
    for descriptor in descriptors:
        packet_path = Path(str(source["packet_template"]).format(descriptor=descriptor))
        for row in read_csv(packet_path):
            lookup[(row["descriptor_name"], row["review_pair_id"])] = row
    return lookup


def detail_reason_lookup(source: dict[str, Any]) -> dict[tuple[str, str], str]:
    grouped: dict[tuple[str, str], Counter[str]] = {}
    for row in read_csv(source["detail_csv"]):
        reason = str(row.get("not_ready_reason", "")).strip()
        if not reason:
            continue
        key = (row["descriptor_name"], row["review_pair_id"])
        grouped.setdefault(key, Counter())[reason] += 1
    output = {}
    for key, counts in grouped.items():
        output[key] = ";".join(f"{reason}:{count}" for reason, count in sorted(counts.items()))
    return output


def decomposition_lookup() -> dict[tuple[str, str], dict[str, str]]:
    if not DECOMPOSITION_CSV.exists():
        return {}
    return {(row["descriptor_name"], row["review_pair_id"]): row for row in read_csv(DECOMPOSITION_CSV)}


def legacy_phase18_to_pferi_id(image_id: str) -> str:
    if image_id.startswith("phase18a_czechlynx_"):
        return f"pferi_lynx_wild_{int(image_id.rsplit('_', 1)[1]):05d}"
    return image_id


def image_path_lookup() -> dict[str, str]:
    lookup = {}
    for row in read_csv(IMAGE_INDEX_CSV):
        lookup[row["image_id"]] = relocate_project_path(row["local_image_path"])
    return lookup


def relocate_project_path(path_text: str) -> str:
    """Translate immutable historical path fields to the current repository layout."""
    for legacy_prefix, current_prefix in LEGACY_PROJECT_PATH_RELOCATIONS:
        if path_text.startswith(legacy_prefix):
            return current_prefix + path_text[len(legacy_prefix) :]
    return path_text


def resolve_image_path(image_id: str, packet_path: str, image_lookup: dict[str, str]) -> str:
    mapped = image_lookup.get(legacy_phase18_to_pferi_id(image_id))
    if mapped:
        return mapped
    relocated_packet_path = relocate_project_path(packet_path)
    if relocated_packet_path and (PROJECT_ROOT / relocated_packet_path).exists():
        return relocated_packet_path
    return relocated_packet_path


def path_exists(path_text: str) -> bool:
    if not path_text:
        return False
    path = Path(path_text)
    if path.is_absolute():
        return path.exists()
    return (PROJECT_ROOT / path).exists()


def proxy_reason(row: dict[str, Any]) -> tuple[str, str]:
    existing = str(row.get("existing_reason_votes", "")).strip()
    if existing:
        reason = existing.split(":", 1)[0].split(";", 1)[0]
        return normalize_existing_reason(reason), "existing_human_reason_vote"
    dominant = str(row.get("dominant_risk_family", "")).strip()
    if dominant == "pair_non_comparability":
        return "non_comparable_viewpoint", "component_proxy"
    if dominant == "descriptor_evidence_conflict":
        return "descriptor_evidence_conflict", "component_proxy"
    if dominant == "image_evidence_deficit":
        return "low_image_evidence", "component_proxy"
    if to_float(row.get("weakest_image_quality_score", "1")) < 0.45:
        return "low_image_evidence", "legacy_quality_proxy"
    if to_float(row.get("pair_geometry_score", "1")) < 0.85:
        return "non_comparable_viewpoint", "legacy_geometry_proxy"
    if to_float(row.get("descriptor_evidence_conflict_risk", "0")) >= 0.35:
        return "descriptor_evidence_conflict", "component_proxy"
    return "other", "low_confidence_proxy"


def normalize_existing_reason(reason: str) -> str:
    mapping = {
        "low_evidence": "low_image_evidence",
        "geometry_mismatch": "non_comparable_viewpoint",
        "descriptor_conflict": "descriptor_evidence_conflict",
        "quality": "low_image_evidence",
    }
    return mapping.get(reason, reason if reason in {label for label, _ in REASON_OPTIONS} else "other")


def merged_source_rows() -> list[dict[str, Any]]:
    decomposition = decomposition_lookup()
    output = []
    seen: set[tuple[str, str, str]] = set()
    for source in SOURCES:
        packets = packet_lookup(source)
        detail_reasons = detail_reason_lookup(source)
        for row in read_csv(source["majority_csv"]):
            key = (row["descriptor_name"], row["review_pair_id"])
            packet = packets[key]
            decomp = decomposition.get(key, {})
            existing_reason_votes = row.get("reason_votes", "") or detail_reasons.get(key, "")
            not_ready = is_not_ready_or_uncertain(row, source)
            merged = {
                **packet,
                **row,
                **{f"decomposition_{name}": value for name, value in decomp.items()},
                "source_id": source["source_id"],
                "source_priority": source["priority"],
                "not_ready_or_uncertain_label": "1" if not_ready else "0",
                "existing_reason_votes": existing_reason_votes,
                "existing_reason_vote_count": reason_vote_count(existing_reason_votes),
            }
            unique = (source["source_id"], merged["descriptor_name"], merged["review_pair_id"])
            if unique not in seen:
                output.append(merged)
                seen.add(unique)
    return output


def candidate_priority(row: dict[str, Any]) -> tuple[Any, ...]:
    not_ready = int(row["not_ready_or_uncertain_label"])
    has_reason_vote = 1 if int(row["existing_reason_vote_count"]) else 0
    return (
        -not_ready,
        has_reason_vote,
        int(row.get("source_priority", 99)),
        -to_float(row.get("evidence_risk_score", row.get("decomposition_evidence_risk_score", "0"))),
        row["descriptor_name"],
        row["review_pair_id"],
    )


def build_queue_rows() -> list[dict[str, Any]]:
    rows = merged_source_rows()
    images = image_path_lookup()
    targets = [row for row in rows if row["not_ready_or_uncertain_label"] == "1"]
    controls = [row for row in rows if row["not_ready_or_uncertain_label"] == "0"]
    targets = sorted(targets, key=candidate_priority)
    controls = sorted(
        controls,
        key=lambda row: (
            int(row.get("source_priority", 99)),
            -to_float(row.get("decomposition_evidence_risk_score", row.get("pf_eri_admissibility_score", "0"))),
            row["descriptor_name"],
            row["review_pair_id"],
        ),
    )
    selected = targets + controls[: max(0, TARGET_TOTAL_REVIEW_ROWS - len(targets))]
    queue = []
    for index, row in enumerate(selected, start=1):
        decomp_prefix = "decomposition_"
        enriched = {
            "dominant_risk_family": row.get(f"{decomp_prefix}dominant_risk_family", ""),
            "evidence_risk_score": row.get(f"{decomp_prefix}evidence_risk_score", ""),
            "image_evidence_deficit_risk": row.get(f"{decomp_prefix}image_evidence_deficit_risk", ""),
            "pair_non_comparability_risk": row.get(f"{decomp_prefix}pair_non_comparability_risk", ""),
            "descriptor_evidence_conflict_risk": row.get(f"{decomp_prefix}descriptor_evidence_conflict_risk", ""),
            "domain_source_stress_risk": row.get(f"{decomp_prefix}domain_source_stress_risk", ""),
        }
        role = "primary_not_ready_reason_enrichment" if row["not_ready_or_uncertain_label"] == "1" else "borderline_review_ready_control"
        merged = {**row, **enriched}
        suggestion, confidence = proxy_reason(merged)
        query_image_path = resolve_image_path(row.get("query_image_id", ""), row.get("query_image_path", ""), images)
        candidate_image_path = resolve_image_path(row.get("candidate_image_id", ""), row.get("candidate_image_path", ""), images)
        queue.append(
            {
                "enrichment_id": f"reason_enrich_{index:04d}",
                "annotation_role": role,
                "source_id": row["source_id"],
                "descriptor_name": row["descriptor_name"],
                "review_pair_id": row["review_pair_id"],
                "majority_decision": row.get("majority_decision", ""),
                "not_ready_or_uncertain_label": row["not_ready_or_uncertain_label"],
                "unanimous_decision": row.get("unanimous_decision", ""),
                "decision_votes": row.get("decision_votes", ""),
                "existing_reason_votes": row["existing_reason_votes"],
                "existing_reason_vote_count": row["existing_reason_vote_count"],
                "suggested_reason_proxy": suggestion,
                "proxy_reason_confidence": confidence,
                **enriched,
                "same_identity_known_id": row.get("same_identity_known_id", ""),
                "rank_bin": row.get("rank_bin", ""),
                "evidence_group": row.get("evidence_group", row.get("admissibility_tertile", "")),
                "descriptor_similarity_percentile": row.get("descriptor_similarity_percentile", ""),
                "pf_eri_admissibility_score": row.get("pf_eri_admissibility_score", ""),
                "pair_geometry_score": row.get("pair_geometry_score", ""),
                "weakest_image_quality_score": row.get("weakest_image_quality_score", ""),
                "query_image_id": row.get("query_image_id", ""),
                "candidate_image_id": row.get("candidate_image_id", ""),
                "query_image_path": query_image_path,
                "candidate_image_path": candidate_image_path,
                "query_image_exists": path_exists(query_image_path),
                "candidate_image_exists": path_exists(candidate_image_path),
                "target_primary_reason": "",
                "target_secondary_reason": "",
                "target_body_region_visible": "",
                "target_notes": "",
                "claim_boundary": "Reason-label enrichment for CzechLynx reviewability only; labels are not identity decisions.",
            }
        )
    return queue


def review_form_rows(queue: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{column: row.get(column, "") for column in REVIEW_COLUMNS} for row in queue]


def codebook_rows() -> list[dict[str, str]]:
    return [{"reason_label": label, "description": description} for label, description in REASON_OPTIONS]


def write_report(audit: dict[str, Any]) -> None:
    lines = [
        "# Reason Label Enrichment Packet",
        "",
        f"Status: `{audit['status']}`",
        "",
        "This packet mines the existing CzechLynx reviewed-pair databases for pairs that need explicit not-ready reason labels.",
        "",
        "## What Was Found",
        "",
        f"- Total review rows selected: `{audit['selected_rows']}`",
        f"- Primary not-ready/uncertain targets: `{audit['primary_not_ready_targets']}`",
        f"- Borderline review-ready controls: `{audit['borderline_controls']}`",
        f"- Rows with existing reason votes: `{audit['rows_with_existing_reason_votes']}`",
        "",
        "The existing database does not contain 300-500 not-ready/uncertain pairs; it currently provides 229 target pairs. The remaining rows are controls for reviewer calibration.",
        "",
        "## Outputs",
        "",
        f"- Queue: `{audit['queue_csv']}`",
        f"- Review form: `{audit['review_form_csv']}`",
        f"- Codebook: `{audit['codebook_csv']}`",
        "",
        "## Boundary",
        "",
        audit["claim_boundary"],
    ]
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build() -> dict[str, Any]:
    queue = build_queue_rows()
    source_counts = Counter(row["source_id"] for row in queue)
    role_counts = Counter(row["annotation_role"] for row in queue)
    reason_proxy_counts = Counter(row["suggested_reason_proxy"] for row in queue)
    missing_images = [
        row["enrichment_id"]
        for row in queue
        if str(row["query_image_exists"]) != "True" or str(row["candidate_image_exists"]) != "True"
    ]
    write_csv(QUEUE_CSV, queue, QUEUE_COLUMNS)
    write_csv(REVIEW_FORM_CSV, review_form_rows(queue), REVIEW_COLUMNS)
    write_csv(CODEBOOK_CSV, codebook_rows(), CODEBOOK_COLUMNS)
    audit = {
        "built_at_utc": utc_now(),
        "status": "PASS" if queue and not missing_images else "FAIL",
        "queue_csv": project_relative(QUEUE_CSV),
        "review_form_csv": project_relative(REVIEW_FORM_CSV),
        "codebook_csv": project_relative(CODEBOOK_CSV),
        "selected_rows": len(queue),
        "primary_not_ready_targets": role_counts["primary_not_ready_reason_enrichment"],
        "borderline_controls": role_counts["borderline_review_ready_control"],
        "rows_with_existing_reason_votes": sum(1 for row in queue if int(row["existing_reason_vote_count"]) > 0),
        "source_counts": dict(sorted(source_counts.items())),
        "annotation_role_counts": dict(sorted(role_counts.items())),
        "suggested_reason_proxy_counts": dict(sorted(reason_proxy_counts.items())),
        "missing_image_rows": missing_images,
        "target_total_review_rows": TARGET_TOTAL_REVIEW_ROWS,
        "target_reason_labels": [label for label, _ in REASON_OPTIONS],
        "claim_boundary": "Reason-label enrichment supports explanation validation only; no identity assignment or Bobcat identity metric claim.",
    }
    write_json(AUDIT_JSON, audit)
    write_report(audit)
    return audit


def main() -> int:
    audit = build()
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
