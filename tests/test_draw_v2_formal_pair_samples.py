import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
SCRIPT = SCRIPTS / "draw_v2_formal_pair_samples.py"


def load_module():
    sys.path.insert(0, str(SCRIPTS))
    try:
        spec = importlib.util.spec_from_file_location("draw_v2_formal_pair_samples", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def row(pair_id, role="confirmation", cell="cell_a", rank="rank_01_05", **changes):
    base = {
        "canonical_pair_id": pair_id,
        "analytical_role": role,
        "endpoint_a_image_id": f"{pair_id}_a",
        "endpoint_b_image_id": f"{pair_id}_b",
        "retrieval_stratum_id": cell,
        "development_sampling_cell_id": cell if role == "development" else "",
        "best_rank_band": rank,
        "descriptor_support_category": "both",
        "dual_descriptor_percentile_disagreement": "0.1",
        "endpoint_quality_measurement_failure": "false",
        "endpoint_frozen_quality_stress": "false",
        "local_match_measurement_failure": "false",
        "local_match_within_role_percentile": "0.5",
    }
    base.update(changes)
    return base


class FormalSelectionTests(unittest.TestCase):
    def test_select_from_cells_is_exact_deterministic_and_capacity_bounded(self):
        module = load_module()
        rows = [row(f"p{i}", role="development", cell="c1") for i in range(4)]
        first = module.select_from_cells(
            rows,
            quotas={"c1": 2},
            analytical_role="development",
            sampling_stage="development_within_cell_order",
            cell_field="development_sampling_cell_id",
            seed_hex="00" * 32,
            contract_version="contract",
        )
        second = module.select_from_cells(
            list(reversed(rows)),
            quotas={"c1": 2},
            analytical_role="development",
            sampling_stage="development_within_cell_order",
            cell_field="development_sampling_cell_id",
            seed_hex="00" * 32,
            contract_version="contract",
        )
        self.assertEqual([item["canonical_pair_id"] for item in first], [item["canonical_pair_id"] for item in second])
        self.assertEqual(len(first), 2)
        self.assertTrue(all(item["first_order_inclusion_probability"] == "0.500000000000" for item in first))

    def test_mechanism_precedence_and_remaining_frame_disagreement_percentile(self):
        module = load_module()
        rows = [
            row("failure", dual_descriptor_percentile_disagreement="0.2", local_match_measurement_failure="true"),
            row("quality", dual_descriptor_percentile_disagreement="0.3", endpoint_frozen_quality_stress="true"),
            row("local", dual_descriptor_percentile_disagreement="0.4", local_match_within_role_percentile="0.1"),
            row("exclusive", descriptor_support_category="dinov2_only", dual_descriptor_percentile_disagreement=""),
            row("dual_high", dual_descriptor_percentile_disagreement="0.9"),
            row("ordinary", dual_descriptor_percentile_disagreement="0.1"),
        ]
        derived = {item["canonical_pair_id"]: item for item in module.derive_mechanism_cells(rows)}
        self.assertEqual(derived["failure"]["mechanism_challenge_state"], "automatic_measurement_failure")
        self.assertEqual(derived["quality"]["mechanism_challenge_state"], "image_quality_stress")
        self.assertEqual(derived["local"]["mechanism_challenge_state"], "local_correspondence_bottom_quintile")
        self.assertEqual(derived["exclusive"]["mechanism_challenge_state"], "descriptor_exclusive")
        self.assertEqual(derived["dual_high"]["mechanism_challenge_state"], "dual_descriptor_percentile_disagreement_top_quintile")
        self.assertEqual(derived["ordinary"]["mechanism_challenge_state"], "ordinary_reference")

    def test_zero_overlap_audit_rejects_duplicate_pair(self):
        module = load_module()
        with self.assertRaisesRegex(ValueError, "overlap"):
            module.assert_zero_pair_overlap({"development": [row("same")], "calibration": [row("same")]})

    def test_existing_formal_directory_is_never_overwritten(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            final = Path(directory) / "formal"
            final.mkdir()
            with self.assertRaisesRegex(FileExistsError, "refusing to overwrite"):
                module.ensure_fresh_final_path(final)

    def test_failed_independent_validation_cannot_create_final_directory(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staging = root / "staging"
            final = root / "formal"
            staging.mkdir()
            original = module.independent_validate
            module.independent_validate = lambda *_: (_ for _ in ()).throw(ValueError("independent failure"))
            try:
                with self.assertRaisesRegex(ValueError, "independent failure"):
                    module.freeze_after_independent_validation(root, staging, final)
            finally:
                module.independent_validate = original
            self.assertFalse(final.exists())
            self.assertTrue(staging.exists())


if __name__ == "__main__":
    unittest.main()
