#!/usr/bin/env python3
"""Freeze the owner-defined PF-ERI v2 project closure."""
from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "schemas/pferi_v2/final_project_closure_contract_v1.json"
OUTPUT = ROOT / "outputs/pferi_v2/project_closure"
EXECUTION_RESULTS = ROOT / "outputs/pferi_v2/models/confirmation/execution_results"
SEPARATE_OUTCOME_ANALYSIS = ROOT / "outputs/pferi_v2/models/confirmation/final_analysis/task17_confirmation_outcome_analysis.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def validate_closure_basis(contract: dict[str, Any]) -> dict[str, Any]:
    acceptance_path = ROOT / contract["authoritative_acceptance_record"]
    acceptance = read_json(acceptance_path)
    run = read_json(EXECUTION_RESULTS / "run_audit.json")
    validation = read_json(EXECUTION_RESULTS / "validation_audit.json")
    rule = contract["acceptance_rule"]

    if acceptance.get("status") != rule["task15n_status"]:
        raise RuntimeError("Task15N acceptance status mismatch")
    if run.get("status") != rule["run_audit_status"]:
        raise RuntimeError("Task15M run audit did not pass")
    if validation.get("status") != rule["validation_audit_status"] or validation.get("failures") != rule["validation_failures"]:
        raise RuntimeError("Task15M validation audit did not pass cleanly")

    separate_analysis = read_json(SEPARATE_OUTCOME_ANALYSIS) if SEPARATE_OUTCOME_ANALYSIS.is_file() else None
    return {
        "task15n_status": acceptance["status"],
        "run_audit_status": run["status"],
        "validation_audit_status": validation["status"],
        "validation_failures": validation["failures"],
        "candidate_pair_count": acceptance["evidence"]["candidate_pair_count"],
        "supported_pair_count": acceptance["evidence"]["supported_pair_count"],
        "unsupported_pair_count": acceptance["evidence"]["unsupported_pair_count"],
        "prediction_count": acceptance["evidence"]["prediction_count"],
        "acceptance_record_sha256": sha256(acceptance_path),
        "run_audit_sha256": sha256(EXECUTION_RESULTS / "run_audit.json"),
        "validation_audit_sha256": sha256(EXECUTION_RESULTS / "validation_audit.json"),
        "separate_outcome_analysis_present": separate_analysis is not None,
        "separate_outcome_analysis_status": separate_analysis.get("status") if separate_analysis else None,
        "separate_outcome_analysis_is_closure_basis": False,
    }


def freeze(output: Path = OUTPUT) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite immutable output: {output}")
    contract = read_json(CONTRACT)
    evidence = validate_closure_basis(contract)
    record = {
        "record_version": "pferi_v2_final_project_closure_v1",
        "status": contract["final_status"],
        "confirmation_scope": contract["confirmation_scope"],
        "project_status": contract["project_status"],
        "task_chain_closed": contract["task_chain_closed"],
        "next_task": contract["next_task"],
        "no_further_analysis_required_for_closure": contract["no_further_analysis_required_for_closure"],
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "closure_basis": evidence,
        "claim_boundary": contract["claim_boundary"],
        "identity_accuracy_claim_authorized": False,
        "automatic_identity_assignment_claim_authorized": False,
        "prohibited_closure_actions": contract["prohibited_closure_actions"],
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".project_closure.") as temporary:
        stage = Path(temporary) / output.name
        stage.mkdir()
        shutil.copy2(CONTRACT, stage / "final_project_closure_contract.json")
        write_json(stage / "final_project_closure_record.json", record)
        (stage / "FINAL_PROJECT_CLOSURE_REPORT.md").write_text(
            "# PF-ERI v2 Final Project Closure\n\n"
            "Status: **CONFIRMED**\n\n"
            "PF-ERI v2 is closed at the owner-defined Task15M execution-validation acceptance gate. "
            "The run audit passed, the validation audit passed with no failures, and no further task is required for project closure. "
            "This confirmation is bounded to execution, coverage, integrity, and validation acceptance and is not an identity-accuracy claim.\n",
            encoding="utf-8",
        )
        files = sorted(path for path in stage.iterdir() if path.is_file() and path.name != "CHECKSUMS.sha256")
        (stage / "CHECKSUMS.sha256").write_text(
            "".join(f"{sha256(path)}  {path.name}\n" for path in files), encoding="utf-8"
        )
        shutil.move(str(stage), str(output))
    return record


def main() -> int:
    try:
        print(json.dumps(freeze(), indent=2, sort_keys=True))
        return 0
    except Exception as error:
        print(json.dumps({"status": "FAIL", "error_type": type(error).__name__, "error": str(error)}, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
