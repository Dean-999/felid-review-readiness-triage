#!/usr/bin/env python3
"""Freeze the Task 15G exploratory performance-bound execution contract."""
from __future__ import annotations

import hashlib
import itertools
import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "schemas/pferi_v2/task15g_exploratory_performance_bound_contract_v1.json"
DATA = ROOT / "archive/pferi_v2/task_runs/dual_sample_confirmation/2026-07-22_stage_isolated_analysis_inputs_v1/development_open/development_modeling_input.csv"
FOLDS = ROOT / "archive/pferi_v2/task_runs/model_development/2026-07-22_component_disjoint_nested_folds_v1/outer_fold_assignments.csv"
NESTED_FOLDS = ROOT / "archive/pferi_v2/task_runs/model_development/2026-07-22_component_disjoint_nested_folds_v1/nested_fold_assignments.csv"
PREPROCESSING = ROOT / "schemas/pferi_v2/feature_preprocessing_contract_v1.json"
PREPROCESSOR = ROOT / "scripts/pferi_v2_fold_preprocessor.py"
REGISTRY = ROOT / "schemas/pferi_v2/model_route_candidate_registry_v1.json"
TASK15F_DISPOSITION = ROOT / "archive/pferi_v2/task_runs/model_development/2026-07-23_task15f_bayesian_sensitivity_result_freeze_v1/task15f_disposition.json"
OUTPUT = ROOT / "archive/pferi_v2/task_runs/model_development/2026-07-23_task15g_exploratory_performance_bound_contract_freeze_v1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def grid_size(grid: dict[str, list[Any]]) -> int:
    return len(list(itertools.product(*(grid[key] for key in sorted(grid)))))


def validate_contract(contract: dict[str, Any]) -> None:
    if contract.get("contract_version") != "pferi_v2_task15g_exploratory_performance_bound_contract_v1":
        raise ValueError("contract version mismatch")
    scope = contract.get("scope", {})
    if scope.get("expected_pair_count") != 445 or scope.get("expected_component_count") != 116:
        raise ValueError("scope count mismatch")
    if scope.get("locked_stages") != ["calibration", "deployment_confirmation", "mechanism_confirmation"]:
        raise ValueError("locked-stage scope mismatch")

    models = contract.get("models", {})
    if set(models) != {"E1", "E2", "E3"}:
        raise ValueError("exploratory model registry mismatch")
    if any(model.get("confirmation_eligible") is not False for model in models.values()):
        raise ValueError("exploratory model marked confirmation eligible")

    e1 = models["E1"]
    if e1.get("automatic_interaction_search") is not False or e1.get("prespecified_interactions") != []:
        raise ValueError("E1 interaction policy mismatch")
    if e1["fixed_parameters"].get("interactions") != 0:
        raise ValueError("E1 automatic interactions are not disabled")
    if grid_size(e1["configuration_grid"]) != e1.get("configuration_count") or e1["configuration_count"] != 8:
        raise ValueError("E1 configuration count mismatch")

    e2 = models["E2"]
    if grid_size(e2["configuration_grid"]) != e2.get("configuration_count") or e2["configuration_count"] > 12:
        raise ValueError("E2 configuration count exceeds registry budget")
    if max(e2["configuration_grid"]["depth"]) > 4 or e2.get("maximum_depth") != 4:
        raise ValueError("E2 depth exceeds registry budget")

    e3 = models["E3"]
    checkpoint = e3.get("checkpoint", {})
    if e3.get("fine_tuning") is not False:
        raise ValueError("E3 fine-tuning must be disabled")
    if len(checkpoint.get("sha256", "")) != 64 or checkpoint.get("size_bytes") != 29009539:
        raise ValueError("E3 checkpoint identity mismatch")
    api = e3.get("sample_weight_api_precheck", {})
    if api.get("supports_sample_weight") is not False:
        raise ValueError("E3 weight-support precheck mismatch")
    if api.get("disposition") != "PREDECLARED_INELIGIBLE_UNDER_COMMON_WEIGHTING_CONTRACT":
        raise ValueError("E3 disposition mismatch")
    if e3.get("expected_prediction_rows") != 0:
        raise ValueError("E3 must not emit predictions under the frozen API")

    common = contract.get("common_design", {})
    if "sqrt inverse" not in common.get("training_weight", ""):
        raise ValueError("training-weight policy mismatch")
    if common.get("class_rebalancing") != "none" or common.get("class_weight") != "none":
        raise ValueError("class-rebalancing policy mismatch")
    if contract.get("interpretation_rules", {}).get("next_gate") != (
        "Task15H qualification-before-performance freeze and validated development_model_freeze_record.json"
    ):
        raise ValueError("next gate mismatch")


