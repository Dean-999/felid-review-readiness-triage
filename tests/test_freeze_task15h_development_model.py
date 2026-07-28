import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "task15h_freeze",
    ROOT / "scripts/freeze_task15h_development_model.py",
)
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def test_real_evidence_validates_and_retains_binding_nonqualification():
    evidence, source_record = M.build_evidence()
    record = M.make_record(evidence, source_record)

    assert evidence["validation_failures"] == []
    assert evidence["checksum_failures"] == {}
    assert record["record_validation_status"] == "PASS"
    assert record["qualification_status"] == "NOT_QUALIFIED"
    assert record["development_model_frozen"] is False
    assert record["calibration_authorized"] is False
    assert record["candidate_dispositions"]["P5"]["qualification"] == "NOT_QUALIFIED"
    assert record["candidate_dispositions"]["P3"]["qualification"] == "NOT_QUALIFIED"


def test_regularization_and_calibration_rules_cannot_silently_pass():
    evidence, source_record = M.build_evidence()
    record = M.make_record(evidence, source_record)
    rules = record["qualification_before_performance"]

    stability = rules["stable_regularization_or_shape_selection"]
    calibration = rules["acceptable_calibration_intercept_and_slope"]
    assert stability["status"] == "FAIL"
    assert stability["evidence"]["maximum_to_minimum_ratio"] == 1000
    assert set(stability["evidence"]["P3_selected_lambda_by_outer_fold"].values()) == {
        0.1,
        100.0,
    }
    assert calibration["status"] == "UNRESOLVED"
    assert "No numeric observed-development" in calibration["evidence"]["interpretation"]


def test_schema_rejects_nonqualified_calibration_authorization():
    evidence, source_record = M.build_evidence()
    record = M.make_record(evidence, source_record)
    record["calibration_authorized"] = True

    failures = M.validate_schema(record, evidence["schema"])

    assert "nonqualified_record_authorized_calibration" in failures


def test_freeze_creates_complete_immutable_package(tmp_path):
    output = tmp_path / "task15h_freeze"

    audit = M.freeze(output=output)

    assert audit["status"] == "PASS"
    assert audit["record_validation_status"] == "PASS"
    assert audit["qualification_status"] == "NOT_QUALIFIED"
    assert audit["development_model_frozen"] is False
    assert audit["calibration_authorized"] is False
    assert (
        output / "development_model_freeze_record.json"
    ).is_file()
    assert (output / "qualification_audit.json").is_file()
    assert (
        output / "TASK15H_DEVELOPMENT_MODEL_FREEZE_REPORT.md"
    ).is_file()
    assert (output / "freeze_builder_snapshot.py").is_file()
    assert (output / "CHECKSUMS.sha256").is_file()

    record = json.loads(
        (output / "development_model_freeze_record.json").read_text(
            encoding="utf-8"
        )
    )
    assert record["status"] == (
        "VALIDATED_NO_DEVELOPMENT_MODEL_QUALIFIED_CALIBRATION_LOCKED"
    )
    assert "promoting P3 as a post-result fallback" in record["prohibited_actions"]

    assert M.verify_checksum_manifest(output) == []
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        M.freeze(output=output)
