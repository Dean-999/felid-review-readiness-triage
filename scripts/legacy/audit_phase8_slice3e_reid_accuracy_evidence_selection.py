#!/usr/bin/env python3
"""Audit Phase 8 Slice 3E evidence-selection outputs."""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase8/reid_accuracy_evidence_selection"
FIGURE_DIR = OUTPUT_DIR / "figures"
SUMMARY_TXT = PROJECT_ROOT / "outputs/czechlynx/qc/phase8_slice3e_reid_accuracy_evidence_selection_audit_summary.txt"
REPORT_CSV = PROJECT_ROOT / "outputs/czechlynx/qc/phase8_slice3e_reid_accuracy_evidence_selection_audit_report.csv"
RESULTS_DOC = PROJECT_ROOT / "docs/phase8/phase8_slice3e_reid_accuracy_evidence_selection_results.md"

FILES = {
    "input_inventory": OUTPUT_DIR / "phase8_slice3e_input_inventory.csv",
    "policy_comparison": OUTPUT_DIR / "phase8_slice3e_policy_comparison.csv",
    "random_summary": OUTPUT_DIR / "phase8_slice3e_random_same_size_baseline_summary.csv",
    "random_raw": OUTPUT_DIR / "phase8_slice3e_random_same_size_baseline_raw.csv",
    "risk_coverage": OUTPUT_DIR / "phase8_slice3e_risk_coverage_curve.csv",
    "pareto": OUTPUT_DIR / "phase8_slice3e_pareto_frontier.csv",
    "calibration": OUTPUT_DIR / "phase8_slice3e_calibration_evaluation_summary.csv",
    "bootstrap": OUTPUT_DIR / "phase8_slice3e_bootstrap_ci_summary.csv",
    "final": OUTPUT_DIR / "phase8_slice3e_final_recommendation.csv",
}

REQUIRED_FIGURES = [
    "phase8_slice3e_risk_coverage.png",
    "phase8_slice3e_random_baseline_differences.png",
    "phase8_slice3e_pareto_context.png",
]

REQUIRED_POLICY_COLUMNS = [
    "policy_id",
    "policy_family",
    "selection_unit",
    "descriptor",
    "top1_accuracy",
    "top3_accuracy",
    "top5_accuracy",
    "mAP",
    "MRR",
    "false_top1_rate",
    "false_reviewed_candidates_per_query",
    "query_coverage",
    "positive_retention",
    "random_baseline_required",
]

