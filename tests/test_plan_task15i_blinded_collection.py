from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("task15i_blind_plan", ROOT / "scripts/plan_task15i_blinded_collection.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class Task15IBlindedCollectionTests(unittest.TestCase):
    def test_planning_key_is_stable_and_private_to_administrator_plan(self) -> None:
        first = MODULE.planner.opaque_reviewer_codes(4, MODULE.PLANNING_KEY)
        second = MODULE.planner.opaque_reviewer_codes(4, MODULE.PLANNING_KEY)
        self.assertEqual(first, second)
        self.assertEqual(len(set(first)), 4)


if __name__ == "__main__":
    unittest.main()
