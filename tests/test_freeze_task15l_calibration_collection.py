from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("task15l_freeze_test", ROOT / "scripts/freeze_task15l_calibration_collection.py")
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
sys.modules["task15l_freeze_test"] = M
SPEC.loader.exec_module(M)


class Task15LCalibrationCollectionTests(unittest.TestCase):
    def test_contract_locks_label_access_until_collection_and_limits_recalibration(self) -> None:
        contract = json.loads(M.CONTRACT.read_text(encoding="utf-8"))
        self.assertFalse(contract["input_requirements"]["calibration_labels_open_at_contract_freeze"])
        self.assertEqual(contract["input_requirements"]["pair_count"], 448)
        self.assertEqual(contract["label_assembly"]["first_pass_reviews_per_pair"], 2)
        self.assertEqual(contract["calibration_model"]["allowed_parameters"], ["intercept", "slope"])
        self.assertIn("refitting P3 or P5 coefficients", contract["calibration_model"]["prohibited"])

    def test_reviewer_inputs_are_balanced_and_blinded_before_package_rendering(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as temporary:
            stage = Path(temporary)
            result = M.build_reviewer_inputs(stage)
            self.assertEqual(len(result["assignments"]), 896)
            self.assertEqual(len(result["eligibility"]), 448)
            self.assertEqual(set(result["loads"].values()), {224})
            self.assertEqual(len(result["execution"]), 560)
            self.assertTrue(all(row["formal_sampling_stage"] == "calibration" for row in result["assignments"]))
            self.assertTrue(all(row["assignment_status"] == "provisional_not_released" for row in result["assignments"]))
            self.assertTrue(all(len({row["reviewer_code"], row["peer_reviewer_code"]}) == 2 for row in result["assignments"]))

    def test_external_export_declaration_is_well_formed(self) -> None:
        self.assertEqual(M.parse_declared_sha(M.DEFAULT_EXPORT_SHA), M.sha256(M.DEFAULT_EXPORT))


if __name__ == "__main__":
    unittest.main()
