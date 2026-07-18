import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.analyze_phase16e_bobcat_scores import (
    build_bobcat_score_analysis,
    build_required_column_report,
    summarize_by_source_tier,
)


def bobcat_row(candidate_id, tier, final_score, iqa, side):
    return {
        "candidate_id": candidate_id,
        "target_quadrant": "urban_bobcat_high_confidence",
        "species_label": "Bobcat",
        "scientific_name": "Lynx rufus",
        "source_mode": "packaged_local",
        "image_uri": f"/images/{candidate_id}.jpg",
        "image_load_success": "true",
        "rejection_reason": "",
        "selection_eligible": "false",
        "final_candidate_score": final_score,
        "iqa_quality_proxy_score": iqa,
        "clip_side_view_score": side,
        "clip_viewpoint_label": "left_side",
        "clip_viewpoint_confidence": 0.8,
        "clip_viewpoint_prob_left_side": 0.7,
        "clip_viewpoint_prob_right_side": 0.2,
        "clip_viewpoint_prob_frontal": 0.01,
        "clip_viewpoint_prob_rear": 0.01,
        "clip_viewpoint_prob_partial_or_occluded": 0.04,
        "clip_viewpoint_prob_unclear": 0.04,
        "pose_enabled": "false",
        "pose_model_name": "",
        "pose_success": "false",
        "pose_failure_reason": "pose_disabled",
        "pose_num_keypoints": "",
        "pose_mean_keypoint_confidence": "",
        "pose_valid_keypoint_fraction": "",
        "pose_body_coverage_score": "",
        "pose_orientation_proxy": "",
        "pose_side_view_proxy": "",
        "pose_front_rear_proxy": "",
        "pose_partial_body_proxy": "",
        "pose_quality_score": "",
        "pose_fallback_scoring_used": "false",
        "scoring_valid_for_selection": "true",
        "source_tier": tier,
        "source_role": "tier_test",
        "source_dataset": "FCF",
        "identity_label_available": "false",
        "topup_reason": "unit_test",
    }


class Phase16EBobcatReceiverTests(unittest.TestCase):
    def test_required_column_report_flags_missing_and_sensitive_columns(self):
        df = pd.DataFrame([{"candidate_id": "a", "identity_label": "secret"}])
        report = build_required_column_report(df)

        self.assertIn("target_quadrant", report["missing_required_columns"])
        self.assertIn("identity_label", report["forbidden_sensitive_columns_present"])

    def test_summarize_by_source_tier_preserves_tier_counts(self):
        df = pd.DataFrame(
            [
                bobcat_row("a", 1, 0.9, 0.8, 0.7),
                bobcat_row("b", 2, 0.5, 0.4, 0.3),
            ]
        )
        summary = summarize_by_source_tier(df)

        self.assertEqual(set(summary["source_tier"].astype(str)), {"1", "2"})

    def test_build_bobcat_score_analysis_writes_recalibrated_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_csv = root / "bobcat_scores.csv"
            output_dir = root / "out"
            pd.DataFrame(
                [
                    bobcat_row("a", 1, 0.9, 0.8, 0.7),
                    bobcat_row("b", 1, 0.8, 0.7, 0.6),
                    bobcat_row("c", 2, 0.4, 0.5, 0.2),
                    bobcat_row("d", 2, 0.2, 0.3, 0.1),
                ]
            ).to_csv(input_csv, index=False)

            audit = build_bobcat_score_analysis(input_csv, output_dir)

            self.assertEqual(audit["input_rows"], 4)
            self.assertTrue((output_dir / "phase16e_bobcat_recalibrated_scores.csv").exists())
            self.assertTrue((output_dir / "phase16e_bobcat_score_analysis_report.md").exists())


if __name__ == "__main__":
    unittest.main()
