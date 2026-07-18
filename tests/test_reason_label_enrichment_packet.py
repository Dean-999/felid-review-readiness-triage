from __future__ import annotations

import unittest

from scripts import build_reason_label_enrichment_packet as packet


class ReasonLabelEnrichmentPacketTests(unittest.TestCase):
    def test_reason_vote_count_parses_semicolon_counts(self) -> None:
        self.assertEqual(packet.reason_vote_count("low_evidence:2;occlusion:1"), 3)
        self.assertEqual(packet.reason_vote_count(""), 0)

    def test_normalize_existing_reason_maps_legacy_low_evidence(self) -> None:
        self.assertEqual(packet.normalize_existing_reason("low_evidence"), "low_image_evidence")
        self.assertEqual(packet.normalize_existing_reason("unknown_legacy_reason"), "other")

    def test_relocate_project_path_maps_frozen_v2_images_without_touching_other_paths(self) -> None:
        self.assertEqual(
            packet.relocate_project_path("outputs/final_freeze/lynx-wild/images/example.jpg"),
            "data/frozen/pferi_v2/lynx-wild/images/example.jpg",
        )
        self.assertEqual(
            packet.relocate_project_path("archive/pferi_v1/outputs/example.csv"),
            "archive/pferi_v1/outputs/example.csv",
        )

    def test_build_queue_contains_primary_targets_and_controls(self) -> None:
        rows = packet.build_queue_rows()
        roles = {row["annotation_role"] for row in rows}
        target_count = sum(1 for row in rows if row["annotation_role"] == "primary_not_ready_reason_enrichment")

        self.assertIn("primary_not_ready_reason_enrichment", roles)
        self.assertIn("borderline_review_ready_control", roles)
        self.assertEqual(len(rows), packet.TARGET_TOTAL_REVIEW_ROWS)
        self.assertGreaterEqual(target_count, 200)

    def test_queue_rows_have_existing_images_and_blank_target_fields(self) -> None:
        rows = packet.build_queue_rows()

        self.assertTrue(all(row["query_image_exists"] for row in rows))
        self.assertTrue(all(row["candidate_image_exists"] for row in rows))
        self.assertTrue(all(row["target_primary_reason"] == "" for row in rows))
        self.assertTrue(all("identity" not in row["claim_boundary"].lower() or "not identity" in row["claim_boundary"].lower() for row in rows))

    def test_build_audit_passes(self) -> None:
        audit = packet.build()

        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(audit["selected_rows"], packet.TARGET_TOTAL_REVIEW_ROWS)
        self.assertEqual(audit["primary_not_ready_targets"], 229)
        self.assertFalse(audit["missing_image_rows"])


if __name__ == "__main__":
    unittest.main()
