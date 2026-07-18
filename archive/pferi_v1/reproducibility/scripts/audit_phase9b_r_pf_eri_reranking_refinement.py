#!/usr/bin/env python3
"""Audit Phase 9B-R PF-ERI reranking refinement outputs."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase9/pf_eri_reranking_refinement"
QC_DIR = PROJECT_ROOT / "outputs/czechlynx/qc"
SUMMARY_TXT = QC_DIR / "phase9b_r_pf_eri_reranking_refinement_audit_summary.txt"
REPORT_CSV = QC_DIR / "phase9b_r_pf_eri_reranking_refinement_audit_report.csv"
RESULTS_DOC = PROJECT_ROOT / "docs/phase9/phase9b_r_pf_eri_reranking_refinement_results.md"

FILES = {
    "inventory": OUTPUT_DIR / "phase9b_r_input_inventory.csv",
    "visual_diagnosis": OUTPUT_DIR / "phase9b_r_visual_component_diagnosis.csv",
    "correlations": OUTPUT_DIR / "phase9b_r_component_correlation_summary.csv",
    "method_summary": OUTPUT_DIR / "phase9b_r_refined_method_metric_summary.csv",
    "heldout": OUTPUT_DIR / "phase9b_r_heldout_split_metric_summary.csv",
    "random_size": OUTPUT_DIR / "phase9b_r_random_same_size_controls.csv",
    "random_coverage": OUTPUT_DIR / "phase9b_r_random_same_coverage_controls.csv",
    "ablation": OUTPUT_DIR / "phase9b_r_feature_ablation_refined_summary.csv",
    "risk": OUTPUT_DIR / "phase9b_r_risk_coverage_curve.csv",
    "pareto": OUTPUT_DIR / "phase9b_r_pareto_summary.csv",
    "final": OUTPUT_DIR / "phase9b_r_final_recommendation.csv",
}

REQUIRED_METHODS = {
    "raw_megadescriptor",
    "raw_resnet50",
    "phase9b_candidate_utility_plus_descriptor",
    "phase9b_full_minus_visual",
    "descriptor_confidence_plus_disagreement",
    "reciprocal_margin_plus_disagreement",
    "visual_as_gate_only",
    "visual_as_penalty_only",
    "visual_failure_penalty_only",
    "visual_identity_only_no_generic_quality",
    "visual_interaction_with_disagreement",
    "visual_interaction_with_low_margin",
    "candidate_utility_with_retention_constraint",
    "candidate_utility_with_coverage_floor",
    "candidate_utility_pareto_selected",
    "quality_only_baseline",
}

SENSITIVE_HEADERS = {
    "unique_name",
    "working_individual_id",
    "query_identity_internal",
    "gallery_identity_internal",
    "expanded_image_id",
    "review_image_path",
    "review_image_path_local",
    "source_review_image_path_original",
    "path",
    "local_image_path",
    "latitude",
    "longitude",
    "cell_code",
    "trap_id",
    "camera_id",
    "site",
    "query_idx",
    "gallery_idx",
}

SENSITIVE_PATTERNS = [
    re.compile(r"/Users/", re.IGNORECASE),
    re.compile(r"data/raw", re.IGNORECASE),
    re.compile(r"(?<![A-Za-z])lynx_[0-9]+", re.IGNORECASE),
    re.compile(r"czlx_expanded_[0-9]+", re.IGNORECASE),
    re.compile(r"\bworking_individual_id\b", re.IGNORECASE),
    re.compile(r"\bunique_name\b", re.IGNORECASE),
    re.compile(r"\blatitude\b", re.IGNORECASE),
    re.compile(r"\blongitude\b", re.IGNORECASE),
    re.compile(r"\btrap_id\b", re.IGNORECASE),
    re.compile(r"\bcell_code\b", re.IGNORECASE),
    re.compile(r"\bcamera_id\b", re.IGNORECASE),
]

FORBIDDEN_CLAIMS = [
    "validated on Mainland Clouded Leopard",
    "validated on Marbled Cat",
    "field deployment ready",
    "population estimation",
    "automatic identity assignment",
    "true individual identification",
    "new Re-ID descriptor",
    "new deep Re-ID model",
    "robustly improves Re-ID accuracy",
]

REPORT_FIELDS = ["severity", "issue_type", "file", "row_id", "field", "value", "message"]


def add_issue(
    report: list[dict[str, str]],
    severity: str,
    issue_type: str,
    message: str,
    file: str = "",
    row_id: str = "",
    field: str = "",
    value: str = "",
) -> None:
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


def scan_frame(path: Path, df: pd.DataFrame, report: list[dict[str, str]]) -> tuple[int, int]:
    leakage = 0
    overclaim = 0
    for column in df.columns:
        lower = column.lower()
        if lower in SENSITIVE_HEADERS:
            leakage += 1
            add_issue(report, "ERROR", "sensitive_header", "sensitive header found", str(path), field=column)

    for idx, row in df.astype(str).iterrows():
        row_id = row.get("method_id", row.get("decision_item", str(idx)))
        for column, value in row.items():
            if path.name == "phase9b_r_input_inventory.csv" and column in {"input_file", "columns"}:
                continue
            for pattern in SENSITIVE_PATTERNS:
                if pattern.search(value):
                    leakage += 1
                    add_issue(report, "ERROR", "sensitive_value", "sensitive value pattern found", str(path), row_id, column, value[:160])
            for phrase in FORBIDDEN_CLAIMS:
                if phrase.lower() in value.lower() and not any(marker in value.lower() for marker in ["forbidden", "not ", "no ", "avoid"]):
                    overclaim += 1
                    add_issue(report, "ERROR", "overclaim_value", "forbidden overclaim wording found", str(path), row_id, column, value[:160])
    return leakage, overclaim


def scan_doc(report: list[dict[str, str]]) -> tuple[int, int]:
    if not RESULTS_DOC.exists():
        add_issue(report, "ERROR", "missing_results_doc", "missing Phase 9B-R results document", str(RESULTS_DOC))
        return 0, 0
    text = RESULTS_DOC.read_text(encoding="utf-8")
    leakage = 0
    overclaim = 0
    for pattern in SENSITIVE_PATTERNS:
        if pattern.search(text):
            leakage += 1
            add_issue(report, "ERROR", "sensitive_doc_value", "sensitive value pattern found in results doc", str(RESULTS_DOC), value=pattern.pattern)
    forbidden_section = text.lower().split("## 12. forbidden claims", 1)[-1]
    for phrase in FORBIDDEN_CLAIMS:
        lower = phrase.lower()
        if lower in text.lower() and lower not in forbidden_section:
            overclaim += 1
            add_issue(report, "ERROR", "overclaim_doc", "forbidden overclaim outside forbidden section", str(RESULTS_DOC), value=phrase)
    return leakage, overclaim


def audit(args: argparse.Namespace) -> int:
    report: list[dict[str, str]] = []
    loaded: dict[str, pd.DataFrame] = {}
    for name, path in FILES.items():
        if not path.exists():
            add_issue(report, "ERROR", "missing_output", f"missing output: {path}", str(path))
        else:
            loaded[name] = pd.read_csv(path)

    if report:
        QC_DIR.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(report, columns=REPORT_FIELDS).to_csv(REPORT_CSV, index=False)
        SUMMARY_TXT.write_text("FAIL\nmissing required outputs\n", encoding="utf-8")
        print("FAIL: missing required outputs")
        return 1

    methods = set(loaded["method_summary"].get("method_id", pd.Series(dtype=str)))
    for method in sorted(REQUIRED_METHODS - methods):
        add_issue(report, "ERROR", "missing_required_method", f"missing method: {method}")

    for method in sorted(REQUIRED_METHODS - set(loaded["heldout"].get("method_id", pd.Series(dtype=str)))):
        add_issue(report, "ERROR", "missing_heldout_method", f"held-out table missing method: {method}")

    heldout = loaded["heldout"]
    if "split_role" not in heldout.columns or set(heldout["split_role"]) != {"evaluation"}:
        add_issue(report, "ERROR", "split_role_error", "heldout table must contain evaluation split_role only")
    if "split_id" not in heldout.columns or heldout["split_id"].nunique() < args.min_splits:
        add_issue(report, "ERROR", "too_few_splits", f"must have at least {args.min_splits} held-out splits")
    if "calibration_score" not in heldout.columns:
        add_issue(report, "ERROR", "missing_calibration_score", "heldout table lacks calibration_score")
    if "calibrated_weight" not in heldout.columns:
        add_issue(report, "ERROR", "missing_calibrated_weight", "heldout table lacks calibrated_weight")

    for control_name in ["random_size", "random_coverage"]:
        control = loaded[control_name]
        if control.empty:
            add_issue(report, "ERROR", "empty_random_control", f"{control_name} is empty")
            continue
        if "random_repeat_count" not in control.columns:
            add_issue(report, "ERROR", "missing_random_repeat_count", f"{control_name} lacks random_repeat_count")
        elif int(pd.to_numeric(control["random_repeat_count"], errors="coerce").min()) < args.min_random_repeats:
            add_issue(report, "ERROR", "too_few_random_repeats", f"{control_name} below minimum repeat count")

    required_metric_cols = [
        "mAP",
        "MRR",
        "top1_accuracy",
        "top5_accuracy",
        "false_candidate_burden",
        "query_coverage",
        "positive_retention",
        "candidate_retention",
        "coverage_adjusted_mAP",
    ]
    for metric in required_metric_cols:
        if metric not in heldout.columns:
            add_issue(report, "ERROR", "missing_metric", f"heldout missing metric {metric}")

    summary = loaded["method_summary"]
    for col in [
        "random_same_size_mAP_minus_random_mean",
        "random_same_coverage_mAP_minus_random_mean",
        "mAP_minus_raw_megadescriptor",
        "mAP_minus_quality_only",
        "mAP_minus_phase9b_candidate_utility",
        "mAP_minus_phase9b_full_minus_visual",
    ]:
        if col not in summary.columns:
            add_issue(report, "ERROR", "missing_summary_comparison", f"method summary missing {col}")

    if loaded["visual_diagnosis"].empty:
        add_issue(report, "ERROR", "empty_visual_diagnosis", "visual diagnosis table is empty")
    if loaded["correlations"].empty:
        add_issue(report, "ERROR", "empty_correlations", "component correlation table is empty")
    if loaded["risk"].empty:
        add_issue(report, "ERROR", "empty_risk_coverage", "risk-coverage table is empty")
    if "pareto_efficient" not in loaded["pareto"].columns or not set(loaded["pareto"]["pareto_efficient"]).issubset({"yes", "no"}):
        add_issue(report, "ERROR", "invalid_pareto", "pareto table must contain yes/no pareto_efficient")

    final_items = set(loaded["final"].get("decision_item", pd.Series(dtype=str)))
    for item in ["phase9b_r_refinement_decision", "best_refined_method", "phase9c_recommended", "visual_utility_interpretation"]:
        if item not in final_items:
            add_issue(report, "ERROR", "missing_final_item", f"final recommendation missing {item}")

    leakage = 0
    overclaim = 0
    for name, path in FILES.items():
        leak_count, over_count = scan_frame(path, loaded[name], report)
        leakage += leak_count
        overclaim += over_count
    doc_leakage, doc_overclaim = scan_doc(report)
    leakage += doc_leakage
    overclaim += doc_overclaim

    delayed_refs = int(loaded["inventory"]["input_file"].astype(str).str.contains("second_review|second-review", case=False, regex=True).sum())
    if delayed_refs:
        add_issue(report, "ERROR", "delayed_second_review_access", "input inventory references delayed second-review data")

    status = "PASS" if not any(item["severity"] == "ERROR" for item in report) else "FAIL"
    summary_lines = [
        status,
        f"required_output_count={len(FILES)}",
        f"method_count={summary['method_id'].nunique()}",
        f"split_count={heldout['split_id'].nunique() if 'split_id' in heldout.columns else 0}",
        f"random_same_size_min_repeats={int(pd.to_numeric(loaded['random_size'].get('random_repeat_count', pd.Series([0])), errors='coerce').min()) if not loaded['random_size'].empty else 0}",
        f"random_same_coverage_min_repeats={int(pd.to_numeric(loaded['random_coverage'].get('random_repeat_count', pd.Series([0])), errors='coerce').min()) if not loaded['random_coverage'].empty else 0}",
        f"visual_diagnosis_rows={len(loaded['visual_diagnosis'])}",
        f"leakage_issues={leakage}",
        f"overclaim_issues={overclaim}",
        f"delayed_second_review_references={delayed_refs}",
    ]
    QC_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_TXT.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    pd.DataFrame(report, columns=REPORT_FIELDS).to_csv(REPORT_CSV, index=False)
    print("\n".join(summary_lines))
    return 0 if status == "PASS" else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min-splits", type=int, default=20)
    parser.add_argument("--min-random-repeats", type=int, default=200)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(audit(parse_args()))
