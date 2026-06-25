#!/usr/bin/env python3
"""Audit Phase 9B PF-ERI-aware fixed-descriptor reranking outputs."""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase9/pf_eri_fixed_descriptor_reranking"
QC_DIR = PROJECT_ROOT / "outputs/czechlynx/qc"
SUMMARY_TXT = QC_DIR / "phase9b_pf_eri_reranking_audit_summary.txt"
REPORT_CSV = QC_DIR / "phase9b_pf_eri_reranking_audit_report.csv"
RESULTS_DOC = PROJECT_ROOT / "docs/phase9/phase9b_pf_eri_aware_fixed_descriptor_reranking_results.md"

FILES = {
    "inventory": OUTPUT_DIR / "phase9b_input_inventory.csv",
    "candidate_table": OUTPUT_DIR / "phase9b_candidate_level_reranking_table.csv",
    "method_summary": OUTPUT_DIR / "phase9b_method_metric_summary.csv",
    "heldout": OUTPUT_DIR / "phase9b_heldout_split_metric_summary.csv",
    "random_size": OUTPUT_DIR / "phase9b_random_same_size_controls.csv",
    "random_coverage": OUTPUT_DIR / "phase9b_random_same_coverage_controls.csv",
    "ablation": OUTPUT_DIR / "phase9b_feature_ablation_summary.csv",
    "risk": OUTPUT_DIR / "phase9b_risk_coverage_curve.csv",
    "pareto": OUTPUT_DIR / "phase9b_pareto_summary.csv",
    "final": OUTPUT_DIR / "phase9b_final_recommendation.csv",
}

REQUIRED_METHODS = {
    "raw_megadescriptor_ranking",
    "raw_resnet50_ranking",
    "simple_pf_eri_hard_filtering",
    "quality_only_reranking",
    "image_utility_reranking",
    "pair_utility_reranking",
    "candidate_utility_reranking",
    "candidate_utility_plus_descriptor_reranking",
}

REQUIRED_ABLATIONS = {
    "descriptor_only",
    "visual_quality_only",
    "visual_identity_evidence_only",
    "descriptor_confidence_only",
    "reciprocal_margin_only",
    "descriptor_disagreement_only",
    "image_utility_only",
    "pair_utility_only",
    "full_pf_eri_candidate_utility",
    "full_minus_visual",
    "full_minus_descriptor_disagreement",
    "full_minus_reciprocal_margin",
}

FORBIDDEN_HEADERS = [
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
    re.compile(r"\bcamera_id\b", re.IGNORECASE),
]

OVERCLAIM_PATTERNS = [
    re.compile(r"PF-ERI is a new Re-ID descriptor", re.IGNORECASE),
    re.compile(r"PF-ERI is a trained deep Re-ID model", re.IGNORECASE),
    re.compile(r"identifies true individuals automatically", re.IGNORECASE),
    re.compile(r"validated across felids", re.IGNORECASE),
    re.compile(r"validated on Mainland Clouded Leopard", re.IGNORECASE),
    re.compile(r"validated on Marbled Cat", re.IGNORECASE),
    re.compile(r"field-deployment ready", re.IGNORECASE),
    re.compile(r"estimates population size", re.IGNORECASE),
    re.compile(r"supports movement, occupancy, abundance, survival, or site-use inference", re.IGNORECASE),
]

REPORT_FIELDS = ["severity", "issue_type", "file", "row_id", "field", "value", "message"]


def add_issue(report: list[dict[str, str]], severity: str, issue_type: str, message: str, file: str = "", row_id: str = "", field: str = "", value: str = "") -> None:
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


def is_finite_or_nan(value: object) -> bool:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return False
    return math.isnan(v) or math.isfinite(v)


def scan_frame(path: Path, df: pd.DataFrame, report: list[dict[str, str]]) -> tuple[int, int]:
    leakage = 0
    overclaim = 0
    for column in df.columns:
        lower = column.lower()
        if any(part == lower or lower.endswith("_" + part) or lower.startswith(part + "_") for part in FORBIDDEN_HEADERS):
            leakage += 1
            add_issue(report, "ERROR", "sensitive_header", "sensitive header found", str(path), field=column)
    for idx, row in df.astype(str).iterrows():
        row_id = row.get("method_id", row.get("decision_item", str(idx)))
        for column, value in row.items():
            if path.name == "phase9b_input_inventory.csv" and column in {"input_file", "columns"}:
                continue
            for pattern in FORBIDDEN_VALUE_PATTERNS:
                if pattern.search(value):
                    leakage += 1
                    add_issue(report, "ERROR", "sensitive_value", "sensitive value pattern found", str(path), row_id, column, value[:160])
            for pattern in OVERCLAIM_PATTERNS:
                if pattern.search(value) and not any(marker in value.lower() for marker in ["not ", "forbidden", "no ", "must not"]):
                    overclaim += 1
                    add_issue(report, "ERROR", "overclaim_value", "forbidden overclaim wording found", str(path), row_id, column, value[:160])
    return leakage, overclaim


