from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from scripts import freeze_pferi_v2_feature_preprocessing as freezer
from scripts.pferi_v2_fold_preprocessor import (
    FittedFoldPreprocessor,
    fit_fold_preprocessor,
)


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "schemas/pferi_v2/feature_preprocessing_contract_v1.json"
MODEL_REGISTRY = ROOT / "schemas/pferi_v2/model_route_candidate_registry_v1.json"
STAGE_ROOT = ROOT / "archive/pferi_v2/task_runs/dual_sample_confirmation/2026-07-22_stage_isolated_analysis_inputs_v1"
FOLD_ROOT = ROOT / "archive/pferi_v2/task_runs/model_development/2026-07-22_component_disjoint_nested_folds_v1"
SIMULATION_DECISION = (
    ROOT
    / "archive/pferi_v2/task_runs/model_development/2026-07-22_outcome_free_design_simulation/current"
    / "minimax_route_decision.json"
)


class FeaturePreprocessingFreezeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.registry = json.loads(MODEL_REGISTRY.read_text(encoding="utf-8"))

    def test_contract_matches_frozen_model_registry(self) -> None:
        self.assertEqual(freezer.validate_contract(self.contract, self.registry), [])

    def test_continuous_statistics_are_training_only_and_missing_is_explicit(self) -> None:
        train = freezer.canonical_fixture().iloc[:4].copy()
        fitted = fit_fold_preprocessor(train, self.contract, ["pair_evidence"])
        transformed = fitted.transform(freezer.canonical_fixture())
        spec = next(row for row in fitted.continuous if row["column"] == "local_match_coverage_fraction")
        self.assertAlmostEqual(spec["median"], 0.3)
        self.assertEqual(transformed.loc[4, "local_match_coverage_fraction__missing"], 1.0)
        self.assertTrue(np.isfinite(transformed.to_numpy()).all())

    def test_unseen_category_maps_to_explicit_unknown(self) -> None:
        fixture = freezer.canonical_fixture()
        fitted = fit_fold_preprocessor(fixture.iloc[:4], self.contract, ["descriptor"])
        transformed = fitted.transform(fixture)
        self.assertEqual(
            transformed.loc[5, "descriptor_support_category==__UNKNOWN__"], 1.0
        )
        self.assertEqual(
            transformed.loc[4, "descriptor_support_category==__MISSING__"], 1.0
        )

    def test_serialization_round_trip_is_exact(self) -> None:
        fixture = freezer.canonical_fixture()
        fitted = fit_fold_preprocessor(
            fixture.iloc[:4], self.contract, ["descriptor", "independent_quality", "pair_evidence"]
        )
        restored = FittedFoldPreprocessor.from_payload(fitted.to_payload())
        self.assertEqual(fitted.sha256, restored.sha256)
        pd.testing.assert_frame_equal(fitted.transform(fixture), restored.transform(fixture))

    def test_P5_adds_only_pair_evidence_columns_after_P3(self) -> None:
        fixture = freezer.canonical_fixture()
        p3 = fit_fold_preprocessor(
            fixture.iloc[:4], self.contract, ["descriptor", "independent_quality"]
        )
        p5 = fit_fold_preprocessor(
            fixture.iloc[:4], self.contract,
            ["descriptor", "independent_quality", "pair_evidence"],
        )
        self.assertEqual(list(p5.output_columns[: len(p3.output_columns)]), list(p3.output_columns))
        added = set(p5.output_columns) - set(p3.output_columns)
        self.assertTrue(added)
        self.assertTrue(all(column.startswith("local_match_") for column in added))

    def test_all_missing_continuous_training_feature_is_hard_failure(self) -> None:
        fixture = freezer.canonical_fixture().iloc[:4].copy()
        fixture["local_match_coverage_fraction"] = np.nan
        with self.assertRaisesRegex(ValueError, "entirely missing"):
            fit_fold_preprocessor(fixture, self.contract, ["pair_evidence"])

    def test_end_to_end_freeze_reads_no_label_values_and_fits_no_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "freeze"
            audit = freezer.run(
                CONTRACT,
                MODEL_REGISTRY,
                STAGE_ROOT / "development_open/development_modeling_input.csv",
                STAGE_ROOT / "stage_gate_contract.json",
                FOLD_ROOT / "fold_validation_audit.json",
                FOLD_ROOT / "outer_fold_assignments.csv",
                FOLD_ROOT / "nested_fold_assignments.csv",
                SIMULATION_DECISION,
                output,
            )
            self.assertEqual(audit["status"], "PASS")
            self.assertFalse(audit["development_label_values_read"])
            self.assertFalse(audit["development_model_fitted"])
            self.assertTrue(audit["P3_P5_nested_invariant_pass"])
            self.assertGreater(audit["P5_transformed_column_count"], audit["P3_transformed_column_count"])
            self.assertTrue((output / "CHECKSUMS.sha256").exists())


if __name__ == "__main__":
    unittest.main()
