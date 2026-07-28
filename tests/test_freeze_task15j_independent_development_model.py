from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "task15j_freeze",
    ROOT / "scripts/freeze_task15j_independent_development_model.py",
)
M = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(M)


class Task15JIndependentDevelopmentModelFreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.evidence = M.validate_sources()
        cls.bundle = M.fit_final_models(cls.evidence)

    def test_task15i_sources_mechanically_qualify_without_new_thresholds(self) -> None:
        self.assertEqual(self.evidence["validation_failures"], [])
        self.assertEqual(self.evidence["source_checksum_failures"], {})
        self.assertEqual(self.evidence["qualification_status"], "QUALIFIED")
        self.assertEqual(
            self.evidence["task15i_result"]["status"],
            "FROZEN_COMPLETE_TASK15I_DECLARED_MANUAL_REVIEW_DEVELOPMENT_SCREEN_PASS",
        )
        self.assertTrue(
            self.evidence["task15i_design"]["qualification_policy"][
                "passing_development_freeze_authorizes_calibration"
            ]
        )

    def test_full_fit_freezes_exact_nested_p3_p5_models(self) -> None:
        self.assertEqual(self.bundle["training_pair_count"], 1600)
        self.assertEqual(self.bundle["training_component_count"], 400)
        self.assertEqual(self.bundle["fixed_lambda"], 100.0)
        p3_columns = self.bundle["models"]["P3"]["feature_columns"]
        p5_columns = self.bundle["models"]["P5"]["feature_columns"]
        self.assertEqual(p5_columns[: len(p3_columns)], p3_columns)
        self.assertEqual(p5_columns[len(p3_columns) :], M.P5_INCREMENTAL_COLUMNS)
        self.assertEqual(len(p5_columns) - len(p3_columns), 5)
        for model_id in ("P3", "P5"):
            coefficients = np.asarray(
                self.bundle["models"][model_id]["coefficients"], dtype=float
            )
            self.assertEqual(
                len(coefficients),
                len(self.bundle["models"][model_id]["feature_columns"]) + 1,
            )
            self.assertTrue(np.isfinite(coefficients).all())
            self.assertLess(float(np.max(np.abs(coefficients))), 100.0)

    def test_qualified_record_freezes_p5_and_authorizes_calibration(self) -> None:
        record = M.make_record(self.evidence, self.bundle)
        self.assertEqual(record["record_validation_status"], "PASS")
        self.assertEqual(record["qualification_status"], "QUALIFIED")
        self.assertTrue(record["development_model_frozen"])
        self.assertEqual(record["active_control_model_id"], "P3")
        self.assertEqual(record["full_model_id"], "P5")
        self.assertTrue(record["calibration_authorized"])
        self.assertFalse(record["confirmation_authorized"])
        self.assertEqual(M.validate_record(record, self.evidence["schema"]), [])

    def test_schema_rejects_inconsistent_calibration_authorization(self) -> None:
        record = M.make_record(self.evidence, self.bundle)
        record["qualification_status"] = "NOT_QUALIFIED"
        failures = M.validate_record(record, self.evidence["schema"])
        self.assertIn("calibration_authorized_without_qualification", failures)

    def test_freeze_creates_checksum_verified_immutable_package(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "task15j_freeze"
            audit = M.freeze(output=output)
            self.assertEqual(audit["status"], "PASS")
            self.assertEqual(audit["qualification_status"], "QUALIFIED")
            self.assertTrue(audit["development_model_frozen"])
            self.assertTrue(audit["calibration_authorized"])
            self.assertFalse(audit["confirmation_authorized"])
            self.assertTrue((output / "development_model_freeze_record_v2.json").is_file())
            self.assertTrue((output / "final_model_bundle.json").is_file())
            self.assertTrue((output / "qualification_audit.json").is_file())
            self.assertTrue(
                (output / "TASK15J_INDEPENDENT_DEVELOPMENT_MODEL_FREEZE_REPORT.md").is_file()
            )
            self.assertTrue((output / "freeze_builder_snapshot.py").is_file())
            self.assertEqual(M.verify_checksum_manifest(output), [])
            record = json.loads(
                (output / "development_model_freeze_record_v2.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                record["status"],
                "QUALIFIED_P5_DEVELOPMENT_MODEL_FROZEN_CALIBRATION_AUTHORIZED",
            )
            with self.assertRaisesRegex(FileExistsError, "refusing to overwrite"):
                M.freeze(output=output)


if __name__ == "__main__":
    unittest.main()
