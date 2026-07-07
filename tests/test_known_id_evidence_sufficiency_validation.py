from __future__ import annotations

import unittest

from scripts import build_known_id_evidence_sufficiency_validation as validation


class KnownIdEvidenceSufficiencyValidationTests(unittest.TestCase):
    def test_phase18_to_pferi_maps_czechlynx_ids(self) -> None:
        self.assertEqual(
            validation.phase18_to_pferi("phase18a_czechlynx_0001"),
            "pferi_lynx_wild_00001",
        )
        self.assertEqual(
            validation.phase18_to_pferi("phase18a_czechlynx_3000"),
            "pferi_lynx_wild_03000",
        )

    def test_auc_and_average_precision_are_perfect_for_perfect_ranking(self) -> None:
        labels = [1, 1, 0, 0]
        scores = [0.9, 0.8, 0.2, 0.1]

        self.assertEqual(validation.auroc(labels, scores), 1.0)
        self.assertEqual(validation.average_precision(labels, scores), 1.0)

    def test_logistic_training_learns_simple_monotonic_signal(self) -> None:
        xs = [[0.0], [0.1], [0.9], [1.0]]
        ys = [0, 0, 1, 1]
        xs_std, _, _ = validation.standardize(xs, xs)
        weights, intercept = validation.train_logistic(xs_std, ys, epochs=200)
        preds = validation.predict_logistic(xs_std, weights, intercept)

        self.assertLess(preds[0], preds[-1])
        self.assertGreater(validation.auroc(ys, preds), 0.9)

    def test_connected_component_folds_keep_connected_images_together(self) -> None:
        rows = [
            {"review_pair_id": "p1", "query_pferi_image_id": "a", "candidate_pferi_image_id": "b"},
            {"review_pair_id": "p2", "query_pferi_image_id": "b", "candidate_pferi_image_id": "c"},
        ]

        folds = validation.connected_component_folds(rows)

        self.assertEqual(folds["p1"], folds["p2"])


if __name__ == "__main__":
    unittest.main()
