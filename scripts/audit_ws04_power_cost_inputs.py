#!/usr/bin/env python3
"""Audit whether Workstream 04 has the pre-outcome inputs needed to run power/cost simulation.

This program intentionally does not estimate power or set a sample size.  It hashes and
summarises only approved pre-outcome inputs, then reports the unresolved decisions that
must be frozen before a numerical simulation can produce an official target or seed.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_VERSION = "pferi_v2_power_cost_simulation_input_contract_v1"
EXPECTED_STATUS = "inputs_not_frozen"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def csv_row_count(path: Path) -> int:
    with path.open(encoding="utf-8", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def validate_contract(contract: dict[str, Any]) -> list[str]:
    if contract.get("contract_version") != CONTRACT_VERSION:
        raise ValueError("Unexpected contract_version")
    if contract.get("status") != EXPECTED_STATUS:
        raise ValueError("This audit is only valid for an explicitly unfrozen input contract")
    required = [
        "primary_estimand",
        "outcome_prevalence",
        "dependence_and_graph_structure",
        "missingness_and_completion",
        "workload_and_cost",
        "sampling_constraints",
        "freeze_gate",
    ]
    missing = [key for key in required if key not in contract]
    if missing:
        raise ValueError(f"Contract is missing required sections: {missing}")
    estimand = contract["primary_estimand"]
    if estimand["decision_rule"]["value"] is not None or estimand["minimum_practical_brier_increment"]["value"] is not None:
        raise ValueError("Numerical decision inputs must not be placed in an unfrozen contract")
    freeze_items = contract["freeze_gate"].get("required_before_any_official_target_or_seed", [])
    if not freeze_items:
        raise ValueError("Freeze gate must enumerate required inputs")
    return list(freeze_items)


def source_record(path: Path, category: str, summary: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    return {
        "path_relative_to_project_root": str(path.relative_to(ROOT)),
        "sha256": sha256(path),
        "category": category,
        "summary": summary,
    }


def build_audit(contract_path: Path) -> dict[str, Any]:
    contract = read_json(contract_path)
    unresolved = validate_contract(contract)

    canonical = ROOT / "outputs/pferi_v2/dual_descriptor_queue/canonical_pairs.csv"
    local_gate = ROOT / "outputs/pferi_v2/measurement_feasibility_pilot/local_match_runs/2026-07-14_gpu_t4_protocol_v2/local_match_measurement_feasibility_gate_audit.json"
    quality_gate = ROOT / "outputs/pferi_v2/measurement_feasibility_pilot/automatic_quality_runs/2026-07-14_gpu_cuda_protocol_v1/automatic_quality_measurement_gate_audit.json"
    exploratory_context_path = ROOT / "schemas/pferi_v2/ws04_exploratory_context_v1.json"
    rules = ROOT / "PROJECT_RULES.md"
    analysis_plan = ROOT / "paper/protocols/pre_specified_analysis_plan.md"

    local = read_json(local_gate)
    quality = read_json(quality_gate)
    exploratory_context = read_json(exploratory_context_path)
    sources = [
        source_record(canonical, "v2_outcome_free_graph_structure", {"canonical_pair_rows": csv_row_count(canonical)}),
        source_record(local_gate, "v2_outcome_free_measurement_feasibility", {
            "status": local.get("status"),
            "canonical_valid_measurement_rate": local.get("prespecified_gate_results", {}).get("observed_valid_measurement_rate"),
            "pair_runtime_p95_seconds": local.get("prespecified_gate_results", {}).get("observed_pair_runtime_p95_seconds"),
        }),
        source_record(quality_gate, "v2_outcome_free_measurement_feasibility", {
            "branch_decision": quality.get("branch_decision"),
            "retained_quality_fields": [
                name for name, details in quality.get("field_decisions", {}).items()
                if str(details.get("decision", "")).startswith("retain_")
            ],
        }),
        source_record(exploratory_context_path, "v1_exploratory_scenario_context_only", {
            "context_version": exploratory_context.get("context_version"),
            "source_count": len(exploratory_context.get("sources", [])),
            "record_count": sum(len(source.get("records", [])) for source in exploratory_context.get("sources", [])),
        }),
        source_record(rules, "binding_rule", {}),
        source_record(analysis_plan, "binding_analysis_plan", {}),
    ]

    return {
        "audit_version": "pferi_v2_workstream_04_power_cost_input_audit_v1",
        "created_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "status": "BLOCKED_PENDING_PRE_OUTCOME_DECISIONS",
        "decision_scope": "Input provenance and freeze-readiness audit only; no power estimate, target, sampling seed, outcome packet, or v2 claim is produced.",
        "contract": {
            "path_relative_to_project_root": str(contract_path.relative_to(ROOT)),
            "sha256": sha256(contract_path),
            "contract_version": contract["contract_version"],
            "status": contract["status"],
        },
        "approved_input_sources": sources,
        "v1_use_boundary": "The frozen v1 exploratory-context capsule is scenario context only. Its label prevalence and any historical model behavior must not become a v2 effect-size assumption, success threshold, calibration target, or confirmation evidence.",
        "v2_outcome_access": "none; this audit reads no v2 reviewability label, response log, model fit, calibration result, or confirmation result.",
        "unresolved_required_freeze_items": unresolved,
        "known_pre_outcome_facts": {
            "eligible_canonical_pair_count": csv_row_count(canonical),
            "default_total_unique_pair_target": contract["sampling_constraints"]["default_target"]["total_unique_canonical_pairs"],
            "default_mechanism_pair_target": contract["sampling_constraints"]["default_target"]["mechanism_pairs"],
            "default_deployment_pair_target": contract["sampling_constraints"]["default_target"]["deployment_pairs"],
        },
        "next_authorized_action": "Obtain and freeze the listed pre-outcome decisions, then run a separate versioned sensitivity simulation. Do not create an official target, seed, or outcome-review packet from this audit.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--contract",
        type=Path,
        default=ROOT / "schemas/pferi_v2/power_cost_simulation_input_contract_v1.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "outputs/pferi_v2/dual_sample_confirmation/2026-07-14_power_cost_input_audit_v1",
    )
    args = parser.parse_args()
    audit = build_audit(args.contract.resolve())
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / "power_cost_input_audit.json"
    output.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(f"{audit['status']}: {output}")


if __name__ == "__main__":
    main()
