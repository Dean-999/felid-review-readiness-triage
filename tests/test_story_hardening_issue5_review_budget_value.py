from __future__ import annotations

import unittest

from scripts import build_story_hardening_issue5_review_budget_value as issue5


def row(
    index: int,
    route: str,
    evidence: float,
    similarity: float,
    ready: int,
    same_id: str,
) -> dict[str, str]:
    return {
        "descriptor_name": "megadescriptor_l_384",
        "review_pair_id": f"pair_{index:03d}",
        "route_label": route,
        "evidence_admission_score": str(evidence),
        "descriptor_similarity_percentile": str(similarity),
        "review_ready_label": str(ready),
        "not_ready_or_uncertain_label": str(1 - ready),
        "same_identity_known_id": same_id,
    }


class StoryHardeningIssue5ReviewBudgetValueTests(unittest.TestCase):
    def test_pferi_priority_uses_route_and_evidence_before_similarity(self) -> None:
        rows = [
            row(1, "conflict_review", 0.95, 0.99, 0, "no"),
            row(2, "accept_review", 0.60, 0.50, 1, "yes"),
            row(3, "cautious_review", 0.90, 0.80, 1, "yes"),
        ]

        ordered = issue5.pferi_priority(rows)

        self.assertEqual([item["route_label"] for item in ordered], ["accept_review", "cautious_review", "conflict_review"])

    def test_descriptor_priority_uses_similarity_first(self) -> None:
        rows = [
            row(1, "accept_review", 0.99, 0.20, 1, "yes"),
            row(2, "conflict_review", 0.10, 0.95, 0, "no"),
        ]

        ordered = issue5.descriptor_priority(rows)

        self.assertEqual(ordered[0]["review_pair_id"], "pair_002")

    def test_budget_summary_reports_review_burden_and_same_id_retention(self) -> None:
        rows = [
            row(1, "accept_review", 0.9, 0.7, 1, "yes"),
            row(2, "conflict_review", 0.2, 0.95, 0, "no"),
            row(3, "cautious_review", 0.7, 0.8, 1, "yes"),
        ]

        summary = issue5.budget_summary("pooled", "pferi_priority", issue5.pferi_priority(rows), budget=2)

        self.assertEqual(summary["selected_count"], 2)
        self.assertEqual(summary["not_ready_or_uncertain_count"], 0)
        self.assertEqual(summary["same_id_retention"], 1.0)
        self.assertIn("review utility only", summary["claim_boundary"])
        self.assertIn("not identity accuracy", summary["claim_boundary"])

    def test_delta_rows_compare_same_scope_budget(self) -> None:
        rows = [
            row(1, "accept_review", 0.9, 0.6, 1, "yes"),
            row(2, "conflict_review", 0.2, 0.99, 0, "no"),
            row(3, "cautious_review", 0.8, 0.7, 1, "yes"),
            row(4, "defer_low_evidence", 0.1, 0.98, 0, "no"),
        ]
        budget_rows = []
        budget_rows.append(issue5.budget_summary("pooled", "pferi_priority", issue5.pferi_priority(rows), 2))
        budget_rows.append(issue5.budget_summary("pooled", "descriptor_priority", issue5.descriptor_priority(rows), 2))

        delta = issue5.build_delta_rows(budget_rows)[0]

        self.assertLess(delta["delta_not_ready_or_uncertain_rate"], 0)
        self.assertIn("review burden", delta["interpretation"])
        self.assertIn("not automated identity assignment", delta["claim_boundary"])

    def test_figure_writer_creates_svg(self) -> None:
        rows = [
            row(1, "accept_review", 0.9, 0.6, 1, "yes"),
            row(2, "conflict_review", 0.2, 0.99, 0, "no"),
            row(3, "cautious_review", 0.8, 0.7, 1, "yes"),
            row(4, "defer_low_evidence", 0.1, 0.98, 0, "no"),
        ]
        budget_rows = []
        for strategy, ordered in {
            "pferi_priority": issue5.pferi_priority(rows),
            "descriptor_priority": issue5.descriptor_priority(rows),
        }.items():
            budget_rows.append(issue5.budget_summary("pooled", strategy, ordered, 2))
            budget_rows.append(issue5.budget_summary("pooled", strategy, ordered, 4))

        issue5.write_figure(budget_rows)

        self.assertTrue(issue5.FIGURE_SVG.exists())
        text = issue5.FIGURE_SVG.read_text(encoding="utf-8")
        self.assertIn("<svg", text)
        self.assertIn("PF-ERI priority", text)
        self.assertIn("Descriptor priority", text)


if __name__ == "__main__":
    unittest.main()
