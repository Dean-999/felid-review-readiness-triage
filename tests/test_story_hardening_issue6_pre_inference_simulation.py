from __future__ import annotations

import unittest

from scripts import build_story_hardening_issue6_pre_inference_simulation as issue6


def row(index: int, route: str, ready: int, same: str, score: float = 0.8) -> dict[str, str]:
    return {
        "scope": "pooled",
        "descriptor_name": "megadescriptor_l_384",
        "review_pair_id": f"pair_{index:03d}",
        "queue_rank": str(index),
        "route_label": route,
        "simulation_decision": issue6.simulation_decision(route),
        "review_ready_label": str(ready),
        "not_ready_or_uncertain_label": str(1 - ready),
        "same_identity_known_id": same,
        "descriptor_similarity_percentile": "0.9",
        "evidence_admission_score": str(score),
        "evidence_risk_score": str(1 - score),
    }


class StoryHardeningIssue6PreInferenceSimulationTests(unittest.TestCase):
    def test_simulation_decision_maps_routes_to_pre_inference_states(self) -> None:
        self.assertEqual(issue6.simulation_decision("accept_review"), "admitted_pre_inference")
        self.assertEqual(issue6.simulation_decision("cautious_review"), "admitted_pre_inference")
        self.assertEqual(issue6.simulation_decision("conflict_review"), "deferred_pre_inference")
        self.assertEqual(issue6.simulation_decision("defer_low_evidence"), "deferred_pre_inference")

    def test_summary_reports_reviewability_and_same_id_coverage(self) -> None:
        rows = [
            row(1, "accept_review", 1, "yes"),
            row(2, "cautious_review", 1, "no"),
            row(3, "conflict_review", 0, "no"),
            row(4, "defer_low_evidence", 0, "yes"),
        ]
        admitted = [item for item in rows if item["simulation_decision"] == "admitted_pre_inference"]

        summary = issue6.summary_for_group("pooled", "admitted_pre_inference", admitted, rows)

        self.assertEqual(summary["pair_count"], 2)
        self.assertEqual(summary["review_ready_rate"], 1.0)
        self.assertEqual(summary["not_ready_or_uncertain_rate"], 0.0)
        self.assertEqual(summary["same_id_retention"], 0.5)
        self.assertIn("false-candidate burden is review burden", summary["claim_boundary"])

    def test_build_summary_rows_produces_admitted_and_deferred_for_each_scope(self) -> None:
        pair_rows = []
        for scope in issue6.SCOPES:
            for index, route_label in enumerate(["accept_review", "conflict_review"], start=1):
                item = row(index, route_label, 1 if route_label == "accept_review" else 0, "yes")
                item["scope"] = scope
                pair_rows.append(item)

        summaries = issue6.build_summary_rows(pair_rows)

        self.assertEqual(len(summaries), len(issue6.SCOPES) * 2)
        self.assertEqual({item["simulation_decision"] for item in summaries}, {"admitted_pre_inference", "deferred_pre_inference"})

    def test_report_boundary_blocks_identity_accuracy_claim(self) -> None:
        rows = [
            row(1, "accept_review", 1, "yes"),
            row(2, "conflict_review", 0, "no"),
        ]

        summary = issue6.summary_for_group("pooled", "deferred_pre_inference", [rows[1]], rows)

        self.assertIn("not identity accuracy", summary["claim_boundary"])
        self.assertNotIn("automatic identity", summary["interpretation"].lower())


if __name__ == "__main__":
    unittest.main()
