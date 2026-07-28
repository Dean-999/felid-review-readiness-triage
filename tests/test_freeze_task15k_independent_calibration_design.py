from __future__ import annotations

import csv
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


FREEZE = load("task15k_freeze_test", ROOT / "scripts/freeze_task15k_independent_calibration_design.py")
RUNNER = load("task15k_runner_test", ROOT / "scripts/task15k_calibration_modelscope_runner.py")
PACKAGE = load("task15k_package_test", ROOT / "scripts/build_task15k_calibration_modelscope_package.py")


class Task15KIndependentCalibrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(FREEZE.CONTRACT_PATH.read_text(encoding="utf-8"))
        cls.temporary = tempfile.TemporaryDirectory()
        cls.output = Path(cls.temporary.name) / "task15k_design"
        cls.audit = FREEZE.freeze(cls.output)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_legacy_calibration_is_recorded_as_incompatible_without_outcome_access(self) -> None:
        legacy = self.audit["legacy_calibration"]
        self.assertEqual(legacy["status"], "INCOMPATIBLE_DESCRIPTOR_TAXONOMY")
        self.assertEqual(legacy["legacy_pair_count"], 445)
        self.assertTrue(legacy["all_legacy_categories_would_be_unknown_under_frozen_P3"])
        self.assertFalse(legacy["calibration_outcomes_accessed"])
        self.assertIn("both", legacy["unsupported_legacy_categories"])

    def test_fixed_seed_produces_compatible_independent_geometry(self) -> None:
        self.assertEqual(self.audit["status"], "PASS")
        self.assertEqual(self.audit["selection_seed"], 77)
        self.assertEqual(self.audit["selected_graph"], {"pair_count": 448, "component_count": 112, "selected_image_count": 560, "maximum_endpoint_degree": 4})
        self.assertEqual(self.audit["task15k_task15i_development_endpoint_overlap_count"], 0)
        with (self.output / "calibration_candidate_pairs.csv").open(newline="", encoding="utf-8") as handle:
            pairs = list(csv.DictReader(handle))
        self.assertEqual(len(pairs), 448)
        self.assertEqual({row["descriptor_support_category"] for row in pairs}, {"both_agreement", "both_reciprocal"})
        self.assertTrue(all(row["selection_evidence_state"] == "outcome_unopened" for row in pairs))
        self.assertEqual(FREEZE.verify_checksum_manifest(self.output), [])

    def test_freeze_rejects_overwrite(self) -> None:
        with self.assertRaisesRegex(FileExistsError, "refusing to overwrite"):
            FREEZE.freeze(self.output)

    def test_frozen_bundle_scores_task15k_inputs_without_refitting(self) -> None:
        with (self.output / "calibration_candidate_pairs.csv").open(newline="", encoding="utf-8") as handle:
            pairs = list(csv.DictReader(handle))
        with (self.output / "quality_reference_percentiles.csv").open(newline="", encoding="utf-8") as handle:
            refs = list(csv.DictReader(handle))
        quality = [{
            "candidate_image_id": row["candidate_image_id"], "content_sha256": row["content_sha256"], "image_decode_status": "ok",
            "native_pixel_count": 1, "sharpness_measure": "1", "exposure_clipping_fraction": "0", "failure_code": "none", "value_status": "not_missing",
        } for row in refs]
        local = [{
            "canonical_pair_id": row["canonical_pair_id"], "failure_code": "none", "value_status": "not_missing",
            "local_match_coverage_fraction": "0.05", "inlier_count": "1", "source_keypoint_count": "10", "target_keypoint_count": "10", "runtime_seconds": "0",
        } for row in pairs]
        bundle = json.loads((FREEZE.TASK15J / "final_model_bundle.json").read_text(encoding="utf-8"))
        frame = RUNNER.build_feature_frame(pairs, quality, local, refs)
        features, predictions = RUNNER.score(bundle, frame)
        self.assertEqual(len(features), 448)
        self.assertEqual(len(predictions), 896)
        self.assertEqual({row["model_id"] for row in predictions}, {"P3", "P5"})
        self.assertTrue(all(0.0 <= float(row["probability_not_ready_or_uncertain"]) <= 1.0 for row in predictions))

    def test_package_builder_creates_hash_verified_standalone_control_package(self) -> None:
        old_design = PACKAGE.DESIGN
        try:
            PACKAGE.DESIGN = self.output
            with tempfile.TemporaryDirectory() as temporary:
                destination = Path(temporary) / "package"
                audit = PACKAGE.build(destination)
                self.assertEqual(audit["status"], "PASS")
                self.assertEqual(audit["image_count"], 560)
                package = destination / PACKAGE.PACKAGE_NAME
                PACKAGE.verify_manifest(package)
                self.assertTrue((destination / f"{PACKAGE.PACKAGE_NAME}.zip").is_file())
        finally:
            PACKAGE.DESIGN = old_design


if __name__ == "__main__":
    unittest.main()
