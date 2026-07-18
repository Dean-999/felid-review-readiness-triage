from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from scripts import validate_v2_reviewer_interface_human_audit as validator


class V2ReviewerInterfaceHumanAuditTests(unittest.TestCase):
    def write_checklist(self, path: Path, rows: list[dict[str, str]]) -> None:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=validator.CHECKLIST_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)

    def compliant_rows(self) -> list[dict[str, str]]:
        return [
            {
                "check_id": f"check_{index:02d}",
                "required_check": requirement,
                "status": "pass",
                "prohibited_exposure_observed": "no",
                "exposed_records_or_na": "not_applicable",
                "leak_source_or_na": "not_applicable",
                "remediation_or_na": "not_applicable",
                "retest_evidence_or_na": "not_applicable",
                "final_disposition": "no_leak_confirmed",
                "auditor_id": "auditor_01",
                "auditor_role": "independent_interface_auditor",
                "audited_at_utc": "2026-07-14T12:00:00+00:00",
                "notes": "checked in rendered browser",
            }
            for index, requirement in enumerate(validator.load_contract(validator.DEFAULT_CONTRACT_PATH)["required_human_browser_checks"], start=1)
        ]

    def test_complete_independent_no_leak_checklist_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            checklist = Path(temporary) / "checklist.csv"
            self.write_checklist(checklist, self.compliant_rows())
            audit = validator.validate_checklist(checklist, validator.DEFAULT_CONTRACT_PATH)
            self.assertEqual(audit["status"], "PASS")

    def test_unfinished_checklist_cannot_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            checklist = Path(temporary) / "checklist.csv"
            rows = self.compliant_rows()
            rows[0]["status"] = "not_started"
            self.write_checklist(checklist, rows)
            audit = validator.validate_checklist(checklist, validator.DEFAULT_CONTRACT_PATH)
            self.assertEqual(audit["status"], "FAIL")
            self.assertIn("incomplete_or_failed_human_check:rendered_dom", audit["error_codes"])

    def test_reviewer_role_cannot_sign_independent_audit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            checklist = Path(temporary) / "checklist.csv"
            rows = self.compliant_rows()
            rows[0]["auditor_role"] = "first_pass_reviewer"
            self.write_checklist(checklist, rows)
            audit = validator.validate_checklist(checklist, validator.DEFAULT_CONTRACT_PATH)
            self.assertEqual(audit["status"], "FAIL")
            self.assertIn("auditor_role_not_independent", audit["error_codes"])


if __name__ == "__main__":
    unittest.main()
