from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from scripts import validate_v2_measurement_feasibility_pilot_contract as contract


class V2MeasurementFeasibilityPilotContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = contract.load_json(contract.DEFAULT_CONTRACT_PATH)

    def test_checked_in_contract_passes(self) -> None:
        audit = contract.validate_contract(self.payload)

        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(audit["target_unique_pair_count"], 160)
        self.assertEqual(audit["gate_count"], 10)

    def test_contract_has_no_outcome_label_or_v1_reuse(self) -> None:
        text = json.dumps(self.payload).lower()

        self.assertNotIn("review_ready", text)
        self.assertNotIn("phase18", text)

    def test_rejects_outcome_field_in_pilot_manifest(self) -> None:
        payload = deepcopy(self.payload)
        payload["pilot_manifest_required_columns"].append("review_ready_label")

        audit = contract.validate_contract(payload)

        self.assertEqual(audit["status"], "FAIL")
        self.assertIn("forbidden_pilot_manifest_field:review_ready_label", audit["error_codes"])

    def test_rejects_adaptive_gate(self) -> None:
        payload = deepcopy(self.payload)
        payload["retention_gates"][0]["selection_rule"] = "choose after inspecting pilot results"

        audit = contract.validate_contract(payload)

        self.assertEqual(audit["status"], "FAIL")
        self.assertIn("adaptive_retention_gate:automatic_quality_valid_output_rate", audit["error_codes"])

    def test_rejects_nonunique_pair_unit(self) -> None:
        payload = deepcopy(self.payload)
        payload["unit_of_sampling"] = "directed_membership"

        audit = contract.validate_contract(payload)

        self.assertEqual(audit["status"], "FAIL")
        self.assertIn("invalid_sampling_unit", audit["error_codes"])

    def test_rejects_missing_required_gate(self) -> None:
        payload = deepcopy(self.payload)
        payload["retention_gates"] = payload["retention_gates"][:-1]

        audit = contract.validate_contract(payload)

        self.assertEqual(audit["status"], "FAIL")
        self.assertIn("missing_required_retention_gates", audit["error_codes"])

    def test_cli_writes_validation_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audit_path = Path(tmp) / "audit.json"
            exit_code = contract.main(["--audit-json", str(audit_path)])

            self.assertEqual(exit_code, 0)
            self.assertEqual(json.loads(audit_path.read_text(encoding="utf-8"))["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
