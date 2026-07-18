import unittest

import pandas as pd

from scripts.build_phase16g_czechlynx_pair_prototype import build_pair_rows


class Phase16GCzechLynxPairPrototypeTest(unittest.TestCase):
    def test_build_pair_rows_creates_known_id_labels_and_controls(self):
        selected = pd.DataFrame(
            [
                {
                    "image_id": "a",
                    "identity_id": "id1",
                    "phase16f_tier": "strict_core",
                    "iqa_score": 0.9,
                    "side_probability": 0.8,
                },
                {
                    "image_id": "b",
                    "identity_id": "id1",
                    "phase16f_tier": "strict_core",
                    "iqa_score": 0.8,
                    "side_probability": 0.7,
                },
                {
                    "image_id": "c",
                    "identity_id": "id2",
                    "phase16f_tier": "balanced_only",
                    "iqa_score": 0.7,
                    "side_probability": 0.6,
                },
            ]
        )
        descriptor = pd.DataFrame(
            [
                {
                    "query_image_id": "a",
                    "candidate_image_id": "b",
                    "descriptor_similarity": 0.95,
                    "descriptor_rank": 1,
                    "descriptor_margin": 0.1,
                },
                {
                    "query_image_id": "a",
                    "candidate_image_id": "c",
                    "descriptor_similarity": 0.50,
                    "descriptor_rank": 2,
                    "descriptor_margin": 0.05,
                },
            ]
        )

        rows = build_pair_rows(selected, descriptor, control_regime="phase16f_selected")

        self.assertEqual(len(rows), 2)
        same = rows.loc[rows["candidate_image_id"].eq("b")].iloc[0]
        different = rows.loc[rows["candidate_image_id"].eq("c")].iloc[0]
        self.assertTrue(bool(same["same_identity_label"]))
        self.assertFalse(bool(different["same_identity_label"]))
        self.assertEqual(same["label_source"], "czechlynx_known_id")
        self.assertTrue(bool(same["label_allowed_for_modeling"]))
        self.assertEqual(same["control_regime"], "phase16f_selected")
        self.assertAlmostEqual(same["weakest_iqa_score"], 0.8)

    def test_pairs_missing_from_selected_are_skipped(self):
        selected = pd.DataFrame(
            [
                {"image_id": "a", "identity_id": "id1", "iqa_score": 0.9},
                {"image_id": "b", "identity_id": "id1", "iqa_score": 0.8},
            ]
        )
        descriptor = pd.DataFrame(
            [
                {
                    "query_image_id": "a",
                    "candidate_image_id": "missing",
                    "descriptor_similarity": 0.95,
                },
                {
                    "query_image_id": "a",
                    "candidate_image_id": "b",
                    "descriptor_similarity": 0.95,
                },
            ]
        )

        rows = build_pair_rows(selected, descriptor, control_regime="phase16f_selected")

        self.assertEqual(list(rows["candidate_image_id"]), ["b"])


if __name__ == "__main__":
    unittest.main()
