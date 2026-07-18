from __future__ import annotations

import csv
import ast
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD_SPEC = importlib.util.spec_from_file_location("timed_rehearsal_builder", ROOT / "scripts/build_v2_timed_operational_rehearsal.py")
assert BUILD_SPEC and BUILD_SPEC.loader
BUILD = importlib.util.module_from_spec(BUILD_SPEC)
BUILD_SPEC.loader.exec_module(BUILD)
AUDIT_SPEC = importlib.util.spec_from_file_location("timed_rehearsal_audit", ROOT / "scripts/audit_v2_timed_operational_rehearsal.py")
assert AUDIT_SPEC and AUDIT_SPEC.loader
AUDIT = importlib.util.module_from_spec(AUDIT_SPEC)
AUDIT_SPEC.loader.exec_module(AUDIT)


class TimedOperationalRehearsalTests(unittest.TestCase):
    def contract(self) -> dict[str, object]:
        return json.loads((ROOT / "schemas/pferi_v2/timed_operational_rehearsal_contract_v2.json").read_text())

    def test_selection_uses_only_included_available_pilot_pairs(self) -> None:
        pilot = [
            {"canonical_pair_id": "p1", "pilot_inclusion_status": "included", "pair_availability_status": "available"},
            {"canonical_pair_id": "p2", "pilot_inclusion_status": "excluded", "pair_availability_status": "available"},
            {"canonical_pair_id": "p3", "pilot_inclusion_status": "included", "pair_availability_status": "unavailable"},
        ]
        canonical = [{"canonical_pair_id": "p1"}, {"canonical_pair_id": "p2"}, {"canonical_pair_id": "p3"}]
        selected = BUILD.select_pilot_pairs(pilot, canonical, 1, "seed")
        self.assertEqual([row["canonical_pair_id"] for row in selected], ["p1"])

    def test_reviewer_app_is_parseable_and_has_no_semantic_response_field(self) -> None:
        ast.parse(BUILD.APP_SOURCE)
        for forbidden in ("review_decision", "reason_codes", "confidence", "optional_note"):
            self.assertNotIn(forbidden, BUILD.APP_SOURCE)

    def test_audit_is_pending_without_logs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "restricted").mkdir()
            (root / "reviewer_view").mkdir()
            (root / "operational_logs").mkdir()
            (root / "restricted" / "build_audit.json").write_text("{}")
            with (root / "restricted" / "participant_task_allocation.csv").open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=AUDIT.ALLOCATION_COLUMNS)
                writer.writeheader()
                writer.writerow({
                    "rehearsal_participant_id": "participant_001",
                    "rehearsal_packet_id": "rehearsal_packet_001",
                    "rehearsal_role": "first_pass_rehearsal",
                    "task_order": "1",
                })
            with (root / "reviewer_view" / "rehearsal_packet.csv").open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["rehearsal_packet_id"])
                writer.writeheader(); writer.writerow({"rehearsal_packet_id": "rehearsal_packet_001"})
            contract_path = root / "contract.json"; contract_path.write_text(json.dumps(self.contract()))
            result = AUDIT.audit_rehearsal(root, contract_path)
            self.assertEqual(result["status"], "PENDING_NO_OPERATIONAL_LOGS")

    def test_audit_rejects_a_semantic_log_column(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "restricted").mkdir(); (root / "reviewer_view").mkdir(); logs = root / "operational_logs"; logs.mkdir()
            (root / "restricted" / "build_audit.json").write_text("{}")
            with (root / "reviewer_view" / "rehearsal_packet.csv").open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["rehearsal_packet_id"])
                writer.writeheader(); writer.writerow({"rehearsal_packet_id": "rehearsal_packet_001"})
            with (logs / "R001.csv").open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=AUDIT.REQUIRED_COLUMNS + ["review_decision"])
                writer.writeheader()
            contract_path = root / "contract.json"; contract_path.write_text(json.dumps(self.contract()))
            result = AUDIT.audit_rehearsal(root, contract_path)
            self.assertEqual(result["status"], "FAIL")
            self.assertIn("header_mismatch:R001.csv", result["error_codes"])

    def test_selection_excludes_retired_rehearsal_pairs(self) -> None:
        pilot = [
            {"canonical_pair_id": "p1", "pilot_inclusion_status": "included", "pair_availability_status": "available"},
            {"canonical_pair_id": "p2", "pilot_inclusion_status": "included", "pair_availability_status": "available"},
        ]
        canonical = [{"canonical_pair_id": "p1"}, {"canonical_pair_id": "p2"}]
        selected = BUILD.select_pilot_pairs(pilot, canonical, 1, "seed", {"p1"})
        self.assertEqual([row["canonical_pair_id"] for row in selected], ["p2"])

    def test_audit_rejects_an_unassigned_operational_task(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "restricted").mkdir(); (root / "reviewer_view").mkdir(); logs = root / "operational_logs"; logs.mkdir()
            (root / "restricted" / "build_audit.json").write_text("{}")
            with (root / "reviewer_view" / "rehearsal_packet.csv").open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["rehearsal_packet_id"])
                writer.writeheader(); writer.writerow({"rehearsal_packet_id": "rehearsal_packet_001"})
            allocation_fields = ["rehearsal_participant_id", "rehearsal_packet_id", "rehearsal_role", "task_order"]
            with (root / "restricted" / "participant_task_allocation.csv").open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=allocation_fields)
                writer.writeheader(); writer.writerow({"rehearsal_participant_id": "assigned", "rehearsal_packet_id": "rehearsal_packet_001", "rehearsal_role": "first_pass_rehearsal", "task_order": "1"})
            with (logs / "unassigned.csv").open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=AUDIT.REQUIRED_COLUMNS)
                writer.writeheader(); writer.writerow({
                    "rehearsal_packet_id": "rehearsal_packet_001", "operational_response_id": "operation_001",
                    "rehearsal_participant_id": "unassigned", "rehearsal_role": "first_pass_rehearsal",
                    "task_started_at_utc": "2026-07-15T00:00:00+00:00", "task_submitted_at_utc": "2026-07-15T00:00:10+00:00",
                    "elapsed_seconds": "10", "completion_status": "completed", "technical_problem_category": "none",
                })
            contract_path = root / "contract.json"; contract_path.write_text(json.dumps(self.contract()))
            result = AUDIT.audit_rehearsal(root, contract_path)
            self.assertIn("unassigned_operational_task", result["error_codes"])

    def test_reviewer_app_requires_restricted_assignment_and_has_no_role_selector(self) -> None:
        self.assertIn("PF_ERI_V2_ASSIGNMENT_FILE", BUILD.APP_SOURCE)
        self.assertNotIn('selectbox("Assigned rehearsal role"', BUILD.APP_SOURCE)

    def test_default_v2_allocation_has_no_duplicate_participant_packet(self) -> None:
        packet_ids = [f"rehearsal_packet_{index:03d}" for index in range(1, 25)]
        allocation = BUILD.default_v2_allocation(packet_ids)
        participant_packet = {(row["rehearsal_participant_id"], row["rehearsal_packet_id"]) for row in allocation}
        self.assertEqual(len(allocation), len(participant_packet))
        self.assertEqual({row["rehearsal_participant_id"] for row in allocation}, set(BUILD.V2_PARTICIPANT_CODES))


if __name__ == "__main__":
    unittest.main()
