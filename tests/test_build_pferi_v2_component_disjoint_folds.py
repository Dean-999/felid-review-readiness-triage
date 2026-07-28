from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from scripts import build_pferi_v2_component_disjoint_folds as module


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "schemas/pferi_v2/component_disjoint_fold_design_v1.json"


class ComponentDisjointFoldTests(unittest.TestCase):
    def make_fixture(self, root: Path) -> tuple[Path, Path]:
        rows = []
        # Twenty components, each a three-edge path. This is large enough for
        # five outer folds and four inner folds without splitting an endpoint.
        for component in range(20):
            for edge in range(3):
                index = component * 3 + edge
                rows.append(
                    {
                        "canonical_pair_id": f"pair_{index:03d}",
                        "pair_execution_id": f"exec_{index:03d}",
                        "analytical_role": "development",
                        "endpoint_a_image_id": f"c{component:02d}_i{edge}",
                        "endpoint_b_image_id": f"c{component:02d}_i{edge + 1}",
                        "development_sampling_cell_id": f"cell_{index % 5}",
                        "descriptor_support_category": ["both", "megadescriptor_only", "dinov2_only"][index % 3],
                        "development_evidence_state": "failure" if index % 19 == 0 else "available",
                        "best_rank_band": ["rank_01_05", "rank_06_10", "rank_11_20"][index % 3],
                        "local_match_measurement_failure": index % 19 == 0,
                        "endpoint_quality_measurement_failure": index % 23 == 0,
                    }
                )
        master = pd.DataFrame(rows)
        formal = pd.DataFrame(
            {
                "formal_sampling_stage": "development",
                "canonical_pair_id": master["canonical_pair_id"],
                "pair_execution_id": master["pair_execution_id"],
                "source_analytical_role": "development",
                "first_order_inclusion_probability": np.linspace(0.1, 0.9, len(master)),
            }
        )
        master_path = root / "master.csv"
        formal_path = root / "formal.csv"
        master.to_csv(master_path, index=False)
        formal.to_csv(formal_path, index=False)
        return master_path, formal_path

    def test_registry_is_valid(self) -> None:
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(module.validate_registry(registry), [])

    def test_connected_components_preserve_transitive_endpoint_groups(self) -> None:
        frame = pd.DataFrame(
            {
                "canonical_pair_id": ["p1", "p2", "p3"],
                "endpoint_a_image_id": ["a", "b", "x"],
                "endpoint_b_image_id": ["b", "c", "y"],
            }
        )
        membership, inventory = module.connected_components(frame)
        self.assertEqual(membership.loc[0], membership.loc[1])
        self.assertNotEqual(membership.loc[0], membership.loc[2])
        self.assertEqual(sorted(inventory["pair_count"].tolist()), [1, 2])

    def test_builder_is_deterministic_and_has_zero_endpoint_leakage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            master_path, formal_path = self.make_fixture(root)
            frame = module.load_outcome_free_development(master_path, formal_path)
            registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
            first = module.build_nested_assignments(frame, registry)
            second = module.build_nested_assignments(frame, registry)
            self.assertTrue(first.outer.equals(second.outer))
            self.assertTrue(first.nested.equals(second.nested))
            issues, _ = module.validate_assignments(frame, first, registry)
            self.assertEqual(issues, [])

    def test_loader_rejects_outcome_bearing_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            master_path, formal_path = self.make_fixture(root)
            master = pd.read_csv(master_path)
            master["final_outcome"] = 1
            master.to_csv(master_path, index=False)
            with self.assertRaisesRegex(ValueError, "outcome-like"):
                module.load_outcome_free_development(master_path, formal_path)

    def test_end_to_end_run_writes_auditable_fold_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            master_path, formal_path = self.make_fixture(root)
            output = root / "folds"
            audit = module.run(
                master_path,
                formal_path,
                REGISTRY,
                output,
                expected_rows=60,
            )
            self.assertEqual(audit["status"], "PASS")
            self.assertEqual(audit["endpoint_leakage_count"], 0)
            self.assertEqual(audit["development_pair_count"], 60)
            self.assertEqual(audit["outer_assignment_row_count"], 60)
            self.assertEqual(audit["nested_assignment_row_count"], 240)
            self.assertEqual(audit["outcome_columns_read"], 0)
            self.assertTrue((output / "outer_fold_assignments.csv").exists())
            self.assertTrue((output / "nested_fold_assignments.csv").exists())
            self.assertTrue((output / "CHECKSUMS.sha256").exists())


if __name__ == "__main__":
    unittest.main()
