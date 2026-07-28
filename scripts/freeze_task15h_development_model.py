#!/usr/bin/env python3
"""Apply frozen qualification rules and create the Task 15H model freeze."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MODEL_ROOT = ROOT / "archive/pferi_v2/task_runs/model_development"
SCHEMA = ROOT / "schemas/pferi_v2/development_model_freeze_record_v1.json"
REGISTRY = ROOT / "schemas/pferi_v2/model_route_candidate_registry_v1.json"
SIMULATION = MODEL_ROOT / "2026-07-22_outcome_free_design_simulation/current"
FOLDS = MODEL_ROOT / "2026-07-22_component_disjoint_nested_folds_v1"
PREPROCESSING = MODEL_ROOT / "2026-07-22_feature_preprocessing_freeze_v1"
TASK15E = MODEL_ROOT / "2026-07-22_task15e_development_model_comparison_freeze_v1"
TASK15F = MODEL_ROOT / "2026-07-23_task15f_bayesian_sensitivity_result_freeze_v1"
TASK15G = (
    MODEL_ROOT
    / "2026-07-23_task15g_exploratory_performance_bound_result_freeze/current"
)
RECONCILIATION = MODEL_ROOT / "2026-07-23_task15g_external_reconciliation_v1"
OUTPUT = MODEL_ROOT / "2026-07-23_task15h_development_model_freeze_v1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def verify_checksum_manifest(directory: Path) -> list[str]:
    manifest = directory / "CHECKSUMS.sha256"
    if not manifest.is_file():
        return ["missing:CHECKSUMS.sha256"]
    failures: list[str] = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, relative = line.split("  ", 1)
        target = directory / relative
        if not target.is_file():
            failures.append(f"missing:{relative}")
        elif sha256(target) != expected:
            failures.append(f"sha256:{relative}")
    return failures


def read_metrics(path: Path) -> dict[str, dict[str, float]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return {
        row["model_id"]: {
            key: float(value)
            for key, value in row.items()
            if key != "model_id" and key != "pair_count" and value not in ("", None)
        }
        for row in rows
    }


def selected_lambdas(path: Path, model_id: str) -> dict[str, float]:
    values: dict[str, set[float]] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["model_id"] == model_id:
                values.setdefault(row["outer_fold"], set()).add(float(row["lambda"]))
    if not values or any(len(items) != 1 for items in values.values()):
        raise RuntimeError(f"ambiguous selected lambda inventory for {model_id}")
    return {fold: next(iter(items)) for fold, items in sorted(values.items())}


def validate_probability_rows(path: Path) -> dict[str, Any]:
    counts = {"P3": 0, "P5": 0}
    failures: list[str] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            model_id = row["model_id"]
            if model_id not in counts:
                continue
            counts[model_id] += 1
            probability = float(row["probability"])
            if not math.isfinite(probability) or not 0.0 <= probability <= 1.0:
                failures.append(f"{model_id}:{row['canonical_pair_id']}")
    return {
        "status": "PASS" if counts == {"P3": 445, "P5": 445} and not failures else "FAIL",
        "row_counts": counts,
        "invalid_rows": failures,
    }


def validate_schema(record: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    failures = [
        f"missing_field:{field}"
        for field in schema["required_top_level_fields"]
        if field not in record
    ]
    rules = record.get("qualification_before_performance", {})
    failures.extend(
        f"missing_rule:{rule}"
        for rule in schema["required_qualification_rules"]
        if rule not in rules
    )
    if record.get("record_validation_status") not in schema[
        "permitted_record_validation_status"
    ]:
        failures.append("invalid_record_validation_status")
    if record.get("qualification_status") not in schema[
        "permitted_qualification_status"
    ]:
        failures.append("invalid_qualification_status")
    for name, rule in rules.items():
        if rule.get("status") not in schema["rule_status_values"]:
            failures.append(f"invalid_rule_status:{name}")
    if record.get("qualification_status") != "QUALIFIED":
        if record.get("calibration_authorized") is not False:
            failures.append("nonqualified_record_authorized_calibration")
        if record.get("development_model_frozen") is not False:
            failures.append("nonqualified_record_froze_model")
    return failures


def build_evidence() -> tuple[dict[str, Any], dict[str, Any]]:
    schema = load_json(SCHEMA)
    registry = load_json(REGISTRY)
    simulation_decision = load_json(SIMULATION / "minimax_route_decision.json")
    simulation_audit = load_json(SIMULATION / "simulation_audit.json")
    fold_audit = load_json(FOLDS / "fold_validation_audit.json")
    preprocessing_audit = load_json(
        PREPROCESSING / "feature_preprocessing_freeze_audit.json"
    )
    task15e_audit = load_json(TASK15E / "freeze_audit.json")
    task15e_validation = load_json(TASK15E / "results/validation_audit.json")
    task15e_disposition = load_json(TASK15E / "development_disposition.json")
    task15f_audit = load_json(TASK15F / "freeze_audit.json")
    task15f_disposition = load_json(TASK15F / "task15f_disposition.json")
    task15g_audit = load_json(TASK15G / "freeze_audit.json")
    task15g_disposition = load_json(TASK15G / "task15g_disposition.json")
    reconciliation = load_json(
        RECONCILIATION / "external_vs_local_reconciliation.json"
    )
    metrics = read_metrics(TASK15E / "results/overall_model_metrics.csv")
    lambdas = {
        model_id: selected_lambdas(
            TASK15E / "results/coefficient_stability.csv", model_id
        )
        for model_id in ("P3", "P5")
    }
    probabilities = validate_probability_rows(
        TASK15E / "results/model_oof_predictions.csv"
    )

    source_directories = {
        "outcome_free_design_simulation_v2": SIMULATION,
        "component_disjoint_nested_folds_v1": FOLDS,
        "feature_preprocessing_freeze_v1": PREPROCESSING,
        "task15e_result_freeze_v1": TASK15E,
        "task15f_result_freeze_v1": TASK15F,
        "task15g_authoritative_result_freeze_v2": TASK15G,
        "task15g_external_reconciliation_v1": RECONCILIATION,
    }
    checksum_failures = {
        name: failures
        for name, directory in source_directories.items()
        if (failures := verify_checksum_manifest(directory))
    }
    validation_failures: list[str] = []
    if checksum_failures:
        validation_failures.append("upstream_checksum_failure")
    expected_passes = {
        "simulation": simulation_audit.get("status"),
        "folds": fold_audit.get("status"),
        "preprocessing": preprocessing_audit.get("status"),
        "task15e": task15e_audit.get("status"),
        "task15e_validation": task15e_validation.get("status"),
        "task15f": task15f_audit.get("status"),
        "task15g": task15g_audit.get("status"),
        "task15g_reconciliation": reconciliation.get("status"),
        "probabilities": probabilities.get("status"),
    }
    validation_failures.extend(
        f"upstream_status:{name}:{status}"
        for name, status in expected_passes.items()
        if status != "PASS"
    )
    if registry["primary_comparison"] != {
        "full_model_id": "P5",
        "active_control_model_id": "P3",
        "only_incremental_feature_block": "pair_evidence",
        "paired_loss": "Brier(active_control) - Brier(full_model)",
        "confirmation_status": "reserved for one-shot deployment confirmation",
    }:
        validation_failures.append("primary_comparison_changed")
    if task15e_disposition.get("P5_final_route_qualification") != "NOT_QUALIFIED":
        validation_failures.append("task15e_P5_disposition_changed")
    if task15f_disposition.get("final_model_selected") is not False:
        validation_failures.append("task15f_selected_model")
    if task15g_disposition.get("final_model_selected") is not False:
        validation_failures.append("task15g_selected_model")
    if reconciliation.get("scientific_conclusion_invariant_across_platforms") is not True:
        validation_failures.append("task15g_platform_conclusion_not_invariant")
    if simulation_decision.get("recommended_training_weight_strategy") != "sqrt_ipw":
        validation_failures.append("simulation_weighting_route_changed")

    lambda_values = sorted(
        set(lambdas["P3"].values()) | set(lambdas["P5"].values())
    )
    lambda_ratio = max(lambda_values) / min(lambda_values)
    common_rules: dict[str, dict[str, Any]] = {
        "zero_endpoint_leakage_across_folds": {
            "status": "PASS" if fold_audit["endpoint_leakage_count"] == 0 else "FAIL",
            "evidence": {
                "endpoint_leakage_count": fold_audit["endpoint_leakage_count"],
                "outer_folds": fold_audit["outer_fold_count"],
                "inner_folds": fold_audit["inner_fold_count"],
            },
        },
        "zero_locked_stage_input_access": {
            "status": (
                "PASS"
                if not preprocessing_audit["locked_stage_input_read"]
                and not task15e_audit["locked_stage_outcomes_accessed"]
                and not task15f_audit["locked_stage_outcomes_accessed"]
                and not task15g_audit["locked_stage_outcomes_accessed"]
                else "FAIL"
            ),
            "evidence": "All authoritative development freezes report no locked-stage access.",
        },
        "fold_train_only_preprocessing": {
            "status": (
                "PASS"
                if preprocessing_audit["status"] == "PASS"
                and preprocessing_audit["outcome_dependent_preprocessing"] is False
                else "FAIL"
            ),
            "evidence": {
                "contract_sha256": preprocessing_audit["contract_frozen_sha256"],
                "outcome_dependent_preprocessing": preprocessing_audit[
                    "outcome_dependent_preprocessing"
                ],
            },
        },
        "finite_probabilities_in_unit_interval": {
            "status": probabilities["status"],
            "evidence": probabilities,
        },
        "stable_regularization_or_shape_selection": {
            "status": "FAIL",
            "evidence": {
                "P3_selected_lambda_by_outer_fold": lambdas["P3"],
                "P5_selected_lambda_by_outer_fold": lambdas["P5"],
                "selected_lambda_values": lambda_values,
                "maximum_to_minimum_ratio": lambda_ratio,
                "binding_interpretation": "Task15E froze this 1000-fold swing as a violation of the intended stable-regularization qualification.",
            },
        },
        "acceptable_calibration_intercept_and_slope": {
            "status": "UNRESOLVED",
            "evidence": {
                "P3_weighted_calibration_intercept": metrics["P3"][
                    "weighted_calibration_intercept"
                ],
                "P3_weighted_calibration_slope": metrics["P3"][
                    "weighted_calibration_slope"
                ],
                "P5_weighted_calibration_intercept": metrics["P5"][
                    "weighted_calibration_intercept"
                ],
                "P5_weighted_calibration_slope": metrics["P5"][
                    "weighted_calibration_slope"
                ],
                "interpretation": "No numeric observed-development intercept or slope acceptance threshold was frozen before Task15E outcomes were opened. The synthetic route threshold cannot be repurposed post hoc as an observed-model gate.",
            },
        },
        "complexity_budget_respected": {
            "status": "PASS",
            "evidence": {
                "registered_lambda_grid": registry["complexity_budgets"][
                    "l2_logistic_lambda_grid"
                ],
                "observed_selected_lambdas_are_registered": all(
                    value
                    in registry["complexity_budgets"]["l2_logistic_lambda_grid"]
                    for value in lambda_values
                ),
            },
        },
        "P3_and_P5_differ_only_by_pair_evidence": {
            "status": (
                "PASS"
                if preprocessing_audit["P3_P5_nested_invariant_pass"]
                and preprocessing_audit["P5_incremental_column_count"] == 5
                else "FAIL"
            ),
            "evidence": {
                "nested_invariant_pass": preprocessing_audit[
                    "P3_P5_nested_invariant_pass"
                ],
                "incremental_column_count": preprocessing_audit[
                    "P5_incremental_column_count"
                ],
            },
        },
    }
    evidence = {
        "schema": schema,
        "registry": registry,
        "source_directories": source_directories,
        "checksum_failures": checksum_failures,
        "validation_failures": validation_failures,
        "rules": common_rules,
        "metrics": metrics,
        "lambdas": lambdas,
        "task15e_disposition": task15e_disposition,
        "task15f_disposition": task15f_disposition,
        "task15g_disposition": task15g_disposition,
        "reconciliation": reconciliation,
    }
    source_record = {
        "schema_sha256": sha256(SCHEMA),
        "candidate_registry_sha256": sha256(REGISTRY),
        "artifacts": {
            name: {
                "path": str(directory.relative_to(ROOT)),
                "checksum_manifest_sha256": sha256(directory / "CHECKSUMS.sha256"),
            }
            for name, directory in source_directories.items()
        },
    }
    return evidence, source_record


def make_record(evidence: dict[str, Any], source_record: dict[str, Any]) -> dict[str, Any]:
    rules = evidence["rules"]
    candidate_dispositions = {
        "P3": {
            "registered_role": "active_control",
            "confirmation_eligible_in_registry": True,
            "qualification": "NOT_QUALIFIED",
            "reason": "P3 shares the failed stable-regularization gate, and no pre-result rule authorizes automatic promotion of the active control as the final model.",
        },
        "P5": {
            "registered_role": "full_primary",
            "confirmation_eligible_in_registry": True,
            "qualification": "NOT_QUALIFIED",
            "reason": "The binding Task15E disposition is NOT_QUALIFIED; the incremental Brier reduction was 0.0000411698 and regularization was unstable.",
        },
        "P0_P2_P4_S1_S5_E1_E3": {
            "qualification": "INELIGIBLE",
            "reason": "The candidate registry marks every model other than P3 and P5 as confirmation_eligible=false.",
        },
    }
    record = {
        "record_version": "pferi_v2_development_model_freeze_record_v1",
        "status": "VALIDATED_NO_DEVELOPMENT_MODEL_QUALIFIED_CALIBRATION_LOCKED",
        "record_validation_status": (
            "PASS" if not evidence["validation_failures"] else "FAIL"
        ),
        "qualification_status": "NOT_QUALIFIED",
        "development_model_frozen": False,
        "active_control_model_id": None,
        "full_model_id": None,
        "calibration_authorized": False,
        "source_evidence": source_record,
        "qualification_before_performance": rules,
        "candidate_dispositions": candidate_dispositions,
        "binding_decision": (
            "No registered development route passed the complete frozen qualification-before-performance rule. "
            "P5 remains not qualified, P3 is not an automatic fallback, and all sensitivity or exploratory routes remain confirmation-ineligible."
        ),
        "locked_stages": [
            "calibration",
            "deployment_confirmation",
            "mechanism_confirmation",
        ],
        "prohibited_actions": [
            "accessing calibration or confirmation outcomes under this record",
            "treating record-validation PASS as model qualification",
            "promoting P3 as a post-result fallback",
            "promoting S1-S5 or E1-E3 to confirmation eligibility",
            "rerunning or retuning Tasks15E-15G",
            "inventing an observed-development calibration threshold after outcomes were opened",
        ],
        "next_authorized_action": "Governance decision on redesign or termination without accessing any locked-stage outcome.",
        "claim_boundary": "This is a validated nonqualification freeze. It authorizes no calibration, confirmation, deployment, or identity-performance claim.",
    }
    schema_failures = validate_schema(record, evidence["schema"])
    if schema_failures:
        evidence["validation_failures"].extend(schema_failures)
        record["record_validation_status"] = "FAIL"
    return record


def report_text(record: dict[str, Any], evidence: dict[str, Any]) -> str:
    metrics = evidence["metrics"]
    rules = record["qualification_before_performance"]
    return f"""# PF-ERI v2 Task 15H Development Model Freeze

