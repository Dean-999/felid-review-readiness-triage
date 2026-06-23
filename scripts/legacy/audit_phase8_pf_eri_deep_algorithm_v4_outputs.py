#!/usr/bin/env python3
"""Audit Phase 8 Slice 3D PF-ERI v4 outputs."""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase8/pf_eri_deep_algorithm_v4"
FIGURE_DIR = OUTPUT_DIR / "figures"
SUMMARY_TXT = PROJECT_ROOT / "outputs/czechlynx/qc/phase8_pf_eri_deep_algorithm_v4_audit_summary.txt"
REPORT_CSV = PROJECT_ROOT / "outputs/czechlynx/qc/phase8_pf_eri_deep_algorithm_v4_audit_report.csv"
REVIEW_DOC = PROJECT_ROOT / "docs/phase8/phase8_slice3d_algorithm_review_and_pf_eri_redesign_plan.md"
RESULTS_DOC = PROJECT_ROOT / "docs/phase8/phase8_slice3d_pf_eri_deep_algorithm_v4_results.md"

FILES = {
    "variant_comparison": OUTPUT_DIR / "phase8_pf_eri_v4_variant_comparison.csv",
    "policy_grid": OUTPUT_DIR / "phase8_pf_eri_v4_policy_grid.csv",
    "top_variants": OUTPUT_DIR / "phase8_pf_eri_v4_top_variants.csv",
    "assignments": OUTPUT_DIR / "phase8_pf_eri_v4_recommended_assignments.csv",
    "bootstrap": OUTPUT_DIR / "phase8_pf_eri_v4_bootstrap_intervals.csv",
    "sensitivity": OUTPUT_DIR / "phase8_pf_eri_v4_sensitivity_audit.csv",
    "failure_summary": OUTPUT_DIR / "phase8_pf_eri_v4_failure_mode_summary.csv",
    "algorithm_decision": OUTPUT_DIR / "phase8_pf_eri_v4_algorithm_decision.csv",
}

REQUIRED_FIGURES = [
    "phase8_v4_coverage_vs_false_top1.png",
    "phase8_v4_workload_vs_positive_retention.png",
    "phase8_v4_false_reviewed_candidates_by_variant.png",
    "phase8_v4_review_tier_distribution.png",
    "phase8_v4_review_clear_vs_caution_risk.png",
    "phase8_v4_bootstrap_intervals_top_variants.png",
    "phase8_v4_sensitivity_lineplot.png",
    "phase8_v4_failure_mode_exposure_review_tiers.png",
]

VALID_DETAIL_CLASSES = {
    "review_clear",
    "review_caution",
    "defer_visual",
    "defer_descriptor_conflict",
    "defer_low_confidence",
    "exclude_inadmissible",
}
VALID_SIMPLE_CLASSES = {"review_candidate", "defer_candidate", "exclude_candidate"}
REPORT_FIELDS = ["severity", "issue_type", "file", "row_id", "field", "value", "message"]

RATE_COLUMNS = [
    "query_coverage",
    "positive_query_coverage",
    "positive_retention",
    "review_burden_reduction",
    "defer_rate",
    "exclude_rate",
    "false_top1_rate",
    "top1_success",
    "top3_success",
    "top5_success",
    "mAP",
    "MRR",
    "same_candidate_retention",
    "false_candidate_review_rate",
    "descriptor_disagreement_exposure",
    "reciprocal_retrieval_support_rate",
    "review_clear_risk",
    "review_caution_risk",
    "failure_exposure_review",
    "failure_mode_rate",
]

FORBIDDEN_HEADER_PARTS = [
    "unique_name",
    "latitude",
    "longitude",
    "trap_id",
    "cell_code",
    "raw_path",
    "review_image_path",
    "image_path",
    "expanded_image_id",
    "source_image_id",
    "working_individual_id",
    "identity_token",
    "true_id",
    "query_token",
    "gallery_token",
]

FORBIDDEN_VALUE_PATTERNS = [
    re.compile(r"/Users/", re.IGNORECASE),
    re.compile(r"data/raw", re.IGNORECASE),
    re.compile(r"unique_name", re.IGNORECASE),
    re.compile(r"\blatitude\b", re.IGNORECASE),
    re.compile(r"\blongitude\b", re.IGNORECASE),
    re.compile(r"\btrap_id\b", re.IGNORECASE),
    re.compile(r"\bcell_code\b", re.IGNORECASE),
    re.compile(r"(?<![A-Za-z])lynx_[0-9]+", re.IGNORECASE),
    re.compile(r"czlx_expanded_[0-9]+", re.IGNORECASE),
]

