#!/usr/bin/env python3
"""Audit Phase 10-Lite matched-identity training manifests."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase10_lite"
AUDIT_CSV = OUTPUT_DIR / "phase10_lite_matched_manifest_audit.csv"

GROUPS = [
    "B2_random_matched_identity",
    "C2_quality_matched_identity",
    "D2_pf_eri_matched_identity",
]
REQUIRED_COLUMNS = [
    "image_id",
    "identity_label_internal",
    "pf_eri_image_score",
    "split_id",
    "train_val_test_role",
    "phase10_lite_group",
    "images_per_identity_k",
    "selection_rule",
    "selection_rank_within_identity",
]


def add(
    rows: list[dict[str, object]],
    manifest_name: str,
    check_name: str,
    status: str,
    detail: str,
    split_id: object = "",
    group: str = "",
) -> None:
    rows.append(
        {
            "manifest": manifest_name,
            "split_id": split_id,
            "phase10_lite_group": group,
            "check_name": check_name,
            "status": status,
            "detail": detail,
        }
    )


def audit_manifest(path: Path, expected_k: int, rows: list[dict[str, object]]) -> None:
    name = path.name
    if not path.exists():
        add(rows, name, "manifest_exists", "FAIL", f"missing file: {path}")
        return
    df = pd.read_csv(path)
    add(rows, name, "manifest_exists", "PASS", f"rows={len(df)}")
    if df.empty:
        add(rows, name, "nonzero_rows", "FAIL", "manifest has zero rows")
        return
    add(rows, name, "nonzero_rows", "PASS", f"rows={len(df)}")

    for col in REQUIRED_COLUMNS:
        status = "PASS" if col in df.columns else "FAIL"
        add(rows, name, f"required_column_{col}", status, "present" if status == "PASS" else "missing")
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        return

    missing_image_id = int(df["image_id"].isna().sum() + (df["image_id"].astype(str).str.strip() == "").sum())
    add(
        rows,
        name,
        "image_id_exists",
        "PASS" if missing_image_id == 0 else "FAIL",
        f"missing_or_blank_image_id={missing_image_id}",
    )
    missing_identity = int(
        df["identity_label_internal"].isna().sum()
        + (df["identity_label_internal"].astype(str).str.strip() == "").sum()
    )
    add(
        rows,
        name,
        "identity_label_internal_exists",
        "PASS" if missing_identity == 0 else "FAIL",
        f"missing_or_blank_identity={missing_identity}",
    )
    missing_pf = int(pd.to_numeric(df["pf_eri_image_score"], errors="coerce").isna().sum())
    add(
        rows,
        name,
        "pf_eri_image_score_exists",
        "PASS" if missing_pf == 0 else "FAIL",
        f"missing_or_non_numeric_pf_eri={missing_pf}",
    )
    k_values = sorted(pd.to_numeric(df["images_per_identity_k"], errors="coerce").dropna().unique().tolist())
    add(
        rows,
        name,
        "expected_k_value",
        "PASS" if k_values == [expected_k] else "FAIL",
        f"observed_k_values={k_values}; expected={expected_k}",
    )

    roles = sorted(df["train_val_test_role"].astype(str).str.lower().unique().tolist())
    add(
        rows,
        name,
        "train_role_only",
        "PASS" if roles == ["train"] else "FAIL",
        f"observed_roles={roles}",
    )
    add(
        rows,
        name,
        "unexpected_role_leakage",
        "PASS" if set(roles) <= {"train"} else "FAIL",
        f"observed_roles={roles}",
    )

    observed_groups = sorted(df["phase10_lite_group"].unique().tolist())
    add(
        rows,
        name,
        "required_groups_present",
        "PASS" if observed_groups == GROUPS else "FAIL",
        f"observed_groups={observed_groups}",
    )

    for split_id, split_rows in df.groupby("split_id", sort=True):
        for group in GROUPS:
            group_rows = split_rows[split_rows["phase10_lite_group"] == group]
            add(
                rows,
                name,
                "split_group_nonzero_rows",
                "PASS" if len(group_rows) > 0 else "FAIL",
                f"rows={len(group_rows)}",
                split_id=split_id,
                group=group,
            )

        identity_sets = {
            group: set(
                split_rows.loc[
                    split_rows["phase10_lite_group"] == group, "identity_label_internal"
                ].astype(str)
            )
            for group in GROUPS
        }
        first_set = identity_sets[GROUPS[0]]
        matching = all(identity_sets[group] == first_set for group in GROUPS)
        add(
            rows,
            name,
            "identity_sets_match_within_split",
            "PASS" if matching else "FAIL",
            "; ".join(f"{group}={len(identity_sets[group])}" for group in GROUPS),
            split_id=split_id,
        )

        row_counts = {
            group: int((split_rows["phase10_lite_group"] == group).sum()) for group in GROUPS
        }
        add(
            rows,
            name,
            "total_rows_equal_across_groups",
            "PASS" if len(set(row_counts.values())) == 1 else "FAIL",
            str(row_counts),
            split_id=split_id,
        )

        per_identity = (
            split_rows.groupby(["phase10_lite_group", "identity_label_internal"])
            .size()
            .rename("row_count")
            .reset_index()
        )
        bad_counts = per_identity[per_identity["row_count"] != expected_k]
        add(
            rows,
            name,
            "per_identity_row_count_equals_k",
            "PASS" if bad_counts.empty else "FAIL",
            f"bad_identity_group_count={len(bad_counts)} expected_k={expected_k}",
            split_id=split_id,
        )

        duplicates = (
            split_rows.groupby(["phase10_lite_group", "identity_label_internal", "image_id"])
            .size()
            .rename("row_count")
            .reset_index()
        )
        duplicate_count = int((duplicates["row_count"] > 1).sum())
        add(
            rows,
            name,
            "no_duplicate_image_rows_within_group_identity",
            "PASS" if duplicate_count == 0 else "FAIL",
            f"duplicate_group_identity_image_rows={duplicate_count}",
            split_id=split_id,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, object]] = []
    for k in [2, 3]:
        audit_manifest(args.output_dir / f"phase10_lite_matched_training_manifest_k{k}.csv", k, rows)

    audit = pd.DataFrame(
        rows,
        columns=[
            "manifest",
            "split_id",
            "phase10_lite_group",
            "check_name",
            "status",
            "detail",
        ],
    )
    audit.to_csv(args.output_dir / AUDIT_CSV.name, index=False)
    fail_count = int((audit["status"] == "FAIL").sum()) if not audit.empty else 1
    pass_count = int((audit["status"] == "PASS").sum()) if not audit.empty else 0
    print(f"{'PASS' if fail_count == 0 else 'FAIL'} audit_phase10_lite_matched_training_manifest")
    print(f"pass_count={pass_count}")
    print(f"fail_count={fail_count}")
    print(f"audit_csv={args.output_dir / AUDIT_CSV.name}")
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
