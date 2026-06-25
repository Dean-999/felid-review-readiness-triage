#!/usr/bin/env python3
"""Audit Phase 8 Slice 3F downstream sensitivity outputs."""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase8/downstream_sensitivity"
QC_DIR = PROJECT_ROOT / "outputs/czechlynx/qc"
SUMMARY_TXT = QC_DIR / "phase8_slice3f_downstream_sensitivity_audit_summary.txt"
REPORT_CSV = QC_DIR / "phase8_slice3f_downstream_sensitivity_audit_report.csv"
RESULTS_DOC = PROJECT_ROOT / "docs/phase8/phase8_slice3f_downstream_ecological_sensitivity_simulation_results.md"

FILES = {
    "inventory": OUTPUT_DIR / "phase8_slice3f_input_inventory.csv",
    "policy_metrics": OUTPUT_DIR / "phase8_slice3f_policy_contamination_metrics.csv",
    "assumption_sensitivity": OUTPUT_DIR / "phase8_slice3f_reviewer_assumption_sensitivity.csv",
    "random_comparison": OUTPUT_DIR / "phase8_slice3f_random_same_size_comparison.csv",
    "tradeoff_summary": OUTPUT_DIR / "phase8_slice3f_contamination_tradeoff_summary.csv",
    "final": OUTPUT_DIR / "phase8_slice3f_final_recommendation.csv",
}

REQUIRED_POLICIES = {
    "raw_megadescriptor_topk",
    "random_same_size_candidate_f",
    "random_same_size_v4_0636",
    "random_same_size_strict_pf_eri_reference",
    "candidate_f",
    "v4_0636",
    "strict_pf_eri_reference",
}

REQUIRED_METRICS_COLUMNS = {
    "policy_id",
    "false_candidate_burden",
    "false_candidate_burden_reduction_vs_raw",
    "simulated_false_merge_proxy",
    "review_workload",
    "positive_retention",
    "query_coverage",
    "candidate_retention",
    "risk_reduction_per_evidence_removed",
    "contamination_per_100_reviewed_candidates",
}

FORBIDDEN_HEADERS = [
    "unique_name",
    "working_individual_id",
    "expanded_image_id",
    "review_image_path",
    "local_image_path",
    "raw_path",
    "path",
    "trap_id",
    "camera_id",
    "cell_code",
    "latitude",
    "longitude",
    "gps",
    "site_name",
    "date",
    "query_token",
    "gallery_token",
]

FORBIDDEN_VALUE_PATTERNS = [
    re.compile(r"/Users/", re.IGNORECASE),
    re.compile(r"data/raw", re.IGNORECASE),
    re.compile(r"(?<![A-Za-z])lynx_[0-9]+", re.IGNORECASE),
    re.compile(r"czlx_expanded_[0-9]+", re.IGNORECASE),
    re.compile(r"\bunique_name\b", re.IGNORECASE),
    re.compile(r"\btrap_id\b", re.IGNORECASE),
    re.compile(r"\bcell_code\b", re.IGNORECASE),
    re.compile(r"\blatitude\b", re.IGNORECASE),
    re.compile(r"\blongitude\b", re.IGNORECASE),
]

OVERCLAIM_PATTERNS = [
    re.compile(r"population estimate", re.IGNORECASE),
    re.compile(r"field deployment", re.IGNORECASE),
    re.compile(r"true individual identification", re.IGNORECASE),
    re.compile(r"validated clouded leopard", re.IGNORECASE),
    re.compile(r"validated marbled cat", re.IGNORECASE),
    re.compile(r"robust re-id accuracy improvement", re.IGNORECASE),
    re.compile(r"new re-id model", re.IGNORECASE),
    re.compile(r"movement inference", re.IGNORECASE),
    re.compile(r"site-use inference", re.IGNORECASE),
    re.compile(r"occupancy estimate", re.IGNORECASE),
    re.compile(r"abundance estimate", re.IGNORECASE),
]