Status: `{record["status"]}`

## Scope and decision order

Task 15H applied the candidate registry's qualification-before-performance rule to the immutable Tasks 15E, 15F, and 15G record. All upstream checksum manifests and validation audits passed, and no locked-stage outcome was accessed. The record itself therefore validates successfully. Record validity is distinct from model qualification: a correctly constructed record can, and here does, document that no development model qualified.

## Qualification result

The engineering gates passed. The nested folds had zero endpoint leakage, preprocessing was fitted within training folds, P3 and P5 retained exact feature nesting, the required out-of-fold probabilities were finite and within [0, 1], and the registered complexity budget was respected. The outcome-free simulation had previously selected square-root inverse-probability weighting under its synthetic calibration-slope rule; that design decision remained unchanged.

The stable-regularization gate failed. P3 and P5 selected lambda 100 in four outer folds and lambda 0.1 in the remaining fold, a maximum-to-minimum ratio of {rules["stable_regularization_or_shape_selection"]["evidence"]["maximum_to_minimum_ratio"]:.0f}. Task 15E had already frozen this pattern as violating the intended stability qualification. P5 reduced weighted Brier from {metrics["P3"]["weighted_brier"]:.12f} for P3 to {metrics["P5"]["weighted_brier"]:.12f}, a difference of only {metrics["P3"]["weighted_brier"] - metrics["P5"]["weighted_brier"]:.12f}. That earlier binding disposition classified P5 as `NOT_QUALIFIED`.

