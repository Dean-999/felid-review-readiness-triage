import unittest

import pandas as pd

from scripts.audit_phase16g_pair_table import audit_pair_table


def valid_table(dataset_role="czechlynx_known_id"):
    return pd.DataFrame(
        [
            {
                "pair_id": "p1",
                "dataset_role": dataset_role,
                "species_context": "czechlynx" if dataset_role == "czechlynx_known_id" else "bobcat",
                "query_image_id": "q1",
                "candidate_image_id": "c1",
                "descriptor_similarity": 0.8,
                "descriptor_evidence_conflict_flag": False,
                "same_identity_label": True if dataset_role == "czechlynx_known_id" else pd.NA,
                "label_source": "czechlynx_known_id" if dataset_role == "czechlynx_known_id" else "none",
                "label_allowed_for_modeling": True if dataset_role == "czechlynx_known_id" else False,
                "split_group": "fold_0",
            }
        ]
    )


class Phase16GPairTableAuditTest(unittest.TestCase):
    def test_valid_czechlynx_table_passes(self):
        audit = audit_pair_table(valid_table())
        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(audit["errors"], [])

    def test_missing_required_column_fails(self):
        table = valid_table().drop(columns=["pair_id"])
        audit = audit_pair_table(table)
        self.assertEqual(audit["status"], "FAIL")
        self.assertIn("missing_required_columns: pair_id", audit["errors"])

    def test_duplicate_pair_id_fails(self):
        table = pd.concat([valid_table(), valid_table()], ignore_index=True)
        audit = audit_pair_table(table)
        self.assertEqual(audit["status"], "FAIL")
        self.assertIn("duplicate_pair_id_count: 1", audit["errors"])

    def test_self_pair_fails(self):
        table = valid_table()
        table.loc[0, "candidate_image_id"] = "q1"
        audit = audit_pair_table(table)
        self.assertEqual(audit["status"], "FAIL")
        self.assertIn("self_pair_count: 1", audit["errors"])

    def test_bobcat_modeling_label_without_verified_source_fails(self):
        table = valid_table(dataset_role="bobcat_transfer_stress")
        table.loc[0, "label_allowed_for_modeling"] = True
        audit = audit_pair_table(table)
        self.assertEqual(audit["status"], "FAIL")
        self.assertIn("bobcat_modeling_labels_require_verified_or_manual_pair_audit", audit["errors"])


if __name__ == "__main__":
    unittest.main()
