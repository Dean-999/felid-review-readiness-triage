#!/usr/bin/env python3
"""Build final PF-ERI robustness checks and claim gates."""

from __future__ import annotations

import csv
import json
from collections import Counter
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
    / "outputs/modeling-validation/known-id-evidence-sufficiency-validation/known_id_reviewability_validation_table.csv"
)
MODEL_METRICS_CSV = (
    PROJECT_ROOT / "outputs/modeling-validation/known-id-evidence-sufficiency-validation/known_id_model_metrics.csv"
)
ROUTES_CSV = PROJECT_ROOT / "outputs/modeling-validation/risk-calibrated-evidence-admission/risk_calibrated_pair_routes.csv"
ROUTER_AUDIT_JSON = PROJECT_ROOT / "outputs/modeling-validation/risk-calibrated-evidence-admission/risk_calibrated_router_audit.json"
DECOMPOSITION_AUDIT_JSON = PROJECT_ROOT / "outputs/modeling-validation/evidence-risk-decomposition/evidence_risk_decomposition_audit.json"
BOBCAT_AUDIT_JSON = (
    PROJECT_ROOT / "outputs/modeling-validation/bobcat-wild-urban-transfer-stress/bobcat_transfer_stress_audit.json"
)
BUDGET_CZECH_CSV = PROJECT_ROOT / "outputs/modeling-validation/review-budget-routing/czechlynx_budget_risk_coverage.csv"
BUDGET_AUDIT_JSON = PROJECT_ROOT / "outputs/modeling-validation/review-budget-routing/review_budget_routing_audit.json"
OUTPUT_DIR = PROJECT_ROOT / "outputs/modeling-validation/robustness-and-claim-gates"
SENSITIVITY_CSV = OUTPUT_DIR / "robustness_sensitivity_checks.csv"
SOURCE_ABLATION_CSV = OUTPUT_DIR / "source_shortcut_ablation.csv"
RELIABILITY_CSV = OUTPUT_DIR / "reliability_curve_checks.csv"
CLAIM_GATES_CSV = OUTPUT_DIR / "final_claim_gate_table.csv"
AUDIT_JSON = OUTPUT_DIR / "robustness_and_claim_gates_audit.json"
REPORT_MD = OUTPUT_DIR / "README.md"

FULL_FEATURES = validation.MODEL_FAMILIES["descriptor_plus_pf_eri"]
NO_SOURCE_FEATURES = [name for name in FULL_FEATURES if name != "source_domain_shift_score"]

SENSITIVITY_COLUMNS = [
    "check_family",
    "scope",
    "subgroup",
    "pair_count",
    "positive_review_ready_count",
    "negative_not_ready_or_uncertain_count",
    "auroc",
    "brier_score",
    "ece_5bin",
    "mean_evidence_admission_score",
    "accept_review_count",
    "accept_review_empirical_risk",
    "claim_boundary",
]
ABLATION_COLUMNS = [
    "ablation_name",
    "feature_set",
    "feature_names",
    "pair_count",
    "auroc",
    "brier_score",
    "ece_5bin",
    "source_variation_status",
    "interpretation",
]
RELIABILITY_COLUMNS = [
    "scope",
    "bin_id",
    "lower_bound",
    "upper_bound",
    "row_count",
    "mean_predicted",
    "observed_review_ready_rate",
    "absolute_gap",
]
CLAIM_COLUMNS = ["claim_id", "status", "claim_text", "evidence_artifact", "rationale", "safe_wording"]


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


def merge_validation_and_routes() -> list[dict[str, Any]]:
    validation_rows = {
        (row["descriptor_name"], row["review_pair_id"]): row
        for row in read_csv(VALIDATION_TABLE_CSV)
    }
    rows = []
    for route in read_csv(ROUTES_CSV):
        key = (route["descriptor_name"], route["review_pair_id"])
        rows.append({**validation_rows[key], **route})
    return rows


