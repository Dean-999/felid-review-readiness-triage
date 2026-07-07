import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.build_phase17b_bobcat_transfer_stress import (
    build_manual_audit_queue,
    mann_whitney_effect,
    prepare_bobcat_frame,
    run_phase17b_bobcat_transfer_stress,
    source_tier_tests,
)


def fixture_bobcat_scores() -> pd.DataFrame:
    rows = []
    for idx in range(1, 9):
        tier = 1 if idx <= 4 else 2
        strict = idx in {1, 2}
        balanced = idx in {1, 2, 3, 5}
        broad = idx in {1, 2, 3, 4, 5, 6}
        rows.append(
            {
                "candidate_id": f"p16e2_bobcat_{idx:05d}",
                "source_tier": tier,
                "source_role": "primary" if tier == 1 else "topup",
                "image_uri": f"https://example.test/{idx}.jpg",
                "image_load_success": True,
                "scoring_valid_for_selection": True,
                "model_fallback_mode": False,
                "pose_fallback_scoring_used": False,
                "strict_recalibrated_eligible": strict,
                "balanced_recalibrated_eligible": balanced,
                "broad_recalibrated_eligible": broad,
                "final_candidate_score": 0.40 - idx * 0.02 if tier == 1 else 0.24 - idx * 0.005,
                "iqa_quality_proxy_score": 0.55 - idx * 0.01,
                "clip_side_view_score": 0.02 if idx % 2 else 0.001,
                "clip_viewpoint_label": "partial_or_occluded" if idx != 7 else "unclear",
                "clip_viewpoint_confidence": 0.90,
                "clip_viewpoint_prob_partial_or_occluded": 0.95 if idx != 7 else 0.20,
                "clip_viewpoint_prob_unclear": 0.02 if idx != 7 else 0.75,
                "md_geometry_score": 0.30 if tier == 1 else 0.0,
            }
        )
    return pd.DataFrame(rows)


class Phase17BBobcatTransferStressTest(unittest.TestCase):
    def test_prepare_frame_assigns_strata_and_routes(self):
        frame = prepare_bobcat_frame(fixture_bobcat_scores())

        self.assertEqual(len(frame), 8)
        self.assertIn("phase17b_stratum", frame.columns)
        self.assertIn("phase17b_route", frame.columns)
        self.assertIn("strict", set(frame["phase17b_stratum"]))
        self.assertIn("topup_stress_review", set(frame["phase17b_route"]))

    def test_source_tier_tests_return_effect_sizes(self):
        frame = prepare_bobcat_frame(fixture_bobcat_scores())
        tests = source_tier_tests(frame)

        self.assertIn("rank_biserial", tests.columns)
        self.assertIn("median_difference", tests.columns)
        final = tests[tests["metric"].eq("final_candidate_score")].iloc[0]
        self.assertGreater(final["median_difference"], 0)

    def test_manual_audit_queue_samples_each_available_stratum(self):
        frame = prepare_bobcat_frame(fixture_bobcat_scores())
        queue = build_manual_audit_queue(frame, per_source_stratum=1)

        self.assertGreaterEqual(len(queue), 4)
        self.assertIn("manual_audit_batch", queue.columns)
        self.assertTrue(queue["candidate_id"].is_unique)

    def test_mann_whitney_effect_has_expected_direction(self):
        effect = mann_whitney_effect(pd.Series([4, 5, 6]), pd.Series([1, 2, 3]))

        self.assertGreater(effect["rank_biserial"], 0)
        self.assertLessEqual(effect["normal_approx_p"], 1)

    def test_run_phase17b_writes_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_csv = root / "bobcat.csv"
            output_dir = root / "out"
            fixture_bobcat_scores().to_csv(input_csv, index=False)

            audit = run_phase17b_bobcat_transfer_stress(
                input_csv=input_csv,
                output_dir=output_dir,
                per_source_stratum=1,
            )

            self.assertEqual(audit["status"], "PASS")
            self.assertEqual(audit["claim_status"], "TRANSFER_STRESS_REVIEW_READINESS_ONLY")
            self.assertTrue((output_dir / "phase17b_bobcat_metric_summary.csv").exists())
            self.assertTrue((output_dir / "phase17b_bobcat_source_tier_tests.csv").exists())
            self.assertTrue((output_dir / "phase17b_bobcat_manual_audit_sheet.csv").exists())
            self.assertTrue((output_dir / "phase17b_bobcat_transfer_stress_report.md").exists())


if __name__ == "__main__":
    unittest.main()
