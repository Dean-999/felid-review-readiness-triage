from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from scripts import validate_v2_automatic_pair_evidence_contract as contract


class V2AutomaticPairEvidenceContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = contract.load_json(contract.DEFAULT_CONTRACT_PATH)
        self.dictionary = contract.load_json(contract.DEFAULT_DICTIONARY_PATH)

    def test_checked_in_contract_passes(self) -> None:
        audit = contract.validate_contract(self.payload, self.dictionary)

        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(audit["primary_evidence_candidate_count"], 1)
        self.assertEqual(audit["diagnostic_only_count"], 1)

    def test_primary_evidence_is_symmetric_and_automatic(self) -> None:
        feature = self.payload["primary_evidence_candidates"][0]

        self.assertEqual(feature["symmetry_rule"], "order_invariant")
        self.assertEqual(feature["inference_time_availability"], "automatic")
        self.assertIn("failure_and_runtime_logged", feature["feasibility_requirements"])

    def test_rejects_descriptor_similarity_as_primary_evidence_input(self) -> None:
        payload = deepcopy(self.payload)
        feature = payload["primary_evidence_candidates"][0]
        feature["allowed_inputs"].append("descriptor_similarity")

        audit = contract.validate_contract(payload, self.dictionary)

        self.assertEqual(audit["status"], "FAIL")
        self.assertIn("forbidden_primary_input:local_match_coverage_fraction:descriptor_similarity", audit["error_codes"])

    def test_rejects_outcome_or_identity_input(self) -> None:
        payload = deepcopy(self.payload)
        feature = payload["primary_evidence_candidates"][0]
        feature["allowed_inputs"].append("identity_truth")

        audit = contract.validate_contract(payload, self.dictionary)

        self.assertEqual(audit["status"], "FAIL")
        self.assertIn("forbidden_primary_input:local_match_coverage_fraction:identity_truth", audit["error_codes"])

    def test_rejects_descriptor_disagreement_as_primary_evidence(self) -> None:
        payload = deepcopy(self.payload)
        payload["primary_evidence_candidates"][0]["feature_name"] = "descriptor_disagreement"

        audit = contract.validate_contract(payload, self.dictionary)

        self.assertEqual(audit["status"], "FAIL")
        self.assertIn("descriptor_derived_feature_cannot_be_primary:descriptor_disagreement", audit["error_codes"])

    def test_rejects_noncanonical_symmetry_rule(self) -> None:
        payload = deepcopy(self.payload)
        payload["primary_evidence_candidates"][0]["symmetry_rule"] = "query_to_candidate_only"

        audit = contract.validate_contract(payload, self.dictionary)

        self.assertEqual(audit["status"], "FAIL")
        self.assertIn("invalid_symmetry_rule:local_match_coverage_fraction", audit["error_codes"])

    def test_cli_writes_validation_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audit_path = Path(tmp) / "audit.json"
            exit_code = contract.main(["--audit-json", str(audit_path)])

            self.assertEqual(exit_code, 0)
            self.assertEqual(json.loads(audit_path.read_text(encoding="utf-8"))["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
