#!/usr/bin/env python3
"""Validate the PF-ERI v2 automatic pair-evidence extraction contract.

The contract allows only order-invariant automatic evidence derived from the
two images and a registered local correspondence procedure. Descriptor-derived
quantities are explicitly diagnostic-only, so descriptor ensembling cannot be
misreported as independent pair evidence.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


CONTRACT_VERSION = "pferi_v2_automatic_pair_evidence_contract_v1"
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT_PATH = ROOT / "schemas" / "pferi_v2" / "automatic_pair_evidence_contract_v1.json"
DEFAULT_DICTIONARY_PATH = ROOT / "schemas" / "pferi_v2" / "evidence_measurement_dictionary_v1.json"
FORBIDDEN_PRIMARY_INPUT_TOKENS = ("descriptor", "similarity", "rank", "review", "outcome", "route", "identity", "manual", "oracle", "historical", "v1")
REQUIRED_PRIMARY_FIELDS = {
    "feature_name", "source_entity_level", "inference_time_availability", "symmetry_rule", "operational_definition",
    "allowed_inputs", "prohibited_inputs", "feasibility_requirements", "output_record_requirements",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _issue(issues: list[dict[str, str]], code: str, message: str) -> None:
    issues.append({"code": code, "message": message})


def validate_contract(payload: Mapping[str, Any], dictionary: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the scientific boundary of automatic pair-evidence fields."""
    issues: list[dict[str, str]] = []
    if payload.get("contract_version") != CONTRACT_VERSION:
        _issue(issues, "invalid_contract_version", "unexpected pair-evidence contract version")
    dictionary_features = {item.get("feature_name"): item for item in dictionary.get("features", []) if isinstance(item, Mapping)}
    primary = payload.get("primary_evidence_candidates", [])
    diagnostics = payload.get("diagnostic_only_features", [])
    if not isinstance(primary, list) or not primary:
        _issue(issues, "primary_evidence_candidates_empty", "at least one primary evidence candidate is required")
        primary = []
    primary_names: set[str] = set()
    required_prohibitions = {"descriptor_similarity", "candidate_rank", "v2_outcome_review", "identity_truth", "manual_oracle_measurement", "historical_v1_proxy_or_constant", "quality_active_control_columns"}
    required_feasibility = {"automatic_without_manual_rescue", "nonconstant_valid_outputs", "failure_and_runtime_logged", "outcome_blind_execution", "reproducible_order_invariance"}
    for item in primary:
        if not isinstance(item, Mapping):
            _issue(issues, "primary_evidence_not_object", "primary evidence candidate must be an object")
            continue
        name = str(item.get("feature_name", ""))
        missing = REQUIRED_PRIMARY_FIELDS.difference(item)
        if missing:
            _issue(issues, f"primary_evidence_missing_fields:{name}", ", ".join(sorted(missing)))
            continue
        if name in primary_names:
            _issue(issues, f"duplicate_primary_evidence_feature:{name}", "primary evidence feature names must be unique")
        primary_names.add(name)
        feature = dictionary_features.get(name)
        if feature is None:
            _issue(issues, f"unknown_dictionary_feature:{name}", "primary feature is absent from dictionary")
            continue
        if name == "descriptor_disagreement":
            _issue(issues, f"descriptor_derived_feature_cannot_be_primary:{name}", "descriptor disagreement is diagnostic-only")
        if feature.get("entity_level") != "pair" or item["source_entity_level"] != "pair":
            _issue(issues, f"primary_evidence_not_pair_level:{name}", "primary evidence must be pair level")
        if feature.get("inference_time_availability") != "automatic" or item["inference_time_availability"] != "automatic":
            _issue(issues, f"primary_evidence_not_automatic:{name}", "primary evidence must be automatic")
        if item["symmetry_rule"] != "order_invariant":
            _issue(issues, f"invalid_symmetry_rule:{name}", "canonical unordered pair needs order-invariant output")
        for value in item["allowed_inputs"]:
            value = str(value)
            if any(token in value.lower() for token in FORBIDDEN_PRIMARY_INPUT_TOKENS):
                _issue(issues, f"forbidden_primary_input:{name}:{value}", "input violates evidence-independence boundary")
        prohibited = {str(value) for value in item["prohibited_inputs"]}
        if not required_prohibitions.issubset(prohibited):
            _issue(issues, f"primary_evidence_missing_prohibitions:{name}", "primary evidence must block all leakage and active-control inputs")
        requirements = {str(value) for value in item["feasibility_requirements"]}
        if not required_feasibility.issubset(requirements):
            _issue(issues, f"primary_evidence_missing_feasibility_requirements:{name}", "primary evidence must declare all feasibility checks")
        record_requirements = {str(value) for value in item["output_record_requirements"]}
        required_records = {"value_status", "failure_code", "extractor_version", "runtime_ms", "canonical_pair_id"}
        if not required_records.issubset(record_requirements):
            _issue(issues, f"primary_evidence_missing_audit_fields:{name}", "primary evidence must retain audit fields")
    for name in diagnostics:
        feature = dictionary_features.get(name)
        if feature is None:
            _issue(issues, f"unknown_diagnostic_feature:{name}", "diagnostic feature is absent from dictionary")
        elif name != "descriptor_disagreement":
            _issue(issues, f"unexpected_diagnostic_feature:{name}", "only registered descriptor-derived diagnostic is allowed here")
        if name in primary_names:
            _issue(issues, f"diagnostic_feature_in_primary_set:{name}", "diagnostic-only feature cannot be primary")
    return {
        "contract_version": payload.get("contract_version"),
        "status": "PASS" if not issues else "FAIL",
        "issues": issues,
        "error_codes": [issue["code"] for issue in issues],
        "primary_evidence_candidate_count": len(primary),
        "diagnostic_only_count": len(diagnostics),
        "claim_boundary": "A passing contract only fixes extraction independence and audit requirements. It does not establish successful local matching, feature validity, incremental predictive value, or a routing benefit.",
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT_PATH)
    parser.add_argument("--dictionary", type=Path, default=DEFAULT_DICTIONARY_PATH)
    parser.add_argument("--audit-json", type=Path)
    args = parser.parse_args(argv)
    audit = validate_contract(load_json(args.contract), load_json(args.dictionary))
    if args.audit_json:
        args.audit_json.parent.mkdir(parents=True, exist_ok=True)
        args.audit_json.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
