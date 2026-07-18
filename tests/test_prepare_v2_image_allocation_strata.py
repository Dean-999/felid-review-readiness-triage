from __future__ import annotations

import unittest
from collections import Counter

from scripts import prepare_v2_image_allocation_strata as strata


def quality_row(image_id: str, value: int) -> dict[str, str]:
    return {
        "image_id": image_id,
        "image_integrity_status": "pass",
        "image_decode_status": "ok",
        "native_pixel_count": str(100 + value),
        "native_pixel_count_value_status": "not_missing",
        "sharpness_measure": str(10 + value),
        "sharpness_value_status": "not_missing",
        "exposure_clipping_fraction": str((30 - value) / 100),
        "exposure_value_status": "not_missing",
    }


class ImageAllocationStrataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.quality = [quality_row(f"image_{index:02d}", index) for index in range(30)]
        self.canonical = []
        pair_index = 0
        for index in range(30):
            for step in (1, 2):
                other = (index + step) % 30
                if index < other:
                    self.canonical.append({
                        "canonical_pair_id": f"pair_{pair_index}",
                        "endpoint_a_image_id": f"image_{index:02d}",
                        "endpoint_b_image_id": f"image_{other:02d}",
                        "pair_availability_status": "available",
                        "pair_inclusion_status": "eligible",
                    })
                    pair_index += 1

    def test_preflight_assigns_all_images_without_roles(self) -> None:
        rows, audit = strata.prepare_strata(self.quality, self.canonical, expected_image_count=30)
        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(len(rows), 30)
        self.assertEqual(audit["official_seed"], None)
        self.assertFalse(audit["role_assignment_created"])
        self.assertTrue(all("partition_role" not in row for row in rows))

    def test_allocation_is_exact_and_reproducible(self) -> None:
        rows, _ = strata.prepare_strata(self.quality, self.canonical, expected_image_count=30)
        first = strata.allocate_roles(rows, target_per_role=10, seed="unit-test-seed")
        second = strata.allocate_roles(rows, target_per_role=10, seed="unit-test-seed")
        self.assertEqual(first, second)
        self.assertEqual(Counter(first.values()), Counter({"development": 10, "calibration": 10, "confirmation": 10}))

    def test_rejects_graph_image_mismatch(self) -> None:
        with self.assertRaises(ValueError):
            strata.prepare_strata(self.quality[:-1], self.canonical, expected_image_count=29)


if __name__ == "__main__":
    unittest.main()
