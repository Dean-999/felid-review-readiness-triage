#!/usr/bin/env python3
"""Analyze external blind reliability reviews against original attested labels."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKET_DIR = PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/blind-reliability-packet"
MASTER_PACKET_CSV = PACKET_DIR / "blind_reliability_master_packet.csv"
DEFAULT_REVIEW_ROOT = PACKET_DIR / "external-reviews"
OUTPUT_DIR = PACKET_DIR / "agreement-analysis"
DETAIL_CSV = OUTPUT_DIR / "blind_reliability_label_detail.csv"
AGREEMENT_CSV = OUTPUT_DIR / "blind_reliability_agreement_summary.csv"
DISAGREEMENT_APPENDIX_CSV = OUTPUT_DIR / "blind_reliability_disagreement_appendix.csv"
REASON_FAMILY_SUMMARY_CSV = OUTPUT_DIR / "blind_reliability_reason_family_summary.csv"
AUDIT_JSON = OUTPUT_DIR / "blind_reliability_analysis_audit.json"
README_MD = OUTPUT_DIR / "README.md"

DETAIL_COLUMNS = [
    "blind_pair_id",
    "source_packet",
    "reviewer_id",
    "original_review_ready",
    "reviewer_review_ready",
    "original_binary_ready",
    "reviewer_binary_ready",
    "review_ready_exact_match",
    "binary_ready_match",
    "original_primary_reason",
    "reviewer_primary_reason",
    "primary_reason_match",
    "original_reason_family",
    "reviewer_reason_family",
    "reason_family_match",
    "reviewer_confidence",
]

AGREEMENT_COLUMNS = [
    "scope",
    "source_packet",
    "reviewer_id",
    "pair_count",
    "three_class_percent_agreement",
    "binary_percent_agreement",
    "binary_cohen_kappa",
    "primary_reason_agreement_on_nonready",
]

DISAGREEMENT_COLUMNS = [
    "blind_pair_id",
    "source_packet",
    "reviewer_id",
    "disagreement_type",
    "original_review_ready",
    "reviewer_review_ready",
    "original_binary_ready",
    "reviewer_binary_ready",
    "original_primary_reason",
    "reviewer_primary_reason",
    "original_reason_family",
    "reviewer_reason_family",
    "reason_family_match",
    "reviewer_confidence",
]

REASON_FAMILY_SUMMARY_COLUMNS = [
    "scope",
    "source_packet",
    "reviewer_id",
    "reason_family",
    "original_count",
    "reviewer_count",
    "matched_count",
    "original_nonready_count",
    "family_agreement_rate_on_original_nonready",
]

REASON_FAMILY_BY_REASON = {
    "low_image_evidence": "image_evidence_deficit",
    "motion_or_blur": "image_evidence_deficit",
    "night_or_low_light": "image_evidence_deficit",
    "subject_too_small": "image_evidence_deficit",
    "partial_body": "image_evidence_deficit",
    "occlusion": "image_evidence_deficit",
    "non_comparable_viewpoint": "pair_non_comparability",
    "non_overlapping_body_region": "pair_non_comparability",
    "descriptor_evidence_conflict": "descriptor_evidence_conflict",
    "source_domain_stress": "source_domain_stress",
    "wrong_species_or_non_target": "source_domain_stress",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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


def project_relative(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def binary_ready(value: str) -> str:
    return "yes" if value == "yes" else "no"


def reason_family(reason: str) -> str:
    if not reason:
        return ""
    return REASON_FAMILY_BY_REASON.get(reason, "other")


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
    return round((observed - expected) / (1.0 - expected), 6)


def original_review_ready(row: dict[str, str]) -> str:
    value = row.get("original_target_review_ready", "")
    if value == "no_or_uncertain":
        return "no"
    if value in {"yes", "no", "uncertain"}:
        return value
    return "no" if row.get("original_primary_reason", "") else "yes"


def find_review_files(review_root: Path) -> list[Path]:
    if review_root.is_file():
        return [review_root]
    return sorted(review_root.glob("*/blind_reliability_review_working.csv"))


def load_reviews(review_root: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in find_review_files(review_root):
        rows.extend(read_csv(path))
    return rows


def build_detail(master_rows: list[dict[str, str]], review_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    master_by_id = {row["blind_pair_id"]: row for row in master_rows}
    detail = []
    for review in review_rows:
        pair_id = review.get("blind_pair_id", "")
        if pair_id not in master_by_id:
            continue
        if review.get("review_ready", "") not in {"yes", "no", "uncertain"}:
            continue
        original = master_by_id[pair_id]
        original_ready = original_review_ready(original)
        reviewer_ready = review["review_ready"]
        original_reason = original.get("original_primary_reason", "")
        reviewer_reason = review.get("primary_reason", "")
        original_family = reason_family(original_reason)
        reviewer_family = reason_family(reviewer_reason)
        detail.append(
            {
                "blind_pair_id": pair_id,
                "source_packet": original["source_packet"],
                "reviewer_id": review.get("reviewer_id", ""),
                "original_review_ready": original_ready,
                "reviewer_review_ready": reviewer_ready,
                "original_binary_ready": binary_ready(original_ready),
                "reviewer_binary_ready": binary_ready(reviewer_ready),
                "review_ready_exact_match": "yes" if original_ready == reviewer_ready else "no",
                "binary_ready_match": "yes" if binary_ready(original_ready) == binary_ready(reviewer_ready) else "no",
                "original_primary_reason": original_reason,
                "reviewer_primary_reason": reviewer_reason,
                "primary_reason_match": "yes" if original_reason and original_reason == reviewer_reason else "no",
                "original_reason_family": original_family,
                "reviewer_reason_family": reviewer_family,
                "reason_family_match": "yes" if original_family and original_family == reviewer_family else "no",
                "reviewer_confidence": review.get("reviewer_confidence", ""),
            }
        )
    return detail


def agreement_row(scope: str, source_packet: str, reviewer_id: str, rows: list[dict[str, str]]) -> dict[str, Any]:
    if not rows:
        return {
            "scope": scope,
            "source_packet": source_packet,
            "reviewer_id": reviewer_id,
            "pair_count": 0,
            "three_class_percent_agreement": 0.0,
            "binary_percent_agreement": 0.0,
            "binary_cohen_kappa": 0.0,
            "primary_reason_agreement_on_nonready": 0.0,
        }
    nonready = [row for row in rows if row["original_binary_ready"] == "no" and row["original_primary_reason"]]
    return {
        "scope": scope,
        "source_packet": source_packet,
        "reviewer_id": reviewer_id,
        "pair_count": len(rows),
        "three_class_percent_agreement": round(
            sum(row["review_ready_exact_match"] == "yes" for row in rows) / len(rows), 6
        ),
        "binary_percent_agreement": round(sum(row["binary_ready_match"] == "yes" for row in rows) / len(rows), 6),
        "binary_cohen_kappa": cohen_kappa(
            [row["original_binary_ready"] for row in rows],
            [row["reviewer_binary_ready"] for row in rows],
        ),
        "primary_reason_agreement_on_nonready": round(
            sum(row["primary_reason_match"] == "yes" for row in nonready) / len(nonready), 6
        )
        if nonready
        else 0.0,
    }


def build_agreement(detail: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows = [agreement_row("overall", "all", "all", detail)]
    by_reviewer: dict[str, list[dict[str, str]]] = defaultdict(list)
    by_packet: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in detail:
        by_reviewer[row["reviewer_id"]].append(row)
        by_packet[(row["source_packet"], row["reviewer_id"])].append(row)
    for reviewer_id, group in sorted(by_reviewer.items()):
        rows.append(agreement_row("reviewer", "all", reviewer_id, group))
    for (source_packet, reviewer_id), group in sorted(by_packet.items()):
        rows.append(agreement_row("source_packet_by_reviewer", source_packet, reviewer_id, group))
    return rows


def disagreement_type(row: dict[str, str]) -> str:
    types = []
    if row["binary_ready_match"] == "no":
        types.append("binary_ready")
    elif row["review_ready_exact_match"] == "no":
        types.append("three_class_ready")
    if (
        row["original_binary_ready"] == "no"
        and row["original_primary_reason"]
        and row["primary_reason_match"] == "no"
    ):
        types.append("primary_reason")
    if (
        row["original_binary_ready"] == "no"
        and row["original_reason_family"]
        and row["reason_family_match"] == "no"
    ):
        types.append("reason_family")
    return "+".join(types)


def build_disagreement_appendix(detail: list[dict[str, str]]) -> list[dict[str, str]]:
    rows = []
    for row in detail:
        dtype = disagreement_type(row)
        if not dtype:
            continue
        rows.append({**row, "disagreement_type": dtype})
    return rows


def reason_family_summary_row(
    scope: str,
    source_packet: str,
    reviewer_id: str,
    rows: list[dict[str, str]],
) -> list[dict[str, Any]]:
    families = sorted(
        set(row["original_reason_family"] for row in rows if row["original_reason_family"])
        | set(row["reviewer_reason_family"] for row in rows if row["reviewer_reason_family"])
    )
    output = []
    for family in families:
        original_nonready = [
            row
            for row in rows
            if row["original_binary_ready"] == "no" and row["original_reason_family"] == family
        ]
        matched = [row for row in original_nonready if row["reason_family_match"] == "yes"]
        output.append(
            {
                "scope": scope,
                "source_packet": source_packet,
                "reviewer_id": reviewer_id,
                "reason_family": family,
                "original_count": sum(row["original_reason_family"] == family for row in rows),
                "reviewer_count": sum(row["reviewer_reason_family"] == family for row in rows),
                "matched_count": len(matched),
                "original_nonready_count": len(original_nonready),
                "family_agreement_rate_on_original_nonready": round(len(matched) / len(original_nonready), 6)
                if original_nonready
                else 0.0,
            }
        )
    return output


def build_reason_family_summary(detail: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows = reason_family_summary_row("overall", "all", "all", detail)
    by_packet: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in detail:
        by_packet[(row["source_packet"], row["reviewer_id"])].append(row)
    for (source_packet, reviewer_id), group in sorted(by_packet.items()):
        rows.extend(reason_family_summary_row("source_packet_by_reviewer", source_packet, reviewer_id, group))
    return rows


def claim_gate(overall: dict[str, Any]) -> str:
    if overall["pair_count"] < 200:
        return "INSUFFICIENT_EXTERNAL_REVIEW_ROWS"
    if overall["binary_cohen_kappa"] >= 0.70 and overall["primary_reason_agreement_on_nonready"] >= 0.65:
        return "BLIND_RELIABILITY_STRONG_SUPPORT"
    if overall["binary_cohen_kappa"] >= 0.55:
        return "BLIND_RELIABILITY_MODERATE_SUPPORT"
    return "BLIND_RELIABILITY_WEAK_SUPPORT_REQUIRES_ADJUDICATION"


def build(review_root: Path = DEFAULT_REVIEW_ROOT) -> dict[str, Any]:
    master_rows = read_csv(MASTER_PACKET_CSV)
    review_rows = load_reviews(review_root)
    detail = build_detail(master_rows, review_rows)
    agreement = build_agreement(detail)
    disagreement_appendix = build_disagreement_appendix(detail)
    reason_family_summary = build_reason_family_summary(detail)
    overall = agreement[0] if agreement else agreement_row("overall", "all", "all", [])
    audit = {
        "built_at_utc": utc_now(),
        "status": "PASS" if detail else "FAIL",
        "review_root": project_relative(review_root),
        "master_rows": len(master_rows),
        "raw_review_rows": len(review_rows),
        "usable_review_rows": len(detail),
        "reviewer_counts": dict(sorted(Counter(row["reviewer_id"] for row in detail).items())),
        "disagreement_rows": len(disagreement_appendix),
        "binary_disagreement_rows": sum(row["binary_ready_match"] == "no" for row in detail),
        "reason_family_summary_rows": len(reason_family_summary),
        "overall_agreement": overall,
        "claim_gate": claim_gate(overall),
        "outputs": {
            "detail_csv": project_relative(DETAIL_CSV),
            "agreement_csv": project_relative(AGREEMENT_CSV),
            "disagreement_appendix_csv": project_relative(DISAGREEMENT_APPENDIX_CSV),
            "reason_family_summary_csv": project_relative(REASON_FAMILY_SUMMARY_CSV),
            "audit_json": project_relative(AUDIT_JSON),
            "readme_md": project_relative(README_MD),
        },
    }
    write_csv(DETAIL_CSV, detail, DETAIL_COLUMNS)
    write_csv(AGREEMENT_CSV, agreement, AGREEMENT_COLUMNS)
    write_csv(DISAGREEMENT_APPENDIX_CSV, disagreement_appendix, DISAGREEMENT_COLUMNS)
    write_csv(REASON_FAMILY_SUMMARY_CSV, reason_family_summary, REASON_FAMILY_SUMMARY_COLUMNS)
    write_json(AUDIT_JSON, audit)
    write_readme(audit)
    return audit


def write_readme(audit: dict[str, Any]) -> None:
    overall = audit["overall_agreement"]
    lines = [
        "# Blind Reliability Agreement Analysis",
        "",
        f"Status: `{audit['status']}`",
        f"Claim gate: `{audit['claim_gate']}`",
        "",
        "## Overall Agreement",
        "",
        f"- Usable review rows: `{audit['usable_review_rows']}`",
        f"- Three-class agreement: `{overall['three_class_percent_agreement']}`",
        f"- Binary agreement: `{overall['binary_percent_agreement']}`",
        f"- Binary Cohen kappa: `{overall['binary_cohen_kappa']}`",
        f"- Primary reason agreement on non-ready rows: `{overall['primary_reason_agreement_on_nonready']}`",
        f"- Disagreement appendix rows: `{audit['disagreement_rows']}`",
        f"- Binary disagreement rows: `{audit['binary_disagreement_rows']}`",
        "",
        "## Reason Family Taxonomy",
        "",
        "- `image_evidence_deficit`: low image evidence, blur/night, small subject, partial body, occlusion.",
        "- `pair_non_comparability`: non-comparable viewpoint or non-overlapping body region.",
        "- `descriptor_evidence_conflict`: descriptor evidence conflicts with visual evidence.",
        "- `source_domain_stress`: source/domain stress or wrong/non-target species.",
        "",
        "## Modeling Interpretation",
        "",
        "High blind reliability upgrades user-attested labels from single-reviewer evidence to reliability-supported labels. "
        "Weak reliability does not invalidate exploratory modeling, but it requires adjudication or narrower claims.",
    ]
    README_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review-root", type=Path, default=DEFAULT_REVIEW_ROOT)
    args = parser.parse_args()
    audit = build(args.review_root)
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