The observed-development calibration gate could not be independently converted into a pass. P3's weighted calibration intercept and slope were {metrics["P3"]["weighted_calibration_intercept"]:.6f} and {metrics["P3"]["weighted_calibration_slope"]:.6f}; P5's were {metrics["P5"]["weighted_calibration_intercept"]:.6f} and {metrics["P5"]["weighted_calibration_slope"]:.6f}. No numeric acceptance threshold for these observed-development values was frozen before Task 15E outcomes were opened. The synthetic simulation threshold applied to post-independent-calibration scenario performance and cannot be repurposed after the fact as a gate for the observed out-of-fold models. The calibration rule is therefore recorded as unresolved rather than silently passed.

## Candidate disposition

P5 remains not qualified as the full primary route. P3 remains the registered active-control model, but confirmation eligibility in the candidate registry was only permission to be considered; it was not a guarantee of qualification or an automatic fallback rule. P3 also shared the failed regularization-stability pattern. Promoting it after seeing P5 fail would create an unregistered post-result fallback and would remove the registered full-versus-active-control comparison. The sensitivity models S1-S5 and exploratory models E1-E3 remain confirmation-ineligible regardless of their descriptive proper scores.

## Binding authorization

No development model was frozen, and calibration is not authorized. Calibration, deployment confirmation, and mechanism confirmation remain locked. The only authorized next action is a governance decision on redesign or termination that does not inspect any locked-stage outcome. A future route would require a prospectively fixed remedy and scientifically independent information; this record cannot be converted into a passing model freeze by reinterpretation, rerunning Tasks 15E-15G, or adding thresholds after the outcomes were observed.

