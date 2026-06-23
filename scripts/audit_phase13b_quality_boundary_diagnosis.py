#!/usr/bin/env python3
"""Audit Phase 13B quality-boundary diagnosis outputs."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase13/quality_boundary_diagnosis"

QUERY_OUTCOME = OUT_DIR / "phase13b_query_level_rescue_harm.csv"
FEATURE_CONTRAST = OUT_DIR / "phase13b_rescue_harm_feature_contrast.csv"
RISK_CONTRAST = OUT_DIR / "phase13b_risk_coverage_boundary_contrast.csv"
SUMMARY_MD = OUT_DIR / "phase13b_quality_boundary_diagnosis_summary.md"
BUILD_AUDIT = OUT_DIR / "phase13b_quality_boundary_diagnosis_build_audit.json"
AUDIT_OUT = OUT_DIR / "phase13b_quality_boundary_diagnosis_audit.csv"


def add(rows: list[dict[str, object]], check: str, passed: bool, detail: str) -> None:
    rows.append({"check": check, "status": "PASS" if passed else "FAIL", "detail": detail})


def main() -> None:
    rows: list[dict[str, object]] = []
    for label, path in {
        "query_outcome": QUERY_OUTCOME,
        "feature_contrast": FEATURE_CONTRAST,
        "risk_contrast": RISK_CONTRAST,
        "summary_md": SUMMARY_MD,
        "build_audit": BUILD_AUDIT,
    }.items():
        add(rows, f"{label}_exists", path.exists(), str(path))

    if QUERY_OUTCOME.exists():
        frame = pd.read_csv(QUERY_OUTCOME)
        add(rows, "query_outcome_nonempty", len(frame) > 0, f"rows={len(frame)}")
        valid_counts = bool((frame[["rescue_count", "harm_count", "both_true_count", "both_false_count"]] >= 0).all().all())
        add(rows, "query_outcome_counts_nonnegative", valid_counts, "rescue/harm/both counts")
        total_ok = bool(
            (
                frame["rescue_count"]
                + frame["harm_count"]
                + frame["both_true_count"]
                + frame["both_false_count"]
                == frame["query_count"]
            ).all()
        )
        add(rows, "query_outcome_counts_sum_to_query_count", total_ok, "rescue + harm + both_true + both_false")

    if FEATURE_CONTRAST.exists():
        frame = pd.read_csv(FEATURE_CONTRAST)
        add(rows, "feature_contrast_nonempty", len(frame) > 0, f"rows={len(frame)}")
        add(rows, "feature_contrast_has_rescue_harm", {"mean_rescue", "mean_harm", "rescue_minus_harm"} <= set(frame.columns), "contrast columns")

    if RISK_CONTRAST.exists():
        frame = pd.read_csv(RISK_CONTRAST)
        add(rows, "risk_contrast_nonempty", len(frame) > 0, f"rows={len(frame)}")
        coverage = pd.to_numeric(frame["coverage"], errors="coerce")
        add(rows, "risk_contrast_coverage_unit_interval", bool(((coverage >= 0) & (coverage <= 1)).all()), "coverage")

    if BUILD_AUDIT.exists():
        try:
            audit = json.loads(BUILD_AUDIT.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            add(rows, "build_audit_valid_json", False, str(exc))
        else:
            add(rows, "build_audit_valid_json", True, "valid")
            add(rows, "build_audit_has_comparisons", len(audit.get("comparisons", [])) >= 4, f"comparisons={audit.get('comparisons')}")

    pd.DataFrame(rows).to_csv(AUDIT_OUT, index=False)
    pass_count = sum(row["status"] == "PASS" for row in rows)
    fail_count = sum(row["status"] == "FAIL" for row in rows)
    print(f"Phase 13B quality-boundary audit: PASS={pass_count} FAIL={fail_count} output={AUDIT_OUT.relative_to(PROJECT_ROOT)}")
    if fail_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
