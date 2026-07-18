from __future__ import annotations

import unittest

from scripts import build_story_hardening_issue9_consistency_audit as issue9


class StoryHardeningIssue9ConsistencyAuditTests(unittest.TestCase):
    def test_boundary_language_is_classified_safe(self) -> None:
        classification, _ = issue9.line_classification("PF-ERI is not a new descriptor.")

        self.assertEqual(classification, "safe_boundary")

    def test_positive_risk_language_is_classified_unsafe(self) -> None:
        classification, _ = issue9.line_classification("PF-ERI validates Bobcat identity accuracy.")

        self.assertEqual(classification, "unsafe_positive_claim")

    def test_gate_fails_on_unsafe_positive_claims(self) -> None:
        findings = [
            {
                "file": "dummy.md",
                "line_number": 1,
                "risk_family": "bobcat_identity_accuracy",
                "classification": "unsafe_positive_claim",
                "line_text": "PF-ERI validates Bobcat identity accuracy.",
                "rationale": "",
            }
        ]
        claim_presence = [
            {
                "file": "PROJECT_RULES.md",
                "has_similarity_line": True,
                "has_pair_level_language": True,
                "has_post_retrieval_language": True,
            }
        ]

        gate = issue9.audit_gate(findings, claim_presence)

        self.assertEqual(gate["status"], "FAIL")
        self.assertEqual(gate["unsafe_positive_claim_count"], 1)

    def test_gate_passes_with_safe_boundaries_and_core_claims(self) -> None:
        findings = [
            {
                "file": "PROJECT_RULES.md",
                "line_number": 1,
                "risk_family": "descriptor_replacement",
                "classification": "safe_boundary",
                "line_text": "PF-ERI is not a new descriptor.",
                "rationale": "",
            }
        ]
        claim_presence = [
            {
                "file": "PROJECT_RULES.md",
                "has_similarity_line": True,
                "has_pair_level_language": True,
                "has_post_retrieval_language": True,
            },
            {
                "file": "README.md",
                "has_similarity_line": True,
                "has_pair_level_language": True,
                "has_post_retrieval_language": True,
            },
            {
                "file": "docs/CURRENT_PROJECT_MAP.md",
                "has_similarity_line": True,
                "has_pair_level_language": True,
                "has_post_retrieval_language": True,
            },
        ]

        gate = issue9.audit_gate(findings, claim_presence)

        self.assertEqual(gate["status"], "PASS")
        self.assertEqual(gate["unsafe_positive_claim_count"], 0)

    def test_required_claim_bearing_files_are_in_audit_scope(self) -> None:
        checked = {issue9.project_relative(path) for path in issue9.CHECKED_FILES}

        self.assertIn("PROJECT_RULES.md", checked)
        self.assertIn("README.md", checked)
        self.assertIn("docs/CURRENT_PROJECT_MAP.md", checked)
        self.assertIn(
            "archive/pferi_v1/outputs/modeling-validation/advanced-mathematical-validation/paper-ready/final_claim_narrative.md",
            checked,
        )


if __name__ == "__main__":
    unittest.main()
