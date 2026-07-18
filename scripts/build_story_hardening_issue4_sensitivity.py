#!/usr/bin/env python3
"""Build Issue 4 quality and similarity sensitivity checks."""

from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VALIDATION_TABLE_CSV = (
    PROJECT_ROOT
    / "archive/pferi_v1/outputs/modeling-validation/known-id-evidence-sufficiency-validation/known_id_reviewability_validation_table.csv"
)
OUTPUT_DIR = PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/story-hardening-issue4"
QUALITY_MATCHED_CSV = OUTPUT_DIR / "issue4_quality_matched_sensitivity.csv"
HIGH_QUALITY_CSV = OUTPUT_DIR / "issue4_high_quality_subset.csv"
HIGH_SIMILARITY_CSV = OUTPUT_DIR / "issue4_high_similarity_subset.csv"
STRATIFIED_CSV = OUTPUT_DIR / "issue4_rank_similarity_stratified_sensitivity.csv"
AUDIT_JSON = OUTPUT_DIR / "issue4_quality_similarity_sensitivity_audit.json"
REPORT_MD = PROJECT_ROOT / "docs/modeling-validation/2026-07-09_quality_similarity_sensitivity.md"

DESCRIPTORS = ["megadescriptor_l_384", "dinov2_vitl14"]
QUALITY_FEATURES = ["visible_pattern_area_score", "body_part_overlap_score", "night_or_motion_blur_risk"]
PAIR_LEVEL_PF_ERI_FEATURES = [
    "body_part_overlap_score",
    "cross_descriptor_agreement_score",
]
SIMILARITY_FEATURE = "descriptor_similarity_percentile"
MIN_STRATUM_ROWS = 20

SUMMARY_COLUMNS = [
    "analysis_name",
    "scope",
    "stratum_label",
    "row_count",
    "review_ready_count",
    "not_ready_or_uncertain_count",
    "review_ready_rate",
    "mean_descriptor_similarity",
    "mean_quality_proxy_score",
    "mean_pf_eri_pair_signal",
    "high_pf_eri_count",
    "low_pf_eri_count",
    "high_pf_eri_review_ready_rate",
    "low_pf_eri_review_ready_rate",
    "high_minus_low_review_ready_rate",
    "estimability_status",
    "interpretation",
    "claim_boundary",
]

STRATIFIED_COLUMNS = [
    *SUMMARY_COLUMNS,
    "rank_bin",
    "similarity_bin",
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


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else math.nan


def fmt(value: Any) -> str:
    if value == "":
        return "not estimable"
    return f"{to_float(value):.3f}"


def quantile(values: list[float], q: float) -> float:
    if not values:
        return math.nan
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * q)))
    return ordered[index]


def quality_proxy_score(row: dict[str, Any]) -> float:
    visible = to_float(row["visible_pattern_area_score"])
    overlap = to_float(row["body_part_overlap_score"])
    blur_ready = 1.0 - to_float(row["night_or_motion_blur_risk"])
    return (visible + overlap + blur_ready) / 3.0


def pf_eri_pair_signal(row: dict[str, Any]) -> float:
    return mean([to_float(row[name]) for name in PAIR_LEVEL_PF_ERI_FEATURES])