OVERCLAIM_PATTERNS = [
    re.compile(r"field deployment readiness", re.IGNORECASE),
    re.compile(r"field readiness", re.IGNORECASE),
    re.compile(r"validated clouded leopard", re.IGNORECASE),
    re.compile(r"validated marbled cat", re.IGNORECASE),
    re.compile(r"broader felid validation supported", re.IGNORECASE),
    re.compile(r"universal felid", re.IGNORECASE),
    re.compile(r"universal animal", re.IGNORECASE),
    re.compile(r"population estimation", re.IGNORECASE),
    re.compile(r"new re-id model", re.IGNORECASE),
    re.compile(r"identity classifier", re.IGNORECASE),
    re.compile(r"true individual identification", re.IGNORECASE),
    re.compile(r"mainland clouded leopard.*validated", re.IGNORECASE),
    re.compile(r"marbled cat.*validated", re.IGNORECASE),
]


def add_issue(report: list[dict[str, str]], severity: str, issue_type: str, message: str,
              file: str = "", row_id: str = "", field: str = "", value: str = "") -> None:
    report.append(
        {
            "severity": severity,
            "issue_type": issue_type,
            "file": file,
            "row_id": row_id,
            "field": field,
            "value": value,
            "message": message,
        }
    )


def valid_rate(value: object) -> bool:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return False
    return math.isnan(v) or 0.0 <= v <= 1.0


def scan_frame(path: Path, df: pd.DataFrame, report: list[dict[str, str]]) -> tuple[int, int]:
    leakage = 0
    overclaim = 0
    for column in df.columns:
        lower = column.lower()
        if any(part in lower for part in FORBIDDEN_HEADER_PARTS):
            leakage += 1
            add_issue(report, "ERROR", "sensitive_header", "sensitive header found", str(path), field=column)
        for pattern in OVERCLAIM_PATTERNS:
            if pattern.search(column):
                overclaim += 1
                add_issue(report, "ERROR", "overclaim_header", "forbidden overclaim wording in header", str(path), field=column)
    for idx, row in df.astype(str).iterrows():
        row_id = row.get("variant_id", row.get("decision_item", str(idx)))
        for column, value in row.items():
            for pattern in FORBIDDEN_VALUE_PATTERNS:
                if pattern.search(value):
                    leakage += 1
                    add_issue(report, "ERROR", "sensitive_value", "sensitive value pattern found", str(path), str(row_id), column, value[:140])
            for pattern in OVERCLAIM_PATTERNS:
                if pattern.search(value):
                    overclaim += 1
                    add_issue(report, "ERROR", "overclaim_value", "forbidden overclaim wording found", str(path), str(row_id), column, value[:140])
    return leakage, overclaim