REQUIRED_POLICIES = [
    "megadescriptor_all_images",
    "resnet50_all_images",
    "megadescriptor_pf_eri_high_only",
    "megadescriptor_pf_eri_medium_or_higher",
    "candidate_f",
    "v4_0636",
    "utility_balanced",
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
            leakage += 1
            add_issue(report, "ERROR", "sensitive_header", "sensitive header found", str(path), field=column)
        for pattern in OVERCLAIM_PATTERNS:
            if pattern.search(column):
                overclaim += 1
                add_issue(report, "ERROR", "overclaim_header", "forbidden overclaim wording in header", str(path), field=column)
    for idx, row in df.astype(str).iterrows():
        row_id = row.get("policy_id", row.get("decision_item", str(idx)))
        for column, value in row.items():
            if path.name == "phase8_slice3e_input_inventory.csv" and column in {"input_file", "columns"}:
                continue
            for pattern in FORBIDDEN_VALUE_PATTERNS:
                if pattern.search(value):
                    leakage += 1
                    add_issue(report, "ERROR", "sensitive_value", "sensitive value pattern found", str(path), row_id, column, value[:160])
            for pattern in OVERCLAIM_PATTERNS:
                if pattern.search(value) and not ("not supported" in value.lower() or "not a" in value.lower() or "no " in value.lower()):
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
        add_issue(report, "ERROR", "missing_results_doc", "missing Slice 3E results document", str(RESULTS_DOC))

    if report:
        args.summary_txt.parent.mkdir(parents=True, exist_ok=True)
        args.summary_txt.write_text("FAIL\nmissing required outputs\n", encoding="utf-8")
        pd.DataFrame(report, columns=REPORT_FIELDS).to_csv(args.report_csv, index=False)
        print("FAIL: missing required outputs")
        return 1

    policy = loaded["policy_comparison"]
    random_summary = loaded["random_summary"]
    random_raw = loaded["random_raw"]
    pareto = loaded["pareto"]
    final = loaded["final"]

    if policy.empty:
        add_issue(report, "ERROR", "empty_policy_comparison", "policy comparison is empty")
    for col in REQUIRED_POLICY_COLUMNS:
        if col not in policy.columns:
            add_issue(report, "ERROR", "missing_column", f"missing policy column: {col}", str(FILES["policy_comparison"]), field=col)
    missing_policies = sorted(set(REQUIRED_POLICIES) - set(policy.get("policy_id", pd.Series(dtype=str))))
    for pid in missing_policies:
        add_issue(report, "ERROR", "missing_policy", f"required policy missing: {pid}")

    required_random_targets = set(policy.loc[policy["random_baseline_required"] == "yes", "policy_id"])
    raw_targets = set(random_raw.get("target_policy_id", pd.Series(dtype=str)))
    missing_random = sorted(required_random_targets - raw_targets)
    for target in missing_random:
        add_issue(report, "ERROR", "missing_random_baseline", f"missing random baseline for {target}")

    repeat_counts = random_raw.groupby("target_policy_id")["random_repeat"].nunique() if "target_policy_id" in random_raw.columns else pd.Series(dtype=int)
    low_repeat = repeat_counts[repeat_counts < args.min_random_repeats]
    for target, count in low_repeat.items():
        add_issue(report, "ERROR", "too_few_random_repeats", f"random baseline has {count} repeats", row_id=str(target))

    for col in ["top1_accuracy", "top3_accuracy", "top5_accuracy", "mAP", "MRR", "false_top1_rate", "query_coverage", "positive_retention", "candidate_retention"]:
        if col in policy.columns and not policy[col].map(valid_rate_or_nan).all():
            add_issue(report, "ERROR", "invalid_rate", f"invalid rate values in {col}", str(FILES["policy_comparison"]), field=col)

    if "pareto_efficient" not in pareto.columns or not set(pareto["pareto_efficient"]).issubset({"yes", "no"}):
        add_issue(report, "ERROR", "invalid_pareto", "pareto output must include yes/no pareto_efficient")
    if final.empty or "decision_item" not in final.columns:
        add_issue(report, "ERROR", "invalid_final_recommendation", "final recommendation is invalid")
    elif "slice3e_reid_accuracy_improvement_claim" not in set(final["decision_item"]):
        add_issue(report, "ERROR", "missing_final_decision", "final recommendation lacks Slice 3E decision")

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

    doc_text = RESULTS_DOC.read_text(encoding="utf-8")
    required_doc_phrases = [
        "No model training",
        "No external dataset",
        "random same-size",
        "not a Re-ID model",
        "population estimation",
    ]
    for phrase in required_doc_phrases:
        if phrase.lower() not in doc_text.lower():
            add_issue(report, "ERROR", "missing_doc_boundary", f"results doc missing required phrase: {phrase}", str(RESULTS_DOC))
    for pattern in FORBIDDEN_VALUE_PATTERNS:
        if pattern.search(doc_text):
            leakage += 1
            add_issue(report, "ERROR", "sensitive_doc_value", "sensitive value pattern found in results doc", str(RESULTS_DOC), value=pattern.pattern)

    error_count = sum(1 for issue in report if issue["severity"] == "ERROR")
    warning_count = sum(1 for issue in report if issue["severity"] == "WARN")
    status = "PASS" if error_count == 0 else "FAIL"
    summary_lines = [
        status,
        f"policy_comparison_row_count: {len(policy)}",
        f"random_summary_row_count: {len(random_summary)}",
        f"random_raw_row_count: {len(random_raw)}",
        f"random_target_count: {len(repeat_counts)}",
        f"minimum_random_repeat_count: {int(repeat_counts.min()) if len(repeat_counts) else 0}",
        f"pareto_row_count: {len(pareto)}",
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
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--figure-dir", type=Path, default=FIGURE_DIR)
    parser.add_argument("--summary-txt", type=Path, default=SUMMARY_TXT)
    parser.add_argument("--report-csv", type=Path, default=REPORT_CSV)
    parser.add_argument("--min-random-repeats", type=int, default=100)
    return parser.parse_args()


def main() -> int:
    return audit(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
