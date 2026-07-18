#!/usr/bin/env python3
"""Audit Phase 13C RQ4 training-control manifest outputs."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase13/rq4_training_control_manifest"

PAIR_MANIFEST = OUT_DIR / "phase13c_rq4_pair_training_control_manifest.csv"
IMAGE_MANIFEST = OUT_DIR / "phase13c_rq4_image_training_roles.csv"
SUMMARY = OUT_DIR / "phase13c_rq4_control_summary.csv"
POLICY_SUMMARY = OUT_DIR / "phase13c_rq4_policy_comparison_summary.csv"
SUMMARY_MD = OUT_DIR / "phase13c_rq4_training_control_manifest_summary.md"
BUILD_AUDIT = OUT_DIR / "phase13c_rq4_training_control_manifest_build_audit.json"
AUDIT_OUT = OUT_DIR / "phase13c_rq4_training_control_manifest_audit.csv"


def add(rows: list[dict[str, object]], check: str, passed: bool, detail: str) -> None:
    rows.append({"check": check, "status": "PASS" if passed else "FAIL", "detail": detail})


def unit_interval(series: pd.Series) -> bool:
    values = pd.to_numeric(series, errors="coerce").dropna()
    return bool(((values >= 0) & (values <= 1)).all())


def main() -> None:
    rows: list[dict[str, object]] = []
    for label, path in {
        "pair_manifest": PAIR_MANIFEST,
        "image_manifest": IMAGE_MANIFEST,
        "summary": SUMMARY,
        "policy_summary": POLICY_SUMMARY,
        "summary_md": SUMMARY_MD,
        "build_audit": BUILD_AUDIT,
    }.items():
        add(rows, f"{label}_exists", path.exists(), str(path))

    if PAIR_MANIFEST.exists():
        frame = pd.read_csv(PAIR_MANIFEST)
        add(rows, "pair_manifest_800000_rows", len(frame) == 800000, f"rows={len(frame)}")
        forbidden = {"query_identity_token", "candidate_identity_token", "unique_name", "latitude", "longitude", "trap_id", "cell_code"}
        add(rows, "pair_manifest_no_sensitive_columns", forbidden.isdisjoint(frame.columns), f"forbidden_present={sorted(forbidden & set(frame.columns))}")
        for column in [
            "pf_eri_admissible_positive_weight",
            "quality_positive_weight",
            "descriptor_only_positive_weight",
            "descriptor_only_negative_weight",
            "quality_control_positive_weight",
            "quality_control_negative_weight",
            "pf_eri_positive_weight",
            "pf_eri_negative_weight",
            "pf_eri_conflict_aware_positive_weight",
            "pf_eri_conflict_aware_negative_weight",
        ]:
            add(rows, f"{column}_unit_interval", unit_interval(frame[column]), column)
        positives = frame["same_identity"].astype(str).str.lower().eq("yes")
        pos_eligible = frame["positive_pair_eligible"].astype(str).str.lower().eq("yes")
        add(rows, "positive_eligible_subset_of_same_identity", bool((~pos_eligible | positives).all()), "positive_pair_eligible implies same_identity")
        unsafe = frame["unsafe_hard_negative"].astype(str).str.lower().eq("yes")
        add(rows, "unsafe_hard_negatives_exist", int(unsafe.sum()) > 0, f"unsafe={int(unsafe.sum())}")
        add(
            rows,
            "unsafe_hard_negatives_downweighted",
            bool((pd.to_numeric(frame.loc[unsafe, "pf_eri_conflict_aware_negative_weight"], errors="coerce") < 1.0).all()),
            "unsafe hard negatives should have negative weight < 1",
        )

    if IMAGE_MANIFEST.exists():
        frame = pd.read_csv(IMAGE_MANIFEST)
        add(rows, "image_manifest_1000_images", frame["image_id"].nunique() == 1000, f"images={frame['image_id'].nunique()}")
        add(rows, "image_manifest_300_identities", frame["identity_token"].nunique() == 300, f"identities={frame['identity_token'].nunique()}")
        add(rows, "singleton_roles_present", "singleton_distractor_only" in set(frame["rq4_training_role"].astype(str)), "singleton role")

    if SUMMARY.exists():
        frame = pd.read_csv(SUMMARY)
        add(rows, "summary_rows_80", len(frame) == 80, f"rows={len(frame)}")
        add(rows, "summary_positive_counts_nonnegative", bool((frame["eligible_positive_pair_count"] >= 0).all()), "eligible_positive_pair_count")

    if POLICY_SUMMARY.exists():
        frame = pd.read_csv(POLICY_SUMMARY)
        add(rows, "policy_summary_rows_400", len(frame) == 400, f"rows={len(frame)}")
        required = {"descriptor_only", "random_control", "quality_control", "pf_eri_positive", "pf_eri_conflict_aware"}
        add(rows, "policy_summary_all_policies", required <= set(frame["policy_id"].astype(str)), f"policies={sorted(set(frame['policy_id'].astype(str)))}")

    if BUILD_AUDIT.exists():
        try:
            audit = json.loads(BUILD_AUDIT.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            add(rows, "build_audit_valid_json", False, str(exc))
        else:
            add(rows, "build_audit_valid_json", True, "valid")
            add(rows, "build_audit_800000_rows", int(audit.get("input_rows", 0)) == 800000, f"rows={audit.get('input_rows')}")
            add(rows, "build_audit_1000_images", int(audit.get("image_count", 0)) == 1000, f"images={audit.get('image_count')}")
            add(rows, "build_audit_300_identities", int(audit.get("identity_count", 0)) == 300, f"identities={audit.get('identity_count')}")

    pd.DataFrame(rows).to_csv(AUDIT_OUT, index=False)
    pass_count = sum(row["status"] == "PASS" for row in rows)
    fail_count = sum(row["status"] == "FAIL" for row in rows)
    print(f"Phase 13C RQ4 training-control audit: PASS={pass_count} FAIL={fail_count} output={AUDIT_OUT.relative_to(PROJECT_ROOT)}")
    if fail_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
