#!/usr/bin/env python3
"""Audit AI-filled FCF bobcat review labels and manual-check exports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REVIEW_DIR = PROJECT_ROOT / "data/external/felidae_conservation_fund/review_batches"
FILLED = REVIEW_DIR / "fcf_bobcat_400_human_review_ai_filled.csv"
UNCERTAIN = REVIEW_DIR / "fcf_bobcat_400_needs_manual_check.csv"
PRIORITY = REVIEW_DIR / "fcf_bobcat_120_priority_manual_check.csv"
AUDIT_OUT = REVIEW_DIR / "fcf_bobcat_400_ai_review_labels_audit.csv"

ALLOWED = {
    "human_pattern_visibility": {"high", "medium", "low", "none", "uncertain"},
    "human_side_flank_visibility": {"left", "right", "both", "frontal", "rear", "unknown"},
    "human_body_visibility": {"76_100", "51_75", "26_50", "0_25", "unknown"},
    "human_blur_level": {"none", "mild", "moderate", "severe", "unknown"},
    "human_occlusion_level": {"none", "partial", "major", "unknown"},
    "human_background_complexity": {"low", "medium", "high", "unknown"},
    "human_modified_background": {"yes", "no", "uncertain"},
    "human_review_bucket": {"review_ready", "review_limited", "species_level_only", "non_comparable", "uncertain"},
    "human_review_confidence": {"high", "medium", "low"},
}


def add(rows: list[dict[str, object]], check: str, passed: bool, detail: str) -> None:
    rows.append({"check": check, "status": "PASS" if passed else "FAIL", "detail": detail})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--filled", default=str(FILLED))
    parser.add_argument("--uncertain", default=str(UNCERTAIN))
    parser.add_argument("--priority", default=str(PRIORITY))
    parser.add_argument("--audit-output", default=str(AUDIT_OUT))
    parser.add_argument("--expected-filled-rows", type=int, default=400)
    parser.add_argument("--expected-priority-rows", type=int, default=120)
    args = parser.parse_args()

    def resolve(path_text: str) -> Path:
        path = Path(path_text)
        return path if path.is_absolute() else PROJECT_ROOT / path

    filled_path = resolve(args.filled)
    uncertain_path = resolve(args.uncertain)
    priority_path = resolve(args.priority)
    audit_out = resolve(args.audit_output)

    rows: list[dict[str, object]] = []
    add(rows, "filled_exists", filled_path.exists(), str(filled_path.relative_to(PROJECT_ROOT)))
    add(rows, "uncertain_exists", uncertain_path.exists(), str(uncertain_path.relative_to(PROJECT_ROOT)))
    add(rows, "priority_exists", priority_path.exists(), str(priority_path.relative_to(PROJECT_ROOT)))
    if not filled_path.exists():
        pd.DataFrame(rows).to_csv(audit_out, index=False)
        return 1
    filled = pd.read_csv(filled_path)
    uncertain = pd.read_csv(uncertain_path) if uncertain_path.exists() else pd.DataFrame()
    priority = pd.read_csv(priority_path) if priority_path.exists() else pd.DataFrame()
    add(
        rows,
        f"filled_row_count_{args.expected_filled_rows}",
        len(filled) == args.expected_filled_rows,
        f"rows={len(filled)}",
    )
    add(rows, "filled_no_duplicate_images", int(filled["image_id"].duplicated().sum()) == 0, f"dupes={int(filled['image_id'].duplicated().sum())}")
    for column, allowed in ALLOWED.items():
        missing = int(filled[column].isna().sum()) if column in filled else len(filled)
        bad_values = sorted(set(filled[column].dropna().astype(str)) - allowed) if column in filled else ["missing_column"]
        add(rows, f"{column}_filled", missing == 0, f"missing={missing}")
        add(rows, f"{column}_allowed_values", not bad_values, f"bad={bad_values}")
    add(rows, "human_notes_filled", int(filled["human_notes"].isna().sum()) == 0, f"missing={int(filled['human_notes'].isna().sum())}")
    needs = filled[filled["needs_manual_check"].eq("yes")]
    add(rows, "uncertain_matches_needs_manual_check", len(uncertain) == len(needs), f"uncertain={len(uncertain)} needs={len(needs)}")
    add(
        rows,
        f"priority_count_{args.expected_priority_rows}",
        len(priority) == args.expected_priority_rows,
        f"priority={len(priority)}",
    )
    priority_missing = sorted(set(priority.get("image_id", [])) - set(filled["image_id"]))
    add(rows, "priority_subset_of_filled", not priority_missing, f"missing={len(priority_missing)}")
    audit = pd.DataFrame(rows)
    audit.to_csv(audit_out, index=False)
    fail_count = int(audit["status"].eq("FAIL").sum())
    print(
        f"{'PASS' if fail_count == 0 else 'FAIL'} phase14 FCF bobcat AI review label audit "
        f"checks={len(audit)} failures={fail_count} output={audit_out.relative_to(PROJECT_ROOT)}"
    )
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
