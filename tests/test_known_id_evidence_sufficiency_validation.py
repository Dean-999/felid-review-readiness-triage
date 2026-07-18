from __future__ import annotations

import unittest

from scripts import build_known_id_evidence_sufficiency_validation as validation


class KnownIdEvidenceSufficiencyValidationTests(unittest.TestCase):
    def test_issue3_model_families_are_complete_and_ordered(self) -> None:
        self.assertEqual(list(validation.MODEL_FAMILIES), validation.REQUIRED_MODEL_FAMILIES)

    def test_model_families_do_not_repeat_features(self) -> None:
        for model_family, feature_names in validation.MODEL_FAMILIES.items():
            with self.subTest(model_family=model_family):
                self.assertEqual(len(feature_names), len(set(feature_names)))

    def test_issue3_comparison_rows_preserve_identical_row_sets(self) -> None:
        metrics = []
        for scope in ["pooled", *validation.DESCRIPTORS]:
            for model_family in validation.REQUIRED_MODEL_FAMILIES:
                metrics.append(
                    {
                        "scope": scope,
                        "model_family": model_family,
                        "feature_names": ",".join(validation.MODEL_FAMILIES[model_family]),
                        "row_set_id": f"{scope}_same_rows",
                        "pair_count": 12,
                        "positive_review_ready_count": 8,
                        "negative_not_ready_or_uncertain_count": 4,
                        "auroc": 0.7,
                        "auroc_ci_lower": 0.6,
                        "auroc_ci_upper": 0.8,
                        "auprc": 0.75,
                        "auprc_ci_lower": 0.65,
                        "auprc_ci_upper": 0.85,
                        "brier_score": 0.2,
                        "ece_5bin": 0.1,
                    }
                )

        rows = validation.issue3_comparison_rows(metrics)

        self.assertEqual(len(rows), 18)
        for scope in ["pooled", *validation.DESCRIPTORS]:
            scope_rows = [row for row in rows if row["scope"] == scope]
            self.assertEqual(len({row["row_set_id"] for row in scope_rows}), 1)
            self.assertEqual([row["model_family"] for row in scope_rows], validation.REQUIRED_MODEL_FAMILIES)

    def test_issue3_comparison_rows_block_identity_claims(self) -> None:
        metric = {
            "scope": "pooled",
            "model_family": "",
            "feature_names": "",
            "row_set_id": "pooled_same_rows",
            "pair_count": 12,
            "positive_review_ready_count": 8,
            "negative_not_ready_or_uncertain_count": 4,
            "auroc": 0.7,
            "auroc_ci_lower": 0.6,
            "auroc_ci_upper": 0.8,
            "auprc": 0.75,
            "auprc_ci_lower": 0.65,
            "auprc_ci_upper": 0.85,
            "brier_score": 0.2,
            "ece_5bin": 0.1,
        }
        metrics = []
        for model_family in validation.REQUIRED_MODEL_FAMILIES:
            metrics.append({**metric, "model_family": model_family})

        rows = validation.issue3_comparison_rows(metrics)

        self.assertTrue(rows)
        for row in rows:
            boundary = row["interpretation_boundary"]
            self.assertIn("Human reviewability/evidential admissibility only", boundary)
            self.assertIn("no identity accuracy", boundary)
            self.assertIn("mAP", boundary)
            self.assertIn("MRR", boundary)
            self.assertIn("top-k identity improvement", boundary)


if __name__ == "__main__":
    unittest.main()