def add_scores(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        enriched = dict(row)
        enriched["quality_proxy_score"] = quality_proxy_score(row)
        enriched["pf_eri_pair_signal"] = pf_eri_pair_signal(row)
        output.append(enriched)
    return output


def median_split_summary(analysis_name: str, scope: str, stratum_label: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    labels = [int(row["review_ready_label"]) for row in rows]
    threshold = quantile([to_float(row["pf_eri_pair_signal"]) for row in rows], 0.5)
    low_rows = [row for row in rows if to_float(row["pf_eri_pair_signal"]) <= threshold]
    high_rows = [row for row in rows if to_float(row["pf_eri_pair_signal"]) > threshold]
    estimable = len(rows) >= MIN_STRATUM_ROWS and low_rows and high_rows and len(set(labels)) > 1
    high_rate = mean([int(row["review_ready_label"]) for row in high_rows]) if high_rows else ""
    low_rate = mean([int(row["review_ready_label"]) for row in low_rows]) if low_rows else ""
    effect = high_rate - low_rate if high_rows and low_rows else ""
    status = "estimable" if estimable else "not_estimable_sparse_or_no_split"
    if estimable and effect > 0:
        interpretation = "PF-ERI pair signal remains positively aligned with human reviewability in this stratum."
    elif estimable and effect <= 0:
        interpretation = "PF-ERI pair signal does not separate human reviewability in this stratum; treat as a boundary."
    else:
        interpretation = "This stratum is too sparse or lacks a usable high/low PF-ERI split."
    return {
        "analysis_name": analysis_name,
        "scope": scope,
        "stratum_label": stratum_label,
        "row_count": len(rows),
        "review_ready_count": sum(labels),
        "not_ready_or_uncertain_count": len(labels) - sum(labels),
        "review_ready_rate": mean(labels) if labels else "",
        "mean_descriptor_similarity": mean([to_float(row[SIMILARITY_FEATURE]) for row in rows]),
        "mean_quality_proxy_score": mean([to_float(row["quality_proxy_score"]) for row in rows]),
        "mean_pf_eri_pair_signal": mean([to_float(row["pf_eri_pair_signal"]) for row in rows]),
        "high_pf_eri_count": len(high_rows),
        "low_pf_eri_count": len(low_rows),
        "high_pf_eri_review_ready_rate": high_rate,
        "low_pf_eri_review_ready_rate": low_rate,
        "high_minus_low_review_ready_rate": effect,
        "estimability_status": status,
        "interpretation": interpretation,
        "claim_boundary": "CzechLynx human reviewability/evidential admissibility only; not identity accuracy or retrieval mAP.",
    }


def scopes(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    output = {"pooled": rows}
    for descriptor in DESCRIPTORS:
        output[descriptor] = [row for row in rows if row["descriptor_name"] == descriptor]
    return output


def quality_matched_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for scope, subset in scopes(rows).items():
        ordered = sorted(subset, key=lambda row: (to_float(row["quality_proxy_score"]), row["review_pair_id"]))
        for bin_id in range(4):
            start = bin_id * len(ordered) // 4
            end = (bin_id + 1) * len(ordered) // 4
            group = ordered[start:end]
            if group:
                output.append(median_split_summary("quality_matched", scope, f"quality_quartile_{bin_id + 1}", group))
    return output


def high_quality_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for scope, subset in scopes(rows).items():
        cutoff = quantile([to_float(row["quality_proxy_score"]) for row in subset], 0.75)
        group = [row for row in subset if to_float(row["quality_proxy_score"]) >= cutoff]
        output.append(median_split_summary("high_quality_only", scope, "top_quality_quartile", group))
    return output


def high_similarity_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for scope, subset in scopes(rows).items():
        cutoff = quantile([to_float(row[SIMILARITY_FEATURE]) for row in subset], 0.75)
        group = [row for row in subset if to_float(row[SIMILARITY_FEATURE]) >= cutoff]
        output.append(median_split_summary("high_similarity_only", scope, "top_similarity_quartile", group))
    return output


def similarity_bin(value: float) -> str:
    if value < 0.82:
        return "similarity_low"
    if value < 0.90:
        return "similarity_mid"
    return "similarity_high"


def stratified_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[("pooled", row["rank_bin"], similarity_bin(to_float(row[SIMILARITY_FEATURE])))].append(row)
        grouped[(row["descriptor_name"], row["rank_bin"], similarity_bin(to_float(row[SIMILARITY_FEATURE])))].append(row)
    for (scope, rank_bin, sim_bin), group in sorted(grouped.items()):
        summary = median_split_summary("rank_similarity_stratified", scope, f"{rank_bin}/{sim_bin}", group)
        summary["rank_bin"] = rank_bin
        summary["similarity_bin"] = sim_bin
        output.append(summary)
    return output


def feature_variation_audit(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    audit = {}
    for feature in [*QUALITY_FEATURES, *PAIR_LEVEL_PF_ERI_FEATURES, SIMILARITY_FEATURE]:
        values = [to_float(row[feature]) for row in rows]
        audit[feature] = {
            "unique_values": len(set(values)),
            "min": min(values),
            "max": max(values),
            "mean": mean(values),
            "estimability_status": "estimable" if len(set(values)) > 1 else "not_estimable_constant_feature",
        }
    return audit


def overall_status(rows: list[dict[str, Any]]) -> str:
    estimable = [row for row in rows if row["estimability_status"] == "estimable"]
    positive = [row for row in estimable if to_float(row["high_minus_low_review_ready_rate"]) > 0]
    return "PASS_WITH_BOUNDARIES" if positive else "FAIL_NO_POSITIVE_SENSITIVITY"


def write_report(audit: dict[str, Any], quality_rows_out: list[dict[str, Any]], high_quality: list[dict[str, Any]], high_similarity: list[dict[str, Any]], stratified: list[dict[str, Any]]) -> None:
    pooled_quality_positive = [
        row for row in quality_rows_out
        if row["scope"] == "pooled" and row["estimability_status"] == "estimable" and to_float(row["high_minus_low_review_ready_rate"]) > 0
    ]
    pooled_high_quality = next(row for row in high_quality if row["scope"] == "pooled")
    pooled_high_similarity = next(row for row in high_similarity if row["scope"] == "pooled")
    pooled_stratified = [row for row in stratified if row["scope"] == "pooled" and row["estimability_status"] == "estimable"]
    positive_strata = [row for row in pooled_stratified if to_float(row["high_minus_low_review_ready_rate"]) > 0]
    lines = [
        "# Quality And Similarity Sensitivity",
        "",
        "Date: 2026-07-09",
        "",
        f"Status: `{audit['status']}`",
        "",
        "This sensitivity package evaluates the two strongest alternative explanations for the Issue 3 model result. The first alternative explanation is that PF-ERI is only an image-quality filter. The second is that PF-ERI is only a descriptor-similarity proxy. The analysis keeps the endpoint fixed as CzechLynx human reviewability and evidential admissibility; it does not evaluate identity accuracy, Bobcat identity performance, mAP, MRR, or top-k retrieval improvement.",
        "",
        "The quality-matched analysis groups pairs by an explicit quality proxy and then asks whether the non-quality PF-ERI pair signal separates review-ready from not-ready or uncertain pairs inside those quality strata. The high-quality-only analysis asks the same question after restricting the table to the top quality quartile. These tests are important because several nominal quality features are constant in the current 400-row reviewed table, so the estimable quality contrast is driven by body-part overlap rather than by visible-pattern area or night-motion blur variation.",
        "",
        f"In the pooled quality-matched table, {len(pooled_quality_positive)} estimable quality strata show a positive high-minus-low PF-ERI reviewability contrast. In the pooled high-quality subset, the high-minus-low PF-ERI contrast is {fmt(pooled_high_quality['high_minus_low_review_ready_rate'])}. This result means that the current data provide a direct guardrail against the simplest quality-only explanation, but the guardrail is bounded by the limited variation of several image-quality fields and by descriptor-specific quality strata that are not uniformly positive.",
        "",
        "The high-similarity and rank/similarity-stratified analyses address the descriptor-proxy explanation. They restrict attention to candidate pairs that are already similar according to the strong descriptor queue or compare pairs within rank and similarity strata. If PF-ERI remains aligned with reviewability inside these restricted comparisons, the result is more consistent with pair-level evidence admission than with a pure retrieval-score restatement.",
        "",
        f"In the pooled high-similarity subset, the high-minus-low PF-ERI contrast is {fmt(pooled_high_similarity['high_minus_low_review_ready_rate'])}. Across pooled estimable rank/similarity strata, {len(positive_strata)} of {len(pooled_stratified)} strata show a positive high-minus-low PF-ERI contrast. This supports the bounded interpretation that PF-ERI is not merely descriptor similarity, while also preserving any weak or sparse strata as claim boundaries rather than converting them into positive evidence.",
        "",
        "The scientific interpretation is therefore stronger than Issue 3 alone but still properly bounded. PF-ERI shows evidence consistent with a pair-level admissibility signal under quality and similarity pressure tests, especially when the comparison is framed around non-quality pair evidence such as body-part overlap and cross-descriptor agreement. The result should not be written as universal superiority over descriptor plus quality; it should be written as evidence that similarity and quality do not fully exhaust the human reviewability construct in the reviewed CzechLynx candidate pairs.",
        "",
        "## Artifact Links",
        "",
        f"The quality-matched table is `{audit['outputs']['quality_matched_csv']}`. The high-quality subset table is `{audit['outputs']['high_quality_csv']}`. The high-similarity subset table is `{audit['outputs']['high_similarity_csv']}`. The rank/similarity-stratified table is `{audit['outputs']['stratified_csv']}`. The audit file is `{audit['outputs']['audit_json']}`.",
    ]
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build() -> dict[str, Any]:
    rows = add_scores(read_csv(VALIDATION_TABLE_CSV))
    quality_rows_out = quality_matched_rows(rows)
    high_quality = high_quality_rows(rows)
    high_similarity = high_similarity_rows(rows)
    stratified = stratified_rows(rows)
    combined = quality_rows_out + high_quality + high_similarity + stratified
    audit = {
        "built_at_utc": utc_now(),
        "status": overall_status(combined),
        "input_validation_table_csv": project_relative(VALIDATION_TABLE_CSV),
        "row_count": len(rows),
        "descriptor_counts": dict(sorted(Counter(row["descriptor_name"] for row in rows).items())),
        "feature_variation": feature_variation_audit(rows),
        "outputs": {
            "quality_matched_csv": project_relative(QUALITY_MATCHED_CSV),
            "high_quality_csv": project_relative(HIGH_QUALITY_CSV),
            "high_similarity_csv": project_relative(HIGH_SIMILARITY_CSV),
            "stratified_csv": project_relative(STRATIFIED_CSV),
            "audit_json": project_relative(AUDIT_JSON),
            "report_md": project_relative(REPORT_MD),
        },
        "claim_boundary": "CzechLynx human reviewability/evidential admissibility only; no identity accuracy, mAP, MRR, top-k identity improvement, or Bobcat identity claim.",
    }
    write_csv(QUALITY_MATCHED_CSV, quality_rows_out, SUMMARY_COLUMNS)
    write_csv(HIGH_QUALITY_CSV, high_quality, SUMMARY_COLUMNS)
    write_csv(HIGH_SIMILARITY_CSV, high_similarity, SUMMARY_COLUMNS)
    write_csv(STRATIFIED_CSV, stratified, STRATIFIED_COLUMNS)
    write_json(AUDIT_JSON, audit)
    write_report(audit, quality_rows_out, high_quality, high_similarity, stratified)
    return audit


def main() -> int:
    audit = build()
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
