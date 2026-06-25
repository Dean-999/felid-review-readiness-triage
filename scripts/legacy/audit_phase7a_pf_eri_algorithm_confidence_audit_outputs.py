#!/usr/bin/env python3
"""Audit Phase 7A PF-ERI algorithm confidence-audit outputs."""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase7a/pf_eri_algorithm_confidence_audit"
FIGURE_DIR = OUTPUT_DIR / "figures"
SUMMARY_TXT = PROJECT_ROOT / "outputs/czechlynx/qc/phase7a_pf_eri_algorithm_confidence_audit_summary.txt"
REPORT_CSV = PROJECT_ROOT / "outputs/czechlynx/qc/phase7a_pf_eri_algorithm_confidence_audit_report.csv"

FILES = {
    "grid": OUTPUT_DIR / "phase7a_pf_eri_algorithm_variant_grid.csv",
    "top": OUTPUT_DIR / "phase7a_pf_eri_top_candidate_rules.csv",
    "uncertainty": OUTPUT_DIR / "phase7a_pf_eri_clustered_uncertainty_intervals.csv",
    "auc": OUTPUT_DIR / "phase7a_pf_eri_descriptor_auc_uncertainty.csv",
    "calibration": OUTPUT_DIR / "phase7a_pf_eri_calibration_bins.csv",
    "failure": OUTPUT_DIR / "phase7a_pf_eri_failure_mode_audit.csv",
    "readiness": OUTPUT_DIR / "phase7a_pf_eri_algorithm_readiness_decision.csv",
}

REQUIRED_FIGURES = [
    "risk_coverage_frontier_by_variant_family.png",
    "top_candidate_rule_comparison.png",
    "clustered_bootstrap_false_support_intervals.png",
    "descriptor_auc_clustered_intervals.png",
    "calibration_reliability_top_variants.png",
    "high_descriptor_low_visual_failure_mode_plot.png",
    "visual_gate_vs_descriptor_only_with_ci_context.png",
    "coverage_vs_false_support_all_candidate_rules.png",
]

FORBIDDEN_HEADER_PARTS = [
    "unique_name",
    "latitude",
    "longitude",
    "trap_id",
    "cell_code",
    "location",
    "raw_path",
    "review_image_path",
    "working_individual_id",
    "true_id",
    "image_id",
    "expanded_image_id",
    "source_image_id",
]

FORBIDDEN_PATTERNS = [
    re.compile(r"/Users/", re.IGNORECASE),
    re.compile(r"data/raw", re.IGNORECASE),
    re.compile(r"unique_name", re.IGNORECASE),
    re.compile(r"\blatitude\b", re.IGNORECASE),
    re.compile(r"\blongitude\b", re.IGNORECASE),
    re.compile(r"\btrap_id\b", re.IGNORECASE),
    re.compile(r"\bcell_code\b", re.IGNORECASE),
    re.compile(r"(?<![A-Za-z])lynx_[0-9]+", re.IGNORECASE),
]

OVERCLAIM_PATTERNS = [
    re.compile(r"deployment readiness", re.IGNORECASE),
    re.compile(r"clouded leopard validation", re.IGNORECASE),
    re.compile(r"safety[_ -]?score", re.IGNORECASE),
    re.compile(r"black[- ]box.*final", re.IGNORECASE),
    re.compile(r"final deployment", re.IGNORECASE),
]

REPORT_FIELDS = ["severity", "issue_type", "file", "row_id", "field", "value", "message"]


def add_issue(report, severity, issue_type, message, file="", row_id="", field="", value=""):
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


def is_number(value) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def scan_frame(name: str, path: Path, df: pd.DataFrame, report: list[dict[str, str]]) -> tuple[int, int]:
    leakage = 0
    overclaim = 0
    for column in df.columns:
        if any(part in column.lower() for part in FORBIDDEN_HEADER_PARTS):
            leakage += 1
            add_issue(report, "ERROR", "sensitive_header", "sensitive or row-level identifier header found", str(path), field=column)
        for pattern in OVERCLAIM_PATTERNS:
            if pattern.search(column):
                overclaim += 1
                add_issue(report, "ERROR", "overclaim_wording", "forbidden overclaim wording in header", str(path), field=column)
    for idx, row in df.astype(str).iterrows():
        row_id = row.get("variant_id", row.get("decision_area", str(idx)))
        for column, value in row.items():
            for pattern in FORBIDDEN_PATTERNS:
                if pattern.search(value):
                    leakage += 1
                    add_issue(report, "ERROR", "sensitive_value", "sensitive value pattern found", str(path), row_id, column, value[:120])
            for pattern in OVERCLAIM_PATTERNS:
                if pattern.search(value):
                    overclaim += 1
                    add_issue(report, "ERROR", "overclaim_wording", "forbidden overclaim wording found", str(path), row_id, column, value[:120])
    return leakage, overclaim


