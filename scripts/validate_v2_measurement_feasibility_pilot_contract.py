#!/usr/bin/env python3
"""Validate the PF-ERI v2 measurement-feasibility pilot and pre-outcome gates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


CONTRACT_VERSION = "pferi_v2_measurement_feasibility_pilot_contract_v1"
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT_PATH = ROOT / "schemas" / "pferi_v2" / "measurement_feasibility_pilot_contract_v1.json"
REQUIRED_MANIFEST_COLUMNS = {"contract_version", "pilot_pair_id", "canonical_pair_id", "selection_seed_id", "selection_stratum", "pair_availability_status", "pilot_inclusion_status", "exclusion_reason"}
FORBIDDEN_MANIFEST_TOKENS = ("review", "outcome", "decision", "label", "route", "pferi", "identity", "phase18", "v1")
REQUIRED_GATES = {
    "automatic_quality_valid_output_rate", "automatic_quality_variation", "automatic_quality_manual_rescue", "automatic_quality_runtime",
    "local_match_valid_output_rate", "local_match_variation", "local_match_order_invariance", "local_match_manual_rescue", "local_match_runtime", "structural_oracle_reliability",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _issue(issues: list[dict[str, str]], code: str, message: str) -> None:
    issues.append({"code": code, "message": message})


def validate_contract(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate pre-outcome pilot isolation, sample unit, and fixed gates."""
    issues: list[dict[str, str]] = []
    if payload.get("contract_version") != CONTRACT_VERSION:
        _issue(issues, "invalid_contract_version", "unexpected pilot-contract version")
    if payload.get("unit_of_sampling") != "canonical_unordered_pair":
        _issue(issues, "invalid_sampling_unit", "pilot must sample canonical unordered pairs")
    target = payload.get("target_unique_pair_count")
    if target != 160:
        _issue(issues, "invalid_target_unique_pair_count", "pilot target is the prespecified 160 unique pairs")
    if payload.get("outcome_data_rule") != "no_v2_outcome_collection_or_outcome_label_access":
        _issue(issues, "invalid_outcome_data_rule", "pilot must be outcome-free")
    if payload.get("confirmation_overlap_rule") != "pilot_pairs_are_ineligible_for_v2_confirmation_samples":
        _issue(issues, "invalid_confirmation_overlap_rule", "pilot pairs must be excluded from confirmation")
    manifest_columns = [str(value) for value in payload.get("pilot_manifest_required_columns", [])]
    if set(manifest_columns) != REQUIRED_MANIFEST_COLUMNS:
        _issue(issues, "invalid_pilot_manifest_columns", "pilot manifest columns must be exact")
    for column in manifest_columns:
        if any(token in column.lower() for token in FORBIDDEN_MANIFEST_TOKENS):
            _issue(issues, f"forbidden_pilot_manifest_field:{column}", "pilot manifest may not carry outcomes or v1 identifiers")
    coverage = set(str(value) for value in payload.get("required_coverage_domains", []))
    required_coverage = {"descriptor_membership", "retrieval_rank_band", "day_or_infrared_metadata", "image_decode_availability", "source_camera_context_when_available"}
    if not required_coverage.issubset(coverage):
        _issue(issues, "incomplete_difficulty_coverage", "pilot must prospectively cover declared operational stress domains")
    gates = payload.get("retention_gates", [])
    if not isinstance(gates, list):
        _issue(issues, "retention_gates_not_list", "retention gates must be a list")
        gates = []
    gate_ids: set[str] = set()
    for gate in gates:
        if not isinstance(gate, Mapping):
            _issue(issues, "retention_gate_not_object", "each gate must be an object")
            continue
        gate_id = str(gate.get("gate_id", ""))
        gate_ids.add(gate_id)
        if not gate.get("metric") or not gate.get("threshold"):
            _issue(issues, f"incomplete_retention_gate:{gate_id}", "gate must specify metric and threshold")
        if gate.get("selection_rule") != "fixed_before_pilot_measurements":
            _issue(issues, f"adaptive_retention_gate:{gate_id}", "retention gate cannot be chosen after pilot inspection")
        if gate.get("failure_action") not in {"remove", "redefine_or_oracle_only", "measurement_not_ready"}:
            _issue(issues, f"invalid_gate_failure_action:{gate_id}", "gate needs a prespecified failure action")
    if gate_ids != REQUIRED_GATES:
        _issue(issues, "missing_required_retention_gates", "pilot requires the complete fixed gate set")
    return {
        "contract_version": payload.get("contract_version"),
        "status": "PASS" if not issues else "FAIL",
        "issues": issues,
        "error_codes": [issue["code"] for issue in issues],
        "target_unique_pair_count": target,
        "gate_count": len(gates),
        "claim_boundary": "This contract fixes the pilot unit, isolation, and retention rules. It does not select real pairs, run an extractor, establish a feature's validity, or support a predictive claim.",
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT_PATH)
    parser.add_argument("--audit-json", type=Path)
    args = parser.parse_args(argv)
    audit = validate_contract(load_json(args.contract))
    if args.audit_json:
        args.audit_json.parent.mkdir(parents=True, exist_ok=True)
        args.audit_json.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
