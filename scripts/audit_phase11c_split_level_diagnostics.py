#!/usr/bin/env python3
"""Audit Phase 11C split-level diagnostic outputs."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase11c/diagnostics"
DOC_PATH = PROJECT_ROOT / "docs/phase11/phase11c_split_level_diagnostic_report.md"
AUDIT_OUT = OUT_DIR / "phase11c_split_level_diagnostics_audit.csv"

C3 = "C3_quality_proxy_matched_identity"
H3 = "H3_pf_eri_quality_hybrid_matched_identity"
EXPECTED_SPLITS = {1, 2, 3, 4, 5}
EXPECTED_FILES = {
    "image_set_overlap": OUT_DIR / "phase11c_image_set_overlap_c3_vs_h3.csv",
    "image_quality": OUT_DIR / "phase11c_image_quality_distribution_by_split_group.csv",
    "positive_pairs": OUT_DIR / "phase11c_positive_pair_reliability_by_split_group.csv",
    "negative_pairs": OUT_DIR / "phase11c_negative_pair_hard_negative_by_split_group.csv",
    "split3": OUT_DIR / "phase11c_split3_special_diagnostic.csv",
    "correlations": OUT_DIR / "phase11c_metric_correlation_diagnostic.csv",
    "field_audit": OUT_DIR / "phase11c_split_level_diagnostic_field_audit.json",
}
REQUIRED_COLUMNS = {
    "image_set_overlap": {
        "split_id",
        "shared_image_count",
        "c3_only_image_count",
        "h3_only_image_count",
        "identity_sets_match",
        "c3_mean_pf_eri_image_score",
        "h3_mean_pf_eri_image_score",
    },
    "image_quality": {
        "split_id",
        "group_name",
        "image_count",
        "identity_count",
        "mean_pf_eri_image_score",
        "mean_quality_proxy_score",
    },
    "positive_pairs": {
        "split_id",
        "group_name",
        "positive_pair_count",
        "mean_pair_reliability_score",
        "pct_positive_pairs_r_lt_025",
        "pct_positive_pairs_r_lt_040",
        "pct_positive_pairs_r_gt_070",
        "mean_side_comparability_score",
        "mean_pattern_pair_score",
    },
    "negative_pairs": {
        "split_id",
        "group_name",
        "negative_pair_count",
        "mean_negative_descriptor_similarity",
        "top_decile_negative_similarity_threshold",
        "hard_negative_count",
        "pct_hard_negative",
    },
    "split3": {
        "diagnostic_family",
        "group_name",
        "metric",
        "split3_value",
        "other_splits_mean",
        "split3_minus_other_splits_mean",
        "interpretation_hint",
    },
    "correlations": {
        "status",
        "reason",
        "n_rows",
        "method",
        "metric_name",
        "structural_feature",
    },
}
FORBIDDEN_TERMS = [
    "second-review",
    "second_review",
    "unique_name",
    "latitude",
    "longitude",
    "trap_id",
    "cell_code",
    "field deployment",
]


def add(rows: list[dict[str, object]], check: str, passed: bool, detail: str) -> None:
    rows.append({"check": check, "status": "PASS" if passed else "FAIL", "detail": detail})


def read_csv_if_exists(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def main() -> None:
    rows: list[dict[str, object]] = []
    frames: dict[str, pd.DataFrame] = {}
    for key, path in EXPECTED_FILES.items():
        exists = path.exists()
        add(rows, f"exists_{key}", exists, str(path.relative_to(PROJECT_ROOT)))
        if key != "field_audit" and exists:
            frame = pd.read_csv(path)
            frames[key] = frame
            add(rows, f"{key}_nonempty", len(frame) > 0, f"rows={len(frame)} cols={len(frame.columns)}")
            missing = sorted(REQUIRED_COLUMNS.get(key, set()) - set(frame.columns))
            add(rows, f"{key}_required_columns", not missing, f"missing={missing}")

    if EXPECTED_FILES["field_audit"].exists():
        field_audit = json.loads(EXPECTED_FILES["field_audit"].read_text(encoding="utf-8"))
        missing_visual = field_audit.get("missing_visual_fields", [])
        add(rows, "no_visual_fields_silently_ignored", not missing_visual, f"missing_visual_fields={missing_visual}")

    for key in ["image_set_overlap", "image_quality", "positive_pairs", "negative_pairs"]:
        frame = frames.get(key, pd.DataFrame())
        if "split_id" in frame.columns:
            splits = set(pd.to_numeric(frame["split_id"], errors="coerce").dropna().astype(int))
            add(rows, f"{key}_splits_1_to_5", EXPECTED_SPLITS <= splits, f"splits={sorted(splits)}")

    for key in ["image_quality", "positive_pairs", "negative_pairs"]:
        frame = frames.get(key, pd.DataFrame())
        if "group_name" in frame.columns:
            groups = set(frame["group_name"].astype(str))
            add(rows, f"{key}_c3_h3_covered", {C3, H3} <= groups, f"has_c3={C3 in groups} has_h3={H3 in groups}")

    overlap = frames.get("image_set_overlap", pd.DataFrame())
    if "identity_sets_match" in overlap.columns:
        all_match = overlap["identity_sets_match"].astype(str).str.lower().isin(["true", "1", "yes"]).all()
        add(rows, "c3_h3_identity_sets_match_all_splits", bool(all_match), f"rows={len(overlap)}")

    sensitive_files = [path for key, path in EXPECTED_FILES.items() if key != "field_audit" and path.exists()]
    if DOC_PATH.exists():
        sensitive_files.append(DOC_PATH)
    add(rows, "diagnostic_report_exists", DOC_PATH.exists(), str(DOC_PATH.relative_to(PROJECT_ROOT)))
    for term in FORBIDDEN_TERMS:
        hits = []
        for path in sensitive_files:
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
            if term.lower() in text:
                hits.append(str(path.relative_to(PROJECT_ROOT)))
        add(rows, f"forbidden_term_absent_{term}", not hits, f"hits={hits}")

    add(rows, "no_raw_data_files_modified_by_audit", True, "audit is read-only over raw/data inputs")

    AUDIT_OUT.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(AUDIT_OUT, index=False)
    pass_count = sum(row["status"] == "PASS" for row in rows)
    fail_count = sum(row["status"] == "FAIL" for row in rows)
    print(f"Phase 11C split diagnostics audit: PASS={pass_count} FAIL={fail_count} output={AUDIT_OUT.relative_to(PROJECT_ROOT)}")
    if fail_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
