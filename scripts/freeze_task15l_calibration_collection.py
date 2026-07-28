#!/usr/bin/env python3
"""Freeze validated Task15K control results and build controlled calibration reviewer packages."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import shutil
import sys
import tempfile
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MODEL_ROOT = ROOT / "archive/pferi_v2/task_runs/model_development"
TASK15K_DESIGN = MODEL_ROOT / "2026-07-27_task15k_independent_calibration_design_freeze_v1"
TASK15K_PACKAGE = ROOT / "work/pferi_v2/gpu/packages/task15k_calibration/PF_ERI_TASK15K_CALIBRATION_MODELSCOPE_CONTROL_PACKAGE"
TASK15J = ROOT / "outputs/pferi_v2/models/development"
ROSTER = ROOT / "artifacts/transfers/pferi_v2/review/task15i_reviewer_packages/restricted/restricted_four_reviewer_roster.csv"
BROWSER_AUDIT = MODEL_ROOT / "2026-07-26_task15i_independent_browser_audit_transcription_v1/browser_audit_validation.json"
CONTRACT = ROOT / "schemas/pferi_v2/task15l_calibration_analysis_contract_v1.json"
DEFAULT_EXPORT = Path("/Users/dshen/Downloads/PF_ERI_TASK15K_CALIBRATION_FINAL_EXPORT.zip")
DEFAULT_EXPORT_SHA = Path("/Users/dshen/Downloads/PF_ERI_TASK15K_CALIBRATION_FINAL_EXPORT.sha256")
OUTPUT = MODEL_ROOT / "2026-07-27_task15l_calibration_collection_freeze_v1"
PLANNING_KEY = hashlib.sha256(b"PF-ERI-Task15L-calibration-collection-20260727").hexdigest()
ASSIGNMENT_VERSION = "pferi_v2_task15l_calibration_collection_assignment_v1"
EXECUTION_COLUMNS = ["image_id", "image_path_relative", "content_sha256"]
ELIGIBILITY_COLUMNS = ["canonical_pair_id", "first_pass_reviewer_code_1", "first_pass_reviewer_code_2", "eligible_adjudicator_codes", "eligibility_status"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="raise", lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)


def read_csv(path: Path, fields: list[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != fields:
            raise ValueError(f"unexpected columns in {path.name}")
        return list(reader)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise RuntimeError(f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def verify_checksum_manifest(directory: Path) -> list[str]:
    manifest = directory / "CHECKSUMS.sha256"
    if not manifest.is_file():
        return ["missing:CHECKSUMS.sha256"]
    declared, failures = set(), []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1); target = directory / relative; declared.add(relative)
        if not target.is_file() or sha256(target) != expected:
            failures.append(relative)
    actual = {str(path.relative_to(directory)) for path in directory.rglob("*") if path.is_file() and path.name not in {"CHECKSUMS.sha256", ".DS_Store"}}
    if actual != declared:
        failures.append("inventory")
    return failures


def parse_declared_sha(path: Path) -> str:
    value = path.read_text(encoding="utf-8").strip().split()[0]
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise ValueError("invalid external SHA256 declaration")
    return value


def extract_and_validate(export_zip: Path, export_sha: Path, stage: Path) -> dict[str, Any]:
    if parse_declared_sha(export_sha) != sha256(export_zip):
        raise ValueError("Task15K external export SHA256 mismatch")
    if not zipfile.is_zipfile(export_zip):
        raise ValueError("Task15K external export is not a ZIP")
    with zipfile.ZipFile(export_zip) as archive:
        if archive.testzip() is not None:
            raise ValueError("Task15K external export ZIP CRC failure")
        expected_prefix = "PF_ERI_TASK15K_CALIBRATION_FINAL_EXPORT/"
        expected = {expected_prefix + item for item in [
            "automatic_quality_measurements.csv", "local_match_measurements.csv", "frozen_model_score_inputs.csv",
            "frozen_model_raw_predictions.csv", "run_audit.json", "validation_audit.json",
        ]}
        if set(archive.namelist()) != expected:
            raise ValueError("unexpected Task15K export inventory")
        destination = stage / "modelscope_results"; destination.mkdir()
        for member in expected:
            target = destination / Path(member).name
            target.write_bytes(archive.read(member))
    runner = load_module("task15k_runner_for_task15l", ROOT / "scripts/task15k_calibration_modelscope_runner.py")
    external_validation = json.loads((destination / "validation_audit.json").read_text(encoding="utf-8"))
    if external_validation.get("status") != "PASS" or external_validation.get("calibration_outcomes_accessed") is not False:
        raise ValueError("external Task15K validation audit did not pass")
    shutil.copy2(destination / "validation_audit.json", destination / "external_validation_audit.json")
    fresh = runner.validate(TASK15K_PACKAGE, destination)
    pairs = runner.read_csv_exact(TASK15K_PACKAGE / "inputs/calibration_candidate_pairs.csv", runner.PAIR_COLUMNS)
    references = runner.read_csv_exact(TASK15K_PACKAGE / "inputs/quality_reference_percentiles.csv", runner.REFERENCE_COLUMNS)
    quality = runner.read_csv_exact(destination / "automatic_quality_measurements.csv", runner.QUALITY_COLUMNS)
    local = runner.read_csv_exact(destination / "local_match_measurements.csv", runner.LOCAL_COLUMNS)
    observed = runner.read_csv_exact(destination / "frozen_model_raw_predictions.csv", runner.PREDICTION_COLUMNS)
    bundle = json.loads((TASK15K_PACKAGE / "inputs/final_model_bundle.json").read_text(encoding="utf-8"))
    frame = runner.build_feature_frame(pairs, quality, local, references)
    expected_features, expected_predictions = runner.score(bundle, frame)
    observed_map = {(row["canonical_pair_id"], row["model_id"]): float(row["probability_not_ready_or_uncertain"]) for row in observed}
    expected_map = {(row["canonical_pair_id"], row["model_id"]): float(row["probability_not_ready_or_uncertain"]) for row in expected_predictions}
    if set(observed_map) != set(expected_map):
        raise ValueError("Task15K prediction coverage mismatch on independent recomputation")
    maximum_difference = max(abs(observed_map[key] - expected_map[key]) for key in observed_map)
    if maximum_difference > 1e-12:
        raise ValueError("Task15K frozen prediction recomputation mismatch")
    score_inputs = pd.read_csv(destination / "frozen_model_score_inputs.csv")
    expected_input = pd.DataFrame(expected_features)
    if list(score_inputs.columns) != list(expected_input.columns) or len(score_inputs) != len(expected_input):
        raise ValueError("Task15K frozen score-input schema mismatch")
    score_inputs = score_inputs.sort_values("canonical_pair_id").reset_index(drop=True)
    expected_input = expected_input.sort_values("canonical_pair_id").reset_index(drop=True)
    if not score_inputs["canonical_pair_id"].equals(expected_input["canonical_pair_id"]):
        raise ValueError("Task15K frozen score-input pair mismatch")
    numeric_difference = np.abs(score_inputs.drop(columns="canonical_pair_id").to_numpy(float) - expected_input.drop(columns="canonical_pair_id").to_numpy(float)).max()
    if numeric_difference > 1e-12:
        raise ValueError("Task15K frozen score-input recomputation mismatch")
    run_audit = json.loads((destination / "run_audit.json").read_text(encoding="utf-8"))
    if run_audit.get("status") != "PASS" or run_audit.get("calibration_outcomes_accessed") is not False or run_audit.get("locked_stage_outcomes_accessed") is not False:
        raise ValueError("Task15K run audit violates outcome boundary")
    return {
        "status": "PASS", "external_zip_sha256": sha256(export_zip), "external_sha256_declaration": parse_declared_sha(export_sha),
        "fresh_validation": fresh, "run_audit": run_audit, "pair_count": len(pairs), "quality_row_count": len(quality),
        "local_row_count": len(local), "prediction_row_count": len(observed),
        "maximum_prediction_recalculation_difference": float(maximum_difference), "maximum_score_input_recalculation_difference": float(numeric_difference),
        "quality_failure_counts": dict(sorted(Counter(row["failure_code"] for row in quality).items())),
        "local_failure_counts": dict(sorted(Counter(row["failure_code"] for row in local).items())),
        "calibration_outcomes_accessed": False,
    }


def build_reviewer_inputs(stage: Path) -> dict[str, Any]:
    planner = load_module("task15l_assignment_planner", ROOT / "scripts/plan_v2_formal_reviewer_assignments.py")
    pair_fields = [
        "canonical_pair_id", "component_id", "formal_sampling_stage", "endpoint_a_image_id", "endpoint_b_image_id",
        "descriptor_support_category", "best_rank_band", "megadescriptor_rank_a_to_b", "megadescriptor_rank_b_to_a",
        "dinov2_rank_a_to_b", "dinov2_rank_b_to_a", "selection_evidence_state",
    ]
    pairs = read_csv(TASK15K_DESIGN / "calibration_candidate_pairs.csv", pair_fields)
    roster = read_csv(ROSTER, ["reviewer_code", "restricted_person_name", "eligible_roles", "training_confirmed", "pair_or_role_conflicts", "conflict_attestation", "signed_at_utc"])
    reviewer_codes = [row["reviewer_code"] for row in roster]
    planner_rows = [{key: row[key] for key in ["canonical_pair_id", "formal_sampling_stage", "endpoint_a_image_id", "endpoint_b_image_id"]} for row in pairs]
    assignments, eligibility = planner.plan_assignments(planner_rows, reviewer_codes, PLANNING_KEY)
    for row in assignments:
        row["assignment_contract_version"] = ASSIGNMENT_VERSION
        row["packet_batch_id"] = "task15l_calibration_first_pass_v1"
    images = read_csv(TASK15K_DESIGN / "selected_image_manifest.csv", ["candidate_image_id", "content_sha256", "local_relative_path", "image_filename"])
    execution = [{"image_id": row["candidate_image_id"], "image_path_relative": row["local_relative_path"], "content_sha256": row["content_sha256"]} for row in images]
    restricted = stage / "restricted"; restricted.mkdir()
    write_csv(restricted / "provisional_four_reviewer_assignment.csv", planner.ASSIGNMENT_COLUMNS, assignments)
    write_csv(restricted / "provisional_adjudicator_eligibility.csv", ELIGIBILITY_COLUMNS, eligibility)
    write_csv(restricted / "selected_image_execution_manifest.csv", EXECUTION_COLUMNS, execution)
    shutil.copy2(ROSTER, restricted / "restricted_four_reviewer_roster.csv")
    loads = Counter(row["reviewer_code"] for row in assignments)
    if set(loads.values()) != {224}:
        raise RuntimeError(f"Task15L reviewer workload is not exactly balanced: {loads}")
    if len(assignments) != 896 or len(eligibility) != 448:
        raise RuntimeError("Task15L assignment coverage mismatch")
    return {"assignments": assignments, "eligibility": eligibility, "execution": execution, "roster": roster, "loads": dict(sorted(loads.items()))}


def authorise_release(stage: Path, package_audit: dict[str, Any]) -> dict[str, Any]:
    prior = json.loads(BROWSER_AUDIT.read_text(encoding="utf-8"))
    if prior.get("status") != "PASS":
        raise ValueError("previous independent browser-audit validation did not pass")
    if package_audit.get("status") != "PASS_CANDIDATE_NOT_RELEASED" or not package_audit.get("conflict_attestations_complete"):
        raise ValueError("Task15L reviewer package candidate is not ready")
    candidate_root = stage / "reviewer_packages"
    app_hashes = {
        sha256(path)
        for path in candidate_root.glob("candidate_reviewer_packages_unzipped/*/reviewer_view/app.py")
    }
    if len(app_hashes) != 1:
        raise RuntimeError("reviewer package interface code differs by reviewer")
    packages = []
    for alias, audit in sorted(package_audit["reviewer_packages"].items()):
        packages.append({"reviewer_alias": alias, "zip_filename": f"PAIR_REVIEW_{alias}.zip", "zip_sha256": audit["zip_sha256"], "first_pass_task_count": audit["first_pass_task_count"]})
    return {
        "authorization_version": "pferi_v2_task15l_calibration_reviewer_release_authorization_v1",
        "authorized_at_utc": utc_now(), "status": "AUTHORIZED_FOR_CONTROLLED_CALIBRATION_FIRST_PASS_COLLECTION",
        "packet_release_authorized": True, "outcome_collection_authorized": True,
        "authorized_scope": {"formal_pair_count": 448, "first_pass_task_count": 896, "reviewer_package_count": 4, "collection_stage": "calibration_first_pass_only"},
        "candidate_build_audit_sha256": sha256(candidate_root / "candidate_build_audit.json"),
        "reviewer_roster_sha256": sha256(ROSTER), "reused_independent_browser_audit_validation_sha256": sha256(BROWSER_AUDIT),
        "reviewer_interface_sha256": next(iter(app_hashes)), "interface_reuse_basis": "The released Task15L packages use the same previously independently browser-audited review instrument, form schema, and static blinded public-packet checks; only hashed image assets and opaque packet tokens differ.",
        "authorized_packages": packages,
        "mandatory_collection_rules": [
            "Distribute only the ZIP matching the assigned reviewer alias and listed SHA256.",
            "A reviewer must not access another reviewer ZIP, any restricted directory, model predictions, descriptor data, image IDs, source metadata, or prior responses.",
            "Return only responses/raw_responses.csv after completion; do not merge or edit it.",
            "Do not adjudicate or fit a calibration model until complete first-pass collection is returned and accepted.",
        ],
        "claim_boundary": "This authorization starts controlled calibration first-pass outcome collection only. It does not establish calibration performance, pair correctness, identity accuracy, deployment performance, or project completion.",
    }


def report_text(record: dict[str, Any]) -> str:
    return f"""# Task15L Calibration Collection Freeze

