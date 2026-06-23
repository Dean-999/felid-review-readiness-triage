#!/usr/bin/env python3
"""Audit Phase 8 Slice 2B failure diagnosis and PF-ERI control outputs."""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase8/full_retrieval_failure_diagnosis"
FIGURE_DIR = OUTPUT_DIR / "figures"
SUMMARY_TXT = PROJECT_ROOT / "outputs/czechlynx/qc/phase8_full_retrieval_failure_diagnosis_audit_summary.txt"
REPORT_CSV = PROJECT_ROOT / "outputs/czechlynx/qc/phase8_full_retrieval_failure_diagnosis_audit_report.csv"

FILES = {
    "query_failure": OUTPUT_DIR / "phase8_full_retrieval_query_failure_table.csv",
    "false_top1": OUTPUT_DIR / "phase8_full_retrieval_false_top1_diagnosis.csv",
    "topk_burden": OUTPUT_DIR / "phase8_full_retrieval_topk_false_burden.csv",
    "control": OUTPUT_DIR / "phase8_pf_eri_control_mode_comparison.csv",
    "rules": OUTPUT_DIR / "phase8_pf_eri_retrieval_control_candidate_rules.csv",
    "assignments": OUTPUT_DIR / "phase8_pf_eri_retrieval_control_recommended_assignment.csv",
    "readiness": OUTPUT_DIR / "phase8_pf_eri_retrieval_control_readiness_decision.csv",
}

REQUIRED_FIGURES = [
    "phase8_false_top1_rate_by_query_visual_band.png",
    "phase8_false_top1_rate_by_gallery_visual_band.png",
    "phase8_first_same_identity_rank_distribution_by_pf_eri_band.png",
    "phase8_topk_false_burden_by_descriptor.png",
    "phase8_pf_eri_control_mode_comparison.png",
    "phase8_coverage_vs_false_top1_tradeoff.png",
    "phase8_query_visual_score_vs_first_same_identity_rank.png",
]

VALID_ASSIGNMENTS = {"review_candidate", "defer_candidate", "exclude_candidate"}
RATE_COLUMNS = [
    "false_top1_rate",
    "false_top1_share_among_false",
    "false_top1_rate_within_group",
    "false_candidate_proportion",
    "topk_success_rate",
    "query_coverage",
    "candidate_coverage",
    "positive_query_coverage",
    "top1_accuracy_among_covered_positive_queries",
    "top5_success_among_covered_positive_queries",
    "mAP_among_covered_positive_queries",
    "review_burden_reduction",
    "positive_retention",
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
    "true_id",
    "identity_token",
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
        row_id = row.get("descriptor", row.get("decision_item", str(idx)))
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

    if "query_failure" in loaded and loaded["query_failure"].empty:
        add_issue(report, "ERROR", "empty_query_failure_table", "query/failure table is empty")
    if "false_top1" in loaded and loaded["false_top1"].empty:
        add_issue(report, "ERROR", "empty_false_top1_table", "false top-1 diagnosis is empty")
    if "control" in loaded and loaded["control"].empty:
        add_issue(report, "ERROR", "empty_control_mode_comparison", "control mode comparison is empty")
    if "assignments" in loaded:
        assignments = loaded["assignments"]
        if assignments.empty:
            add_issue(report, "ERROR", "empty_assignment_table", "recommended assignment table is empty")
        elif not set(assignments["recommended_assignment"]).issubset(VALID_ASSIGNMENTS):
            add_issue(report, "ERROR", "invalid_assignment_label", "recommended assignments must be review/defer/exclude candidate")
    if "control" in loaded:
        control = loaded["control"]
        expected_modes = {
            "no_pf_eri_control",
            "query_only_filter",
            "gallery_only_filter",
            "query_and_gallery_filter",
            "pair_level_topk_review_pruning",
            "descriptor_pf_eri_reranking_diagnostic",
        }
        missing_modes = sorted(expected_modes - set(control["control_mode"]))
        if missing_modes:
            add_issue(report, "ERROR", "missing_control_modes", f"missing control modes: {', '.join(missing_modes)}")
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
        f"query_failure_row_count: {len(loaded.get('query_failure', []))}",
        f"false_top1_summary_row_count: {len(loaded.get('false_top1', []))}",
        f"topk_burden_row_count: {len(loaded.get('topk_burden', []))}",
        f"control_mode_row_count: {len(loaded.get('control', []))}",
        f"assignment_row_count: {len(loaded.get('assignments', []))}",
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
