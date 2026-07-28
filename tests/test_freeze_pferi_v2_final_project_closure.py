from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import freeze_pferi_v2_final_project_closure as closure


class FinalProjectClosureTests(unittest.TestCase):
    def test_owner_defined_acceptance_gate_passes(self) -> None:
        contract = json.loads(closure.CONTRACT.read_text(encoding="utf-8"))
        evidence = closure.validate_closure_basis(contract)
        self.assertEqual(evidence["task15n_status"], "PASS_TASK15M_EXECUTION_VALIDATION")
        self.assertEqual(evidence["run_audit_status"], "PASS")
        self.assertEqual(evidence["validation_audit_status"], "PASS")
        self.assertEqual(evidence["validation_failures"], [])
        self.assertFalse(evidence["separate_outcome_analysis_is_closure_basis"])

    def test_contract_closes_task_chain(self) -> None:
        contract = json.loads(closure.CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(contract["final_status"], "CONFIRMED")
        self.assertEqual(contract["project_status"], "CLOSED")
        self.assertTrue(contract["task_chain_closed"])
        self.assertIsNone(contract["next_task"])
        self.assertTrue(contract["no_further_analysis_required_for_closure"])


if __name__ == "__main__":
    unittest.main()
