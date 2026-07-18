from __future__ import annotations

import unittest

from scripts import build_story_hardening_issue4_sensitivity as issue4


def row(index: int, ready: int, quality: float, similarity: float, pf_signal: float) -> dict[str, str]:
    return {
        "descriptor_name": "megadescriptor_l_384" if index % 2 == 0 else "dinov2_vitl14",
        "review_pair_id": f"pair_{index:03d}",
        "review_ready_label": str(ready),
        "not_ready_or_uncertain_label": str(1 - ready),
        "rank_bin": "rank_02_05" if index < 20 else "rank_06_10",
        "descriptor_similarity_percentile": str(similarity),
        "visible_pattern_area_score": str(quality),
        "body_part_overlap_score": str(pf_signal),
        "night_or_motion_blur_risk": "0.1",
        "cross_descriptor_agreement_score": str(pf_signal),
        "source_domain_shift_score": "0.1",
    }


class StoryHardeningIssue4SensitivityTests(unittest.TestCase):
    def test_quality_matched_rows_use_reviewability_endpoint(self) -> None:
        rows = issue4.add_scores(
            [row(i, 1 if i >= 20 else 0, 0.7 + (i % 4) * 0.01, 0.85, i / 39) for i in range(40)]
        )

        output = issue4.quality_matched_rows(rows)

        self.assertTrue(output)
        for item in output:
            self.assertIn("review_ready_count", item)
            self.assertIn("not_ready_or_uncertain_count", item)
            self.assertIn("human reviewability/evidential admissibility only", item["claim_boundary"])
            self.assertNotIn("identity accuracy claim", item["interpretation"].lower())

    def test_high_similarity_subset_selects_top_similarity_quartile(self) -> None:
        rows = issue4.add_scores([row(i, 1 if i >= 15 else 0, 0.8, i / 39, i / 39) for i in range(40)])

        output = issue4.high_similarity_rows(rows)
        pooled = next(item for item in output if item["scope"] == "pooled")

        self.assertEqual(pooled["analysis_name"], "high_similarity_only")
        self.assertEqual(pooled["stratum_label"], "top_similarity_quartile")
        self.assertGreaterEqual(pooled["mean_descriptor_similarity"], 0.75)

    def test_sparse_or_unsplit_stratum_is_not_estimable(self) -> None:
        rows = issue4.add_scores([row(i, 1, 0.8, 0.9, 0.5) for i in range(10)])

        summary = issue4.median_split_summary("x", "pooled", "sparse", rows)

        self.assertEqual(summary["estimability_status"], "not_estimable_sparse_or_no_split")
        self.assertIn("too sparse", summary["interpretation"])

    def test_feature_variation_audit_flags_constant_features(self) -> None:
        rows = issue4.add_scores([row(i, 1 if i % 2 else 0, 0.74, 0.8 + i / 100, i / 39) for i in range(40)])

        audit = issue4.feature_variation_audit(rows)

        self.assertEqual(audit["visible_pattern_area_score"]["estimability_status"], "not_estimable_constant_feature")
        self.assertEqual(audit["night_or_motion_blur_risk"]["estimability_status"], "not_estimable_constant_feature")
        self.assertEqual(audit["descriptor_similarity_percentile"]["estimability_status"], "estimable")

    def test_overall_status_requires_positive_estimable_sensitivity(self) -> None:
        positive = {
            "estimability_status": "estimable",
            "high_minus_low_review_ready_rate": 0.25,
        }
        negative = {
            "estimability_status": "estimable",
            "high_minus_low_review_ready_rate": -0.1,
        }

        self.assertEqual(issue4.overall_status([positive]), "PASS_WITH_BOUNDARIES")
        self.assertEqual(issue4.overall_status([negative]), "FAIL_NO_POSITIVE_SENSITIVITY")


if __name__ == "__main__":
    unittest.main()