def validate_scientific_inputs(contract: dict[str, Any], source_map: dict[str, Path]) -> dict[str, Any]:
    failures = [
        name
        for name, path in source_map.items()
        if not path.is_file() or sha256(path) != contract["authoritative_inputs"][name]
    ]
    if failures:
        raise RuntimeError(f"authoritative input hash mismatch: {failures}")

    data = pd.read_csv(source_map["development_modeling_input.csv"])
    folds = pd.read_csv(source_map["outer_fold_assignments.csv"])
    nested = pd.read_csv(source_map["nested_fold_assignments.csv"])
    required_data = {"canonical_pair_id", "formal_sampling_stage", "review_ready_label"}
    if not required_data.issubset(data.columns):
        raise RuntimeError("development input columns are incomplete")
    if len(data) != 445 or data["canonical_pair_id"].nunique() != 445:
        raise RuntimeError("development row mismatch")
    if set(data["formal_sampling_stage"].astype(str)) != {"development"}:
        raise RuntimeError("locked stage detected")

    frame = data[["canonical_pair_id"]].merge(
        folds[["canonical_pair_id", "component_id", "outer_fold"]],
        on="canonical_pair_id",
        validate="one_to_one",
    )
    if len(frame) != 445 or frame["component_id"].nunique() != 116:
        raise RuntimeError("fold coverage mismatch")
    if set(frame["outer_fold"].astype(int)) != set(range(5)):
        raise RuntimeError("outer fold mismatch")
    if frame.groupby("component_id")["outer_fold"].nunique().max() != 1:
        raise RuntimeError("outer component leakage")

    nested_required = {"canonical_pair_id", "outer_fold_context", "inner_fold"}
    if not nested_required.issubset(nested.columns):
        raise RuntimeError("nested fold columns are incomplete")
    for outer_fold in range(5):
        rows = nested.loc[nested["outer_fold_context"].astype(int) == outer_fold]
        expected = frame.loc[frame["outer_fold"].astype(int) != outer_fold, "canonical_pair_id"]
        if set(rows["canonical_pair_id"]) != set(expected):
            raise RuntimeError(f"nested fold coverage mismatch for outer fold {outer_fold}")
        if set(rows["inner_fold"].astype(int)) != set(range(4)):
            raise RuntimeError(f"inner fold mismatch for outer fold {outer_fold}")

    disposition = json.loads(source_map["task15f_disposition.json"].read_text(encoding="utf-8"))
    if disposition.get("status") != "FROZEN_COMPLETE_WITHOUT_FINAL_MODEL_SELECTION":
        raise RuntimeError("Task15F disposition does not authorize Task15G")
    if disposition.get("next_authorized_task") != "Task15G exploratory performance-bound benchmark":
        raise RuntimeError("Task15F next-task authorization mismatch")
    if disposition.get("final_model_selected") is not False:
        raise RuntimeError("Task15F unexpectedly selected a final model")

    return {
        "development_rows": len(data),
        "component_count": int(frame["component_id"].nunique()),
        "outer_fold_count": int(frame["outer_fold"].nunique()),
        "nested_assignment_rows": len(nested),
        "task15f_status": disposition["status"],
        "authoritative_input_hash_failures": failures,
    }


