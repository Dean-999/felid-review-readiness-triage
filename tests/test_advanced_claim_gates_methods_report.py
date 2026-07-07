from __future__ import annotations

import unittest

from scripts import build_advanced_claim_gates_methods_report as report


class AdvancedClaimGatesMethodsReportTests(unittest.TestCase):
    def test_required_overclaims_are_blocked(self) -> None:
        claims = report.claim_gate_rows()
        blocked = {row["claim_id"] for row in claims if row["status"] == "blocked"}

        self.assertIn("blocked_new_descriptor", blocked)
        self.assertIn("blocked_automatic_identity_assignment", blocked)
        self.assertIn("blocked_bobcat_identity_metrics", blocked)
        self.assertIn("blocked_source_heldout_causal_domain_generalization", blocked)
        self.assertIn("blocked_validated_reason_classification", blocked)
        self.assertIn("blocked_unqualified_distribution_free_claim", blocked)

    def test_allowed_claims_have_safe_and_prohibited_wording(self) -> None:
        claims = report.claim_gate_rows()
        allowed = [row for row in claims if row["status"].startswith("allowed")]

        self.assertGreaterEqual(len(allowed), 5)
        for row in allowed:
            self.assertTrue(row["safe_wording"])
            self.assertTrue(row["prohibited_wording"])
            self.assertNotIn("automatic identity", row["safe_wording"].lower())
            self.assertNotIn("new descriptor", row["safe_wording"].lower())

    def test_reason_decomposition_remains_exploratory(self) -> None:
        claims = report.claim_gate_rows()
        reason_claim = next(row for row in claims if row["claim_id"] == "exploratory_component_risk_decomposition")
        blocked_reason = next(row for row in claims if row["claim_id"] == "blocked_validated_reason_classification")

        self.assertEqual(reason_claim["status"], "exploratory")
        self.assertEqual(blocked_reason["status"], "blocked")
        self.assertIn("Reason-label enrichment", reason_claim["remaining_caveat"])

    def test_assumptions_include_no_leakage_budget_rule(self) -> None:
        assumptions = report.assumption_rows()
        budget = next(row for row in assumptions if row["assumption_id"] == "budget_optimization")

        self.assertEqual(budget["status"], "predicted_risk_only")
        self.assertIn("Human labels are reserved", budget["required_wording"])

    def test_build_audit_passes_and_counts_statuses(self) -> None:
        audit = report.build()

        self.assertEqual(audit["status"], "PASS")
        self.assertGreaterEqual(audit["claim_status_counts"]["blocked"], 6)
        self.assertTrue(audit["reason_label_enrichment_required"])


if __name__ == "__main__":
    unittest.main()
