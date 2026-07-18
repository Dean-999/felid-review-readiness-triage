#!/usr/bin/env python3
"""Evaluate Bobcat wild/urban PF-ERI transfer-stress diagnostics."""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scripts import build_known_id_evidence_sufficiency_validation as validation
    from scripts import build_risk_calibrated_evidence_admission as router
except ImportError:  # pragma: no cover - direct script execution
    import build_known_id_evidence_sufficiency_validation as validation
    import build_risk_calibrated_evidence_admission as router


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FEATURE_TABLE_CSV = PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/evidence-feature-extraction/pair_evidence_features.csv"
VALIDATION_TABLE_CSV = (
    PROJECT_ROOT
    / "archive/pferi_v1/outputs/modeling-validation/known-id-evidence-sufficiency-validation/known_id_reviewability_validation_table.csv"
)
THRESHOLDS_JSON = PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/risk-calibrated-evidence-admission/risk_calibrated_thresholds.json"
OUTPUT_DIR = PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/bobcat-wild-urban-transfer-stress"
BOBCAT_ROUTED_CSV = OUTPUT_DIR / "bobcat_transfer_stress_routed_pairs.csv"
SUMMARY_CSV = OUTPUT_DIR / "bobcat_transfer_stress_summary.csv"
AUDIT_JSON = OUTPUT_DIR / "bobcat_transfer_stress_audit.json"
REPORT_MD = OUTPUT_DIR / "README.md"

