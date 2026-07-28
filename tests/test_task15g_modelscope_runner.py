import importlib.util
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


M = load_module("task15g_runner", ROOT / "scripts/task15g_modelscope_runner.py")
B = load_module("task15g_builder", ROOT / "scripts/build_task15g_modelscope_package.py")


def contract():
    return json.loads(
        (
            ROOT
            / "schemas/pferi_v2/task15g_exploratory_performance_bound_contract_v1.json"
        ).read_text(encoding="utf-8")
    )


def test_design_weights_are_normalized_and_distinct():
    inclusion = np.array([0.01, 0.04, 0.25, 1.0])
    training = M.training_weights(inclusion)
    evaluation = M.evaluation_weights(inclusion)

    assert training.mean() == pytest.approx(1.0)
    assert evaluation.mean() == pytest.approx(1.0)
    assert not np.allclose(training, evaluation)
    assert training[0] / training[-1] == pytest.approx(10.0)
    assert evaluation[0] / evaluation[-1] == pytest.approx(100.0)


def test_configuration_grids_match_frozen_budgets():
    frozen = contract()

    assert len(M.expand_configurations(frozen["models"]["E1"])) == 8
    assert len(M.expand_configurations(frozen["models"]["E2"])) == 12
    assert max(
        configuration["depth"]
        for configuration in M.expand_configurations(frozen["models"]["E2"])
    ) == 4


def test_selection_uses_mean_brier_then_frozen_simplicity_tie_break():
    rows = []
    configurations = [
        {"learning_rate": 0.05, "max_bins": 32, "max_leaves": 3},
        {"learning_rate": 0.025, "max_bins": 16, "max_leaves": 2},
    ]
    for index, configuration in enumerate(configurations):
        for inner_fold in range(4):
            rows.append(
                {
                    "configuration_id": f"E1_C{index:02d}",
                    "configuration_json": json.dumps(configuration),
                    "inner_fold": inner_fold,
                    "status": "PASS",
                    "brier": 0.12,
                }
            )

    selected_id, selected, score = M.select_configuration(
        "E1", pd.DataFrame(rows), tolerance=1e-12
    )

    assert selected_id == "E1_C01"
    assert selected["max_leaves"] == 2
    assert score == pytest.approx(0.12)


def test_incomplete_configuration_cannot_be_selected():
    rows = [
        {
            "configuration_id": "E2_C00",
            "configuration_json": json.dumps(
                {"depth": 2, "learning_rate": 0.03, "l2_leaf_reg": 10}
            ),
            "inner_fold": fold,
            "status": "PASS",
            "brier": 0.1,
        }
        for fold in range(3)
    ]

    with pytest.raises(RuntimeError, match="no_complete_configuration"):
        M.select_configuration("E2", pd.DataFrame(rows), tolerance=1e-12)


def test_fit_predict_passes_exact_training_weights(monkeypatch):
    captured = {}

    class FakeEstimator:
        def fit(self, x, y, sample_weight=None):
            captured["weights"] = np.asarray(sample_weight)
            return self

        def predict_proba(self, x):
            return np.column_stack([np.full(len(x), 0.4), np.full(len(x), 0.6)])

    monkeypatch.setattr(M, "make_estimator", lambda *args, **kwargs: FakeEstimator())
    train = pd.DataFrame(
        {
            "review_ready_label": [0, 1, 1],
            "first_order_inclusion_probability": [0.04, 0.25, 1.0],
        }
    )
    probability = M.fit_predict(
        "E1",
        {},
        {},
        1,
        pd.DataFrame({"x": [1.0, 2.0, 3.0]}),
        train,
        pd.DataFrame({"x": [4.0, 5.0]}),
    )

    assert np.allclose(
        captured["weights"],
        M.training_weights(train["first_order_inclusion_probability"].to_numpy()),
    )
    assert np.allclose(probability, 0.6)


def test_builder_inspects_tabpfn_fit_signature_from_wheel(tmp_path):
    wheel = tmp_path / "synthetic.whl"
    source = """
class TabPFNClassifier:
    def fit(self, X, y):
        return self
"""
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("tabpfn/classifier.py", source)

    audit = B.inspect_tabpfn_fit_signature(wheel)

    assert audit["fit_signature"] == "fit(self, X, y)"
    assert audit["supports_sample_weight"] is False
    assert audit["disposition"] == (
        "PREDECLARED_INELIGIBLE_UNDER_COMMON_WEIGHTING_CONTRACT"
    )


