import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "task15g_reconciliation",
    ROOT / "scripts/reconcile_task15g_external_results.py",
)
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def test_external_and_local_runs_preserve_scientific_conclusion():
    analysis = M.analyze()

    assert analysis["status"] == "PASS"
    assert analysis["package_manifest_sha256_equal"] is True
    assert analysis["contract_sha256_equal"] is True
    assert analysis["prediction_keys_equal"] is True
    assert analysis["selected_configuration_ids_equal"] is True
    assert analysis["scientific_conclusion_invariant_across_platforms"] is True


def test_cross_platform_difference_is_small_and_model_specific():
    analysis = M.analyze()
    e1 = analysis["cross_platform_probability_difference"]["E1"]
    e2 = analysis["cross_platform_probability_difference"]["E2"]

    assert e1["maximum_absolute_probability_difference"] < 0.003
    assert e1["rows_above_1e_3"] == 24
    assert e2["maximum_absolute_probability_difference"] < 1e-12
    assert e2["rows_above_1e_12"] == 0


def test_effect_size_and_fold_concentration_are_recomputed():
    analysis = M.analyze()

    assert analysis["effect_sizes"]["E1_minus_E2_weighted_brier"] == pytest.approx(
        0.003712582993742608
    )
    assert analysis["pair_loss_direction_counts"]["E1_lower"] == 296
    assert analysis["component_loss_direction_counts"]["E1_lower"] == 73
    assert analysis["fold_contribution_fraction_of_net_difference"]["2"] == pytest.approx(
        2.2354434941692136
    )
    assert analysis["inferential_test_performed"] is False


def test_build_writes_immutable_analysis_package(tmp_path):
    output = tmp_path / "analysis"

    result = M.build(output)

    assert result["status"] == "PASS"
    assert (output / "external_vs_local_reconciliation.json").is_file()
    assert (output / "TASK15G_EXTERNAL_STATISTICAL_ANALYSIS.md").is_file()
    assert (output / "analysis_builder_snapshot.py").is_file()
    assert (output / "CHECKSUMS.sha256").is_file()
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        M.build(output)
