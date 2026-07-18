from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from scripts import validate_v2_independent_quality_control_contract as contract


class V2IndependentQualityControlContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = contract.load_json(contract.DEFAULT_CONTRACT_PATH)
        self.dictionary = contract.load_json(contract.DEFAULT_DICTIONARY_PATH)

    def test_checked_in_contract_passes(self) -> None:
        audit = contract.validate_contract(self.payload, self.dictionary)

        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(audit["control_count"], 4)
        self.assertEqual(audit["context_only_count"], 1)

    def test_controls_are_raw_image_measurements_with_fixed_pair_aggregation(self) -> None:
        for control in self.payload["quality_controls"]:
            self.assertEqual(control["source_entity_level"], "image")
            self.assertIn(control["pair_aggregation"], {"minimum", "maximum"})
            self.assertEqual(control["role"], "independent_quality_control_candidate")

    def test_rejects_descriptor_input(self) -> None:
        payload = deepcopy(self.payload)
        payload["quality_controls"][0]["allowed_inputs"].append("descriptor_similarity")

        audit = contract.validate_contract(payload, self.dictionary)

        self.assertEqual(audit["status"], "FAIL")
        self.assertIn("forbidden_input:pair_min_animal_coverage_fraction:descriptor_similarity", audit["error_codes"])

    def test_rejects_oracle_feature_as_quality_control(self) -> None:
        payload = deepcopy(self.payload)
        payload["quality_controls"][0]["raw_feature_name"] = "occlusion_fraction"

        audit = contract.validate_contract(payload, self.dictionary)

        self.assertEqual(audit["status"], "FAIL")
        self.assertIn("quality_control_not_automatic:pair_min_animal_coverage_fraction", audit["error_codes"])

    def test_rejects_pair_evidence_feature_in_active_control(self) -> None:
        payload = deepcopy(self.payload)
        payload["quality_controls"][0]["raw_feature_name"] = "local_match_coverage_fraction"

        audit = contract.validate_contract(payload, self.dictionary)

        self.assertEqual(audit["status"], "FAIL")
        self.assertIn("quality_control_not_image_level:pair_min_animal_coverage_fraction", audit["error_codes"])

    def test_rejects_context_feature_as_primary_control(self) -> None:
        payload = deepcopy(self.payload)
        payload["quality_controls"][0]["raw_feature_name"] = "infrared_likelihood"

        audit = contract.validate_contract(payload, self.dictionary)

        self.assertEqual(audit["status"], "FAIL")
        self.assertIn("quality_control_is_context_only:pair_min_animal_coverage_fraction", audit["error_codes"])

    def test_cli_writes_validation_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audit_path = Path(tmp) / "audit.json"
            exit_code = contract.main(["--audit-json", str(audit_path)])

            self.assertEqual(exit_code, 0)
            self.assertEqual(json.loads(audit_path.read_text(encoding="utf-8"))["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
