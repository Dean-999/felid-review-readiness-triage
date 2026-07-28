#!/usr/bin/env python3
"""Build stage-isolated PF-ERI v2 analysis inputs.

Only development outcomes are exposed. Calibration, deployment-confirmation,
and mechanism-confirmation receive outcome-free feature tables plus immutable
outcome commitments. Later tasks must present the required freeze records
before a locked outcome stage can be joined to predictions.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


OUTCOME_FREE_FEATURE_COLUMNS = [
    "derivation_contract_version", "canonical_pair_id", "pair_execution_id",
    "analytical_role", "endpoint_a_image_id", "endpoint_b_image_id",
    "descriptor_support_category", "best_rank_band", "retrieval_stratum_id",
    "megadescriptor_similarity", "dinov2_similarity",
    "megadescriptor_within_role_percentile", "dinov2_within_role_percentile",
    "dual_descriptor_percentile_disagreement",
    "dual_descriptor_disagreement_within_role_percentile",
    "endpoint_native_pixel_quality_percentile_min",
    "endpoint_sharpness_quality_percentile_min",
    "endpoint_exposure_quality_percentile_min", "endpoint_quality_measurement_failure",
    "endpoint_frozen_quality_stress", "local_match_coverage_fraction",
    "local_match_within_role_percentile", "local_match_measurement_failure",
    "development_evidence_state", "development_sampling_cell_id",
]
OUTCOME_REQUIRED_COLUMNS = [
    "canonical_pair_id", "formal_sampling_stage", "endpoint_a_image_id",
    "endpoint_b_image_id", "sampling_cell_id", "first_order_inclusion_probability",
    "final_label_source", "final_three_category_label", "review_ready_label",
    "not_ready_or_uncertain_label",
]
STAGES = (
    "development", "calibration", "deployment_confirmation", "mechanism_confirmation"
)
LOCKED_STAGES = STAGES[1:]
PRODUCTION_STAGE_COUNTS = {
    "development": 445,
    "calibration": 445,
    "deployment_confirmation": 889,
    "mechanism_confirmation": 445,
}
LOCKED_FEATURE_OUTPUT_COLUMNS = ["formal_sampling_stage"] + OUTCOME_FREE_FEATURE_COLUMNS
DEVELOPMENT_OUTPUT_COLUMNS = LOCKED_FEATURE_OUTPUT_COLUMNS + [
    "sampling_cell_id", "first_order_inclusion_probability", "final_label_source",
    "final_three_category_label", "review_ready_label", "not_ready_or_uncertain_label",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path, required_columns: Iterable[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        missing = sorted(set(required_columns) - set(fields))
        if missing:
            raise ValueError(f"missing columns in {path}: {missing}")
        return list(reader)


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_checksum_manifest(directory: Path) -> int:
    manifest = directory / "CHECKSUMS.sha256"
    if not manifest.exists():
        raise ValueError("source outcome checksum manifest is missing")
    checked = 0
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, relative = line.split("  ", 1)
        path = directory / relative
        if not path.is_file() or sha256_file(path) != digest:
            raise ValueError(f"source outcome checksum mismatch: {relative}")
        checked += 1
    if checked == 0:
        raise ValueError("source outcome checksum manifest is empty")
    return checked


def expected_role(stage: str) -> str:
    return "confirmation" if stage in {"deployment_confirmation", "mechanism_confirmation"} else stage


def commitment_digest(rows: list[dict[str, str]]) -> str:
    canonical = "\n".join(
        "|".join(
            row[key]
            for key in (
                "canonical_pair_id", "final_three_category_label", "review_ready_label",
                "not_ready_or_uncertain_label", "final_label_source",
            )
        )
        for row in sorted(rows, key=lambda item: item["canonical_pair_id"])
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build(
    *,
    outcome_dir: Path,
    feature_frame: Path,
    output_dir: Path,
    expected_stage_counts: dict[str, int] | None = None,
) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite: {output_dir}")
    expected_stage_counts = expected_stage_counts or PRODUCTION_STAGE_COUNTS
    if set(expected_stage_counts) != set(STAGES):
        raise ValueError("expected stage-count contract is incomplete")

    outcome_path = outcome_dir / "final_adjudicated_outcomes.csv"
    audit_path = outcome_dir / "final_outcome_audit.json"
    disposition_path = outcome_dir / "adjudication_acceptance_disposition.json"
    source_audit = load_json(audit_path)
    source_disposition = load_json(disposition_path)
    if source_disposition.get("model_analysis_authorized") is not True:
        raise ValueError("source disposition does not authorize model analysis")
    if source_audit.get("status") != "PASS" or source_audit.get("model_analysis_authorized") is not True:
        raise ValueError("source outcome audit does not authorize model analysis")
    checked_source_files = verify_checksum_manifest(outcome_dir)

    outcomes = read_csv(outcome_path, OUTCOME_REQUIRED_COLUMNS)
    outcome_by_pair = {row["canonical_pair_id"]: row for row in outcomes}
    if len(outcome_by_pair) != len(outcomes):
        raise ValueError("duplicate canonical pair in final outcomes")
    observed_counts = Counter(row["formal_sampling_stage"] for row in outcomes)
    if dict(observed_counts) != expected_stage_counts:
        raise ValueError(
            f"formal outcome stage counts do not match contract: {dict(observed_counts)}"
        )
    if int(source_audit.get("formal_pair_count", -1)) != len(outcomes):
        raise ValueError("source outcome audit row count mismatch")

    features = read_csv(feature_frame, OUTCOME_FREE_FEATURE_COLUMNS)
    feature_by_pair = {row["canonical_pair_id"]: row for row in features}
    if len(feature_by_pair) != len(features):
        raise ValueError("duplicate canonical pair in outcome-free feature frame")
    if not set(outcome_by_pair).issubset(feature_by_pair):
        raise ValueError("feature frame does not exactly cover formal outcomes")
    selected_features = {pair_id: feature_by_pair[pair_id] for pair_id in outcome_by_pair}
    if len(selected_features) != len(outcome_by_pair):
        raise ValueError("feature frame does not exactly cover formal outcomes")

    development_rows: list[dict[str, str]] = []
    locked_feature_rows: dict[str, list[dict[str, str]]] = {stage: [] for stage in LOCKED_STAGES}
    stage_outcomes: dict[str, list[dict[str, str]]] = {stage: [] for stage in STAGES}
    for pair_id in sorted(outcome_by_pair):
        outcome = outcome_by_pair[pair_id]
        feature = selected_features[pair_id]
        stage = outcome["formal_sampling_stage"]
        if feature["analytical_role"] != expected_role(stage):
            raise ValueError(f"feature role mismatch: {pair_id}")
        if {feature["endpoint_a_image_id"], feature["endpoint_b_image_id"]} != {
            outcome["endpoint_a_image_id"], outcome["endpoint_b_image_id"]
        }:
            raise ValueError(f"feature endpoint mismatch: {pair_id}")
        stage_outcomes[stage].append(outcome)
        feature_row = {"formal_sampling_stage": stage, **{key: feature[key] for key in OUTCOME_FREE_FEATURE_COLUMNS}}
        if stage == "development":
            development_rows.append(
                {
                    **feature_row,
                    "sampling_cell_id": outcome["sampling_cell_id"],
                    "first_order_inclusion_probability": outcome["first_order_inclusion_probability"],
                    "final_label_source": outcome["final_label_source"],
                    "final_three_category_label": outcome["final_three_category_label"],
                    "review_ready_label": outcome["review_ready_label"],
                    "not_ready_or_uncertain_label": outcome["not_ready_or_uncertain_label"],
                }
            )
        else:
            locked_feature_rows[stage].append(feature_row)

    commitments = {
        "commitment_version": "pferi_v2_stage_outcome_commitments_v1",
        "created_at_utc": utc_now(),
        "algorithm": "sha256_over_sorted_canonical_label_records",
        "locked_stages": {
            stage: {
                "row_count": len(stage_outcomes[stage]),
                "outcome_commitment_sha256": commitment_digest(stage_outcomes[stage]),
            }
            for stage in LOCKED_STAGES
        },
        "development_outcome_commitment_sha256": commitment_digest(stage_outcomes["development"]),
        "label_values_exposed_for_locked_stages": False,
    }
    gate_contract = {
        "contract_version": "pferi_v2_stage_analysis_gate_v1",
        "created_at_utc": utc_now(),
        "current_open_stage": "development",
        "collection_interface_requirement": "nonbinding",
        "rules": {
            "development": {
                "status": "OPEN_FOR_MODEL_DEVELOPMENT",
                "permitted_use": "feature transformation, model-family comparison, regularization selection, cross-validation, and development error analysis",
            },
            "calibration": {
                "status": "LOCKED",
                "unlock_requires": ["development_model_freeze_record.json"],
                "permitted_use_after_unlock": "probability calibration and action-threshold fitting only",
            },
            "deployment_confirmation": {
                "status": "LOCKED",
                "unlock_requires": [
                    "development_model_freeze_record.json",
                    "calibration_policy_freeze_record.json",
                    "confirmation_analysis_bundle_freeze_record.json",
                    "frozen_active_control_predictions.csv",
                    "frozen_full_model_predictions.csv",
                ],
                "permitted_use_after_unlock": "one-shot primary paired Brier and deployment evaluation",
            },
            "mechanism_confirmation": {
                "status": "LOCKED",
                "unlock_requires": [
                    "development_model_freeze_record.json",
                    "calibration_policy_freeze_record.json",
                    "confirmation_analysis_bundle_freeze_record.json",
                    "frozen_active_control_predictions.csv",
                    "frozen_full_model_predictions.csv",
                ],
                "permitted_use_after_unlock": "prespecified mechanism and failure analyses without pooling into the primary deployment estimate",
            },
        },
        "hard_prohibitions": [
            "Do not join locked-stage labels to features or predictions before the declared prerequisites exist and pass validation.",
            "Do not use calibration, deployment-confirmation, or mechanism-confirmation labels for feature selection, model selection, regularization, or missing-data rule selection.",
            "Do not pool mechanism-confirmation pairs into the primary deployment estimand.",
            "Do not rerun or replace the formal 2,224-pair sample.",
        ],
    }
    exposure_register = {
        "register_version": "pferi_v2_task14_exposure_register_v1",
        "created_at_utc": utc_now(),
        "known_pre_task14_exposure": "Aggregate stage label counts were computed during final outcome validation.",
        "this_builder_computed_locked_stage_feature_outcome_associations": False,
        "mitigation": "All subsequent development code must use only development_open/development_modeling_input.csv. Locked-stage feature tables contain no outcome columns.",
    }
    audit: dict[str, Any] = {
        "audit_version": "pferi_v2_stage_isolation_audit_v1",
        "created_at_utc": utc_now(),
        "status": "PASS",
        "current_open_stage": "development",
        "development_open_row_count": len(development_rows),
        "locked_stage_feature_row_counts": {
            stage: len(rows) for stage, rows in locked_feature_rows.items()
        },
        "locked_stage_label_columns_exposed": 0,
        "source_outcome_checksum_files_verified": checked_source_files,
        "source_final_outcome_sha256": sha256_file(outcome_path),
        "source_feature_frame_sha256": sha256_file(feature_frame),
        "source_stage_counts": dict(observed_counts),
        "model_training_permitted_stages": ["development"],
        "model_training_prohibited_stages": list(LOCKED_STAGES),
        "claim_boundary": "Task 14 creates analysis-role isolation. It does not fit, select, calibrate, or evaluate a PF-ERI model.",
    }

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=output_dir.name + ".staging.", dir=output_dir.parent))
    try:
        write_csv(
            staging / "development_open" / "development_modeling_input.csv",
            DEVELOPMENT_OUTPUT_COLUMNS,
            development_rows,
        )
        for stage, rows in locked_feature_rows.items():
            write_csv(
                staging / "outcome_free_locked_features" / f"{stage}_features.csv",
                LOCKED_FEATURE_OUTPUT_COLUMNS,
                rows,
            )
        for name, payload in (
            ("sealed_outcome_commitments.json", commitments),
            ("stage_gate_contract.json", gate_contract),
            ("exposure_register.json", exposure_register),
            ("stage_isolation_audit.json", audit),
        ):
            (staging / name).write_text(
                json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
        checksum_lines = [
            f"{sha256_file(path)}  {path.relative_to(staging)}"
            for path in sorted(staging.rglob("*"))
            if path.is_file() and path.name != "CHECKSUMS.sha256"
        ]
        (staging / "CHECKSUMS.sha256").write_text(
            "\n".join(checksum_lines) + "\n", encoding="utf-8"
        )
        os.replace(staging, output_dir)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return audit


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outcome-dir", type=Path, required=True)
    parser.add_argument("--feature-frame", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    audit = build(
        outcome_dir=args.outcome_dir,
        feature_frame=args.feature_frame,
        output_dir=args.output_dir,
    )
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
