from __future__ import annotations

import copy
import csv
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from scripts import freeze_pferi_v2_model_route_registry as module


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "schemas/pferi_v2/model_route_candidate_registry_v1.json"


class ModelRouteRegistryTests(unittest.TestCase):
    def load_registry(self) -> dict[str, object]:
        return json.loads(REGISTRY.read_text(encoding="utf-8"))

    def write_valid_inputs(self, root: Path, row_count: int = 1) -> tuple[Path, Path, Path]:
        registry = self.load_registry()
        feature_columns = sorted(
            {
                column
                for block in registry["feature_blocks"].values()
                for column in block["columns"]
            }
        )
        fieldnames = [
            "canonical_pair_id",
            "endpoint_a_image_id",
            "endpoint_b_image_id",
            *feature_columns,
            "review_ready_label",
        ]
        development = root / "development.csv"
        with development.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for index in range(row_count):
                row = {column: "0" for column in fieldnames}
                row.update(
                    {
                        "canonical_pair_id": f"pair_{index}",
                        "endpoint_a_image_id": f"a_{index}",
                        "endpoint_b_image_id": f"b_{index}",
                        "review_ready_label": "1",
                    }
                )
                writer.writerow(row)
        stage_gate = root / "stage_gate.json"
        stage_gate.write_text(
            json.dumps(
                {
                    "current_open_stage": "development",
                    "rules": {
                        "calibration": {"status": "LOCKED"},
                        "deployment_confirmation": {"status": "LOCKED"},
                        "mechanism_confirmation": {"status": "LOCKED"},
                    },
                }
            ),
            encoding="utf-8",
        )
        registry_path = root / "registry.json"
        registry_path.write_text(json.dumps(registry), encoding="utf-8")
        return registry_path, development, stage_gate

    def test_default_registry_passes_scientific_invariants(self) -> None:
        registry = self.load_registry()
        issues = module.validate_registry(registry)
        self.assertEqual(issues, [])

        models = {item["model_id"]: item for item in registry["models"]}
        self.assertEqual(models["P3"]["family"], models["P5"]["family"])
        self.assertEqual(models["P3"]["preprocessing_policy"], models["P5"]["preprocessing_policy"])
        self.assertEqual(
            set(models["P5"]["feature_blocks"]) - set(models["P3"]["feature_blocks"]),
            {"pair_evidence"},
        )

    def test_primary_route_rejects_diagnostic_disagreement_feature(self) -> None:
        registry = self.load_registry()
        registry["feature_blocks"]["pair_evidence"]["columns"].append(
            "dual_descriptor_percentile_disagreement"
        )
        issues = module.validate_registry(registry)
        self.assertTrue(any("diagnostic-only" in issue for issue in issues))

    def test_primary_route_rejects_class_rebalancing(self) -> None:
        registry = self.load_registry()
        registry["global_training_rules"]["class_rebalancing"] = "SMOTE"
        issues = module.validate_registry(registry)
        self.assertTrue(any("class rebalancing" in issue for issue in issues))

    def test_duplicate_model_ids_are_rejected(self) -> None:
        registry = self.load_registry()
        registry["models"].append(copy.deepcopy(registry["models"][0]))
        issues = module.validate_registry(registry)
        self.assertTrue(any("duplicate model_id" in issue for issue in issues))

    def test_freeze_records_hashes_without_copying_outcomes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry_path, development, stage_gate = self.write_valid_inputs(root)

            record = module.build_freeze_record(registry_path, development, stage_gate)

            self.assertEqual(record["status"], "FROZEN_PASS")
            self.assertEqual(record["development_row_count"], 1)
            self.assertNotIn("review_ready_label", json.dumps(record))
            self.assertEqual(record["locked_stage_label_columns_read"], 0)

    def test_existing_output_directory_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "existing"
            output.mkdir()
            with self.assertRaises(FileExistsError):
                module.assert_new_output_directory(output)

    def test_run_writes_complete_immutable_freeze_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry_path, development, stage_gate = self.write_valid_inputs(root, row_count=2)
            output = root / "freeze"

            record = module.run(
                registry_path,
                development,
                stage_gate,
                output,
                expected_development_rows=2,
            )

            self.assertEqual(record["status"], "FROZEN_PASS")
            self.assertEqual(
                {path.name for path in output.iterdir()},
                {
                    "candidate_model_registry_frozen.json",
                    "registry_validation_audit.json",
                    "model_route_freeze_record.json",
                    "CHECKSUMS.sha256",
                },
            )
            self.assertIn("P5_vs_P3", (output / "model_route_freeze_record.json").read_text())

    def test_build_rejects_unlocked_calibration_stage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry_path, development, stage_gate = self.write_valid_inputs(root)
            gate = json.loads(stage_gate.read_text())
            gate["rules"]["calibration"]["status"] = "OPEN"
            stage_gate.write_text(json.dumps(gate), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not locked"):
                module.build_freeze_record(registry_path, development, stage_gate)

    def test_run_rejects_unexpected_development_row_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry_path, development, stage_gate = self.write_valid_inputs(root)
            with self.assertRaisesRegex(ValueError, "row count mismatch"):
                module.run(
                    registry_path,
                    development,
                    stage_gate,
                    root / "freeze",
                    expected_development_rows=445,
                )

    def test_cli_main_executes_the_same_freeze_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry_path, development, stage_gate = self.write_valid_inputs(root)
            output = root / "freeze"
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = module.main(
                    [
                        "--registry", str(registry_path),
                        "--development-input", str(development),
                        "--stage-gate", str(stage_gate),
                        "--output-dir", str(output),
                        "--expected-development-rows", "1",
                    ]
                )
            self.assertEqual(code, 0)
            self.assertIn('"status": "FROZEN_PASS"', stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
