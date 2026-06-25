#!/usr/bin/env python3
"""Prioritize the most important manual checks from AI-filled FCF bobcat labels."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REVIEW_DIR = PROJECT_ROOT / "data/external/felidae_conservation_fund/review_batches"
DEFAULT_FILLED = REVIEW_DIR / "fcf_bobcat_400_human_review_ai_filled.csv"
DEFAULT_OUT = REVIEW_DIR / "fcf_bobcat_120_priority_manual_check.csv"
DEFAULT_AUDIT = REVIEW_DIR / "fcf_bobcat_120_priority_manual_check_audit.json"


def priority_score(row: pd.Series) -> float:
    score = 0.0
    notes = str(row.get("human_notes", ""))
    if row.get("auto_night_ir") == "yes":
        score += 4.0
    if "auto_defer" in notes:
        score += 4.0
    if "weak_center_signal" in notes:
        score += 3.0
    if "boundary_score" in notes:
        score += 2.5
    if "possible_exposure_issue" in notes:
        score += 1.5
    if "low_contrast" in notes:
        score += 1.5
    evidence = float(row.get("auto_evidence_score", 0.0))
    score += max(0.0, 1.0 - abs(evidence - 0.60) * 3.0)
    return score


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--filled", default=str(DEFAULT_FILLED))
    parser.add_argument("--output", default=str(DEFAULT_OUT))
    parser.add_argument("--audit", default=str(DEFAULT_AUDIT))
    parser.add_argument("--limit", type=int, default=120)
    args = parser.parse_args()

    filled_path = Path(args.filled)
    output_path = Path(args.output)
    audit_path = Path(args.audit)
    if not filled_path.is_absolute():
        filled_path = PROJECT_ROOT / filled_path
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path
    if not audit_path.is_absolute():
        audit_path = PROJECT_ROOT / audit_path

    filled = pd.read_csv(filled_path)
    candidates = filled[filled["needs_manual_check"].eq("yes")].copy()
    candidates["manual_check_priority_score"] = candidates.apply(priority_score, axis=1)
    priority = candidates.sort_values(
        ["manual_check_priority_score", "auto_evidence_score", "review_index"],
        ascending=[False, True, True],
    ).head(args.limit)
    priority.to_csv(output_path, index=False)
    audit = {
        "filled_input": str(filled_path.relative_to(PROJECT_ROOT)),
        "priority_output": str(output_path.relative_to(PROJECT_ROOT)),
        "candidate_manual_check_count": int(len(candidates)),
        "priority_count": int(len(priority)),
        "auto_review_bucket_counts": {str(k): int(v) for k, v in priority["auto_review_bucket"].value_counts().sort_index().items()},
        "night_ir_count": int(priority["auto_night_ir"].eq("yes").sum()),
        "claim_boundary": "priority_subset_for_human_review_not_ground_truth",
    }
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "PASS phase14 FCF bobcat priority manual checks "
        f"rows={len(priority)} output={output_path.relative_to(PROJECT_ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
