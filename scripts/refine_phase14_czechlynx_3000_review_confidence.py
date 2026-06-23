#!/usr/bin/env python3
"""Refine Phase 14 CzechLynx 3000 review confidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from refine_phase14_fcf_bobcat_review_confidence import is_stable_boundary, risk_group  # noqa: E402

IN_DIR = PROJECT_ROOT / "data/interim/czechlynx/phase14"
DEFAULT_INPUT = IN_DIR / "czechlynx_phase14_3000_review_labels.csv"
DEFAULT_OUTPUT = IN_DIR / "czechlynx_phase14_3000_refined_review_labels.csv"
DEFAULT_MANUAL = IN_DIR / "czechlynx_phase14_3000_refined_needs_manual_check.csv"
DEFAULT_PROMOTED = IN_DIR / "czechlynx_phase14_3000_confidence_promoted_stable_boundary.csv"
DEFAULT_AUDIT = IN_DIR / "czechlynx_phase14_3000_confidence_refinement_audit.json"


def resolve(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else PROJECT_ROOT / path


def refine(table: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, row in table.iterrows():
        item = row.to_dict()
        item["first_pass_human_review_confidence"] = item.get("human_review_confidence", "")
        item["first_pass_needs_manual_check"] = item.get("needs_manual_check", "")
        item["confidence_refinement_action"] = "unchanged"
        item["confidence_refinement_reason"] = risk_group(row)
        if (
            str(row.get("ai_fill_status")) == "ai_first_pass"
            and str(row.get("human_review_confidence")) == "low"
            and is_stable_boundary(row)
        ):
            item["human_review_confidence"] = "medium"
            item["needs_manual_check"] = "no"
            item["human_notes"] = str(item.get("human_notes", "")).replace(
                "boundary_score", "stable_boundary_resolved"
            )
            item["confidence_refinement_action"] = "promoted_low_to_medium"
            item["confidence_refinement_reason"] = (
                "stable_boundary_no_night_no_weak_signal_no_exposure_or_contrast_flag"
            )
        rows.append(item)
    return pd.DataFrame(rows)


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
        "manual_check_reason_counts": {
            str(k): int(v)
            for k, v in manual["confidence_refinement_reason"].value_counts().sort_index().items()
        },
        "claim_boundary": "confidence_refinement_for_czechlynx_review_prioritization_not_new_human_ground_truth",
    }
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "PASS phase14 CzechLynx confidence refinement "
        f"rows={len(refined)} promoted={len(promoted)} manual_remaining={len(manual)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
