#!/usr/bin/env python3
"""Audit Phase 12C confidence evidence outputs."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase12/rq_confidence_evidence"
TOP1_SPLIT = OUT_DIR / "phase12c_top1_split_metrics.csv"
TOP1_PAIRED = OUT_DIR / "phase12c_top1_paired_confidence.csv"
TOPK_BURDEN = OUT_DIR / "phase12c_topk_false_burden_positive_retention.csv"
RELIABILITY_THRESHOLD = OUT_DIR / "phase12c_reliability_threshold_curve.csv"
CONFLICT_ENRICHMENT = OUT_DIR / "phase12c_conflict_enrichment.csv"
RANDOM_CONTROL = OUT_DIR / "phase12c_random_top20_control.csv"
SUMMARY_MD = OUT_DIR / "phase12c_confidence_evidence_summary.md"
BUILD_AUDIT = OUT_DIR / "phase12c_confidence_evidence_build_audit.json"
AUDIT_OUT = OUT_DIR / "phase12c_confidence_evidence_audit.csv"


def add(rows: list[dict[str, object]], check: str, passed: bool, detail: str) -> None:
    rows.append({"check": check, "status": "PASS" if passed else "FAIL", "detail": detail})


def unit_interval(series: pd.Series) -> bool:
    values = pd.to_numeric(series, errors="coerce").dropna()
    return bool(((values >= 0) & (values <= 1)).all())


def main() -> None:
    rows: list[dict[str, object]] = []
    outputs = {
        "top1_split": TOP1_SPLIT,
        "top1_paired": TOP1_PAIRED,
        "topk_burden": TOPK_BURDEN,
        "reliability_threshold": RELIABILITY_THRESHOLD,
        "conflict_enrichment": CONFLICT_ENRICHMENT,
        "random_control": RANDOM_CONTROL,
        "summary_md": SUMMARY_MD,
        "build_audit": BUILD_AUDIT,
    }
    for label, path in outputs.items():
        add(rows, f"{label}_exists", path.exists(), str(path))

    if TOP1_SPLIT.exists():
        frame = pd.read_csv(TOP1_SPLIT)
        add(rows, "top1_split_nonempty", len(frame) > 0, f"rows={len(frame)}")
        add(rows, "top1_false_rate_unit_interval", unit_interval(frame["false_top1_rate"]), "false_top1_rate")
        methods = set(frame["method_id"].astype(str))
        add(rows, "top1_methods_present", {"raw_descriptor", "pf_eri_candidate_utility", "quality_only", "pair_reliability"} <= methods, f"methods={sorted(methods)}")

    if TOP1_PAIRED.exists():
        frame = pd.read_csv(TOP1_PAIRED)
        add(rows, "top1_paired_nonempty", len(frame) > 0, f"rows={len(frame)}")
        add(rows, "paired_direction_probability_unit_interval", unit_interval(frame["p_direction_gt_0"]), "p_direction_gt_0")
        add(rows, "paired_split_count_20", set(frame["split_pair_count"].astype(int)) == {20}, f"split_counts={sorted(set(frame['split_pair_count'].astype(int)))}")

    if TOPK_BURDEN.exists():
        frame = pd.read_csv(TOPK_BURDEN)
        add(rows, "topk_burden_nonempty", len(frame) > 0, f"rows={len(frame)}")
        add(rows, "positive_present_top5_unit_interval", unit_interval(frame["positive_present_top5_rate"]), "positive_present_top5_rate")

    if RELIABILITY_THRESHOLD.exists():
        frame = pd.read_csv(RELIABILITY_THRESHOLD)
        add(rows, "reliability_threshold_nonempty", len(frame) > 0, f"rows={len(frame)}")
        add(rows, "threshold_query_coverage_unit_interval", unit_interval(frame["query_coverage"]), "query_coverage")
        thresholds = set(pd.to_numeric(frame["pair_reliability_threshold"], errors="coerce").round(2))
        add(rows, "threshold_grid_present", {0.0, 0.25, 0.5, 0.75, 1.0} <= thresholds, f"thresholds={sorted(thresholds)[:5]}...{sorted(thresholds)[-5:]}")

    if CONFLICT_ENRICHMENT.exists():
        frame = pd.read_csv(CONFLICT_ENRICHMENT)
        add(rows, "conflict_enrichment_nonempty", len(frame) > 0, f"rows={len(frame)}")
        populations = set(frame["population"].astype(str))
        add(rows, "conflict_populations_present", {"all_candidates", "hard_negative_candidates", "false_candidates"} <= populations, f"populations={sorted(populations)}")

    if RANDOM_CONTROL.exists():
        frame = pd.read_csv(RANDOM_CONTROL)
        add(rows, "random_control_nonempty", len(frame) > 0, f"rows={len(frame)}")
        add(rows, "random_control_iterations_200", int(frame["iteration"].nunique()) == 200, f"iterations={frame['iteration'].nunique()}")
        add(rows, "random_control_false_rate_unit_interval", unit_interval(frame["false_top1_rate"]), "false_top1_rate")

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
    print(f"Phase 12C confidence evidence audit: PASS={pass_count} FAIL={fail_count} output={AUDIT_OUT.relative_to(PROJECT_ROOT)}")
    if fail_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
