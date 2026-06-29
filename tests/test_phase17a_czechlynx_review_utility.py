import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.build_phase17a_czechlynx_review_utility import (
    assign_proxy_review_actions,
    evaluate_abstention_coverage,
    evaluate_conflict_enrichment,
    evaluate_fixed_positive_retention,
    evaluate_fixed_review_budget,
    prepare_review_frame,
    run_phase17a_review_utility,
)


def fixture_scored_pairs() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "pair_id": "p1",
                "query_image_id": "q1",
                "candidate_image_id": "c1",
                "phase16h_label": True,
                "label_allowed_for_modeling": True,
                "source_leakage_pressure_flag": False,
                "descriptor_evidence_conflict_flag": False,
                "score_descriptor_only": 0.95,
                "score_quality_only": 0.90,
                "score_evidence_only": 0.90,
                "score_conflict_penalized_descriptor": 0.94,
                "score_phase16h_diagnostic": 0.92,
            },
            {
                "pair_id": "p2",
                "query_image_id": "q1",
                "candidate_image_id": "c2",
                "phase16h_label": False,
                "label_allowed_for_modeling": True,
                "source_leakage_pressure_flag": False,
                "descriptor_evidence_conflict_flag": True,
                "score_descriptor_only": 0.93,
                "score_quality_only": 0.20,
                "score_evidence_only": 0.45,
                "score_conflict_penalized_descriptor": 0.30,
                "score_phase16h_diagnostic": 0.20,
            },
            {
                "pair_id": "p3",
                "query_image_id": "q2",
                "candidate_image_id": "c3",
                "phase16h_label": True,
                "label_allowed_for_modeling": True,
                "source_leakage_pressure_flag": False,
                "descriptor_evidence_conflict_flag": False,
                "score_descriptor_only": 0.80,
                "score_quality_only": 0.75,
                "score_evidence_only": 0.82,
                "score_conflict_penalized_descriptor": 0.78,
                "score_phase16h_diagnostic": 0.84,
            },
            {
                "pair_id": "p4",
                "query_image_id": "q2",
                "candidate_image_id": "c4",
                "phase16h_label": False,
                "label_allowed_for_modeling": True,
                "source_leakage_pressure_flag": False,
                "descriptor_evidence_conflict_flag": False,
                "score_descriptor_only": 0.70,
                "score_quality_only": 0.30,
                "score_evidence_only": 0.25,
                "score_conflict_penalized_descriptor": 0.65,
                "score_phase16h_diagnostic": 0.32,
            },
            {
                "pair_id": "p5",
                "query_image_id": "q3",
                "candidate_image_id": "c5",
                "phase16h_label": False,
                "label_allowed_for_modeling": True,
                "source_leakage_pressure_flag": True,
                "descriptor_evidence_conflict_flag": True,
                "score_descriptor_only": 0.99,
                "score_quality_only": 0.10,
                "score_evidence_only": 0.10,
                "score_conflict_penalized_descriptor": 0.10,
                "score_phase16h_diagnostic": 0.05,
            },
        ]
    )


class Phase17ACzechLynxReviewUtilityTest(unittest.TestCase):
    def test_prepare_review_frame_excludes_leakage_by_default(self):
        frame = prepare_review_frame(fixture_scored_pairs(), exclude_leakage=True)

        self.assertEqual(len(frame), 4)
        self.assertFalse(frame["source_leakage_pressure_flag"].any())
        self.assertIn("phase17a_label", frame.columns)

    def test_fixed_review_budget_reports_false_burden(self):
        frame = prepare_review_frame(fixture_scored_pairs(), exclude_leakage=True)
        metrics = evaluate_fixed_review_budget(frame, k_values=[1])

        self.assertIn("descriptor_only", set(metrics["policy_id"]))
        self.assertIn("phase17a_diagnostic_review_utility", set(metrics["policy_id"]))
        diagnostic = metrics[metrics["policy_id"].eq("phase17a_diagnostic_review_utility")].iloc[0]
        self.assertEqual(int(diagnostic["retained_positive_pairs"]), 2)
        self.assertEqual(int(diagnostic["retained_false_pairs"]), 0)

    def test_positive_retention_and_abstention_outputs(self):
        frame = prepare_review_frame(fixture_scored_pairs(), exclude_leakage=True)
        retention = evaluate_fixed_positive_retention(frame, targets=[1.0])
        abstention = evaluate_abstention_coverage(frame, coverage_levels=[0.5])

        self.assertTrue((retention["positive_retention"] >= 1.0).all())
        self.assertIn("deferred_false_rate", abstention.columns)

    def test_conflict_enrichment_and_actions(self):
        frame = prepare_review_frame(fixture_scored_pairs(), exclude_leakage=True)
        enrichment = evaluate_conflict_enrichment(frame)
        actions = assign_proxy_review_actions(frame)

        self.assertIn("all_pairs", set(enrichment["subset_name"]))
        self.assertIn("phase17a_proxy_review_action", actions.columns)
        self.assertIn("defer", set(actions["phase17a_proxy_review_action"]))

    def test_run_phase17a_review_utility_writes_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_csv = root / "scored_pairs.csv"
            output_dir = root / "out"
            fixture_scored_pairs().to_csv(input_csv, index=False)

            audit = run_phase17a_review_utility(input_csv=input_csv, output_dir=output_dir)

            self.assertEqual(audit["status"], "PASS")
            self.assertEqual(audit["claim_status"], "REVIEW_UTILITY_VALIDATION_ONLY")
            self.assertTrue((output_dir / "phase17a_fixed_review_budget.csv").exists())
            self.assertTrue((output_dir / "phase17a_fixed_positive_retention.csv").exists())
            self.assertTrue((output_dir / "phase17a_abstention_coverage.csv").exists())
            self.assertTrue((output_dir / "phase17a_conflict_enrichment.csv").exists())
            self.assertTrue((output_dir / "phase17a_proxy_review_action_summary.csv").exists())
            self.assertTrue((output_dir / "phase17a_review_utility_report.md").exists())


if __name__ == "__main__":
    unittest.main()
