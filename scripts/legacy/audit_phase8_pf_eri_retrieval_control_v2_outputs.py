#!/usr/bin/env python3
"""Audit Phase 8 PF-ERI retrieval-control v2 optimizer outputs."""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase8/pf_eri_retrieval_control_v2"
FIGURE_DIR = OUTPUT_DIR / "figures"
SUMMARY_TXT = PROJECT_ROOT / "outputs/czechlynx/qc/phase8_pf_eri_retrieval_control_v2_audit_summary.txt"
REPORT_CSV = PROJECT_ROOT / "outputs/czechlynx/qc/phase8_pf_eri_retrieval_control_v2_audit_report.csv"

FILES = {
    "policy_grid": OUTPUT_DIR / "phase8_pf_eri_retrieval_control_v2_policy_grid.csv",
    "top_policies": OUTPUT_DIR / "phase8_pf_eri_retrieval_control_v2_top_policies.csv",
    "assignments": OUTPUT_DIR / "phase8_pf_eri_retrieval_control_v2_recommended_assignments.csv",
    "failure_summary": OUTPUT_DIR / "phase8_pf_eri_retrieval_control_v2_failure_mode_summary.csv",
    "comparison": OUTPUT_DIR / "phase8_pf_eri_retrieval_control_v2_comparison_to_prior.csv",
    "bootstrap": OUTPUT_DIR / "phase8_pf_eri_retrieval_control_v2_bootstrap_intervals.csv",
    "readiness": OUTPUT_DIR / "phase8_pf_eri_retrieval_control_v2_readiness_decision.csv",
}

REQUIRED_FIGURES = [
    "phase8_v2_policy_frontier_coverage_vs_false_top1.png",
    "phase8_v2_review_burden_vs_positive_retention.png",
    "phase8_v2_top_policies_vs_prior.png",
    "phase8_v2_review_defer_exclude_counts.png",
    "phase8_v2_failure_mode_exposure_review_candidates.png",
    "phase8_v2_map_vs_coverage.png",
    "phase8_v2_bootstrap_intervals_balanced_policy.png",
]

VALID_ASSIGNMENTS = {"review_candidate", "defer_candidate", "exclude_candidate"}
RATE_COLUMNS = [
    "query_coverage",
    "positive_query_coverage",
    "review_burden_reduction",
    "defer_rate",
    "exclude_rate",
    "top1_success_among_covered_queries",
    "top3_success_among_covered_queries",
    "top5_success_among_covered_queries",
    "mAP_among_covered_positive_queries",
    "MRR_among_covered_positive_queries",
    "false_top1_rate_among_covered_queries",
    "false_reviewed_candidate_rate_at_topk",
    "true_same_identity_candidate_retention",
    "positive_retention",
    "failure_mode_exposure_among_review_candidates",
    "failure_mode_rate",
    "estimate",
    "ci_lower",
    "ci_upper",
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
    re.compile(r"validated clouded leopard", re.IGNORECASE),
    re.compile(r"validated marbled cat", re.IGNORECASE),
    re.compile(r"broader felid validation supported", re.IGNORECASE),
    re.compile(r"universal felid", re.IGNORECASE),
    re.compile(r"universal animal", re.IGNORECASE),
    re.compile(r"population estimation", re.IGNORECASE),
    re.compile(r"pf-eri.*identity model", re.IGNORECASE),
    re.compile(r"pf-eri.*identity classifier", re.IGNORECASE),
    re.compile(r"new re-id model", re.IGNORECASE),
]

REPORT_FIELDS = ["severity", "issue_type", "file", "row_id", "field", "value", "message"]


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
        row_id = row.get("policy_id", row.get("decision_item", str(idx)))
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

    missing_figures = 0
    for figure in REQUIRED_FIGURES:
        path = args.figure_dir / figure
        if not path.exists() or path.stat().st_size == 0:
            missing_figures += 1
            add_issue(report, "ERROR", "missing_figure", f"missing or empty figure: {figure}", str(path))

    if "policy_grid" in loaded:
        grid = loaded["policy_grid"]
        if grid.empty:
            add_issue(report, "ERROR", "empty_policy_grid", "policy grid is empty")
        if len(grid) < 5000:
            add_issue(report, "ERROR", "policy_grid_too_small", "policy grid must contain at least 5000 policies")
        expected = {
            "A_baseline_descriptor_retrieval",
            "C_pair_level_topk_pruning",
            "D_review_defer_exclude_triage",
            "E_failure_mode_conservative_triage",
            "F_balanced_review_burden_policy",
        }
        missing_families = sorted(expected - set(grid["policy_family"]))
        if missing_families:
            add_issue(report, "ERROR", "missing_policy_family", f"missing families: {', '.join(missing_families)}")
    if "top_policies" in loaded:
        top = loaded["top_policies"]
        if top.empty:
            add_issue(report, "ERROR", "empty_top_policies", "top policies output is empty")
        required_regimes = {"reliability_first", "balanced_main_v2_recommendation", "coverage_preserving", "evidence_control"}
        missing_regimes = sorted(required_regimes - set(top["selection_regime"]))
        if missing_regimes:
            add_issue(report, "ERROR", "missing_selection_regime", f"missing regimes: {', '.join(missing_regimes)}")
        if "main_recommendation" in top.columns and int((top["main_recommendation"] == "yes").sum()) != 1:
            add_issue(report, "ERROR", "invalid_main_recommendation", "exactly one top policy must be marked as main recommendation")
    if "assignments" in loaded:
        assignments = loaded["assignments"]
        if assignments.empty:
            add_issue(report, "ERROR", "empty_assignments", "recommended assignments output is empty")
        elif not set(assignments["recommended_assignment"]).issubset(VALID_ASSIGNMENTS):
            add_issue(report, "ERROR", "invalid_assignment_label", "assignments must be review/defer/exclude candidate")
    if "bootstrap" in loaded:
        boot = loaded["bootstrap"]
        if boot.empty:
            add_issue(report, "ERROR", "empty_bootstrap", "bootstrap interval output is empty")
        elif ((boot["ci_lower"] > boot["estimate"]) | (boot["estimate"] > boot["ci_upper"])).any():
            add_issue(report, "ERROR", "invalid_bootstrap_interval", "bootstrap intervals must contain estimates")

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
        f"policy_grid_row_count: {len(loaded.get('policy_grid', []))}",
        f"top_policy_row_count: {len(loaded.get('top_policies', []))}",
        f"assignment_row_count: {len(loaded.get('assignments', []))}",
        f"bootstrap_row_count: {len(loaded.get('bootstrap', []))}",
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
    return parser.parse_args()


def main() -> int:
    return audit(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