def audit(args: argparse.Namespace) -> int:
    report: list[dict[str, str]] = []
    loaded: dict[str, pd.DataFrame] = {}
    for name, path in FILES.items():
        if not path.exists():
            add_issue(report, "ERROR", "missing_output", f"missing output: {path}", str(path))
        else:
            loaded[name] = pd.read_csv(path)
    if not RESULTS_DOC.exists():
        add_issue(report, "ERROR", "missing_results_doc", "missing Phase 9B results document", str(RESULTS_DOC))

    if report:
        QC_DIR.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(report, columns=REPORT_FIELDS).to_csv(REPORT_CSV, index=False)
        SUMMARY_TXT.write_text("FAIL\nmissing required outputs\n", encoding="utf-8")
        print("FAIL: missing required outputs")
        return 1

    methods = set(loaded["method_summary"].get("method_id", pd.Series(dtype=str)))
    for method in sorted(REQUIRED_METHODS - methods):
        add_issue(report, "ERROR", "missing_required_method", f"missing method: {method}")

    ablations = set(loaded["ablation"].get("method_id", pd.Series(dtype=str)))
    for method in sorted(REQUIRED_ABLATIONS - ablations):
        add_issue(report, "ERROR", "missing_required_ablation", f"missing ablation: {method}")

    heldout = loaded["heldout"]
    if "split_role" not in heldout.columns or set(heldout["split_role"]) != {"evaluation"}:
        add_issue(report, "ERROR", "split_role_error", "heldout table must contain evaluation split_role only")
    if "split_id" not in heldout.columns or heldout["split_id"].nunique() < args.min_splits:
        add_issue(report, "ERROR", "too_few_splits", f"must have at least {args.min_splits} held-out splits")

    candidate = loaded["candidate_table"]
    for required in ["split_id", "calibration_or_evaluation", "query_image_id", "gallery_image_id", "same_identity_truth_internal"]:
        if required not in candidate.columns:
            add_issue(report, "ERROR", "missing_candidate_column", f"candidate table missing {required}")
    if "calibration_or_evaluation" in candidate.columns and not set(candidate["calibration_or_evaluation"]).issuperset({"calibration", "evaluation"}):
        add_issue(report, "ERROR", "missing_split_roles", "candidate table must include calibration and evaluation roles")

    for control_name in ["random_size", "random_coverage"]:
        control = loaded[control_name]
        if control.empty:
            add_issue(report, "ERROR", "empty_random_control", f"{control_name} is empty")
            continue
        if "random_repeat_count" not in control.columns:
            add_issue(report, "ERROR", "missing_random_repeat_count", f"{control_name} lacks random_repeat_count")
        elif int(pd.to_numeric(control["random_repeat_count"], errors="coerce").min()) < args.min_random_repeats:
            add_issue(report, "ERROR", "too_few_random_repeats", f"{control_name} below minimum repeat count")

    for metric in ["mAP", "MRR", "top1_accuracy", "top5_accuracy", "false_candidate_burden", "query_coverage", "positive_retention"]:
        if metric not in heldout.columns:
            add_issue(report, "ERROR", "missing_metric", f"heldout missing metric {metric}")
        elif not heldout[metric].map(is_finite_or_nan).all():
            add_issue(report, "ERROR", "nonfinite_metric", f"non-finite metric values in {metric}", field=metric)

    if "pareto_efficient" not in loaded["pareto"].columns or not set(loaded["pareto"]["pareto_efficient"]).issubset({"yes", "no"}):
        add_issue(report, "ERROR", "invalid_pareto", "pareto table must contain yes/no pareto_efficient")
    if "phase9b_fixed_descriptor_reranking_decision" not in set(loaded["final"].get("decision_item", pd.Series(dtype=str))):
        add_issue(report, "ERROR", "missing_final_decision", "final recommendation missing Phase 9B decision")

    leakage = 0
    overclaim = 0
    for path in FILES.values():
        leak_count, over_count = scan_frame(path, loaded[[k for k, v in FILES.items() if v == path][0]], report)
        leakage += leak_count
        overclaim += over_count

    doc_text = RESULTS_DOC.read_text(encoding="utf-8")
    for pattern in FORBIDDEN_VALUE_PATTERNS:
        if pattern.search(doc_text):
            leakage += 1
            add_issue(report, "ERROR", "sensitive_doc_value", "sensitive value pattern found in results doc", str(RESULTS_DOC), value=pattern.pattern)
    forbidden_section = doc_text.lower().split("## 16. forbidden claims", 1)[-1]
    for pattern in OVERCLAIM_PATTERNS:
        for match in pattern.finditer(doc_text):
            if match.group(0).lower() not in forbidden_section:
                overclaim += 1
                add_issue(report, "ERROR", "overclaim_doc", "forbidden overclaim outside forbidden section", str(RESULTS_DOC), value=match.group(0))

    delayed_inputs = loaded["inventory"]["input_file"].astype(str).str.contains("second_review|second-review", case=False, regex=True).sum()
    if delayed_inputs:
        add_issue(report, "ERROR", "delayed_second_review_access", "input inventory references delayed second-review data")

    status = "PASS" if not any(item["severity"] == "ERROR" for item in report) else "FAIL"
    summary_lines = [
        status,
        f"required_output_count={len(FILES)}",
        f"method_count={loaded['method_summary']['method_id'].nunique()}",
        f"split_count={heldout['split_id'].nunique() if 'split_id' in heldout.columns else 0}",
        f"candidate_table_rows={len(candidate)}",
        f"random_same_size_min_repeats={int(pd.to_numeric(loaded['random_size'].get('random_repeat_count', pd.Series([0])), errors='coerce').min()) if not loaded['random_size'].empty else 0}",
        f"random_same_coverage_min_repeats={int(pd.to_numeric(loaded['random_coverage'].get('random_repeat_count', pd.Series([0])), errors='coerce').min()) if not loaded['random_coverage'].empty else 0}",
        f"leakage_issues={leakage}",
        f"overclaim_issues={overclaim}",
        f"delayed_second_review_references={int(delayed_inputs)}",
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
