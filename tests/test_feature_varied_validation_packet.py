from __future__ import annotations

import unittest

from scripts import build_feature_varied_validation_packet as packet


class FeatureVariedValidationPacketTests(unittest.TestCase):
    def test_bin_feature_covers_core_feature_ranges(self) -> None:
        self.assertEqual(packet.bin_feature("visible_pattern_area_score", "0.10"), "low_visible_pattern")
        self.assertEqual(packet.bin_feature("visible_pattern_area_score", "0.30"), "mid_visible_pattern")
        self.assertEqual(packet.bin_feature("visible_pattern_area_score", "0.80"), "high_visible_pattern")
        self.assertEqual(packet.bin_feature("cross_descriptor_agreement_score", "0.40"), "low_descriptor_agreement")
        self.assertEqual(packet.bin_feature("cross_descriptor_agreement_score", "0.50"), "neutral_descriptor_agreement")
        self.assertEqual(packet.bin_feature("cross_descriptor_agreement_score", "0.90"), "high_descriptor_agreement")

    def test_select_evenly_is_deterministic_and_spread(self) -> None:
        rows = [
            {"pair_id": f"pair_{idx:03d}", "pair_family": "a", "pair_scope": "b", "construction_rule": "c"}
            for idx in range(10)
        ]
        selected = packet.select_evenly(rows, 3)

        self.assertEqual([row["pair_id"] for row in selected], ["pair_000", "pair_004", "pair_009"])

    def test_audit_fails_constant_feature_packet(self) -> None:
        rows = []
        for idx in range(600):
            row = {
                "feature_varied_id": f"feature_varied_{idx:04d}",
                "query_image_exists": "yes",
                "candidate_image_exists": "yes",
                "pair_family": "known_id_validation",
                "construction_rule": "same_known_id",
                "identity_relation": "known",
                "same_identity_label": "yes",
                "selection_role": "test",
            }
            for feature in packet.CORE_FEATURES:
                row[feature] = "0.5"
                row[f"{feature}_bin"] = packet.bin_feature(feature, "0.5")
            rows.append(row)

        audit = packet.audit_packet(rows, target_rows=600)

        self.assertEqual(audit["status"], "FAIL")
        self.assertIn("core_features_without_variation", audit["failures"])

    def test_audit_bobcat_identity_boundary_is_boolean(self) -> None:
        rows = []
        for idx, value in enumerate(["", "yes"]):
            row = {
                "feature_varied_id": f"feature_varied_{idx:04d}",
                "query_image_exists": "yes",
                "candidate_image_exists": "yes",
                "pair_family": "transfer_stress",
                "construction_rule": "within_scope_unlabeled",
                "identity_relation": "unlabeled",
                "same_identity_label": value,
                "selection_role": "test",
            }
            for feature in packet.CORE_FEATURES:
                row[feature] = "0.5" if idx == 0 else "0.9"
                row[f"{feature}_bin"] = packet.bin_feature(feature, row[feature])
            rows.append(row)

        audit = packet.audit_packet(rows * 300, target_rows=600)

        self.assertEqual(audit["bobcat_identity_boundary_violations"], 300)
        self.assertIn("bobcat_identity_boundary_violation", audit["failures"])

    def test_packet_row_preserves_bobcat_identity_boundary(self) -> None:
        source = {
            "pair_id": "p1",
            "pair_family": "transfer_stress",
            "pair_scope": "bobcat-wild",
            "construction_rule": "within_scope_unlabeled",
            "identity_relation": "unlabeled",
            "same_identity_label": "",
            "query_image_id": "q",
            "candidate_image_id": "c",
            "descriptor_score_source": "none",
            "visible_pattern_area_source": "proxy",
            "source_domain_shift_source": "proxy",
        }
        for feature in packet.CORE_FEATURES:
            source[feature] = "0.5"

        row = packet.packet_row(source, {"q": "missing_q.jpg", "c": "missing_c.jpg"}, "fv1", "test", "multi", "bin")

        self.assertEqual(row["validation_label_role"], "unlabeled_feature_variation_only_no_identity_claim")
        self.assertIn("Bobcat rows are not identity-labeled", row["claim_boundary"])


if __name__ == "__main__":
    unittest.main()
