#!/usr/bin/env python3
"""Refine FCF bobcat AI first-pass confidence without treating labels as ground truth."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REVIEW_DIR = PROJECT_ROOT / "data/external/felidae_conservation_fund/review_batches"
DEFAULT_INPUT = REVIEW_DIR / "fcf_bobcat_3000_ai_first_pass_review_labels.csv"
DEFAULT_OUTPUT = REVIEW_DIR / "fcf_bobcat_3000_ai_refined_review_labels.csv"
DEFAULT_MANUAL = REVIEW_DIR / "fcf_bobcat_3000_refined_needs_manual_check.csv"
DEFAULT_PROMOTED = REVIEW_DIR / "fcf_bobcat_3000_confidence_promoted_stable_boundary.csv"
DEFAULT_AUDIT = REVIEW_DIR / "fcf_bobcat_3000_confidence_refinement_audit.json"

RISK_NOTE_TOKENS = (
    "night_ir",
    "weak_center_signal",
    "auto_defer",
    "pattern_review_conflict",
    "possible_exposure_issue",
    "low_contrast",
)


def resolve(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else PROJECT_ROOT / path


def is_stable_boundary(row: pd.Series) -> bool:
    notes = str(row.get("human_notes", ""))
    if "boundary_score" not in notes:
        return False
    if any(token in notes for token in RISK_NOTE_TOKENS):
        return False
    if row.get("human_review_bucket") != "review_limited":
        return False
    if row.get("auto_center_animal_signal") not in {"medium", "strong"}:
        return False
    if row.get("auto_blur_band") not in {"none", "mild"}:
        return False
    if row.get("auto_exposure_band") not in {"limited", "good", "strong"}:
        return False
    if row.get("auto_contrast_band") not in {"medium", "high"}:
        return False
    if row.get("auto_night_ir") == "yes":
        return False
    evidence = float(row.get("auto_evidence_score", 0.0))
    quality = float(row.get("auto_quality_score", 0.0))
    return evidence >= 0.50 and quality >= 0.57


def risk_group(row: pd.Series) -> str:
    notes = str(row.get("human_notes", ""))
    if "night_ir" in notes:
        return "night_ir"
    if "auto_defer" in notes:
        return "auto_defer"
    if "pattern_review_conflict" in notes:
        return "pattern_review_conflict"
    if "weak_center_signal" in notes:
        return "weak_center_signal"
    if "possible_exposure_issue" in notes:
        return "possible_exposure_issue"
    if "low_contrast" in notes:
        return "low_contrast"
    if "boundary_score" in notes:
        return "boundary_score_only"
    return "other_low_confidence"


def refine(table: pd.DataFrame) -> pd.DataFrame:
    refined_rows: list[dict[str, Any]] = []
    for _, row in table.iterrows():
        item = row.to_dict()
        item["first_pass_human_review_confidence"] = item.get("human_review_confidence", "")
        item["first_pass_needs_manual_check"] = item.get("needs_manual_check", "")
        item["confidence_refinement_action"] = "unchanged"
        item["confidence_refinement_reason"] = risk_group(row)

        if str(row.get("human_review_confidence")) == "low" and is_stable_boundary(row):
            item["human_review_confidence"] = "medium"
            item["needs_manual_check"] = "no"
            notes = str(item.get("human_notes", ""))
            item["human_notes"] = notes.replace("boundary_score", "stable_boundary_resolved")
            item["confidence_refinement_action"] = "promoted_low_to_medium"
            item["confidence_refinement_reason"] = (
                "stable_boundary_no_night_no_weak_signal_no_exposure_or_contrast_flag"
            )
        refined_rows.append(item)
    return pd.DataFrame(refined_rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--manual-output", default=str(DEFAULT_MANUAL))
    parser.add_argument("--promoted-output", default=str(DEFAULT_PROMOTED))
    parser.add_argument("--audit", default=str(DEFAULT_AUDIT))
    args = parser.parse_args()

    input_path = resolve(args.input)
    output_path = resolve(args.output)
    manual_path = resolve(args.manual_output)
    promoted_path = resolve(args.promoted_output)
    audit_path = resolve(args.audit)

    table = pd.read_csv(input_path)
    refined = refine(table)
    manual = refined[refined["needs_manual_check"].eq("yes")].copy()
    promoted = refined[refined["confidence_refinement_action"].eq("promoted_low_to_medium")].copy()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    refined.to_csv(output_path, index=False)
    manual.to_csv(manual_path, index=False)
    promoted.to_csv(promoted_path, index=False)

    audit = {
        "input": str(input_path.relative_to(PROJECT_ROOT)),
        "output": str(output_path.relative_to(PROJECT_ROOT)),
        "manual_output": str(manual_path.relative_to(PROJECT_ROOT)),
        "promoted_output": str(promoted_path.relative_to(PROJECT_ROOT)),
        "row_count": int(len(refined)),
        "first_pass_needs_manual_check_count": int(table["needs_manual_check"].eq("yes").sum()),
        "refined_needs_manual_check_count": int(refined["needs_manual_check"].eq("yes").sum()),
        "promoted_low_to_medium_count": int(len(promoted)),
        "human_review_confidence_counts": {
            str(k): int(v)
            for k, v in refined["human_review_confidence"].value_counts().sort_index().items()
        },
        "manual_check_reason_counts": {
            str(k): int(v)
            for k, v in manual["confidence_refinement_reason"].value_counts().sort_index().items()
        },
        "claim_boundary": "confidence_refinement_for_review_prioritization_not_ground_truth_labels",
    }
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "PASS phase14 FCF bobcat confidence refinement "
        f"rows={len(refined)} promoted={len(promoted)} "
        f"manual_remaining={len(manual)} output={output_path.relative_to(PROJECT_ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
