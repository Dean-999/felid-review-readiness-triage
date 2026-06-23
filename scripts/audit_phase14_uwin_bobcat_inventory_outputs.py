#!/usr/bin/env python3
"""Audit Phase 14 UWIN bobcat inventory outputs."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "outputs/phase14"
INVENTORY = OUT_DIR / "uwin_bobcat_inventory.csv"
SUMMARY = OUT_DIR / "uwin_bobcat_inventory_summary.json"
AUDIT_OUT = OUT_DIR / "uwin_bobcat_inventory_audit.csv"

REQUIRED_COLUMNS = {
    "relative_path",
    "source_category",
    "file_extension",
    "rows_sampled",
    "n_columns",
    "candidate_signal",
    "sensitive_fields_present",
    "identity_like_fields_present",
    "pair_audit_like_fields_present",
    "sensitive_columns",
    "identity_like_columns",
    "pair_audit_like_columns",
    "bobcat_like_columns",
    "sampled_value_token_hit_counts",
}

FORBIDDEN_VALUE_PATTERNS = [
    re.compile(r"/Users/", re.IGNORECASE),
    re.compile(r"data/raw", re.IGNORECASE),
    re.compile(r"\.(jpg|jpeg|png|tif|tiff)\b", re.IGNORECASE),
    re.compile(r"-?\d{1,3}\.\d{4,}"),  # likely coordinate-like precision
]


def add(rows: list[dict[str, object]], check: str, passed: bool, detail: str) -> None:
    rows.append({"check": check, "status": "PASS" if passed else "FAIL", "detail": detail})


def main() -> int:
    rows: list[dict[str, object]] = []
    add(rows, "inventory_exists", INVENTORY.exists(), str(INVENTORY.relative_to(PROJECT_ROOT)))
    add(rows, "summary_exists", SUMMARY.exists(), str(SUMMARY.relative_to(PROJECT_ROOT)))
    if not INVENTORY.exists() or not SUMMARY.exists():
        pd.DataFrame(rows).to_csv(AUDIT_OUT, index=False)
        print(f"FAIL phase14 UWIN inventory audit output={AUDIT_OUT.relative_to(PROJECT_ROOT)}")
        return 1

    inventory = pd.read_csv(INVENTORY)
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    missing = sorted(REQUIRED_COLUMNS - set(inventory.columns))
    add(rows, "required_columns_present", not missing, f"missing={missing}")
    add(rows, "summary_scanned_file_count_positive", int(summary.get("scanned_file_count", 0)) > 0, f"scanned={summary.get('scanned_file_count')}")
    add(
        rows,
        "summary_matches_inventory_rows",
        int(summary.get("candidate_file_count", -1)) == len(inventory),
        f"summary={summary.get('candidate_file_count')} inventory={len(inventory)}",
    )
    local_count = int((inventory.get("source_category", pd.Series(dtype=str)).astype(str) == "local_data").sum())
    add(
        rows,
        "local_data_count_matches_summary",
        int(summary.get("local_data_candidate_file_count", -1)) == local_count,
        f"summary={summary.get('local_data_candidate_file_count')} inventory={local_count}",
    )

    leakage_count = 0
    for column in inventory.columns:
        for value in inventory[column].dropna().astype(str):
            if any(pattern.search(value) for pattern in FORBIDDEN_VALUE_PATTERNS):
                leakage_count += 1
                break
    add(rows, "no_sensitive_value_patterns", leakage_count == 0, f"columns_with_leakage={leakage_count}")
    add(
        rows,
        "claim_boundary_no_verified_labels_without_local_data",
        not (local_count == 0 and summary.get("verified_individual_labels") == "yes"),
        f"local_data={local_count} verified_individual_labels={summary.get('verified_individual_labels')}",
    )
    add(
        rows,
        "claim_boundary_no_pair_audit_without_local_data",
        not (local_count == 0 and summary.get("human_pair_audit_labels") == "yes"),
        f"local_data={local_count} human_pair_audit_labels={summary.get('human_pair_audit_labels')}",
    )

    audit = pd.DataFrame(rows)
    audit.to_csv(AUDIT_OUT, index=False)
    fail_count = int(audit["status"].eq("FAIL").sum())
    print(
        f"{'PASS' if fail_count == 0 else 'FAIL'} phase14 UWIN inventory audit "
        f"checks={len(audit)} failures={fail_count} output={AUDIT_OUT.relative_to(PROJECT_ROOT)}"
    )
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
