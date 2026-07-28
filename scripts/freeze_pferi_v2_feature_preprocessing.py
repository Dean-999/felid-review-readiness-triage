#!/usr/bin/env python3
"""Freeze PF-ERI v2 feature lineage and fold-train preprocessing before fitting."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd

try:
    from scripts.pferi_v2_fold_preprocessor import fit_fold_preprocessor
except ModuleNotFoundError:  # direct execution places scripts/ rather than repo root on sys.path
    from pferi_v2_fold_preprocessor import fit_fold_preprocessor


ROOT = Path(__file__).resolve().parents[1]
PREDICTIVE_BLOCKS = {"descriptor", "independent_quality", "pair_evidence"}
LOCKED_STAGES = {"calibration", "deployment_confirmation", "mechanism_confirmation"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_header_count(path: Path) -> tuple[list[str], int]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise ValueError("empty development input") from exc
        count = sum(1 for _ in reader)
    if not header or len(header) != len(set(header)) or any(not value for value in header):
        raise ValueError("invalid development input header")
    return header, count


def _contract_block_columns(contract: dict[str, Any], block: str) -> list[str]:
    spec = contract.get("feature_blocks", {}).get(block, {})
    return list(map(str, spec.get("continuous", []))) + list(map(str, spec.get("categorical", [])))


def validate_contract(contract: dict[str, Any], model_registry: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if contract.get("contract_version") != "pferi_v2_feature_preprocessing_contract_v1":
        issues.append("unexpected preprocessing contract version")
    if contract.get("status") != "FROZEN_BEFORE_MODEL_FITTING":
        issues.append("preprocessing contract is not frozen before fitting")
    if model_registry.get("registry_version") != contract.get("source_model_registry_version"):
        issues.append("source model registry version mismatch")
    if set(contract.get("feature_blocks", {})) != PREDICTIVE_BLOCKS:
        issues.append("preprocessing contract predictive blocks mismatch")
    for block in sorted(PREDICTIVE_BLOCKS):
        contract_columns = set(_contract_block_columns(contract, block))
        registry_columns = set(
            map(str, model_registry.get("feature_blocks", {}).get(block, {}).get("columns", []))
        )
        if contract_columns != registry_columns:
            issues.append(f"feature lineage mismatch for {block}")
    all_predictors = {
        column for block in PREDICTIVE_BLOCKS for column in _contract_block_columns(contract, block)
    }
    diagnostic = set(
        map(
            str,
            model_registry.get("feature_blocks", {}).get("diagnostic_only", {}).get("columns", []),
        )
    )
    if all_predictors & diagnostic:
        issues.append("diagnostic-only field entered predictive preprocessing")
    if any("outcome" in column.lower() or "label" in column.lower() for column in all_predictors):
        issues.append("outcome-like field entered predictive preprocessing")
    if contract.get("permitted_outcome_column") != "review_ready_label":
        issues.append("unexpected permitted development outcome")
    prohibited = " ".join(map(str, contract.get("prohibited", []))).lower()
    for token in ["global preprocessing", "outcome-target", "smote", "balanced class"]:
        if token not in prohibited:
            issues.append(f"missing prohibited preprocessing rule: {token}")
    p3 = next((row for row in model_registry.get("models", []) if row.get("model_id") == "P3"), None)
    p5 = next((row for row in model_registry.get("models", []) if row.get("model_id") == "P5"), None)
    if not p3 or not p5:
        issues.append("P3/P5 models missing")
    elif list(p5.get("feature_blocks", [])) != list(p3.get("feature_blocks", [])) + ["pair_evidence"]:
        issues.append("P3/P5 block ordering is not strictly nested")
    return issues


def canonical_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "fixture_row": ["train_1", "train_2", "train_3", "train_4", "probe_missing", "probe_unknown"],
            "megadescriptor_within_role_percentile": [0.1, 0.8, np.nan, 0.4, np.nan, 0.9],
            "dinov2_within_role_percentile": [0.2, np.nan, 0.7, 0.5, np.nan, 0.1],
            "descriptor_support_category": [
                "both", "megadescriptor_only", "dinov2_only", "both", None, "future_descriptor_level"
            ],
            "endpoint_native_pixel_quality_percentile_min": [0.3, 0.6, 0.9, 0.1, np.nan, 0.5],
            "endpoint_sharpness_quality_percentile_min": [0.4, 0.7, 0.8, 0.2, np.nan, 0.6],
            "endpoint_exposure_quality_percentile_min": [0.5, 0.8, 0.7, 0.3, np.nan, 0.4],
            "endpoint_quality_measurement_failure": [False, False, False, True, None, "future_bool"],
            "endpoint_frozen_quality_stress": [False, True, False, True, None, "future_stress"],
            "local_match_coverage_fraction": [0.05, 0.2, 0.7, 0.4, np.nan, 0.9],
            "local_match_measurement_failure": [False, False, False, True, None, "future_failure"],
        }
    )


def _feature_manifest(contract: dict[str, Any], model_registry: dict[str, Any]) -> pd.DataFrame:
    registry_roles = model_registry["feature_blocks"]
    rows: list[dict[str, Any]] = []
    for block in ["descriptor", "independent_quality", "pair_evidence"]:
        spec = contract["feature_blocks"][block]
        for kind in ["continuous", "categorical"]:
            for column in spec[kind]:
                rows.append(
                    {
                        "feature_block": block,
                        "source_column": column,
                        "feature_type": kind,
                        "registered_role": registry_roles[block]["role"],
                        "primary_full_only": block == "pair_evidence",
                        "diagnostic_only": False,
                    }
                )
    return pd.DataFrame(rows)


def run(
    contract_path: Path,
    model_registry_path: Path,
    development_path: Path,
    stage_gate_path: Path,
    fold_audit_path: Path,
    fold_outer_path: Path,
    fold_nested_path: Path,
    simulation_decision_path: Path,
    output_dir: Path,
    *,
    expected_rows: int = 445,
) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(f"refusing to replace existing preprocessing freeze: {output_dir}")
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    model_registry = json.loads(model_registry_path.read_text(encoding="utf-8"))
    issues = validate_contract(contract, model_registry)
    if issues:
        raise ValueError("preprocessing contract validation failed: " + "; ".join(issues))
    stage_gate = json.loads(stage_gate_path.read_text(encoding="utf-8"))
    if stage_gate.get("current_open_stage") != "development":
        raise ValueError("development is not the open analysis stage")
    unlocked = [
        stage for stage in LOCKED_STAGES
        if stage_gate.get("rules", {}).get(stage, {}).get("status") != "LOCKED"
    ]
    if unlocked:
        raise ValueError(f"locked analysis stage is not locked: {sorted(unlocked)}")
    fold_audit = json.loads(fold_audit_path.read_text(encoding="utf-8"))
    if fold_audit.get("status") != "PASS" or fold_audit.get("endpoint_leakage_count") != 0:
        raise ValueError("component-disjoint fold gate has not passed")
    if sha256_file(fold_outer_path) != next(
        line.split()[0] for line in (fold_audit_path.parent / "CHECKSUMS.sha256").read_text().splitlines()
        if line.split()[-1] == fold_outer_path.name
    ):
        raise ValueError("outer fold assignment checksum mismatch")
    if sha256_file(fold_nested_path) != next(
        line.split()[0] for line in (fold_audit_path.parent / "CHECKSUMS.sha256").read_text().splitlines()
        if line.split()[-1] == fold_nested_path.name
    ):
        raise ValueError("nested fold assignment checksum mismatch")
    simulation = json.loads(simulation_decision_path.read_text(encoding="utf-8"))
    if simulation.get("status") != "PRIMARY_WEIGHTING_ROUTE_SELECTED":
        raise ValueError("outcome-free weighting strategy was not selected")
    if simulation.get("recommended_training_weight_strategy") != "sqrt_ipw":
        raise ValueError("unexpected selected training weighting strategy")
    header, row_count = read_header_count(development_path)
    required = {
        column
        for block in PREDICTIVE_BLOCKS
        for column in _contract_block_columns(contract, block)
    } | {"review_ready_label", "canonical_pair_id", "first_order_inclusion_probability"}
    missing = sorted(required - set(header))
    if missing:
        raise ValueError(f"development input lacks frozen fields: {missing}")
    if row_count != expected_rows:
        raise ValueError(f"development row count mismatch: {row_count} != {expected_rows}")

    fixture = canonical_fixture()
    training_fixture = fixture.iloc[:4].copy()
    p3_blocks = ["descriptor", "independent_quality"]
    p5_blocks = p3_blocks + ["pair_evidence"]
    p3 = fit_fold_preprocessor(training_fixture, contract, p3_blocks)
    p5 = fit_fold_preprocessor(training_fixture, contract, p5_blocks)
    p3_output = p3.transform(fixture)
    p5_output = p5.transform(fixture)
    if list(p5.output_columns[: len(p3.output_columns)]) != list(p3.output_columns):
        raise RuntimeError("canonical fixture violated the P3/P5 nested design invariant")
    if set(p5.output_columns) - set(p3.output_columns) != {
        column for column in p5.output_columns if column.startswith("local_match_")
    }:
        raise RuntimeError("P5 adds a non-pair-evidence transformed column")

    output_dir.mkdir(parents=True)
    frozen_contract = output_dir / "feature_preprocessing_contract_frozen.json"
    manifest_path = output_dir / "feature_schema_manifest.csv"
    fixture_path = output_dir / "canonical_transform_fixture.csv"
    p3_fit_path = output_dir / "P3_fixture_preprocessor.json"
    p5_fit_path = output_dir / "P5_fixture_preprocessor.json"
    p3_output_path = output_dir / "P3_fixture_transformed.csv"
    p5_output_path = output_dir / "P5_fixture_transformed.csv"
    audit_path = output_dir / "feature_preprocessing_freeze_audit.json"
    report_path = output_dir / "FEATURE_PREPROCESSING_REPORT.md"
    freezer_snapshot = output_dir / "freeze_builder_snapshot.py"
    transformer_snapshot = output_dir / "fold_preprocessor_snapshot.py"
    frozen_contract.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _feature_manifest(contract, model_registry).to_csv(manifest_path, index=False)
    fixture.to_csv(fixture_path, index=False)
    p3_fit_path.write_text(json.dumps(p3.to_payload(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    p5_fit_path.write_text(json.dumps(p5.to_payload(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    pd.concat([fixture[["fixture_row"]], p3_output.reset_index(drop=True)], axis=1).to_csv(
        p3_output_path, index=False
    )
    pd.concat([fixture[["fixture_row"]], p5_output.reset_index(drop=True)], axis=1).to_csv(
        p5_output_path, index=False
    )
    freezer_snapshot.write_text(Path(__file__).read_text(encoding="utf-8"), encoding="utf-8")
    transformer_source = ROOT / "scripts/pferi_v2_fold_preprocessor.py"
    transformer_snapshot.write_text(transformer_source.read_text(encoding="utf-8"), encoding="utf-8")

    audit = {
        "audit_version": "pferi_v2_feature_preprocessing_freeze_audit_v1",
        "status": "PASS",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "development_row_count": row_count,
        "development_column_count": len(header),
        "development_label_values_read": False,
        "development_model_fitted": False,
        "locked_stage_input_read": False,
        "outcome_dependent_preprocessing": False,
        "training_weight_strategy": "sqrt_ipw",
        "validation_weight_strategy": "hajek_ipw",
        "predictive_feature_count": len(_feature_manifest(contract, model_registry)),
        "diagnostic_predictor_count": 0,
        "P3_transformed_column_count": len(p3.output_columns),
        "P5_transformed_column_count": len(p5.output_columns),
        "P5_incremental_column_count": len(p5.output_columns) - len(p3.output_columns),
        "P3_P5_nested_invariant_pass": True,
        "canonical_fixture_P3_preprocessor_sha256": p3.sha256,
        "canonical_fixture_P5_preprocessor_sha256": p5.sha256,
        "development_input_sha256": sha256_file(development_path),
        "stage_gate_sha256": sha256_file(stage_gate_path),
        "fold_audit_sha256": sha256_file(fold_audit_path),
        "outer_fold_assignments_sha256": sha256_file(fold_outer_path),
        "nested_fold_assignments_sha256": sha256_file(fold_nested_path),
        "simulation_decision_sha256": sha256_file(simulation_decision_path),
        "model_registry_sha256": sha256_file(model_registry_path),
        "contract_source_sha256": sha256_file(contract_path),
        "contract_frozen_sha256": sha256_file(frozen_contract),
        "freezer_sha256": sha256_file(Path(__file__)),
        "transformer_sha256": sha256_file(transformer_source),
        "claim_boundary": contract["claim_boundary"],
    }
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(
        "\n".join(
            [
                "# PF-ERI v2 Feature and Preprocessing Freeze",
                "",
                "Status: **PASS — NO MODEL FIT**",
                "",
                "The predictive lineage is limited to descriptor, independent-quality, and pair-evidence blocks. "
                "Continuous medians, means, scales, and categorical levels are learned separately inside each "
                "training fold. Missing and unknown states have explicit columns. Failed measurements are never "
                "converted to zero evidence.",
                "",
                f"The canonical implementation fixture produced {len(p3.output_columns)} P3 columns and "
                f"{len(p5.output_columns)} P5 columns. P5 adds only {len(p5.output_columns)-len(p3.output_columns)} "
                "transformed pair-evidence columns. The exact transformer and fixture hashes are frozen.",
                "",
                "This task read the development header and row count but no label value. It fitted no predictive "
                "model and did not access calibration or confirmation inputs.",
            ]
        ) + "\n",
        encoding="utf-8",
    )
    checksum_paths = [
        frozen_contract, manifest_path, fixture_path, p3_fit_path, p5_fit_path,
        p3_output_path, p5_output_path, audit_path, report_path, freezer_snapshot,
        transformer_snapshot,
    ]
    (output_dir / "CHECKSUMS.sha256").write_text(
        "\n".join(f"{sha256_file(path)}  {path.name}" for path in checksum_paths) + "\n",
        encoding="utf-8",
    )
    return audit


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--contract", type=Path,
        default=ROOT / "schemas/pferi_v2/feature_preprocessing_contract_v1.json",
    )
    parser.add_argument(
        "--model-registry", type=Path,
        default=ROOT / "schemas/pferi_v2/model_route_candidate_registry_v1.json",
    )
    stage_root = ROOT / "archive/pferi_v2/task_runs/dual_sample_confirmation/2026-07-22_stage_isolated_analysis_inputs_v1"
    fold_root = ROOT / "archive/pferi_v2/task_runs/model_development/2026-07-22_component_disjoint_nested_folds_v1"
    parser.add_argument(
        "--development-input", type=Path,
        default=stage_root / "development_open/development_modeling_input.csv",
    )
    parser.add_argument("--stage-gate", type=Path, default=stage_root / "stage_gate_contract.json")
    parser.add_argument("--fold-audit", type=Path, default=fold_root / "fold_validation_audit.json")
    parser.add_argument("--outer-folds", type=Path, default=fold_root / "outer_fold_assignments.csv")
    parser.add_argument("--nested-folds", type=Path, default=fold_root / "nested_fold_assignments.csv")
    parser.add_argument(
        "--simulation-decision", type=Path,
        default=ROOT
        / "archive/pferi_v2/task_runs/model_development/2026-07-22_outcome_free_design_simulation/current"
        / "minimax_route_decision.json",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-rows", type=int, default=445)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    audit = run(
        args.contract.resolve(), args.model_registry.resolve(), args.development_input.resolve(),
        args.stage_gate.resolve(), args.fold_audit.resolve(), args.outer_folds.resolve(),
        args.nested_folds.resolve(), args.simulation_decision.resolve(), args.output_dir.resolve(),
        expected_rows=args.expected_rows,
    )
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
