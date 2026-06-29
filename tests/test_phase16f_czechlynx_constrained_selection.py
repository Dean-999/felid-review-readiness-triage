import unittest

import pandas as pd

from scripts.build_phase16f_czechlynx_constrained_selection import (
    assign_candidate_buckets,
    build_constrained_selection,
    compute_selection_scores,
    derive_balance_group,
    manual_audit_sample,
)


def row(candidate_id, group, final_score, iqa, side, **extra):
    base = {
        "candidate_id": candidate_id,
        "image_key": f"CzechLynx/source/{group}/{candidate_id}.jpg",
        "image_load_success": "true",
        "scoring_valid_for_selection": "true",
        "final_candidate_score": final_score,
        "iqa_quality_proxy_score": iqa,
        "clip_side_view_score": side,
        "clip_viewpoint_prob_partial_or_occluded": 0.0,
        "clip_viewpoint_prob_unclear": 0.0,
        "clip_viewpoint_prob_frontal": 0.0,
        "clip_viewpoint_prob_rear": 0.0,
        "already_in_current_high_final": "false",
        "strict_recalibrated_eligible": "false",
        "balanced_recalibrated_eligible": "true",
        "broad_recalibrated_eligible": "true",
        "clip_viewpoint_label": "left_side",
    }
    base.update(extra)
    return base


class Phase16FCzechLynxSelectionTests(unittest.TestCase):
    def test_derive_balance_group_uses_identity_like_path_segment(self):
        self.assertEqual(
            derive_balance_group("CzechLynx/foe_carpaths/lynx_296/00001.jpg"),
            "lynx_296",
        )
        self.assertEqual(derive_balance_group("bad/path"), "unknown")

    def test_scores_reward_quality_side_view_and_current_final_bonus(self):
        df = pd.DataFrame(
            [
                row("a", "g1", 0.9, 0.9, 0.9, already_in_current_high_final="true"),
                row("b", "g1", 0.8, 0.8, 0.1),
            ]
        )
        scored = compute_selection_scores(df)

        score_a = float(scored.loc[scored["candidate_id"] == "a", "phase16f_selection_score"].iloc[0])
        score_b = float(scored.loc[scored["candidate_id"] == "b", "phase16f_selection_score"].iloc[0])

        self.assertGreater(score_a, score_b)

    def test_constrained_selection_uses_balanced_pool_and_respects_group_cap(self):
        rows = []
        for i in range(4):
            rows.append(row(f"a{i}", "group_a", 0.95 - i * 0.01, 0.8, 0.7))
        for i in range(4):
            rows.append(row(f"b{i}", "group_b", 0.80 - i * 0.01, 0.8, 0.7))
        rows.append(
            row(
                "reserve",
                "group_c",
                0.99,
                0.9,
                0.9,
                balanced_recalibrated_eligible="false",
                broad_recalibrated_eligible="true",
            )
        )
        df = assign_candidate_buckets(compute_selection_scores(pd.DataFrame(rows)))
        selected, rejected, audit = build_constrained_selection(
            df,
            target_count=4,
            max_per_balance_group=2,
        )

        self.assertEqual(len(selected), 4)
        self.assertEqual(audit["selected_rows"], 4)
        self.assertEqual(audit["broad_reserve_used_count"], 0)
        self.assertLessEqual(selected["phase16f_balance_group"].value_counts().max(), 2)
        self.assertIn("reserve", set(rejected["candidate_id"]))

    def test_manual_audit_sample_includes_requested_buckets(self):
        df = pd.DataFrame(
            [
                row("strict", "g1", 0.9, 0.9, 0.9, strict_recalibrated_eligible="true"),
                row("balanced", "g2", 0.8, 0.8, 0.3),
                row("broad", "g3", 0.7, 0.7, 0.2, balanced_recalibrated_eligible="false"),
            ]
        )
        df = assign_candidate_buckets(compute_selection_scores(df))
        sample = manual_audit_sample(df, per_bucket=1, random_seed=1)

        self.assertGreaterEqual(set(sample["phase16f_selection_bucket"]), {"strict_core", "balanced_only"})


if __name__ == "__main__":
    unittest.main()
