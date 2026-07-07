#!/usr/bin/env python3
"""Build final advanced mathematical claim gates and Methods-ready report."""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ADVANCED_DIR = PROJECT_ROOT / "outputs/modeling-validation/advanced-mathematical-validation"
KNOWN_ID_DIR = PROJECT_ROOT / "outputs/modeling-validation/known-id-evidence-sufficiency-validation"
RISK_ROUTING_DIR = PROJECT_ROOT / "outputs/modeling-validation/risk-calibrated-evidence-admission"
DECOMPOSITION_DIR = PROJECT_ROOT / "outputs/modeling-validation/evidence-risk-decomposition"
BOBCAT_DIR = PROJECT_ROOT / "outputs/modeling-validation/bobcat-wild-urban-transfer-stress"
BUDGET_DIR = PROJECT_ROOT / "outputs/modeling-validation/review-budget-routing"

CONTRACT_AUDIT_JSON = ADVANCED_DIR / "advanced_mathematical_validation_contract_audit.json"
MODEL_METRICS_CSV = KNOWN_ID_DIR / "known_id_model_metrics.csv"
VALIDATION_TABLE_CSV = KNOWN_ID_DIR / "known_id_reviewability_validation_table.csv"
CONFORMAL_THRESHOLDS_CSV = ADVANCED_DIR / "conformal_selective_thresholds.csv"
CLUSTER_INTERVALS_CSV = ADVANCED_DIR / "cluster_bootstrap_metric_intervals.csv"
DESCRIPTOR_FLAGS_CSV = ADVANCED_DIR / "descriptor_stratified_calibration_flags.csv"
NONLINEAR_SENSITIVITY_CSV = ADVANCED_DIR / "nonlinear_evidence_sensitivity.csv"
NONLINEAR_AUDIT_JSON = ADVANCED_DIR / "feature_effect_monotonicity_audit.json"
DECOMPOSITION_AUDIT_JSON = DECOMPOSITION_DIR / "evidence_risk_decomposition_audit.json"
BOBCAT_AUDIT_JSON = BOBCAT_DIR / "bobcat_transfer_stress_audit.json"
BUDGET_CSV = BUDGET_DIR / "czechlynx_budget_risk_coverage.csv"
BUDGET_AUDIT_JSON = BUDGET_DIR / "review_budget_routing_audit.json"

CLAIM_GATES_CSV = ADVANCED_DIR / "final_advanced_claim_gate_table.csv"
METHODS_REPORT_MD = ADVANCED_DIR / "final_methods_ready_report.md"
ASSUMPTIONS_CSV = ADVANCED_DIR / "final_methods_assumptions_and_limitations.csv"
AUDIT_JSON = ADVANCED_DIR / "final_advanced_claim_gates_audit.json"

CLAIM_COLUMNS = [
    "claim_id",
    "status",
    "claim_family",
    "claim_text",
    "evidence_artifacts",
    "key_numbers",
    "rationale",
    "safe_wording",
    "prohibited_wording",
    "remaining_caveat",
]

