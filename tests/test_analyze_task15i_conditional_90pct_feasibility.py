import json
from pathlib import Path

import pytest

from scripts import analyze_task15i_conditional_90pct_feasibility as M


ROOT = Path(__file__).resolve().parents[1]


def test_independence_first_screen_design_exceeds_90_percent_conditionally():
    rows = M.build_scenarios(
        component_counts=(300, 400),
        pairs_per_component=4,
        true_increments=(0.01,),
        paired_loss_sd=0.12,
        intracomponent_correlation=0.10,
        practical_increment=0.005,
    )

    selected = M.minimum_design(
        rows,
        true_increment=0.01,
        probability_key="point_threshold_success_probability",
        required_probability=0.90,
    )

    assert selected["component_count"] == 400
    assert selected["analyzable_pair_count"] == 1600
    assert selected["point_threshold_success_probability"] > 0.90


def test_lower_bound_target_requires_materially_more_independent_components():
    rows = M.build_scenarios(
        component_counts=(400, 1000, 1600, 2000),
        pairs_per_component=4,
        true_increments=(0.01,),
        paired_loss_sd=0.12,
        intracomponent_correlation=0.10,
        practical_increment=0.005,
    )

    selected = M.minimum_design(
        rows,
        true_increment=0.01,
        probability_key="lower_confidence_bound_success_probability",
        required_probability=0.90,
    )

    assert selected["component_count"] == 2000
    assert selected["analyzable_pair_count"] == 8000
    assert selected["lower_confidence_bound_success_probability"] > 0.90


def test_freeze_is_conditional_and_does_not_authorize_outcome_access(tmp_path):
    output = tmp_path / "conditional_analysis"

    audit = M.freeze(output=output)

    assert audit["status"] == "PASS"
    assert audit["outcomes_accessed"] is False
    assert audit["conditional_not_actual_pass_probability"] is True
    assert audit["recommended_90pct_screen_design"]["component_count"] == 400
    assert audit["recommended_90pct_screen_design"]["analyzable_pair_count"] == 1600
    assert (output / "conditional_90pct_scenarios.csv").is_file()
    assert (output / "CONDITIONAL_90PCT_FEASIBILITY_REPORT.md").is_file()
    assert M.verify_checksum_manifest(output) == []

    record = json.loads(
        (output / "conditional_90pct_feasibility_record.json").read_text(
            encoding="utf-8"
        )
    )
    assert record["calibration_authorized"] is False
    assert record["actual_model_pass_probability_estimated"] is False
    assert record["adoption_requires_new_contract_version"] is True

    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        M.freeze(output=output)
