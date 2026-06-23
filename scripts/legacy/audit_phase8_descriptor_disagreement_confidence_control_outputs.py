#!/usr/bin/env python3
"""Audit Phase 8 Slice 3B descriptor-disagreement confidence outputs."""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase8/descriptor_disagreement_confidence_control"
FIGURE_DIR = OUTPUT_DIR / "figures"
SUMMARY_TXT = PROJECT_ROOT / "outputs/czechlynx/qc/phase8_descriptor_disagreement_confidence_control_audit_summary.txt"
REPORT_CSV = PROJECT_ROOT / "outputs/czechlynx/qc/phase8_descriptor_disagreement_confidence_control_audit_report.csv"

FILES = {
    "definition_audit": OUTPUT_DIR / "phase8_descriptor_disagreement_definition_audit.csv",
    "policy_grid": OUTPUT_DIR / "phase8_descriptor_disagreement_policy_grid.csv",
    "top_policies": OUTPUT_DIR / "phase8_descriptor_disagreement_top_policies.csv",
    "comparison": OUTPUT_DIR / "phase8_descriptor_disagreement_v2_vs_v3_comparison.csv",
    "assignments": OUTPUT_DIR / "phase8_descriptor_disagreement_recommended_assignments.csv",
    "failure_summary": OUTPUT_DIR / "phase8_descriptor_disagreement_failure_mode_summary.csv",
    "bootstrap": OUTPUT_DIR / "phase8_descriptor_disagreement_bootstrap_intervals.csv",
    "paired_bootstrap": OUTPUT_DIR / "phase8_descriptor_disagreement_paired_bootstrap_differences.csv",
    "readiness": OUTPUT_DIR / "phase8_descriptor_disagreement_readiness_decision.csv",
}

REQUIRED_FIGURES = [
    "phase8_disagreement_exposure_vs_false_top1.png",
    "phase8_v2_vs_v3_metric_comparison.png",
    "phase8_bootstrap_intervals_selected_policies.png",
    "phase8_paired_bootstrap_differences_vs_v2.png",
    "phase8_disagreement_exposure_by_assignment.png",
    "phase8_coverage_vs_disagreement_reduction.png",
    "phase8_positive_retention_vs_disagreement_reduction.png",
    "phase8_failure_mode_exposure_review_candidates.png",
]

VALID_ASSIGNMENTS = {"review_candidate", "defer_candidate", "exclude_candidate"}
RATE_COLUMNS = [
    "query_coverage",
    "same_candidate_rate",
    "false_candidate_rate",
    "false_candidate_rate_unexposed",
    "v2_review_candidate_exposure",
    "positive_query_coverage",
    "review_burden_reduction",
    "false_top1_rate",
    "top1_success",
    "top3_success",
    "top5_success",
    "mAP_among_covered_positives",
    "MRR_among_covered_positives",
    "positive_retention",
    "true_same_candidate_retention",
    "false_reviewed_candidate_rate",
    "disagreement_exposure_review",
    "disagreement_exposure_defer",
    "disagreement_exposure_false_review",
    "same_candidate_rate_disagreement_review",
    "false_candidate_rate_disagreement_review",
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
    re.compile(r"pf-eri.*re-id model", re.IGNORECASE),
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

    if "definition_audit" in loaded and loaded["definition_audit"].empty:
        add_issue(report, "ERROR", "empty_definition_audit", "disagreement definition audit is empty")
    if "policy_grid" in loaded:
        grid = loaded["policy_grid"]
        if grid.empty:
            add_issue(report, "ERROR", "empty_policy_grid", "policy grid is empty")
        if len(grid) < 5000:
            add_issue(report, "ERROR", "policy_grid_too_small", "expected at least 5000 candidate v3 policies")
    if "top_policies" in loaded:
        top = loaded["top_policies"]
        if top.empty:
            add_issue(report, "ERROR", "empty_top_policies", "top policies output is empty")
        required = {"v2_baseline", "reliability_first_disagreement", "balanced_v3_main_candidate", "coverage_preserving_disagreement", "evidence_control"}
        missing = sorted(required - set(top["selection_regime"]))
        if missing:
            add_issue(report, "ERROR", "missing_regime", f"missing top-policy regimes: {', '.join(missing)}")
    if "assignments" in loaded:
        assignments = loaded["assignments"]
        if assignments.empty:
            add_issue(report, "ERROR", "empty_assignments", "recommended assignments output is empty")
        elif not set(assignments["recommended_assignment"]).issubset(VALID_ASSIGNMENTS):
            add_issue(report, "ERROR", "invalid_assignment", "invalid recommended assignment labels")
    if "bootstrap" in loaded:
        boot = loaded["bootstrap"]
        if boot.empty:
            add_issue(report, "ERROR", "empty_bootstrap", "bootstrap intervals are empty")
        elif ((boot["ci_lower"] > boot["estimate"]) | (boot["estimate"] > boot["ci_upper"])).any():
            add_issue(report, "ERROR", "invalid_bootstrap_interval", "bootstrap intervals must contain estimates")
    if "paired_bootstrap" in loaded:
        paired = loaded["paired_bootstrap"]
        if paired.empty:
            add_issue(report, "ERROR", "empty_paired_bootstrap", "paired bootstrap differences are empty")
        elif ((paired["ci_lower"] > paired["estimate"]) | (paired["estimate"] > paired["ci_upper"])).any():
            add_issue(report, "ERROR", "invalid_paired_bootstrap_interval", "paired bootstrap intervals must contain estimates")

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
        f"definition_audit_row_count: {len(loaded.get('definition_audit', []))}",
        f"policy_grid_row_count: {len(loaded.get('policy_grid', []))}",
        f"top_policy_row_count: {len(loaded.get('top_policies', []))}",
        f"assignment_row_count: {len(loaded.get('assignments', []))}",
        f"bootstrap_row_count: {len(loaded.get('bootstrap', []))}",
        f"paired_bootstrap_row_count: {len(loaded.get('paired_bootstrap', []))}",
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
