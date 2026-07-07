from __future__ import annotations

import unittest

from scripts import build_bobcat_wild_urban_transfer_stress as transfer


class BobcatWildUrbanTransferStressTests(unittest.TestCase):
    def test_score_row_uses_neutral_descriptor_percentile(self) -> None:
        strong_row = {
            "visible_pattern_area_score": "0.8",
            "viewpoint_side_compatibility": "0.7",
            "body_part_overlap_score": "0.6",
            "night_or_motion_blur_risk": "0.1",
            "cross_descriptor_agreement_score": "0.5",
            "source_domain_shift_score": "0.0",
            "descriptor_similarity_percentile": "1.0",
        }
        weak_row = {
            "visible_pattern_area_score": "0.2",
            "viewpoint_side_compatibility": "0.2",
            "body_part_overlap_score": "0.2",
            "night_or_motion_blur_risk": "0.9",
            "cross_descriptor_agreement_score": "0.2",
            "source_domain_shift_score": "0.8",
            "descriptor_similarity_percentile": "1.0",
        }
        weights = [
            -1.0 if name in {"night_or_motion_blur_risk", "source_domain_shift_score"} else 1.0
            for name in transfer.FEATURE_NAMES
        ]
        means = [0.5 for _ in transfer.FEATURE_NAMES]
        stds = [1.0 for _ in transfer.FEATURE_NAMES]

        strong_score = transfer.score_row(strong_row, weights, 0.0, means, stds)
        strong_row["descriptor_similarity_percentile"] = "0.0"
        neutralized_score = transfer.score_row(strong_row, weights, 0.0, means, stds)
        weak_score = transfer.score_row(weak_row, weights, 0.0, means, stds)

        self.assertAlmostEqual(strong_score, neutralized_score)
        self.assertGreater(strong_score, weak_score)
        self.assertGreater(strong_score, 0.0)
        self.assertLess(strong_score, 1.0)


if __name__ == "__main__":
    unittest.main()
