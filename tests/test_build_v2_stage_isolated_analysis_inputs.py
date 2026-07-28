from __future__ import annotations

import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts import build_v2_stage_isolated_analysis_inputs as builder


class StageIsolatedAnalysisInputTests(unittest.TestCase):
    def write_csv(self, path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def write_json(self, path: Path, payload: dict) -> None:
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def make_inputs(self, root: Path) -> tuple[Path, Path]:
        outcome_dir = root / "outcomes"
        outcome_dir.mkdir()
        stages = ["development", "calibration", "deployment_confirmation", "mechanism_confirmation"]
        outcome_fields = [
            "canonical_pair_id", "formal_sampling_stage", "endpoint_a_image_id", "endpoint_b_image_id",
            "sampling_cell_id", "first_order_inclusion_probability", "final_label_source",
            "final_three_category_label", "review_ready_label", "not_ready_or_uncertain_label",
        ]
        outcomes = []
        features = []
        for index, stage in enumerate(stages):
            pair_id = f"pair_{stage}"
            label = "review_ready" if index % 2 == 0 else "not_review_ready"
            outcomes.append(
                {
                    "canonical_pair_id": pair_id,
                    "formal_sampling_stage": stage,
                    "endpoint_a_image_id": f"image_{index}_a",
                    "endpoint_b_image_id": f"image_{index}_b",
                    "sampling_cell_id": f"cell_{stage}",
                    "first_order_inclusion_probability": "0.5",
                    "final_label_source": "first_pass_exact_agreement",
                    "final_three_category_label": label,
                    "review_ready_label": "1" if label == "review_ready" else "0",
                    "not_ready_or_uncertain_label": "0" if label == "review_ready" else "1",
                }
            )
            role = "confirmation" if "confirmation" in stage else stage
            features.append(
                {
                    "canonical_pair_id": pair_id,
                    "pair_execution_id": f"execution_{index}",
                    "analytical_role": role,
                    "endpoint_a_image_id": f"image_{index}_a",
                    "endpoint_b_image_id": f"image_{index}_b",
                    "descriptor_support_category": "both",
                    "best_rank_band": "rank_01_05",
                    "retrieval_stratum_id": "both__rank_01_05",
                    "megadescriptor_similarity": "0.8",
                    "dinov2_similarity": "0.7",
                    "megadescriptor_within_role_percentile": "0.8",
                    "dinov2_within_role_percentile": "0.7",
                    "dual_descriptor_percentile_disagreement": "0.1",
                    "dual_descriptor_disagreement_within_role_percentile": "0.2",
                    "endpoint_native_pixel_quality_percentile_min": "0.6",
                    "endpoint_sharpness_quality_percentile_min": "0.5",
                    "endpoint_exposure_quality_percentile_min": "0.4",
                    "endpoint_quality_measurement_failure": "false",
                    "endpoint_frozen_quality_stress": "false",
                    "local_match_coverage_fraction": "0.03",
                    "local_match_within_role_percentile": "0.55",
                    "local_match_measurement_failure": "false",
                    "development_evidence_state": "ordinary" if stage == "development" else "",
                    "development_sampling_cell_id": "cell" if stage == "development" else "",
                }
            )
        outcome_path = outcome_dir / "final_adjudicated_outcomes.csv"
        self.write_csv(outcome_path, outcome_fields, outcomes)
        self.write_json(
            outcome_dir / "final_outcome_audit.json",
            {"status": "PASS", "model_analysis_authorized": True, "formal_pair_count": 4},
        )
        self.write_json(
            outcome_dir / "adjudication_acceptance_disposition.json",
            {"status": "PASS_OWNER_ACCEPTED_HUMAN_ADJUDICATION", "model_analysis_authorized": True},
        )
        checksum_rows = []
        for path in sorted(outcome_dir.glob("*")):
            if path.name != "CHECKSUMS.sha256":
                checksum_rows.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}")
        (outcome_dir / "CHECKSUMS.sha256").write_text("\n".join(checksum_rows) + "\n", encoding="utf-8")

        feature_path = root / "outcome_free_features.csv"
        self.write_csv(feature_path, builder.OUTCOME_FREE_FEATURE_COLUMNS, features)
        return outcome_dir, feature_path

    def test_opens_only_development_labels_and_keeps_other_feature_tables_outcome_free(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            outcome_dir, feature_path = self.make_inputs(root)
            output = root / "stage_inputs"
            audit = builder.build(
                outcome_dir=outcome_dir,
                feature_frame=feature_path,
                output_dir=output,
                expected_stage_counts={
                    "development": 1,
                    "calibration": 1,
                    "deployment_confirmation": 1,
                    "mechanism_confirmation": 1,
                },
            )

            self.assertEqual(audit["status"], "PASS")
            self.assertEqual(audit["development_open_row_count"], 1)
            development_path = output / "development_open" / "development_modeling_input.csv"
            with development_path.open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                development_rows = list(reader)
                development_fields = reader.fieldnames or []
            self.assertEqual(development_rows[0]["formal_sampling_stage"], "development")
            self.assertIn("review_ready_label", development_fields)

            prohibited = {"final_three_category_label", "review_ready_label", "not_ready_or_uncertain_label"}
            for stage in ("calibration", "deployment_confirmation", "mechanism_confirmation"):
                path = output / "outcome_free_locked_features" / f"{stage}_features.csv"
                with path.open(newline="", encoding="utf-8") as handle:
                    reader = csv.DictReader(handle)
                    rows = list(reader)
                    fields = set(reader.fieldnames or [])
                self.assertEqual(len(rows), 1)
                self.assertTrue(prohibited.isdisjoint(fields))

            commitments = json.loads((output / "sealed_outcome_commitments.json").read_text())
            self.assertEqual(set(commitments["locked_stages"]), {
                "calibration", "deployment_confirmation", "mechanism_confirmation"
            })
            self.assertNotIn("review_ready", json.dumps(commitments["locked_stages"]))

    def test_rejects_missing_feature_join(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            outcome_dir, feature_path = self.make_inputs(root)
            with feature_path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.write_csv(feature_path, builder.OUTCOME_FREE_FEATURE_COLUMNS, rows[:-1])
            with self.assertRaisesRegex(ValueError, "feature frame does not exactly cover formal outcomes"):
                builder.build(
                    outcome_dir=outcome_dir,
                    feature_frame=feature_path,
                    output_dir=root / "stage_inputs",
                    expected_stage_counts={
                        "development": 1, "calibration": 1,
                        "deployment_confirmation": 1, "mechanism_confirmation": 1,
                    },
                )

    def test_rejects_unpassed_source_disposition(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            outcome_dir, feature_path = self.make_inputs(root)
            self.write_json(
                outcome_dir / "adjudication_acceptance_disposition.json",
                {"status": "FAIL", "model_analysis_authorized": False},
            )
            with self.assertRaisesRegex(ValueError, "source disposition does not authorize model analysis"):
                builder.build(
                    outcome_dir=outcome_dir,
                    feature_frame=feature_path,
                    output_dir=root / "stage_inputs",
                    expected_stage_counts={
                        "development": 1, "calibration": 1,
                        "deployment_confirmation": 1, "mechanism_confirmation": 1,
                    },
                )

    def test_rejects_source_checksum_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            outcome_dir, feature_path = self.make_inputs(root)
            with (outcome_dir / "final_adjudicated_outcomes.csv").open("a", encoding="utf-8") as handle:
                handle.write("tampered\n")
            with self.assertRaisesRegex(ValueError, "source outcome checksum mismatch"):
                builder.build(
                    outcome_dir=outcome_dir,
                    feature_frame=feature_path,
                    output_dir=root / "stage_inputs",
                    expected_stage_counts={
                        "development": 1, "calibration": 1,
                        "deployment_confirmation": 1, "mechanism_confirmation": 1,
                    },
                )

    def test_refuses_to_overwrite_existing_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            outcome_dir, feature_path = self.make_inputs(root)
            output = root / "stage_inputs"
            output.mkdir()
            with self.assertRaisesRegex(FileExistsError, "refusing to overwrite"):
                builder.build(
                    outcome_dir=outcome_dir,
                    feature_frame=feature_path,
                    output_dir=output,
                    expected_stage_counts={
                        "development": 1, "calibration": 1,
                        "deployment_confirmation": 1, "mechanism_confirmation": 1,
                    },
                )


if __name__ == "__main__":
    unittest.main()
