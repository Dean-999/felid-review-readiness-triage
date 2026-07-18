from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from scripts import validate_v2_local_match_execution_contract as contract


class V2LocalMatchExecutionContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = contract.load_json(contract.DEFAULT_CONTRACT_PATH)

    def test_checked_in_contract_passes(self) -> None:
        self.assertEqual(contract.validate_contract(self.payload)["status"], "PASS")

    def test_rejects_nonminimum_symmetric_aggregation(self) -> None:
        payload = deepcopy(self.payload)
        payload["canonical_aggregation"]["rule"] = "mean"
        self.assertIn("invalid_canonical_aggregation", contract.validate_contract(payload)["error_codes"])

    def test_rejects_missing_forbidden_descriptor_input(self) -> None:
        payload = deepcopy(self.payload)
        payload["prohibited_inputs"].remove("descriptor_similarity")
        self.assertIn("missing_prohibited_input:descriptor_similarity", contract.validate_contract(payload)["error_codes"])

    def test_cli_writes_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "audit.json"
            self.assertEqual(contract.main(["--audit-json", str(output)]), 0)
            self.assertEqual(json.loads(output.read_text())["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
