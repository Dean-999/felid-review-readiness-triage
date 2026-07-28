import importlib.util
import json
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("task15f_freeze", ROOT / "scripts/freeze_task15f_bayesian_sensitivity_contract.py")
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def test_contract_freezes_models_marginalization_and_runtime():
    contract = json.loads((ROOT / "schemas/pferi_v2/task15f_bayesian_sensitivity_contract_v1.json").read_text())
    M.validate_contract(contract)
    assert set(contract["models"]) == {"S3", "S4", "S5"}
    assert "20-node Gauss-Hermite" in contract["models"]["S4"]["outer_test_prediction"]
    assert contract["mcmc"]["pymc"] == "6.0.1"
    assert contract["models"]["S5"]["selection_eligible"] is False


def test_complete_separation_linear_program_detects_separable_case():
    x = np.column_stack([np.ones(4), np.array([-2.0, -1.0, 1.0, 2.0])])
    y = np.array([0.0, 0.0, 1.0, 1.0])
    assert M.complete_separation_feasible(x, y)


def test_complete_separation_linear_program_rejects_overlap():
    x = np.column_stack([np.ones(4), np.array([-2.0, -1.0, 1.0, 2.0])])
    y = np.array([0.0, 1.0, 0.0, 1.0])
    assert not M.complete_separation_feasible(x, y)


def test_logistic_objective_is_finite_at_origin():
    x = np.column_stack([np.ones(4), np.arange(4.0)])
    value, gradient = M.logistic_objective(np.zeros(2), x, np.array([0.0, 0.0, 1.0, 1.0]))
    assert np.isfinite(value)
    assert np.isfinite(gradient).all()
