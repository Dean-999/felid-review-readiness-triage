from __future__ import annotations

import unittest

from scripts import build_risk_calibrated_evidence_admission as router


class RiskCalibratedEvidenceAdmissionTests(unittest.TestCase):
    def test_choose_threshold_maximizes_coverage_under_alpha(self) -> None:
        rows = [
            {"evidence_admission_score": 0.9, "not_ready_or_uncertain_label": 0},
            {"evidence_admission_score": 0.8, "not_ready_or_uncertain_label": 0},
            {"evidence_admission_score": 0.7, "not_ready_or_uncertain_label": 1},
            {"evidence_admission_score": 0.2, "not_ready_or_uncertain_label": 1},
        ]

        threshold = router.choose_threshold(rows, 0.25)

        self.assertEqual(threshold["threshold"], 0.8)
        self.assertEqual(threshold["calibration_accepted_count"], 2)
        self.assertEqual(threshold["calibration_empirical_risk"], 0.0)

    def test_empirical_risk_reports_accepted_coverage_and_risk(self) -> None:
        rows = [
            {"evidence_admission_score": 0.9, "not_ready_or_uncertain_label": 0},
            {"evidence_admission_score": 0.8, "not_ready_or_uncertain_label": 1},
            {"evidence_admission_score": 0.1, "not_ready_or_uncertain_label": 1},
        ]

        count, coverage, risk = router.empirical_risk(rows, 0.8)

        self.assertEqual(count, 2)
        self.assertAlmostEqual(coverage, 2 / 3)
        self.assertAlmostEqual(risk, 0.5)

    def test_route_prioritizes_descriptor_conflict(self) -> None:
        row = {
            "evidence_admission_score": 0.95,
            "cross_descriptor_agreement_score": "0.4",
            "descriptor_similarity_percentile": "0.9",
        }

        label, reason = router.route_for_row(row, 0.8, 0.6)

        self.assertEqual(label, "conflict_review")
        self.assertIn("descriptor", reason)


if __name__ == "__main__":
    unittest.main()
