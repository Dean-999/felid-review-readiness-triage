from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts import finalize_v2_adjudication_outcomes as finalizer
from scripts import build_v2_formal_reviewer_packages as formal


class FinalizeV2AdjudicationOutcomesTests(unittest.TestCase):
    def write_csv(self, path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def make_inputs(self, root: Path) -> dict[str, Path]:
        assignments = []
        responses = {"reviewer_A": [], "reviewer_B": []}
        pairs = [
            ("pair_agree", "development", "review_ready", "review_ready"),
            ("pair_disagree", "deployment_confirmation", "review_ready", "uncertain"),
        ]
        for index, (pair_id, stage, left_decision, right_decision) in enumerate(pairs):
            for alias, decision in (("reviewer_A", left_decision), ("reviewer_B", right_decision)):
                packet_id = f"task_{pair_id}_{alias}"
                peer = "reviewer_B" if alias == "reviewer_A" else "reviewer_A"
                assignments.append(
                    {
                        "assignment_contract_version": "contract_v1",
                        "review_packet_id": packet_id,
                        "canonical_pair_id": pair_id,
                        "formal_sampling_stage": stage,
                        "reviewer_assignment_id": f"assignment_{pair_id}_{alias}",
                        "reviewer_code": alias,
                        "peer_reviewer_code": peer,
                        "eligible_adjudicator_codes": "adjudicator_A",
                        "left_image_id": f"image_{index}_left",
                        "right_image_id": f"image_{index}_right",
                        "left_asset_token": f"asset_{index}_left",
                        "right_asset_token": f"asset_{index}_right",
                        "packet_batch_id": "batch_v1",
                        "assignment_status": "assigned",
                    }
                )
                reason = "none_review_ready" if decision == "review_ready" else "non_comparable"
                responses[alias].append(
                    {
                        "review_packet_id": packet_id,
                        "raw_reviewer_response_id": f"response_{pair_id}_{alias}",
                        "review_decision": decision,
                        "reason_codes": reason,
                        "confidence": "medium",
                        "optional_note": "",
                        "submitted_at_utc": "untrusted-time",
                        "technical_problem_flag": "no",
                    }
                )

        assignment_path = root / "assignment.csv"
        first_pass_dir = root / "first_pass"
        self.write_csv(assignment_path, formal.ASSIGNMENT_COLUMNS, assignments)
        for alias, rows in responses.items():
            self.write_csv(first_pass_dir / alias / "raw_responses.csv", formal.RAW_RESPONSE_COLUMNS, rows)

        linkage_fields = [
            "adjudication_packet_id", "canonical_pair_id", "left_image_id", "right_image_id",
            "adjudicator_alias", "formal_sampling_stage", "first_pass_reviewer_codes",
            "first_pass_packet_ids",
        ]
        linkage_path = root / "adjudication_linkage.csv"
        self.write_csv(
            linkage_path,
            linkage_fields,
            [
                {
                    "adjudication_packet_id": "adjudication_task_1",
                    "canonical_pair_id": "pair_disagree",
                    "left_image_id": "image_1_left",
                    "right_image_id": "image_1_right",
                    "adjudicator_alias": "adjudicator_A",
                    "formal_sampling_stage": "deployment_confirmation",
                    "first_pass_reviewer_codes": "reviewer_A;reviewer_B",
                    "first_pass_packet_ids": "task_pair_disagree_reviewer_A;task_pair_disagree_reviewer_B",
                }
            ],
        )
        adjudication_dir = root / "adjudication"
        self.write_csv(
            adjudication_dir / "anything" / "raw_responses.csv",
            formal.RAW_RESPONSE_COLUMNS,
            [
                {
                    "review_packet_id": "adjudication_task_1",
                    "raw_reviewer_response_id": "adjudication_response_1",
                    "review_decision": "not_review_ready",
                    "reason_codes": "low_evidence",
                    "confidence": "high",
                    "optional_note": "",
                    "submitted_at_utc": "also-untrusted",
                    "technical_problem_flag": "no",
                }
            ],
        )

        sampling_fields = [
            "formal_sampling_stage", "canonical_pair_id", "endpoint_a_image_id", "endpoint_b_image_id",
            "sampling_cell_id", "first_order_inclusion_probability",
        ]
        sampling_path = root / "sampling.csv"
        self.write_csv(
            sampling_path,
            sampling_fields,
            [
                {
                    "formal_sampling_stage": stage,
                    "canonical_pair_id": pair_id,
                    "endpoint_a_image_id": f"image_{index}_left",
                    "endpoint_b_image_id": f"image_{index}_right",
                    "sampling_cell_id": f"cell_{index}",
                    "first_order_inclusion_probability": "0.5",
                }
                for index, (pair_id, stage, _, _) in enumerate(pairs)
            ],
        )
        return {
            "assignment": assignment_path,
            "first_pass": first_pass_dir,
            "linkage": linkage_path,
            "adjudication": adjudication_dir,
            "sampling": sampling_path,
        }

    def test_builds_final_labels_and_excludes_time_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inputs = self.make_inputs(root)
            output = root / "output"
            audit = finalizer.finalize(output_dir=output, **inputs)

            self.assertEqual(audit["status"], "PASS")
            self.assertTrue(audit["formal_outcome_use_authorized"])
            self.assertEqual(audit["final_label_counts"], {"not_review_ready": 1, "review_ready": 1})

            with (output / "final_adjudicated_outcomes.csv").open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
                fields = handle.seek(0) or next(csv.reader(handle))
            self.assertEqual(len(rows), 2)
            self.assertNotIn("submitted_at_utc", fields)
            by_pair = {row["canonical_pair_id"]: row for row in rows}
            self.assertEqual(by_pair["pair_agree"]["final_label_source"], "first_pass_exact_agreement")
            self.assertEqual(by_pair["pair_disagree"]["final_three_category_label"], "not_review_ready")
            self.assertEqual(by_pair["pair_disagree"]["review_ready_label"], "0")

            disposition = json.loads((output / "adjudication_acceptance_disposition.json").read_text())
            self.assertEqual(disposition["status"], "PASS_OWNER_ACCEPTED_HUMAN_ADJUDICATION")
            self.assertEqual(disposition["collection_interface_requirement"], "nonbinding")

    def test_rejects_missing_adjudication(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inputs = self.make_inputs(root)
            (inputs["adjudication"] / "anything" / "raw_responses.csv").unlink()
            with self.assertRaisesRegex(ValueError, "adjudication returns do not exactly cover disagreements"):
                finalizer.finalize(output_dir=root / "output", **inputs)

    def test_rejects_invalid_decision_reason_combination(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inputs = self.make_inputs(root)
            response_path = inputs["adjudication"] / "anything" / "raw_responses.csv"
            with response_path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            rows[0]["reason_codes"] = "none_review_ready"
            self.write_csv(response_path, formal.RAW_RESPONSE_COLUMNS, rows)
            with self.assertRaisesRegex(ValueError, "invalid reason combination"):
                finalizer.finalize(output_dir=root / "output", **inputs)


if __name__ == "__main__":
    unittest.main()
