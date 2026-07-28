from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import freeze_task16_final_claim_matrix as task16


class Task16FinalClaimMatrixTests(unittest.TestCase):
    def test_sources_support_only_bounded_claims(self) -> None:
        contract = json.loads(task16.CONTRACT.read_text(encoding="utf-8"))
        evidence = task16.validate_sources(contract)
        self.assertEqual(evidence["development_pair_count"], 1600)
        self.assertEqual(evidence["calibration_pair_count"], 448)
        self.assertEqual(evidence["execution_candidate_pair_count"], 889)
        self.assertEqual(evidence["execution_supported_pair_count"], 252)
        self.assertFalse(evidence["confirmation_outcomes_accessed"])
        self.assertFalse(evidence["outcome_performance_analysis_performed"])

    def test_external_performance_and_identity_claims_are_blocked(self) -> None:
        contract = json.loads(task16.CONTRACT.read_text(encoding="utf-8"))
        dispositions = {claim["claim_id"]: claim["disposition"] for claim in contract["claims"]}
        self.assertEqual(dispositions["C06_EXTERNAL_P5_SUPERIORITY"], "NOT_ESTABLISHED")
        self.assertEqual(dispositions["C07_IDENTITY_ACCURACY"], "PROHIBITED")
        self.assertEqual(dispositions["C08_DEPLOYMENT_UTILITY"], "NOT_ESTABLISHED")
        self.assertEqual(dispositions["C09_PROJECT_COMPLETION"], "NOT_ESTABLISHED")
        self.assertEqual(contract["workstream_exit_decision"], "DEFERRED_PENDING_AUTHORIZED_CONFIRMATION_OUTCOME_ANALYSIS")


if __name__ == "__main__":
    unittest.main()
