from __future__ import annotations

import unittest

from scripts import build_evidence_feature_extraction as features


class EvidenceFeatureExtractionTests(unittest.TestCase):
    def test_bobcat_urban_image_evidence_uses_detector_fields(self) -> None:
        row = {
            "scope": "bobcat-urban",
            "source_md_area_fraction": "0.30",
            "source_pattern_evidence_score": "0.80",
            "source_side_flank_evidence_score": "0.70",
            "source_body_visibility_score": "0.75",
            "source_blur_evidence_score": "0.90",
            "source_image_evidence_risk_score": "0.10",
        }

        evidence = features.image_evidence(row)

        self.assertEqual(evidence["subject_area_score"], 1.0)
        self.assertAlmostEqual(evidence["visible_pattern_area_score"], 0.8)
        self.assertEqual(evidence["blur_risk_score"], 0.1)
        self.assertEqual(evidence["source"], "detector_and_phase14_evidence_fields")

    def test_bobcat_wild_image_evidence_uses_area_and_clarity_when_available(self) -> None:
        row = {
            "scope": "bobcat-wild",
            "source_phase19_area10_area_fraction": "0.15",
            "source_phase19_clarity_second_pass_score": "96",
        }

        evidence = features.image_evidence(row)

        self.assertAlmostEqual(evidence["subject_area_score"], 0.5)
        self.assertAlmostEqual(evidence["visible_pattern_area_score"], 0.62)
        self.assertAlmostEqual(evidence["blur_risk_score"], 0.2)
        self.assertEqual(evidence["source"], "phase19_area10_and_clarity_fields")

    def test_descriptor_agreement_is_neutral_when_scores_are_unavailable(self) -> None:
        pair = {
            "query_image_id": "pferi_bobcat_urban_00001",
            "candidate_image_id": "pferi_bobcat_wild_00001",
        }

        score, md, dino, source = features.descriptor_agreement(pair, {}, {})

        self.assertEqual(score, 0.5)
        self.assertEqual(md, "")
        self.assertEqual(dino, "")
        self.assertEqual(source, "descriptor_scores_unavailable_for_current_scope")

    def test_legacy_phase18_id_maps_five_digit_pferi_ids_to_four_digit_phase18_ids(self) -> None:
        self.assertEqual(
            features.legacy_phase18_id("pferi_lynx_wild_00001"),
            "phase18a_czechlynx_0001",
        )
        self.assertEqual(
            features.legacy_phase18_id("pferi_bobcat_wild_03000"),
            "phase18a_bobcat_3000",
        )

    def test_schema_excludes_identity_labels_from_core_predictors(self) -> None:
        schema = features.feature_schema()

        self.assertNotIn("same_identity_label", schema["core_model_predictors"])
        self.assertNotIn("query_identity_label", schema["core_model_predictors"])
        self.assertNotIn("candidate_identity_label", schema["core_model_predictors"])
        self.assertEqual(schema["fields"]["same_identity_label"]["role"], "target_or_label_not_predictor")

    def test_audit_fails_when_blocked_field_enters_predictor_set(self) -> None:
        schema = features.feature_schema()
        schema["core_model_predictors"] = [*schema["core_model_predictors"], "same_identity_label"]
        row = {
            "pair_family": "known_id_validation",
            "construction_rule": "same_known_id",
            "descriptor_score_source": "descriptor_pair_not_in_returned_topk_scores",
            "visible_pattern_area_source": "proxy",
            "blocked_leakage_fields_present": "same_identity_label",
            **{feature: "0.5" for feature in features.CORE_FEATURES},
        }

        audit = features.audit_features([row], schema)

        self.assertEqual(audit["status"], "FAIL")
        self.assertIn("blocked_fields_in_predictor_set", audit["failures"])


if __name__ == "__main__":
    unittest.main()