def test_manifest_rejects_unexpected_file(tmp_path):
    package = tmp_path / "package"
    package.mkdir()
    (package / "declared.txt").write_text("declared\n", encoding="utf-8")
    (package / "PACKAGE_MANIFEST.sha256").write_text(
        f"{M.sha256(package / 'declared.txt')}  declared.txt\n", encoding="utf-8"
    )
    assert M.verify_manifest(package) == M.sha256(package / "PACKAGE_MANIFEST.sha256")

    (package / "unexpected.pyc").write_bytes(b"bytecode")
    with pytest.raises(RuntimeError, match="package_inventory_mismatch"):
        M.verify_manifest(package)


def test_validator_rejects_incomplete_results(tmp_path):
    pd.DataFrame(
        {
            "canonical_pair_id": ["pair"],
            "model_id": ["E1"],
            "outer_fold": [0],
            "probability": [0.5],
        }
    ).to_csv(tmp_path / "exploratory_oof_predictions.csv", index=False)

    audit = M.validate_results(tmp_path, write=False)

    assert audit["status"] == "FAIL"
    assert "prediction_row_count_mismatch" in audit["failures"]
    assert "missing_required_output:execution_contract_frozen.json" in audit["failures"]


def test_validator_accepts_complete_hashed_fixture(tmp_path):
    required_placeholders = [
        "exploratory_outer_fold_metrics.csv",
        "exploratory_overall_metrics.csv",
        "component_paired_brier_regret.csv",
        "configuration_stability.csv",
    ]
    for name in required_placeholders:
        (tmp_path / name).write_text("placeholder\n", encoding="utf-8")
    (tmp_path / "TASK15G_EXPLORATORY_PERFORMANCE_BOUND_REPORT.md").write_text(
        "# Fixture\n", encoding="utf-8"
    )
    frozen = contract()
    M.write_json(tmp_path / "execution_contract_frozen.json", frozen)
    M.write_json(
        tmp_path / "model_availability_audit.json",
        {"status": "PASS", "E3_prediction_rows": 0},
    )

    predictions = []
    for index in range(445):
        for model_id in M.MODELS:
            predictions.append(
                {
                    "canonical_pair_id": f"pair_{index:03d}",
                    "model_id": model_id,
                    "outer_fold": index % 5,
                    "probability": 0.7,
                }
            )
    pd.DataFrame(predictions).to_csv(
        tmp_path / "exploratory_oof_predictions.csv", index=False
    )
    inner = []
    for outer_fold in range(5):
        for model_id, count in (("E1", 8), ("E2", 12)):
            for configuration in range(count):
                for inner_fold in range(4):
                    inner.append(
                        {
                            "outer_fold": outer_fold,
                            "model_id": model_id,
                            "configuration_id": f"{model_id}_C{configuration:02d}",
                            "inner_fold": inner_fold,
                        }
                    )
    pd.DataFrame(inner).to_csv(tmp_path / "inner_selection_results.csv", index=False)
    selected = [
        {
            "model_id": model_id,
            "outer_fold": outer_fold,
            "configuration_id": f"{model_id}_C00",
        }
        for outer_fold in range(5)
        for model_id in M.MODELS
    ]
    pd.DataFrame(selected).to_csv(tmp_path / "selected_configurations.csv", index=False)
    M.write_json(
        tmp_path / "execution_audit.json",
        {
            "contract_sha256": M.sha256(tmp_path / "execution_contract_frozen.json"),
            "locked_stage_outcomes_accessed": False,
            "final_model_selected": False,
        },
    )
    checkpoint_dir = tmp_path / "fold_checkpoints"
    checkpoint_dir.mkdir()
    for outer_fold in range(5):
        for model_id in M.MODELS:
            prefix = checkpoint_dir / f"{model_id}_fold{outer_fold}"
            prediction_path = prefix.with_name(prefix.name + "_predictions.csv")
            inner_path = prefix.with_name(prefix.name + "_inner_selection.csv")
            selected_path = prefix.with_name(prefix.name + "_selected_configuration.json")
            prediction_path.write_text("x\n", encoding="utf-8")
            inner_path.write_text("x\n", encoding="utf-8")
            selected_path.write_text("{}\n", encoding="utf-8")
            M.write_json(
                prefix.with_suffix(".json"),
                {
                    "predictions_sha256": M.sha256(prediction_path),
                    "inner_sha256": M.sha256(inner_path),
                    "selected_sha256": M.sha256(selected_path),
                },
            )

    audit = M.validate_results(tmp_path, write=False)

    assert audit["status"] == "PASS"
    assert audit["failures"] == []
