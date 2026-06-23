#!/usr/bin/env python3
"""Audit Phase 14 FCF bobcat auto prefeatures and review batch."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LABEL_DIR = PROJECT_ROOT / "data/external/felidae_conservation_fund/labels"
REVIEW_DIR = PROJECT_ROOT / "data/external/felidae_conservation_fund/review_batches"
PREFEATURES = LABEL_DIR / "fcf_bobcat_3000_auto_prefeatures.csv"
PREFEATURE_SUMMARY = LABEL_DIR / "fcf_bobcat_3000_auto_prefeatures_summary.json"
REVIEW = REVIEW_DIR / "fcf_bobcat_400_human_review_manifest.csv"
REVIEW_AUDIT = REVIEW_DIR / "fcf_bobcat_400_human_review_manifest_audit.json"
AUDIT_OUT = LABEL_DIR / "fcf_bobcat_3000_auto_prefeatures_audit.csv"

REQUIRED_PREFEATURE_COLUMNS = {
    "sample_index",
    "image_id",
    "local_relative_path",
    "image_exists",
    "auto_prefeature_status",
    "auto_review_bucket",
    "auto_evidence_score",
    "auto_quality_score",
    "auto_night_ir",
    "auto_blur_band",
    "auto_exposure_band",
    "auto_contrast_band",
    "auto_center_animal_signal",
    "auto_failure_flags",
}

REQUIRED_HUMAN_COLUMNS = {
    "human_pattern_visibility",
    "human_side_flank_visibility",
    "human_body_visibility",
    "human_blur_level",
    "human_occlusion_level",
    "human_background_complexity",
    "human_modified_background",
    "human_review_bucket",
    "human_review_confidence",
    "human_notes",
}


def add(rows: list[dict[str, object]], check: str, passed: bool, detail: str) -> None:
    rows.append({"check": check, "status": "PASS" if passed else "FAIL", "detail": detail})


def main() -> int:
    rows: list[dict[str, object]] = []
    add(rows, "prefeatures_exists", PREFEATURES.exists(), str(PREFEATURES.relative_to(PROJECT_ROOT)))
    add(rows, "review_exists", REVIEW.exists(), str(REVIEW.relative_to(PROJECT_ROOT)))
    add(rows, "prefeature_summary_exists", PREFEATURE_SUMMARY.exists(), str(PREFEATURE_SUMMARY.relative_to(PROJECT_ROOT)))
    add(rows, "review_audit_exists", REVIEW_AUDIT.exists(), str(REVIEW_AUDIT.relative_to(PROJECT_ROOT)))
    if not PREFEATURES.exists() or not REVIEW.exists():
        pd.DataFrame(rows).to_csv(AUDIT_OUT, index=False)
        return 1

    pre = pd.read_csv(PREFEATURES)
    review = pd.read_csv(REVIEW)
    missing_pre = sorted(REQUIRED_PREFEATURE_COLUMNS - set(pre.columns))
    add(rows, "prefeature_required_columns", not missing_pre, f"missing={missing_pre}")
    missing_human = sorted(REQUIRED_HUMAN_COLUMNS - set(review.columns))
    add(rows, "review_human_columns_present", not missing_human, f"missing={missing_human}")
    add(rows, "prefeature_row_count_3000", len(pre) == 3000, f"rows={len(pre)}")
    add(rows, "review_row_count_400", len(review) == 400, f"rows={len(review)}")
    add(rows, "prefeature_no_failed_rows", int(pre["auto_prefeature_status"].ne("ok").sum()) == 0, f"failed={int(pre['auto_prefeature_status'].ne('ok').sum())}")
    add(rows, "prefeature_no_duplicate_images", int(pre["image_id"].duplicated().sum()) == 0, f"dupes={int(pre['image_id'].duplicated().sum())}")
    add(rows, "review_no_duplicate_images", int(review["image_id"].duplicated().sum()) == 0, f"dupes={int(review['image_id'].duplicated().sum())}")
    missing_review_images = sorted(set(review["image_id"]) - set(pre["image_id"]))
    add(rows, "review_subset_of_prefeatures", not missing_review_images, f"missing={len(missing_review_images)}")

    missing_files = 0
    for path_text in pre["local_relative_path"]:
        if not (PROJECT_ROOT / str(path_text)).exists():
            missing_files += 1
    add(rows, "all_prefeature_images_exist", missing_files == 0, f"missing_files={missing_files}")

    for column in ["auto_evidence_score", "auto_quality_score"]:
        values = pd.to_numeric(pre[column], errors="coerce")
        bad = int((values.isna() | (values < 0) | (values > 1)).sum())
        add(rows, f"{column}_unit_interval", bad == 0, f"bad={bad}")

    summary = json.loads(PREFEATURE_SUMMARY.read_text(encoding="utf-8"))
    add(rows, "summary_failed_count_zero", int(summary.get("failed_count", -1)) == 0, f"failed={summary.get('failed_count')}")
    review_audit = json.loads(REVIEW_AUDIT.read_text(encoding="utf-8"))
    add(rows, "review_location_count_min_100", int(review_audit.get("location_count", 0)) >= 100, f"locations={review_audit.get('location_count')}")
    add(rows, "review_includes_night_ir", int(review_audit.get("night_ir_counts", {}).get("yes", 0)) > 0, f"night_ir={review_audit.get('night_ir_counts')}")

    audit = pd.DataFrame(rows)
    AUDIT_OUT.parent.mkdir(parents=True, exist_ok=True)
    audit.to_csv(AUDIT_OUT, index=False)
    fail_count = int(audit["status"].eq("FAIL").sum())
    print(
        f"{'PASS' if fail_count == 0 else 'FAIL'} phase14 FCF bobcat prefeature audit "
        f"checks={len(audit)} failures={fail_count} output={AUDIT_OUT.relative_to(PROJECT_ROOT)}"
    )
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
