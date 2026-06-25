#!/usr/bin/env python3
"""Audit Phase 7A CI-aware PF-ERI policy optimizer outputs."""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase7a/pf_eri_policy_optimization"
FIGURE_DIR = OUTPUT_DIR / "figures"
SUMMARY_TXT = PROJECT_ROOT / "outputs/czechlynx/qc/phase7a_pf_eri_policy_optimization_audit_summary.txt"
REPORT_CSV = PROJECT_ROOT / "outputs/czechlynx/qc/phase7a_pf_eri_policy_optimization_audit_report.csv"

FILES = {
    "grid": OUTPUT_DIR / "phase7a_pf_eri_policy_candidate_grid.csv",
    "top": OUTPUT_DIR / "phase7a_pf_eri_policy_top_candidates.csv",
    "assignment": OUTPUT_DIR / "phase7a_pf_eri_policy_assignment_top.csv",
    "regime": OUTPUT_DIR / "phase7a_pf_eri_policy_regime_summary.csv",
    "failure": OUTPUT_DIR / "phase7a_pf_eri_policy_failure_mode_summary.csv",
    "decision": OUTPUT_DIR / "phase7a_pf_eri_policy_confidence_decision.csv",
}

REQUIRED_FIGURES = [
    "phase7a_policy_risk_coverage_frontier.png",
    "phase7a_top_policy_false_support_ci.png",
    "phase7a_top_policy_coverage_ci.png",
    "phase7a_policy_family_median_comparison.png",
    "phase7a_regime_pass_counts.png",
    "phase7a_failure_mode_review_exposure.png",
    "phase7a_policy_ranking_score_distribution.png",
    "phase7a_descriptor_support_context.png",
    "phase7a_risk_load_relative_to_pool.png",
]

REQUIRED_FAMILIES = {
    "A_descriptor_only_baseline",
    "B_visual_gate_megadescriptor",
    "C_visual_gate_megadescriptor_failure_defer",
    "D_dual_descriptor_agreement_caution",
    "E_conservative_high_confidence_policy",
    "F_balanced_review_policy",
}

ASSIGNMENTS = {"review_candidate", "defer_candidate", "exclude_candidate"}

FORBIDDEN_HEADER_PARTS = [
    "unique_name",
    "latitude",
    "longitude",
    "trap_id",
    "cell_code",
    "raw_path",
    "review_image_path",
    "working_individual_id",
    "true_id",
    "image_id",
    "expanded_image_id",
    "source_image_id",
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
]

