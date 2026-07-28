from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import task15m_confirmation_modelscope_runner as runner


class Task15MConfirmationRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pair = {
            "canonical_pair_id": "pair_1", "component_id": "component_1", "formal_sampling_stage": "deployment_confirmation",
            "endpoint_a_image_id": "image_a", "endpoint_b_image_id": "image_b",
            "descriptor_support_category": "PENDING_CURRENT_DESCRIPTOR_INFERENCE", "best_rank_band": "PENDING_CURRENT_DESCRIPTOR_INFERENCE",
            "selection_evidence_state": "outcome_unopened",
        }

    def test_classifies_same_direction_dual_descriptor_as_supported(self) -> None:
        measurements, supported, unsupported = runner.classify_pairs(
            [self.pair],
            [{"query_image_id": "image_a", "candidate_image_id": "image_b", "candidate_rank": 3}],
            [{"query_image_id": "image_a", "candidate_image_id": "image_b", "candidate_rank": 4}],
        )
        self.assertEqual(measurements[0]["descriptor_support_category"], "both_agreement")
        self.assertEqual(measurements[0]["best_rank_band"], "top_5")
        self.assertEqual(len(supported), 1)
        self.assertEqual(unsupported, [])

    def test_requires_same_direction_consensus(self) -> None:
        measurements, supported, unsupported = runner.classify_pairs(
            [self.pair],
            [{"query_image_id": "image_a", "candidate_image_id": "image_b", "candidate_rank": 3}],
            [{"query_image_id": "image_b", "candidate_image_id": "image_a", "candidate_rank": 3}],
        )
        self.assertEqual(measurements[0]["descriptor_support_category"], "unsupported")
        self.assertEqual(supported, [])
        self.assertEqual(unsupported[0]["unsupported_reason"], "no_same_direction_dual_descriptor_top20_consensus")

    def test_uses_fixed_reference_cdf_and_logit_calibration(self) -> None:
        percentiles = runner.percentile_reference(
            [{"candidate_image_id": "new", "content_sha256": "0" * 64, "failure_code": "none", "native_pixel_count": "5", "sharpness_measure": "5", "exposure_clipping_fraction": "5"}],
            [
                {"candidate_image_id": "low", "content_sha256": "1" * 64, "failure_code": "none", "native_pixel_count": "1", "sharpness_measure": "1", "exposure_clipping_fraction": "1"},
                {"candidate_image_id": "high", "content_sha256": "2" * 64, "failure_code": "none", "native_pixel_count": "10", "sharpness_measure": "10", "exposure_clipping_fraction": "10"},
            ],
        )
        self.assertEqual(percentiles[0]["endpoint_native_pixel_quality_percentile"], "0.500000000000")
        calibrated = runner.apply_calibration(
            [{"canonical_pair_id": "pair_1", "model_id": "P3", "probability_not_ready_or_uncertain": "0.5"}],
            {"fixed_task15l_calibration": {"P3": {"intercept": 1.0, "slope": 2.0}}},
        )
        self.assertAlmostEqual(float(calibrated[0]["calibrated_probability_not_ready_or_uncertain"]), 1.0 / (1.0 + math.exp(-1.0)))


if __name__ == "__main__":
    unittest.main()
