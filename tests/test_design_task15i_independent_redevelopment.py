import json
from pathlib import Path

import pytest

from scripts import design_task15i_independent_redevelopment as M


ROOT = Path(__file__).resolve().parents[1]


def test_component_operating_characteristics_count_components_not_raw_pairs():
    rows = M.simulate_component_operating_characteristics(
        component_counts=(200, 300),
        pairs_per_component=4,
        true_increments=(0.01,),
        paired_loss_sd=0.12,
        intracomponent_correlation=0.10,
        practical_increment=0.005,
        replicates=4000,
        seed=2026072501,
    )
    by_components = {row["component_count"]: row for row in rows}

    assert by_components[300]["analyzable_pair_count"] == 1200
    assert by_components[300]["effective_pair_count"] < 1200
    assert (
        by_components[300]["point_threshold_success_probability"]
        > by_components[200]["point_threshold_success_probability"]
    )


def test_contract_requires_independent_new_development_data_and_no_fallback():
    contract = json.loads(M.CONTRACT.read_text(encoding="utf-8"))

    assert contract["information_boundary"]["existing_locked_stages_may_be_reassigned"] is False
    assert contract["information_boundary"]["locked_outcomes_may_be_read"] is False
    assert contract["independent_data_requirements"]["image_overlap_with_existing_roles"] == 0
    assert contract["qualification_policy"]["automatic_P3_fallback_if_P5_fails"] is False


def test_freeze_builds_immutable_outcome_free_design_package(tmp_path):
    output = tmp_path / "task15i_design"

    audit = M.freeze(
        output=output,
        lambda_replicates_override=1,
        operating_characteristic_replicates_override=500,
    )

    assert audit["status"] == "PASS"
    assert audit["real_outcomes_used"] is False
    assert audit["locked_stage_outcomes_accessed"] is False
    assert audit["recommended_design"]["component_count"] >= 300
    assert audit["recommended_design"]["analyzable_pair_count"] >= 1200
    assert (output / "independent_redevelopment_design_record.json").is_file()
    assert (output / "fixed_lambda_selection.json").is_file()
    assert (output / "component_operating_characteristics.csv").is_file()
    assert (output / "CHECKSUMS.sha256").is_file()
    assert M.verify_checksum_manifest(output) == []

    record = json.loads(
        (output / "independent_redevelopment_design_record.json").read_text(
            encoding="utf-8"
        )
    )
    assert record["calibration_authorized"] is False
    assert record["new_development_outcomes_opened"] is False
    assert record["fixed_lambda"] in record["lambda_selection"]["candidate_grid"]

    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        M.freeze(output=output)
