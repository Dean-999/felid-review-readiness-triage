#!/usr/bin/env python3
"""Validate an independent human-browser leakage audit for a v2 dry-run UI."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT_PATH = ROOT / "schemas/pferi_v2/reviewer_interface_dry_run_contract_v1.json"
CHECKLIST_COLUMNS = [
    "check_id",
    "required_check",
    "status",
    "prohibited_exposure_observed",
    "exposed_records_or_na",
    "leak_source_or_na",
    "remediation_or_na",
    "retest_evidence_or_na",
    "final_disposition",
    "auditor_id",
    "auditor_role",
    "audited_at_utc",
    "notes",
]


def load_contract(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def validate_checklist(checklist_path: Path, contract_path: Path = DEFAULT_CONTRACT_PATH) -> dict[str, Any]:
    contract = load_contract(contract_path)
    rows, headers = read_csv(checklist_path)
    audit: dict[str, Any] = {
        "audit_version": "pferi_v2_reviewer_interface_human_audit_validator_v1",
        "contract_version": contract["contract_version"],
        "status": "FAIL",
        "checklist_path": str(checklist_path),
        "error_codes": [],
    }
    if headers != CHECKLIST_COLUMNS:
        audit["error_codes"].append("human_audit_header_mismatch")
        return audit
    required = contract["required_human_browser_checks"]
    by_requirement = {row.get("required_check", ""): row for row in rows}
    if len(by_requirement) != len(rows) or set(by_requirement) != set(required):
        audit["error_codes"].append("human_audit_required_check_set_mismatch")
    auditor_ids = {row.get("auditor_id", "") for row in rows}
    if "" in auditor_ids or len(auditor_ids) != 1:
        audit["error_codes"].append("auditor_identity_missing_or_inconsistent")
    roles = {row.get("auditor_role", "") for row in rows}
    if roles != {"independent_interface_auditor"}:
        audit["error_codes"].append("auditor_role_not_independent")
    for requirement in required:
        row = by_requirement.get(requirement, {})
        if row.get("status") != "pass" or row.get("prohibited_exposure_observed") != "no" or row.get("final_disposition") != "no_leak_confirmed":
            audit["error_codes"].append("incomplete_or_failed_human_check:" + requirement)
        if not row.get("audited_at_utc"):
            audit["error_codes"].append("missing_audit_timestamp:" + requirement)
    audit["completed_check_count"] = sum(row.get("status") == "pass" for row in rows)
    audit["status"] = "PASS" if not audit["error_codes"] else "FAIL"
    return audit


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checklist", type=Path, required=True)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT_PATH)
    parser.add_argument("--audit-json", type=Path, required=True)
    args = parser.parse_args(argv)
    audit = validate_checklist(args.checklist, args.contract)
    args.audit_json.parent.mkdir(parents=True, exist_ok=True)
    args.audit_json.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
