from __future__ import annotations

import unittest

from scripts import build_advanced_claim_gates_methods_report as report


class AdvancedClaimGatesMethodsReportTests(unittest.TestCase):
    def test_required_overclaims_are_blocked(self) -> None:
        claims = report.claim_gate_rows()
        blocked = {row["claim_id"] for row in claims if row["status"] == "blocked"}
        allowed = {row["claim_id"] for row in claims if row["status"].startswith("allowed")}

        self.assertIn("allowed_blind_reliability_supported_labels", allowed)
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
        reason = next(row for row in assumptions if row["assumption_id"] == "reason_labels")

        self.assertEqual(budget["status"], "predicted_risk_only")
        self.assertIn("Human labels are reserved", budget["required_wording"])
        self.assertEqual(reason["status"], "blind_reliability_supported_bounded")
        self.assertIn("mechanistic explanation remains component attribution", reason["required_wording"])

    def test_confidence_limitations_table_bounds_paper_claims(self) -> None:
        claims = report.claim_gate_rows()
        rows = report.confidence_limitation_rows(claims)
        levels = {row["confidence_level"] for row in rows}
        topics = {row["topic_id"] for row in rows}

        self.assertIn("high", levels)
        self.assertIn("medium", levels)
        self.assertIn("blocked", levels)
        self.assertIn("blind_reliability_supported_labels", topics)
        self.assertIn("bobcat_identity_metrics", topics)
        self.assertIn("automatic_identity_assignment", topics)
        self.assertIn("new_descriptor_claim", topics)
        self.assertIn("distribution_free_cross_domain_guarantee", topics)

    def test_build_audit_passes_and_counts_statuses(self) -> None:
        audit = report.build()

        self.assertEqual(audit["status"], "PASS")
        self.assertGreaterEqual(audit["claim_status_counts"]["blocked"], 6)
        self.assertGreaterEqual(audit["confidence_level_counts"]["blocked"], 4)
        self.assertFalse(audit["reason_label_enrichment_required"])
        self.assertIn("main_result_table", audit["output_files"])
        self.assertIn("confidence_limitations_table", audit["output_files"])
        self.assertIn("claim_narrative", audit["output_files"])


if __name__ == "__main__":
    unittest.main()
