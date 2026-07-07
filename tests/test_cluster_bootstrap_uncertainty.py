from __future__ import annotations

import unittest

from scripts import build_cluster_bootstrap_uncertainty as boot


class ClusterBootstrapUncertaintyTests(unittest.TestCase):
    def test_cluster_bootstrap_resamples_whole_clusters(self) -> None:
        rows = [
            {"cluster": "a", "row_id": "a1"},
            {"cluster": "a", "row_id": "a2"},
            {"cluster": "b", "row_id": "b1"},
        ]

        samples = boot.cluster_bootstrap_samples(rows, "cluster", iterations=5, seed=1)

        self.assertEqual(len(samples), 5)
        for sample in samples:
            sample_ids = [row["row_id"] for row in sample]
            self.assertIn(len(sample_ids), {2, 3, 4})
            if "a1" in sample_ids:
                self.assertIn("a2", sample_ids)

    def test_metric_value_selective_risk_and_coverage(self) -> None:
        rows = [
            {
                "review_ready_label": "1",
                "not_ready_or_uncertain_label": "0",
                "evidence_admission_score": "0.9",
                "alpha_0_15_admitted": "yes",
            },
            {
                "review_ready_label": "0",
                "not_ready_or_uncertain_label": "1",
                "evidence_admission_score": "0.2",
                "alpha_0_15_admitted": "no",
            },
        ]

        self.assertEqual(boot.metric_value(rows, "alpha_0_15_selective_risk"), 0.0)
        self.assertEqual(boot.metric_value(rows, "alpha_0_15_coverage"), 0.5)

    def test_metric_value_skips_auroc_for_single_class(self) -> None:
        rows = [
            {"review_ready_label": "1", "evidence_admission_score": "0.9", "alpha_0_15_admitted": "yes"},
            {"review_ready_label": "1", "evidence_admission_score": "0.8", "alpha_0_15_admitted": "yes"},
        ]

        self.assertIsNone(boot.metric_value(rows, "auroc"))

    def test_interval_row_reports_cluster_count(self) -> None:
        rows = [
            {
                "cluster": "a",
                "calibration_role": "calibration",
                "review_ready_label": "1",
                "not_ready_or_uncertain_label": "0",
                "evidence_admission_score": "0.9",
                "alpha_0_15_admitted": "yes",
            },
            {
                "cluster": "b",
                "calibration_role": "calibration",
                "review_ready_label": "0",
                "not_ready_or_uncertain_label": "1",
                "evidence_admission_score": "0.2",
                "alpha_0_15_admitted": "no",
            },
        ]

        row = boot.interval_row(rows, "test_cluster", "cluster", "all", "alpha_0_15_coverage")

        self.assertEqual(row["cluster_count"], 2)
        self.assertEqual(row["row_count"], 2)
        self.assertEqual(row["point_estimate"], 0.5)
        self.assertEqual(row["uncertainty_status"], "sparse_cluster_warning")


if __name__ == "__main__":
    unittest.main()
