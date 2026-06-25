#!/usr/bin/env python3
"""Audit Phase 12 unified pair/candidate analysis table."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase12"
TABLE = OUT_DIR / "phase12_pair_candidate_analysis_table.csv"
SUMMARY = OUT_DIR / "phase12_pair_candidate_analysis_summary.csv"
BUILD_AUDIT_JSON = OUT_DIR / "phase12_pair_candidate_analysis_build_audit.json"
AUDIT_OUT = OUT_DIR / "phase12_pair_candidate_analysis_table_audit.csv"

REQUIRED_COLUMNS = {
    "split_id",
    "calibration_or_evaluation",
    "descriptor",
    "query_image_id",
    "candidate_image_id",
    "query_identity_token",
    "candidate_identity_token",
    "same_identity",
    "candidate_rank_raw",
    "candidate_rank_pf_eri",
    "is_top1_raw",
    "is_top1_pf_eri",
    "false_candidate",
    "false_top1_raw",
    "false_top1_pf_eri",
    "descriptor_similarity",
    "descriptor_similarity_percentile",
    "reciprocal_rank_support",
    "margin_confidence",
    "margin_confidence_norm",
    "descriptor_disagreement_score",
    "side_comparability_score",
    "pattern_pair_score",
    "blur_pair_score",
    "occlusion_pair_score",
    "body_visibility_pair_score",
    "viewpoint_compatibility_score",
    "pair_reliability_score",
    "image_quality_proxy_min",
    "image_quality_proxy_mean",
    "image_utility_proxy_min",
    "image_utility_proxy_mean",
    "visual_identity_evidence_min",
    "visual_identity_evidence_mean",
    "descriptor_evidence_conflict_score",
    "descriptor_evidence_conflict_margin_score",
    "descriptor_evidence_conflict_disagreement_score",
    "conflict_band",
    "admissibility_band",
    "candidate_utility_rq_score",
    "hard_negative_candidate",
    "review_decision",
    "detection_assisted_fields_available",
    "object_detection_source",
    "detection_box_quality_proxy",
    "domain_shift_proxy_available",
    "domain_diagnostic_note",
}

UNIT_COLUMNS = [
    "descriptor_similarity_percentile",
    "reciprocal_rank_support",
    "margin_confidence_norm",
    "descriptor_disagreement_score",
    "side_comparability_score",
    "pattern_pair_score",
    "blur_pair_score",
    "occlusion_pair_score",
    "body_visibility_pair_score",
    "viewpoint_compatibility_score",
    "pair_reliability_score",
    "image_quality_proxy_min",
    "image_quality_proxy_mean",
    "image_utility_proxy_min",
    "image_utility_proxy_mean",
    "visual_identity_evidence_min",
    "visual_identity_evidence_mean",
    "descriptor_evidence_conflict_score",
    "descriptor_evidence_conflict_margin_score",
    "descriptor_evidence_conflict_disagreement_score",
    "candidate_utility_rq_score",
]

BOOLEAN_COLUMNS = [
    "same_identity",
    "is_top1_raw",
    "is_top1_pf_eri",
    "false_candidate",
    "false_top1_raw",
    "false_top1_pf_eri",
    "hard_negative_candidate",
]

FORBIDDEN_HEADERS = {
    "query_idx",
    "gallery_idx",
    "expanded_image_id",
    "working_individual_id",
    "identity_a",
    "identity_b",
    "query_identity",
    "candidate_identity",
    "review_image_path",
    "review_image_path_local",
    "source_review_image_path_original",
    "path",
    "local_image_path",
    "source",
    "date",
    "encounter",
    "trap_id",
    "camera_id",
    "site",
    "latitude",
    "longitude",
    "cell_code",
}

FORBIDDEN_VALUE_PATTERNS = [
    re.compile(r"/Users/", re.IGNORECASE),
    re.compile(r"data/raw", re.IGNORECASE),
    re.compile(r"(?<![A-Za-z])lynx_[0-9]+", re.IGNORECASE),
    re.compile(r"czlx_expanded_[0-9]+", re.IGNORECASE),
    re.compile(r"\btrap_id\b", re.IGNORECASE),
    re.compile(r"\bcamera_id\b", re.IGNORECASE),
    re.compile(r"\bcell_code\b", re.IGNORECASE),
]


def add(rows: list[dict[str, object]], check: str, passed: bool, detail: str) -> None:
    rows.append({"check": check, "status": "PASS" if passed else "FAIL", "detail": detail})


def main() -> None:
    rows: list[dict[str, object]] = []
    if not TABLE.exists():
        add(rows, "table_exists", False, str(TABLE))
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows).to_csv(AUDIT_OUT, index=False)
        raise SystemExit(1)

    table = pd.read_csv(TABLE)
    add(rows, "table_nonempty", len(table) > 0, f"rows={len(table)}")
    missing = sorted(REQUIRED_COLUMNS - set(table.columns))
    add(rows, "required_columns_present", not missing, f"missing={missing}")
    forbidden_headers = sorted(set(table.columns) & FORBIDDEN_HEADERS)
    add(rows, "no_sensitive_headers", not forbidden_headers, f"forbidden_headers={forbidden_headers}")

    if missing:
        pd.DataFrame(rows).to_csv(AUDIT_OUT, index=False)
        raise SystemExit(1)

    dupes = int(table.duplicated(["split_id", "calibration_or_evaluation", "descriptor", "query_image_id", "candidate_image_id"]).sum())
    add(rows, "no_duplicate_candidate_rows", dupes == 0, f"duplicate_rows={dupes}")
    self_pairs = int((table["query_image_id"].astype(str) == table["candidate_image_id"].astype(str)).sum())
    add(rows, "no_self_candidate_pairs", self_pairs == 0, f"self_pairs={self_pairs}")

    roles = set(table["calibration_or_evaluation"].astype(str))
    add(rows, "split_roles_present", roles == {"calibration", "evaluation"}, f"roles={sorted(roles)}")
    descriptors = set(table["descriptor"].astype(str))
    add(rows, "expected_descriptors_present", descriptors == {"megadescriptor", "resnet50"}, f"descriptors={sorted(descriptors)}")
    split_count = int(table["split_id"].nunique())
    add(rows, "split_count_at_least_20", split_count >= 20, f"split_count={split_count}")

    for column in UNIT_COLUMNS:
        values = pd.to_numeric(table[column], errors="coerce")
        bad = int((values.isna() | (values < 0) | (values > 1)).sum())
        add(rows, f"{column}_unit_interval", bad == 0, f"bad_values={bad}")

    for column in BOOLEAN_COLUMNS:
        values = set(table[column].astype(str).str.lower().unique())
        bad = sorted(values - {"yes", "no"})
        add(rows, f"{column}_yes_no", not bad, f"bad_values={bad}")

    raw_rank = pd.to_numeric(table["candidate_rank_raw"], errors="coerce")
    pf_rank = pd.to_numeric(table["candidate_rank_pf_eri"], errors="coerce")
    add(rows, "raw_rank_valid", bool(((raw_rank >= 1) & (raw_rank <= 20)).all()), f"min={raw_rank.min()} max={raw_rank.max()}")
    add(rows, "pf_eri_rank_valid", bool(((pf_rank >= 1) & (pf_rank <= 20)).all()), f"min={pf_rank.min()} max={pf_rank.max()}")

    expected_false = table["same_identity"].astype(str).str.lower().eq("no")
    observed_false = table["false_candidate"].astype(str).str.lower().eq("yes")
    mismatch = int((expected_false != observed_false).sum())
    add(rows, "false_candidate_matches_same_identity", mismatch == 0, f"mismatches={mismatch}")

    top1_raw_count = table.groupby(["split_id", "calibration_or_evaluation", "descriptor", "query_image_id"])["is_top1_raw"].apply(lambda s: s.astype(str).str.lower().eq("yes").sum())
    bad_top1_raw = int((top1_raw_count != 1).sum())
    add(rows, "exactly_one_raw_top1_per_query", bad_top1_raw == 0, f"bad_query_groups={bad_top1_raw}")
    top1_pf_count = table.groupby(["split_id", "calibration_or_evaluation", "descriptor", "query_image_id"])["is_top1_pf_eri"].apply(lambda s: s.astype(str).str.lower().eq("yes").sum())
    bad_top1_pf = int((top1_pf_count != 1).sum())
    add(rows, "exactly_one_pf_eri_top1_per_query", bad_top1_pf == 0, f"bad_query_groups={bad_top1_pf}")

    leakage = 0
    text_sample = table.astype(str)
    for column in text_sample.columns:
        for value in text_sample[column].head(2000):
            if any(pattern.search(value) for pattern in FORBIDDEN_VALUE_PATTERNS):
                leakage += 1
                break
    add(rows, "no_sensitive_value_patterns_sample", leakage == 0, f"columns_with_sample_leakage={leakage}")

    conflict_values = set(table["conflict_band"].astype(str))
    add(
        rows,
        "conflict_bands_valid",
        conflict_values <= {"minimal_conflict", "low_conflict", "medium_conflict", "high_conflict"},
        f"values={sorted(conflict_values)}",
    )
    adm_values = set(table["admissibility_band"].astype(str))
    add(
        rows,
        "admissibility_bands_valid",
        adm_values <= {"high", "medium", "low", "unusable"},
        f"values={sorted(adm_values)}",
    )

    high_conflict_count = int(table["conflict_band"].eq("high_conflict").sum())
    hard_negative_count = int(table["hard_negative_candidate"].eq("yes").sum())
    add(rows, "rq2_conflict_fields_available", high_conflict_count >= 0 and hard_negative_count >= 0, f"high_conflict={high_conflict_count} hard_negative={hard_negative_count}")
    add(rows, "summary_exists", SUMMARY.exists(), str(SUMMARY))
    add(rows, "build_audit_json_exists", BUILD_AUDIT_JSON.exists(), str(BUILD_AUDIT_JSON))

    if BUILD_AUDIT_JSON.exists():
        build_audit = json.loads(BUILD_AUDIT_JSON.read_text(encoding="utf-8"))
        lineage = build_audit.get("annotation_lineage", {})
        covers_both = bool(lineage.get("active_source_covers_both_500_halves", False))
        active_unique = int(lineage.get("active_annotation_unique_ids", 0))
        phase4_overlap = int(lineage.get("active_overlap_phase4_500_ids", 0))
        phase6_overlap = int(lineage.get("active_overlap_phase6_v2_500_ids", 0))
        add(
            rows,
            "annotation_source_covers_two_500_label_halves",
            covers_both,
            f"active_unique={active_unique} phase4_overlap={phase4_overlap} phase6_overlap={phase6_overlap}",
        )
        add(
            rows,
            "annotation_source_is_1000_unique_ids",
            active_unique >= 1000,
            f"active_unique={active_unique}",
        )

    pd.DataFrame(rows).to_csv(AUDIT_OUT, index=False)
    fail_count = sum(row["status"] == "FAIL" for row in rows)
    pass_count = sum(row["status"] == "PASS" for row in rows)
    print(f"Phase 12A audit: PASS={pass_count} FAIL={fail_count} output={AUDIT_OUT.relative_to(PROJECT_ROOT)}")
    if fail_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
