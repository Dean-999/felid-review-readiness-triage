from __future__ import annotations

import unittest

from scripts import build_v2_within_role_pair_frames as frames


class WithinRolePairFrameTests(unittest.TestCase):
    def test_rank_band_boundaries(self) -> None:
        self.assertEqual(frames.rank_band(1), "rank_01_05")
        self.assertEqual(frames.rank_band(5), "rank_01_05")
        self.assertEqual(frames.rank_band(6), "rank_06_10")
        self.assertEqual(frames.rank_band(10), "rank_06_10")
        self.assertEqual(frames.rank_band(11), "rank_11_20")
        self.assertEqual(frames.rank_band(20), "rank_11_20")
        with self.assertRaises(ValueError):
            frames.rank_band(21)

    def test_membership_metadata_uses_support_union_and_best_rank(self) -> None:
        metadata = frames.membership_metadata([
            {"canonical_pair_id": "pair_a", "descriptor_name": "megadescriptor_l_384", "candidate_rank": "8"},
            {"canonical_pair_id": "pair_a", "descriptor_name": "dinov2_vitl14", "candidate_rank": "3"},
        ])
        self.assertEqual(metadata["pair_a"]["descriptor_support_category"], "both")
        self.assertEqual(metadata["pair_a"]["best_candidate_rank"], 3)
        self.assertEqual(metadata["pair_a"]["best_rank_band"], "rank_01_05")
        self.assertEqual(metadata["pair_a"]["membership_count"], 2)


if __name__ == "__main__":
    unittest.main()
