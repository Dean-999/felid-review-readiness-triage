import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("task15f", ROOT / "scripts/task15f_modelscope_runner.py")
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def test_gauss_hermite_zero_sigma_equals_logistic():
    eta = np.array([[-2.0, 0.0, 2.0], [1.0, -1.0, 0.5]])
    sigma = np.zeros(2)
    actual = M.gauss_hermite_marginal_probability(eta, sigma, nodes=20)
    expected = 1.0 / (1.0 + np.exp(-eta))
    assert np.allclose(actual, expected, atol=1e-12)


def test_gauss_hermite_preserves_half_at_zero():
    eta = np.zeros((3, 4))
    sigma = np.array([0.1, 0.5, 1.0])
    actual = M.gauss_hermite_marginal_probability(eta, sigma, nodes=20)
    assert np.allclose(actual, 0.5, atol=1e-12)


def test_firth_flic_is_finite_on_separated_data():
    x = np.column_stack([np.ones(6), np.array([-3, -2, -1, 1, 2, 3], dtype=float)])
    y = np.array([0, 0, 0, 1, 1, 1], dtype=float)
    fit = M.fit_firth_flic(x, y, np.ones(6))
    probability = M.logistic(x @ fit["coef"])
    assert fit["success"]
    assert np.isfinite(fit["coef"]).all()
    assert np.all((probability > 0) & (probability < 1))
    assert abs(probability.mean() - y.mean()) < 1e-8


def test_result_validator_rejects_incomplete_predictions(tmp_path):
    pd.DataFrame({"canonical_pair_id": ["a"], "model_id": ["S3"], "posterior_mean_probability": [0.5]}).to_csv(tmp_path / "bayesian_oof_predictions.csv", index=False)
    audit = M.validate_results(tmp_path, write=False)
    assert audit["status"] == "FAIL"
    assert "bayesian_prediction_row_count_mismatch" in audit["failures"]


def test_result_validator_requires_firth_and_frozen_contract(tmp_path):
    audit = M.validate_results(tmp_path, write=False)
    assert "missing_required_output:firth_flic_diagnostic.csv" in audit["failures"]
    assert "missing_required_output:execution_contract_frozen.json" in audit["failures"]


def test_contract_runtime_and_model_roles_are_frozen():
    contract = json.loads((ROOT / "schemas/pferi_v2/task15f_bayesian_sensitivity_contract_v1.json").read_text())
    assert contract["mcmc"]["pymc"] == "6.0.1"
    assert contract["models"]["S5"]["selection_eligible"] is False
    assert "20-node Gauss-Hermite" in contract["models"]["S4"]["outer_test_prediction"]
