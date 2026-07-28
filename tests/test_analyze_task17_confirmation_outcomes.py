from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import analyze_task17_confirmation_outcomes as task17


class Task17ConfirmationOutcomeTests(unittest.TestCase):
    def test_dyadic_interval_equals_independent_variance_without_shared_endpoints(self) -> None:
        deltas = np.asarray([0.0, 1.0, 2.0], dtype=float)
        weights = np.ones(3, dtype=float)
        result = task17.dyadic_interval(deltas, weights, [("a", "b"), ("c", "d"), ("e", "f")], 1.96)
        self.assertAlmostEqual(result["variance"], result["independent_row_se_diagnostic"] ** 2)

    def test_actual_inputs_have_complete_one_to_one_supported_outcome_linkage(self) -> None:
        contract = json.loads(task17.CONTRACT.read_text(encoding="utf-8"))
        records, provenance = task17.validate_and_prepare(contract)
        self.assertEqual(len(records), 252)
        self.assertEqual(provenance["deployment_outcome_row_count"], 889)
        self.assertEqual(len({row["historical_canonical_pair_id"] for row in records}), 252)
        self.assertTrue(all(row["not_ready_or_uncertain_label"] in {0.0, 1.0} for row in records))

    def test_primary_analysis_preserves_frozen_scope(self) -> None:
        contract = json.loads(task17.CONTRACT.read_text(encoding="utf-8"))
        report, records = task17.analyze(contract)
        self.assertEqual(len(records), 252)
        self.assertIn(report["status"], {"PASS_PRIMARY_CONFIRMATION", "FAIL_PRIMARY_CONFIRMATION"})
        self.assertFalse(report["models_refit"])
        self.assertFalse(report["calibration_parameters_recomputed"])
        self.assertEqual(report["decision_rule"], "lower_95 > 0.005")


if __name__ == "__main__":
    unittest.main()
