from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from scripts import simulate_pferi_v2_model_design as module


ROOT = Path(__file__).resolve().parents[1]
DGP_REGISTRY = ROOT / "schemas/pferi_v2/model_design_dgp_registry_v1.json"
DGP_REGISTRY_V2 = ROOT / "schemas/pferi_v2/model_design_dgp_registry_v2.json"
MODEL_REGISTRY = ROOT / "schemas/pferi_v2/model_route_candidate_registry_v1.json"


class ModelDesignSimulationTests(unittest.TestCase):
    def make_fixture(self, root: Path, population_n: int = 80, sample_n: int = 24) -> tuple[Path, Path]:
        rng = np.random.default_rng(19)
        ids = [f"pair_{index:03d}" for index in range(population_n)]
        master = pd.DataFrame(
            {
                "canonical_pair_id": ids,
                "pair_execution_id": [f"exec_{index:03d}" for index in range(population_n)],
                "analytical_role": "development",
                "endpoint_a_image_id": [f"image_{index // 2:03d}" for index in range(population_n)],
                "endpoint_b_image_id": [f"image_{(index // 2) + 1:03d}" for index in range(population_n)],
                "descriptor_support_category": np.where(np.arange(population_n) % 3, "both", "mega_only"),
                "megadescriptor_within_role_percentile": rng.uniform(size=population_n),
                "dinov2_within_role_percentile": rng.uniform(size=population_n),
                "endpoint_native_pixel_quality_percentile_min": rng.uniform(size=population_n),
                "endpoint_sharpness_quality_percentile_min": rng.uniform(size=population_n),
                "endpoint_exposure_quality_percentile_min": rng.uniform(size=population_n),
                "endpoint_quality_measurement_failure": np.arange(population_n) % 17 == 0,
                "endpoint_frozen_quality_stress": np.where(np.arange(population_n) % 4, "none", "stress"),
                "local_match_coverage_fraction": rng.uniform(size=population_n),
                "local_match_measurement_failure": np.arange(population_n) % 19 == 0,
                "development_sampling_cell_id": np.where(np.arange(population_n) % 2, "cell_a", "cell_b"),
            }
        )
        formal = pd.DataFrame(
            {
                "formal_sampling_stage": "development",
                "canonical_pair_id": ids[:sample_n],
                "pair_execution_id": [f"exec_{index:03d}" for index in range(sample_n)],
                "source_analytical_role": "development",
                "first_order_inclusion_probability": np.linspace(0.08, 0.9, sample_n),
            }
        )
        master_path = root / "master.csv"
        formal_path = root / "formal.csv"
        master.to_csv(master_path, index=False)
        formal.to_csv(formal_path, index=False)
        return master_path, formal_path

    def make_three_stage_fixture(self, root: Path, role_n: int = 60, sample_n: int = 20) -> tuple[Path, Path]:
        pieces = []
        formal_pieces = []
        for role_index, role in enumerate(["development", "calibration", "confirmation"]):
            role_root = root / role
            role_root.mkdir()
            master_path, formal_path = self.make_fixture(role_root, role_n, sample_n)
            frame = pd.read_csv(master_path)
            frame["canonical_pair_id"] = role + "_" + frame["canonical_pair_id"].astype(str)
            frame["pair_execution_id"] = role + "_" + frame["pair_execution_id"].astype(str)
            frame["endpoint_a_image_id"] = role + "_" + frame["endpoint_a_image_id"].astype(str)
            frame["endpoint_b_image_id"] = role + "_" + frame["endpoint_b_image_id"].astype(str)
            frame["analytical_role"] = role
            if role != "development":
                frame["development_sampling_cell_id"] = np.nan
            pieces.append(frame)
            if role in {"development", "calibration"}:
                formal = pd.read_csv(formal_path)
                formal["canonical_pair_id"] = role + "_" + formal["canonical_pair_id"].astype(str)
                formal["pair_execution_id"] = role + "_" + formal["pair_execution_id"].astype(str)
                formal["formal_sampling_stage"] = role
                formal["source_analytical_role"] = role
                formal_pieces.append(formal)
        master = pd.concat(pieces, ignore_index=True)
        formal = pd.concat(formal_pieces, ignore_index=True)
        master_path = root / "three_stage_master.csv"
        formal_path = root / "three_stage_formal.csv"
        master.to_csv(master_path, index=False)
        formal.to_csv(formal_path, index=False)
        return master_path, formal_path

    def test_default_dgp_registry_passes_validation(self) -> None:
        registry = json.loads(DGP_REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(module.validate_dgp_registry(registry), [])
        self.assertGreaterEqual(len(registry["scenarios"]), 10)
        self.assertIn("null_evidence_increment", {row["scenario_id"] for row in registry["scenarios"]})

    def test_v2_registry_resolves_to_three_stage_design(self) -> None:
        registry = module.load_dgp_registry(DGP_REGISTRY_V2)
        self.assertEqual(registry["registry_version"], "pferi_v2_model_design_dgp_registry_v2")
        self.assertEqual(module.validate_dgp_registry(registry), [])
        self.assertIn("three_stage_design", registry)

    def test_inverse_probability_weight_strategies_are_positive_and_normalized(self) -> None:
        pi = np.array([0.1, 0.2, 0.5, 1.0])
        for strategy in ["unweighted", "hajek_ipw", "sqrt_ipw"]:
            weights = module.training_weights(pi, strategy)
            self.assertTrue(np.all(np.isfinite(weights)))
            self.assertTrue(np.all(weights > 0))
            self.assertAlmostEqual(float(weights.mean()), 1.0)

    def test_synthetic_probabilities_are_bounded_and_target_prevalence_is_respected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            master_path, formal_path = self.make_fixture(Path(tmp))
            population, _ = module.load_outcome_free_inputs(master_path, formal_path)
            registry = json.loads(DGP_REGISTRY.read_text(encoding="utf-8"))
            scenario = registry["scenarios"][1]
            probabilities = module.synthetic_probabilities(
                population,
                scenario,
                np.random.default_rng(7),
            )
            self.assertEqual(probabilities.shape, (len(population),))
            self.assertTrue(np.all((probabilities > 0) & (probabilities < 1)))
            self.assertAlmostEqual(
                float(probabilities.mean()),
                float(scenario["target_prevalence"]),
                delta=0.01,
            )

    def test_loader_rejects_any_outcome_bearing_input_header(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            master_path, formal_path = self.make_fixture(root)
            frame = pd.read_csv(master_path)
            frame["review_ready_label"] = 1
            frame.to_csv(master_path, index=False)
            with self.assertRaisesRegex(ValueError, "outcome-like"):
                module.load_outcome_free_inputs(master_path, formal_path)

    def test_expected_probability_metrics_are_zero_at_oracle_prediction(self) -> None:
        truth = np.array([0.1, 0.4, 0.8])
        metrics = module.expected_probability_metrics(truth, truth)
        self.assertAlmostEqual(metrics["brier_regret"], 0.0)
        self.assertAlmostEqual(metrics["log_loss_regret"], 0.0)
        self.assertAlmostEqual(metrics["calibration_intercept"], 0.0, places=6)
        self.assertAlmostEqual(metrics["calibration_slope"], 1.0, places=6)

    def test_end_to_end_simulation_writes_auditable_outputs_without_real_labels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            master_path, formal_path = self.make_fixture(root)
            output = root / "simulation"
            audit = module.run_simulation(
                master_path,
                formal_path,
                DGP_REGISTRY,
                MODEL_REGISTRY,
                output,
                replicates_override=2,
                expected_population_rows=80,
                expected_sample_rows=24,
            )
            self.assertEqual(audit["status"], "PASS")
            self.assertEqual(audit["outcome_columns_read"], 0)
            self.assertFalse(audit["real_outcomes_used"])
            self.assertEqual(audit["population_row_count"], 80)
            self.assertEqual(audit["sample_row_count"], 24)
            self.assertTrue((output / "simulation_replicate_metrics.csv").exists())
            self.assertTrue((output / "dgp_route_summary.csv").exists())
            self.assertTrue((output / "minimax_route_decision.json").exists())
            self.assertTrue((output / "CHECKSUMS.sha256").exists())

    def test_three_stage_simulation_uses_synthetic_calibration_and_confirmation_population(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            master_path, formal_path = self.make_three_stage_fixture(root)
            output = root / "simulation_v2"
            audit = module.run_simulation(
                master_path,
                formal_path,
                DGP_REGISTRY_V2,
                MODEL_REGISTRY,
                output,
                replicates_override=2,
                expected_population_rows=60,
                expected_sample_rows=20,
                expected_calibration_rows=20,
                expected_confirmation_rows=60,
            )
            self.assertEqual(audit["status"], "PASS")
            self.assertEqual(audit["master_outcome_free_row_count"], 180)
            self.assertEqual(audit["calibration_sample_row_count"], 20)
            self.assertEqual(audit["confirmation_population_row_count"], 60)
            self.assertTrue(audit["synthetic_calibration_performed"])
            self.assertFalse(audit["real_outcomes_used"])


if __name__ == "__main__":
    unittest.main()
