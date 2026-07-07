#!/usr/bin/env python3
"""Build conformal-inspired PF-ERI selective evidence router diagnostics."""

from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ADVANCED_DIR = PROJECT_ROOT / "outputs/modeling-validation/advanced-mathematical-validation"
CONTRACT_AUDIT_JSON = ADVANCED_DIR / "advanced_mathematical_validation_contract_audit.json"
ROUTES_CSV = PROJECT_ROOT / "outputs/modeling-validation/risk-calibrated-evidence-admission/risk_calibrated_pair_routes.csv"
BOBCAT_AUDIT_JSON = (
    PROJECT_ROOT / "outputs/modeling-validation/bobcat-wild-urban-transfer-stress/bobcat_transfer_stress_audit.json"
)
THRESHOLDS_CSV = ADVANCED_DIR / "conformal_selective_thresholds.csv"
RISK_COVERAGE_CSV = ADVANCED_DIR / "conformal_selective_risk_coverage.csv"
ROUTED_PAIRS_CSV = ADVANCED_DIR / "conformal_selective_pair_routes.csv"
AUDIT_JSON = ADVANCED_DIR / "conformal_selective_router_audit.json"
REPORT_MD = ADVANCED_DIR / "conformal_selective_router_README.md"

TARGET_ALPHAS = [0.05, 0.10, 0.15, 0.20, 0.30]
CALIBRATION_ROLE = "calibration"
EVALUATION_ROLE = "evaluation"
FINITE_SAMPLE_DELTA = 0.10

