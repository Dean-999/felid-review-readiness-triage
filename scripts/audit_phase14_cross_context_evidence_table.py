#!/usr/bin/env python3
"""Audit Phase 14 shared cross-context evidence table."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "outputs/phase14"
TABLE = OUT_DIR / "phase14_cross_context_evidence_table.csv"
BUILD_AUDIT = OUT_DIR / "phase14_cross_context_evidence_table_build_audit.json"
AUDIT_OUT = OUT_DIR / "phase14_cross_context_evidence_table_audit.csv"

REQUIRED_COLUMNS = {
    "row_id",
    "context",
    "species",
    "source_dataset",
    "image_key_blinded",
    "has_identity_label",
    "identity_label_available_for_validation",
    "pf_eri_image_score",
    "pattern_visibility",
    "side_flank_visibility",
    "body_visibility",
    "blur_level",
    "occlusion_level",
    "night_ir",
    "background_complexity",
    "human_modified_background",
    "descriptor_confidence",
    "descriptor_evidence_conflict",
    "feature_available_flags",
}

FORBIDDEN_HEADERS = {
    "review_image_path_local",
    "source_review_image_path_original",
    "path",
    "local_image_path",
    "unique_name",
    "working_individual_id",
    "latitude",
    "longitude",
    "trap_id",
    "camera_id",
    "site",
    "location",
    "cell_code",
}

FORBIDDEN_VALUE_PATTERNS = [
    re.compile(r"/Users/", re.IGNORECASE),
    re.compile(r"data/raw", re.IGNORECASE),
    re.compile(r"\.(jpg|jpeg|png|tif|tiff)\b", re.IGNORECASE),
    re.compile(r"(?<!czech)lynx_[0-9]+", re.IGNORECASE),
    re.compile(r"czlx_expanded_[0-9]+", re.IGNORECASE),
]


def add(rows: list[dict[str, object]], check: str, passed: bool, detail: str) -> None:
    rows.append({"check": check, "status": "PASS" if passed else "FAIL", "detail": detail})


def main() -> int:
    rows: list[dict[str, object]] = []
    add(rows, "table_exists", TABLE.exists(), str(TABLE.relative_to(PROJECT_ROOT)))
    add(rows, "build_audit_exists", BUILD_AUDIT.exists(), str(BUILD_AUDIT.relative_to(PROJECT_ROOT)))
    if not TABLE.exists() or not BUILD_AUDIT.exists():
        pd.DataFrame(rows).to_csv(AUDIT_OUT, index=False)
        print(f"FAIL phase14 cross-context table audit output={AUDIT_OUT.relative_to(PROJECT_ROOT)}")
        return 1

    table = pd.read_csv(TABLE)
    build_audit = json.loads(BUILD_AUDIT.read_text(encoding="utf-8"))
    add(rows, "table_nonempty", len(table) > 0, f"rows={len(table)}")
    missing = sorted(REQUIRED_COLUMNS - set(table.columns))
    add(rows, "required_columns_present", not missing, f"missing={missing}")
    extra_sensitive_headers = sorted((set(table.columns) & FORBIDDEN_HEADERS) - {"image_key_blinded"})
    add(rows, "no_forbidden_headers", not extra_sensitive_headers, f"headers={extra_sensitive_headers}")
    row_id_dupes = int(table["row_id"].duplicated().sum()) if "row_id" in table else -1
    add(rows, "row_id_unique", row_id_dupes == 0, f"duplicate_row_ids={row_id_dupes}")
    key_dupes = int(table["image_key_blinded"].duplicated().sum()) if "image_key_blinded" in table else -1
    add(rows, "image_key_blinded_unique", key_dupes == 0, f"duplicate_keys={key_dupes}")

    if "pf_eri_image_score" in table:
        score = pd.to_numeric(table["pf_eri_image_score"], errors="coerce")
        bad_score = int(((score.notna()) & ((score < 0) | (score > 1))).sum())
        add(rows, "pf_eri_image_score_unit_interval_when_present", bad_score == 0, f"bad_values={bad_score}")

    leakage_columns = 0
    for column in table.columns:
        for value in table[column].dropna().astype(str).head(5000):
            if any(pattern.search(value) for pattern in FORBIDDEN_VALUE_PATTERNS):
                leakage_columns += 1
                break
    add(rows, "no_sensitive_value_patterns", leakage_columns == 0, f"columns_with_leakage={leakage_columns}")

    contexts = set(table["context"].astype(str)) if "context" in table else set()
    add(rows, "known_context_values", contexts <= {"wild_known_id", "urban_stress"}, f"contexts={sorted(contexts)}")
    uwin_rows = int(table["source_dataset"].astype(str).eq("UWIN_bobcat").sum()) if "source_dataset" in table else 0
    add(
        rows,
        "dry_run_claim_boundary_matches_uwin_presence",
        bool(build_audit.get("czechlynx_only_dry_run")) == (uwin_rows == 0),
        f"uwin_rows={uwin_rows} dry_run={build_audit.get('czechlynx_only_dry_run')}",
    )
    add(
        rows,
        "claim_boundary_not_cross_context_without_uwin",
        not (uwin_rows == 0 and build_audit.get("claim_boundary") == "cross_context_ready"),
        f"uwin_rows={uwin_rows} claim_boundary={build_audit.get('claim_boundary')}",
    )

    flags_ok = True
    bad_flag_examples = 0
    for value in table["feature_available_flags"].dropna().astype(str).head(100):
        try:
            parsed = json.loads(value)
            flags_ok = flags_ok and isinstance(parsed, dict)
        except json.JSONDecodeError:
            flags_ok = False
            bad_flag_examples += 1
    add(rows, "feature_available_flags_json", flags_ok, f"bad_examples={bad_flag_examples}")

    audit = pd.DataFrame(rows)
    audit.to_csv(AUDIT_OUT, index=False)
    fail_count = int(audit["status"].eq("FAIL").sum())
    print(
        f"{'PASS' if fail_count == 0 else 'FAIL'} phase14 cross-context table audit "
        f"checks={len(audit)} failures={fail_count} output={AUDIT_OUT.relative_to(PROJECT_ROOT)}"
    )
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
