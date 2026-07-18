#!/usr/bin/env python3
"""Build descriptor-family-stratified PF-ERI calibration diagnostics."""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scripts import build_conformal_selective_router as conformal
except ImportError:  # pragma: no cover - direct script execution
    import build_conformal_selective_router as conformal


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ADVANCED_DIR = PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/advanced-mathematical-validation"
MODEL_METRICS_CSV = (
    PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/known-id-evidence-sufficiency-validation/known_id_model_metrics.csv"
)
CALIBRATION_BINS_CSV = (
    PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/known-id-evidence-sufficiency-validation/known_id_calibration_bins.csv"
)
CONFORMAL_ROUTES_CSV = ADVANCED_DIR / "conformal_selective_pair_routes.csv"
CONFORMAL_THRESHOLDS_CSV = ADVANCED_DIR / "conformal_selective_thresholds.csv"
CLUSTER_INTERVALS_CSV = ADVANCED_DIR / "cluster_bootstrap_metric_intervals.csv"
OUTPUT_CALIBRATION_CSV = ADVANCED_DIR / "descriptor_stratified_calibration.csv"
OUTPUT_RELIABILITY_CSV = ADVANCED_DIR / "descriptor_stratified_reliability.csv"
OUTPUT_RISK_COVERAGE_CSV = ADVANCED_DIR / "descriptor_stratified_risk_coverage.csv"
OUTPUT_FLAGS_CSV = ADVANCED_DIR / "descriptor_stratified_calibration_flags.csv"
AUDIT_JSON = ADVANCED_DIR / "descriptor_stratified_calibration_audit.json"
REPORT_MD = ADVANCED_DIR / "descriptor_stratified_calibration_README.md"

DESCRIPTOR_SCOPES = ["megadescriptor_l_384", "dinov2_vitl14"]
MODEL_FAMILIES = ["descriptor_only", "quality_only", "pf_eri_evidence_only", "descriptor_plus_pf_eri"]
PRIMARY_MODEL = "descriptor_plus_pf_eri"
REFERENCE_ALPHA = 0.15
MIN_DESCRIPTOR_ROWS = 100
WEAK_ECE_THRESHOLD = 0.10
MATERIAL_AUROC_DROP = 0.05