NEGATIVE_CONTEXT = [
    "not",
    "no ",
    "forbidden",
    "does not",
    "do not",
    "not a",
    "not ecological",
    "not supported",
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


def has_negative_context(text: str) -> bool:
    lower = text.lower()
    return any(token in lower for token in NEGATIVE_CONTEXT)


def scan_frame(path: Path, df: pd.DataFrame, report: list[dict[str, str]]) -> tuple[int, int]:
    leakage = 0
    overclaim = 0
    for col in df.columns:
        lower = col.lower()
        if any(lower == h or lower.endswith("_" + h) or lower.startswith(h + "_") for h in FORBIDDEN_HEADERS):
            if path.name != "phase8_slice3f_input_inventory.csv":
                leakage += 1
                add_issue(report, "ERROR", "sensitive_header", "sensitive header found", str(path), field=col)
        for pattern in OVERCLAIM_PATTERNS:
            if pattern.search(col):
                overclaim += 1
                add_issue(report, "ERROR", "overclaim_header", "overclaim wording in header", str(path), field=col)
    for idx, row in df.astype(str).iterrows():
        row_id = row.get("policy_id", row.get("decision_item", str(idx)))
        for col, value in row.items():
            if path.name == "phase8_slice3f_input_inventory.csv" and col in {"input_file", "columns"}:
                continue
            for pattern in FORBIDDEN_VALUE_PATTERNS:
                if pattern.search(value):
                    leakage += 1
                    add_issue(report, "ERROR", "sensitive_value", "sensitive value pattern found", str(path), row_id, col, value[:160])
            for pattern in OVERCLAIM_PATTERNS:
                if pattern.search(value) and not has_negative_context(value):
                    overclaim += 1
                    add_issue(report, "ERROR", "overclaim_value", "overclaim wording without negative context", str(path), row_id, col, value[:160])
    return leakage, overclaim


def valid_numeric(series: pd.Series) -> bool:
    vals = pd.to_numeric(series, errors="coerce")
    return vals.notna().all() and vals.map(math.isfinite).all()


def audit(args: argparse.Namespace) -> int:
    report: list[dict[str, str]] = []
    loaded: dict[str, pd.DataFrame] = {}
    for name, path in FILES.items():
        if not path.exists():
            add_issue(report, "ERROR", "missing_output", f"missing required output {path}", str(path))
        else:
            df = pd.read_csv(path)
            loaded[name] = df
            if df.empty:
                add_issue(report, "ERROR", "empty_output", "required output is empty", str(path))
    if not RESULTS_DOC.exists():
        add_issue(report, "ERROR", "missing_results_doc", "missing results document", str(RESULTS_DOC))

    if report:
        QC_DIR.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(report, columns=REPORT_FIELDS).to_csv(REPORT_CSV, index=False)
        SUMMARY_TXT.write_text("FAIL\nmissing or empty required outputs\n", encoding="utf-8")
        print("FAIL: missing or empty required outputs")
        return 1

    policy = loaded["policy_metrics"]
    assumptions = loaded["assumption_sensitivity"]
    random = loaded["random_comparison"]
    tradeoff = loaded["tradeoff_summary"]
    final = loaded["final"]

    missing_cols = sorted(REQUIRED_METRICS_COLUMNS - set(policy.columns))
    for col in missing_cols:
        add_issue(report, "ERROR", "missing_required_column", f"policy metrics missing {col}", str(FILES["policy_metrics"]), field=col)

    policy_ids = set(policy["policy_id"]) | {f"random_same_size_{x}" for x in set(random.get("target_policy_id", pd.Series(dtype=str)))}
    for pid in sorted(REQUIRED_POLICIES - policy_ids):
        add_issue(report, "ERROR", "missing_policy", f"missing required policy/control: {pid}")

    if "false_accept_rate" not in assumptions.columns:
        add_issue(report, "ERROR", "missing_assumption_grid", "assumption output missing false_accept_rate")
    else:
        rates = set(round(float(x), 2) for x in assumptions["false_accept_rate"].dropna().unique())
        expected = {0.05, 0.10, 0.20, 0.30, 0.50}
        if rates != expected:
            add_issue(report, "ERROR", "invalid_assumption_grid", f"false acceptance grid {sorted(rates)} != {sorted(expected)}")

    if "random_repeat_count" not in random.columns or int(random["random_repeat_count"].min()) < args.min_random_repeats:
        add_issue(report, "ERROR", "too_few_random_repeats", f"random repeats below {args.min_random_repeats}")

    numeric_cols = [
        "false_candidate_burden",
        "review_workload",
        "positive_retention",
        "query_coverage",
        "candidate_retention",
        "contamination_per_100_reviewed_candidates",
    ]
    for col in numeric_cols:
        if col in policy.columns and not valid_numeric(policy[col]):
            add_issue(report, "ERROR", "invalid_numeric", f"non-finite numeric values in {col}", str(FILES["policy_metrics"]), field=col)

    if "slice3f_downstream_workflow_value_supported" not in set(final.get("decision_item", pd.Series(dtype=str))):
        add_issue(report, "ERROR", "missing_final_decision", "final recommendation lacks Slice 3F support decision")
    if "beats_random_same_size_on_false_burden" not in tradeoff.columns:
        add_issue(report, "ERROR", "missing_random_comparison_decision", "tradeoff output lacks random comparison decision")

    leakage = 0
    overclaim = 0
    for name, path in FILES.items():
        leak_count, over_count = scan_frame(path, loaded[name], report)
        leakage += leak_count
        overclaim += over_count

    doc_text = RESULTS_DOC.read_text(encoding="utf-8")
    required_doc_phrases = [
        "No training",
        "No external data",
        "No frozen-data edit",
        "not ecological estimation",
        "not a Re-ID model",
        "population size",
        "random same-size",
    ]
    for phrase in required_doc_phrases:
        if phrase.lower() not in doc_text.lower():
            add_issue(report, "ERROR", "missing_doc_boundary", f"results doc missing phrase: {phrase}", str(RESULTS_DOC))
    for pattern in FORBIDDEN_VALUE_PATTERNS:
        if pattern.search(doc_text):
            leakage += 1
            add_issue(report, "ERROR", "sensitive_doc_value", "sensitive value pattern found in results doc", str(RESULTS_DOC), value=pattern.pattern)
    for pattern in OVERCLAIM_PATTERNS:
        for match in pattern.finditer(doc_text):
            start = max(0, match.start() - 80)
            end = min(len(doc_text), match.end() + 80)
            context = doc_text[start:end]
            if not has_negative_context(context):
                overclaim += 1
                add_issue(report, "ERROR", "overclaim_doc_value", "overclaim wording without negative context in results doc", str(RESULTS_DOC), value=context[:200])

    error_count = sum(1 for issue in report if issue["severity"] == "ERROR")
    status = "PASS" if error_count == 0 else "FAIL"
    QC_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(report, columns=REPORT_FIELDS).to_csv(REPORT_CSV, index=False)
    summary = [
        status,
        f"policy_metric_rows: {len(policy)}",
        f"assumption_rows: {len(assumptions)}",
        f"random_comparison_rows: {len(random)}",
        f"tradeoff_rows: {len(tradeoff)}",
        f"minimum_random_repeat_count: {int(random['random_repeat_count'].min()) if 'random_repeat_count' in random.columns else 0}",
        f"leakage_issue_count: {leakage}",
        f"overclaim_issue_count: {overclaim}",
        f"error_count: {error_count}",
    ]
    SUMMARY_TXT.write_text("\n".join(summary) + "\n", encoding="utf-8")
    print("\n".join(summary))
    return 0 if error_count == 0 else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min-random-repeats", type=int, default=200)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(audit(parse_args()))
