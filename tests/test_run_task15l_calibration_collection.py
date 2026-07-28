from __future__ import annotations

import importlib.util
import csv
import re
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("task15l_runner_test", ROOT / "scripts/run_task15l_calibration_collection.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules["task15l_runner_test"] = MODULE
SPEC.loader.exec_module(MODULE)


class Task15LRunnerTests(unittest.TestCase):
    def test_valid_review_ready_response_has_no_schema_errors(self) -> None:
        row = {
            "review_packet_id": "task_opaque",
            "raw_reviewer_response_id": "response_opaque",
            "review_decision": "review_ready",
            "reason_codes": "none_review_ready",
            "confidence": "medium",
            "optional_note": "",
            "submitted_at_utc": "2026-07-27T08:00:00+00:00",
            "technical_problem_flag": "no",
        }
        self.assertEqual(MODULE.response_errors(row), [])

    def test_reason_codes_cannot_change_eligibility_rule(self) -> None:
        row = {
            "review_decision": "review_ready",
            "reason_codes": "low_evidence",
            "confidence": "high",
            "technical_problem_flag": "no",
        }
        self.assertIn("ready_reason_contradiction", MODULE.response_errors(row))

    def test_unpenalized_two_parameter_calibration_is_finite(self) -> None:
        y = np.array([0, 1, 0, 1, 0, 1, 1, 0], dtype=float)
        predictor = np.array([-2.0, -1.1, -0.5, -0.2, 0.1, 0.7, 1.2, 1.6])
        fit = MODULE.fit_logistic(y, predictor)
        self.assertTrue(fit["converged"])
        self.assertTrue(np.isfinite([fit["intercept"], fit["slope"], fit["intercept_se"], fit["slope_se"]]).all())

    def test_synthetic_response_ids_and_timestamps_follow_form_schema_without_human_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package = Path(temporary) / "package" / "reviewer_view"
            assets = package / "assets"
            assets.mkdir(parents=True)
            Image.new("RGB", (30, 20), (100, 110, 120)).save(assets / "asset_left.png")
            Image.new("RGB", (30, 20), (120, 110, 100)).save(assets / "asset_right.png")
            with (package / "reviewer_packet.csv").open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=MODULE.PACKET_COLUMNS)
                writer.writeheader()
                writer.writerow({"review_packet_id": "task_opaque", "left_asset_token": "asset_left", "right_asset_token": "asset_right", "instrument_version": "instrument", "review_form_schema_version": "schema"})
            completed = Path(temporary) / "completed"
            MODULE.write_completed_package(package.parent, "reviewer_A", completed)
            with (completed / "raw_responses.csv").open(newline="", encoding="utf-8") as handle:
                row = next(csv.DictReader(handle))
            self.assertRegex(row["raw_reviewer_response_id"], r"^response_[0-9a-f]{32}$")
            self.assertNotEqual(row["submitted_at_utc"], "2026-07-27T08:00:00+00:00")
            self.assertIsNotNone(datetime.fromisoformat(row["submitted_at_utc"]).tzinfo)
            self.assertIn("synthetic reviewer", (completed / "reviewer_A_attestation.txt").read_text(encoding="utf-8").lower())


if __name__ == "__main__":
    unittest.main()
