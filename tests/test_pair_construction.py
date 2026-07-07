from __future__ import annotations

import unittest

from scripts import build_pair_construction as pairs


def row(image_id: str, scope: str, identity: str = "", source_row_number: int = 1) -> dict[str, str]:
    species = "czechlynx" if scope == "lynx-wild" else "bobcat"
    domain = {
        "lynx-wild": "wild",
        "bobcat-wild": "wild",
        "bobcat-urban": "urban_periurban",
    }[scope]
    return {
        "image_id": image_id,
        "scope": scope,
        "species": species,
        "domain_label": domain,
        "source_row_number": str(source_row_number),
        "identity_label": identity,
    }


class PairConstructionTests(unittest.TestCase):
    def test_czechlynx_pairs_include_same_and_different_known_id_labels(self) -> None:
        image_rows = [
            row("lx1", "lynx-wild", "id_a", 1),
            row("lx2", "lynx-wild", "id_a", 2),
            row("lx3", "lynx-wild", "id_b", 3),
            row("lx4", "lynx-wild", "id_b", 4),
            row("lx5", "lynx-wild", "id_c", 5),
        ]

        built = pairs.build_czechlynx_pairs(image_rows)
        same = [item for item in built if item["same_identity_label"] == "yes"]
        different = [item for item in built if item["same_identity_label"] == "no"]

        self.assertGreater(len(same), 0)
        self.assertGreater(len(different), 0)
        self.assertTrue(all(item["identity_relation"] == "known" for item in built))
        self.assertFalse(any(item["query_image_id"] == item["candidate_image_id"] for item in built))
        self.assertTrue(all(item["split_group_key"].startswith("identity:") for item in built))

    def test_bobcat_pairs_are_unlabeled_transfer_stress_only(self) -> None:
        image_rows = [
            row("bw1", "bobcat-wild", source_row_number=1),
            row("bw2", "bobcat-wild", source_row_number=2),
            row("bu1", "bobcat-urban", source_row_number=1),
            row("bu2", "bobcat-urban", source_row_number=2),
        ]

        built = pairs.build_bobcat_pairs(image_rows)

        self.assertGreater(len(built), 0)
        self.assertTrue(all(item["pair_family"] == "transfer_stress" for item in built))
        self.assertTrue(all(item["identity_relation"] == "unlabeled" for item in built))
        self.assertTrue(all(item["same_identity_label"] == "" for item in built))
        self.assertTrue(all(item["query_identity_label"] == "" for item in built))
        self.assertTrue(all(item["candidate_identity_label"] == "" for item in built))

    def test_audit_fails_bobcat_identity_boundary_violation(self) -> None:
        bad_bobcat_pair = {
            "pair_id": "bad",
            "pair_family": "transfer_stress",
            "query_image_id": "bw1",
            "candidate_image_id": "bu1",
            "identity_relation": "known",
            "same_identity_label": "yes",
            "query_identity_label": "x",
            "candidate_identity_label": "x",
            "split_role": "evaluation",
            "pair_scope": "bobcat-wild_to_bobcat-urban",
            "construction_rule": "cross_scope_unlabeled",
        }

        audit = pairs.audit_pairs(
            [
                {
                    "pair_id": "lynx_same",
                    "pair_family": "known_id_validation",
                    "query_image_id": "lx1",
                    "candidate_image_id": "lx2",
                    "same_identity_label": "yes",
                    "split_role": "evaluation",
                    "pair_scope": "lynx-wild",
                    "construction_rule": "same_known_id",
                },
                {
                    "pair_id": "lynx_diff",
                    "pair_family": "known_id_validation",
                    "query_image_id": "lx1",
                    "candidate_image_id": "lx3",
                    "same_identity_label": "no",
                    "split_role": "evaluation",
                    "pair_scope": "lynx-wild",
                    "construction_rule": "different_known_id",
                },
            ],
            [bad_bobcat_pair],
        )

        self.assertEqual(audit["status"], "FAIL")
        self.assertIn("bobcat_identity_boundary_violations", audit["failures"])


if __name__ == "__main__":
    unittest.main()
