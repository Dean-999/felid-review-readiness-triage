#!/usr/bin/env python3
"""Audit Phase 8 Slice 3E-R query-level calibration/evaluation outputs."""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase8/reid_accuracy_query_calibration"
SUMMARY_TXT = PROJECT_ROOT / "outputs/czechlynx/qc/phase8_slice3e_query_calibration_audit_summary.txt"
REPORT_CSV = PROJECT_ROOT / "outputs/czechlynx/qc/phase8_slice3e_query_calibration_audit_report.csv"
RESULTS_DOC = PROJECT_ROOT / "docs/phase8/phase8_slice3e_query_level_calibration_evaluation_results.md"

FILES = {
    "inventory": OUTPUT_DIR / "phase8_slice3e_query_split_inventory.csv",
    "split_design": OUTPUT_DIR / "phase8_slice3e_query_split_design.csv",
    "selection": OUTPUT_DIR / "phase8_slice3e_query_calibration_policy_selection.csv",
    "evaluation": OUTPUT_DIR / "phase8_slice3e_query_evaluation_policy_comparison.csv",
    "random_summary": OUTPUT_DIR / "phase8_slice3e_query_random_same_size_baseline_summary.csv",
    "random_raw": OUTPUT_DIR / "phase8_slice3e_query_random_same_size_baseline_raw.csv",
    "risk": OUTPUT_DIR / "phase8_slice3e_query_risk_coverage_curve.csv",
    "pareto": OUTPUT_DIR / "phase8_slice3e_query_pareto_frontier.csv",
    "uncertainty": OUTPUT_DIR / "phase8_slice3e_query_bootstrap_ci_summary.csv",
    "final": OUTPUT_DIR / "phase8_slice3e_query_final_recommendation.csv",
}

REQUIRED_POLICIES = {
    "megadescriptor_pf_eri_medium_or_higher_without_severe_failures",
    "candidate_f",
    "v4_0636",
    "utility_workload_constrained",
    "utility_balanced",
    "raw_megadescriptor",
}

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
    "local_image_path",
    "path",
]

FORBIDDEN_VALUE_PATTERNS = [
    re.compile(r"/Users/", re.IGNORECASE),
    re.compile(r"data/raw", re.IGNORECASE),
    re.compile(r"(?<![A-Za-z])lynx_[0-9]+", re.IGNORECASE),
    re.compile(r"czlx_expanded_[0-9]+", re.IGNORECASE),
    re.compile(r"\blatitude\b", re.IGNORECASE),
    re.compile(r"\blongitude\b", re.IGNORECASE),
    re.compile(r"\btrap_id\b", re.IGNORECASE),
    re.compile(r"\bcell_code\b", re.IGNORECASE),
]