THRESHOLD_COLUMNS = [
    "alpha",
    "risk_threshold_tau",
    "evidence_score_threshold",
    "calibration_accepted_count",
    "calibration_coverage",
    "calibration_selective_risk",
    "calibration_hoeffding_upper_risk",
    "evaluation_accepted_count",
    "evaluation_coverage",
    "evaluation_selective_risk",
    "selection_rule",
    "finite_sample_status",
    "claim_scope",
]
CURVE_COLUMNS = [
    "scope",
    "risk_threshold_tau",
    "evidence_score_threshold",
    "accepted_count",
    "coverage",
    "selective_risk",
    "hoeffding_upper_risk",
    "review_ready_rate",
]
PAIR_COLUMNS = [
    "descriptor_name",
    "review_pair_id",
    "fold_id",
    "calibration_role",
    "review_ready_label",
    "not_ready_or_uncertain_label",
    "evidence_admission_score",
    "evidence_risk_score",
    "nonconformity_loss",
    "alpha_0_15_admitted",
    "alpha_0_15_route_label",
    "claim_boundary",
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


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def evidence_risk(row: dict[str, Any]) -> float:
    if str(row.get("evidence_risk_score", "")).strip():
        return to_float(row["evidence_risk_score"])
    return 1.0 - to_float(row["evidence_admission_score"])


def accepted_rows(rows: list[dict[str, Any]], risk_threshold_tau: float) -> list[dict[str, Any]]:
    return [row for row in rows if evidence_risk(row) <= risk_threshold_tau]


def selective_metrics(rows: list[dict[str, Any]], risk_threshold_tau: float, delta: float = FINITE_SAMPLE_DELTA) -> dict[str, Any]:
    accepted = accepted_rows(rows, risk_threshold_tau)
    accepted_count = len(accepted)
    if not rows:
        return {
            "accepted_count": 0,
            "coverage": 0.0,
            "selective_risk": "",
            "hoeffding_upper_risk": "",
            "review_ready_rate": "",
        }
    if not accepted:
        return {
            "accepted_count": 0,
            "coverage": 0.0,
            "selective_risk": "",
            "hoeffding_upper_risk": "",
            "review_ready_rate": "",
        }
    loss_sum = sum(int(row["not_ready_or_uncertain_label"]) for row in accepted)
    risk = loss_sum / accepted_count
    upper = min(1.0, risk + math.sqrt(math.log(1.0 / delta) / (2.0 * accepted_count)))
    return {
        "accepted_count": accepted_count,
        "coverage": accepted_count / len(rows),
        "selective_risk": risk,
        "hoeffding_upper_risk": upper,
        "review_ready_rate": 1.0 - risk,
    }


def candidate_thresholds(rows: list[dict[str, Any]]) -> list[float]:
    return sorted({evidence_risk(row) for row in rows})


def choose_threshold(rows: list[dict[str, Any]], alpha: float) -> dict[str, Any]:
    best: dict[str, Any] | None = None
    for tau in candidate_thresholds(rows):
        metrics = selective_metrics(rows, tau)
        if metrics["accepted_count"] and metrics["selective_risk"] <= alpha:
            candidate = {
                "alpha": alpha,
                "risk_threshold_tau": tau,
                "evidence_score_threshold": 1.0 - tau,
                "calibration_accepted_count": metrics["accepted_count"],
                "calibration_coverage": metrics["coverage"],
                "calibration_selective_risk": metrics["selective_risk"],
                "calibration_hoeffding_upper_risk": metrics["hoeffding_upper_risk"],
            }
            if best is None or candidate["calibration_coverage"] > best["calibration_coverage"]:
                best = candidate
    if best is not None:
        best["selection_rule"] = "max_coverage_subject_to_empirical_calibration_risk_le_alpha"
        best["finite_sample_status"] = (
            "upper_bound_supported" if best["calibration_hoeffding_upper_risk"] <= alpha else "empirical_only_upper_bound_exceeds_alpha"
        )
        best["claim_scope"] = "CzechLynx calibration/evaluation split only; no Bobcat domain-shift guarantee."
        return best
    return {
        "alpha": alpha,
        "risk_threshold_tau": -1.0,
        "evidence_score_threshold": 2.0,
        "calibration_accepted_count": 0,
        "calibration_coverage": 0.0,
        "calibration_selective_risk": "",
        "calibration_hoeffding_upper_risk": "",
        "selection_rule": "no_nonempty_threshold_satisfies_empirical_calibration_risk",
        "finite_sample_status": "no_admission",
        "claim_scope": "No nonempty CzechLynx admission set at this alpha.",
    }


def risk_coverage_rows(rows: list[dict[str, Any]], scope: str) -> list[dict[str, Any]]:
    output = []
    for tau in candidate_thresholds(rows):
        metrics = selective_metrics(rows, tau)
        output.append(
            {
                "scope": scope,
                "risk_threshold_tau": tau,
                "evidence_score_threshold": 1.0 - tau,
                "accepted_count": metrics["accepted_count"],
                "coverage": metrics["coverage"],
                "selective_risk": metrics["selective_risk"],
                "hoeffding_upper_risk": metrics["hoeffding_upper_risk"],
                "review_ready_rate": metrics["review_ready_rate"],
            }
        )
    return output


def routed_pair_rows(rows: list[dict[str, str]], alpha_threshold: float) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        risk = evidence_risk(row)
        admitted = risk <= alpha_threshold
        output.append(
            {
                "descriptor_name": row["descriptor_name"],
                "review_pair_id": row["review_pair_id"],
                "fold_id": row["fold_id"],
                "calibration_role": row["calibration_role"],
                "review_ready_label": row["review_ready_label"],
                "not_ready_or_uncertain_label": row["not_ready_or_uncertain_label"],
                "evidence_admission_score": row["evidence_admission_score"],
                "evidence_risk_score": risk,
                "nonconformity_loss": row["not_ready_or_uncertain_label"],
                "alpha_0_15_admitted": "yes" if admitted else "no",
                "alpha_0_15_route_label": "accept_selective_evidence" if admitted else "defer_selective_evidence",
                "claim_boundary": "Conformal-inspired CzechLynx selective evidence admission only; no identity assignment.",
            }
        )
    return output


def build() -> dict[str, Any]:
    contract = read_json(CONTRACT_AUDIT_JSON)
    rows = read_csv(ROUTES_CSV)
    calibration_rows = [row for row in rows if row["calibration_role"] == CALIBRATION_ROLE]
    evaluation_rows = [row for row in rows if row["calibration_role"] == EVALUATION_ROLE]
    thresholds = []
    for alpha in TARGET_ALPHAS:
        threshold = choose_threshold(calibration_rows, alpha)
        eval_metrics = selective_metrics(evaluation_rows, threshold["risk_threshold_tau"])
        threshold.update(
            {
                "evaluation_accepted_count": eval_metrics["accepted_count"],
                "evaluation_coverage": eval_metrics["coverage"],
                "evaluation_selective_risk": eval_metrics["selective_risk"],
            }
        )
        thresholds.append(threshold)
    threshold_by_alpha = {float(row["alpha"]): float(row["risk_threshold_tau"]) for row in thresholds}
    routed = routed_pair_rows(rows, threshold_by_alpha[0.15])
    curves = (
        risk_coverage_rows(calibration_rows, "calibration")
        + risk_coverage_rows(evaluation_rows, "evaluation")
        + risk_coverage_rows(rows, "all")
    )
    bobcat_audit = read_json(BOBCAT_AUDIT_JSON)
    finite_counts: dict[str, int] = {}
    for threshold in thresholds:
        finite_counts[str(threshold["finite_sample_status"])] = finite_counts.get(str(threshold["finite_sample_status"]), 0) + 1
    audit = {
        "built_at_utc": utc_now(),
        "status": "PASS" if contract.get("status") == "PASS" and thresholds and routed else "FAIL",
        "input_contract_audit_json": project_relative(CONTRACT_AUDIT_JSON),
        "input_routes_csv": project_relative(ROUTES_CSV),
        "thresholds_csv": project_relative(THRESHOLDS_CSV),
        "risk_coverage_csv": project_relative(RISK_COVERAGE_CSV),
        "routed_pairs_csv": project_relative(ROUTED_PAIRS_CSV),
        "target_alphas": TARGET_ALPHAS,
        "calibration_role": CALIBRATION_ROLE,
        "evaluation_role": EVALUATION_ROLE,
        "calibration_rows": len(calibration_rows),
        "evaluation_rows": len(evaluation_rows),
        "loss_definition": "nonconformity_loss = 1 if not-ready-or-uncertain, else 0; selective risk is mean loss among admitted pairs.",
        "threshold_direction": "admit if evidence_risk_score <= risk_threshold_tau, equivalently evidence_admission_score >= evidence_score_threshold.",
        "finite_sample_delta": FINITE_SAMPLE_DELTA,
        "finite_sample_status_counts": dict(sorted(finite_counts.items())),
        "bobcat_conformal_scope": "out_of_scope_for_distribution_free_claims",
        "bobcat_rows_seen_in_transfer_audit": bobcat_audit.get("bobcat_pair_rows", ""),
        "claim_boundary": "Conformal-inspired selective risk calibration on CzechLynx reviewed pairs only; not Re-ID identity accuracy.",
    }
    write_csv(THRESHOLDS_CSV, thresholds, THRESHOLD_COLUMNS)
    write_csv(RISK_COVERAGE_CSV, curves, CURVE_COLUMNS)
    write_csv(ROUTED_PAIRS_CSV, routed, PAIR_COLUMNS)
    write_json(AUDIT_JSON, audit)
    write_report(audit)
    return audit


def write_report(audit: dict[str, Any]) -> None:
    finite_status = json.dumps(audit["finite_sample_status_counts"], sort_keys=True)
    lines = [
        "# Conformal-Inspired Selective Router",
        "",
        f"Status: `{audit['status']}`",
        "",
        "This module chooses alpha-level selective evidence admission thresholds",
        "from CzechLynx calibration folds and reports evaluation risk/coverage.",
        "",
        "## Loss",
        "",
        audit["loss_definition"],
        "",
        "## Direction",
        "",
        audit["threshold_direction"],
        "",
        "## Finite-Sample Diagnostic",
        "",
        f"`{finite_status}`",
        "",
        "Thresholds are selected by empirical calibration selective risk. The",
        "Hoeffding upper-risk column is reported as a diagnostic; rows whose",
        "upper bound exceeds alpha must not be described as finite-sample",
        "upper-bound supported guarantees.",
        "",
        "## Outputs",
        "",
        f"- Thresholds: `{audit['thresholds_csv']}`",
        f"- Risk/coverage curve: `{audit['risk_coverage_csv']}`",
        f"- Pair routes: `{audit['routed_pairs_csv']}`",
        "",
        "## Boundary",
        "",
        audit["claim_boundary"],
        "Bobcat transfer-stress rows are out of scope for distribution-free conformal claims.",
    ]
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    audit = build()
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
