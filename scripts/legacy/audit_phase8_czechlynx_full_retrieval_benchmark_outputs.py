#!/usr/bin/env python3
"""Audit Phase 8 full CzechLynx retrieval benchmark outputs."""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase8/full_retrieval_benchmark"
FIGURE_DIR = OUTPUT_DIR / "figures"
SUMMARY_TXT = PROJECT_ROOT / "outputs/czechlynx/qc/phase8_czechlynx_full_retrieval_benchmark_audit_summary.txt"
REPORT_CSV = PROJECT_ROOT / "outputs/czechlynx/qc/phase8_czechlynx_full_retrieval_benchmark_audit_report.csv"

FILES = {
    "metrics": OUTPUT_DIR / "phase8_czechlynx_full_retrieval_metrics_summary.csv",
    "cmc": OUTPUT_DIR / "phase8_czechlynx_full_retrieval_cmc_table.csv",
    "topk": OUTPUT_DIR / "phase8_czechlynx_full_retrieval_topk_table.csv",
    "map": OUTPUT_DIR / "phase8_czechlynx_full_retrieval_map_summary.csv",
    "comparison": OUTPUT_DIR / "phase8_czechlynx_full_retrieval_pf_eri_filter_comparison.csv",
    "failures": OUTPUT_DIR / "phase8_czechlynx_full_retrieval_failure_cases.csv",
    "failure_summary": OUTPUT_DIR / "phase8_czechlynx_full_retrieval_failure_mode_summary.csv",
    "feasibility": OUTPUT_DIR / "phase8_czechlynx_full_retrieval_feasibility_report.csv",
    "rank_distribution": OUTPUT_DIR / "phase8_czechlynx_full_retrieval_same_identity_rank_distribution.csv",
}

REQUIRED_FIGURES = [
    "phase8_full_retrieval_cmc_curves.png",
    "phase8_full_retrieval_map_comparison.png",
    "phase8_full_retrieval_top1_comparison.png",
    "phase8_full_retrieval_false_top1_comparison.png",
    "phase8_full_retrieval_query_coverage_vs_map.png",
    "phase8_full_retrieval_pf_eri_filter_tradeoff.png",
    "phase8_full_retrieval_topk_comparison.png",
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
    re.compile(r"field deployment", re.IGNORECASE),
    re.compile(r"deployment readiness", re.IGNORECASE),
    re.compile(r"clouded leopard validation", re.IGNORECASE),
    re.compile(r"broader felid validation", re.IGNORECASE),
    re.compile(r"universal felid", re.IGNORECASE),
    re.compile(r"universal animal", re.IGNORECASE),
    re.compile(r"population estimation", re.IGNORECASE),
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
        column_lower = column.lower()
        if any(part in column_lower for part in FORBIDDEN_HEADER_PARTS):
            leakage += 1
            add_issue(report, "ERROR", "sensitive_header", "sensitive header found", str(path), field=column)
        for pattern in OVERCLAIM_PATTERNS:
            if pattern.search(column):
                overclaim += 1
                add_issue(report, "ERROR", "overclaim_header", "forbidden overclaim wording in header", str(path), field=column)
    for idx, row in df.astype(str).iterrows():
        row_id = row.get("descriptor", row.get("item", str(idx)))
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

    metrics = loaded["metrics"]
    cmc = loaded["cmc"]
    topk = loaded["topk"]
    feasibility = loaded["feasibility"]
    ranks = loaded["rank_distribution"]

    if metrics.empty:
        add_issue(report, "ERROR", "empty_metrics", "metrics output is empty")
    if set(metrics["descriptor"]) != {"megadescriptor", "resnet50"}:
        add_issue(report, "ERROR", "missing_descriptors", "metrics must include MegaDescriptor and ResNet50")
    if metrics["query_count"].max() <= 0:
        add_issue(report, "ERROR", "invalid_query_count", "query count must be positive")
    if metrics["gallery_count"].max() <= 0:
        add_issue(report, "ERROR", "invalid_gallery_count", "gallery count must be positive")
    rate_cols = [
        "query_coverage",
        "positive_query_coverage",
        "mAP",
        "mean_reciprocal_rank",
        "false_top1_rate",
        "top1_accuracy",
        "top3_accuracy",
        "top5_accuracy",
        "top10_accuracy",
    ]
    for col in rate_cols:
        if col in metrics.columns and not metrics[col].map(valid_rate).all():
            add_issue(report, "ERROR", "invalid_rate", f"invalid rate values in {col}")
    if "self_matches_excluded" not in metrics.columns or set(metrics["self_matches_excluded"]) != {"yes"}:
        add_issue(report, "ERROR", "self_match_exclusion_missing", "metrics must state self-matches were excluded")
    if not cmc["cmc"].map(valid_rate).all():
        add_issue(report, "ERROR", "invalid_cmc", "CMC values must be valid rates")
    if not topk["topk_accuracy"].map(valid_rate).all():
        add_issue(report, "ERROR", "invalid_topk", "top-k values must be valid rates")
    if not ranks.empty and (ranks["first_same_identity_rank"] <= 0).any():
        add_issue(report, "ERROR", "invalid_rank_distribution", "same-identity ranks must be positive")
    if feasibility.empty or set(feasibility["status"]) != {"feasible"}:
        add_issue(report, "ERROR", "invalid_feasibility_status", "feasibility report must state feasible")
    if "identity_label_use" not in feasibility.columns or set(feasibility["identity_label_use"]) != {"evaluation_only_not_retrieval_scoring"}:
        add_issue(report, "ERROR", "label_use_boundary_missing", "feasibility must state identity labels are evaluation-only")

    missing_figures = 0
    for figure in REQUIRED_FIGURES:
        path = args.figure_dir / figure
        if not path.exists() or path.stat().st_size == 0:
            missing_figures += 1
            add_issue(report, "ERROR", "missing_figure", f"missing or empty figure: {figure}", str(path))

    leakage = 0
    overclaim = 0
    for name, path in FILES.items():
        leak_count, over_count = scan_frame(path, loaded[name], report)
        leakage += leak_count
        overclaim += over_count

    error_count = sum(1 for issue in report if issue["severity"] == "ERROR")
    warning_count = sum(1 for issue in report if issue["severity"] == "WARN")
    status = "PASS" if error_count == 0 else "FAIL"
    summary_lines = [
        status,
        f"metrics_row_count: {len(metrics)}",
        f"cmc_row_count: {len(cmc)}",
        f"topk_row_count: {len(topk)}",
        f"rank_distribution_row_count: {len(ranks)}",
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
