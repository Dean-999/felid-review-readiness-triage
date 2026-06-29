import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.build_phase16h_czechlynx_readiness_controls import (
    build_confidence_loop,
    compute_policy_scores,
    evaluate_leakage_sensitivity,
    evaluate_topk_controls,
    run_phase16h_readiness,
)


def fixture_pairs() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "pair_id": "p1",
                "query_image_id": "q1",
                "candidate_image_id": "c1",
                "descriptor_similarity": 0.95,
                "weakest_iqa_score": 0.90,
                "query_side_probability": 0.8,
                "candidate_side_probability": 0.7,
                "descriptor_margin": 0.05,
                "source_leakage_pressure_flag": False,
                "laterality_relation": "same_side",
                "same_identity_label": True,
                "label_allowed_for_modeling": True,
                "split_group": "query::id1",
            },
            {
                "pair_id": "p2",
                "query_image_id": "q1",
                "candidate_image_id": "c2",
                "descriptor_similarity": 0.80,
                "weakest_iqa_score": 0.40,
                "query_side_probability": 0.8,
                "candidate_side_probability": 0.2,
                "descriptor_margin": 0.40,
                "source_leakage_pressure_flag": True,
                "laterality_relation": "unknown",
                "same_identity_label": False,
                "label_allowed_for_modeling": True,
                "split_group": "query::id1",
            },
            {
                "pair_id": "p3",
                "query_image_id": "q2",
                "candidate_image_id": "c3",
                "descriptor_similarity": 0.70,
                "weakest_iqa_score": 0.75,
                "query_side_probability": 0.9,
                "candidate_side_probability": 0.8,
                "descriptor_margin": 0.10,
                "source_leakage_pressure_flag": False,
                "laterality_relation": "same_side",
                "same_identity_label": True,
                "label_allowed_for_modeling": True,
                "split_group": "query::id2",
            },
            {
                "pair_id": "p4",
                "query_image_id": "q2",
                "candidate_image_id": "c4",
                "descriptor_similarity": 0.60,
                "weakest_iqa_score": 0.20,
                "query_side_probability": 0.9,
                "candidate_side_probability": 0.1,
                "descriptor_margin": 0.50,
                "source_leakage_pressure_flag": True,
                "laterality_relation": "unknown",
                "same_identity_label": False,
                "label_allowed_for_modeling": True,
                "split_group": "query::id2",
            },
        ]
    )


class Phase16HCzechLynxReadinessControlsTest(unittest.TestCase):
    def test_compute_policy_scores_adds_expected_controls(self):
        scored = compute_policy_scores(fixture_pairs())

        for column in [
            "score_descriptor_only",
            "score_quality_only",
            "score_evidence_only",
            "score_conflict_penalized_descriptor",
            "score_phase16h_diagnostic",
        ]:
            self.assertIn(column, scored.columns)

        self.assertGreater(scored.loc[0, "score_phase16h_diagnostic"], scored.loc[1, "score_phase16h_diagnostic"])

    def test_evaluate_topk_controls_includes_random_same_size(self):
        scored = compute_policy_scores(fixture_pairs())
        metrics = evaluate_topk_controls(scored, k_values=[1], random_repeats=5, random_seed=7)

        self.assertIn("descriptor_only", set(metrics["policy_id"]))
        self.assertIn("quality_only", set(metrics["policy_id"]))
        self.assertIn("random_same_size", set(metrics["policy_id"]))
        random_row = metrics[metrics["policy_id"].eq("random_same_size")].iloc[0]
        self.assertEqual(int(random_row["random_repeats"]), 5)

    def test_confidence_loop_reports_vulnerabilities_and_mitigations(self):
        scored = compute_policy_scores(fixture_pairs())
        controls = evaluate_topk_controls(scored, k_values=[1], random_repeats=5, random_seed=7)
        loop = build_confidence_loop(scored, leakage_sensitivity_available=True, controls=controls)

        self.assertGreaterEqual(len(loop), 1)
        self.assertIn("vulnerability", loop.columns)
        self.assertIn("mitigation", loop.columns)

    def test_leakage_sensitivity_reports_excluded_subset(self):
        scored = compute_policy_scores(fixture_pairs())
        sensitivity = evaluate_leakage_sensitivity(scored, k_values=[1])

        self.assertIn("all_pairs", set(sensitivity["sensitivity_subset"]))
        self.assertIn("leakage_excluded", set(sensitivity["sensitivity_subset"]))
        excluded = sensitivity[sensitivity["sensitivity_subset"].eq("leakage_excluded")]
        self.assertGreater(len(excluded), 0)
        self.assertTrue((excluded["source_leakage_pressure_rate"] == 0.0).all())

    def test_run_phase16h_readiness_writes_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_csv = root / "pairs.csv"
            output_dir = root / "out"
            fixture_pairs().to_csv(input_csv, index=False)

            audit = run_phase16h_readiness(
                input_csv=input_csv,
                output_dir=output_dir,
                random_repeats=3,
                random_seed=11,
            )

            self.assertEqual(audit["status"], "PASS")
            self.assertTrue((output_dir / "phase16h_czechlynx_readiness_audit.json").exists())
            self.assertTrue((output_dir / "phase16h_czechlynx_control_topk_metrics.csv").exists())
            self.assertTrue((output_dir / "phase16h_czechlynx_leakage_sensitivity.csv").exists())
            self.assertTrue((output_dir / "phase16h_czechlynx_confidence_loop.csv").exists())
            self.assertTrue((output_dir / "phase16h_czechlynx_readiness_report.md").exists())


if __name__ == "__main__":
    unittest.main()
