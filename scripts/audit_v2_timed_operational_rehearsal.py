#!/usr/bin/env python3
"""Validate returned PF-ERI v2 timed operational-rehearsal logs without interpreting images."""

from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_COLUMNS = ["rehearsal_packet_id", "operational_response_id", "rehearsal_participant_id", "rehearsal_role", "task_started_at_utc", "task_submitted_at_utc", "elapsed_seconds", "completion_status", "technical_problem_category"]
ALLOCATION_COLUMNS = ["rehearsal_participant_id", "rehearsal_packet_id", "rehearsal_role", "task_order"]


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def read_log_rows(log_dir: Path) -> tuple[list[dict[str, str]], list[str]]:
    rows: list[dict[str, str]] = []
    issues: list[str] = []
    for path in sorted(log_dir.glob("*.csv")):
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if list(reader.fieldnames or []) != REQUIRED_COLUMNS:
                issues.append(f"header_mismatch:{path.name}")
                continue
            rows.extend(reader)
    return rows, issues


def read_allocation_tasks(restricted_dir: Path, assignment_required: bool) -> tuple[set[tuple[str, str, str]], list[str]]:
    path = restricted_dir / "participant_task_allocation.csv"
    if not path.exists():
        return set(), ["missing_assignment_manifest"] if assignment_required else []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if list(reader.fieldnames or []) != ALLOCATION_COLUMNS:
            return set(), ["assignment_manifest_header_mismatch"]
        rows = list(reader)
    tasks = {(row["rehearsal_participant_id"], row["rehearsal_packet_id"], row["rehearsal_role"]) for row in rows}
    if not tasks:
        return tasks, ["empty_assignment_manifest"]
    if len(tasks) != len(rows):
        return tasks, ["duplicate_assignment_task"]
    return tasks, []


def audit_rehearsal(output_dir: Path, contract_path: Path) -> dict[str, Any]:
    output_dir, contract_path = output_dir.resolve(), contract_path.resolve()
    contract = load_json(contract_path)
    build = load_json(output_dir / "restricted" / "build_audit.json")
    packet_path = output_dir / "reviewer_view" / "rehearsal_packet.csv"
    with packet_path.open(newline="", encoding="utf-8") as handle:
        packet_ids = {row["rehearsal_packet_id"] for row in csv.DictReader(handle)}
    rows, issues = read_log_rows(output_dir / "operational_logs")
    assigned_tasks, assignment_issues = read_allocation_tasks(
        output_dir / "restricted", bool(contract.get("assignment_enforcement") == "required")
    )
    base = {
        "audit_version": "pferi_v2_timed_operational_rehearsal_return_audit_v1",
        "created_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "build_audit_sha256": __import__("hashlib").sha256((output_dir / "restricted" / "build_audit.json").read_bytes()).hexdigest(),
        "contract_sha256": __import__("hashlib").sha256(contract_path.read_bytes()).hexdigest(),
        "outcome_access": "none; operational fields are audited without reading or deriving an image judgement.",
        "error_codes": issues + assignment_issues,
    }
    if not rows:
        status = "FAIL" if base["error_codes"] else "PENDING_NO_OPERATIONAL_LOGS"
        return {**base, "status": status, "returned_row_count": 0}
    response_ids = [row["operational_response_id"] for row in rows]
    if len(response_ids) != len(set(response_ids)):
        base["error_codes"].append("duplicate_operational_response_id")
    participant_packet = [(row["rehearsal_participant_id"], row["rehearsal_packet_id"]) for row in rows]
    if len(participant_packet) != len(set(participant_packet)):
        base["error_codes"].append("duplicate_packet_within_participant")
    elapsed: list[float] = []
    valid_statuses = set(contract["completion_status_values"])
    valid_technical = set(contract["technical_problem_category_values"])
    for row in rows:
        if row["rehearsal_packet_id"] not in packet_ids:
            base["error_codes"].append("unknown_rehearsal_packet")
        task = (row["rehearsal_participant_id"], row["rehearsal_packet_id"], row["rehearsal_role"])
        if assigned_tasks and task not in assigned_tasks:
            base["error_codes"].append("unassigned_operational_task")
        if row["completion_status"] not in valid_statuses or row["technical_problem_category"] not in valid_technical:
            base["error_codes"].append("invalid_operational_category")
        try:
            value = float(row["elapsed_seconds"])
        except ValueError:
            base["error_codes"].append("nonnumeric_elapsed_seconds")
            continue
        if not math.isfinite(value) or value <= 0 or value > float(contract["minimum_operational_return"]["maximum_plausible_elapsed_seconds_per_task"]):
            base["error_codes"].append("implausible_elapsed_seconds")
        else:
            elapsed.append(value)
    participants = sorted({row["rehearsal_participant_id"] for row in rows})
    completed_by_participant = {participant: sum(1 for row in rows if row["rehearsal_participant_id"] == participant and row["completion_status"] == "completed") for participant in participants}
    min_return = contract["minimum_operational_return"]
    if len(participants) < int(min_return["minimum_distinct_participants"]):
        base["error_codes"].append("insufficient_distinct_participants")
    if any(count < int(min_return["minimum_completed_tasks_per_participant"]) for count in completed_by_participant.values()):
        base["error_codes"].append("insufficient_completed_tasks_per_participant")
    if bool(min_return["require_at_least_one_adjudication_rehearsal_role"]) and not any(row["rehearsal_role"] == "adjudication_rehearsal" for row in rows):
        base["error_codes"].append("missing_adjudication_rehearsal")
    completed = sum(row["completion_status"] == "completed" for row in rows)
    technical = len(rows) - completed
    summary = {
        "returned_row_count": len(rows),
        "distinct_participant_count": len(participants),
        "completed_task_count": completed,
        "technical_interruption_count": technical,
        "completion_rate": completed / len(rows),
        "completed_tasks_by_participant": completed_by_participant,
        "elapsed_seconds_median": sorted(elapsed)[len(elapsed) // 2] if elapsed else None,
        "elapsed_seconds_p95": sorted(elapsed)[max(0, math.ceil(0.95 * len(elapsed)) - 1)] if elapsed else None,
    }
    base["error_codes"] = sorted(set(base["error_codes"]))
    status = "PASS" if not base["error_codes"] else "FAIL"
    return {**base, **summary, "status": status, "claim_boundary": contract["claim_boundary"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rehearsal-dir", type=Path, required=True)
    parser.add_argument("--contract", type=Path, default=ROOT / "schemas/pferi_v2/timed_operational_rehearsal_contract_v2.json")
    parser.add_argument("--audit-json", type=Path, required=True)
    args = parser.parse_args()
    audit = audit_rehearsal(args.rehearsal_dir, args.contract)
    args.audit_json.parent.mkdir(parents=True, exist_ok=True)
    args.audit_json.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))
    if audit["status"] == "FAIL":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