ASSUMPTION_COLUMNS = [
    "assumption_id",
    "status",
    "methods_section",
    "statement",
    "why_it_matters",
    "required_wording",
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


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def metric_row(scope: str, model_family: str) -> dict[str, str]:
    for row in read_csv(MODEL_METRICS_CSV):
        if row["scope"] == scope and row["model_family"] == model_family:
            return row
    raise ValueError(f"missing model metric {scope}/{model_family}")


def threshold_row(alpha: float) -> dict[str, str]:
    for row in read_csv(CONFORMAL_THRESHOLDS_CSV):
        if to_float(row["alpha"]) == alpha:
            return row
    raise ValueError(f"missing conformal threshold alpha={alpha}")


def cluster_interval(metric: str, scope: str = "all", cluster_family: str = "query_image_cluster") -> dict[str, str]:
    for row in read_csv(CLUSTER_INTERVALS_CSV):
        if row["metric"] == metric and row["scope"] == scope and row["cluster_family"] == cluster_family:
            return row
    raise ValueError(f"missing cluster interval {cluster_family}/{scope}/{metric}")


def budget_row(strategy: str, alpha: float, budget: int) -> dict[str, str]:
    for row in read_csv(BUDGET_CSV):
        if row["strategy"] == strategy and to_float(row["alpha"]) == alpha and int(row["budget"]) == budget:
            return row
    raise ValueError(f"missing budget row {strategy}/alpha={alpha}/budget={budget}")


def descriptor_warning_text() -> str:
    flags = [row for row in read_csv(DESCRIPTOR_FLAGS_CSV) if row["severity"] == "warning"]
    return "; ".join(f"{row['descriptor_name']}:{row['flag_id']}={row['status']}" for row in flags)


def nonlinear_status_summary() -> str:
    rows = [row for row in read_csv(NONLINEAR_SENSITIVITY_CSV) if row["descriptor_name"] == "pooled"]
    statuses: dict[str, str] = {}
    for row in rows:
        statuses.setdefault(row["feature_name"], row["sensitivity_status"])
    return "; ".join(f"{feature}={status}" for feature, status in sorted(statuses.items()))


def claim_gate_rows() -> list[dict[str, Any]]:
    pooled_descriptor = metric_row("pooled", "descriptor_only")
    pooled_quality = metric_row("pooled", "quality_only")
    pooled_pferi = metric_row("pooled", "pf_eri_evidence_only")
    pooled_full = metric_row("pooled", "descriptor_plus_pf_eri")
    mega_full = metric_row("megadescriptor_l_384", "descriptor_plus_pf_eri")
    dino_full = metric_row("dinov2_vitl14", "descriptor_plus_pf_eri")
    alpha_015 = threshold_row(0.15)
    cluster_alpha_015 = cluster_interval("alpha_0_15_selective_risk")
    decomposition = read_json(DECOMPOSITION_AUDIT_JSON)
    bobcat = read_json(BOBCAT_AUDIT_JSON)
    budget = budget_row("pferi_risk_constrained_queue", 0.15, 100)
    descriptor_budget = budget_row("descriptor_rank_fixed_budget_unconstrained", 0.15, 100)
    budget_audit = read_json(BUDGET_AUDIT_JSON)
    nonlinear_audit = read_json(NONLINEAR_AUDIT_JSON)
    constant_features = [
        feature
        for feature, entry in nonlinear_audit["feature_variation"].items()
        if entry["estimability_status"] == "not_estimable_constant_feature"
    ]
    return [
        {
            "claim_id": "allowed_selective_evidence_inference_frame",
            "status": "allowed",
            "claim_family": "framing",
            "claim_text": "PF-ERI is a pair-level selective evidence inference layer after strong descriptor retrieval.",
            "evidence_artifacts": project_relative(CONTRACT_AUDIT_JSON),
            "key_numbers": "formal target=maximize accepted-pair coverage subject to selective evidence risk",
            "rationale": "The contract defines reviewability/evidence-admissibility as the target, downstream of MegaDescriptor and DINOv2 candidate queues.",
            "safe_wording": "PF-ERI governs whether retrieved candidate pairs are evidence-admissible and review-ready.",
            "prohibited_wording": "PF-ERI is a new descriptor; PF-ERI identifies animals automatically.",
            "remaining_caveat": "Frame as evidence governance, not identity assignment.",
        },
        {
            "claim_id": "allowed_descriptor_controlled_reviewability_signal",
            "status": "allowed",
            "claim_family": "predictive_validation",
            "claim_text": "PF-ERI features add reviewability signal beyond strong descriptor similarity on CzechLynx reviewed pairs.",
            "evidence_artifacts": project_relative(MODEL_METRICS_CSV),
            "key_numbers": (
                f"descriptor_only_AUROC={pooled_descriptor['auroc']}; "
                f"quality_only_AUROC={pooled_quality['auroc']}; "
                f"pf_eri_evidence_only_AUROC={pooled_pferi['auroc']}; "
                f"descriptor_plus_pf_eri_AUROC={pooled_full['auroc']}"
            ),
            "rationale": "PF-ERI evidence-only and descriptor+PF-ERI exceed descriptor-only and image-quality-only reviewability baselines.",
            "safe_wording": "On the CzechLynx reviewed validation set, PF-ERI evidence features improve reviewability prediction after descriptor retrieval.",
            "prohibited_wording": "PF-ERI improves identity matching accuracy or descriptor mAP.",
            "remaining_caveat": "Claim is reviewability/admissibility, not identity retrieval performance.",
        },
        {
            "claim_id": "allowed_descriptor_stratified_reporting",
            "status": "allowed_with_caveat",
            "claim_family": "descriptor_stratification",
            "claim_text": "Report MegaDescriptor and DINOv2 results separately rather than relying only on pooled metrics.",
            "evidence_artifacts": project_relative(DESCRIPTOR_FLAGS_CSV),
            "key_numbers": f"MegaDescriptor_full_AUROC={mega_full['auroc']}; DINOv2_full_AUROC={dino_full['auroc']}; warnings={descriptor_warning_text()}",
            "rationale": "Both descriptor families support the primary signal, but pooled alpha thresholds do not guarantee every descriptor family separately.",
            "safe_wording": "The signal is observed in both descriptor-family queues, with descriptor-specific calibration caveats.",
            "prohibited_wording": "The pooled alpha threshold controls risk for every descriptor family without qualification.",
            "remaining_caveat": "DINOv2 alpha=0.15 calibration selective risk exceeded alpha under the pooled threshold.",
        },
        {
            "claim_id": "allowed_empirical_selective_router",
            "status": "allowed_with_caveat",
            "claim_family": "risk_coverage",
            "claim_text": "A selective router can choose higher-coverage admitted sets under empirical calibration risk constraints.",
            "evidence_artifacts": project_relative(CONFORMAL_THRESHOLDS_CSV),
            "key_numbers": (
                f"alpha=0.15 calibration_risk={alpha_015['calibration_selective_risk']}; "
                f"evaluation_risk={alpha_015['evaluation_selective_risk']}; "
                f"evaluation_coverage={alpha_015['evaluation_coverage']}; "
                f"finite_sample_status={alpha_015['finite_sample_status']}"
            ),
            "rationale": "Thresholds are selected on calibration folds and evaluated separately, but Hoeffding upper bounds exceed target alpha.",
            "safe_wording": "Empirical CzechLynx calibration/evaluation risk-coverage routing is supported.",
            "prohibited_wording": "Distribution-free finite-sample guarantees are proven for all domains or Bobcat.",
            "remaining_caveat": "Finite-sample upper-bound support is not achieved in current sample sizes.",
        },
        {
            "claim_id": "allowed_cluster_uncertainty_report",
            "status": "allowed",
            "claim_family": "uncertainty",
            "claim_text": "Cluster-aware uncertainty intervals can be reported for key CzechLynx reviewability metrics.",
            "evidence_artifacts": project_relative(CLUSTER_INTERVALS_CSV),
            "key_numbers": (
                f"alpha_0.15_selective_risk={cluster_alpha_015['point_estimate']} "
                f"[{cluster_alpha_015['ci_lower']}, {cluster_alpha_015['ci_upper']}]; "
                f"cluster_count={cluster_alpha_015['cluster_count']}"
            ),
            "rationale": "Query-image clustered bootstrap is reportable for reviewed CzechLynx pairs.",
            "safe_wording": "Report cluster-aware uncertainty as validation uncertainty for CzechLynx reviewed pairs.",
            "prohibited_wording": "These intervals validate Bobcat identity performance.",
            "remaining_caveat": "Component-group intervals remain sparse and identity-cluster bootstrap is not feasible without identity labels.",
        },
        {
            "claim_id": "allowed_nonlinear_sensitivity_partial",
            "status": "allowed_with_caveat",
            "claim_family": "feature_sensitivity",
            "claim_text": "Binned nonlinear sensitivity is estimable for body overlap and cross-descriptor agreement, but not for constant features.",
            "evidence_artifacts": project_relative(NONLINEAR_SENSITIVITY_CSV),
            "key_numbers": nonlinear_status_summary(),
            "rationale": "Only two core features vary enough for binned sensitivity; constant features cannot support nonlinear effect claims.",
            "safe_wording": "Report nonlinear sensitivity only for estimable features and mark constant features as design/data limitations.",
            "prohibited_wording": "All six PF-ERI features have validated nonlinear effects.",
            "remaining_caveat": f"Constant features: {', '.join(sorted(constant_features))}.",
        },
        {
            "claim_id": "allowed_predicted_risk_budget_optimization",
            "status": "allowed_with_caveat",
            "claim_family": "workflow_optimization",
            "claim_text": "Review budget allocation can be formulated as predicted-risk constrained optimization.",
            "evidence_artifacts": project_relative(BUDGET_CSV),
            "key_numbers": (
                f"alpha=0.15 B=100 PF-ERI selected={budget['selected_count']} "
                f"mean_predicted_risk={budget['mean_predicted_evidence_risk']} empirical_risk={budget['empirical_risk']}; "
                f"descriptor_unconstrained_predicted_risk={descriptor_budget['mean_predicted_evidence_risk']}"
            ),
            "rationale": "The optimizer uses predicted risk for selection and human labels only for post-selection audit.",
            "safe_wording": "PF-ERI supports predicted-risk constrained review-budget allocation.",
            "prohibited_wording": "The budget optimizer provides a new finite-sample conformal guarantee.",
            "remaining_caveat": budget_audit["selection_leakage_guard"],
        },
        {
            "claim_id": "exploratory_component_risk_decomposition",
            "status": "exploratory",
            "claim_family": "risk_decomposition",
            "claim_text": "Risk family outputs can be used as component attribution for why evidence may be weak.",
            "evidence_artifacts": project_relative(DECOMPOSITION_AUDIT_JSON),
            "key_numbers": f"reason_label_enrichment_needed={decomposition['reason_label_enrichment_needed']}; support={decomposition['reason_support_counts']}",
            "rationale": "Current labels support component attribution, not validated human reason classification.",
            "safe_wording": "Use risk families as component attributions and motivation for reason-label enrichment.",
            "prohibited_wording": "PF-ERI has fully validated reason-class explanations.",
            "remaining_caveat": "Reason-label enrichment remains required for stronger explanation claims.",
        },
        {
            "claim_id": "exploratory_bobcat_transfer_workflow",
            "status": "exploratory",
            "claim_family": "transfer_stress",
            "claim_text": "Bobcat outputs can be used for unlabeled workflow allocation and transfer-stress diagnostics.",
            "evidence_artifacts": project_relative(BOBCAT_AUDIT_JSON),
            "key_numbers": f"bobcat_pair_rows={bobcat['bobcat_pair_rows']}; route_counts={bobcat['route_counts']}",
            "rationale": "Bobcat lacks audited same/different identity and reviewability labels in this workflow.",
            "safe_wording": "Bobcat is an unlabeled transfer-stress/workflow allocation analysis.",
            "prohibited_wording": "Bobcat identity accuracy, mAP, MRR, top-k, or false-match accuracy improved.",
            "remaining_caveat": "Do not report Bobcat identity metrics until labels exist.",
        },
        {
            "claim_id": "blocked_new_descriptor",
            "status": "blocked",
            "claim_family": "overclaim",
            "claim_text": "PF-ERI is a new descriptor or embedding.",
            "evidence_artifacts": project_relative(CONTRACT_AUDIT_JSON),
            "key_numbers": "descriptor role=upstream control/baseline",
            "rationale": "PF-ERI consumes descriptor queues and governs pair evidence.",
            "safe_wording": "PF-ERI is downstream of descriptors.",
            "prohibited_wording": "new descriptor; new embedding; replaces MegaDescriptor/DINOv2",
            "remaining_caveat": "None; this claim is blocked.",
        },
        {
            "claim_id": "blocked_automatic_identity_assignment",
            "status": "blocked",
            "claim_family": "overclaim",
            "claim_text": "PF-ERI automatically identifies individual animals.",
            "evidence_artifacts": project_relative(VALIDATION_TABLE_CSV),
            "key_numbers": "target label=review_ready/not_ready_or_uncertain",
            "rationale": "The modeled target is evidence admissibility/reviewability, not identity assignment.",
            "safe_wording": "PF-ERI routes candidate pairs for review.",
            "prohibited_wording": "automatic ID; individual recognition; assigns identity",
            "remaining_caveat": "None; this claim is blocked.",
        },
        {
            "claim_id": "blocked_bobcat_identity_metrics",
            "status": "blocked",
            "claim_family": "overclaim",
            "claim_text": "PF-ERI improves Bobcat identity accuracy, false-match accuracy, mAP, MRR, or top-k retrieval.",
            "evidence_artifacts": project_relative(BOBCAT_AUDIT_JSON),
            "key_numbers": "; ".join(bobcat["blocked_claims"]),
            "rationale": "Bobcat labels are not sufficient for identity metrics in this workflow.",
            "safe_wording": "Bobcat is workflow/transfer-stress only.",
            "prohibited_wording": "Bobcat identity accuracy; Bobcat mAP; Bobcat top-k",
            "remaining_caveat": "Blocked until audited Bobcat identity labels exist.",
        },
        {
            "claim_id": "blocked_source_heldout_causal_domain_generalization",
            "status": "blocked",
            "claim_family": "overclaim",
            "claim_text": "The current validation proves source-held-out causal domain generalization.",
            "evidence_artifacts": project_relative(NONLINEAR_AUDIT_JSON),
            "key_numbers": "source_domain_shift_score unique=1 in current CzechLynx validation",
            "rationale": "The supervised validation table does not contain source/domain variation for source-held-out causal claims.",
            "safe_wording": "Source/domain results are diagnostics and future validation targets.",
            "prohibited_wording": "causal domain generalization proven; source-held-out guarantee",
            "remaining_caveat": "Requires source-varied held-out validation.",
        },
        {
            "claim_id": "blocked_validated_reason_classification",
            "status": "blocked",
            "claim_family": "overclaim",
            "claim_text": "PF-ERI has validated not-ready reason classification.",
            "evidence_artifacts": project_relative(DECOMPOSITION_AUDIT_JSON),
            "key_numbers": f"reason_support_counts={decomposition['reason_support_counts']}",
            "rationale": "Current reason outputs are component attributions without human reason labels.",
            "safe_wording": "Risk decomposition is component attribution.",
            "prohibited_wording": "validated reason classifier; proven explanation classes",
            "remaining_caveat": "Requires explicit human not-ready reason labels.",
        },
        {
            "claim_id": "blocked_unqualified_distribution_free_claim",
            "status": "blocked",
            "claim_family": "overclaim",
            "claim_text": "The current router provides unqualified distribution-free risk control across domain shift.",
            "evidence_artifacts": project_relative(CONFORMAL_THRESHOLDS_CSV),
            "key_numbers": f"alpha=0.15 finite_sample_status={alpha_015['finite_sample_status']}",
            "rationale": "Hoeffding upper risk exceeds alpha and Bobcat shift is outside the calibration claim scope.",
            "safe_wording": "Use empirical calibration/evaluation risk-coverage language with stated assumptions.",
            "prohibited_wording": "distribution-free guarantee across Bobcat/domain shift",
            "remaining_caveat": "Requires stronger calibration design and assumptions.",
        },
    ]


def assumption_rows() -> list[dict[str, str]]:
    return [
        {
            "assumption_id": "target_definition",
            "status": "locked",
            "methods_section": "Outcome",
            "statement": "y(p)=1 denotes not-ready-or-uncertain evidence risk; review-ready is the complement.",
            "why_it_matters": "Prevents identity-matching language from replacing the actual supervised target.",
            "required_wording": "The model predicts evidence admissibility/reviewability, not identity.",
        },
        {
            "assumption_id": "strong_descriptor_position",
            "status": "locked",
            "methods_section": "Candidate Generation",
            "statement": "MegaDescriptor and DINOv2 are upstream candidate-queue descriptors.",
            "why_it_matters": "PF-ERI is not competing as a descriptor.",
            "required_wording": "PF-ERI operates after strong descriptor retrieval.",
        },
        {
            "assumption_id": "risk_coverage",
            "status": "empirical_only",
            "methods_section": "Selective Routing",
            "statement": "Selective risk is the not-ready-or-uncertain rate among admitted pairs; coverage is the admitted fraction.",
            "why_it_matters": "Keeps alpha-level claims tied to calibration/evaluation artifacts.",
            "required_wording": "Report empirical calibration/evaluation risk separately from finite-sample diagnostics.",
        },
        {
            "assumption_id": "uncertainty",
            "status": "reportable_with_scope",
            "methods_section": "Uncertainty",
            "statement": "Query-image cluster bootstrap intervals are reportable for CzechLynx reviewed pairs.",
            "why_it_matters": "Pair rows are not fully independent.",
            "required_wording": "Use cluster-aware uncertainty for CzechLynx reviewability only.",
        },
        {
            "assumption_id": "budget_optimization",
            "status": "predicted_risk_only",
            "methods_section": "Review Budget",
            "statement": "Budget allocation constrains mean predicted evidence risk, not post-hoc label risk.",
            "why_it_matters": "Avoids selection leakage from human labels.",
            "required_wording": "Human labels are reserved for post-selection empirical audits.",
        },
        {
            "assumption_id": "reason_labels",
            "status": "required_for_stronger_claim",
            "methods_section": "Risk Decomposition",
            "statement": "Validated reason classification requires explicit human reason labels.",
            "why_it_matters": "Current decomposition is component attribution.",
            "required_wording": "Reason-label enrichment remains future work before stronger explanation claims.",
        },
    ]


def write_methods_report(path: Path, claims: list[dict[str, Any]], assumptions: list[dict[str, str]]) -> None:
    status_counts = Counter(row["status"] for row in claims)
    allowed = [row for row in claims if row["status"].startswith("allowed")]
    exploratory = [row for row in claims if row["status"] == "exploratory"]
    blocked = [row for row in claims if row["status"] == "blocked"]
    lines = [
        "# PF-ERI Advanced Methods and Claim Gates",
        "",
        "## Final Framing",
        "",
        "PF-ERI is a selective evidence inference layer for wildlife Re-ID candidate pairs after strong descriptor retrieval. It does not introduce a new descriptor and does not assign identity.",
        "",
        "## Mathematical Target",
        "",
        "For candidate pair `p=(x_i,x_j)`, the descriptor queue provides similarity context `s_d(p)`. PF-ERI estimates evidence risk `R_hat(p)=P(y=1|z(p),s_d(p))`, where `y=1` means not-ready-or-uncertain. A selective gate admits a pair when `R_hat(p)<=tau`. Coverage is the admitted fraction, and selective risk is the not-ready-or-uncertain rate among admitted pairs.",
        "",
        "## Loss and Risk Definitions",
        "",
        "`L(p)=1` when a pair admitted for review is not-ready-or-uncertain, and `L(p)=0` otherwise. For gate `g_tau(p)=1[R_hat(p)<=tau]`, coverage is `E[g_tau(p)]` and selective risk is `E[L(p) | g_tau(p)=1]`. Reported alpha-level routing is empirical calibration/evaluation risk unless a finite-sample upper-bound diagnostic is explicitly satisfied.",
        "",
        "## Calibration Procedure",
        "",
        "Thresholds are selected on calibration folds by maximizing admitted coverage subject to empirical selective risk no greater than target `alpha`. Evaluation folds are reported separately and are not used to choose thresholds. Current Hoeffding upper-risk diagnostics exceed alpha, so finite-sample distribution-free language remains blocked.",
        "",
        "## Uncertainty Procedure",
        "",
        "Uncertainty is reported with query-image cluster bootstrap intervals for CzechLynx reviewed pairs. Component-group intervals are diagnostic when sparse, and identity-cluster bootstrap is blocked until resolved identity labels are available.",
        "",
        "## Algorithm Steps",
        "",
        "1. Build strong descriptor candidate queues with MegaDescriptor and DINOv2 context.",
        "2. Extract image evidence, pair comparability, descriptor-conflict, and source/domain diagnostic features.",
        "3. Train/evaluate reviewability models on CzechLynx known-ID reviewed pairs.",
        "4. Choose empirical calibration thresholds for selective evidence routing.",
        "5. Report calibration/evaluation risk-coverage and cluster-aware uncertainty.",
        "6. Allocate review budget by maximizing predicted admissible evidence under a predicted-risk constraint.",
        "7. Keep Bobcat outputs as unlabeled transfer-stress/workflow diagnostics.",
        "",
        "## Claim Status Counts",
        "",
        f"`{dict(sorted(status_counts.items()))}`",
        "",
        "## Allowed Claims",
        "",
    ]
    for row in allowed:
        lines.append(f"- `{row['claim_id']}`: {row['safe_wording']} Key evidence: {row['key_numbers']}")
    lines.extend(["", "## Exploratory Claims", ""])
    for row in exploratory:
        lines.append(f"- `{row['claim_id']}`: {row['safe_wording']} Caveat: {row['remaining_caveat']}")
    lines.extend(["", "## Blocked Claims", ""])
    for row in blocked:
        lines.append(f"- `{row['claim_id']}`: prohibit `{row['prohibited_wording']}`. Safe wording: {row['safe_wording']}")
    lines.extend(["", "## Methods Assumptions", ""])
    for row in assumptions:
        lines.append(f"- `{row['assumption_id']}` ({row['status']}): {row['required_wording']}")
    lines.extend(
        [
            "",
            "## Required Limitation Paragraph",
            "",
            "Current evidence supports PF-ERI as a pair-level evidence governance layer for CzechLynx reviewed candidate pairs. Finite-sample distribution-free claims, Bobcat identity metrics, source-held-out causal domain generalization, and validated reason classification remain blocked until the corresponding labels and calibration designs exist.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build() -> dict[str, Any]:
    claims = claim_gate_rows()
    assumptions = assumption_rows()
    write_csv(CLAIM_GATES_CSV, claims, CLAIM_COLUMNS)
    write_csv(ASSUMPTIONS_CSV, assumptions, ASSUMPTION_COLUMNS)
    write_methods_report(METHODS_REPORT_MD, claims, assumptions)
    status_counts = Counter(row["status"] for row in claims)
    required_blocked = {
        "blocked_new_descriptor",
        "blocked_automatic_identity_assignment",
        "blocked_bobcat_identity_metrics",
        "blocked_source_heldout_causal_domain_generalization",
        "blocked_validated_reason_classification",
        "blocked_unqualified_distribution_free_claim",
    }
    present_blocked = {row["claim_id"] for row in claims if row["status"] == "blocked"}
    audit = {
        "generated_at": utc_now(),
        "status": "PASS" if required_blocked.issubset(present_blocked) and claims and assumptions else "FAIL",
        "input_files": {
            "contract": project_relative(CONTRACT_AUDIT_JSON),
            "model_metrics": project_relative(MODEL_METRICS_CSV),
            "conformal_thresholds": project_relative(CONFORMAL_THRESHOLDS_CSV),
            "cluster_intervals": project_relative(CLUSTER_INTERVALS_CSV),
            "descriptor_flags": project_relative(DESCRIPTOR_FLAGS_CSV),
            "nonlinear_sensitivity": project_relative(NONLINEAR_SENSITIVITY_CSV),
            "decomposition": project_relative(DECOMPOSITION_AUDIT_JSON),
            "bobcat": project_relative(BOBCAT_AUDIT_JSON),
            "budget": project_relative(BUDGET_CSV),
        },
        "output_files": {
            "claim_gates": project_relative(CLAIM_GATES_CSV),
            "assumptions": project_relative(ASSUMPTIONS_CSV),
            "methods_report": project_relative(METHODS_REPORT_MD),
            "audit": project_relative(AUDIT_JSON),
        },
        "claim_status_counts": dict(sorted(status_counts.items())),
        "required_blocked_claims": sorted(required_blocked),
        "reason_label_enrichment_required": True,
        "final_frame": "PF-ERI is a pair-level selective evidence inference layer after strong descriptor retrieval.",
        "claim_boundary": "Methods-ready claim gates for PF-ERI evidence governance; not identity assignment or descriptor replacement.",
    }
    write_json(AUDIT_JSON, audit)
    return audit


def main() -> int:
    audit = build()
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
