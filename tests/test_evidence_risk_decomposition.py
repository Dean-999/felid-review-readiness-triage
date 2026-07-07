from __future__ import annotations

import unittest

from scripts import build_evidence_risk_decomposition as decomposition


class EvidenceRiskDecompositionTests(unittest.TestCase):
    def test_component_risks_are_bounded(self) -> None:
        row = {
            "visible_pattern_area_score": "0.2",
            "body_part_overlap_score": "0.4",
            "viewpoint_side_compatibility": "0.5",
            "night_or_motion_blur_risk": "0.8",
            "cross_descriptor_agreement_score": "0.4",
            "descriptor_similarity_percentile": "0.9",
            "source_domain_shift_score": "0.85",
        }

        risks = decomposition.component_risks(row)

        self.assertEqual(set(risks), set(decomposition.RISK_FAMILIES))
        self.assertTrue(all(0.0 <= value <= 1.0 for value in risks.values()))

    def test_reason_support_uses_human_reason_votes(self) -> None:
        support = decomposition.reason_support("image_evidence_deficit", "low_evidence:2", "")

        self.assertEqual(support, "human_or_route_supported")

    def test_reason_support_keeps_unsupported_components_as_attribution_only(self) -> None:
        support = decomposition.reason_support("domain_source_stress", "", "")

        self.assertEqual(support, "component_attribution_only")


if __name__ == "__main__":
    unittest.main()
