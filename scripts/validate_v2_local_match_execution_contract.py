#!/usr/bin/env python3
"""Validate the pre-inference PF-ERI v2 local matcher contract."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT_PATH = ROOT / "schemas/pferi_v2/local_match_execution_contract_v1.json"
REQUIRED_FORBIDDEN = {"descriptor_similarity", "candidate_rank", "identity_truth", "v2_outcome_review", "manual_oracle_measurement"}
REQUIRED_DIRECTIONS = {"A_to_B", "B_to_A"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_contract(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if payload.get("contract_version") != "pferi_v2_local_match_execution_contract_v1":
        errors.append("invalid_contract_version")
    if set(payload.get("required_directions", [])) != REQUIRED_DIRECTIONS:
        errors.append("invalid_required_directions")
    if payload.get("canonical_aggregation", {}).get("rule") != "minimum_of_two_valid_directions":
        errors.append("invalid_canonical_aggregation")
    for item in sorted(REQUIRED_FORBIDDEN - set(payload.get("prohibited_inputs", []))):
        errors.append(f"missing_prohibited_input:{item}")
    pipeline = payload.get("pipeline", {})
    if set(("animal_region_detector", "local_feature_extractor", "local_matcher", "lightglue_source_revision")) - set(pipeline):
        errors.append("incomplete_pipeline_registration")
    if not payload.get("directional_output_columns") or not payload.get("canonical_output_columns"):
        errors.append("missing_output_schema")
    return {"contract_version": payload.get("contract_version", ""), "status": "PASS" if not errors else "FAIL", "error_codes": errors}


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
