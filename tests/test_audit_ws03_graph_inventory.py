from __future__ import annotations

import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ws03_graph_audit", ROOT / "scripts/audit_ws03_graph_inventory.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class GraphInventoryAuditTest(unittest.TestCase):
    def write_csv(self, path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def canonical_row(self, pair_id: str, a: str, b: str) -> dict[str, str]:
        return {
            "contract_version": "contract-v1",
            "canonical_pair_id": pair_id,
            "endpoint_a_image_id": a,
            "endpoint_b_image_id": b,
            "source_dataset": "test",
            "pair_availability_status": "available",
            "pair_inclusion_status": "eligible",
            "exclusion_reason": "",
        }

    def membership_row(self, pair_id: str, query: str, candidate: str, direction: str) -> dict[str, str]:
        return {
            "contract_version": "contract-v1",
            "canonical_pair_id": pair_id,
            "descriptor_name": "descriptor",
            "queue_name": "queue",
            "queue_snapshot_id": "snapshot",
            "query_image_id": query,
            "candidate_image_id": candidate,
            "candidate_rank": "1",
            "descriptor_similarity": "0.5",
            "membership_direction": direction,
        }

    def test_passes_and_writes_component_inventory_for_consistent_graph(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary = Path(temporary_directory)
            canonical = temporary / "canonical.csv"
            memberships = temporary / "memberships.csv"
            output = temporary / "output"
            self.write_csv(
                canonical,
                sorted(MODULE.CANONICAL_COLUMNS),
                [self.canonical_row("p1", "a", "b"), self.canonical_row("p2", "b", "c")],
            )
            self.write_csv(
                memberships,
                sorted(MODULE.MEMBERSHIP_COLUMNS),
                [
                    self.membership_row("p1", "a", "b", "a_to_b"),
                    self.membership_row("p2", "c", "b", "b_to_a"),
                ],
            )
            result = MODULE.audit(canonical, memberships, output)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["graph_structure"]["connected_component_count"], 1)
            self.assertEqual(result["graph_structure"]["image_node_count"], 3)
            self.assertTrue((output / "candidate_graph_component_structure.png").exists())
            self.assertEqual(json.loads((output / "graph_inventory_audit.json").read_text())["status"], "PASS")

    def test_fails_when_membership_orientation_is_inconsistent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary = Path(temporary_directory)
            canonical = temporary / "canonical.csv"
            memberships = temporary / "memberships.csv"
            self.write_csv(canonical, sorted(MODULE.CANONICAL_COLUMNS), [self.canonical_row("p1", "a", "b")])
            self.write_csv(
                memberships,
                sorted(MODULE.MEMBERSHIP_COLUMNS),
                [self.membership_row("p1", "b", "a", "a_to_b")],
            )
            result = MODULE.audit(canonical, memberships, temporary / "output")
            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(result["integrity_checks"]["membership_orientation_mismatch_count"], 1)


if __name__ == "__main__":
    unittest.main()
