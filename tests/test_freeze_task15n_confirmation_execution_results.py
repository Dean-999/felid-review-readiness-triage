from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import freeze_task15n_confirmation_execution_results as task15n


class Task15NConfirmationExecutionFreezeTests(unittest.TestCase):
    def test_authoritative_source_passes_without_recalculation(self) -> None:
        contract = json.loads(task15n.CONTRACT.read_text(encoding="utf-8"))
        evidence = task15n.validate_source(task15n.SOURCE, contract)
        self.assertEqual(evidence["candidate_pair_count"], 889)
        self.assertEqual(evidence["supported_pair_count"], 252)
        self.assertEqual(evidence["unsupported_pair_count"], 637)
        self.assertEqual(evidence["prediction_count"], 504)
        self.assertEqual(evidence["quality_failure_counts"], {"none": 815})
        self.assertEqual(evidence["local_match_failure_counts"], {"none": 252})

    def test_contract_forbids_parameter_and_performance_recalculation(self) -> None:
        contract = json.loads(task15n.CONTRACT.read_text(encoding="utf-8"))
        prohibited = set(contract["prohibited_recalculations"])
        self.assertIn("Task15J coefficient estimation", prohibited)
        self.assertIn("Task15L calibration-parameter estimation", prohibited)
        self.assertIn("Brier or other outcome-performance analysis", prohibited)
        self.assertEqual(contract["accepted_status"], "PASS_TASK15M_EXECUTION_VALIDATION")


if __name__ == "__main__":
    unittest.main()
