from __future__ import annotations

import unittest

from scripts import build_robustness_and_claim_gates as gates


class RobustnessAndClaimGatesTests(unittest.TestCase):
    def test_metric_summary_computes_accept_risk(self) -> None:
        rows = [
            {
                "review_ready_label": "1",
                "not_ready_or_uncertain_label": "0",
                "evidence_admission_score": "0.9",
                "route_label": "accept_review",
            },
            {
                "review_ready_label": "0",
                "not_ready_or_uncertain_label": "1",
                "evidence_admission_score": "0.2",
                "route_label": "defer_low_evidence",
            },
        ]

        row = gates.metric_summary("test", "scope", "subgroup", rows)

        self.assertEqual(row["pair_count"], 2)
        self.assertEqual(row["auroc"], 1.0)
        self.assertEqual(row["accept_review_count"], 1)
        self.assertEqual(row["accept_review_empirical_risk"], 0.0)

    def test_reliability_rows_keep_empty_bins(self) -> None:
        rows = [
            {"review_ready_label": "1", "evidence_admission_score": "0.9"},
            {"review_ready_label": "0", "evidence_admission_score": "0.1"},
        ]

        out = gates.reliability_rows(rows, "tiny", bins=5)

        self.assertEqual(len(out), 5)
        self.assertEqual(sum(1 for row in out if row["row_count"]), 2)

    def test_no_source_features_remove_source_domain_shift(self) -> None:
        self.assertIn("source_domain_shift_score", gates.FULL_FEATURES)
        self.assertNotIn("source_domain_shift_score", gates.NO_SOURCE_FEATURES)


if __name__ == "__main__":
    unittest.main()