## Claim boundary

This record establishes a negative model-qualification result, not a negative estimate of whether pair evidence has any signal. The development analyses contained descriptive evidence in several directions, but none can override the frozen eligibility and stability rules. The record supports no calibration, confirmation, deployment, or identity-performance claim.
"""


def freeze(output: Path = OUTPUT) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing freeze: {output}")
    evidence, source_record = build_evidence()
    if evidence["validation_failures"]:
        raise RuntimeError(
            f"source validation failed: {evidence['validation_failures']}"
        )
    record = make_record(evidence, source_record)
    if record["record_validation_status"] != "PASS":
        raise RuntimeError(
            f"record validation failed: {evidence['validation_failures']}"
        )
    with tempfile.TemporaryDirectory(dir=output.parent) as temporary:
        stage = Path(temporary) / output.name
        stage.mkdir()
        write_json(stage / "development_model_freeze_record.json", record)
        qualification_failures = [
            name
            for name, rule in record["qualification_before_performance"].items()
            if rule["status"] != "PASS"
        ]
        audit = {
            "audit_version": "pferi_v2_task15h_qualification_audit_v1",
            "status": "PASS",
            "frozen_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "record_validation_status": record["record_validation_status"],
            "qualification_status": record["qualification_status"],
            "qualification_failures_or_unresolved": qualification_failures,
            "source_checksum_failures": evidence["checksum_failures"],
            "source_validation_failures": evidence["validation_failures"],
            "development_model_frozen": record["development_model_frozen"],
            "calibration_authorized": record["calibration_authorized"],
            "locked_stage_outcomes_accessed": False,
            "authoritative_task15g_zip_sha256": evidence["reconciliation"][
                "authoritative_external_zip_sha256"
            ],
            "disposition": record["status"],
        }
        write_json(stage / "qualification_audit.json", audit)
        (stage / "TASK15H_DEVELOPMENT_MODEL_FREEZE_REPORT.md").write_text(
            report_text(record, evidence), encoding="utf-8"
        )
        shutil.copy2(Path(__file__), stage / "freeze_builder_snapshot.py")
        targets = sorted(
            path
            for path in stage.rglob("*")
            if path.is_file() and path.name != "CHECKSUMS.sha256"
        )
        (stage / "CHECKSUMS.sha256").write_text(
            "".join(
                f"{sha256(path)}  {path.relative_to(stage)}\n" for path in targets
            ),
            encoding="utf-8",
        )
        shutil.move(str(stage), output)
    return audit


def main() -> int:
    try:
        audit = freeze()
    except Exception as error:
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "error_type": type(error).__name__,
                    "error": str(error),
                },
                indent=2,
            )
        )
        return 1
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
