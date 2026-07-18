#!/usr/bin/env python3
"""Audit Phase 12B RQ1-RQ3 evidence analysis outputs."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase12/rq1_rq3_evidence_analysis"
BAND_SUMMARY = OUT_DIR / "phase12b_rq1_admissibility_band_summary.csv"
PREDICTOR_SUMMARY = OUT_DIR / "phase12b_rq1_predictor_diagnostic_summary.csv"
CONFLICT_SUMMARY = OUT_DIR / "phase12b_rq2_conflict_group_summary.csv"
RISK_COVERAGE = OUT_DIR / "phase12b_rq3_risk_coverage_curve.csv"
METHOD_SUMMARY = OUT_DIR / "phase12b_rq3_method_summary.csv"
RESEARCH_SUMMARY = OUT_DIR / "phase12b_research_evidence_summary.md"
BUILD_AUDIT = OUT_DIR / "phase12b_evidence_analysis_build_audit.json"
AUDIT_OUT = OUT_DIR / "phase12b_evidence_analysis_audit.csv"


def add(rows: list[dict[str, object]], check: str, passed: bool, detail: str) -> None:
    rows.append({"check": check, "status": "PASS" if passed else "FAIL", "detail": detail})


def main() -> None:
    rows: list[dict[str, object]] = []
    outputs = {
        "band_summary": BAND_SUMMARY,
        "predictor_summary": PREDICTOR_SUMMARY,
        "conflict_summary": CONFLICT_SUMMARY,
        "risk_coverage": RISK_COVERAGE,
        "method_summary": METHOD_SUMMARY,
        "research_summary": RESEARCH_SUMMARY,
        "build_audit": BUILD_AUDIT,
    }
    for label, path in outputs.items():
        add(rows, f"{label}_exists", path.exists(), str(path))

    if BAND_SUMMARY.exists():
        band = pd.read_csv(BAND_SUMMARY)
        add(rows, "band_summary_nonempty", len(band) > 0, f"rows={len(band)}")
        bands = set(band["admissibility_band"].astype(str))
        add(rows, "admissibility_bands_present", {"high", "medium", "low", "unusable"} <= bands, f"bands={sorted(bands)}")
        rates = pd.to_numeric(band["false_candidate_rate"], errors="coerce")
        add(rows, "band_false_rates_valid", bool(((rates >= 0) & (rates <= 1)).all()), f"min={rates.min()} max={rates.max()}")

    if PREDICTOR_SUMMARY.exists():
        predictors = pd.read_csv(PREDICTOR_SUMMARY)
        add(rows, "predictor_summary_nonempty", len(predictors) > 0, f"rows={len(predictors)}")
        expected = {
            "pf_eri_pair_reliability_risk",
            "image_quality_min_risk",
            "candidate_utility_risk_inverse",
            "descriptor_evidence_conflict_score",
        }
        observed = set(predictors["predictor"].astype(str))
        add(rows, "expected_predictors_present", expected <= observed, f"predictors={sorted(observed)}")
        auc = pd.to_numeric(predictors["auc_for_false_candidate_risk"], errors="coerce").dropna()
        add(rows, "predictor_auc_unit_interval", bool(((auc >= 0) & (auc <= 1)).all()), f"min={auc.min()} max={auc.max()}")

    if CONFLICT_SUMMARY.exists():
        conflict = pd.read_csv(CONFLICT_SUMMARY)
        add(rows, "conflict_summary_nonempty", len(conflict) > 0, f"rows={len(conflict)}")
        groups = set(conflict["conflict_group"].astype(str))
        add(
            rows,
            "conflict_groups_present",
            {"high_similarity_low_admissibility_conflict", "high_similarity_high_admissibility"} <= groups,
            f"groups={sorted(groups)}",
        )

    if RISK_COVERAGE.exists():
        curve = pd.read_csv(RISK_COVERAGE)
        add(rows, "risk_coverage_nonempty", len(curve) > 0, f"rows={len(curve)}")
        methods = set(curve["method_id"].astype(str))
        expected_methods = {
            "raw_descriptor_top1",
            "pf_eri_candidate_utility_top1",
            "quality_only_rerank_top1",
            "pair_reliability_rerank_top1",
        }
        add(rows, "risk_coverage_methods_present", expected_methods <= methods, f"methods={sorted(methods)}")
        coverage = pd.to_numeric(curve["coverage"], errors="coerce").dropna()
        add(rows, "coverage_unit_interval", bool(((coverage >= 0) & (coverage <= 1)).all()), f"min={coverage.min()} max={coverage.max()}")

    if METHOD_SUMMARY.exists():
        methods = pd.read_csv(METHOD_SUMMARY)
        add(rows, "method_summary_nonempty", len(methods) > 0, f"rows={len(methods)}")

    if BUILD_AUDIT.exists():
        try:
            audit = json.loads(BUILD_AUDIT.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            add(rows, "build_audit_valid_json", False, str(exc))
        else:
            add(rows, "build_audit_valid_json", True, "valid")
            add(rows, "build_audit_1000_query_images", int(audit.get("input_query_images", 0)) == 1000, f"query_images={audit.get('input_query_images')}")
            add(rows, "build_audit_800000_rows", int(audit.get("input_rows", 0)) == 800000, f"rows={audit.get('input_rows')}")

    pd.DataFrame(rows).to_csv(AUDIT_OUT, index=False)
    pass_count = sum(row["status"] == "PASS" for row in rows)
    fail_count = sum(row["status"] == "FAIL" for row in rows)
    print(f"Phase 12B evidence analysis audit: PASS={pass_count} FAIL={fail_count} output={AUDIT_OUT.relative_to(PROJECT_ROOT)}")
    if fail_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