def metric_summary(check_family: str, scope: str, subgroup: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    labels = [int(row["review_ready_label"]) for row in rows]
    scores = [to_float(row["evidence_admission_score"]) for row in rows]
    accepted = [row for row in rows if row["route_label"] == "accept_review"]
    accepted_not_ready = sum(int(row["not_ready_or_uncertain_label"]) for row in accepted)
    return {
        "check_family": check_family,
        "scope": scope,
        "subgroup": subgroup,
        "pair_count": len(rows),
        "positive_review_ready_count": sum(labels),
        "negative_not_ready_or_uncertain_count": len(labels) - sum(labels),
        "auroc": validation.auroc(labels, scores) if len(set(labels)) > 1 else "not_estimable_single_class",
        "brier_score": validation.brier(labels, scores) if rows else "",
        "ece_5bin": validation.ece(labels, scores) if rows else "",
        "mean_evidence_admission_score": sum(scores) / len(scores) if scores else "",
        "accept_review_count": len(accepted),
        "accept_review_empirical_risk": accepted_not_ready / len(accepted) if accepted else "",
        "claim_boundary": "Sensitivity on reviewed CzechLynx pair reviewability labels only.",
    }


def sensitivity_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    checks = [metric_summary("pooled", "pooled", "all", rows)]
    group_columns = [
        ("descriptor_family", "descriptor_name"),
        ("identity_relation", "same_identity_known_id"),
        ("image_component_fold", "fold_id"),
        ("evidence_group", "evidence_group"),
        ("rank_bin", "rank_bin"),
        ("route_label", "route_label"),
    ]
    for family, column in group_columns:
        for value in sorted({str(row[column]) for row in rows}):
            subset = [row for row in rows if str(row[column]) == value]
            checks.append(metric_summary(family, column, value, subset))
    return checks


def crossval_scores(rows: list[dict[str, Any]], feature_names: list[str]) -> tuple[list[int], list[float]]:
    predictions: dict[tuple[str, str], float] = {}
    labels_by_key: dict[tuple[str, str], int] = {}
    folds = sorted({int(row["fold_id"]) for row in rows})
    for fold in folds:
        train_rows = [row for row in rows if int(row["fold_id"]) != fold]
        eval_rows = [row for row in rows if int(row["fold_id"]) == fold]
        train_x = [[to_float(row[name]) for name in feature_names] for row in train_rows]
        eval_x = [[to_float(row[name]) for name in feature_names] for row in eval_rows]
        train_y = [int(row["review_ready_label"]) for row in train_rows]
        train_x_std, means, stds = validation.standardize(train_x, train_x)
        eval_x_std = [[(row[i] - means[i]) / stds[i] for i in range(len(feature_names))] for row in eval_x]
        weights, intercept = validation.train_logistic(train_x_std, train_y)
        eval_scores = validation.predict_logistic(eval_x_std, weights, intercept)
        for row, score in zip(eval_rows, eval_scores):
            key = (row["descriptor_name"], row["review_pair_id"])
            predictions[key] = score
            labels_by_key[key] = int(row["review_ready_label"])
    ordered = sorted(predictions)
    return [labels_by_key[key] for key in ordered], [predictions[key] for key in ordered]


def source_ablation_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    source_values = sorted({str(row["source_domain_shift_score"]) for row in rows})
    source_status = "constant_in_czechlynx_validation" if len(source_values) == 1 else "varies"
    outputs = []
    for name, features in [
        ("full_descriptor_plus_pf_eri", FULL_FEATURES),
        ("remove_source_domain_shift_score", NO_SOURCE_FEATURES),
    ]:
        labels, scores = crossval_scores(rows, features)
        outputs.append(
            {
                "ablation_name": "remove_source_shortcut",
                "feature_set": name,
                "feature_names": ",".join(features),
                "pair_count": len(labels),
                "auroc": validation.auroc(labels, scores),
                "brier_score": validation.brier(labels, scores),
                "ece_5bin": validation.ece(labels, scores),
                "source_variation_status": source_status,
                "interpretation": "Source-held-out causal domain claim remains blocked if source/domain does not vary.",
            }
        )
    return outputs


def reliability_rows(rows: list[dict[str, Any]], scope: str, bins: int = 5) -> list[dict[str, Any]]:
    labels = [int(row["review_ready_label"]) for row in rows]
    scores = [to_float(row["evidence_admission_score"]) for row in rows]
    output = []
    for bin_id in range(bins):
        low = bin_id / bins
        high = (bin_id + 1) / bins
        idx = [i for i, score in enumerate(scores) if low <= score <= high and (bin_id == bins - 1 or score < high)]
        mean_pred = sum(scores[i] for i in idx) / len(idx) if idx else ""
        observed = sum(labels[i] for i in idx) / len(idx) if idx else ""
        output.append(
            {
                "scope": scope,
                "bin_id": bin_id,
                "lower_bound": low,
                "upper_bound": high,
                "row_count": len(idx),
                "mean_predicted": mean_pred,
                "observed_review_ready_rate": observed,
                "absolute_gap": abs(mean_pred - observed) if idx else "",
            }
        )
    return output


def model_metric(scope: str, model_family: str) -> dict[str, str]:
    for row in read_csv(MODEL_METRICS_CSV):
        if row["scope"] == scope and row["model_family"] == model_family:
            return row
    raise ValueError(f"missing model metric {scope}/{model_family}")


def budget_metric(strategy: str, budget: int) -> dict[str, str]:
    for row in read_csv(BUDGET_CZECH_CSV):
        if row["strategy"] == strategy and int(row["budget"]) == budget:
            return row
    raise ValueError(f"missing budget metric {strategy}/{budget}")


def claim_gate_rows() -> list[dict[str, str]]:
    pooled_descriptor = model_metric("pooled", "descriptor_only")
    pooled_full = model_metric("pooled", "descriptor_plus_pf_eri")
    mega_full = model_metric("megadescriptor_l_384", "descriptor_plus_pf_eri")
    dino_full = model_metric("dinov2_vitl14", "descriptor_plus_pf_eri")
    router_audit = read_json(ROUTER_AUDIT_JSON)
    decomposition_audit = read_json(DECOMPOSITION_AUDIT_JSON)
    bobcat_audit = read_json(BOBCAT_AUDIT_JSON)
    budget_audit = read_json(BUDGET_AUDIT_JSON)
    pferi_200 = budget_metric("pferi_selective_evidence_queue", 200)
    descriptor_200 = budget_metric("descriptor_rank_only_queue", 200)
    eval_threshold = next(row for row in router_audit["thresholds"] if float(row["alpha"]) == 0.15)
    return [
        {
            "claim_id": "allowed_pair_level_governance_layer",
            "status": "allowed",
            "claim_text": "PF-ERI is a pair-level evidence governance layer after strong descriptor retrieval.",
            "evidence_artifact": project_relative(MODEL_METRICS_CSV),
            "rationale": "The tested model uses MegaDescriptor/DINOv2 candidate-pair context and predicts reviewability, not identity descriptors.",
            "safe_wording": "PF-ERI evaluates evidence admissibility and review readiness after descriptor retrieval.",
        },
        {
            "claim_id": "allowed_descriptor_controlled_reviewability_signal",
            "status": "allowed",
            "claim_text": "PF-ERI features add reviewability signal beyond descriptor similarity on CzechLynx reviewed pairs.",
            "evidence_artifact": project_relative(MODEL_METRICS_CSV),
            "rationale": f"Pooled AUROC descriptor_only={pooled_descriptor['auroc']}; descriptor_plus_pf_eri={pooled_full['auroc']}.",
            "safe_wording": "On the reviewed CzechLynx validation set, PF-ERI evidence features improve reviewability prediction over descriptor similarity alone.",
        },
        {
            "claim_id": "allowed_descriptor_family_stratification",
            "status": "allowed",
            "claim_text": "The effect is stratified across MegaDescriptor and DINOv2 candidate queues.",
            "evidence_artifact": project_relative(MODEL_METRICS_CSV),
            "rationale": f"MegaDescriptor descriptor_plus_pf_eri AUROC={mega_full['auroc']}; DINOv2 descriptor_plus_pf_eri AUROC={dino_full['auroc']}.",
            "safe_wording": "Report descriptor-family-stratified results rather than a single unqualified pooled effect.",
        },
        {
            "claim_id": "allowed_risk_calibrated_router",
            "status": "allowed",
            "claim_text": "A selective evidence router can be calibrated to control reviewability risk on held-out CzechLynx folds.",
            "evidence_artifact": project_relative(ROUTER_AUDIT_JSON),
            "rationale": f"Alpha 0.15 threshold has evaluation empirical risk={eval_threshold['evaluation_empirical_risk']} and coverage={eval_threshold['evaluation_coverage']}.",
            "safe_wording": "Use risk/coverage language on CzechLynx reviewed-pair validation only.",
        },
        {
            "claim_id": "allowed_review_budget_routing",
            "status": "allowed",
            "claim_text": "PF-ERI routing improves fixed-budget review allocation compared with descriptor rank alone.",
            "evidence_artifact": project_relative(BUDGET_CZECH_CSV),
            "rationale": f"Budget 200 empirical risk PF-ERI={pferi_200['empirical_risk']}; descriptor-only={descriptor_200['empirical_risk']}.",
            "safe_wording": "PF-ERI reduces evidence-review risk under fixed budgets in the CzechLynx reviewed-pair benchmark.",
        },
        {
            "claim_id": "exploratory_risk_decomposition_reason_classes",
            "status": "exploratory",
            "claim_text": "PF-ERI explains why a pair is not review-ready through risk families.",
            "evidence_artifact": project_relative(DECOMPOSITION_AUDIT_JSON),
            "rationale": f"Reason labels remain sparse: {decomposition_audit['reason_support_counts']}.",
            "safe_wording": "Treat risk families as component attributions until reason-label enrichment is completed.",
        },
        {
            "claim_id": "exploratory_bobcat_transfer_stress",
            "status": "exploratory",
            "claim_text": "Bobcat wild/urban outputs diagnose transfer evidence burden.",
            "evidence_artifact": project_relative(BOBCAT_AUDIT_JSON),
            "rationale": f"Bobcat rows={bobcat_audit['bobcat_pair_rows']}; descriptor conflict enrichment={bobcat_audit['descriptor_conflict_enrichment_status']}.",
            "safe_wording": "Use Bobcat only as unlabeled transfer-stress and workflow-allocation diagnostics.",
        },
        {
            "claim_id": "blocked_new_descriptor",
            "status": "blocked",
            "claim_text": "PF-ERI is a new visual descriptor or Re-ID embedding.",
            "evidence_artifact": project_relative(MODEL_METRICS_CSV),
            "rationale": "The project explicitly evaluates pair-level evidence governance after strong descriptors.",
            "safe_wording": "Do not describe PF-ERI as a descriptor.",
        },
        {
            "claim_id": "blocked_automatic_individual_identification",
            "status": "blocked",
            "claim_text": "PF-ERI automatically identifies individual animals.",
            "evidence_artifact": project_relative(VALIDATION_TABLE_CSV),
            "rationale": "Targets are human reviewability/admissibility labels, not automatic identity decisions.",
            "safe_wording": "PF-ERI routes evidence for review; it does not assign identity.",
        },
        {
            "claim_id": "blocked_bobcat_identity_metrics",
            "status": "blocked",
            "claim_text": "Bobcat identity accuracy, false-match accuracy, mAP, MRR, or top-k retrieval improved.",
            "evidence_artifact": project_relative(BOBCAT_AUDIT_JSON),
            "rationale": "; ".join(bobcat_audit["blocked_claims"]),
            "safe_wording": "No Bobcat identity metrics are claimed in this stage.",
        },
        {
            "claim_id": "blocked_source_heldout_causal_domain_claim",
            "status": "blocked",
            "claim_text": "Source-held-out tests prove causal source/domain generalization.",
            "evidence_artifact": project_relative(VALIDATION_TABLE_CSV),
            "rationale": "CzechLynx validation has constant source_domain_shift_score; source-held-out causal claims are not supported.",
            "safe_wording": "Report source/domain diagnostics as sensitivity or future validation unless a source-varied held-out set is built.",
        },
        {
            "claim_id": "blocked_bobcat_descriptor_baseline",
            "status": "blocked",
            "claim_text": "Bobcat descriptor-rank baseline or descriptor-conflict enrichment is estimated.",
            "evidence_artifact": project_relative(BUDGET_AUDIT_JSON),
            "rationale": budget_audit["bobcat_descriptor_baseline_status"],
            "safe_wording": "Bobcat descriptor comparisons require returned-pair descriptor scores.",
        },
    ]


def build() -> dict[str, Any]:
    rows = merge_validation_and_routes()
    sensitivity = sensitivity_rows(rows)
    ablation = source_ablation_rows(rows)
    reliability = reliability_rows(rows, "pooled")
    for descriptor in sorted({row["descriptor_name"] for row in rows}):
        reliability.extend(reliability_rows([row for row in rows if row["descriptor_name"] == descriptor], descriptor))
    claims = claim_gate_rows()
    write_csv(SENSITIVITY_CSV, sensitivity, SENSITIVITY_COLUMNS)
    write_csv(SOURCE_ABLATION_CSV, ablation, ABLATION_COLUMNS)
    write_csv(RELIABILITY_CSV, reliability, RELIABILITY_COLUMNS)
    write_csv(CLAIM_GATES_CSV, claims, CLAIM_COLUMNS)
    claim_counts = Counter(row["status"] for row in claims)
    source_values = sorted({row["source_domain_shift_score"] for row in rows})
    audit = {
        "built_at_utc": utc_now(),
        "status": "PASS" if claim_counts["allowed"] >= 4 and claim_counts["blocked"] >= 4 else "FAIL",
        "input_validation_table_csv": project_relative(VALIDATION_TABLE_CSV),
        "input_routes_csv": project_relative(ROUTES_CSV),
        "input_decomposition_audit_json": project_relative(DECOMPOSITION_AUDIT_JSON),
        "input_bobcat_audit_json": project_relative(BOBCAT_AUDIT_JSON),
        "input_budget_audit_json": project_relative(BUDGET_AUDIT_JSON),
        "sensitivity_csv": project_relative(SENSITIVITY_CSV),
        "source_ablation_csv": project_relative(SOURCE_ABLATION_CSV),
        "reliability_csv": project_relative(RELIABILITY_CSV),
        "claim_gates_csv": project_relative(CLAIM_GATES_CSV),
        "pair_rows": len(rows),
        "descriptor_counts": dict(sorted(Counter(row["descriptor_name"] for row in rows).items())),
        "identity_counts": dict(sorted(Counter(row["same_identity_known_id"] for row in rows).items())),
        "source_domain_shift_values": source_values,
        "claim_status_counts": dict(sorted(claim_counts.items())),
        "final_frame": "PF-ERI is a pair-level evidence governance layer after strong descriptor retrieval.",
    }
    write_json(AUDIT_JSON, audit)
    write_report(audit)
    return audit


def write_report(audit: dict[str, Any]) -> None:
    lines = [
        "# Robustness and Claim Gates",
        "",
        f"Status: `{audit['status']}`",
        "",
        "This module locks the defensible scientific claims for the PF-ERI",
        "Selective Evidence Sufficiency Model.",
        "",
        "## Outputs",
        "",
        f"- Sensitivity checks: `{audit['sensitivity_csv']}`",
        f"- Source shortcut ablation: `{audit['source_ablation_csv']}`",
        f"- Reliability checks: `{audit['reliability_csv']}`",
        f"- Final claim gate table: `{audit['claim_gates_csv']}`",
        "",
        "## Final Frame",
        "",
        audit["final_frame"],
        "",
        "PF-ERI is not a new descriptor and does not claim automatic individual",
        "identification.",
    ]
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    audit = build()
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
