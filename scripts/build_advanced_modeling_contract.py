#!/usr/bin/env python3
"""Build the PF-ERI advanced mathematical validation contract."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs/modeling-validation/advanced-mathematical-validation"
CONTRACT_MD = OUTPUT_DIR / "advanced_mathematical_validation_contract.md"
INPUTS_CSV = OUTPUT_DIR / "advanced_validation_authoritative_inputs.csv"
OUTPUT_SCHEMA_JSON = OUTPUT_DIR / "advanced_validation_output_contract.json"
CLAIM_BOUNDARIES_CSV = OUTPUT_DIR / "advanced_validation_claim_boundaries.csv"
AUDIT_JSON = OUTPUT_DIR / "advanced_mathematical_validation_contract_audit.json"
REPORT_MD = OUTPUT_DIR / "README.md"

AUTHORITATIVE_INPUTS = [
    {
        "input_id": "final_modeling_bootstrap_contract",
        "path": "outputs/modeling-validation/final-modeling-bootstrap/final_modeling_contract.md",
        "role": "physical image freeze and base modeling scope",
        "required": "yes",
        "claim_use": "defines allowed species/domain cells and base blocked claims",
    },
    {
        "input_id": "pair_construction_index",
        "path": "outputs/modeling-validation/pair-construction/pair_construction_index.csv",
        "role": "candidate pair universe and pair-family definitions",
        "required": "yes",
        "claim_use": "defines CzechLynx supervised pairs and Bobcat transfer-stress pairs",
    },
    {
        "input_id": "pair_evidence_features",
        "path": "outputs/modeling-validation/evidence-feature-extraction/pair_evidence_features.csv",
        "role": "PF-ERI pair-level evidence feature table",
        "required": "yes",
        "claim_use": "defines image evidence, pair comparability, descriptor conflict, and source/domain stress predictors",
    },
    {
        "input_id": "known_id_reviewability_validation",
        "path": "outputs/modeling-validation/known-id-evidence-sufficiency-validation/known_id_reviewability_validation_table.csv",
        "role": "supervised CzechLynx reviewed-pair validation table",
        "required": "yes",
        "claim_use": "defines y(p)=not-ready-or-uncertain labels for supervised risk estimation",
    },
    {
        "input_id": "risk_calibrated_routes",
        "path": "outputs/modeling-validation/risk-calibrated-evidence-admission/risk_calibrated_pair_routes.csv",
        "role": "baseline selective evidence router output",
        "required": "yes",
        "claim_use": "defines existing evidence admission scores and route labels for advanced calibration",
    },
    {
        "input_id": "review_budget_routing",
        "path": "outputs/modeling-validation/review-budget-routing/czechlynx_budget_risk_coverage.csv",
        "role": "baseline fixed-budget PF-ERI versus descriptor-rank queue comparison",
        "required": "yes",
        "claim_use": "defines starting point for risk-constrained budget optimization",
    },
    {
        "input_id": "robustness_claim_gates",
        "path": "outputs/modeling-validation/robustness-and-claim-gates/final_claim_gate_table.csv",
        "role": "current allowed/exploratory/blocked claim baseline",
        "required": "yes",
        "claim_use": "prevents advanced validation from weakening existing claim boundaries",
    },
    {
        "input_id": "bobcat_transfer_stress_routes",
        "path": "outputs/modeling-validation/bobcat-wild-urban-transfer-stress/bobcat_transfer_stress_routed_pairs.csv",
        "role": "unlabeled Bobcat transfer/workflow diagnostics",
        "required": "yes",
        "claim_use": "supports transfer-stress allocation only, not Bobcat identity or conformal domain-shift guarantees",
    },
]

CLAIM_BOUNDARIES = [
    {
        "claim_id": "allowed_selective_evidence_admission",
        "status": "allowed",
        "statement": "PF-ERI may be framed as selective evidence admission after strong descriptor retrieval.",
        "safe_condition": "Use only pair-level evidence admissibility and review-readiness language.",
    },
    {
        "claim_id": "allowed_alpha_level_czechlynx_calibration",
        "status": "allowed_after_implementation",
        "statement": "Alpha-level risk-control statements may be made on CzechLynx calibration/evaluation splits.",
        "safe_condition": "Only after #16 implements threshold selection and reports calibration/evaluation risk separately.",
    },
    {
        "claim_id": "exploratory_bobcat_transfer_stress",
        "status": "exploratory",
        "statement": "Bobcat outputs may diagnose transfer-stress and review burden.",
        "safe_condition": "Do not present as Bobcat identity, retrieval, or distribution-free conformal validation.",
    },
    {
        "claim_id": "blocked_new_descriptor",
        "status": "blocked",
        "statement": "PF-ERI is a new descriptor or embedding.",
        "safe_condition": "PF-ERI remains downstream of MegaDescriptor, DINOv2, or other descriptor queues.",
    },
    {
        "claim_id": "blocked_automatic_identity_assignment",
        "status": "blocked",
        "statement": "PF-ERI automatically identifies individuals.",
        "safe_condition": "PF-ERI routes evidence for review; it does not assign identity.",
    },
    {
        "claim_id": "blocked_bobcat_identity_metrics",
        "status": "blocked",
        "statement": "PF-ERI improves Bobcat identity accuracy, false-match accuracy, mAP, MRR, or top-k retrieval.",
        "safe_condition": "Bobcat lacks the required reviewed identity labels in this workflow.",
    },
    {
        "claim_id": "blocked_unqualified_distribution_free_domain_shift",
        "status": "blocked",
        "statement": "Conformal guarantees hold unqualified under Bobcat domain shift.",
        "safe_condition": "Distribution-free language is limited to supported calibration assumptions and excludes Bobcat shift unless validated later.",
    },
]

OUTPUT_CONTRACT = {
    "output_root": "outputs/modeling-validation/advanced-mathematical-validation",
    "modules": [
        {
            "module_id": "advanced-modeling-contract",
            "required_outputs": [
                "advanced_mathematical_validation_contract.md",
                "advanced_validation_authoritative_inputs.csv",
                "advanced_validation_output_contract.json",
                "advanced_validation_claim_boundaries.csv",
                "advanced_mathematical_validation_contract_audit.json",
                "README.md",
            ],
        },
        {
            "module_id": "conformal-selective-router",
            "required_outputs": [
                "conformal_selective_thresholds.csv",
                "conformal_selective_risk_coverage.csv",
                "conformal_selective_router_audit.json",
                "README.md",
            ],
        },
        {
            "module_id": "cluster-bootstrap-uncertainty",
            "required_outputs": [
                "cluster_bootstrap_metric_intervals.csv",
                "cluster_bootstrap_resampling_audit.json",
                "README.md",
            ],
        },
        {
            "module_id": "descriptor-stratified-calibration",
            "required_outputs": [
                "descriptor_stratified_calibration.csv",
                "descriptor_stratified_reliability.csv",
                "descriptor_stratified_calibration_audit.json",
                "README.md",
            ],
        },
        {
            "module_id": "nonlinear-evidence-sensitivity",
            "required_outputs": [
                "nonlinear_evidence_sensitivity.csv",
                "feature_effect_monotonicity_audit.json",
                "README.md",
            ],
        },
        {
            "module_id": "risk-constrained-review-budget-optimization",
            "required_outputs": [
                "risk_constrained_budget_frontier.csv",
                "risk_constrained_budget_selection.csv",
                "risk_constrained_budget_audit.json",
                "README.md",
            ],
        },
        {
            "module_id": "advanced-claim-gates-and-methods-report",
            "required_outputs": [
                "advanced_final_claim_gate_table.csv",
                "advanced_methods_ready_report.md",
                "advanced_claim_gates_audit.json",
                "README.md",
            ],
        },
    ],
    "required_audit_fields": [
        "built_at_utc",
        "status",
        "authoritative_inputs_present",
        "claim_boundary_status",
        "mathematical_target",
    ],
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def project_relative(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def authoritative_input_rows() -> list[dict[str, Any]]:
    rows = []
    for item in AUTHORITATIVE_INPUTS:
        path = PROJECT_ROOT / item["path"]
        rows.append(
            {
                **item,
                "exists": "yes" if path.exists() else "no",
                "size_bytes": path.stat().st_size if path.exists() else "",
            }
        )
    return rows


def contract_text(audit: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# PF-ERI Advanced Mathematical Validation Contract",
            "",
            f"Status: `{audit['status']}`",
            "",
            "## Scientific Frame",
            "",
            "PF-ERI is a pair-level selective evidence governance layer after",
            "strong wildlife Re-ID descriptor retrieval. It is not a new visual",
            "descriptor, not an embedding model, and not an automatic individual",
            "identification system.",
            "",
            "## Notation",
            "",
            "- Candidate pair: `p = (x_i, x_j)`.",
            "- Descriptor score: `s_d(p)`, produced upstream by MegaDescriptor,",
            "  DINOv2, WildFusion, or another strong descriptor queue.",
            "- PF-ERI evidence vector: `z(p)`, including image evidence, pair",
            "  comparability, descriptor-evidence conflict, and source/domain",
            "  stress diagnostics.",
            "- Label: `y(p) = 1` means the reviewed pair is not-ready-or-uncertain;",
            "  `y(p) = 0` means review-ready.",
            "- Evidence risk score: `R_hat(p) = P(y(p)=1 | z(p), s_d(p))`.",
            "- Evidence sufficiency score: `S_hat(p) = 1 - R_hat(p)`.",
            "- Selective gate: `g_tau(p) = 1[R_hat(p) <= tau]`.",
            "",
            "## Mathematical Target",
            "",
            "For target evidence risk `alpha`, choose an admission threshold `tau`",
            "that maximizes admitted-pair coverage while controlling selective risk:",
            "",
            "```text",
            "coverage(tau) = P(g_tau(p)=1)",
            "selective_risk(tau) = P(y(p)=1 | g_tau(p)=1)",
            "",
            "maximize coverage(tau)",
            "subject to selective_risk(tau) <= alpha",
            "```",
            "",
            "The claim-bearing validation target is CzechLynx reviewed-pair",
            "evidence admissibility. Bobcat outputs are transfer-stress and",
            "workflow-allocation diagnostics only.",
            "",
            "## Assumptions",
            "",
            "- Calibration/evaluation claims require the declared split protocol.",
            "- Pair dependence must be handled by image/component/identity-aware",
            "  splitting or cluster-aware uncertainty.",
            "- Source/domain generalization claims require actual source/domain",
            "  variation; constant-source CzechLynx validation cannot prove them.",
            "- Reason-class explanations require human reason labels; observable",
            "  risk components alone support component attribution only.",
            "",
            "## Authoritative Inputs",
            "",
            f"`{audit['authoritative_inputs_csv']}`",
            "",
            "## Output Contract",
            "",
            f"`{audit['output_contract_json']}`",
            "",
            "## Claim Boundaries",
            "",
            f"`{audit['claim_boundaries_csv']}`",
            "",
            "## Binding Statement",
            "",
            audit["mathematical_target"],
        ]
    ) + "\n"


def report_text(audit: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Advanced Mathematical Validation",
            "",
            f"Status: `{audit['status']}`",
            "",
            "This directory is the formal mathematical contract for the advanced",
            "PF-ERI validation layer.",
            "",
            "## Outputs",
            "",
            f"- Contract: `{audit['contract_md']}`",
            f"- Authoritative inputs: `{audit['authoritative_inputs_csv']}`",
            f"- Output contract: `{audit['output_contract_json']}`",
            f"- Claim boundaries: `{audit['claim_boundaries_csv']}`",
            "",
            "## Boundary",
            "",
            "PF-ERI is selective evidence admission after strong descriptor retrieval;",
            "it is not a new descriptor and does not claim automatic individual ID.",
        ]
    ) + "\n"


def build() -> dict[str, Any]:
    inputs = authoritative_input_rows()
    missing_required = [row["input_id"] for row in inputs if row["required"] == "yes" and row["exists"] != "yes"]
    blocked_claims = [row for row in CLAIM_BOUNDARIES if row["status"] == "blocked"]
    audit = {
        "built_at_utc": utc_now(),
        "status": "PASS" if not missing_required and len(blocked_claims) >= 3 else "FAIL",
        "contract_md": project_relative(CONTRACT_MD),
        "authoritative_inputs_csv": project_relative(INPUTS_CSV),
        "output_contract_json": project_relative(OUTPUT_SCHEMA_JSON),
        "claim_boundaries_csv": project_relative(CLAIM_BOUNDARIES_CSV),
        "authoritative_inputs_present": not missing_required,
        "missing_required_inputs": missing_required,
        "claim_boundary_status": "PASS" if len(blocked_claims) >= 3 else "FAIL",
        "mathematical_target": "maximize accepted-pair coverage subject to selective evidence risk <= alpha",
        "label_semantics": {"1": "not-ready-or-uncertain", "0": "review-ready"},
        "blocked_claims": [row["claim_id"] for row in blocked_claims],
    }
    write_csv(INPUTS_CSV, inputs)
    write_json(OUTPUT_SCHEMA_JSON, OUTPUT_CONTRACT)
    write_csv(CLAIM_BOUNDARIES_CSV, CLAIM_BOUNDARIES)
    CONTRACT_MD.write_text(contract_text(audit), encoding="utf-8")
    REPORT_MD.write_text(report_text(audit), encoding="utf-8")
    write_json(AUDIT_JSON, audit)
    return audit


def main() -> int:
    audit = build()
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
