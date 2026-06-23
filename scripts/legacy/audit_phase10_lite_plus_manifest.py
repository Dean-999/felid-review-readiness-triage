#!/usr/bin/env python3
"""Audit Phase 10-Lite Plus matched and all-train reference manifests."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase10_lite"
MANIFEST = OUTPUT_DIR / "phase10_lite_plus_matched_training_manifest_k3.csv"
AUDIT_CSV = OUTPUT_DIR / "phase10_lite_plus_manifest_audit.csv"

MATCHED_GROUPS = [
    "B3_random_matched_identity",
    "C3_quality_proxy_matched_identity",
    "D3_pf_eri_matched_identity",
    "H3_pf_eri_quality_hybrid_matched_identity",
]
E4_GROUP = "E4_pf_eri_weighted_all_train_reference"
REQUIRED_COLUMNS = [
    "image_id",
    "identity_label_internal",
    "pf_eri_image_score",
    "split_id",
    "train_val_test_role",
    "phase10_lite_plus_group",
    "images_per_identity_k",
    "selection_rule",
    "selection_rank_within_identity",
    "sample_weight",
    "quality_bucket_rank_normalized",
    "hybrid_score",
]


def add(rows: list[dict[str, object]], check: str, status: str, detail: str, split_id: object = "", group: str = "") -> None:
    rows.append(
        {
            "split_id": split_id,
            "phase10_lite_plus_group": group,
            "check_name": check,
            "status": status,
            "detail": detail,
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    if not MANIFEST.exists():
        add(rows, "manifest_exists", "FAIL", f"missing {MANIFEST}")
        pd.DataFrame(rows).to_csv(AUDIT_CSV, index=False)
        print("FAIL audit_phase10_lite_plus_manifest")
        return 1
    df = pd.read_csv(MANIFEST)
    add(rows, "manifest_exists", "PASS", f"rows={len(df)}")
    add(rows, "manifest_nonempty", "PASS" if len(df) else "FAIL", f"rows={len(df)}")
    for col in REQUIRED_COLUMNS:
        add(rows, f"required_column_{col}", "PASS" if col in df.columns else "FAIL", "present" if col in df.columns else "missing")
    if any(row["status"] == "FAIL" for row in rows):
        pd.DataFrame(rows).to_csv(AUDIT_CSV, index=False)
        print("FAIL audit_phase10_lite_plus_manifest")
        return 1

    roles = sorted(df["train_val_test_role"].astype(str).str.lower().unique())
    add(rows, "train_role_only", "PASS" if roles == ["train"] else "FAIL", f"roles={roles}")
    observed_groups = sorted(df["phase10_lite_plus_group"].unique())
    expected_groups = sorted(MATCHED_GROUPS + [E4_GROUP])
    add(rows, "expected_groups_present", "PASS" if observed_groups == expected_groups else "FAIL", f"observed={observed_groups}")
    for col in ["image_id", "identity_label_internal", "pf_eri_image_score"]:
        missing = int(df[col].isna().sum() + (df[col].astype(str).str.strip() == "").sum())
        add(rows, f"{col}_not_missing", "PASS" if missing == 0 else "FAIL", f"missing={missing}")

    for split_id, split_rows in df.groupby("split_id", sort=True):
        identity_sets = {}
        row_counts = {}
        for group in MATCHED_GROUPS:
            group_rows = split_rows[split_rows["phase10_lite_plus_group"] == group]
            identity_sets[group] = set(group_rows["identity_label_internal"].astype(str))
            row_counts[group] = len(group_rows)
            add(rows, "matched_group_nonzero", "PASS" if len(group_rows) else "FAIL", f"rows={len(group_rows)}", split_id, group)
            per_identity = group_rows.groupby("identity_label_internal")["image_id"].nunique()
            bad = int((per_identity != 3).sum())
            add(rows, "matched_group_exactly_3_images_per_identity", "PASS" if bad == 0 and len(per_identity) else "FAIL", f"bad_identity_count={bad}", split_id, group)
            dupes = int(group_rows.duplicated(["identity_label_internal", "image_id"]).sum())
            add(rows, "no_duplicate_image_rows_within_group_identity", "PASS" if dupes == 0 else "FAIL", f"duplicates={dupes}", split_id, group)
        first = identity_sets[MATCHED_GROUPS[0]]
        matched = all(identity_sets[group] == first for group in MATCHED_GROUPS)
        add(rows, "matched_identity_sets_equal_b3_c3_d3_h3", "PASS" if matched else "FAIL", ";".join(f"{g}={len(identity_sets[g])}" for g in MATCHED_GROUPS), split_id)
        add(rows, "matched_total_rows_equal_b3_c3_d3_h3", "PASS" if len(set(row_counts.values())) == 1 else "FAIL", str(row_counts), split_id)

        e4 = split_rows[split_rows["phase10_lite_plus_group"] == E4_GROUP]
        per_identity_e4 = e4.groupby("identity_label_internal")["image_id"].nunique()
        add(rows, "e4_nonzero", "PASS" if len(e4) else "FAIL", f"rows={len(e4)}", split_id, E4_GROUP)
        add(rows, "e4_expected_75_identities", "PASS" if e4["identity_label_internal"].nunique() == 75 else "FAIL", f"identities={e4['identity_label_internal'].nunique()}", split_id, E4_GROUP)
        add(rows, "e4_expected_300_rows_when_available", "PASS" if len(e4) == 300 else "FAIL", f"rows={len(e4)}", split_id, E4_GROUP)
        add(rows, "e4_all_train_four_or_available", "PASS" if int(per_identity_e4.min()) >= 1 and int(per_identity_e4.max()) == 4 else "FAIL", f"min={per_identity_e4.min() if len(per_identity_e4) else 'NA'} max={per_identity_e4.max() if len(per_identity_e4) else 'NA'}", split_id, E4_GROUP)
        weights_ok = pd.to_numeric(e4["sample_weight"], errors="coerce").between(0.25, 1.0).all()
        add(rows, "e4_sample_weight_present_and_bounded", "PASS" if weights_ok else "FAIL", "expected 0.25..1.0", split_id, E4_GROUP)

    audit = pd.DataFrame(rows, columns=["split_id", "phase10_lite_plus_group", "check_name", "status", "detail"])
    audit.to_csv(AUDIT_CSV, index=False)
    fail_count = int((audit["status"] == "FAIL").sum())
    print(f"{'PASS' if fail_count == 0 else 'FAIL'} audit_phase10_lite_plus_manifest")
    print(f"pass_count={int((audit['status'] == 'PASS').sum())}")
    print(f"fail_count={fail_count}")
    print(f"audit_csv={AUDIT_CSV}")
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
