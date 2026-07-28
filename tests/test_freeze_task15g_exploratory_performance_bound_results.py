import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "task15g_result_freeze",
    ROOT / "scripts/freeze_task15g_exploratory_performance_bound_results.py",
)
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def test_recomputed_metrics_use_design_weights():
    frame = pd.DataFrame(
        {
            "review_ready_label": [0, 1, 1],
            "probability": [0.2, 0.8, 0.6],
            "first_order_inclusion_probability": [0.1, 0.5, 1.0],
        }
    )

    metrics = M.recompute_metric(frame)
    weights = (1 / frame["first_order_inclusion_probability"].to_numpy(float))
    expected = np.average(
        (frame["review_ready_label"] - frame["probability"]) ** 2,
        weights=weights,
    )

    assert metrics["weighted_brier"] == pytest.approx(expected)
    assert np.isfinite(metrics["weighted_log_loss"])


def test_real_export_passes_independent_recalculation():
    results = M.EXECUTION / "results"

    analysis = M.independent_analysis(results, M.TASK15E_FREEZE, M.TASK15F_FREEZE)

    assert analysis["status"] == "PASS"
    assert analysis["failures"] == []
    assert analysis["prediction_rows"] == 890
    assert analysis["unique_pairs"] == 445
    assert analysis["unique_components"] == 116
    assert analysis["inner_selection_rows"] == 400
    assert analysis["selected_configuration_rows"] == 10
    assert analysis["E3_prediction_rows"] == 0
    assert analysis["E1_E2_fold_brier_wins"] == {
        "E1_lower_brier_folds": 3,
        "E2_lower_brier_folds": 2,
        "ties": 0,
    }


def test_real_export_proper_scores_match_expected_values():
    analysis = M.independent_analysis(
        M.EXECUTION / "results", M.TASK15E_FREEZE, M.TASK15F_FREEZE
    )

    assert analysis["recomputed_overall"]["E1"]["weighted_brier"] == pytest.approx(
        0.1327253786299507
    )
    assert analysis["recomputed_overall"]["E2"]["weighted_brier"] == pytest.approx(
        0.1289734657984624
    )
    assert analysis["cross_task_brier_comparison"]["E2"][
        "minus_S3_weighted_brier"
    ] > 0
    assert analysis["selected_configuration_counts"]["E2"] == {"E2_C01": 5}


def test_freeze_creates_complete_immutable_package(tmp_path):
    output = tmp_path / "freeze"

    audit = M.freeze(output=output)

    assert audit["status"] == "PASS"
    assert audit["prediction_rows"] == 890
    assert audit["internal_checksum_count"] == 52
    assert (output / "source_delivery" / M.ZIP.name).is_file()
    assert (output / "results" / "exploratory_oof_predictions.csv").is_file()
    assert (output / "independent_recalculation.json").is_file()
    assert (output / "task15g_disposition.json").is_file()
    assert (
        output / "TASK15G_EXPLORATORY_PERFORMANCE_BOUND_RESULT_FREEZE_REPORT.md"
    ).is_file()
    disposition = json.loads(
        (output / "task15g_disposition.json").read_text(encoding="utf-8")
    )
    assert disposition["final_model_selected"] is False
    assert disposition["next_authorized_task"].startswith("Task15H")

    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        M.freeze(output=output)


def test_external_sha_mismatch_is_rejected(tmp_path):
    declaration = tmp_path / "bad.sha256"
    declaration.write_text(f"{'0' * 64}  export.zip\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="external ZIP SHA256 mismatch"):
        M.freeze(sha_path=declaration, output=tmp_path / "freeze")


def test_malformed_sha_declaration_is_rejected(tmp_path):
    declaration = tmp_path / "bad.sha256"
    declaration.write_text("not-a-hash\n", encoding="utf-8")

    with pytest.raises(ValueError, match="declaration is invalid"):
        M.parse_declared_sha(declaration)
