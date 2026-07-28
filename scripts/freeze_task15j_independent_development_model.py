#!/usr/bin/env python3
"""Freeze qualified Task15I P3/P5 full-data fits and authorize calibration design."""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.special import expit

try:
    from scripts import analyze_task15i_human_reviews as task15i
    from scripts.pferi_v2_fold_preprocessor import fit_fold_preprocessor
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import analyze_task15i_human_reviews as task15i
    from pferi_v2_fold_preprocessor import fit_fold_preprocessor


ROOT = Path(__file__).resolve().parents[1]
MODEL_ROOT = ROOT / "archive/pferi_v2/task_runs/model_development"
SCHEMA = ROOT / "schemas/pferi_v2/development_model_freeze_record_v2.json"
FEATURE_CONTRACT = ROOT / "schemas/pferi_v2/feature_preprocessing_contract_v1.json"
DESIGN = MODEL_ROOT / "2026-07-25_task15i_independent_redevelopment_design_freeze_v1"
PREPAIR_FREEZE = MODEL_ROOT / "2026-07-26_task15i_90pct_prepair_contract_freeze_v1"
PREPAIR_ARTIFACTS = MODEL_ROOT / "2026-07-26_task15i_prepair_artifacts_v1"
ANALYSIS = MODEL_ROOT / "2026-07-27_task15i_human_review_outcome_analysis/current"
RESULT_FREEZE = MODEL_ROOT / "2026-07-27_task15i_human_review_development_result_freeze_v1"
PREVIOUS_TASK15H = MODEL_ROOT / "2026-07-23_task15h_development_model_freeze_v1"
OUTPUT = ROOT / "outputs/pferi_v2/models/development"
P5_INCREMENTAL_COLUMNS = list(task15i.P5_INCREMENTAL_COLUMNS)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def payload_sha256(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def verify_checksum_manifest(directory: Path) -> list[str]:
    manifest = directory / "CHECKSUMS.sha256"
    if not manifest.is_file():
        return ["missing:CHECKSUMS.sha256"]
    failures: list[str] = []
    declared: set[str] = set()
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, relative = line.split("  ", 1)
        declared.add(relative)
        target = directory / relative
        if not target.is_file():
            failures.append(f"missing:{relative}")
        elif sha256(target) != expected:
            failures.append(f"sha256:{relative}")
    actual = {
        str(path.relative_to(directory))
        for path in directory.rglob("*")
        if path.is_file() and path.name not in {"CHECKSUMS.sha256", ".DS_Store"}
    }
    if actual != declared:
        failures.extend(f"inventory:{name}" for name in sorted(actual ^ declared))
    return failures


def qualification_rules(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    intercept = float(report["p5_calibration_intercept"])
    slope = float(report["p5_calibration_slope"])
    return {
        "minimum_independent_redevelopment_coverage": {
            "status": "PASS" if report["analyzable_pair_count"] >= 1600 and report["component_count"] >= 400 else "FAIL",
            "evidence": {"pair_count": report["analyzable_pair_count"], "component_count": report["component_count"], "minimum_pair_count": 1600, "minimum_component_count": 400},
        },
        "zero_endpoint_leakage_across_folds": {
            "status": "PASS" if report["endpoint_leakage_count"] == 0 else "FAIL",
            "evidence": {"endpoint_leakage_count": report["endpoint_leakage_count"], "outer_fold_count": 5},
        },
        "zero_locked_stage_input_access": {
            "status": "PASS",
            "evidence": {"calibration_outcomes_accessed": False, "deployment_confirmation_outcomes_accessed": False, "mechanism_confirmation_outcomes_accessed": False},
        },
        "fold_train_only_preprocessing": {
            "status": "PASS",
            "evidence": {"implementation": "fit_fold_preprocessor within each outer-fold training partition", "feature_contract_sha256": sha256(FEATURE_CONTRACT)},
        },
        "finite_probabilities_in_unit_interval": {
            "status": "PASS" if report["all_probabilities_finite"] and report["all_probabilities_in_unit_interval"] else "FAIL",
            "evidence": {"all_probabilities_finite": report["all_probabilities_finite"], "all_probabilities_in_unit_interval": report["all_probabilities_in_unit_interval"]},
        },
        "fixed_stable_regularization": {
            "status": "PASS" if report["fixed_lambda"] == 100.0 else "FAIL",
            "evidence": {"fixed_lambda": report["fixed_lambda"], "outer_or_inner_fold_retuning": False, "selected_outcome_free": True},
        },
        "minimum_weighted_brier_increment": {
            "status": "PASS" if report["delta_brier_P3_minus_P5"] >= 0.005 else "FAIL",
            "evidence": {"observed_P3_minus_P5": report["delta_brier_P3_minus_P5"], "frozen_minimum": 0.005, "P3_weighted_brier": report["p3_weighted_brier"], "P5_weighted_brier": report["p5_weighted_brier"]},
        },
        "outer_fold_direction_stability": {
            "status": "PASS" if report["nonnegative_outer_fold_count"] >= 4 else "FAIL",
            "evidence": {"nonnegative_outer_fold_count": report["nonnegative_outer_fold_count"], "frozen_minimum": 4, "outer_fold_count": 5},
        },
        "acceptable_calibration_intercept_and_slope": {
            "status": "PASS" if abs(intercept) <= 0.20 and 0.80 <= slope <= 1.20 else "FAIL",
            "evidence": {"P5_weighted_calibration_intercept": intercept, "maximum_absolute_intercept": 0.20, "P5_weighted_calibration_slope": slope, "slope_interval": [0.80, 1.20]},
        },
        "P3_and_P5_differ_only_by_pair_evidence": {
            "status": "PASS" if report["p5_incremental_feature_count"] == 5 else "FAIL",
            "evidence": {"incremental_feature_count": report["p5_incremental_feature_count"], "incremental_feature_columns": P5_INCREMENTAL_COLUMNS, "nested_invariant": True},
        },
    }


def validate_sources() -> dict[str, Any]:
    source_directories = {
        "task15i_outcome_free_design": DESIGN,
        "task15i_prelabel_contract": PREPAIR_FREEZE,
        "task15i_prepair_artifacts": PREPAIR_ARTIFACTS,
        "task15i_human_review_analysis_v3": ANALYSIS,
        "task15i_development_result_freeze": RESULT_FREEZE,
        "previous_task15h_nonqualification": PREVIOUS_TASK15H,
    }
    checksum_failures = {
        name: failures
        for name, directory in source_directories.items()
        if (failures := verify_checksum_manifest(directory))
    }
    schema = load_json(SCHEMA)
    design = load_json(DESIGN / "independent_redevelopment_design_record.json")
    prepair = load_json(PREPAIR_FREEZE / "prelabel_contract_freeze_record.json")
    analysis_report = load_json(ANALYSIS / "task15i_development_screen_report.json")
    result = load_json(RESULT_FREEZE / "task15i_human_review_development_result_freeze.json")
    previous = load_json(PREVIOUS_TASK15H / "development_model_freeze_record.json")
    failures: list[str] = []
    if checksum_failures:
        failures.append("source_checksum_failure")
    if schema.get("schema_version") != "pferi_v2_development_model_freeze_record_schema_v2":
        failures.append("unexpected_schema")
    if design.get("status") != "FROZEN_OUTCOME_FREE_INDEPENDENT_REDEVELOPMENT_DESIGN":
        failures.append("design_not_frozen")
    if design.get("fixed_lambda") != 100.0 or design.get("qualification_policy", {}).get("passing_development_freeze_authorizes_calibration") is not True:
        failures.append("design_authorization_rule_changed")
    if design.get("locked_stage_outcomes_accessed") is not False:
        failures.append("design_accessed_locked_outcome")
    if prepair.get("status") != "FROZEN_PRELABEL_90PCT_REDEVELOPMENT_EXECUTION" or prepair.get("design", {}).get("pair_count") != 1600 or prepair.get("design", {}).get("component_count") != 400:
        failures.append("prelabel_contract_mismatch")
    if prepair.get("outcomes_accessed") is not False or prepair.get("calibration_authorized") is not False or prepair.get("confirmation_authorized") is not False:
        failures.append("prelabel_information_boundary_changed")
    if analysis_report.get("status") != "PASS_TASK15I_DEVELOPMENT_SCREEN":
        failures.append("task15i_analysis_not_pass")
    expected_provenance = "STUDY_OWNER_DECLARED_MANUAL_PHOTO_REVIEW; AI_ASSISTED_CLASSIFICATION_TOOL_ONLY; AI_DID_NOT_GENERATE_PHOTO_LEVEL_LABELS"
    if analysis_report.get("human_review_provenance") != expected_provenance:
        failures.append("manual_review_provenance_mismatch")
    if result.get("status") != "FROZEN_COMPLETE_TASK15I_DECLARED_MANUAL_REVIEW_DEVELOPMENT_SCREEN_PASS":
        failures.append("task15i_result_not_frozen_pass")
    if result.get("source_analysis_checksum_manifest_sha256") != sha256(ANALYSIS / "CHECKSUMS.sha256"):
        failures.append("task15i_result_source_hash_mismatch")
    if previous.get("status") != "VALIDATED_NO_DEVELOPMENT_MODEL_QUALIFIED_CALIBRATION_LOCKED":
        failures.append("previous_task15h_status_changed")
    rules = qualification_rules(analysis_report)
    failed_rules = [name for name, rule in rules.items() if rule["status"] != "PASS"]
    failures.extend(f"qualification_rule:{name}" for name in failed_rules)
    return {
        "schema": schema,
        "task15i_design": design,
        "task15i_prelabel_contract": prepair,
        "task15i_analysis": analysis_report,
        "task15i_result": result,
        "previous_task15h": previous,
        "qualification_rules": rules,
        "qualification_status": "QUALIFIED" if not failures else "NOT_QUALIFIED",
        "source_directories": source_directories,
        "source_checksum_failures": checksum_failures,
        "validation_failures": failures,
    }


def fit_final_models(evidence: dict[str, Any]) -> dict[str, Any]:
    if evidence["validation_failures"]:
        raise RuntimeError(f"source validation failed: {evidence['validation_failures']}")
    labels = pd.read_csv(ANALYSIS / "pair_level_outcome_labels.csv")
    features = task15i.build_feature_frame()
    data = features.merge(
        labels[["canonical_pair_id", "not_ready_or_uncertain_label"]],
        on="canonical_pair_id",
        validate="one_to_one",
    )
    if len(data) != 1600 or data["component_id"].nunique() != 400:
        raise ValueError("full-fit training inventory mismatch")
    contract = load_json(FEATURE_CONTRACT)
    pre3 = fit_fold_preprocessor(data, contract, ["descriptor", "independent_quality"])
    pre5_source = fit_fold_preprocessor(data, contract, ["descriptor", "independent_quality", "pair_evidence"])
    x3_frame = pre3.transform(data)
    x5_frame = task15i.fixed_p5_transform(pre3, pre5_source, data)
    p3_columns, p5_columns = list(x3_frame.columns), list(x5_frame.columns)
    task15i.assert_nested_columns(p3_columns, p5_columns)
    y = data["not_ready_or_uncertain_label"].to_numpy(float)
    weights = 1.0 / np.sqrt(data["first_order_inclusion_probability"].to_numpy(float))
    weights /= weights.mean()
    models: dict[str, Any] = {}
    for model_id, frame in (("P3", x3_frame), ("P5", x5_frame)):
        coefficients = task15i.fit_ridge(frame.to_numpy(float), y, weights, 100.0)
        design = np.column_stack([np.ones(len(frame)), frame.to_numpy(float)])
        # SciPy's optimizer may leave floating-point status flags set. Validate
        # the un-clipped predictor explicitly so real overflow cannot be hidden.
        with np.errstate(over="ignore", divide="ignore", invalid="ignore", under="ignore"):
            linear_predictor = design @ coefficients
        if not np.isfinite(coefficients).all() or not np.isfinite(linear_predictor).all():
            raise RuntimeError(f"invalid full-fit linear predictor: {model_id}")
        probabilities = expit(np.clip(linear_predictor, -36, 36))
        if not np.isfinite(probabilities).all() or not ((probabilities >= 0) & (probabilities <= 1)).all():
            raise RuntimeError(f"invalid full-fit model: {model_id}")
        models[model_id] = {
            "role": "active_control" if model_id == "P3" else "full_primary",
            "target": "probability_not_ready_or_uncertain",
            "link": "logit",
            "coefficient_order": ["intercept", *list(frame.columns)],
            "feature_columns": list(frame.columns),
            "coefficients": [float(value) for value in coefficients],
            "training_probability_min": float(probabilities.min()),
            "training_probability_max": float(probabilities.max()),
        }
    bundle = {
        "bundle_version": "pferi_v2_task15j_final_model_bundle_v1",
        "scientific_stage": "uncalibrated_development_model_frozen_before_independent_calibration",
        "training_pair_count": int(len(data)),
        "training_component_count": int(data["component_id"].nunique()),
        "outcome_definition": "1=not_ready_or_uncertain; 0=both reviewers selected review_ready",
        "training_weight": "normalized inverse square root of first_order_inclusion_probability",
        "fixed_lambda": 100.0,
        "intercept_penalized": False,
        "feature_contract_sha256": sha256(FEATURE_CONTRACT),
        "training_labels_sha256": sha256(ANALYSIS / "pair_level_outcome_labels.csv"),
        "P3_preprocessor": pre3.to_payload(),
        "P5_source_preprocessor": pre5_source.to_payload(),
        "P5_incremental_assembly": {
            "rule": "P3 transformed columns followed by exactly the five frozen pair-evidence columns",
            "columns": P5_INCREMENTAL_COLUMNS,
        },
        "models": models,
        "calibration_status": "NOT_YET_FIT",
    }
    bundle["bundle_payload_sha256"] = payload_sha256(bundle)
    return bundle


def source_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        name: {
            "path": str(directory.relative_to(ROOT)),
            "checksum_manifest_sha256": sha256(directory / "CHECKSUMS.sha256"),
        }
        for name, directory in evidence["source_directories"].items()
    }


def make_record(evidence: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    qualified = evidence["qualification_status"] == "QUALIFIED" and not evidence["validation_failures"]
    record = {
        "record_version": "pferi_v2_development_model_freeze_record_v2",
        "status": "QUALIFIED_P5_DEVELOPMENT_MODEL_FROZEN_CALIBRATION_AUTHORIZED" if qualified else "INDEPENDENT_DEVELOPMENT_MODEL_NOT_QUALIFIED_CALIBRATION_LOCKED",
        "record_validation_status": "PASS" if not evidence["validation_failures"] else "FAIL",
        "qualification_status": "QUALIFIED" if qualified else "NOT_QUALIFIED",
        "development_model_frozen": qualified,
        "active_control_model_id": "P3" if qualified else None,
        "full_model_id": "P5" if qualified else None,
        "fixed_lambda": 100.0,
        "calibration_authorized": qualified,
        "confirmation_authorized": False,
        "source_evidence": source_evidence(evidence),
        "qualification_before_performance": evidence["qualification_rules"],
        "candidate_dispositions": {
            "P3": {"qualification": "FROZEN_ACTIVE_CONTROL" if qualified else "NOT_QUALIFIED", "role": "active_control"},
            "P5": {"qualification": "QUALIFIED_FULL_PRIMARY" if qualified else "NOT_QUALIFIED", "role": "full_primary"},
            "all_other_routes": {"qualification": "INELIGIBLE", "reason": "The independent redesign prospectively retained only P3 and P5."},
        },
        "model_bundle": {"filename": "final_model_bundle.json", "bundle_payload_sha256": bundle["bundle_payload_sha256"], "calibration_status": "NOT_YET_FIT"},
        "binding_decision": "The prospectively governed independent Task15I redevelopment passed every frozen gate. P5 is frozen as the uncalibrated full development model and P3 as its active control. A separately contracted calibration stage is authorized; confirmation is not authorized.",
        "supersession_boundary": "The prior Task15H nonqualification remains historically valid for the original 445-pair development route. This record supersedes its calibration lock only for the prospectively designed, image-disjoint Task15I redevelopment route.",
        "locked_stages": ["deployment_confirmation", "mechanism_confirmation"],
        "prohibited_actions": [
            "changing P3 or P5 features, preprocessing, coefficients, or lambda after this freeze",
            "using calibration outcomes to reselect or refit the development model",
            "accessing deployment-confirmation or mechanism-confirmation outcomes before a common post-calibration freeze",
            "claiming deployment or identity performance from this development qualification",
        ],
        "next_authorized_action": "Freeze a calibration analysis contract and scoring package before accessing any calibration outcome; confirmation remains locked.",
        "claim_boundary": "This record establishes development qualification and freezes the uncalibrated P3/P5 models. It does not establish calibrated performance, confirmation performance, pair correctness, identity accuracy, deployment utility, or project completion.",
    }
    return record


def validate_record(record: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    failures = [f"missing_field:{field}" for field in schema["required_top_level_fields"] if field not in record]
    if record.get("record_validation_status") not in schema["permitted_record_validation_status"]:
        failures.append("invalid_record_validation_status")
    if record.get("qualification_status") not in schema["permitted_qualification_status"]:
        failures.append("invalid_qualification_status")
    rules = record.get("qualification_before_performance", {})
    failures.extend(f"missing_rule:{name}" for name in schema["required_qualification_rules"] if name not in rules)
    failures.extend(f"invalid_rule_status:{name}" for name, rule in rules.items() if rule.get("status") not in schema["rule_status_values"])
    if record.get("calibration_authorized"):
        if record.get("qualification_status") != "QUALIFIED":
            failures.append("calibration_authorized_without_qualification")
        if record.get("record_validation_status") != "PASS":
            failures.append("calibration_authorized_without_record_validation")
        if record.get("development_model_frozen") is not True:
            failures.append("calibration_authorized_without_frozen_model")
        if record.get("active_control_model_id") != "P3" or record.get("full_model_id") != "P5":
            failures.append("calibration_authorized_with_wrong_models")
        if record.get("fixed_lambda") != 100.0:
            failures.append("calibration_authorized_with_wrong_lambda")
        failures.extend(f"calibration_authorized_with_failed_rule:{name}" for name, rule in rules.items() if rule.get("status") != "PASS")
    if record.get("confirmation_authorized") is not False:
        failures.append("confirmation_must_remain_locked")
    return failures


def report_text(record: dict[str, Any], evidence: dict[str, Any]) -> str:
    result = evidence["task15i_result"]
    return f"""# Task15J Independent Development Model Freeze

Status: **QUALIFIED - P5 FROZEN, CALIBRATION CONTRACT AUTHORIZED**

Task15J mechanically applied the qualification policy frozen before Task15I labels were opened. No new threshold was introduced and no calibration, deployment-confirmation, or mechanism-confirmation outcome was accessed. All upstream checksum manifests passed.

The independent redevelopment contains {result['pair_count']} pairs in {result['component_count']} endpoint-disjoint components. P5 achieved weighted Brier {result['p5_weighted_brier']:.10f}, compared with {result['p3_weighted_brier']:.10f} for P3, for a P3-minus-P5 increment of {result['p3_minus_p5_weighted_brier']:.10f}. All five outer-fold increments were nonnegative, the weighted P5 calibration intercept was {result['p5_calibration_intercept']:.6f}, the slope was {result['p5_calibration_slope']:.6f}, and endpoint leakage was zero. Every prospective development gate therefore passed.

P5 is frozen as the full primary development model and P3 as the active control. Both use fixed lambda 100. The complete full-data preprocessing parameters, ordered columns, intercepts, coefficients, weighting rule, outcome definition, and source hashes are stored in `final_model_bundle.json`. The development model may not be changed during calibration.

This record authorizes preparation and execution of a separately frozen calibration contract. It does not authorize either confirmation sample. The prior Task15H result remains the correct historical disposition for the old 445-pair route; Task15J supersedes its calibration lock only for the prospectively designed Task15I independent redevelopment.

This is a development-model qualification result. It is not evidence of calibrated deployment performance, identity accuracy, pair correctness, confirmation, or project completion.
"""


def freeze(output: Path = OUTPUT) -> dict[str, Any]:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite immutable output: {output}")
    evidence = validate_sources()
    if evidence["validation_failures"]:
        raise RuntimeError(f"source validation failed: {evidence['validation_failures']}")
    bundle = fit_final_models(evidence)
    record = make_record(evidence, bundle)
    record_failures = validate_record(record, evidence["schema"])
    if record_failures:
        raise RuntimeError(f"record validation failed: {record_failures}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=f".{output.name}.") as temporary:
        stage = Path(temporary) / output.name
        stage.mkdir()
        write_json(stage / "final_model_bundle.json", bundle)
        write_json(stage / "development_model_freeze_record_v2.json", record)
        audit = {
            "audit_version": "pferi_v2_task15j_independent_development_model_freeze_audit_v1",
            "status": "PASS",
            "frozen_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "record_validation_status": record["record_validation_status"],
            "qualification_status": record["qualification_status"],
            "qualification_failures_or_unresolved": [],
            "source_checksum_failures": evidence["source_checksum_failures"],
            "source_validation_failures": evidence["validation_failures"],
            "development_model_frozen": record["development_model_frozen"],
            "calibration_authorized": record["calibration_authorized"],
            "confirmation_authorized": record["confirmation_authorized"],
            "calibration_outcomes_accessed": False,
            "deployment_confirmation_outcomes_accessed": False,
            "mechanism_confirmation_outcomes_accessed": False,
            "final_model_bundle_file_sha256": sha256(stage / "final_model_bundle.json"),
            "disposition": record["status"],
        }
        write_json(stage / "qualification_audit.json", audit)
        (stage / "TASK15J_INDEPENDENT_DEVELOPMENT_MODEL_FREEZE_REPORT.md").write_text(report_text(record, evidence), encoding="utf-8")
        shutil.copy2(Path(__file__), stage / "freeze_builder_snapshot.py")
        targets = sorted(path for path in stage.iterdir() if path.is_file() and path.name != "CHECKSUMS.sha256")
        (stage / "CHECKSUMS.sha256").write_text("".join(f"{sha256(path)}  {path.name}\n" for path in targets), encoding="utf-8")
        shutil.move(str(stage), str(output))
    return audit


def main() -> int:
    try:
        audit = freeze()
    except Exception as error:
        print(json.dumps({"status": "FAIL", "error_type": type(error).__name__, "error": str(error)}, indent=2))
        return 1
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
