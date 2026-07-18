from __future__ import annotations

import unittest

import numpy as np

from scripts import run_v2_pilot_quality_measurements as quality


class PilotQualityMeasurementTests(unittest.TestCase):
    def test_native_metrics_are_deterministic(self) -> None:
        image = np.array(
            [
                [[0, 10, 20], [255, 20, 30]],
                [[10, 20, 30], [40, 50, 60]],
            ],
            dtype=np.uint8,
        )
        metrics = quality.native_metrics(image)
        self.assertEqual(metrics["native_pixel_count"], 4)
        self.assertEqual(metrics["exposure_clipping_fraction"], 0.5)
        self.assertGreaterEqual(metrics["sharpness_measure"], 0.0)

    def test_coverage_requires_qualifying_cat_instance(self) -> None:
        self.assertEqual(quality.coverage_from_instances([], score_threshold=0.5, mask_threshold=0.5), (None, "detector_no_subject"))

        mask = np.array([[0.6, 0.4], [0.9, 0.1]], dtype=np.float32)
        instances = [{"label": "cat", "score": 0.8, "mask": mask}]
        coverage, status = quality.coverage_from_instances(instances, score_threshold=0.5, mask_threshold=0.5)
        self.assertEqual(status, "not_missing")
        self.assertEqual(coverage, 0.5)

    def test_rejects_forbidden_execution_manifest_headers(self) -> None:
        with self.assertRaises(ValueError):
            quality.assert_safe_execution_headers(["image_id", "identity_truth", "image_path_relative", "content_sha256"])


if __name__ == "__main__":
    unittest.main()
