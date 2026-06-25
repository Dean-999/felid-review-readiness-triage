#!/usr/bin/env python3
"""Audit Phase 12D failure diagnosis and policy revision outputs."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase12/rq_failure_diagnosis_policy_revision"
QUERY_DIFFICULTY = OUT_DIR / "phase12d_query_difficulty_and_ceiling.csv"
SCORE_SEPARATION = OUT_DIR / "phase12d_score_separation_diagnostics.csv"
FAILURE_MODES = OUT_DIR / "phase12d_false_top1_failure_modes.csv"
CALIBRATED_POLICIES = OUT_DIR / "phase12d_calibrated_policy_grid_selection.csv"
CALIBRATED_EVAL = OUT_DIR / "phase12d_calibrated_policy_evaluation.csv"
PAIRED_CONFIDENCE = OUT_DIR / "phase12d_calibrated_policy_paired_confidence.csv"
SUMMARY_MD = OUT_DIR / "phase12d_failure_diagnosis_and_revision_summary.md"
BUILD_AUDIT = OUT_DIR / "phase12d_failure_diagnosis_build_audit.json"
AUDIT_OUT = OUT_DIR / "phase12d_failure_diagnosis_audit.csv"


def add(rows: list[dict[str, object]], check: str, passed: bool, detail: str) -> None:
    rows.append({"check": check, "status": "PASS" if passed else "FAIL", "detail": detail})


def unit_interval(series: pd.Series) -> bool:
    values = pd.to_numeric(series, errors="coerce").dropna()
    return bool(((values >= 0) & (values <= 1)).all())


def main() -> None:
    rows: list[dict[str, object]] = []
    outputs = {
        "query_difficulty": QUERY_DIFFICULTY,
        "score_separation": SCORE_SEPARATION,
        "failure_modes": FAILURE_MODES,
        "calibrated_policies": CALIBRATED_POLICIES,
        "calibrated_eval": CALIBRATED_EVAL,
        "paired_confidence": PAIRED_CONFIDENCE,
        "summary_md": SUMMARY_MD,
        "build_audit": BUILD_AUDIT,
    }
    for label, path in outputs.items():
        add(rows, f"{label}_exists", path.exists(), str(path))

    if QUERY_DIFFICULTY.exists():
        frame = pd.read_csv(QUERY_DIFFICULTY)
        add(rows, "query_difficulty_nonempty", len(frame) > 0, f"rows={len(frame)}")
        add(rows, "oracle_ceiling_unit_interval", unit_interval(frame["oracle_top20_true_rate_ceiling"]), "oracle_top20_true_rate_ceiling")

    if SCORE_SEPARATION.exists():
        frame = pd.read_csv(SCORE_SEPARATION)
        add(rows, "score_separation_nonempty", len(frame) > 0, f"rows={len(frame)}")
        add(rows, "auc_same_unit_interval", unit_interval(frame["auc_for_same_identity"]), "auc_for_same_identity")

    if FAILURE_MODES.exists():
        frame = pd.read_csv(FAILURE_MODES)
        add(rows, "failure_modes_nonempty", len(frame) > 0, f"rows={len(frame)}")
        count_cols = ["raw_false_pf_true_rescue_count", "raw_true_pf_false_harm_count", "both_false_count", "both_true_count"]
        valid_counts = bool((frame[count_cols].apply(pd.to_numeric, errors="coerce") >= 0).all().all())
        add(rows, "failure_mode_counts_nonnegative", valid_counts, ",".join(count_cols))

    if CALIBRATED_POLICIES.exists():
        frame = pd.read_csv(CALIBRATED_POLICIES)
        add(rows, "selected_policy_rows_40", len(frame) == 40, f"rows={len(frame)}")

    if CALIBRATED_EVAL.exists():
        frame = pd.read_csv(CALIBRATED_EVAL)
        add(rows, "calibrated_eval_rows_120", len(frame) == 120, f"rows={len(frame)}")
        methods = set(frame["method_id"].astype(str))
        add(rows, "calibrated_eval_methods_present", {"raw_descriptor", "current_pf_eri_candidate_utility", "calibrated_policy"} <= methods, f"methods={sorted(methods)}")
        add(rows, "calibrated_eval_true_rate_unit_interval", unit_interval(frame["true_top1_rate_eligible"]), "true_top1_rate_eligible")

    if PAIRED_CONFIDENCE.exists():
        frame = pd.read_csv(PAIRED_CONFIDENCE)
        add(rows, "paired_confidence_nonempty", len(frame) > 0, f"rows={len(frame)}")
        add(rows, "paired_confidence_probability_unit_interval", unit_interval(frame["p_gt_0"]), "p_gt_0")

    if BUILD_AUDIT.exists():
        try:
            audit = json.loads(BUILD_AUDIT.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            add(rows, "build_audit_valid_json", False, str(exc))
        else:
            add(rows, "build_audit_valid_json", True, "valid")
            add(rows, "build_audit_800000_rows", int(audit.get("input_rows", 0)) == 800000, f"rows={audit.get('input_rows')}")
            add(rows, "build_audit_1000_query_images", int(audit.get("input_query_images", 0)) == 1000, f"query_images={audit.get('input_query_images')}")

    pd.DataFrame(rows).to_csv(AUDIT_OUT, index=False)
    pass_count = sum(row["status"] == "PASS" for row in rows)
    fail_count = sum(row["status"] == "FAIL" for row in rows)
    print(f"Phase 12D failure diagnosis audit: PASS={pass_count} FAIL={fail_count} output={AUDIT_OUT.relative_to(PROJECT_ROOT)}")
    if fail_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
