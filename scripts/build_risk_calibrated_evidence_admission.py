#!/usr/bin/env python3
"""Calibrate PF-ERI selective evidence-admission routing thresholds."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scripts import build_known_id_evidence_sufficiency_validation as validation
except ImportError:  # pragma: no cover - direct script execution
    import build_known_id_evidence_sufficiency_validation as validation


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VALIDATION_TABLE_CSV = (
    PROJECT_ROOT
    / "archive/pferi_v1/outputs/modeling-validation/known-id-evidence-sufficiency-validation/known_id_reviewability_validation_table.csv"
)
OUTPUT_DIR = PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/risk-calibrated-evidence-admission"
ROUTED_PAIRS_CSV = OUTPUT_DIR / "risk_calibrated_pair_routes.csv"
THRESHOLDS_CSV = OUTPUT_DIR / "risk_calibrated_thresholds.csv"
THRESHOLDS_JSON = OUTPUT_DIR / "risk_calibrated_thresholds.json"
RISK_COVERAGE_CSV = OUTPUT_DIR / "risk_coverage_curve.csv"
AUDIT_JSON = OUTPUT_DIR / "risk_calibrated_router_audit.json"
REPORT_MD = OUTPUT_DIR / "README.md"

MODEL_FAMILY = "descriptor_plus_pf_eri"
FEATURE_NAMES = validation.MODEL_FAMILIES[MODEL_FAMILY]
TARGET_ALPHAS = [0.05, 0.10, 0.15, 0.20, 0.30]
ACCEPT_ALPHA = 0.15
CAUTIOUS_ALPHA = 0.30
CALIBRATION_FOLDS = {0, 1}

ROUTE_COLUMNS = [
    "descriptor_name",
    "review_pair_id",
    "fold_id",
    "calibration_role",
    "review_ready_label",
    "not_ready_or_uncertain_label",
    "evidence_admission_score",
    "evidence_risk_score",
    "route_label",
    "route_reason",
    "accept_threshold_alpha_0_15",
    "cautious_threshold_alpha_0_30",
    "claim_boundary",
]

THRESHOLD_COLUMNS = [
    "alpha",
    "threshold",
    "calibration_accepted_count",
    "calibration_coverage",
    "calibration_empirical_risk",
    "evaluation_accepted_count",
    "evaluation_coverage",
    "evaluation_empirical_risk",
]

CURVE_COLUMNS = ["scope", "threshold", "accepted_count", "coverage", "empirical_risk", "review_ready_rate"]


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


def crossval_predictions(rows: list[dict[str, str]]) -> dict[str, float]:
    predictions: dict[str, float] = {}
    folds = sorted({int(row["fold_id"]) for row in rows})
    for fold in folds:
        train_rows = [row for row in rows if int(row["fold_id"]) != fold]
        eval_rows = [row for row in rows if int(row["fold_id"]) == fold]
        train_x = [[to_float(row[name]) for name in FEATURE_NAMES] for row in train_rows]
        eval_x = [[to_float(row[name]) for name in FEATURE_NAMES] for row in eval_rows]
        train_y = [int(row["review_ready_label"]) for row in train_rows]
        train_x_std, means, stds = validation.standardize(train_x, train_x)
        eval_x_std = [[(row[i] - means[i]) / stds[i] for i in range(len(FEATURE_NAMES))] for row in eval_x]
        weights, intercept = validation.train_logistic(train_x_std, train_y)
        scores = validation.predict_logistic(eval_x_std, weights, intercept)
        for row, score in zip(eval_rows, scores):
            predictions[row["review_pair_id"]] = score
    return predictions


def empirical_risk(rows: list[dict[str, Any]], threshold: float) -> tuple[int, float, float]:
    accepted = [row for row in rows if float(row["evidence_admission_score"]) >= threshold]
    if not rows:
        return 0, 0.0, 0.0
    if not accepted:
        return 0, 0.0, 0.0
    risk = sum(int(row["not_ready_or_uncertain_label"]) for row in accepted) / len(accepted)
    return len(accepted), len(accepted) / len(rows), risk


def choose_threshold(rows: list[dict[str, Any]], alpha: float) -> dict[str, Any]:
    thresholds = sorted({float(row["evidence_admission_score"]) for row in rows}, reverse=True)
    best: dict[str, Any] | None = None
    for threshold in thresholds:
        count, coverage, risk = empirical_risk(rows, threshold)
        if count and risk <= alpha:
            candidate = {
                "alpha": alpha,
                "threshold": threshold,
                "calibration_accepted_count": count,
                "calibration_coverage": coverage,
                "calibration_empirical_risk": risk,
            }
            if best is None or coverage > best["calibration_coverage"]:
                best = candidate
    if best is not None:
        return best
    return {
        "alpha": alpha,
        "threshold": 1.01,
        "calibration_accepted_count": 0,
        "calibration_coverage": 0.0,
        "calibration_empirical_risk": "",
    }


def risk_coverage_curve(rows: list[dict[str, Any]], scope: str) -> list[dict[str, Any]]:
    output = []
    thresholds = sorted({float(row["evidence_admission_score"]) for row in rows}, reverse=True)
    for threshold in thresholds:
        count, coverage, risk = empirical_risk(rows, threshold)
        output.append(
            {
                "scope": scope,
                "threshold": threshold,
                "accepted_count": count,
                "coverage": coverage,
                "empirical_risk": risk,
                "review_ready_rate": 1.0 - risk if count else "",
            }
        )
    return output


def route_for_row(row: dict[str, Any], accept_threshold: float, cautious_threshold: float) -> tuple[str, str]:
    score = float(row["evidence_admission_score"])
    high_descriptor = to_float(row["descriptor_similarity_percentile"], 0.0) >= 0.75
    low_overlap = to_float(row.get("body_part_overlap_score"), 1.0) < 0.55
    low_visible_evidence = to_float(row.get("visible_pattern_area_score"), 1.0) < 0.65
    low_descriptor_agreement = to_float(row["cross_descriptor_agreement_score"], 0.5) < 0.49
    if high_descriptor and (low_descriptor_agreement or low_overlap or low_visible_evidence):
        return "conflict_review", "high_descriptor_similarity_low_pair_evidence_or_descriptor_agreement"
    if score >= accept_threshold:
        return "accept_review", "score_above_alpha_0_15_threshold"
    if score >= cautious_threshold:
        return "cautious_review", "score_above_alpha_0_30_threshold"
    return "defer_low_evidence", "score_below_cautious_threshold"


def build() -> dict[str, Any]:
    rows = read_csv(VALIDATION_TABLE_CSV)
    predictions = crossval_predictions(rows)
    routed = []
    for row in rows:
        score = predictions[row["review_pair_id"]]
        routed.append(
            {
                **row,
                "calibration_role": "calibration" if int(row["fold_id"]) in CALIBRATION_FOLDS else "evaluation",
                "evidence_admission_score": score,
                "evidence_risk_score": 1.0 - score,
            }
        )
    calibration_rows = [row for row in routed if row["calibration_role"] == "calibration"]
    evaluation_rows = [row for row in routed if row["calibration_role"] == "evaluation"]
    thresholds = []
    for alpha in TARGET_ALPHAS:
        threshold = choose_threshold(calibration_rows, alpha)
        eval_count, eval_coverage, eval_risk = empirical_risk(evaluation_rows, float(threshold["threshold"]))
        threshold.update(
            {
                "evaluation_accepted_count": eval_count,
                "evaluation_coverage": eval_coverage,
                "evaluation_empirical_risk": eval_risk if eval_count else "",
            }
        )
        thresholds.append(threshold)
    threshold_by_alpha = {float(row["alpha"]): float(row["threshold"]) for row in thresholds}
    accept_threshold = threshold_by_alpha[ACCEPT_ALPHA]
    cautious_threshold = threshold_by_alpha[CAUTIOUS_ALPHA]
    routed_output = []
    for row in routed:
        route, reason = route_for_row(row, accept_threshold, cautious_threshold)
        routed_output.append(
            {
                **row,
                "route_label": route,
                "route_reason": reason,
                "accept_threshold_alpha_0_15": accept_threshold,
                "cautious_threshold_alpha_0_30": cautious_threshold,
                "claim_boundary": "Risk-calibrated evidence admission only; not Re-ID identity accuracy.",
            }
        )
    curves = (
        risk_coverage_curve(calibration_rows, "calibration")
        + risk_coverage_curve(evaluation_rows, "evaluation")
        + risk_coverage_curve(routed, "all")
    )
    route_counts = dict(sorted((route, sum(row["route_label"] == route for row in routed_output)) for route in {row["route_label"] for row in routed_output}))
    audit = {
        "built_at_utc": utc_now(),
        "status": "PASS" if routed_output and thresholds and "accept_review" in route_counts else "FAIL",
        "input_validation_table_csv": project_relative(VALIDATION_TABLE_CSV),
        "routed_pairs_csv": project_relative(ROUTED_PAIRS_CSV),
        "thresholds_csv": project_relative(THRESHOLDS_CSV),
        "thresholds_json": project_relative(THRESHOLDS_JSON),
        "risk_coverage_csv": project_relative(RISK_COVERAGE_CSV),
        "model_family": MODEL_FAMILY,
        "feature_names": FEATURE_NAMES,
        "calibration_folds": sorted(CALIBRATION_FOLDS),
        "target_alphas": TARGET_ALPHAS,
        "pair_rows": len(routed_output),
        "route_counts": route_counts,
        "thresholds": thresholds,
        "claim_boundary": "Risk-calibrated evidence admission only; not Re-ID identity accuracy.",
    }
    write_csv(ROUTED_PAIRS_CSV, routed_output, ROUTE_COLUMNS)
    write_csv(THRESHOLDS_CSV, thresholds, THRESHOLD_COLUMNS)
    write_json(THRESHOLDS_JSON, {"thresholds": thresholds, "model_family": MODEL_FAMILY, "feature_names": FEATURE_NAMES})
    write_csv(RISK_COVERAGE_CSV, curves, CURVE_COLUMNS)
    write_json(AUDIT_JSON, audit)
    write_report(audit)
    return audit


def write_report(audit: dict[str, Any]) -> None:
    lines = [
        "# Risk-Calibrated Evidence Admission",
        "",
        f"Status: `{audit['status']}`",
        "",
        "This module calibrates selective evidence-admission thresholds from",
        "CzechLynx reviewed-pair validation outputs.",
        "",
        "## Outputs",
        "",
        f"- Routed pairs: `{audit['routed_pairs_csv']}`",
        f"- Thresholds: `{audit['thresholds_csv']}`",
        f"- Risk/coverage curve: `{audit['risk_coverage_csv']}`",
        "",
        "## Route Counts",
        "",
        f"`{audit['route_counts']}`",
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
