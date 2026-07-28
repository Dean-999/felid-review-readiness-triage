import importlib.util
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "plan_v2_formal_reviewer_assignments.py"


def load_module():
    spec = importlib.util.spec_from_file_location("plan_v2_formal_reviewer_assignments", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def pairs(count=2224):
    return [
        {
            "canonical_pair_id": f"pair_{index:04d}",
            "endpoint_a_image_id": f"image_{index:04d}_a",
            "endpoint_b_image_id": f"image_{index:04d}_b",
            "formal_sampling_stage": "development",
        }
        for index in range(count)
    ]


def four_stage_pairs():
    rows = []
    start = 0
    for stage, count in (
        ("development", 445),
        ("calibration", 445),
        ("deployment_confirmation", 889),
        ("mechanism_confirmation", 445),
    ):
        for index in range(start, start + count):
            rows.append(
                {
                    "canonical_pair_id": f"pair_{index:04d}",
                    "endpoint_a_image_id": f"image_{index:04d}_a",
                    "endpoint_b_image_id": f"image_{index:04d}_b",
                    "formal_sampling_stage": stage,
                }
            )
        start += count
    return rows


class ReviewerAssignmentPlanningTests(unittest.TestCase):
    def test_workload_scenario_reports_exact_arithmetic_bounds(self):
        module = load_module()
        self.assertEqual(
            module.workload_scenario(pair_count=2224, reviewer_count=8),
            {
                "distinct_reviewer_count": 8,
                "formal_pair_count": 2224,
                "first_pass_decision_count": 4448,
                "minimum_first_pass_tasks_per_reviewer": 556,
                "maximum_first_pass_tasks_per_reviewer": 556,
                "eligible_adjudicators_per_pair": 6,
                "adjudication_task_count": "unknown_until_first_pass_disagreement_audit",
            },
        )

    def test_four_reviewers_receive_exactly_1112_first_pass_tasks_each(self):
        module = load_module()
        codes = module.opaque_reviewer_codes(4, "00" * 32)
        assignments, eligibility = module.plan_assignments(pairs(), codes, "00" * 32)
        loads = Counter(row["reviewer_code"] for row in assignments)
        self.assertEqual(set(loads.values()), {1112})
        self.assertEqual(len(assignments), 4448)
        self.assertEqual(len(eligibility), 2224)

    def test_four_reviewer_plan_is_balanced_within_every_sampling_stage(self):
        module = load_module()
        codes = module.opaque_reviewer_codes(4, "55" * 32)
        assignments, _ = module.plan_assignments(four_stage_pairs(), codes, "55" * 32)
        for stage in ("development", "calibration", "deployment_confirmation", "mechanism_confirmation"):
            loads = Counter(
                row["reviewer_code"] for row in assignments if row["formal_sampling_stage"] == stage
            )
            self.assertLessEqual(max(loads.values()) - min(loads.values()), 1, (stage, loads))

    def test_four_reviewer_pairings_are_balanced_globally_and_within_stage(self):
        module = load_module()
        codes = module.opaque_reviewer_codes(4, "66" * 32)
        assignments, _ = module.plan_assignments(four_stage_pairs(), codes, "66" * 32)
        pair_edges = {}
        pair_stages = {}
        for row in assignments:
            pair_edges.setdefault(row["canonical_pair_id"], set()).add(row["reviewer_code"])
            pair_stages[row["canonical_pair_id"]] = row["formal_sampling_stage"]
        global_edges = Counter(tuple(sorted(edge)) for edge in pair_edges.values())
        self.assertLessEqual(max(global_edges.values()) - min(global_edges.values()), 1, global_edges)
        for stage in ("development", "calibration", "deployment_confirmation", "mechanism_confirmation"):
            stage_edges = Counter(
                tuple(sorted(pair_edges[pair_id]))
                for pair_id, pair_stage in pair_stages.items()
                if pair_stage == stage
            )
            self.assertLessEqual(max(stage_edges.values()) - min(stage_edges.values()), 1, (stage, stage_edges))

    def test_every_pair_has_two_distinct_reviewers_and_excludes_them_from_adjudication(self):
        module = load_module()
        codes = module.opaque_reviewer_codes(5, "11" * 32)
        assignments, eligibility = module.plan_assignments(pairs(31), codes, "11" * 32)
        by_pair = {}
        for row in assignments:
            by_pair.setdefault(row["canonical_pair_id"], []).append(row["reviewer_code"])
        eligible_by_pair = {row["canonical_pair_id"]: row["eligible_adjudicator_codes"].split(";") for row in eligibility}
        for pair_id, reviewers in by_pair.items():
            self.assertEqual(len(reviewers), 2)
            self.assertEqual(len(set(reviewers)), 2)
            self.assertTrue(set(reviewers).isdisjoint(eligible_by_pair[pair_id]))
            self.assertEqual(len(eligible_by_pair[pair_id]), 3)

    def test_assignment_is_input_order_invariant(self):
        module = load_module()
        codes = module.opaque_reviewer_codes(4, "22" * 32)
        first, _ = module.plan_assignments(pairs(50), codes, "22" * 32)
        second, _ = module.plan_assignments(list(reversed(pairs(50))), codes, "22" * 32)
        key = lambda row: (row["canonical_pair_id"], row["reviewer_code"], row["review_packet_id"])
        self.assertEqual(sorted(map(key, first)), sorted(map(key, second)))

    def test_reviewer_visible_rows_have_exact_blinded_allowlist(self):
        module = load_module()
        codes = module.opaque_reviewer_codes(3, "33" * 32)
        assignments, _ = module.plan_assignments(pairs(3), codes, "33" * 32)
        visible = module.reviewer_visible_row(assignments[0])
        self.assertEqual(list(visible), module.REVIEWER_PACKET_COLUMNS)
        text = "|".join(visible.values()).lower()
        for forbidden in ("canonical", "image_", "development", "descriptor", "rank", "failure"):
            self.assertNotIn(forbidden, text)

    def test_fewer_than_three_reviewers_is_rejected(self):
        module = load_module()
        with self.assertRaisesRegex(ValueError, "at least three"):
            module.plan_assignments(pairs(2), ["rv_a", "rv_b"], "44" * 32)


if __name__ == "__main__":
    unittest.main()
