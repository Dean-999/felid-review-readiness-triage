from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from scripts import validate_v2_blinded_outcome_export_contract as contract


class V2BlindedOutcomeExportContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = contract.load_json(contract.DEFAULT_CONTRACT_PATH)

    def test_checked_in_contract_passes(self) -> None:
        audit = contract.validate_contract(self.payload)

        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(audit["packet_allowlist_count"], 5)
        self.assertEqual(audit["raw_response_allowlist_count"], 8)

    def test_packet_has_no_identity_or_feature_linkage_field(self) -> None:
        fields = set(self.payload["reviewer_packet_allowlist"])

        self.assertNotIn("canonical_pair_id", fields)
        self.assertNotIn("descriptor_similarity", fields)
        self.assertNotIn("same_identity_known_id", fields)

    def test_rejects_rank_in_reviewer_packet(self) -> None:
        payload = deepcopy(self.payload)
        payload["reviewer_packet_allowlist"].append("candidate_rank")

        audit = contract.validate_contract(payload)

        self.assertEqual(audit["status"], "FAIL")
        self.assertIn("forbidden_packet_field:candidate_rank", audit["error_codes"])

    def test_rejects_feature_value_in_reviewer_packet(self) -> None:
        payload = deepcopy(self.payload)
        payload["reviewer_packet_allowlist"].append("local_match_coverage_fraction")

        audit = contract.validate_contract(payload)

        self.assertEqual(audit["status"], "FAIL")
        self.assertIn("forbidden_packet_field:local_match_coverage_fraction", audit["error_codes"])

    def test_rejects_derived_label_from_raw_response_export(self) -> None:
        payload = deepcopy(self.payload)
        payload["raw_response_allowlist"].append("derived_majority_label")

        audit = contract.validate_contract(payload)

        self.assertEqual(audit["status"], "FAIL")
        self.assertIn("forbidden_raw_response_field:derived_majority_label", audit["error_codes"])

    def test_rejects_unmasked_filename_rule(self) -> None:
        payload = deepcopy(self.payload)
        payload["rendered_asset_rule"] = "source filename may be displayed"

        audit = contract.validate_contract(payload)

        self.assertEqual(audit["status"], "FAIL")
        self.assertIn("invalid_rendered_asset_rule", audit["error_codes"])

    def test_cli_writes_validation_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audit_path = Path(tmp) / "audit.json"
            exit_code = contract.main(["--audit-json", str(audit_path)])

            self.assertEqual(exit_code, 0)
            self.assertEqual(json.loads(audit_path.read_text(encoding="utf-8"))["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