Status: **AUTHORIZED FOR CONTROLLED CALIBRATION FIRST-PASS COLLECTION**

Task15K returned a verified outcome-free control execution: {record['modelscope_result']['pair_count']} calibration pairs, {record['modelscope_result']['quality_row_count']} endpoint-quality records, and {record['modelscope_result']['prediction_row_count']} frozen P3/P5 raw probabilities. The external ZIP, its declared SHA256, output schemas, and direct recomputation of all model score inputs and probabilities passed.

Task15L freezes the next label collection. Each of the 448 pairs receives two independent blinded reviews, producing 896 first-pass tasks. The four already trained and conflict-attested reviewers each receive exactly 224 tasks. The reviewer-visible ZIPs contain only opaque packet and image-asset tokens; they do not expose pair IDs, image IDs, predictions, descriptors, quality measurements, components, stages, or metadata.

When completed, the label is 0 only if both reviewers select `review_ready`; any other two-review combination is label 1 (`not_ready_or_uncertain`). Assignment coverage, response schema, unique response provenance, and no technical-problem flag are the only hard eligibility requirements. Reasons, confidence, timestamps, and reviewer agreement remain descriptive.

After responses are returned, the frozen analysis may fit only a logistic intercept and slope on the logit of each raw P3/P5 probability. It cannot refit model coefficients, alter features or preprocessing, alter lambda, select a model, or create an action threshold. Any apparent calibration result still requires an independent future confirmation sample before a performance claim.
"""


def freeze(export_zip: Path = DEFAULT_EXPORT, export_sha: Path = DEFAULT_EXPORT_SHA, output: Path = OUTPUT) -> dict[str, Any]:
    export_zip, export_sha, output = export_zip.resolve(), export_sha.resolve(), output.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite immutable output: {output}")
    if not export_zip.is_file() or not export_sha.is_file():
        raise FileNotFoundError("Task15K export ZIP and SHA256 declaration are required")
    if verify_checksum_manifest(TASK15K_DESIGN) or verify_checksum_manifest(TASK15J):
        raise RuntimeError("Task15K design or Task15J model freeze checksum verification failed")
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if contract["input_requirements"]["calibration_labels_open_at_contract_freeze"] is not False:
        raise RuntimeError("Task15L contract must freeze before calibration labels open")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=f".{output.name}.") as temporary:
        stage = Path(temporary) / output.name; stage.mkdir()
        source = stage / "source_delivery"; source.mkdir(); shutil.copy2(export_zip, source / export_zip.name); shutil.copy2(export_sha, source / export_sha.name)
        modelscope_result = extract_and_validate(export_zip, export_sha, stage)
        reviewer_inputs = build_reviewer_inputs(stage)
        builder = load_module("task15l_reviewer_builder", ROOT / "scripts/build_v2_formal_reviewer_packages.py")
        package_audit = builder.build_packages(
            assignment_path=stage / "restricted/provisional_four_reviewer_assignment.csv",
            roster_path=stage / "restricted/restricted_four_reviewer_roster.csv",
            execution_manifest_path=stage / "restricted/selected_image_execution_manifest.csv",
            project_root=ROOT, output_dir=stage / "reviewer_packages",
        )
        release = authorise_release(stage, package_audit)
        write_json(stage / "task15l_calibration_analysis_contract.json", contract)
        write_json(stage / "release_authorization.json", release)
        record = {
            "record_version": "pferi_v2_task15l_calibration_collection_freeze_record_v1", "status": "CALIBRATION_COLLECTION_FROZEN_AND_AUTHORIZED",
            "frozen_at_utc": utc_now(), "contract_sha256": sha256(CONTRACT), "modelscope_result": modelscope_result,
            "reviewer_assignment": {"pair_count": 448, "first_pass_task_count": 896, "reviewer_loads": reviewer_inputs["loads"], "every_pair_two_distinct_reviewers": True, "eligible_adjudicators_per_pair": 2},
            "release_authorization": {"filename": "release_authorization.json", "sha256": sha256(stage / "release_authorization.json"), "status": release["status"]},
            "calibration_outcomes_accessed": False, "deployment_confirmation_outcomes_accessed": False, "mechanism_confirmation_outcomes_accessed": False,
            "next_authorized_action": "Distribute the four listed calibration reviewer ZIPs, collect raw responses, then run the frozen Task15L label-assembly and intercept/slope recalibration analysis.",
            "claim_boundary": contract["claim_boundary"],
        }
        write_json(stage / "task15l_collection_freeze_record.json", record)
        (stage / "TASK15L_CALIBRATION_COLLECTION_REPORT.md").write_text(report_text(record), encoding="utf-8")
        shutil.copy2(Path(__file__), stage / "freeze_builder_snapshot.py")
        files = sorted(path for path in stage.rglob("*") if path.is_file() and path.name != "CHECKSUMS.sha256")
        (stage / "CHECKSUMS.sha256").write_text("".join(f"{sha256(path)}  {path.relative_to(stage)}\n" for path in files), encoding="utf-8")
        shutil.move(str(stage), str(output))
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-zip", type=Path, default=DEFAULT_EXPORT)
    parser.add_argument("--export-sha256", type=Path, default=DEFAULT_EXPORT_SHA)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    try:
        print(json.dumps(freeze(args.export_zip, args.export_sha256, args.output), indent=2, sort_keys=True)); return 0
    except Exception as error:
        print(json.dumps({"status": "FAIL", "error_type": type(error).__name__, "error": str(error)}, indent=2, sort_keys=True)); return 1


if __name__ == "__main__":
    raise SystemExit(main())
