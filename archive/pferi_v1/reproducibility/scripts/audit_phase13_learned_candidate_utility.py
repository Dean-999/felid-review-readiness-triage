#!/usr/bin/env python3
"""Audit Phase 13 learned candidate-utility outputs."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase13/learned_candidate_utility"

TRAINING_TABLE = OUT_DIR / "phase13_candidate_utility_training_table.csv"
MODEL_RESULTS = OUT_DIR / "phase13_calibrated_utility_model_results.csv"
RISK_COVERAGE = OUT_DIR / "phase13_risk_coverage_comparison.csv"
ABLATION_SUMMARY = OUT_DIR / "phase13_model_ablation_summary.csv"
HOLDOUT_CONFIDENCE = OUT_DIR / "phase13_holdout_confidence_summary.csv"
TOP1_SELECTIONS = OUT_DIR / "phase13_top1_selection_records.csv"
SUMMARY_MD = OUT_DIR / "phase13_learned_candidate_utility_summary.md"
BUILD_AUDIT = OUT_DIR / "phase13_learned_candidate_utility_build_audit.json"
AUDIT_OUT = OUT_DIR / "phase13_learned_candidate_utility_audit.csv"


def add(rows: list[dict[str, object]], check: str, passed: bool, detail: str) -> None:
    rows.append({"check": check, "status": "PASS" if passed else "FAIL", "detail": detail})


def unit_interval(series: pd.Series) -> bool:
    values = pd.to_numeric(series, errors="coerce").dropna()
    return bool(((values >= 0) & (values <= 1)).all())


def main() -> None:
    rows: list[dict[str, object]] = []
    outputs = {
        "training_table": TRAINING_TABLE,
        "model_results": MODEL_RESULTS,
        "risk_coverage": RISK_COVERAGE,
        "ablation_summary": ABLATION_SUMMARY,
        "holdout_confidence": HOLDOUT_CONFIDENCE,
        "top1_selections": TOP1_SELECTIONS,
        "summary_md": SUMMARY_MD,
        "build_audit": BUILD_AUDIT,
    }
    for label, path in outputs.items():
        add(rows, f"{label}_exists", path.exists(), str(path))

    if TRAINING_TABLE.exists():
        frame = pd.read_csv(TRAINING_TABLE)
        add(rows, "training_table_800000_rows", len(frame) == 800000, f"rows={len(frame)}")
        forbidden = {"query_identity_token", "candidate_identity_token", "unique_name", "latitude", "longitude", "trap_id", "cell_code"}
        add(rows, "training_table_no_sensitive_columns", forbidden.isdisjoint(frame.columns), f"forbidden_present={sorted(forbidden & set(frame.columns))}")
        add(rows, "training_table_1000_queries", frame["query_image_id"].nunique() == 1000, f"queries={frame['query_image_id'].nunique()}")

    if MODEL_RESULTS.exists():
        frame = pd.read_csv(MODEL_RESULTS)
        add(rows, "model_results_rows_360", len(frame) == 360, f"rows={len(frame)}")
        methods = set(frame["method_id"].astype(str))
        required = {
            "raw_descriptor",
            "fixed_pf_eri_candidate_utility",
            "fixed_quality_only",
            "fixed_conflict_penalty",
            "learned_descriptor_logistic",
            "learned_quality_control_logistic",
            "learned_pf_eri_full_logistic",
            "learned_pf_eri_interaction_logistic",
            "learned_pf_eri_monotonic_hgb",
        }
        add(rows, "all_methods_present", required <= methods, f"methods={sorted(methods)}")
        for column in ["candidate_roc_auc", "candidate_average_precision", "true_top1_rate_eligible", "false_top1_rate_eligible", "positive_present_top5_rate"]:
            add(rows, f"{column}_unit_interval", unit_interval(frame[column]), column)

    if RISK_COVERAGE.exists():
        frame = pd.read_csv(RISK_COVERAGE)
        add(rows, "risk_coverage_rows_3600", len(frame) == 3600, f"rows={len(frame)}")
        add(rows, "risk_coverage_coverage_unit_interval", unit_interval(frame["coverage"]), "coverage")
        add(rows, "risk_coverage_risk_unit_interval", unit_interval(frame["false_top1_rate_eligible"]), "false_top1_rate_eligible")

    if ABLATION_SUMMARY.exists():
        frame = pd.read_csv(ABLATION_SUMMARY)
        add(rows, "ablation_summary_nonempty", len(frame) > 0, f"rows={len(frame)}")
        add(rows, "ablation_probability_unit_interval", unit_interval(frame["p_gt_0"]), "p_gt_0")
        expected = {"learned_pf_eri_full_logistic", "learned_pf_eri_interaction_logistic", "learned_pf_eri_monotonic_hgb"}
        add(rows, "ablation_learned_pf_eri_present", expected <= set(frame["method_id"].astype(str)), f"methods={sorted(set(frame['method_id'].astype(str)))}")

    if HOLDOUT_CONFIDENCE.exists():
        frame = pd.read_csv(HOLDOUT_CONFIDENCE)
        add(rows, "holdout_confidence_nonempty", len(frame) > 0, f"rows={len(frame)}")
        add(rows, "holdout_split_counts_positive", bool((pd.to_numeric(frame["split_count"], errors="coerce") > 0).all()), "split_count")

    if TOP1_SELECTIONS.exists():
        frame = pd.read_csv(TOP1_SELECTIONS)
        if MODEL_RESULTS.exists():
            results = pd.read_csv(MODEL_RESULTS)
            expected_rows = int(results["query_count"].sum())
            add(rows, "top1_records_expected_rows", len(frame) == expected_rows, f"rows={len(frame)} expected={expected_rows}")
        else:
            add(rows, "top1_records_expected_rows", False, "model results missing")
        add(rows, "top1_records_one_per_query_method_split", frame.groupby(["split_id", "descriptor", "method_id", "query_image_id"]).size().max() == 1, "group max should be 1")

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
    print(f"Phase 13 learned candidate utility audit: PASS={pass_count} FAIL={fail_count} output={AUDIT_OUT.relative_to(PROJECT_ROOT)}")
    if fail_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
