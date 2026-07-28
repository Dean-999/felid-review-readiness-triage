from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "task15i_freeze", ROOT / "scripts/freeze_task15i_human_review_development_results.py"
)
assert SPEC and SPEC.loader
freeze_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(freeze_module)


class Task15IHumanReviewResultFreezeTests(unittest.TestCase):
    def test_verified_v2_analysis_meets_the_frozen_result_conditions(self) -> None:
        result = freeze_module.validate_analysis(freeze_module.ANALYSIS)
        self.assertEqual(result["report"]["status"], "PASS_TASK15I_DEVELOPMENT_SCREEN")
        self.assertEqual(len(result["folds"]), 5)
        self.assertTrue((result["folds"]["delta_brier_P3_minus_P5"] >= 0).all())
        self.assertEqual(len(result["labels"]), 1600)


if __name__ == "__main__":
    unittest.main()
