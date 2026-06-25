#!/usr/bin/env python3
"""Build calibrated Phase 14 2x2 manual-audit labels from issue details."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = PROJECT_ROOT / "outputs/phase14/phase14_2x2_manual_audit_400"
DEFAULT_REFERENCE = AUDIT_DIR / "phase14_2x2_manual_audit_400_ai_reference.csv"
DEFAULT_ISSUES = AUDIT_DIR / "external_audit/phase14_2x2_label_audit_issue_detail.csv"
DEFAULT_OUT = AUDIT_DIR / "phase14_2x2_manual_audit_400_calibrated_labels.csv"
DEFAULT_SUMMARY = AUDIT_DIR / "phase14_2x2_manual_audit_400_calibration_summary.json"


def resolve(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else PROJECT_ROOT / path


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def value_counts(frame: pd.DataFrame, column: str) -> dict[str, int]:
    if column not in frame.columns:
        return {}
    return {str(k): int(v) for k, v in frame[column].fillna("").astype(str).value_counts().sort_index().items()}


def build_calibrated(reference: pd.DataFrame, issues: pd.DataFrame) -> pd.DataFrame:
    issue_map = issues.set_index("photo_id", drop=False)
    calibrated = reference.copy()
    calibrated["manual_issue_flag"] = calibrated["audit_id"].isin(issue_map.index).map({True: "yes", False: "no"})
    calibrated["manual_issue_severity"] = ""
    calibrated["manual_error_type_raw"] = ""
    calibrated["manual_problem_type_cn"] = ""
    calibrated["manual_specific_problem"] = ""
    calibrated["manual_recommended_action"] = ""

    defaults = {
        "manual_review_bucket": "human_review_bucket",
        "manual_review_confidence": "human_review_confidence",
        "manual_pattern_visibility": "human_pattern_visibility",
        "manual_side_flank_visibility": "human_side_flank_visibility",
        "manual_body_visibility": "human_body_visibility",
        "manual_training_eligible": "training_eligible",
        "manual_stress_test_eligible": "stress_test_eligible",
        "manual_evidence_tier": "evidence_tier",
    }
    for manual_col, original_col in defaults.items():
        calibrated[manual_col] = calibrated[original_col] if original_col in calibrated.columns else ""

    issue_to_manual = {
        "audited_bucket": "manual_review_bucket",
        "audited_confidence": "manual_review_confidence",
        "audited_pattern_visibility": "manual_pattern_visibility",
        "audited_side_flank_visibility": "manual_side_flank_visibility",
        "audited_body_visibility": "manual_body_visibility",
        "audited_training_eligible": "manual_training_eligible",
        "audited_stress_test_eligible": "manual_stress_test_eligible",
        "audited_evidence_tier": "manual_evidence_tier",
        "severity": "manual_issue_severity",
        "error_type_raw": "manual_error_type_raw",
        "problem_type_cn": "manual_problem_type_cn",
        "specific_problem": "manual_specific_problem",
        "recommended_action": "manual_recommended_action",
    }
    for index, row in calibrated[calibrated["manual_issue_flag"].eq("yes")].iterrows():
        issue = issue_map.loc[row["audit_id"]]
        for issue_col, manual_col in issue_to_manual.items():
            calibrated.at[index, manual_col] = issue.get(issue_col, "")

    calibrated["manual_core_high_confidence"] = (
        calibrated["manual_review_bucket"].eq("review_ready")
        & calibrated["manual_training_eligible"].eq("yes")
        & calibrated["manual_evidence_tier"].eq("high_confidence")
    ).map({True: "yes", False: "no"})
    calibrated["manual_clean_stress"] = (
        calibrated["manual_stress_test_eligible"].eq("yes")
        & ~calibrated["manual_review_bucket"].eq("review_ready")
        & calibrated["manual_evidence_tier"].eq("low_evidence_stress")
    ).map({True: "yes", False: "no"})
    calibrated["manual_middle_or_review"] = (
        calibrated["manual_review_bucket"].isin(["review_limited", "uncertain"])
        & calibrated["manual_core_high_confidence"].eq("no")
    ).map({True: "yes", False: "no"})
    return calibrated


def summarize(calibrated: pd.DataFrame, reference_path: Path, issues_path: Path, output_path: Path) -> dict[str, Any]:
    by_quadrant: dict[str, Any] = {}
    for quadrant, group in calibrated.groupby("audit_quadrant", sort=True):
        by_quadrant[str(quadrant)] = {
            "rows": int(len(group)),
            "manual_issue_rows": int(group["manual_issue_flag"].eq("yes").sum()),
            "manual_issue_rate": round(float(group["manual_issue_flag"].eq("yes").mean()), 4),
            "manual_bucket_counts": value_counts(group, "manual_review_bucket"),
            "manual_confidence_counts": value_counts(group, "manual_review_confidence"),
            "manual_evidence_tier_counts": value_counts(group, "manual_evidence_tier"),
            "manual_core_high_confidence": int(group["manual_core_high_confidence"].eq("yes").sum()),
            "manual_clean_stress": int(group["manual_clean_stress"].eq("yes").sum()),
            "manual_middle_or_review": int(group["manual_middle_or_review"].eq("yes").sum()),
            "original_training_eligible": int(group["training_eligible"].eq("yes").sum()),
            "manual_training_eligible": int(group["manual_training_eligible"].eq("yes").sum()),
            "original_stress_test_eligible": int(group["stress_test_eligible"].eq("yes").sum()),
            "manual_stress_test_eligible": int(group["manual_stress_test_eligible"].eq("yes").sum()),
        }
    return {
        "reference_csv": rel(reference_path),
        "issue_detail_csv": rel(issues_path),
        "output_csv": rel(output_path),
        "rows": int(len(calibrated)),
        "issue_rows": int(calibrated["manual_issue_flag"].eq("yes").sum()),
        "non_issue_rows_inferred_unchanged": int(calibrated["manual_issue_flag"].eq("no").sum()),
        "duplicate_audit_ids": int(calibrated["audit_id"].duplicated().sum()),
        "by_quadrant": by_quadrant,
        "interpretation": {
            "status": "original_2x2_ai_labels_are_not_clean_experimental_labels",
            "main_bias": "bobcat_high_overpermissive_and_czechlynx_stress_overstrict",
            "recommended_next_step": "fit_or_define_calibrated_evidence_admission_model_before_rebuilding_full_3000_sets",
        },
        "claim_boundary": "calibrated from 400-image manual audit; use for threshold/model calibration, not final full-dataset human labels",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", default=str(DEFAULT_REFERENCE))
    parser.add_argument("--issues", default=str(DEFAULT_ISSUES))
    parser.add_argument("--output", default=str(DEFAULT_OUT))
    parser.add_argument("--summary", default=str(DEFAULT_SUMMARY))
    args = parser.parse_args()

    reference_path = resolve(args.reference)
    issues_path = resolve(args.issues)
    output_path = resolve(args.output)
    summary_path = resolve(args.summary)
    reference = pd.read_csv(reference_path)
    issues = pd.read_csv(issues_path)
    unmatched = sorted(set(issues["photo_id"].astype(str)) - set(reference["audit_id"].astype(str)))
    if unmatched:
        raise ValueError(f"issue rows not found in reference audit_id: {unmatched[:5]}")
    calibrated = build_calibrated(reference, issues)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    calibrated.to_csv(output_path, index=False)
    summary = summarize(calibrated, reference_path, issues_path, output_path)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "PASS phase14 2x2 manual audit calibration "
        f"rows={len(calibrated)} issues={summary['issue_rows']} output={rel(output_path)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
