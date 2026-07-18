from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ws04_power_cost_audit", ROOT / "scripts/audit_ws04_power_cost_inputs.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PowerCostInputAuditTests(unittest.TestCase):
    def contract(self) -> dict[str, object]:
        with (ROOT / "schemas/pferi_v2/power_cost_simulation_input_contract_v1.json").open(encoding="utf-8") as handle:
            return json.load(handle)

    def test_contract_is_explicitly_unfrozen_and_has_all_freeze_items(self) -> None:
        unresolved = MODULE.validate_contract(self.contract())
        self.assertGreaterEqual(len(unresolved), 8)
        self.assertIn("minimum practical Brier increment", unresolved)

    def test_contract_rejects_hidden_numerical_freeze(self) -> None:
        broken = self.contract()
        broken["primary_estimand"]["minimum_practical_brier_increment"]["value"] = 0.01
        with self.assertRaises(ValueError):
            MODULE.validate_contract(broken)

    def test_actual_audit_preserves_pre_outcome_boundary(self) -> None:
        audit = MODULE.build_audit(ROOT / "schemas/pferi_v2/power_cost_simulation_input_contract_v1.json")
        self.assertEqual(audit["status"], "BLOCKED_PENDING_PRE_OUTCOME_DECISIONS")
        self.assertEqual(audit["v2_outcome_access"], "none; this audit reads no v2 reviewability label, response log, model fit, calibration result, or confirmation result.")
        self.assertEqual(audit["known_pre_outcome_facts"]["eligible_canonical_pair_count"], 85182)
        self.assertEqual(len(audit["approved_input_sources"]), 6)
        context = audit["approved_input_sources"][3]
        self.assertEqual(context["summary"]["source_count"], 3)
        self.assertEqual(context["summary"]["record_count"], 10)


if __name__ == "__main__":
    unittest.main()
