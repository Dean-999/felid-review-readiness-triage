#!/usr/bin/env python3
"""Audit Phase16G pair-level tables."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = [
    "pair_id",
    "dataset_role",
    "species_context",
    "query_image_id",
    "candidate_image_id",
    "descriptor_similarity",
    "descriptor_evidence_conflict_flag",
    "same_identity_label",
    "label_source",
    "label_allowed_for_modeling",
    "split_group",
]

BOBCAT_MODELING_LABEL_SOURCES = {"verified_bobcat_id", "manual_pair_audit"}


def audit_pair_table(table: pd.DataFrame) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []

    missing = [column for column in REQUIRED_COLUMNS if column not in table.columns]
    if missing:
        errors.append("missing_required_columns: " + ", ".join(missing))
        return {"status": "FAIL", "row_count": int(len(table)), "errors": errors, "warnings": warnings}

    duplicate_count = int(table["pair_id"].duplicated().sum())
    if duplicate_count:
        errors.append(f"duplicate_pair_id_count: {duplicate_count}")

    if table["pair_id"].isna().any():
        errors.append("null_pair_id")

    same_image = table["query_image_id"].astype(str).eq(table["candidate_image_id"].astype(str))
    if same_image.any():
        errors.append(f"self_pair_count: {int(same_image.sum())}")

    bobcat = table["species_context"].astype(str).str.lower().eq("bobcat")
    modeling = table["label_allowed_for_modeling"].fillna(False).astype(bool)
    unverified_bobcat_modeling = (
        bobcat
        & modeling
        & ~table["label_source"].isin(BOBCAT_MODELING_LABEL_SOURCES)
    )
    if unverified_bobcat_modeling.any():
        errors.append("bobcat_modeling_labels_require_verified_or_manual_pair_audit")

    if table["split_group"].isna().any():
        warnings.append("split_group_has_missing_values")

    return {
        "status": "FAIL" if errors else "PASS",
        "row_count": int(len(table)),
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    table = pd.read_csv(args.input)
    audit = audit_pair_table(table)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n")
    print(f"Audit status: {audit['status']}")
    print(f"Wrote {args.output}")
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
