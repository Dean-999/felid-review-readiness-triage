from __future__ import annotations

import unittest

from scripts import build_v2_full_frame_local_match_shards as shards


class FullFrameLocalMatchShardTests(unittest.TestCase):
    def test_shards_cover_every_pair_once(self) -> None:
        frame = []
        images = []
        for index in range(12):
            images.append({"image_id": f"image_{index}", "image_path_relative": f"images/file_{index}.jpg"})
        for role_index, role in enumerate(("development", "calibration", "confirmation")):
            for pair_index in range(5):
                frame.append({
                    "canonical_pair_id": f"{role}_pair_{pair_index}",
                    "endpoint_a_image_id": f"image_{role_index * 4}",
                    "endpoint_b_image_id": f"image_{role_index * 4 + 1}",
                    "partition_role": role,
                })
        result, linkage, audit = shards.build_shards(frame, images, seed="s" * 64, shard_size=2)
        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(audit["shard_count"], 9)
        self.assertEqual(len(linkage), 15)
        self.assertEqual(sum(len(rows) for rows in result.values()), 15)
        self.assertEqual(len({row["pair_execution_id"] for row in linkage}), 15)

    def test_rejects_missing_image(self) -> None:
        with self.assertRaises(ValueError):
            shards.build_shards(
                [{
                    "canonical_pair_id": "pair_a",
                    "endpoint_a_image_id": "missing",
                    "endpoint_b_image_id": "image_b",
                    "partition_role": "development",
                }],
                [{"image_id": "image_b", "image_path_relative": "images/b.jpg"}],
                seed="x" * 64,
                shard_size=10,
            )


if __name__ == "__main__":
    unittest.main()
