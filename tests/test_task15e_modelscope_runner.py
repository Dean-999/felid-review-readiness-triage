import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("task15e", ROOT / "scripts/task15e_modelscope_runner.py")
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def test_contract_has_frozen_scope_and_models():
    contract = json.loads((ROOT / "schemas/pferi_v2/task15e_execution_contract_v1.json").read_text())
    assert contract["scope"]["expected_pair_count"] == 445
    assert list(contract["models"]) == ["P0", "P1", "P2", "P3", "P4", "P5", "S1", "S2"]
    assert contract["nested_validation"]["lambda_grid"][-1] == 100.0


def test_weight_rules_and_one_se_prefer_stronger_lambda():
    pi = np.array([0.25, 1.0])
    assert np.allclose(M.training_weights(pi), np.array([4 / 3, 2 / 3]))
    assert np.allclose(M.evaluation_weights(pi), np.array([1.6, 0.4]))
    summary = pd.DataFrame({"lambda": [0.1, 1.0, 10.0], "mean_brier": [0.20, 0.205, 0.209], "se_brier": [0.01, 0.01, 0.01]})
    assert M.select_lambda_one_se(summary) == 10.0


def test_penalized_logistic_produces_finite_probabilities():
    x = np.array([[-2.0], [-1.0], [1.0], [2.0]])
    y = np.array([0.0, 0.0, 1.0, 1.0])
    fit = M.fit_penalized_logistic(x, y, np.ones(4), 0.1)
    p = M.predict_probability(x, fit["coef"])
    assert fit["success"]
    assert np.all(np.isfinite(p)) and np.all((p > 0) & (p < 1))
    assert p[0] < p[-1]


def test_gam_basis_is_train_fitted_and_has_four_columns():
    train = pd.DataFrame({"x__z": [-2.0, -0.5, 0.5, 2.0], "x__missing": [0, 0, 0, 0]})
    spec = M.fit_gam_design(train, ["x"])
    out = M.transform_gam_design(train, spec)
    assert out.shape == (4, 5)
    assert list(out.columns) == ["x__spline_0", "x__spline_1", "x__spline_2", "x__spline_3", "x__missing"]
    assert np.isfinite(out.to_numpy()).all()


def test_validator_rejects_duplicate_or_incomplete_oof(tmp_path):
    rows = pd.DataFrame({"canonical_pair_id": ["a", "a"], "model_id": ["P0", "P0"], "probability": [0.5, 0.5]})
    path = tmp_path / "model_oof_predictions.csv"
    rows.to_csv(path, index=False)
    audit = M.validate_results(tmp_path, expected_pairs=1, expected_models=["P0"], write_audit=False)
    assert audit["status"] == "FAIL"
    assert "duplicate_pair_model_prediction" in audit["failures"]
