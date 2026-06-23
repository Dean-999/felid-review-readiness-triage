#!/usr/bin/env python3
"""Audit Phase 11 pair-level PF-ERI reliability table."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PAIR_TABLE = PROJECT_ROOT / "outputs/czechlynx/phase11/phase11_pair_level_pf_eri_table.csv"
MANIFEST = PROJECT_ROOT / "outputs/czechlynx/phase10_lite/phase10_lite_plus_matched_training_manifest_k3.csv"
EMBEDDINGS = PROJECT_ROOT / "outputs/czechlynx/phase4/czechlynx_phase4c_megadescriptor_embeddings.csv"
OUT = PROJECT_ROOT / "outputs/czechlynx/phase11/phase11_pair_level_pf_eri_table_audit.csv"

REQUIRED_COLUMNS = {
    "split_id",
    "group_name",
    "image_id_a",
    "image_id_b",
    "identity_a",
    "identity_b",
    "same_identity",
    "role",
    "descriptor_similarity",
    "side_comparability_score",
    "pattern_pair_score",
    "blur_pair_score",
    "occlusion_pair_score",
    "body_visibility_pair_score",
    "viewpoint_compatibility_score",
    "pair_reliability_score",
    "positive_pair_weight",
    "negative_pair_weight",
    "hard_negative_flag",
    "pf_eri_pair_penalty",
    "source_manifest_path",
}
SCORE_COLUMNS = [
    "side_comparability_score",
    "pattern_pair_score",
    "blur_pair_score",
    "occlusion_pair_score",
    "body_visibility_pair_score",
    "viewpoint_compatibility_score",
    "pair_reliability_score",
    "positive_pair_weight",
    "negative_pair_weight",
    "pf_eri_pair_penalty",
]


def audit_row(rows: list[dict[str, object]], check: str, passed: bool, detail: str) -> None:
    rows.append({"check": check, "status": "PASS" if passed else "FAIL", "detail": detail})


def main() -> None:
    rows: list[dict[str, object]] = []
    if not PAIR_TABLE.exists():
        audit_row(rows, "pair_table_exists", False, str(PAIR_TABLE))
        pd.DataFrame(rows).to_csv(OUT, index=False)
        raise SystemExit("Phase 11 pair table missing")

    table = pd.read_csv(PAIR_TABLE)
    manifest = pd.read_csv(MANIFEST)
    embeddings = pd.read_csv(EMBEDDINGS, usecols=["expanded_image_id"])
    audit_row(rows, "pair_table_nonempty", len(table) > 0, f"rows={len(table)}")
    missing = sorted(REQUIRED_COLUMNS - set(table.columns))
    audit_row(rows, "required_columns", not missing, f"missing={missing}")

    if missing:
        pd.DataFrame(rows).to_csv(OUT, index=False)
        raise SystemExit("Phase 11 pair table required-column audit failed")

    dupes = int(table.duplicated(["split_id", "group_name", "image_id_a", "image_id_b"]).sum())
    audit_row(rows, "no_duplicate_pair_rows", dupes == 0, f"duplicate_rows={dupes}")
    reverse_dupes = int(
        table.assign(
            lo=table[["image_id_a", "image_id_b"]].min(axis=1),
            hi=table[["image_id_a", "image_id_b"]].max(axis=1),
        ).duplicated(["split_id", "group_name", "lo", "hi"]).sum()
    )
    audit_row(rows, "no_reversed_duplicate_pairs", reverse_dupes == 0, f"reversed_duplicates={reverse_dupes}")
    self_pairs = int((table["image_id_a"].astype(str) == table["image_id_b"].astype(str)).sum())
    audit_row(rows, "no_self_pairs", self_pairs == 0, f"self_pairs={self_pairs}")

    same_expected = table["identity_a"].astype(str) == table["identity_b"].astype(str)
    same_observed = table["same_identity"].astype(str).str.lower().isin(["true", "1", "yes"])
    mismatch = int((same_expected != same_observed).sum())
    audit_row(rows, "same_identity_correct", mismatch == 0, f"mismatches={mismatch}")

    role_values = sorted(table["role"].astype(str).unique())
    audit_row(rows, "role_train_pair_only", role_values == ["train_pair"], f"roles={role_values}")

    for column in SCORE_COLUMNS:
        values = pd.to_numeric(table[column], errors="coerce")
        bad = int((values.isna() | (values < 0) | (values > 1)).sum())
        audit_row(rows, f"{column}_in_unit_interval", bad == 0, f"bad_values={bad}")

    bool_values = set(table["hard_negative_flag"].astype(str).str.lower().unique())
    allowed_bool = {"true", "false", "1", "0", "yes", "no"}
    audit_row(rows, "hard_negative_flag_boolean_like", bool_values <= allowed_bool, f"values={sorted(bool_values)}")

    expected_groups = sorted(manifest["phase10_lite_plus_group"].astype(str).unique())
    observed_groups = sorted(table["group_name"].astype(str).unique())
    audit_row(rows, "group_coverage", observed_groups == expected_groups, f"observed={observed_groups}")
    expected_splits = sorted(manifest["split_id"].astype(int).unique())
    observed_splits = sorted(table["split_id"].astype(int).unique())
    audit_row(rows, "split_coverage", observed_splits == expected_splits, f"observed={observed_splits}")

    expected_counts = []
    for (split_id, group_name), frame in manifest.groupby(["split_id", "phase10_lite_plus_group"]):
        n = len(frame)
        expected_counts.append({"split_id": int(split_id), "group_name": str(group_name), "expected_pairs": n * (n - 1) // 2})
    expected = pd.DataFrame(expected_counts)
    observed = table.groupby(["split_id", "group_name"]).size().reset_index(name="observed_pairs")
    merged = expected.merge(observed, on=["split_id", "group_name"], how="left")
    count_mismatch = int((merged["expected_pairs"] != merged["observed_pairs"]).sum())
    audit_row(rows, "deterministic_row_counts", count_mismatch == 0, f"mismatched_split_groups={count_mismatch}")

    roles = sorted(manifest["train_val_test_role"].astype(str).str.lower().unique())
    audit_row(rows, "source_manifest_train_only", roles == ["train"], f"roles={roles}")
    valid_pairs = set(zip(manifest["split_id"].astype(int), manifest["phase10_lite_plus_group"].astype(str), manifest["image_id"].astype(str)))
    pair_images = pd.concat(
        [
            table[["split_id", "group_name", "image_id_a"]].rename(columns={"group_name": "group", "image_id_a": "image_id"}),
            table[["split_id", "group_name", "image_id_b"]].rename(columns={"group_name": "group", "image_id_b": "image_id"}),
        ],
        ignore_index=True,
    )
    pair_image_keys = set(zip(pair_images["split_id"].astype(int), pair_images["group"].astype(str), pair_images["image_id"].astype(str)))
    missing_manifest_images = len(pair_image_keys - valid_pairs)
    audit_row(rows, "no_train_test_manifest_leakage", missing_manifest_images == 0, f"pair_images_not_in_train_manifest={missing_manifest_images}")

    embedding_ids = set(embeddings["expanded_image_id"].astype(str))
    all_pair_ids = set(table["image_id_a"].astype(str)) | set(table["image_id_b"].astype(str))
    missing_embeddings = sorted(all_pair_ids - embedding_ids)
    audit_row(rows, "embedding_coverage", len(missing_embeddings) == 0, f"missing_embeddings={len(missing_embeddings)}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT, index=False)
    pass_count = sum(row["status"] == "PASS" for row in rows)
    fail_count = sum(row["status"] == "FAIL" for row in rows)
    print(f"Phase 11 pair table audit: PASS={pass_count} FAIL={fail_count} output={OUT.relative_to(PROJECT_ROOT)}")
    if fail_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