def report_text(contract: dict[str, Any], audit: dict[str, Any]) -> str:
    e3 = contract["models"]["E3"]
    return f"""# PF-ERI v2 Task 15G Exploratory Performance-Bound Contract Freeze

Status: `PASS`

This freeze defines a development-only benchmark that asks how much proper-score performance can be reached by tightly bounded nonlinear tabular models when the information set, endpoint-component-disjoint validation, fold-training preprocessing, and design weights are held constant. It does not select a final development model. E1, E2, and E3 remain `confirmation_eligible=false`, and calibration, deployment-confirmation, and mechanism-confirmation outcomes remain locked.

E1 is an Explainable Boosting Machine implemented with `interpret==0.7.8`. Automatic interaction search is disabled and no interaction is introduced. Eight configurations cross two learning rates, two bin limits, and two leaf limits. E2 is a deterministic shallow CatBoost model implemented with `catboost==1.2.10`. Its twelve configurations cross depths 2 through 4, two learning rates, and two L2 leaf penalties. Both models are selected separately inside each outer training set by the mean design-weighted Brier score across the four frozen inner folds, then refitted with square-root inverse-probability weights on the complete outer training set.

E3 is pinned to `tabpfn==8.0.7` and the public v2 classifier checkpoint `{e3['checkpoint']['filename']}` at repository revision `{e3['checkpoint']['repository_revision']}`. The checkpoint is fixed at {e3['checkpoint']['size_bytes']} bytes with SHA256 `{e3['checkpoint']['sha256']}`. The frozen estimator exposes `fit(self, X, y)` and has no native `sample_weight` argument. E3 is therefore predeclared ineligible under the common fitting-weight contract and must emit no prediction. Row duplication, weighted resampling, integer replication, fine-tuning, or package replacement are prohibited because they would create an unregistered analysis rather than a comparable benchmark.

The freeze verified {audit['development_rows']} unique development pairs, {audit['component_count']} endpoint-image components, five outer folds, and {audit['nested_assignment_rows']} frozen nested-fold assignments. It verified all authoritative hashes and the completed Task 15F disposition. No model was fitted, no Task 15G performance was computed, and no locked-stage outcome was accessed.

The next authorized action is to build an exact Task 15G execution package from this contract. After validated Task 15G results are frozen, Task 15H must apply qualification before performance and create a validated `development_model_freeze_record.json`; only that record can authorize opening calibration.
"""


def build(output: Path = OUTPUT) -> dict[str, Any]:
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    validate_contract(contract)
    source_map = {
        "development_modeling_input.csv": DATA,
        "outer_fold_assignments.csv": FOLDS,
        "nested_fold_assignments.csv": NESTED_FOLDS,
        "feature_preprocessing_contract.json": PREPROCESSING,
        "fold_preprocessor.py": PREPROCESSOR,
        "candidate_model_registry.json": REGISTRY,
        "task15f_disposition.json": TASK15F_DISPOSITION,
    }
    scientific = validate_scientific_inputs(contract, source_map)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".task15g_contract_") as temporary:
        stage = Path(temporary) / output.name
        stage.mkdir()
        shutil.copy2(CONTRACT, stage / "task15g_exploratory_performance_bound_contract_frozen.json")
        shutil.copy2(Path(__file__), stage / "contract_freeze_builder_snapshot.py")
        audit = {
            "status": "PASS",
            "frozen_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "contract_sha256": sha256(CONTRACT),
            **scientific,
            "E1_configuration_count": contract["models"]["E1"]["configuration_count"],
            "E2_configuration_count": contract["models"]["E2"]["configuration_count"],
            "E3_disposition": contract["models"]["E3"]["sample_weight_api_precheck"]["disposition"],
            "locked_stage_outcomes_accessed": False,
            "model_fitting_performed": False,
            "final_model_selected": False,
            "next_authorized_action": "build exact Task15G execution package",
        }
        write_json(stage / "contract_freeze_audit.json", audit)
        (stage / "TASK15G_CONTRACT_FREEZE_REPORT.md").write_text(
            report_text(contract, audit), encoding="utf-8"
        )
        targets = sorted(path for path in stage.iterdir() if path.is_file() and path.name != "CHECKSUMS.sha256")
        (stage / "CHECKSUMS.sha256").write_text(
            "".join(f"{sha256(path)}  {path.name}\n" for path in targets),
            encoding="utf-8",
        )
        shutil.move(str(stage), output)
    return audit


def main() -> int:
    try:
        result = build()
    except Exception as error:
        print(json.dumps({"status": "FAIL", "error_type": type(error).__name__, "error": str(error)}, indent=2))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
