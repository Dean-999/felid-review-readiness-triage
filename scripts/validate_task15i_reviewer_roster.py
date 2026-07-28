#!/usr/bin/env python3
"""Validate the restricted Task15I reviewer roster before packet generation."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PLANNING_ASSIGNMENT = (
    ROOT
    / "archive/pferi_v2/task_runs/model_development/2026-07-26_task15i_blinded_collection_planning_v1"
    / "restricted/provisional_four_reviewer_assignment.csv"
)
ROSTER_COLUMNS = [
    "reviewer_code",
    "restricted_person_name",
    "eligible_roles",
    "training_confirmed",
    "pair_or_role_conflicts",
    "conflict_attestation",
    "signed_at_utc",
]
REQUIRED_ROLES = {"first_pass_reviewer", "adjudicator"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path, expected: list[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if list(reader.fieldnames or []) != expected:
            raise ValueError(f"unexpected columns in {path.name}")
        return list(reader)


def expected_reviewer_codes(assignment_path: Path = PLANNING_ASSIGNMENT) -> set[str]:
    with assignment_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    codes = {row.get("reviewer_code", "") for row in rows}
    peer_codes = {row.get("peer_reviewer_code", "") for row in rows}
    if len(rows) != 3200 or not codes or codes != peer_codes or "" in codes:
        raise ValueError("invalid frozen reviewer assignment")
    return codes


def valid_utc_timestamp(value: str) -> bool:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def validate_roster(rows: list[dict[str, str]], expected_codes: set[str]) -> list[str]:
    failures: list[str] = []
    codes = [row["reviewer_code"].strip() for row in rows]
    names = [row["restricted_person_name"].strip() for row in rows]
    if set(codes) != expected_codes or len(codes) != len(expected_codes):
        failures.append("reviewer_codes_do_not_exactly_match_frozen_assignment")
    if len(set(codes)) != len(codes):
        failures.append("reviewer_codes_are_not_unique")
    if any(not name for name in names):
        failures.append("restricted_person_name_missing")
    if len(set(names)) != len(names):
        failures.append("restricted_person_name_not_distinct")
    for row in rows:
        code = row["reviewer_code"].strip() or "unknown"
        roles = {value.strip() for value in row["eligible_roles"].split(";") if value.strip()}
        if roles != REQUIRED_ROLES:
            failures.append(f"{code}:eligible_roles_not_complete")
        if row["training_confirmed"].strip().lower() != "yes":
            failures.append(f"{code}:training_not_confirmed")
        if not row["pair_or_role_conflicts"].strip():
            failures.append(f"{code}:conflict_declaration_missing")
        if row["conflict_attestation"].strip().lower() != "confirmed":
            failures.append(f"{code}:conflict_attestation_not_confirmed")
        if not valid_utc_timestamp(row["signed_at_utc"].strip()):
            failures.append(f"{code}:signed_at_utc_invalid")
    return sorted(set(failures))


def audit_roster(roster_path: Path, assignment_path: Path = PLANNING_ASSIGNMENT) -> dict[str, Any]:
    rows = read_csv(roster_path, ROSTER_COLUMNS)
    expected_codes = expected_reviewer_codes(assignment_path)
    failures = validate_roster(rows, expected_codes)
    return {
        "status": "PASS_ROSTER_READY_FOR_INDEPENDENT_LEAKAGE_AUDIT" if not failures else "FAIL_ROSTER_NOT_RELEASE_ELIGIBLE",
        "roster_sha256": sha256(roster_path),
        "frozen_assignment_sha256": sha256(assignment_path),
        "expected_reviewer_count": len(expected_codes),
        "submitted_reviewer_count": len(rows),
        "failure_codes": failures,
        "packet_release_authorized": False,
        "outcome_collection_authorized": False,
        "next_required_gate": "independent_browser_leakage_audit" if not failures else "complete_restricted_roster",
        "claim_boundary": "Roster preflight only. A passing preflight does not create reviewer assets, release a packet, collect outcomes, or establish pair correctness.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("roster", type=Path, help="restricted four-person roster CSV")
    parser.add_argument("--assignment", type=Path, default=PLANNING_ASSIGNMENT)
    args = parser.parse_args()
    audit = audit_roster(args.roster, args.assignment)
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
