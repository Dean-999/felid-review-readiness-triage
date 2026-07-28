from __future__ import annotations

import unittest

import numpy as np

from scripts import analyze_task15i_human_reviews as analysis


class Task15IHumanReviewAnalysisTests(unittest.TestCase):
    def test_conservative_label_requires_two_ready_decisions(self) -> None:
        self.assertEqual(analysis.conservative_outcome("review_ready", "review_ready"), 0)
        self.assertEqual(analysis.conservative_outcome("review_ready", "uncertain"), 1)
        self.assertEqual(analysis.conservative_outcome("not_review_ready", "review_ready"), 1)

    def test_qualification_requires_all_frozen_gates(self) -> None:
        checks = {
            "analyzable_pair_count": 1600,
            "delta_brier_P3_minus_P5": 0.005,
            "nonnegative_outer_fold_count": 4,
            "p5_calibration_intercept": 0.20,
            "p5_calibration_slope": 0.80,
            "all_probabilities_finite": True,
            "all_probabilities_in_unit_interval": True,
            "endpoint_leakage_count": 0,
            "fixed_lambda": 100.0,
            "p5_incremental_feature_count": 5,
        }
        self.assertTrue(analysis.qualify(checks))
        checks["delta_brier_P3_minus_P5"] = 0.004999
        self.assertFalse(analysis.qualify(checks))

    def test_nested_feature_contract_requires_exact_five_columns(self) -> None:
        p3 = ["a", "b"]
        self.assertEqual(analysis.assert_nested_columns(p3, [*p3, *analysis.P5_INCREMENTAL_COLUMNS]), 5)

    def test_ridge_fit_returns_finite_coefficients(self) -> None:
        coefficients = analysis.fit_ridge(
            np.asarray([[0.0], [1.0], [0.0], [1.0]]),
            np.asarray([0.0, 1.0, 0.0, 1.0]),
            np.ones(4),
            100.0,
        )
        self.assertTrue(np.isfinite(coefficients).all())


if __name__ == "__main__":
    unittest.main()
