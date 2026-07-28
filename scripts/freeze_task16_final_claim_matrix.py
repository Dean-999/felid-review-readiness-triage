#!/usr/bin/env python3
"""Freeze the bounded PF-ERI v2 claim matrix without outcome analysis."""
from __future__ import annotations

import csv
import hashlib
import json
import shutil
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "schemas/pferi_v2/task16_final_claim_matrix_contract_v1.json"
OUTPUT = ROOT / "outputs/pferi_v2/models/confirmation/claim_matrix"


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


def resolve_sources(contract: dict[str, Any]) -> dict[str, Path]:
    return {name: ROOT / relative for name, relative in contract["source_records"].items()}


def validate_sources(contract: dict[str, Any]) -> dict[str, Any]:
    sources = resolve_sources(contract)
    missing = [str(path.relative_to(ROOT)) for path in sources.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing Task16 source records: {missing}")

    development = read_json(sources["task15j_development"])
    calibration = read_json(sources["task15l_calibration"])
    execution = read_json(sources["task15n_execution"])
    required = contract["required_source_states"]

    if development.get("status") != required["task15j_status"] or development.get("qualification_status") != required["task15j_qualification_status"]:
        raise RuntimeError("Task15J development state mismatch")
    if not development.get("development_model_frozen") or development.get("full_model_id") != "P5" or development.get("active_control_model_id") != "P3":
        raise RuntimeError("Task15J frozen-model binding mismatch")

    if calibration.get("status") != required["task15l_status"] or calibration.get("calibration", {}).get("status") != "PASS":
        raise RuntimeError("Task15L calibration state mismatch")
    calibration_state = calibration["calibration"]
    if calibration_state.get("model_selection_performed") or calibration_state.get("original_models_refit"):
        raise RuntimeError("Task15L altered model selection or original models")
    if not calibration_state.get("p3_calibrated_probabilities_valid") or not calibration_state.get("p5_calibrated_probabilities_valid"):
        raise RuntimeError("Task15L calibrated probabilities are invalid")

    if execution.get("status") != required["task15n_status"]:
        raise RuntimeError("Task15N execution state mismatch")
    if execution.get("confirmation_outcomes_accessed") is not required["task15n_confirmation_outcomes_accessed"]:
        raise RuntimeError("Task15N outcome-access boundary mismatch")
    if execution.get("outcome_performance_analysis_performed") is not required["task15n_outcome_performance_analysis_performed"]:
        raise RuntimeError("Task15N performance-analysis boundary mismatch")

    manuscript = sources["manuscript_integration"].read_text(encoding="utf-8")
    required_phrases = (
        "PASS_TASK15M_EXECUTION_VALIDATION",
        "does not establish identity accuracy",
        "historical v1 manuscript remains exploratory",
    )
    absent = [phrase for phrase in required_phrases if phrase not in manuscript]
    if not any(
        phrase in manuscript
        for phrase in (
            "has not established independent confirmation performance",
            "did not establish independent confirmation superiority",
        )
    ):
        absent.append("bounded independent confirmation disposition")
    if absent:
        raise RuntimeError(f"Task16 manuscript boundary phrases missing: {absent}")

    disposition_counts = dict(Counter(claim["disposition"] for claim in contract["claims"]))
    return {
        "development_status": development["status"],
        "development_increment": development["qualification_before_performance"]["minimum_weighted_brier_increment"]["evidence"]["observed_P3_minus_P5"],
        "development_pair_count": development["qualification_before_performance"]["minimum_independent_redevelopment_coverage"]["evidence"]["pair_count"],
        "development_component_count": development["qualification_before_performance"]["minimum_independent_redevelopment_coverage"]["evidence"]["component_count"],
        "calibration_status": calibration["status"],
        "calibration_pair_count": calibration["calibratability"]["total_pairs"],
        "execution_status": execution["status"],
        "execution_candidate_pair_count": execution["evidence"]["candidate_pair_count"],
        "execution_supported_pair_count": execution["evidence"]["supported_pair_count"],
        "execution_unsupported_pair_count": execution["evidence"]["unsupported_pair_count"],
        "confirmation_outcomes_accessed": execution["confirmation_outcomes_accessed"],
        "outcome_performance_analysis_performed": execution["outcome_performance_analysis_performed"],
        "claim_count": len(contract["claims"]),
        "claim_disposition_counts": disposition_counts,
        "source_sha256": {name: sha256(path) for name, path in sources.items()},
    }


def write_claim_csv(path: Path, claims: list[dict[str, Any]]) -> None:
    fields = ["claim_id", "disposition", "public_statement", "evidence_ids", "manuscript_treatment"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for claim in claims:
            row = dict(claim)
            row["evidence_ids"] = ";".join(claim["evidence_ids"])
            writer.writerow(row)


def freeze(output: Path = OUTPUT) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite immutable output: {output}")
    contract = read_json(CONTRACT)
    evidence = validate_sources(contract)
    record = {
        "record_version": "pferi_v2_task16_final_claim_matrix_v1",
        "status": contract["accepted_status"],
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "workstream_exit_decision": contract["workstream_exit_decision"],
        "evidence": evidence,
        "claims": contract["claims"],
        "prohibited_actions": contract["prohibited_actions"],
        "confirmation_performance_established": False,
        "identity_accuracy_established": False,
        "deployment_utility_established": False,
        "project_complete": False,
        "next_authorized_action": "Either authorize a separately governed confirmation-outcome analysis or close the project with external performance explicitly unconfirmed.",
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".task16_claims.") as temporary:
        stage = Path(temporary) / output.name
        stage.mkdir()
        shutil.copy2(CONTRACT, stage / "task16_final_claim_matrix_contract.json")
        write_json(stage / "task16_final_claim_matrix.json", record)
        write_claim_csv(stage / "task16_final_claim_matrix.csv", contract["claims"])
        (stage / "TASK16_FINAL_CLAIM_MATRIX_REPORT.md").write_text(
            "# Task16 Final Claim Matrix\n\n"
            "Status: **TASK16_CLAIM_MATRIX_FROZEN_PERFORMANCE_UNCONFIRMED**\n\n"
            "Task16 verified the frozen development, calibration, and execution records and mapped them to bounded public claims. "
            "Task15M execution validation passed, but confirmation outcomes were not accessed and no outcome-performance analysis was performed. "
            "Accordingly, external P5 superiority, identity accuracy, deployment utility, and project completion remain unestablished.\n",
            encoding="utf-8",
        )
        freeze_files = sorted(path for path in stage.iterdir() if path.is_file() and path.name != "CHECKSUMS.sha256")
        (stage / "CHECKSUMS.sha256").write_text(
            "".join(f"{sha256(path)}  {path.name}\n" for path in freeze_files), encoding="utf-8"
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
