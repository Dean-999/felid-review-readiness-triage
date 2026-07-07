from __future__ import annotations

import unittest

from scripts import build_review_budget_routing as routing


class ReviewBudgetRoutingTests(unittest.TestCase):
    def test_pferi_queue_prioritizes_route_then_score(self) -> None:
        rows = [
            {"route_label": "defer_low_evidence", "evidence_admission_score": "0.99", "descriptor_similarity_percentile": "0.99"},
            {"route_label": "accept_review", "evidence_admission_score": "0.60", "descriptor_similarity_percentile": "0.10"},
            {"route_label": "cautious_review", "evidence_admission_score": "0.95", "descriptor_similarity_percentile": "0.90"},
        ]

        ordered = routing.pferi_queue(rows)

        self.assertEqual([row["route_label"] for row in ordered], ["accept_review", "cautious_review", "defer_low_evidence"])

    def test_descriptor_queue_uses_descriptor_similarity_first(self) -> None:
        rows = [
            {"descriptor_similarity_percentile": "0.20", "evidence_admission_score": "0.99"},
            {"descriptor_similarity_percentile": "0.90", "evidence_admission_score": "0.10"},
        ]

        ordered = routing.descriptor_queue(rows)

        self.assertEqual(ordered[0]["descriptor_similarity_percentile"], "0.90")

    def test_czech_budget_metrics_reports_risk_and_coverage(self) -> None:
        rows = [
            {
                "review_ready_label": "1",
                "not_ready_or_uncertain_label": "0",
                "route_label": "accept_review",
                "evidence_admission_score": "0.9",
                "descriptor_similarity_percentile": "0.8",
            },
            {
                "review_ready_label": "0",
                "not_ready_or_uncertain_label": "1",
                "route_label": "defer_low_evidence",
                "evidence_admission_score": "0.2",
                "descriptor_similarity_percentile": "0.95",
            },
        ]

        metrics = routing.czech_budget_metrics(rows, "pferi_selective_evidence_queue", 1)

        self.assertEqual(metrics["selected_count"], 1)
        self.assertEqual(metrics["empirical_risk"], 0.0)
        self.assertEqual(metrics["evidence_admissible_coverage"], 1.0)
        self.assertEqual(metrics["accept_review_count"], 1)


if __name__ == "__main__":
    unittest.main()
