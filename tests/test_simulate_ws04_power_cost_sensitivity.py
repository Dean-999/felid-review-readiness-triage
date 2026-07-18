from __future__ import annotations

import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ws04_power_cost", ROOT / "scripts/simulate_ws04_power_cost_sensitivity.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PowerCostSensitivityTests(unittest.TestCase):
    def config(self) -> dict[str, object]:
        return {
            "scenario_version": MODULE.SCENARIO_VERSION,
            "binding_status": MODULE.BOUNDARY,
            "claim_boundary": "synthetic test only",
            "primary_estimand": "control Brier minus full Brier",
            "simulation_seed": 3,
            "graph_draws_per_design_point": 100,
            "confidence_level": 0.95,
            "statistical_model": {
                "practical_brier_increment_scenarios": [0.005],
                "true_brier_increment_scenarios": [0.01],
                "paired_loss_difference_sd_scenarios": [0.1],
                "image_variance_fraction_scenarios": [0.0, 0.1],
                "confirmation_analyzable_pair_counts": [2, 3],
                "success_rule": "test only",
            },
            "completion_and_workload_scenarios": {
                "completion_rates": [0.9],
                "profiles": [{
                    "profile_id": "test",
                    "first_pass_minutes_per_pair": 1.0,
                    "adjudication_rate": 0.2,
                    "adjudication_minutes_per_pair": 1.0,
                }],
            },
            "feature_runtime_context": {"local_match_pair_runtime_p95_seconds": 1.0},
        }

    def write_manifest(self, path: Path) -> None:
        fields = ["contract_version", "canonical_pair_id", "endpoint_a_image_id", "endpoint_b_image_id", "pair_availability_status", "pair_inclusion_status"]
        rows = [
            ["v1", "p1", "a", "b", "available", "eligible"],
            ["v1", "p2", "b", "c", "available", "eligible"],
            ["v1", "p3", "c", "d", "available", "eligible"],
            ["v1", "p4", "a", "d", "available", "eligible"],
        ]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(fields)
            writer.writerows(rows)

    def test_nonbinding_config_rejects_official_seed(self) -> None:
        config = self.config()
        config["official_seed"] = 4
        with self.assertRaises(ValueError):
            MODULE.validate_config(config)

    def test_shared_images_inflate_design_effect(self) -> None:
        edges = MODULE.np.array([[0, 1], [1, 2], [2, 3], [0, 3]], dtype=MODULE.np.int32)
        effects = MODULE.design_effects(edges, 4, 3, 0.1, 30, MODULE.np.random.default_rng(9))
        self.assertTrue(MODULE.np.all(effects > 1.0))
        independent = MODULE.design_effects(edges, 4, 3, 0.0, 30, MODULE.np.random.default_rng(9))
        self.assertTrue(MODULE.np.all(independent == 1.0))

    def test_run_writes_nonbinding_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            manifest = directory / "canonical.csv"
            config = directory / "config.json"
            output = directory / "output"
            self.write_manifest(manifest)
            config.write_text(json.dumps(self.config()), encoding="utf-8")
            audit = MODULE.run_simulation(manifest, config, output)
            self.assertEqual(audit["status"], "NONBINDING_SENSITIVITY_COMPLETE_NOT_READY_TO_FREEZE")
            self.assertTrue((output / "power_sensitivity_results.csv").exists())
            self.assertTrue((output / "graph_design_effect_summary.csv").exists())
            self.assertTrue((output / "collection_workload_sensitivity.csv").exists())
            self.assertTrue((output / "power_sensitivity_illustration.png").exists())
            self.assertTrue((output / "power_cost_sensitivity_report.md").exists())


if __name__ == "__main__":
    unittest.main()
