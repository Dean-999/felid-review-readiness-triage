#!/usr/bin/env python3
"""Fill AI-assisted first-pass human-review labels for FCF bobcat review batch."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REVIEW_DIR = PROJECT_ROOT / "data/external/felidae_conservation_fund/review_batches"
DEFAULT_INPUT = REVIEW_DIR / "fcf_bobcat_400_human_review_manifest.csv"
DEFAULT_OUTPUT = REVIEW_DIR / "fcf_bobcat_400_human_review_ai_filled.csv"
DEFAULT_UNCERTAIN = REVIEW_DIR / "fcf_bobcat_400_needs_manual_check.csv"
DEFAULT_AUDIT = REVIEW_DIR / "fcf_bobcat_400_human_review_ai_filled_audit.json"


def map_pattern(row: pd.Series) -> str:
    score = float(row["auto_evidence_score"])
    center = str(row["auto_center_animal_signal"])
    contrast = str(row["auto_contrast_band"])
    if center == "strong" and score >= 0.78:
        return "high"
    if center in {"strong", "medium"} and score >= 0.58 and contrast != "low":
        return "medium"
    if center != "weak" and score >= 0.40:
        return "low"
    if "likely_night_ir" in str(row["auto_failure_flags"]) and score < 0.45:
        return "none"
    return "low"


def map_side(row: pd.Series) -> str:
    center = str(row["auto_center_animal_signal"])
    if center == "strong":
        return "unknown"
    if center == "medium":
        return "unknown"
    return "unknown"


def map_body(row: pd.Series) -> str:
    center = str(row["auto_center_animal_signal"])
    score = float(row["auto_evidence_score"])
    if center == "strong" and score >= 0.75:
        return "76_100"
    if center in {"strong", "medium"} and score >= 0.55:
        return "51_75"
    if center == "medium" or score >= 0.38:
        return "26_50"
    return "0_25"


def map_blur(row: pd.Series) -> str:
    band = str(row["auto_blur_band"])
    if band in {"none", "mild", "moderate", "severe"}:
        return band
    return "unknown"


def map_occlusion(row: pd.Series) -> str:
    center = str(row["auto_center_animal_signal"])
    flags = str(row["auto_failure_flags"])
    if center == "weak":
        return "major"
    if "weak_center_animal_signal" in flags:
        return "partial"
    return "none"


def map_background(row: pd.Series) -> str:
    edge = float(row.get("edge_density", 0.0))
    if edge >= 0.18:
        return "high"
    if edge >= 0.06:
        return "medium"
    return "low"


def map_modified_background(row: pd.Series) -> str:
    # No reliable built-environment detector is available in this pass.
    return "uncertain"


def map_review_bucket(row: pd.Series) -> str:
    auto_bucket = str(row["auto_review_bucket"])
    mapping = {
        "likely_review_ready": "review_ready",
        "review_limited": "review_limited",
        "likely_species_level_only": "species_level_only",
        "defer_manual_check": "uncertain",
    }
    return mapping.get(auto_bucket, "uncertain")


def confidence_and_notes(row: pd.Series, labels: dict[str, str]) -> tuple[str, str, str]:
    score = float(row["auto_evidence_score"])
    flags = [flag for flag in str(row["auto_failure_flags"]).split("|") if flag]
    auto_bucket = str(row["auto_review_bucket"])
    review_bucket = labels["human_review_bucket"]
    reasons: list[str] = []
    needs_check = False

    if auto_bucket == "defer_manual_check":
        needs_check = True
        reasons.append("auto_defer")
    if row["auto_night_ir"] == "yes":
        needs_check = True
        reasons.append("night_ir")
    if "weak_center_animal_signal" in flags:
        needs_check = True
        reasons.append("weak_center_signal")
    if "possible_exposure_issue" in flags:
        reasons.append("possible_exposure_issue")
    if "low_contrast" in flags:
        reasons.append("low_contrast")
    if review_bucket in {"review_limited", "species_level_only"} and 0.48 <= score <= 0.66:
        needs_check = True
        reasons.append("boundary_score")
    if labels["human_pattern_visibility"] in {"none", "low"} and review_bucket == "review_ready":
        needs_check = True
        reasons.append("pattern_review_conflict")

    if needs_check:
        confidence = "low"
    elif reasons:
        confidence = "medium"
    else:
        confidence = "high"
    notes = ";".join(reasons) if reasons else "ai_first_pass"
    return confidence, notes, "yes" if needs_check else "no"


def fill_row(row: pd.Series) -> dict[str, str]:
    labels = {
        "human_pattern_visibility": map_pattern(row),
        "human_side_flank_visibility": map_side(row),
        "human_body_visibility": map_body(row),
        "human_blur_level": map_blur(row),
        "human_occlusion_level": map_occlusion(row),
        "human_background_complexity": map_background(row),
        "human_modified_background": map_modified_background(row),
        "human_review_bucket": map_review_bucket(row),
    }
    confidence, notes, needs_check = confidence_and_notes(row, labels)
    labels["human_review_confidence"] = confidence
    labels["human_notes"] = notes
    labels["needs_manual_check"] = needs_check
    labels["ai_fill_status"] = "ai_first_pass"
    return labels


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--uncertain-output", default=str(DEFAULT_UNCERTAIN))
    parser.add_argument("--audit", default=str(DEFAULT_AUDIT))
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    uncertain_path = Path(args.uncertain_output)
    audit_path = Path(args.audit)
    if not input_path.is_absolute():
        input_path = PROJECT_ROOT / input_path
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path
    if not uncertain_path.is_absolute():
        uncertain_path = PROJECT_ROOT / uncertain_path
    if not audit_path.is_absolute():
        audit_path = PROJECT_ROOT / audit_path

    review = pd.read_csv(input_path)
    if "review_index" not in review.columns:
        review.insert(0, "review_index", range(1, len(review) + 1))
    filled_rows: list[dict[str, Any]] = []
    for _, row in review.iterrows():
        base = row.to_dict()
        base.update(fill_row(row))
        filled_rows.append(base)
    filled = pd.DataFrame(filled_rows)
    uncertain = filled[filled["needs_manual_check"].eq("yes")].copy()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    filled.to_csv(output_path, index=False)
    uncertain.to_csv(uncertain_path, index=False)
    audit = {
        "input": str(input_path.relative_to(PROJECT_ROOT)),
        "output": str(output_path.relative_to(PROJECT_ROOT)),
        "uncertain_output": str(uncertain_path.relative_to(PROJECT_ROOT)),
        "row_count": int(len(filled)),
        "needs_manual_check_count": int(len(uncertain)),
        "human_review_bucket_counts": {str(k): int(v) for k, v in filled["human_review_bucket"].value_counts().sort_index().items()},
        "human_review_confidence_counts": {str(k): int(v) for k, v in filled["human_review_confidence"].value_counts().sort_index().items()},
        "claim_boundary": "ai_first_pass_review_labels_require_human_audit_before_ground_truth_use",
    }
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "PASS phase14 FCF bobcat AI-filled review labels "
        f"rows={len(filled)} needs_manual_check={len(uncertain)} output={output_path.relative_to(PROJECT_ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
