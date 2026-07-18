from __future__ import annotations

import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ws03_partition_feasibility", ROOT / "scripts/simulate_ws03_image_partition_feasibility.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def canonical(pair_id: str, left: str, right: str) -> dict[str, str]:
    return {
        "canonical_pair_id": pair_id,
        "endpoint_a_image_id": left,
        "endpoint_b_image_id": right,
        "pair_availability_status": "available",
        "pair_inclusion_status": "eligible",
    }


def membership(pair_id: str, descriptor: str) -> dict[str, str]:
    return {"canonical_pair_id": pair_id, "descriptor_name": descriptor}


class ImagePartitionFeasibilityTests(unittest.TestCase):
    def write_csv(self, path: Path, rows: list[dict[str, str]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def config(self) -> dict[str, object]:
        return {
            "scenario_version": MODULE.SCENARIO_VERSION,
            "binding_status": "nonbinding_feasibility_stress_test",
            "seeds": [1, 2, 3],
            "nonbinding_capacity_stress_benchmarks": {
                "minimum_unique_canonical_pairs_per_active_role": 1,
                "minimum_descriptor_covered_canonical_pairs_per_active_role": 1,
            },
            "scenarios": [
                {
                    "scenario_id": "equal",
                    "description": "synthetic equal stress scenario",
                    "image_role_shares": {"development": 1 / 3, "calibration": 1 / 3, "confirmation": 1 / 3},
                }
            ],
        }

    def test_deterministic_simulation_accounts_for_every_pair(self) -> None:
        rows = [
            canonical("p1", "a", "b"),
            canonical("p2", "c", "d"),
            canonical("p3", "e", "f"),
            canonical("p4", "a", "c"),
            canonical("p5", "b", "e"),
            canonical("p6", "d", "f"),
        ]
        descriptors = {row["canonical_pair_id"]: {"mega", "dino"} for row in rows}
        first = MODULE.simulate_once(rows, descriptors, list("abcdef"), self.config()["scenarios"][0], 1, self.config()["nonbinding_capacity_stress_benchmarks"])
        second = MODULE.simulate_once(rows, descriptors, list("abcdef"), self.config()["scenarios"][0], 1, self.config()["nonbinding_capacity_stress_benchmarks"])
        self.assertEqual(first, second)
        retained = sum(first[f"{role}_canonical_pair_count"] for role in MODULE.ACTIVE_ROLES)
        self.assertEqual(retained + first["cross_role_pair_count"], len(rows))

    def test_run_writes_only_summary_artifacts_and_not_an_actual_split(self) -> None:
        canonical_rows = [
            canonical("p1", "a", "b"),
            canonical("p2", "c", "d"),
            canonical("p3", "e", "f"),
            canonical("p4", "a", "c"),
            canonical("p5", "b", "e"),
            canonical("p6", "d", "f"),
            canonical("p7", "a", "d"),
            canonical("p8", "b", "f"),
            canonical("p9", "c", "e"),
        ]
        membership_rows = [
            membership(row["canonical_pair_id"], descriptor)
            for row in canonical_rows
            for descriptor in ("mega", "dino")
        ]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            canonical_path = root / "canonical.csv"
            membership_path = root / "membership.csv"
            config_path = root / "scenario.json"
            output_dir = root / "out"
            self.write_csv(canonical_path, canonical_rows)
            self.write_csv(membership_path, membership_rows)
            config_path.write_text(json.dumps(self.config()), encoding="utf-8")
            audit = MODULE.run_simulation(canonical_path, membership_path, config_path, output_dir)
            self.assertEqual(audit["binding_status"], "nonbinding_feasibility_stress_test")
            self.assertTrue((output_dir / "nonbinding_partition_feasibility_audit.json").exists())
            self.assertTrue((output_dir / "nonbinding_partition_feasibility_runs.csv").exists())
            self.assertTrue((output_dir / "nonbinding_partition_feasibility_summary.csv").exists())
            self.assertFalse(any("partition_images" in path.name or "partition_pairs" in path.name for path in output_dir.iterdir()))

    def test_rejects_a_binding_or_malformed_scenario_config(self) -> None:
        invalid = self.config()
        invalid["binding_status"] = "official_split"
        with self.assertRaises(ValueError):
            MODULE.validate_scenarios(invalid)
        invalid = self.config()
        invalid["scenarios"][0]["image_role_shares"]["confirmation"] = 0.5
        with self.assertRaises(ValueError):
            MODULE.validate_scenarios(invalid)


if __name__ == "__main__":
    unittest.main()