FEATURE_NAMES = router.FEATURE_NAMES
ROUTED_COLUMNS = [
    "pair_id",
    "pair_scope",
    "query_scope",
    "candidate_scope",
    "evidence_admission_score",
    "evidence_risk_score",
    "route_label",
    "route_reason",
    "descriptor_similarity_percentile",
    "descriptor_source_note",
    "claim_boundary",
]
SUMMARY_COLUMNS = [
    "pair_scope",
    "pair_count",
    "mean_evidence_admission_score",
    "mean_evidence_risk_score",
    "accept_review_rate",
    "cautious_review_rate",
    "defer_low_evidence_rate",
    "conflict_review_rate",
    "expected_human_review_burden_rate",
    "calibration_drift_mean_score_vs_czechlynx",
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


def train_final_router_model() -> tuple[list[float], float, list[float], list[float], float]:
    rows = read_csv(VALIDATION_TABLE_CSV)
    xs = [[to_float(row[name]) for name in FEATURE_NAMES] for row in rows]
    ys = [int(row["review_ready_label"]) for row in rows]
    xs_std, means, stds = validation.standardize(xs, xs)
    weights, intercept = validation.train_logistic(xs_std, ys)
    scores = validation.predict_logistic(xs_std, weights, intercept)
    return weights, intercept, means, stds, sum(scores) / len(scores)


def score_row(row: dict[str, str], weights: list[float], intercept: float, means: list[float], stds: list[float]) -> float:
    values = []
    for name in FEATURE_NAMES:
        if name == "descriptor_similarity_percentile":
            values.append(0.5)
        else:
            values.append(to_float(row[name]))
    standardized = [(values[i] - means[i]) / stds[i] for i in range(len(values))]
    return validation.sigmoid(intercept + sum(weight * value for weight, value in zip(weights, standardized)))


def load_threshold(alpha: float) -> float:
    data = json.loads(THRESHOLDS_JSON.read_text(encoding="utf-8"))
    for row in data["thresholds"]:
        if float(row["alpha"]) == alpha:
            return float(row["threshold"])
    raise ValueError(f"missing threshold for alpha={alpha}")


def pair_endpoint_scopes(pair_scope: str) -> tuple[str, str]:
    if "_to_" in pair_scope:
        left, right = pair_scope.split("_to_", 1)
        return left, right
    return pair_scope, pair_scope


def build() -> dict[str, Any]:
    weights, intercept, means, stds, czech_mean_score = train_final_router_model()
    accept_threshold = load_threshold(0.15)
    cautious_threshold = load_threshold(0.30)
    routed = []
    for row in read_csv(FEATURE_TABLE_CSV):
        if row["pair_family"] != "transfer_stress":
            continue
        score = score_row(row, weights, intercept, means, stds)
        route_input = {**row, "evidence_admission_score": score, "descriptor_similarity_percentile": "0.5"}
        route_label, route_reason = router.route_for_row(route_input, accept_threshold, cautious_threshold)
        query_scope, candidate_scope = pair_endpoint_scopes(row["pair_scope"])
        routed.append(
            {
                "pair_id": row["pair_id"],
                "pair_scope": row["pair_scope"],
                "query_scope": query_scope,
                "candidate_scope": candidate_scope,
                "evidence_admission_score": score,
                "evidence_risk_score": 1.0 - score,
                "route_label": route_label,
                "route_reason": route_reason,
                "descriptor_similarity_percentile": 0.5,
                "descriptor_source_note": "neutral_descriptor_percentile_for_unlabeled_bobcat_transfer_stress",
                "claim_boundary": "Bobcat transfer-stress only; no identity accuracy or same/different labels.",
            }
        )
    summary = []
    for scope in sorted({row["pair_scope"] for row in routed}):
        subset = [row for row in routed if row["pair_scope"] == scope]
        counts = Counter(row["route_label"] for row in subset)
        n = len(subset)
        mean_score = sum(float(row["evidence_admission_score"]) for row in subset) / n
        summary.append(
            {
                "pair_scope": scope,
                "pair_count": n,
                "mean_evidence_admission_score": mean_score,
                "mean_evidence_risk_score": 1.0 - mean_score,
                "accept_review_rate": counts["accept_review"] / n,
                "cautious_review_rate": counts["cautious_review"] / n,
                "defer_low_evidence_rate": counts["defer_low_evidence"] / n,
                "conflict_review_rate": counts["conflict_review"] / n,
                "expected_human_review_burden_rate": (n - counts["accept_review"]) / n,
                "calibration_drift_mean_score_vs_czechlynx": mean_score - czech_mean_score,
                "claim_boundary": "Transfer-stress evidence burden only; no Bobcat identity metric.",
            }
        )
    audit = {
        "built_at_utc": utc_now(),
        "status": "PASS" if routed and all(row["descriptor_similarity_percentile"] == 0.5 for row in routed) else "FAIL",
        "input_feature_table_csv": project_relative(FEATURE_TABLE_CSV),
        "input_validation_table_csv": project_relative(VALIDATION_TABLE_CSV),
        "input_thresholds_json": project_relative(THRESHOLDS_JSON),
        "routed_pairs_csv": project_relative(BOBCAT_ROUTED_CSV),
        "summary_csv": project_relative(SUMMARY_CSV),
        "bobcat_pair_rows": len(routed),
        "route_counts": dict(sorted(Counter(row["route_label"] for row in routed).items())),
        "pair_scope_counts": dict(sorted(Counter(row["pair_scope"] for row in routed).items())),
        "czechlynx_training_mean_evidence_admission_score": czech_mean_score,
        "accept_threshold_alpha_0_15": accept_threshold,
        "cautious_threshold_alpha_0_30": cautious_threshold,
        "descriptor_conflict_enrichment_status": "not_estimable_without_bobcat_returned_pair_descriptor_scores",
        "blocked_claims": ["Bobcat identity accuracy", "Bobcat false-match accuracy", "Bobcat mAP/MRR/top-k identity retrieval"],
        "claim_boundary": "Bobcat transfer/evidence-stress diagnostics only.",
    }
    write_csv(BOBCAT_ROUTED_CSV, routed, ROUTED_COLUMNS)
    write_csv(SUMMARY_CSV, summary, SUMMARY_COLUMNS)
    write_json(AUDIT_JSON, audit)
    write_report(audit)
    return audit


def write_report(audit: dict[str, Any]) -> None:
    route_counts = json.dumps(audit["route_counts"], sort_keys=True)
    pair_scope_counts = json.dumps(audit["pair_scope_counts"], sort_keys=True)
    REPORT_MD.write_text(
        "# Bobcat Wild/Urban Transfer Stress\n\n"
        f"Status: `{audit['status']}`\n\n"
        "This module applies the PF-ERI evidence router to unlabeled Bobcat wild/urban transfer pairs.\n\n"
        "## Scope\n\n"
        f"- Bobcat transfer-stress pair rows: `{audit['bobcat_pair_rows']}`\n"
        f"- Pair scope counts: `{pair_scope_counts}`\n"
        f"- Route counts: `{route_counts}`\n"
        f"- Descriptor conflict enrichment: `{audit['descriptor_conflict_enrichment_status']}`\n\n"
        "## Boundary\n\n"
        f"{audit['claim_boundary']} Bobcat identity accuracy remains blocked.\n",
        encoding="utf-8",
    )


def main() -> int:
    audit = build()
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
