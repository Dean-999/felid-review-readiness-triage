from __future__ import annotations

import unittest

from scripts import build_conformal_selective_router as router


class ConformalSelectiveRouterTests(unittest.TestCase):
    def test_selective_metrics_accepts_low_risk_rows(self) -> None:
        rows = [
            {"evidence_risk_score": "0.1", "not_ready_or_uncertain_label": "0"},
            {"evidence_risk_score": "0.2", "not_ready_or_uncertain_label": "1"},
            {"evidence_risk_score": "0.9", "not_ready_or_uncertain_label": "1"},
        ]

        metrics = router.selective_metrics(rows, 0.2)

        self.assertEqual(metrics["accepted_count"], 2)
        self.assertAlmostEqual(metrics["coverage"], 2 / 3)
        self.assertAlmostEqual(metrics["selective_risk"], 0.5)
        self.assertGreaterEqual(metrics["hoeffding_upper_risk"], metrics["selective_risk"])

    def test_choose_threshold_maximizes_coverage_under_alpha(self) -> None:
        rows = [
            {"evidence_risk_score": "0.1", "not_ready_or_uncertain_label": "0"},
            {"evidence_risk_score": "0.2", "not_ready_or_uncertain_label": "0"},
            {"evidence_risk_score": "0.3", "not_ready_or_uncertain_label": "1"},
            {"evidence_risk_score": "0.9", "not_ready_or_uncertain_label": "1"},
        ]

        threshold = router.choose_threshold(rows, 0.25)

        self.assertEqual(threshold["risk_threshold_tau"], 0.2)
        self.assertEqual(threshold["calibration_accepted_count"], 2)
        self.assertEqual(threshold["calibration_selective_risk"], 0.0)
        self.assertEqual(threshold["selection_rule"], "max_coverage_subject_to_empirical_calibration_risk_le_alpha")

    def test_choose_threshold_reports_no_admission_when_alpha_cannot_be_met(self) -> None:
        rows = [
            {"evidence_risk_score": "0.1", "not_ready_or_uncertain_label": "1"},
            {"evidence_risk_score": "0.2", "not_ready_or_uncertain_label": "1"},
        ]

        threshold = router.choose_threshold(rows, 0.05)

        self.assertEqual(threshold["risk_threshold_tau"], -1.0)
        self.assertEqual(threshold["calibration_accepted_count"], 0)
        self.assertEqual(threshold["finite_sample_status"], "no_admission")

    def test_routed_pairs_use_risk_threshold_direction(self) -> None:
        rows = [
            {
                "descriptor_name": "d",
                "review_pair_id": "p1",
                "fold_id": "0",
                "calibration_role": "calibration",
                "review_ready_label": "1",
                "not_ready_or_uncertain_label": "0",
                "evidence_admission_score": "0.9",
                "evidence_risk_score": "0.1",
            },
            {
                "descriptor_name": "d",
                "review_pair_id": "p2",
                "fold_id": "0",
                "calibration_role": "calibration",
                "review_ready_label": "0",
                "not_ready_or_uncertain_label": "1",
                "evidence_admission_score": "0.4",
                "evidence_risk_score": "0.6",
            },
        ]

        routed = router.routed_pair_rows(rows, 0.15)

        self.assertEqual(routed[0]["alpha_0_15_admitted"], "yes")
        self.assertEqual(routed[1]["alpha_0_15_admitted"], "no")


if __name__ == "__main__":
    unittest.main()
