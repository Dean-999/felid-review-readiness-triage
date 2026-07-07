from __future__ import annotations

import unittest

from scripts import build_advanced_modeling_contract as contract


class AdvancedModelingContractTests(unittest.TestCase):
    def test_authoritative_input_rows_mark_existing_inputs(self) -> None:
        rows = contract.authoritative_input_rows()

        self.assertGreaterEqual(len(rows), 6)
        self.assertTrue(all(row["required"] == "yes" for row in rows))
        self.assertTrue(all(row["exists"] == "yes" for row in rows))

    def test_contract_text_contains_selective_risk_objective_and_label_semantics(self) -> None:
        audit = {
            "status": "PASS",
            "authoritative_inputs_csv": "inputs.csv",
            "output_contract_json": "contract.json",
            "claim_boundaries_csv": "claims.csv",
            "mathematical_target": "maximize accepted-pair coverage subject to selective evidence risk <= alpha",
        }

        text = contract.contract_text(audit)

        self.assertIn("y(p) = 1", text)
        self.assertIn("not-ready-or-uncertain", text)
        self.assertIn("selective_risk(tau)", text)
        self.assertIn("maximize coverage(tau)", text)
        self.assertIn("subject to selective_risk(tau) <= alpha", text)

    def test_claim_boundaries_block_identity_and_descriptor_overclaims(self) -> None:
        blocked = {row["claim_id"] for row in contract.CLAIM_BOUNDARIES if row["status"] == "blocked"}

        self.assertIn("blocked_new_descriptor", blocked)
        self.assertIn("blocked_automatic_identity_assignment", blocked)
        self.assertIn("blocked_bobcat_identity_metrics", blocked)

    def test_missing_required_input_fails_contract_status_logic(self) -> None:
        original = contract.AUTHORITATIVE_INPUTS
        try:
            contract.AUTHORITATIVE_INPUTS = [
                {
                    "input_id": "missing",
                    "path": "outputs/modeling-validation/does-not-exist.csv",
                    "role": "missing",
                    "required": "yes",
                    "claim_use": "test",
                }
            ]
            rows = contract.authoritative_input_rows()
            missing = [row["input_id"] for row in rows if row["required"] == "yes" and row["exists"] != "yes"]

            self.assertEqual(missing, ["missing"])
        finally:
            contract.AUTHORITATIVE_INPUTS = original


if __name__ == "__main__":
    unittest.main()