def audit(args: argparse.Namespace) -> int:
    report: list[dict[str, str]] = []
    loaded: dict[str, pd.DataFrame] = {}
    for name, path in FILES.items():
        if not path.exists():
            add_issue(report, "ERROR", "missing_output", f"missing output file: {path}", str(path))
        else:
            loaded[name] = pd.read_csv(path)
    for doc in [args.review_doc, args.results_doc]:
        if not doc.exists() or doc.stat().st_size == 0:
            add_issue(report, "ERROR", "missing_doc", f"missing or empty doc: {doc}", str(doc))

    missing_figures = 0
    for figure in REQUIRED_FIGURES:
        path = args.figure_dir / figure
        if not path.exists() or path.stat().st_size == 0:
            missing_figures += 1
            add_issue(report, "ERROR", "missing_figure", f"missing or empty figure: {figure}", str(path))

    if "variant_comparison" in loaded and loaded["variant_comparison"].empty:
        add_issue(report, "ERROR", "empty_variant_comparison", "variant comparison is empty")
    if "policy_grid" in loaded:
        grid = loaded["policy_grid"]
        if grid.empty:
            add_issue(report, "ERROR", "empty_policy_grid", "policy grid is empty")
        if len(grid) < 1000:
            add_issue(report, "ERROR", "small_policy_grid", "expected at least 1000 v4 policy candidates")
    if "assignments" in loaded:
        assignments = loaded["assignments"]
        if assignments.empty:
            add_issue(report, "ERROR", "empty_assignments", "recommended assignments are empty")
        if not set(assignments.get("final_class", [])).issubset(VALID_SIMPLE_CLASSES):
            add_issue(report, "ERROR", "invalid_final_class", "invalid simplified final classes")
        if not set(assignments.get("detailed_assignment", [])).issubset(VALID_DETAIL_CLASSES):
            add_issue(report, "ERROR", "invalid_detailed_assignment", "invalid detailed assignment classes")
    if "bootstrap" in loaded:
        boot = loaded["bootstrap"]
        if boot.empty:
            add_issue(report, "ERROR", "empty_bootstrap", "bootstrap intervals are empty")
        elif ((boot["ci_lower"] > boot["estimate"]) | (boot["estimate"] > boot["ci_upper"])).any():
            add_issue(report, "ERROR", "invalid_bootstrap_interval", "bootstrap intervals must contain estimates")
    if "sensitivity" in loaded and loaded["sensitivity"].empty:
        add_issue(report, "ERROR", "empty_sensitivity", "sensitivity audit is empty")
    if "algorithm_decision" in loaded:
        final = loaded["algorithm_decision"]
        required = {
            "v4_replaces_candidate_f",
            "candidate_f_remains_primary",
            "v4_becomes_refinement_only",
            "strongest_algorithm_contribution",
            "unresolved_risks",
            "readiness_for_external_patterned_felid_access_audit",
            "broader_felid_claim_boundary",
            "mainland_clouded_leopard_marbled_cat_boundary",
        }
        missing = sorted(required - set(final.get("decision_item", [])))
        if missing:
            add_issue(report, "ERROR", "missing_decision_item", f"missing decision items: {', '.join(missing)}")

    for name, df in loaded.items():
        for column in RATE_COLUMNS:
            if column in df.columns and not df[column].map(valid_rate).all():
                add_issue(report, "ERROR", "invalid_rate", f"invalid rate values in {column}", str(FILES[name]), field=column)

    leakage = 0
    overclaim = 0
    for name, df in loaded.items():
        leak_count, over_count = scan_frame(FILES[name], df, report)
        leakage += leak_count
        overclaim += over_count

    error_count = sum(1 for issue in report if issue["severity"] == "ERROR")
    warning_count = sum(1 for issue in report if issue["severity"] == "WARN")
    status = "PASS" if error_count == 0 else "FAIL"
    summary_lines = [
        status,
        f"variant_comparison_row_count: {len(loaded.get('variant_comparison', []))}",
        f"policy_grid_row_count: {len(loaded.get('policy_grid', []))}",
        f"top_variant_row_count: {len(loaded.get('top_variants', []))}",
        f"assignment_row_count: {len(loaded.get('assignments', []))}",
        f"bootstrap_row_count: {len(loaded.get('bootstrap', []))}",
        f"sensitivity_row_count: {len(loaded.get('sensitivity', []))}",
        f"failure_summary_row_count: {len(loaded.get('failure_summary', []))}",
        f"algorithm_decision_row_count: {len(loaded.get('algorithm_decision', []))}",
        f"leakage_issue_count: {leakage}",
        f"overclaim_issue_count: {overclaim}",
        f"missing_figure_count: {missing_figures}",
        f"error_count: {error_count}",
        f"warning_count: {warning_count}",
    ]
    args.summary_txt.parent.mkdir(parents=True, exist_ok=True)
    args.summary_txt.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    pd.DataFrame(report, columns=REPORT_FIELDS).to_csv(args.report_csv, index=False)
    print(status)
    for line in summary_lines[1:]:
        print(line)
    return 0 if status == "PASS" else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--figure-dir", type=Path, default=FIGURE_DIR)
    parser.add_argument("--summary-txt", type=Path, default=SUMMARY_TXT)
    parser.add_argument("--report-csv", type=Path, default=REPORT_CSV)
    parser.add_argument("--review-doc", type=Path, default=REVIEW_DOC)
    parser.add_argument("--results-doc", type=Path, default=RESULTS_DOC)
    return parser.parse_args()


def main() -> int:
    return audit(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
