#!/usr/bin/env python3
"""Freeze the authoritative Task15M execution result without model recalculation."""
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

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs/pferi_v2/models/confirmation/execution_results"
CONTRACT = ROOT / "schemas/pferi_v2/task15n_confirmation_execution_result_freeze_contract_v1.json"
OUTPUT = ROOT / "outputs/pferi_v2/models/confirmation/execution_freeze"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def source_files(source: Path) -> list[Path]:
    return sorted(path for path in source.rglob("*") if path.is_file() and path.name != ".DS_Store")


def validate_source(source: Path, contract: dict[str, Any]) -> dict[str, Any]:
    run = json.loads((source / "run_audit.json").read_text(encoding="utf-8"))
    validation = json.loads((source / "validation_audit.json").read_text(encoding="utf-8"))
    rule = contract["acceptance_rule"]
    if run.get("status") != rule["run_audit_status"] or validation.get("status") != rule["validation_audit_status"]:
        raise RuntimeError("Task15M run or validation audit did not pass")
    if validation.get("failures") != rule["validation_failures"] or run.get("confirmation_outcomes_accessed") is not False:
        raise RuntimeError("Task15M validation failures or outcome-access boundary mismatch")
    if run.get("package_manifest_sha256") != contract["frozen_bindings"]["package_manifest_sha256"] or run.get("contract_sha256") != contract["frozen_bindings"]["execution_contract_sha256"]:
        raise RuntimeError("Task15M package or execution-contract binding mismatch")

    measurements = read_csv(source / "descriptor_pair_measurements.csv")
    supported = read_csv(source / "supported_pair_manifest.csv")
    unsupported = read_csv(source / "unsupported_pair_manifest.csv")
    quality = read_csv(source / "automatic_quality_measurements.csv")
    local = read_csv(source / "local_match_measurements.csv")
    predictions = read_csv(source / "frozen_model_calibrated_predictions.csv")
    measured_ids = {row["canonical_pair_id"] for row in measurements}
    supported_ids = {row["canonical_pair_id"] for row in supported}
    unsupported_ids = {row["canonical_pair_id"] for row in unsupported}
    if len(measurements) != rule["expected_candidate_pair_count"] or len(measured_ids) != len(measurements):
        raise RuntimeError("Task15M candidate-pair coverage mismatch")
    if len(supported) != rule["expected_supported_pair_count"] or len(unsupported) != rule["expected_unsupported_pair_count"] or supported_ids & unsupported_ids or supported_ids | unsupported_ids != measured_ids:
        raise RuntimeError("Task15M supported/unsupported partition mismatch")
    if len(quality) != rule["expected_image_count"] or set(row["failure_code"] for row in quality) != {"none"}:
        raise RuntimeError("Task15M quality coverage or failure mismatch")
    if len(local) != len(supported) or set(row["failure_code"] for row in local) != {"none"}:
        raise RuntimeError("Task15M local-match coverage or failure mismatch")
    expected_predictions = {(pair_id, model) for pair_id in supported_ids for model in ("P3", "P5")}
    if len(predictions) != rule["expected_prediction_count"] or {(row["canonical_pair_id"], row["model_id"]) for row in predictions} != expected_predictions:
        raise RuntimeError("Task15M prediction coverage mismatch")

    descriptor_checks: dict[str, Any] = {}
    audits = {item["descriptor_name"]: item for item in run["descriptor_runs"]}
    for name, expected_shape, score_name in (
        ("megadescriptor_l_384", [815, 1536], "pair_scores.csv"),
        ("dinov2_vitl14", [815, 1024], "scores.csv"),
    ):
        audit = audits[name]
        embeddings = np.load(source / name / "embeddings.npy", allow_pickle=False)
        manifest = read_csv(source / name / "embedding_manifest_v2.csv")
        scores = read_csv(source / name / score_name)
        checks = {
            "embedding_shape": list(embeddings.shape),
            "embedding_l2_normalized": bool(np.allclose(np.linalg.norm(embeddings, axis=1), 1.0, rtol=1e-4, atol=1e-4)),
            "manifest_row_count": len(manifest),
            "score_row_count": len(scores),
            "embedding_sha256_match": sha256(source / name / "embeddings.npy") == audit["embeddings_sha256"],
            "manifest_sha256_match": sha256(source / name / "embedding_manifest_v2.csv") == audit["embedding_manifest_sha256"],
            "scores_sha256_match": sha256(source / name / score_name) == audit["scores_sha256"],
        }
        if checks["embedding_shape"] != expected_shape or not checks["embedding_l2_normalized"] or checks["manifest_row_count"] != 815 or checks["score_row_count"] != 16300 or not all(checks[key] for key in ("embedding_sha256_match", "manifest_sha256_match", "scores_sha256_match")):
            raise RuntimeError(f"Task15M descriptor validation mismatch: {name}")
        descriptor_checks[name] = checks

    return {
        "candidate_pair_count": len(measurements),
        "supported_pair_count": len(supported),
        "unsupported_pair_count": len(unsupported),
        "verified_image_count": len(quality),
        "quality_failure_counts": dict(Counter(row["failure_code"] for row in quality)),
        "local_match_failure_counts": dict(Counter(row["failure_code"] for row in local)),
        "prediction_count": len(predictions),
        "descriptor_checks": descriptor_checks,
        "run_audit_sha256": sha256(source / "run_audit.json"),
        "validation_audit_sha256": sha256(source / "validation_audit.json"),
    }


