from __future__ import annotations

import csv
import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "ws04_four_stage_allocation_audit",
    ROOT / "scripts/audit_ws04_four_stage_allocation.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FourStageAllocationAuditTests(unittest.TestCase):
    def contract(self) -> dict[str, object]:
        with (ROOT / "schemas/pferi_v2/four_stage_sample_allocation_contract_v1.json").open(encoding="utf-8") as handle:
            return json.load(handle)

    def write_summary(self, path: Path, development: int = 9130, calibration: int = 9200, confirmation: int = 9119) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "scenario_id",
                    "development_image_count__min",
                    "calibration_image_count__min",
                    "confirmation_image_count__min",
                    "development_canonical_pair_count__min",
                    "calibration_canonical_pair_count__min",
                    "confirmation_canonical_pair_count__min",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "scenario_id": "equal_image_thirds",
                    "development_image_count__min": 1000,
                    "calibration_image_count__min": 1000,
                    "confirmation_image_count__min": 1000,
                    "development_canonical_pair_count__min": development,
                    "calibration_canonical_pair_count__min": calibration,
                    "confirmation_canonical_pair_count__min": confirmation,
                }
            )

    def test_actual_contract_has_accepted_totals(self) -> None:
        requirements = MODULE.validate_contract(self.contract())
        self.assertEqual(requirements, {"development": 445, "calibration": 445, "confirmation": 1334})

    def test_contract_rejects_inconsistent_planned_count(self) -> None:
        broken = copy.deepcopy(self.contract())
        broken["analytical_roles"]["development"]["planned_collection_pairs"] = 444
        with self.assertRaisesRegex(ValueError, "planned collection"):
            MODULE.validate_contract(broken)

    def test_contract_rejects_confirmation_overlap(self) -> None:
        broken = copy.deepcopy(self.contract())
        broken["separation_rules"]["mechanism_and_deployment_pair_overlap_allowed"] = True
        with self.assertRaisesRegex(ValueError, "overlap"):
            MODULE.validate_contract(broken)

    def test_contract_rejects_sequential_confirmation_tuning(self) -> None:
        broken = copy.deepcopy(self.contract())
        broken["separation_rules"]["both_confirmation_samples_released_only_after_common_freeze"] = False
        with self.assertRaisesRegex(ValueError, "common freeze"):
            MODULE.validate_contract(broken)

    def test_build_audit_passes_capacity_only_without_outcomes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            summary_path = Path(temporary) / "summary.csv"
            self.write_summary(summary_path)
            audit = MODULE.build_audit(
                ROOT / "schemas/pferi_v2/four_stage_sample_allocation_contract_v1.json",
                summary_path,
            )
        self.assertEqual(audit["status"], "PASS_CAPACITY_ONLY")
        self.assertEqual(audit["v2_outcome_access"], "none")
        self.assertFalse(audit["authorizes_official_split_or_outcome_packet"])
        self.assertEqual(audit["capacity_checks"]["confirmation"]["required_planned_pairs"], 1334)

    def test_build_audit_fails_when_confirmation_capacity_is_insufficient(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            summary_path = Path(temporary) / "summary.csv"
            self.write_summary(summary_path, confirmation=1333)
            audit = MODULE.build_audit(
                ROOT / "schemas/pferi_v2/four_stage_sample_allocation_contract_v1.json",
                summary_path,
            )
        self.assertEqual(audit["status"], "FAIL_CAPACITY")
        self.assertFalse(audit["capacity_checks"]["confirmation"]["pass"])


if __name__ == "__main__":
    unittest.main()
