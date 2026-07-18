#!/usr/bin/env python3
"""Validate the PF-ERI v2 blinded outcome-review export contract.

This validator checks the declared data boundary. It does not replace the
required independent rendered-interface leakage audit before collection.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


CONTRACT_VERSION = "pferi_v2_blinded_outcome_export_contract_v1"
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT_PATH = ROOT / "schemas" / "pferi_v2" / "blinded_outcome_export_contract_v1.json"
REQUIRED_PACKET_FIELDS = {"review_packet_id", "left_asset_token", "right_asset_token", "instrument_version", "review_form_schema_version"}
REQUIRED_RESPONSE_FIELDS = {"review_packet_id", "raw_reviewer_response_id", "review_decision", "reason_codes", "confidence", "optional_note", "submitted_at_utc", "technical_problem_flag"}
REQUIRED_RESTRICTED_LINKAGE_FIELDS = {"review_packet_id", "canonical_pair_id", "left_image_id", "right_image_id", "reviewer_assignment_id", "packet_batch_id"}
PACKET_FORBIDDEN_TOKENS = ("canonical", "endpoint", "descriptor", "similarity", "rank", "pferi", "feature", "quality", "route", "stratum", "identity", "label", "source", "camera", "site", "filename", "path", "metadata", "outcome", "prior", "previous", "comment")
RESPONSE_FORBIDDEN_TOKENS = ("derived", "majority", "adjudicat", "canonical", "descriptor", "similarity", "rank", "pferi", "feature", "quality", "route", "identity")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _issue(issues: list[dict[str, str]], code: str, message: str) -> None:
    issues.append({"code": code, "message": message})


def _forbidden(field: str, tokens: Sequence[str]) -> bool:
    return any(token in field.lower() for token in tokens)


def validate_contract(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate declared reviewer-facing and restricted export fields."""
    issues: list[dict[str, str]] = []
    if payload.get("contract_version") != CONTRACT_VERSION:
        _issue(issues, "invalid_contract_version", "unexpected outcome-export contract version")
    packet_fields = [str(field) for field in payload.get("reviewer_packet_allowlist", [])]
    response_fields = [str(field) for field in payload.get("raw_response_allowlist", [])]
    restricted_fields = [str(field) for field in payload.get("restricted_linkage_allowlist", [])]
    if set(packet_fields) != REQUIRED_PACKET_FIELDS:
        _issue(issues, "invalid_packet_allowlist", "reviewer packet allowlist must be exact")
    if set(response_fields) != REQUIRED_RESPONSE_FIELDS:
        _issue(issues, "invalid_raw_response_allowlist", "raw response allowlist must be exact")
    if set(restricted_fields) != REQUIRED_RESTRICTED_LINKAGE_FIELDS:
        _issue(issues, "invalid_restricted_linkage_allowlist", "restricted linkage allowlist must be exact")
    for field in packet_fields:
        if field not in REQUIRED_PACKET_FIELDS or _forbidden(field, PACKET_FORBIDDEN_TOKENS):
            _issue(issues, f"forbidden_packet_field:{field}", "reviewer packet field may reveal assignment condition")
    for field in response_fields:
        if field not in REQUIRED_RESPONSE_FIELDS or _forbidden(field, RESPONSE_FORBIDDEN_TOKENS):
            _issue(issues, f"forbidden_raw_response_field:{field}", "raw response export may not contain derived or restricted fields")
    asset_rule = payload.get("rendered_asset_rule")
    if asset_rule != "opaque_rendered_asset_tokens_only":
        _issue(issues, "invalid_rendered_asset_rule", "reviewer-facing assets need opaque rendered tokens")
    if payload.get("canonical_pair_linkage_visibility") != "restricted_only":
        _issue(issues, "canonical_linkage_not_restricted", "canonical pair linkage must not reach reviewers")
    if payload.get("first_pass_isolation_rule") != "reviewers_and_adjudicators_receive_no_prior_responses":
        _issue(issues, "invalid_first_pass_isolation_rule", "first pass and adjudication require response isolation")
    required_audit_steps = {"rendered_dom", "url_and_browser_state", "asset_tokens_and_filenames", "export_columns", "sort_filter_search_controls", "network_or_hidden_fields", "leak_disposition_log"}
    audit_steps = {str(step) for step in payload.get("required_independent_leakage_audit", [])}
    if not required_audit_steps.issubset(audit_steps):
        _issue(issues, "incomplete_independent_leakage_audit", "contract must require all rendered-interface leakage checks")
    return {
        "contract_version": payload.get("contract_version"),
        "status": "PASS" if not issues else "FAIL",
        "issues": issues,
        "error_codes": [issue["code"] for issue in issues],
        "packet_allowlist_count": len(packet_fields),
        "raw_response_allowlist_count": len(response_fields),
        "restricted_linkage_allowlist_count": len(restricted_fields),
        "claim_boundary": "A passing validator verifies a declared field boundary only. The batch remains invalid until an independent person documents a rendered-interface leakage audit and its disposition.",
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
