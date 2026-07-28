#!/usr/bin/env python3
"""Freeze the PF-ERI v2 candidate-model route without fitting any model."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_VERSION = "pferi_v2_model_route_freeze_v1"
REQUIRED_MODEL_IDS = {
    "P0", "P1", "P2", "P3", "P4", "P5",
    "S1", "S2", "S3", "S4", "S5",
    "E1", "E2", "E3",
}
LOCKED_STAGES = {"calibration", "deployment_confirmation", "mechanism_confirmation"}
PRIMARY_DIAGNOSTIC_ONLY_COLUMNS = {
    "megadescriptor_similarity",
    "dinov2_similarity",
    "dual_descriptor_percentile_disagreement",
    "dual_descriptor_disagreement_within_role_percentile",
    "local_match_within_role_percentile",
    "best_rank_band",
    "retrieval_stratum_id",
    "development_evidence_state",
    "development_sampling_cell_id",
    "sampling_cell_id",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def assert_new_output_directory(path: Path) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to replace existing freeze directory: {path}")


def read_csv_header_and_count(path: Path) -> tuple[list[str], int]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise ValueError(f"empty development input: {path}") from exc
        row_count = sum(1 for _ in reader)
    if not header or any(not column.strip() for column in header):
        raise ValueError("development input has a blank or missing header")
    if len(header) != len(set(header)):
        raise ValueError("development input has duplicate columns")
    return header, row_count


def _predictive_columns(registry: dict[str, Any]) -> set[str]:
    blocks = registry.get("feature_blocks", {})
    columns: set[str] = set()
    for name, block in blocks.items():
        if name in {"intercept", "diagnostic_only"}:
            continue
        columns.update(str(column) for column in block.get("columns", []))
    return columns


def validate_registry(registry: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if registry.get("registry_version") != "pferi_v2_model_route_candidate_registry_v1":
        issues.append("unexpected registry_version")

    feature_blocks = registry.get("feature_blocks")
    models = registry.get("models")
    if not isinstance(feature_blocks, dict):
        return issues + ["feature_blocks must be an object"]
    if not isinstance(models, list):
        return issues + ["models must be a list"]

    model_ids = [str(model.get("model_id", "")) for model in models]
    if len(model_ids) != len(set(model_ids)):
        issues.append("duplicate model_id in candidate registry")
    missing_models = sorted(REQUIRED_MODEL_IDS - set(model_ids))
    extra_models = sorted(set(model_ids) - REQUIRED_MODEL_IDS)
    if missing_models:
        issues.append(f"missing required model IDs: {missing_models}")
    if extra_models:
        issues.append(f"unregistered extra model IDs: {extra_models}")

    block_names = set(feature_blocks)
    for model in models:
        unknown = sorted(set(model.get("feature_blocks", [])) - block_names)
        if unknown:
            issues.append(f"{model.get('model_id')} references unknown feature blocks: {unknown}")
        if model.get("preprocessing_policy") not in registry.get("preprocessing_policies", {}):
            issues.append(f"{model.get('model_id')} references unknown preprocessing policy")

    pair_evidence = set(feature_blocks.get("pair_evidence", {}).get("columns", []))
    diagnostic_leak = sorted(pair_evidence & PRIMARY_DIAGNOSTIC_ONLY_COLUMNS)
    if diagnostic_leak:
        issues.append(f"diagnostic-only columns entered primary pair evidence: {diagnostic_leak}")
    if pair_evidence != {"local_match_coverage_fraction", "local_match_measurement_failure"}:
        issues.append("pair_evidence block must contain only frozen local-match coverage and failure state")

    predictive_columns = _predictive_columns(registry)
    label_like = sorted(
        column for column in predictive_columns
        if "label" in column.lower() or column.lower().startswith("final_")
    )
    if label_like:
        issues.append(f"outcome-like columns entered predictive feature blocks: {label_like}")

    by_id = {str(model.get("model_id")): model for model in models}
    if {"P3", "P5"} <= set(by_id):
        p3, p5 = by_id["P3"], by_id["P5"]
        if p3.get("family") != "l2_logistic" or p5.get("family") != "l2_logistic":
            issues.append("P3 and P5 must both use l2_logistic")
        if p3.get("family") != p5.get("family"):
            issues.append("P3 and P5 model families differ")
        if p3.get("preprocessing_policy") != p5.get("preprocessing_policy"):
            issues.append("P3 and P5 preprocessing policies differ")
        p3_blocks = set(p3.get("feature_blocks", []))
        p5_blocks = set(p5.get("feature_blocks", []))
        if p5_blocks - p3_blocks != {"pair_evidence"} or p3_blocks - p5_blocks:
            issues.append("P3 and P5 must differ only by pair_evidence")
        if not p3.get("confirmation_eligible") or not p5.get("confirmation_eligible"):
            issues.append("P3 and P5 must be the confirmation-eligible nested pair")

    confirmation_ids = {
        str(model.get("model_id")) for model in models if model.get("confirmation_eligible")
    }
    if confirmation_ids != {"P3", "P5"}:
        issues.append(f"only P3 and P5 may be confirmation eligible: {sorted(confirmation_ids)}")

    primary = registry.get("primary_comparison", {})
    if primary.get("full_model_id") != "P5" or primary.get("active_control_model_id") != "P3":
        issues.append("primary comparison must be P5 versus P3")
    if primary.get("only_incremental_feature_block") != "pair_evidence":
        issues.append("primary comparison increment must be pair_evidence")

    rules = registry.get("global_training_rules", {})
    if str(rules.get("class_rebalancing", "")).lower() != "none":
        issues.append("class rebalancing must remain none")
    if "component-disjoint" not in str(rules.get("outer_split", "")):
        issues.append("outer split must be endpoint-component-disjoint")
    if "component-disjoint" not in str(rules.get("inner_split", "")):
        issues.append("inner split must be endpoint-component-disjoint")

    grid = registry.get("complexity_budgets", {}).get("l2_logistic_lambda_grid", [])
    if not grid or any(float(value) <= 0 for value in grid):
        issues.append("ridge lambda grid must contain positive values")
    if list(grid) != sorted(set(grid)):
        issues.append("ridge lambda grid must be unique and ascending")
    return issues


def build_freeze_record(
    registry_path: Path,
    development_path: Path,
    stage_gate_path: Path,
) -> dict[str, Any]:
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    issues = validate_registry(registry)
    if issues:
        raise ValueError("registry validation failed: " + "; ".join(issues))

    stage_gate = json.loads(stage_gate_path.read_text(encoding="utf-8"))
    if stage_gate.get("current_open_stage") != "development":
        raise ValueError("development is not the only open analysis stage")
    stage_rules = stage_gate.get("rules", {})
    unlocked = sorted(
        stage for stage in LOCKED_STAGES
        if stage_rules.get(stage, {}).get("status") != "LOCKED"
    )
    if unlocked:
        raise ValueError(f"locked analysis stages are not locked: {unlocked}")

    header, row_count = read_csv_header_and_count(development_path)
    missing_features = sorted(_predictive_columns(registry) - set(header))
    if missing_features:
        raise ValueError(f"development input lacks registered feature columns: {missing_features}")
    required_graph_columns = {"canonical_pair_id", "endpoint_a_image_id", "endpoint_b_image_id"}
    missing_graph = sorted(required_graph_columns - set(header))
    if missing_graph:
        raise ValueError(f"development input lacks graph columns: {missing_graph}")

    return {
        "freeze_contract_version": CONTRACT_VERSION,
        "status": "FROZEN_PASS",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "registry_version": registry["registry_version"],
        "registry_sha256": sha256_file(registry_path),
        "development_input_sha256": sha256_file(development_path),
        "development_row_count": row_count,
        "development_column_count": len(header),
        "stage_gate_sha256": sha256_file(stage_gate_path),
        "current_open_stage": "development",
        "locked_stage_label_columns_read": 0,
        "development_label_values_copied": False,
        "model_count": len(registry["models"]),
        "primary_comparison": "P5_vs_P3",
        "model_fitting_performed": False,
        "calibration_performed": False,
        "confirmation_prediction_performed": False,
        "next_gate": registry["next_gate"],
        "claim_boundary": (
            "This freeze registers candidate roles and scientific invariants only. "
            "It does not select a fitted model, reveal locked outcomes, or authorize calibration or confirmation."
        ),
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run(
    registry_path: Path,
    development_path: Path,
    stage_gate_path: Path,
    output_dir: Path,
    *,
    expected_development_rows: int = 445,
) -> dict[str, Any]:
    assert_new_output_directory(output_dir)
    record = build_freeze_record(registry_path, development_path, stage_gate_path)
    if record["development_row_count"] != expected_development_rows:
        raise ValueError(
            f"development row count mismatch: {record['development_row_count']} != {expected_development_rows}"
        )

    output_dir.mkdir(parents=True)
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    frozen_registry = output_dir / "candidate_model_registry_frozen.json"
    validation_audit = output_dir / "registry_validation_audit.json"
    freeze_record = output_dir / "model_route_freeze_record.json"
    write_json(frozen_registry, registry)
    write_json(
        validation_audit,
        {
            "audit_version": "pferi_v2_model_route_registry_validation_v1",
            "status": "PASS",
            "issue_count": 0,
            "registered_model_count": len(registry["models"]),
            "required_model_ids_present": sorted(REQUIRED_MODEL_IDS),
            "confirmation_eligible_model_ids": ["P3", "P5"],
            "primary_pair_differs_only_by_pair_evidence": True,
            "class_rebalancing": "none",
            "row_random_cross_validation": "prohibited",
            "locked_stage_label_columns_read": 0,
        },
    )
    record["frozen_registry_sha256"] = sha256_file(frozen_registry)
    record["registry_validation_audit_sha256"] = sha256_file(validation_audit)
    record["freezer_sha256"] = sha256_file(Path(__file__))
    write_json(freeze_record, record)

    checksum_paths = [frozen_registry, validation_audit, freeze_record]
    checksum_lines = [f"{sha256_file(path)}  {path.name}" for path in checksum_paths]
    (output_dir / "CHECKSUMS.sha256").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    return record


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--registry",
        type=Path,
        default=ROOT / "schemas/pferi_v2/model_route_candidate_registry_v1.json",
    )
    parser.add_argument(
        "--development-input",
        type=Path,
        default=ROOT
        / "archive/pferi_v2/task_runs/dual_sample_confirmation/2026-07-22_stage_isolated_analysis_inputs_v1"
        / "development_open/development_modeling_input.csv",
    )
    parser.add_argument(
        "--stage-gate",
        type=Path,
        default=ROOT
        / "archive/pferi_v2/task_runs/dual_sample_confirmation/2026-07-22_stage_isolated_analysis_inputs_v1"
        / "stage_gate_contract.json",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-development-rows", type=int, default=445)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    record = run(
        args.registry.resolve(),
        args.development_input.resolve(),
        args.stage_gate.resolve(),
        args.output_dir.resolve(),
        expected_development_rows=args.expected_development_rows,
    )
    print(json.dumps(record, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