def freeze(source: Path = SOURCE, output: Path = OUTPUT) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite immutable output: {output}")
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    evidence = validate_source(source, contract)
    files = source_files(source)
    if len(files) != 18:
        raise RuntimeError(f"unexpected Task15M source file count: {len(files)}")
    record = {
        "record_version": "pferi_v2_task15n_confirmation_execution_result_freeze_v1",
        "status": contract["accepted_status"],
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "authoritative_source": str(source.relative_to(ROOT)),
        "source_file_count_excluding_macos_metadata": len(files),
        "evidence": evidence,
        "model_coefficients_recomputed": False,
        "calibration_parameters_recomputed": False,
        "outcome_performance_analysis_performed": False,
        "confirmation_outcomes_accessed": False,
        "superseded_artifact": contract["superseded_artifact"],
        "supersession_reason": "The earlier artifact was derived from the wrong user-supplied source and is excluded from the authoritative evidence chain.",
        "claim_boundary": contract["claim_boundary"],
        "next_authorized_action": "Task16 final claim matrix, governance closeout, and manuscript integration using PASS_TASK15M_EXECUTION_VALIDATION only.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".task15n_freeze.") as temporary:
        stage = Path(temporary) / output.name
        stage.mkdir()
        shutil.copy2(CONTRACT, stage / "task15n_confirmation_execution_result_freeze_contract.json")
        write_json(stage / "task15n_confirmation_execution_result_freeze.json", record)
        (stage / "SOURCE_RESULTS_CHECKSUMS.sha256").write_text("".join(f"{sha256(path)}  {path.relative_to(source)}\n" for path in files), encoding="utf-8")
        (stage / "TASK15N_CONFIRMATION_EXECUTION_RESULT_FREEZE_REPORT.md").write_text(
            "# Task15N Confirmation Execution Result Freeze\n\n"
            "Status: **PASS_TASK15M_EXECUTION_VALIDATION**\n\n"
            "The authoritative Task15M directory passed run, validation, coverage, descriptor, and artifact-integrity checks. "
            "This freeze does not recalculate Task15J coefficients, Task15L calibration parameters, or outcome-performance metrics.\n\n"
            "The prior Task15M external-confirmation analysis artifact is superseded because it used the wrong user-supplied source and must not be cited.\n",
            encoding="utf-8",
        )
        freeze_files = sorted(path for path in stage.rglob("*") if path.is_file() and path.name != "CHECKSUMS.sha256")
        (stage / "CHECKSUMS.sha256").write_text("".join(f"{sha256(path)}  {path.relative_to(stage)}\n" for path in freeze_files), encoding="utf-8")
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
