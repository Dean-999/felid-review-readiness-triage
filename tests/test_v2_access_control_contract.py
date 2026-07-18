from __future__ import annotations

import copy
import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts import validate_v2_access_control_contract as contract


class AccessControlContractTests(unittest.TestCase):
    def test_checked_in_contract_matches_executable_specification(self) -> None:
        path = Path(__file__).resolve().parents[1] / "schemas/pferi_v2/access_control_and_leak_response_contract_v1.json"
        checked_in = json.loads(path.read_text(encoding="utf-8"))
        audit, issues = contract.validate_contract(checked_in)
        self.assertEqual(checked_in, contract.build_contract_schema())
        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(issues, [])

    def test_rejects_outcome_access_for_packet_builder(self) -> None:
        invalid = copy.deepcopy(contract.build_contract_schema())
        invalid["access_matrix"]["packet_builder"]["read"].append("development_outcome_table")
        audit, issues = contract.validate_contract(invalid)
        self.assertEqual(audit["status"], "FAIL")
        self.assertIn("forbidden_outcome_access", {issue["code"] for issue in issues})

    def test_rejects_reviewer_access_to_restricted_linkage(self) -> None:
        invalid = copy.deepcopy(contract.build_contract_schema())
        invalid["access_matrix"]["first_pass_reviewer"]["read"].append("restricted_packet_linkage")
        audit, issues = contract.validate_contract(invalid)
        self.assertEqual(audit["status"], "FAIL")
        self.assertIn("reviewer_boundary_violation", {issue["code"] for issue in issues})

    def test_rejects_confirmation_role_that_can_rewrite_calibration_policy(self) -> None:
        invalid = copy.deepcopy(contract.build_contract_schema())
        invalid["access_matrix"]["confirmation_analyst"]["write"].append("calibration_policy_artifacts")
        audit, issues = contract.validate_contract(invalid)
        self.assertEqual(audit["status"], "FAIL")
        self.assertIn("confirmation_mutability_violation", {issue["code"] for issue in issues})

    def test_rejects_calibration_access_to_confirmation_feature_table(self) -> None:
        invalid = copy.deepcopy(contract.build_contract_schema())
        invalid["access_matrix"]["calibration_analyst"]["read"].append("confirmation_feature_table")
        audit, issues = contract.validate_contract(invalid)
        self.assertEqual(audit["status"], "FAIL")
        self.assertIn("cross_partition_feature_access", {issue["code"] for issue in issues})

    def test_cli_writes_audit_issue_table_and_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            input_contract = root / "contract.json"
            audit_json = root / "audit.json"
            issues_csv = root / "issues.csv"
            written_schema = root / "schema.json"
            input_contract.write_text(json.dumps(contract.build_contract_schema()), encoding="utf-8")
            exit_code = contract.main(
                [
                    "--contract",
                    str(input_contract),
                    "--audit-json",
                    str(audit_json),
                    "--issue-csv",
                    str(issues_csv),
                    "--write-schema",
                    str(written_schema),
                ]
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(json.loads(audit_json.read_text(encoding="utf-8"))["status"], "PASS")
            self.assertEqual(json.loads(written_schema.read_text(encoding="utf-8")), contract.build_contract_schema())
            with issues_csv.open(encoding="utf-8", newline="") as handle:
                self.assertEqual(csv.DictReader(handle).fieldnames, list(contract.ISSUE_FIELDS))


if __name__ == "__main__":
    unittest.main()