OVERCLAIM_PATTERNS = [
    re.compile(r"field deployment", re.IGNORECASE),
    re.compile(r"deployment readiness", re.IGNORECASE),
    re.compile(r"clouded leopard validation", re.IGNORECASE),
    re.compile(r"safety[_ -]?score", re.IGNORECASE),
    re.compile(r"universal animal", re.IGNORECASE),
    re.compile(r"general animal re-id validation", re.IGNORECASE),
    re.compile(r"population estimation", re.IGNORECASE),
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


def is_number(value) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def scan_frame(name: str, path: Path, df: pd.DataFrame, report: list[dict[str, str]]) -> tuple[int, int]:
    leakage = 0
    overclaim = 0
    for column in df.columns:
        column_lower = column.lower()
        if column != "same_identity_validation_label" and any(part in column_lower for part in FORBIDDEN_HEADER_PARTS):
            leakage += 1
            add_issue(report, "ERROR", "sensitive_header", "sensitive row-level or location header found", str(path), field=column)
        for pattern in OVERCLAIM_PATTERNS:
            if pattern.search(column):
                overclaim += 1
                add_issue(report, "ERROR", "overclaim_header", "forbidden overclaim wording in header", str(path), field=column)
    for idx, row in df.astype(str).iterrows():
        row_id = row.get("policy_id", row.get("decision_area", str(idx)))
        for column, value in row.items():
            for pattern in FORBIDDEN_VALUE_PATTERNS:
                if pattern.search(value):
                    leakage += 1
                    add_issue(report, "ERROR", "sensitive_value", "sensitive value pattern found", str(path), row_id, column, value[:140])
            for pattern in OVERCLAIM_PATTERNS:
                if pattern.search(value):
                    overclaim += 1
                    add_issue(report, "ERROR", "overclaim_value", "forbidden overclaim wording found", str(path), row_id, column, value[:140])
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
    assignment = loaded["assignment"]
    regime = loaded["regime"]
    failure = loaded["failure"]
    decision = loaded["decision"]

    if len(grid) < args.min_candidate_policies:
        add_issue(report, "ERROR", "candidate_grid_too_small", f"candidate policy grid too small: {len(grid)}")
    missing_families = REQUIRED_FAMILIES - set(grid.get("policy_family", []))
    if missing_families:
        add_issue(report, "ERROR", "missing_policy_family", "missing policy families: " + ", ".join(sorted(missing_families)))
    if top.empty:
        add_issue(report, "ERROR", "empty_top_candidates", "top candidate file is empty")
    if len(top) < 8:
        add_issue(report, "ERROR", "too_few_bootstrapped_top_candidates", f"only {len(top)} top policies were bootstrapped")

    observed_assignments = set(assignment.get("assignment", []))
    invalid_assignments = observed_assignments - ASSIGNMENTS
    if invalid_assignments:
        add_issue(report, "ERROR", "invalid_assignment_categories", "invalid assignment values: " + ", ".join(sorted(invalid_assignments)))
    if not {"review_candidate", "defer_candidate"}.issubset(observed_assignments):
        add_issue(report, "ERROR", "missing_core_assignment_categories", "assignment output must include review and defer decisions")
    if "exclude_candidate" not in observed_assignments:
        add_issue(report, "WARN", "no_exclude_in_recommended_policy", "recommended policy did not assign any pair to exclude; exclusion remains represented in candidate-grid alternatives")
    if len(assignment) == 0:
        add_issue(report, "ERROR", "empty_assignment_output", "assignment output is empty")
    if assignment["pair_id"].duplicated().any():
        add_issue(report, "ERROR", "duplicate_assignment_pair_id", "assignment output has duplicate pair IDs")

    if "candidate_pair_count" in grid.columns and int(grid["candidate_pair_count"].max()) != len(assignment):
        add_issue(report, "ERROR", "assignment_count_mismatch", "assignment row count does not match candidate pair count")

    required_top_ci = [
        "review_coverage_ci_lower",
        "review_coverage_ci_upper",
        "review_false_support_rate_ci_lower",
        "review_false_support_rate_ci_upper",
        "bootstrap_n",
        "cluster_unit",
    ]
    for col in required_top_ci:
        if col not in top.columns:
            add_issue(report, "ERROR", "missing_top_ci_column", f"missing top candidate CI column: {col}")
    if set(["bootstrap_n", "cluster_unit"]).issubset(top.columns):
        if top["bootstrap_n"].isna().any() or top["cluster_unit"].astype(str).str.strip().eq("").any():
            add_issue(report, "ERROR", "missing_bootstrap_metadata", "top candidates missing bootstrap metadata")
        if top["bootstrap_n"].min() < args.min_bootstrap_n:
            add_issue(report, "ERROR", "bootstrap_too_low", f"bootstrap_n below minimum {args.min_bootstrap_n}")

    invalid_ci = 0
    for _, row in top.iterrows():
        for metric in ["review_coverage", "review_false_support_rate", "review_same_proportion", "same_accept_rate"]:
            lower = row.get(f"{metric}_ci_lower")
            upper = row.get(f"{metric}_ci_upper")
            estimate = row.get(metric)
            if is_number(lower) and is_number(upper):
                if float(lower) > float(upper):
                    invalid_ci += 1
                    add_issue(report, "ERROR", "invalid_ci_order", "CI lower exceeds upper", FILES["top"].as_posix(), row.get("policy_id", ""), metric)
                if is_number(estimate) and not (float(lower) - 1e-9 <= float(estimate) <= float(upper) + 1e-9):
                    invalid_ci += 1
                    add_issue(report, "ERROR", "estimate_outside_ci", "estimate outside CI", FILES["top"].as_posix(), row.get("policy_id", ""), metric)

    expected_regimes = {"strict", "moderate", "balanced", "exploratory"}
    if set(regime.get("regime", [])) != expected_regimes:
        add_issue(report, "ERROR", "invalid_regime_rows", "regime summary must contain strict, moderate, balanced, exploratory")
    if failure.empty:
        add_issue(report, "ERROR", "empty_failure_summary", "failure-mode summary is empty")
    if decision.empty:
        add_issue(report, "ERROR", "empty_confidence_decision", "confidence decision output is empty")
    else:
        allowed_label_use = set(decision.get("same_different_label_use", []))
        if allowed_label_use != {"validation_metrics_only_not_policy_inputs"}:
            add_issue(report, "ERROR", "label_use_boundary_missing", "decision must state labels were validation-only")

    missing_figures = 0
    for figure in REQUIRED_FIGURES:
        figure_path = args.figure_dir / figure
        if not figure_path.exists() or figure_path.stat().st_size == 0:
            missing_figures += 1
            add_issue(report, "ERROR", "missing_figure", f"missing or empty figure: {figure}", str(figure_path))

    leakage = 0
    overclaim = 0
    for name, path in FILES.items():
        leak_count, over_count = scan_frame(name, path, loaded[name], report)
        leakage += leak_count
        overclaim += over_count

    error_count = sum(1 for issue in report if issue["severity"] == "ERROR")
    warning_count = sum(1 for issue in report if issue["severity"] == "WARN")
    status = "PASS" if error_count == 0 else "FAIL"
    summary_lines = [
        status,
        f"candidate_policy_count: {len(grid)}",
        f"top_policy_count: {len(top)}",
        f"assignment_row_count: {len(assignment)}",
        f"invalid_ci_count: {invalid_ci}",
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
    parser.add_argument("--min-candidate-policies", type=int, default=10000)
    parser.add_argument("--min-bootstrap-n", type=int, default=300)
    return parser.parse_args()


def main() -> int:
    return audit(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
