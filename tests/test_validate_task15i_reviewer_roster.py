from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("task15i_roster", ROOT / "scripts/validate_task15i_reviewer_roster.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class Task15IReviewerRosterTests(unittest.TestCase):
    def valid_rows(self) -> list[dict[str, str]]:
        return [
            {
                "reviewer_code": code,
                "restricted_person_name": name,
                "eligible_roles": "first_pass_reviewer;adjudicator",
                "training_confirmed": "yes",
                "pair_or_role_conflicts": "none_declared",
                "conflict_attestation": "confirmed",
                "signed_at_utc": "2026-07-26T12:00:00+00:00",
            }
            for code, name in [("rv_a", "Person A"), ("rv_b", "Person B"), ("rv_c", "Person C"), ("rv_d", "Person D")]
        ]

    def test_valid_distinct_roster_passes(self) -> None:
        self.assertEqual(MODULE.validate_roster(self.valid_rows(), {"rv_a", "rv_b", "rv_c", "rv_d"}), [])

    def test_blank_template_is_not_release_eligible(self) -> None:
        rows = self.valid_rows()
        rows[0]["restricted_person_name"] = ""
        rows[1]["training_confirmed"] = "no"
        rows[2]["pair_or_role_conflicts"] = ""
        rows[3]["conflict_attestation"] = "pending"
        rows[3]["signed_at_utc"] = ""
        failures = MODULE.validate_roster(rows, {"rv_a", "rv_b", "rv_c", "rv_d"})
        self.assertIn("restricted_person_name_missing", failures)
        self.assertIn("rv_b:training_not_confirmed", failures)
        self.assertIn("rv_c:conflict_declaration_missing", failures)
        self.assertIn("rv_d:conflict_attestation_not_confirmed", failures)
        self.assertIn("rv_d:signed_at_utc_invalid", failures)

    def test_duplicate_person_is_rejected(self) -> None:
        rows = self.valid_rows()
        rows[3]["restricted_person_name"] = "Person A"
        self.assertIn("restricted_person_name_not_distinct", MODULE.validate_roster(rows, {"rv_a", "rv_b", "rv_c", "rv_d"}))


if __name__ == "__main__":
    unittest.main()