def audit(args: argparse.Namespace) -> int:
    report: list[dict[str, str]] = []
    loaded: dict[str, pd.DataFrame] = {}
    for name, path in FILES.items():
        if not path.exists():
            add_issue(report, "ERROR", "missing_output", f"missing output file: {path}", str(path))
        else:
            loaded[name] = pd.read_csv(path)

    if report:
        args.summary_txt.parent.mkdir(parents=True, exist_ok=True)
        args.summary_txt.write_text("FAIL\nmissing required outputs\n", encoding="utf-8")
        pd.DataFrame(report, columns=REPORT_FIELDS).to_csv(args.report_csv, index=False)
        print("FAIL: missing required outputs")
        return 1

    grid = loaded["grid"]
    top = loaded["top"]
    uncertainty = loaded["uncertainty"]
    auc = loaded["auc"]
    calibration = loaded["calibration"]
    failure = loaded["failure"]

    if len(grid) < 500:
        add_issue(report, "ERROR", "candidate_grid_too_small", f"candidate grid too small: {len(grid)}")
    if top.empty:
        add_issue(report, "ERROR", "empty_top_candidates", "top candidate rules are empty")
    if failure.empty:
        add_issue(report, "ERROR", "empty_failure_mode_audit", "failure-mode audit is empty")

    invalid_ci_count = 0
    for name, df in [("uncertainty", uncertainty), ("auc", auc), ("failure", failure)]:
        if {"ci_lower", "ci_upper"}.issubset(df.columns):
            estimate_col = "estimate" if "estimate" in df.columns else "AUC_estimate" if "AUC_estimate" in df.columns else "false_support_rate"
            for idx, row in df.iterrows():
                lower = row.get("ci_lower", row.get("CI_lower"))
                upper = row.get("ci_upper", row.get("CI_upper"))
                estimate = row.get(estimate_col)
                if not (is_number(lower) and is_number(upper)):
                    continue
                if float(lower) > float(upper):
                    invalid_ci_count += 1
                    add_issue(report, "ERROR", "invalid_ci_order", "CI lower exceeds CI upper", name, str(idx))
                if is_number(estimate) and not (float(lower) - 1e-9 <= float(estimate) <= float(upper) + 1e-9):
                    invalid_ci_count += 1
                    add_issue(report, "ERROR", "estimate_outside_ci", "estimate outside CI", name, str(idx), estimate_col, str(estimate))

    missing_cluster_count = 0
    for name, df in [("uncertainty", uncertainty), ("auc", auc), ("failure", failure)]:
        if "cluster_unit" not in df.columns or df["cluster_unit"].astype(str).str.strip().eq("").any():
            missing_cluster_count += 1
            add_issue(report, "ERROR", "missing_cluster_unit", f"cluster_unit missing in {name}", name)
        if "bootstrap_n" not in df.columns or df["bootstrap_n"].isna().any():
            missing_cluster_count += 1
            add_issue(report, "ERROR", "missing_bootstrap_n", f"bootstrap_n missing in {name}", name)

    invalid_calibration_count = 0
    required_calibration = {
        "variant_family",
        "bin_id",
        "pair_count",
        "observed_same_proportion",
        "observed_false_support_rate",
        "sparse_bin_flag",
    }
    missing_calibration = required_calibration - set(calibration.columns)
    if missing_calibration:
        invalid_calibration_count += len(missing_calibration)
        add_issue(report, "ERROR", "missing_calibration_columns", "missing calibration columns: " + ", ".join(sorted(missing_calibration)))
    else:
        bad_flags = set(calibration["sparse_bin_flag"].astype(str)) - {"yes", "no"}
        if bad_flags:
            invalid_calibration_count += len(bad_flags)
            add_issue(report, "ERROR", "invalid_sparse_bin_flag", "invalid sparse_bin_flag values: " + ", ".join(sorted(bad_flags)))

    leakage_count = 0
    overclaim_count = 0
    for name, path in FILES.items():
        leakage, overclaim = scan_frame(name, path, loaded[name], report)
        leakage_count += leakage
        overclaim_count += overclaim

    missing_figure_count = 0
    for figure in REQUIRED_FIGURES:
        path = args.figure_dir / figure
        if not path.exists() or path.stat().st_size == 0:
            missing_figure_count += 1
            add_issue(report, "ERROR", "missing_figure", f"missing or empty figure: {figure}", str(path))

    error_count = sum(1 for issue in report if issue["severity"] == "ERROR")
    warning_count = sum(1 for issue in report if issue["severity"] == "WARN")
    status = "PASS" if error_count == 0 else "FAIL"
    summary_lines = [
        status,
        f"candidate_rule_count: {len(grid)}",
        f"top_candidate_count: {len(top)}",
        f"invalid_ci_count: {invalid_ci_count}",
        f"missing_cluster_or_bootstrap_count: {missing_cluster_count}",
        f"invalid_calibration_count: {invalid_calibration_count}",
        f"leakage_issue_count: {leakage_count}",
        f"overclaim_issue_count: {overclaim_count}",
        f"missing_figure_count: {missing_figure_count}",
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
