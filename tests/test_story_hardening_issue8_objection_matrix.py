from __future__ import annotations

import unittest

from scripts import build_story_hardening_issue8_objection_matrix as issue8


class StoryHardeningIssue8ObjectionMatrixTests(unittest.TestCase):
    def test_matrix_covers_all_required_objections(self) -> None:
        rows = issue8.objection_rows()
        covered = {row["objection_id"] for row in rows}

        self.assertEqual(set(issue8.REQUIRED_OBJECTIONS), covered)

    def test_each_objection_has_evidence_or_boundary(self) -> None:
        rows = issue8.objection_rows()

        for row in rows:
            has_evidence = bool(row["primary_artifact"].strip() or row["appendix_or_sensitivity_artifact"].strip())
            has_boundary = "blocked" in row["answer_type"] or bool(row["blocked_wording"].strip())
            self.assertTrue(has_evidence or has_boundary, row["objection_id"])

    def test_bobcat_identity_objection_is_explicitly_blocked(self) -> None:
        rows = {row["objection_id"]: row for row in issue8.objection_rows()}
        bobcat = rows["bobcat_identity_label_absence"]

        self.assertEqual(bobcat["answer_type"], "explicitly_blocked_as_claim")
        self.assertIn("Bobcat identity accuracy", bobcat["blocked_wording"])
        self.assertIn("transfer-stress", bobcat["safe_wording"])

    def test_claim_gate_passes_only_when_required_objections_present(self) -> None:
        rows = issue8.objection_rows()
        gate = issue8.claim_gate(rows)

        self.assertEqual(gate["status"], "PASS")
        self.assertEqual(gate["missing_required_objections"], [])
        self.assertIn("PF-ERI is a new descriptor or embedding.", gate["blocked_claims"])

    def test_claim_gate_fails_when_required_objection_missing(self) -> None:
        rows = [row for row in issue8.objection_rows() if row["objection_id"] != "quality_proxy"]
        gate = issue8.claim_gate(rows)

        self.assertEqual(gate["status"], "FAIL")
        self.assertEqual(gate["missing_required_objections"], ["quality_proxy"])


if __name__ == "__main__":
    unittest.main()
