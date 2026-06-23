#!/usr/bin/env python3
"""Audit Phase 8 Slice 3C utility-constrained policy selection outputs."""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase8/utility_constrained_policy_selection"
FIGURE_DIR = OUTPUT_DIR / "figures"
SUMMARY_TXT = PROJECT_ROOT / "outputs/czechlynx/qc/phase8_utility_policy_selection_audit_summary.txt"
REPORT_CSV = PROJECT_ROOT / "outputs/czechlynx/qc/phase8_utility_policy_selection_audit_report.csv"

FILES = {
    "candidate_comparison": OUTPUT_DIR / "phase8_utility_policy_candidate_comparison.csv",
    "component_scores": OUTPUT_DIR / "phase8_utility_policy_component_scores.csv",
    "regime_winners": OUTPUT_DIR / "phase8_utility_policy_regime_winners.csv",
    "paired_bootstrap": OUTPUT_DIR / "phase8_utility_policy_paired_bootstrap_differences.csv",
    "bootstrap": OUTPUT_DIR / "phase8_utility_policy_bootstrap_intervals.csv",
    "recommended_assignment": OUTPUT_DIR / "phase8_utility_policy_recommended_assignment.csv",
    "final_decision": OUTPUT_DIR / "phase8_utility_policy_final_decision.csv",
}

REQUIRED_FIGURES = [
    "phase8_utility_candidate_component_comparison.png",
    "phase8_utility_v2_vs_v3_paired_bootstrap_differences.png",
    "phase8_utility_false_top1_vs_query_coverage.png",
    "phase8_utility_positive_retention_vs_false_review_burden.png",
    "phase8_utility_disagreement_exposure_vs_review_burden.png",
    "phase8_utility_final_candidate_confidence_intervals.png",
    "phase8_utility_regime_winners_summary.png",
]

REQUIRED_REGIMES = {
    "operational_primary",
    "confidence_first",
    "coverage_first",
    "evidence_control",
    "external_testing_readiness",
}

VALID_ASSIGNMENTS = {"review_candidate", "defer_candidate", "exclude_candidate"}
REPORT_FIELDS = ["severity", "issue_type", "file", "row_id", "field", "value", "message"]

RATE_COLUMNS = [
    "query_coverage",
    "positive_retention",
    "mAP_among_covered_positives",
    "false_top1_rate",
    "review_burden_reduction",
    "disagreement_exposure_review",
    "severe_failure_exposure_review",
    "high_descriptor_low_evidence_exposure_review",
    "caution_flag_review_exposure",
    "true_same_candidate_retention",
    "false_reviewed_candidate_rate",
    "reliability_utility",
    "coverage_utility",
    "review_burden_utility",
    "evidence_control_utility",
    "operational_utility",
    "visible_utility_score",
    "regime_score",
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
        row_id = row.get("candidate_id", row.get("decision_item", str(idx)))
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

    if "candidate_comparison" in loaded:
        comparison = loaded["candidate_comparison"]
        if comparison.empty:
            add_issue(report, "ERROR", "empty_candidate_comparison", "candidate comparison is empty")
        if len(comparison) < 6:
            add_issue(report, "ERROR", "too_few_candidates", "expected at least six candidate policies")
        required = {
            "A_v2_primary_baseline",
            "B_reliability_first_v3",
            "C_balanced_v3",
            "D_coverage_preserving_v3",
            "E_evidence_control_v3",
            "F_v2_with_disagreement_caution",
        }
        missing = sorted(required - set(comparison.get("candidate_id", [])))
        if missing:
            add_issue(report, "ERROR", "missing_candidate", f"missing candidates: {', '.join(missing)}")

    if "component_scores" in loaded:
        components = loaded["component_scores"]
        if components.empty:
            add_issue(report, "ERROR", "empty_component_scores", "component scores are empty")
        required_cols = {"reliability_utility", "coverage_utility", "review_burden_utility", "evidence_control_utility", "operational_utility", "visible_utility_score"}
        missing_cols = sorted(required_cols - set(components.columns))
        if missing_cols:
            add_issue(report, "ERROR", "missing_component_column", f"missing component columns: {', '.join(missing_cols)}")

    if "regime_winners" in loaded:
        winners = loaded["regime_winners"]
        if winners.empty:
            add_issue(report, "ERROR", "empty_regime_winners", "regime winners are empty")
        missing_regimes = sorted(REQUIRED_REGIMES - set(winners.get("decision_regime", [])))
        if missing_regimes:
            add_issue(report, "ERROR", "missing_regime", f"missing decision regimes: {', '.join(missing_regimes)}")

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
            add_issue(report, "ERROR", "invalid_paired_bootstrap_interval", "paired intervals must contain estimates")

    if "recommended_assignment" in loaded:
        assignment = loaded["recommended_assignment"]
        if assignment.empty:
            add_issue(report, "ERROR", "empty_recommended_assignment", "recommended assignment is empty")
        elif not set(assignment["recommended_assignment"]).issubset(VALID_ASSIGNMENTS):
            add_issue(report, "ERROR", "invalid_assignment", "invalid recommended assignment labels")

    if "final_decision" in loaded:
        final = loaded["final_decision"]
        required_items = {
            "final_carry_forward_policy",
            "v2_remains_primary",
            "v3_replaces_v2",
            "v3_becomes_confidence_variant",
            "descriptor_disagreement_added_as_caution_layer",
            "external_access_audit_can_proceed",
            "broader_felid_validation_supported",
            "mainland_clouded_leopard_marbled_cat_status",
        }
        missing_items = sorted(required_items - set(final.get("decision_item", [])))
        if missing_items:
            add_issue(report, "ERROR", "missing_decision_item", f"missing decision rows: {', '.join(missing_items)}")
        bad = final[(final["decision_item"] == "v3_replaces_v2") & (final["decision"].astype(str).str.lower() != "no")]
        if not bad.empty:
            add_issue(report, "ERROR", "bad_v3_replacement_decision", "v3 should not replace v2 in Slice 3C")

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
        f"candidate_comparison_row_count: {len(loaded.get('candidate_comparison', []))}",
        f"component_score_row_count: {len(loaded.get('component_scores', []))}",
        f"regime_winner_row_count: {len(loaded.get('regime_winners', []))}",
        f"bootstrap_row_count: {len(loaded.get('bootstrap', []))}",
        f"paired_bootstrap_row_count: {len(loaded.get('paired_bootstrap', []))}",
        f"recommended_assignment_row_count: {len(loaded.get('recommended_assignment', []))}",
        f"final_decision_row_count: {len(loaded.get('final_decision', []))}",
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
