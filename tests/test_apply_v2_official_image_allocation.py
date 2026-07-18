from __future__ import annotations

import unittest
from collections import Counter

from scripts import apply_v2_official_image_allocation as allocation


class OfficialImageAllocationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rows = [
            {
                "image_id": f"image_{index:02d}",
                "image_allocation_cell_id": f"cell_{index % 4}",
            }
            for index in range(30)
        ]

    def test_exact_reproducible_zero_crossing_allocation(self) -> None:
        first, audit = allocation.build_allocation(self.rows, seed="a" * 64, target_per_role=10)
        second, _ = allocation.build_allocation(self.rows, seed="a" * 64, target_per_role=10)
        self.assertEqual(first, second)
        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(audit["cross_role_image_overlap_count"], 0)
        self.assertEqual(Counter(row["partition_role"] for row in first), Counter({
            "development": 10,
            "calibration": 10,
            "confirmation": 10,
        }))

    def test_rejects_duplicate_images(self) -> None:
        duplicate = self.rows + [self.rows[0]]
        with self.assertRaises(ValueError):
            allocation.build_allocation(duplicate, seed="b" * 64, target_per_role=10)


if __name__ == "__main__":
    unittest.main()
