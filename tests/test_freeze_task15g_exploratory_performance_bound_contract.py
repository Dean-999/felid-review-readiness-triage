import copy
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "task15g_contract_freeze",
    ROOT / "scripts/freeze_task15g_exploratory_performance_bound_contract.py",
)
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def load_contract():
    return json.loads(
        (ROOT / "schemas/pferi_v2/task15g_exploratory_performance_bound_contract_v1.json").read_text(
            encoding="utf-8"
        )
    )


def test_contract_freezes_registered_roles_and_common_design():
    contract = load_contract()
    M.validate_contract(contract)

    assert set(contract["models"]) == {"E1", "E2", "E3"}
    assert all(model["confirmation_eligible"] is False for model in contract["models"].values())
    assert "sqrt inverse" in contract["common_design"]["training_weight"]
    assert contract["common_design"]["class_rebalancing"] == "none"
    assert contract["scope"]["locked_stages"] == [
        "calibration",
        "deployment_confirmation",
        "mechanism_confirmation",
    ]


def test_complexity_budgets_are_exact_and_within_registry_limits():
    contract = load_contract()
    e1 = contract["models"]["E1"]
    e2 = contract["models"]["E2"]

    assert M.grid_size(e1["configuration_grid"]) == 8
    assert e1["automatic_interaction_search"] is False
    assert e1["prespecified_interactions"] == []
    assert M.grid_size(e2["configuration_grid"]) == 12
    assert max(e2["configuration_grid"]["depth"]) == 4


def test_tabpfn_identity_and_weight_incompatibility_are_frozen():
    e3 = load_contract()["models"]["E3"]

    assert e3["package"] == "tabpfn==8.0.7"
    assert e3["checkpoint"]["sha256"] == "cf8c519c01eaf1613ee91239006d57b1c806ff5f23ac1aeb1315ba1015210e49"
    assert e3["sample_weight_api_precheck"]["supports_sample_weight"] is False
    assert e3["expected_prediction_rows"] == 0
    assert "row duplication" in e3["prohibited_workarounds"]


def test_contract_rejects_complexity_and_eligibility_drift():
    contract = load_contract()
    eligible = copy.deepcopy(contract)
    eligible["models"]["E1"]["confirmation_eligible"] = True
    with pytest.raises(ValueError, match="confirmation eligible"):
        M.validate_contract(eligible)

    too_deep = copy.deepcopy(contract)
    too_deep["models"]["E2"]["configuration_grid"]["depth"] = [2, 3, 5]
    with pytest.raises(ValueError, match="depth exceeds"):
        M.validate_contract(too_deep)


def test_real_scientific_inputs_match_contract_and_task15f_authorization():
    contract = load_contract()
    source_map = {
        "development_modeling_input.csv": M.DATA,
        "outer_fold_assignments.csv": M.FOLDS,
        "nested_fold_assignments.csv": M.NESTED_FOLDS,
        "feature_preprocessing_contract.json": M.PREPROCESSING,
        "fold_preprocessor.py": M.PREPROCESSOR,
        "candidate_model_registry.json": M.REGISTRY,
        "task15f_disposition.json": M.TASK15F_DISPOSITION,
    }

    audit = M.validate_scientific_inputs(contract, source_map)

    assert audit["development_rows"] == 445
    assert audit["component_count"] == 116
    assert audit["outer_fold_count"] == 5
    assert audit["nested_assignment_rows"] == 1780
    assert audit["authoritative_input_hash_failures"] == []


def test_build_creates_complete_immutable_freeze(tmp_path):
    output = tmp_path / "freeze"

    audit = M.build(output)

    assert audit["status"] == "PASS"
    assert audit["model_fitting_performed"] is False
    assert (output / "task15g_exploratory_performance_bound_contract_frozen.json").is_file()
    assert (output / "contract_freeze_audit.json").is_file()
    assert (output / "TASK15G_CONTRACT_FREEZE_REPORT.md").is_file()
    assert (output / "contract_freeze_builder_snapshot.py").is_file()
    assert (output / "CHECKSUMS.sha256").is_file()

    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        M.build(output)