CALIBRATION_COLUMNS = [
    "descriptor_name",
    "model_family",
    "pair_count",
    "positive_review_ready_count",
    "negative_not_ready_or_uncertain_count",
    "auroc",
    "auprc",
    "brier_score",
    "ece_5bin",
    "auroc_delta_vs_descriptor_only",
    "auroc_delta_vs_quality_only",
    "auroc_delta_vs_pooled_same_model",
    "calibration_status",
    "claim_boundary",
]
RELIABILITY_COLUMNS = [
    "descriptor_name",
    "model_family",
    "bin_id",
    "row_count",
    "mean_predicted",
    "observed_review_ready_rate",
    "absolute_gap",
    "claim_boundary",
]
RISK_COVERAGE_COLUMNS = [
    "descriptor_name",
    "scope",
    "alpha",
    "risk_threshold_tau",
    "accepted_count",
    "coverage",
    "selective_risk",
    "review_ready_rate",
    "claim_boundary",
]
FLAG_COLUMNS = [
    "descriptor_name",
    "flag_id",
    "severity",
    "status",
    "evidence",
    "recommended_interpretation",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def project_relative(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        text = str(value).strip()
        if not text:
            return default
        return float(text)
    except (TypeError, ValueError):
        return default


def metrics_by_key() -> dict[tuple[str, str], dict[str, str]]:
    return {(row["scope"], row["model_family"]): row for row in read_csv(MODEL_METRICS_CSV)}


def descriptor_metric_rows() -> list[dict[str, Any]]:
    metrics = metrics_by_key()
    output = []
    for descriptor in DESCRIPTOR_SCOPES:
        descriptor_baseline = metrics[(descriptor, "descriptor_only")]
        quality_baseline = metrics[(descriptor, "quality_only")]
        for model in MODEL_FAMILIES:
            row = metrics[(descriptor, model)]
            pooled = metrics[("pooled", model)]
            auroc = to_float(row["auroc"])
            pair_count = int(row["pair_count"])
            ece = to_float(row["ece_5bin"])
            statuses = []
            if pair_count < MIN_DESCRIPTOR_ROWS:
                statuses.append("sparse_descriptor_rows")
            if ece > WEAK_ECE_THRESHOLD:
                statuses.append("weak_calibration_ece_gt_0_10")
            if model == PRIMARY_MODEL and auroc < to_float(metrics[("pooled", PRIMARY_MODEL)]["auroc"]) - MATERIAL_AUROC_DROP:
                statuses.append("materially_worse_than_pooled_primary")
            if not statuses:
                statuses.append("pass")
            output.append(
                {
                    "descriptor_name": descriptor,
                    "model_family": model,
                    "pair_count": pair_count,
                    "positive_review_ready_count": row["positive_review_ready_count"],
                    "negative_not_ready_or_uncertain_count": row["negative_not_ready_or_uncertain_count"],
                    "auroc": auroc,
                    "auprc": to_float(row["auprc"]),
                    "brier_score": to_float(row["brier_score"]),
                    "ece_5bin": ece,
                    "auroc_delta_vs_descriptor_only": auroc - to_float(descriptor_baseline["auroc"]),
                    "auroc_delta_vs_quality_only": auroc - to_float(quality_baseline["auroc"]),
                    "auroc_delta_vs_pooled_same_model": auroc - to_float(pooled["auroc"]),
                    "calibration_status": "|".join(statuses),
                    "claim_boundary": "Descriptor-stratified CzechLynx reviewability calibration; not descriptor replacement.",
                }
            )
    return output


def reliability_rows() -> list[dict[str, Any]]:
    rows = []
    for row in read_csv(CALIBRATION_BINS_CSV):
        if row["scope"] not in DESCRIPTOR_SCOPES or row["model_family"] not in MODEL_FAMILIES:
            continue
        mean_pred = to_float(row["mean_predicted"], None) if row["mean_predicted"] else ""
        observed = to_float(row["observed_review_ready_rate"], None) if row["observed_review_ready_rate"] else ""
        abs_gap = abs(mean_pred - observed) if mean_pred != "" and observed != "" else ""
        rows.append(
            {
                "descriptor_name": row["scope"],
                "model_family": row["model_family"],
                "bin_id": row["bin_id"],
                "row_count": row["row_count"],
                "mean_predicted": mean_pred,
                "observed_review_ready_rate": observed,
                "absolute_gap": abs_gap,
                "claim_boundary": "Reliability bins are descriptor-family diagnostics for reviewability only.",
            }
        )
    return rows


def risk_threshold(alpha: float) -> float:
    for row in read_csv(CONFORMAL_THRESHOLDS_CSV):
        if float(row["alpha"]) == alpha:
            return to_float(row["risk_threshold_tau"])
    raise ValueError(f"missing conformal threshold alpha={alpha}")


def risk_coverage_rows() -> list[dict[str, Any]]:
    routes = read_csv(CONFORMAL_ROUTES_CSV)
    tau = risk_threshold(REFERENCE_ALPHA)
    output = []
    for descriptor in DESCRIPTOR_SCOPES:
        descriptor_rows = [row for row in routes if row["descriptor_name"] == descriptor]
        for scope in ["all", "calibration", "evaluation"]:
            subset = [row for row in descriptor_rows if scope == "all" or row["calibration_role"] == scope]
            metrics = conformal.selective_metrics(subset, tau)
            risk = metrics["selective_risk"]
            output.append(
                {
                    "descriptor_name": descriptor,
                    "scope": scope,
                    "alpha": REFERENCE_ALPHA,
                    "risk_threshold_tau": tau,
                    "accepted_count": metrics["accepted_count"],
                    "coverage": metrics["coverage"],
                    "selective_risk": risk,
                    "review_ready_rate": metrics["review_ready_rate"],
                    "claim_boundary": "Descriptor-family selective risk at alpha=0.15; CzechLynx only.",
                }
            )
    return output


def flag_rows(metric_rows: list[dict[str, Any]], risk_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flags = []
    for descriptor in DESCRIPTOR_SCOPES:
        primary = next(row for row in metric_rows if row["descriptor_name"] == descriptor and row["model_family"] == PRIMARY_MODEL)
        statuses = str(primary["calibration_status"]).split("|")
        flags.append(
            {
                "descriptor_name": descriptor,
                "flag_id": "primary_model_calibration_status",
                "severity": "warning" if statuses != ["pass"] else "info",
                "status": primary["calibration_status"],
                "evidence": f"AUROC={primary['auroc']}; ECE={primary['ece_5bin']}; pair_count={primary['pair_count']}",
                "recommended_interpretation": "Report descriptor-family-specific results; do not rely only on pooled metrics.",
            }
        )
        weak_models = [
            row for row in metric_rows
            if row["descriptor_name"] == descriptor and "weak_calibration_ece_gt_0_10" in str(row["calibration_status"])
        ]
        flags.append(
            {
                "descriptor_name": descriptor,
                "flag_id": "any_model_weak_calibration_ece",
                "severity": "warning" if weak_models else "info",
                "status": "warning" if weak_models else "pass",
                "evidence": "|".join(f"{row['model_family']}:ECE={row['ece_5bin']}" for row in weak_models) if weak_models else "none",
                "recommended_interpretation": "Calibration weakness in any comparator model should be reported as model-family nuance, not hidden by the primary model.",
            }
        )
        calibration_risk = next(row for row in risk_rows if row["descriptor_name"] == descriptor and row["scope"] == "calibration")
        calibration_risk_value = calibration_risk["selective_risk"]
        flags.append(
            {
                "descriptor_name": descriptor,
                "flag_id": "alpha_0_15_calibration_selective_risk",
                "severity": "warning" if calibration_risk_value != "" and float(calibration_risk_value) > REFERENCE_ALPHA else "info",
                "status": "pass" if calibration_risk_value != "" and float(calibration_risk_value) <= REFERENCE_ALPHA else "risk_gt_alpha_or_not_estimable",
                "evidence": f"calibration_selective_risk={calibration_risk_value}; coverage={calibration_risk['coverage']}",
                "recommended_interpretation": "Pooled alpha threshold may not control every descriptor family separately; report descriptor-specific calibration risk.",
            }
        )
        eval_risk = next(row for row in risk_rows if row["descriptor_name"] == descriptor and row["scope"] == "evaluation")
        risk_value = eval_risk["selective_risk"]
        flags.append(
            {
                "descriptor_name": descriptor,
                "flag_id": "alpha_0_15_evaluation_selective_risk",
                "severity": "warning" if risk_value != "" and float(risk_value) > REFERENCE_ALPHA else "info",
                "status": "pass" if risk_value != "" and float(risk_value) <= REFERENCE_ALPHA else "risk_gt_alpha_or_not_estimable",
                "evidence": f"evaluation_selective_risk={risk_value}; coverage={eval_risk['coverage']}",
                "recommended_interpretation": "Evaluation risk is reported separately and was not used to choose the threshold.",
            }
        )
    return flags


def build() -> dict[str, Any]:
    metric_rows = descriptor_metric_rows()
    rel_rows = reliability_rows()
    rc_rows = risk_coverage_rows()
    flags = flag_rows(metric_rows, rc_rows)
    descriptor_counts = Counter(row["descriptor_name"] for row in metric_rows if row["model_family"] == PRIMARY_MODEL)
    warning_count = sum(row["severity"] == "warning" for row in flags)
    audit = {
        "built_at_utc": utc_now(),
        "status": "PASS" if set(descriptor_counts) == set(DESCRIPTOR_SCOPES) and metric_rows and rel_rows and rc_rows else "FAIL",
        "input_model_metrics_csv": project_relative(MODEL_METRICS_CSV),
        "input_calibration_bins_csv": project_relative(CALIBRATION_BINS_CSV),
        "input_conformal_routes_csv": project_relative(CONFORMAL_ROUTES_CSV),
        "input_cluster_intervals_csv": project_relative(CLUSTER_INTERVALS_CSV),
        "descriptor_stratified_calibration_csv": project_relative(OUTPUT_CALIBRATION_CSV),
        "descriptor_stratified_reliability_csv": project_relative(OUTPUT_RELIABILITY_CSV),
        "descriptor_stratified_risk_coverage_csv": project_relative(OUTPUT_RISK_COVERAGE_CSV),
        "descriptor_stratified_flags_csv": project_relative(OUTPUT_FLAGS_CSV),
        "descriptor_scopes": DESCRIPTOR_SCOPES,
        "model_families": MODEL_FAMILIES,
        "warning_count": warning_count,
        "claim_boundary": "PF-ERI is evaluated after descriptor retrieval; descriptor-stratified diagnostics do not claim descriptor replacement.",
    }
    write_csv(OUTPUT_CALIBRATION_CSV, metric_rows, CALIBRATION_COLUMNS)
    write_csv(OUTPUT_RELIABILITY_CSV, rel_rows, RELIABILITY_COLUMNS)
    write_csv(OUTPUT_RISK_COVERAGE_CSV, rc_rows, RISK_COVERAGE_COLUMNS)
    write_csv(OUTPUT_FLAGS_CSV, flags, FLAG_COLUMNS)
    write_json(AUDIT_JSON, audit)
    write_report(audit)
    return audit


def write_report(audit: dict[str, Any]) -> None:
    lines = [
        "# Descriptor-Stratified Calibration",
        "",
        f"Status: `{audit['status']}`",
        "",
        "This module checks MegaDescriptor and DINOv2 candidate queues separately",
        "so pooled PF-ERI performance cannot hide descriptor-family behavior.",
        "",
        "## Outputs",
        "",
        f"- Calibration metrics: `{audit['descriptor_stratified_calibration_csv']}`",
        f"- Reliability bins: `{audit['descriptor_stratified_reliability_csv']}`",
        f"- Risk/coverage: `{audit['descriptor_stratified_risk_coverage_csv']}`",
        f"- Flags: `{audit['descriptor_stratified_flags_csv']}`",
        "",
        "## Boundary",
        "",
        audit["claim_boundary"],
    ]
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    audit = build()
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
