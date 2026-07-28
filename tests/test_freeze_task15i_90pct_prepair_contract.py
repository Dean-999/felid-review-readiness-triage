from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("task15i_contract", ROOT / "scripts/freeze_task15i_90pct_prepair_contract.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class Task15IPrepairContractTests(unittest.TestCase):
    def test_fold_inputs_are_outcome_free_and_complete(self) -> None:
        pairs = [{"candidate_pair_id": "p1", "endpoint_a_candidate_image_id": "a", "endpoint_b_candidate_image_id": "b", "descriptor_support_category": "dual_descriptor_reciprocal", "best_rank_band": "top_5", "development_evidence_state": "outcome_unopened", "endpoint_quality_measurement_failure": "none", "local_match_measurement_failure": "none"}]
        master, formal = MODULE.build_fold_inputs(pairs)
        self.assertEqual(master[0]["canonical_pair_id"], "p1")
        self.assertEqual(formal[0]["first_order_inclusion_probability"], "1.0")
        self.assertFalse(any("label" in column.lower() for column in master[0]))


if __name__ == "__main__":
    unittest.main()