OVERCLAIM_PATTERNS = [
    re.compile(r"field deployment", re.IGNORECASE),
    re.compile(r"deployment readiness", re.IGNORECASE),
    re.compile(r"validated across felids", re.IGNORECASE),
    re.compile(r"general animal re-id validation", re.IGNORECASE),
    re.compile(r"clouded leopard validation", re.IGNORECASE),
    re.compile(r"marbled cat validation", re.IGNORECASE),
    re.compile(r"population estimation", re.IGNORECASE),
    re.compile(r"new re-id model", re.IGNORECASE),
    re.compile(r"identifies true individual", re.IGNORECASE),
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


def valid_rate_or_nan(value: object) -> bool:
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
        if any(part == lower or lower.endswith("_" + part) or lower.startswith(part + "_") for part in FORBIDDEN_HEADER_PARTS):
            if path.name not in {"phase8_slice3e_query_split_inventory.csv"}:
                leakage += 1
                add_issue(report, "ERROR", "sensitive_header", "sensitive header found", str(path), field=column)
        for pattern in OVERCLAIM_PATTERNS:
            if pattern.search(column):
                overclaim += 1
                add_issue(report, "ERROR", "overclaim_header", "forbidden overclaim wording in header", str(path), field=column)
    for idx, row in df.astype(str).iterrows():
        row_id = row.get("policy_id", row.get("decision_item", str(idx)))
        for column, value in row.items():
            if path.name == "phase8_slice3e_query_split_inventory.csv" and column in {"input_file", "columns"}:
                continue
            for pattern in FORBIDDEN_VALUE_PATTERNS:
                if pattern.search(value):
                    leakage += 1
                    add_issue(report, "ERROR", "sensitive_value", "sensitive value pattern found", str(path), row_id, column, value[:160])
            for pattern in OVERCLAIM_PATTERNS:
                if pattern.search(value) and not ("not supported" in value.lower() or "not a" in value.lower() or "no " in value.lower() or "forbidden" in value.lower()):
                    overclaim += 1
                    add_issue(report, "ERROR", "overclaim_value", "forbidden overclaim wording found", str(path), row_id, column, value[:160])
    return leakage, overclaim


def audit(args: argparse.Namespace) -> int:
    report: list[dict[str, str]] = []
    loaded: dict[str, pd.DataFrame] = {}
    for name, path in FILES.items():
        if not path.exists():
            add_issue(report, "ERROR", "missing_output", f"missing output file: {path}", str(path))
        else:
            loaded[name] = pd.read_csv(path)
    if not RESULTS_DOC.exists():
        add_issue(report, "ERROR", "missing_results_doc", "missing results doc", str(RESULTS_DOC))
    if report:
        args.summary_txt.parent.mkdir(parents=True, exist_ok=True)
        args.summary_txt.write_text("FAIL\nmissing required outputs\n", encoding="utf-8")
        pd.DataFrame(report, columns=REPORT_FIELDS).to_csv(args.report_csv, index=False)
        print("FAIL: missing required outputs")
        return 1

    split_design = loaded["split_design"]
    selection = loaded["selection"]
    evaluation = loaded["evaluation"]
    random_raw = loaded["random_raw"]
    random_summary = loaded["random_summary"]
    pareto = loaded["pareto"]
    final = loaded["final"]

    split_count = int(split_design["split_id"].nunique()) if "split_id" in split_design.columns else 0
    if split_count < args.min_splits:
        add_issue(report, "ERROR", "too_few_splits", f"split count {split_count} below minimum {args.min_splits}")
    if "split_design" not in split_design.columns or not split_design["split_design"].astype(str).str.contains("query", case=False).all():
        add_issue(report, "ERROR", "split_not_query_level", "split design must be query-level")
    if "evaluation_identity_count" in split_design.columns and (split_design["evaluation_identity_count"] <= 0).any():
        add_issue(report, "ERROR", "empty_evaluation_identity_split", "evaluation identity count must be positive")

    missing_policies = sorted(REQUIRED_POLICIES - set(selection.get("policy_id", pd.Series(dtype=str))))
    for policy_id in missing_policies:
        add_issue(report, "ERROR", "missing_policy_candidate", f"missing policy candidate: {policy_id}")
    selected = evaluation[evaluation.get("selected_for_evaluation", pd.Series(dtype=str)) == "yes"]
    if selected.empty:
        add_issue(report, "ERROR", "no_selected_evaluation_policy", "no selected held-out policy rows")
    if selected["split_id"].nunique() != split_count:
        add_issue(report, "ERROR", "selected_policy_not_per_split", "must have one selected evaluation policy per split")

    if "random_repeat" not in random_raw.columns:
        add_issue(report, "ERROR", "missing_random_repeat_column", "random raw output lacks random_repeat")
        repeat_min = 0
    else:
        repeat_counts = random_raw.groupby(["split_id", "target_policy_id"])["random_repeat"].nunique()
        repeat_min = int(repeat_counts.min()) if len(repeat_counts) else 0
        if repeat_min < args.min_random_repeats:
            add_issue(report, "ERROR", "too_few_random_repeats", f"minimum repeat count {repeat_min} below {args.min_random_repeats}")
    for col in ["top1_accuracy", "top3_accuracy", "top5_accuracy", "mAP", "MRR", "false_top1_rate", "query_coverage", "positive_retention", "candidate_retention"]:
        if col in evaluation.columns and not evaluation[col].map(valid_rate_or_nan).all():
            add_issue(report, "ERROR", "invalid_rate", f"invalid rate values in {col}", str(FILES["evaluation"]), field=col)
    if "pareto_efficient" not in pareto.columns or not set(pareto["pareto_efficient"]).issubset({"yes", "no"}):
        add_issue(report, "ERROR", "invalid_pareto", "pareto output must include yes/no pareto_efficient")
    if "slice3e_r_held_out_reid_accuracy_claim" not in set(final.get("decision_item", pd.Series(dtype=str))):
        add_issue(report, "ERROR", "missing_final_decision", "final recommendation lacks held-out decision")

    leakage = 0
    overclaim = 0
    for name, path in FILES.items():
        leak_count, over_count = scan_frame(path, loaded[name], report)
        leakage += leak_count
        overclaim += over_count

    doc_text = RESULTS_DOC.read_text(encoding="utf-8")
    for phrase in ["No training", "No external data", "No frozen-data edit", "random same-size", "not a Re-ID model", "population estimation"]:
        if phrase.lower() not in doc_text.lower():
            add_issue(report, "ERROR", "missing_doc_boundary", f"results doc missing phrase: {phrase}", str(RESULTS_DOC))
    for pattern in FORBIDDEN_VALUE_PATTERNS:
        if pattern.search(doc_text):
            leakage += 1
            add_issue(report, "ERROR", "sensitive_doc_value", "sensitive value pattern found in results doc", str(RESULTS_DOC), value=pattern.pattern)

    error_count = sum(1 for issue in report if issue["severity"] == "ERROR")
    warning_count = sum(1 for issue in report if issue["severity"] == "WARN")
    status = "PASS" if error_count == 0 else "FAIL"
    summary_lines = [
        status,
        f"query_split_count: {split_count}",
        f"selection_row_count: {len(selection)}",
        f"evaluation_row_count: {len(evaluation)}",
        f"selected_evaluation_row_count: {len(selected)}",
        f"random_summary_row_count: {len(random_summary)}",
        f"random_raw_row_count: {len(random_raw)}",
        f"minimum_random_repeat_count: {repeat_min}",
        f"pareto_row_count: {len(pareto)}",
        f"leakage_issue_count: {leakage}",
        f"overclaim_issue_count: {overclaim}",
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
    parser.add_argument("--summary-txt", type=Path, default=SUMMARY_TXT)
    parser.add_argument("--report-csv", type=Path, default=REPORT_CSV)
    parser.add_argument("--min-splits", type=int, default=10)
    parser.add_argument("--min-random-repeats", type=int, default=100)
    return parser.parse_args()


def main() -> int:
    return audit(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
