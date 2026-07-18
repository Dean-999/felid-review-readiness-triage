#!/usr/bin/env python3
"""Validate PF-ERI v2's independent automatic image-quality control contract.

This contract defines the active-control quality variables, not their observed
performance. It prohibits descriptor, pair-evidence, outcome, identity, and
manual-oracle inputs, so the later full-model comparison has a genuine
descriptor-plus-independent-quality baseline.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


CONTRACT_VERSION = "pferi_v2_independent_quality_control_contract_v1"
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT_PATH = ROOT / "schemas" / "pferi_v2" / "independent_quality_control_contract_v1.json"
DEFAULT_DICTIONARY_PATH = ROOT / "schemas" / "pferi_v2" / "evidence_measurement_dictionary_v1.json"
FORBIDDEN_INPUT_TOKENS = ("descriptor", "similarity", "rank", "review", "outcome", "route", "identity", "manual", "oracle", "historical", "v1")
REQUIRED_CONTROL_FIELDS = {
    "control_id", "raw_feature_name", "source_entity_level", "pair_aggregation", "model_column_name",
    "role", "allowed_inputs", "prohibited_inputs", "feasibility_requirements",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _issue(issues: list[dict[str, str]], code: str, message: str) -> None:
    issues.append({"code": code, "message": message})


def validate_contract(payload: Mapping[str, Any], dictionary: Mapping[str, Any]) -> dict[str, Any]:
    """Validate quality-control independence and return a deterministic audit."""
    issues: list[dict[str, str]] = []
    if payload.get("contract_version") != CONTRACT_VERSION:
        _issue(issues, "invalid_contract_version", "unexpected quality-control contract version")
    dictionary_features = {item.get("feature_name"): item for item in dictionary.get("features", []) if isinstance(item, Mapping)}
    controls = payload.get("quality_controls", [])
    context_only = payload.get("context_only_features", [])
    if not isinstance(controls, list) or not controls:
        _issue(issues, "quality_controls_empty", "at least one independent quality control is required")
        controls = []
    control_ids: set[str] = set()
    model_columns: set[str] = set()
    for control in controls:
        if not isinstance(control, Mapping):
            _issue(issues, "quality_control_not_object", "each quality control must be an object")
            continue
        identifier = str(control.get("control_id", ""))
        missing = REQUIRED_CONTROL_FIELDS.difference(control)
        if missing:
            _issue(issues, f"quality_control_missing_fields:{identifier}", ", ".join(sorted(missing)))
            continue
        if identifier in control_ids:
            _issue(issues, f"duplicate_quality_control_id:{identifier}", "control IDs must be unique")
        control_ids.add(identifier)
        column = str(control["model_column_name"])
        if column in model_columns:
            _issue(issues, f"duplicate_quality_model_column:{column}", "quality model columns must be unique")
        model_columns.add(column)
        raw_feature = str(control["raw_feature_name"])
        feature = dictionary_features.get(raw_feature)
        if feature is None:
            _issue(issues, f"unknown_dictionary_feature:{identifier}", "raw feature is absent from the v2 dictionary")
            continue
        if feature.get("inference_time_availability") != "automatic":
            _issue(issues, f"quality_control_not_automatic:{identifier}", "quality control must be automatically available")
        if feature.get("entity_level") != "image" or control["source_entity_level"] != "image":
            _issue(issues, f"quality_control_not_image_level:{identifier}", "quality control must originate from image-level measurement")
        if raw_feature in set(context_only):
            _issue(issues, f"quality_control_is_context_only:{identifier}", "context-only feature cannot enter active quality control")
        if control["role"] != "independent_quality_control_candidate":
            _issue(issues, f"invalid_quality_control_role:{identifier}", "quality control role is invalid")
        if control["pair_aggregation"] not in {"minimum", "maximum"}:
            _issue(issues, f"invalid_pair_aggregation:{identifier}", "pair aggregation must be minimum or maximum")
        allowed_inputs = [str(item) for item in control["allowed_inputs"]]
        if not allowed_inputs:
            _issue(issues, f"quality_control_no_allowed_inputs:{identifier}", "quality control requires declared raw inputs")
        for item in allowed_inputs:
            if any(token in item.lower() for token in FORBIDDEN_INPUT_TOKENS):
                _issue(issues, f"forbidden_input:{identifier}:{item}", "quality control input violates independence boundary")
        prohibited = {str(item) for item in control["prohibited_inputs"]}
        required_prohibitions = {"descriptor_similarity", "candidate_rank", "v2_outcome_review", "identity_truth", "manual_oracle_measurement", "historical_v1_proxy_or_constant"}
        if not required_prohibitions.issubset(prohibited):
            _issue(issues, f"quality_control_missing_prohibitions:{identifier}", "quality control must prohibit all leakage and proxy inputs")
        requirements = set(str(item) for item in control["feasibility_requirements"])
        required_requirements = {"automatic_without_manual_rescue", "nonconstant_valid_outputs", "failure_and_runtime_logged", "outcome_blind_execution", "reproducible_pair_aggregation"}
        if not required_requirements.issubset(requirements):
            _issue(issues, f"quality_control_missing_feasibility_requirements:{identifier}", "quality control must have all feasibility checks")
    for feature_name in context_only:
        feature = dictionary_features.get(feature_name)
        if feature is None:
            _issue(issues, f"unknown_context_feature:{feature_name}", "context-only field must exist in dictionary")
        elif feature.get("inference_time_availability") != "automatic":
            _issue(issues, f"context_feature_not_automatic:{feature_name}", "context-only field must be automatic if recorded")
    return {
        "contract_version": payload.get("contract_version"),
        "status": "PASS" if not issues else "FAIL",
        "issues": issues,
        "error_codes": [issue["code"] for issue in issues],
        "control_count": len(controls),
        "context_only_count": len(context_only),
        "claim_boundary": "A passing contract establishes independence and planned feasibility checks only. It does not show that a quality control is valid, nonconstant, predictive, or ready for a primary model.",
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
