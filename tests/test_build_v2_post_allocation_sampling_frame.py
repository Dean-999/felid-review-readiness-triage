import importlib.util
import math
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_v2_post_allocation_sampling_frame.py"


def load_module():
    spec = importlib.util.spec_from_file_location("post_allocation_sampling_frame", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class MidrankPercentileTests(unittest.TestCase):
    def test_equal_values_are_not_split_and_zero_is_valid(self):
        module = load_module()
        observed = module.midrank_percentiles({"a": 0.0, "b": 0.0, "c": 1.0, "d": 2.0})
        self.assertEqual(observed, {"a": 0.25, "b": 0.25, "c": 0.625, "d": 0.875})

    def test_nonfinite_value_is_rejected(self):
        module = load_module()
        with self.assertRaisesRegex(ValueError, "finite"):
            module.midrank_percentiles({"a": math.nan})


class QuotaTests(unittest.TestCase):
    def test_hamilton_quota_is_capacity_safe_and_sums_to_target(self):
        module = load_module()
        observed = module.hamilton_quotas(
            {"large": 7, "medium": 2, "small": 1},
            target=6,
            tie_order={"large": "2", "medium": "1", "small": "0"},
            minimum_one=True,
        )
        self.assertEqual(sum(observed.values()), 6)
        self.assertTrue(all(0 <= observed[k] <= v for k, v in {"large": 7, "medium": 2, "small": 1}.items()))
        self.assertTrue(all(observed[k] >= 1 for k in observed))

    def test_waterfill_skips_exhausted_cells_without_merging_cells(self):
        module = load_module()
        observed = module.waterfill_quotas(
            {"a": 1, "b": 4, "c": 4}, target=7, tie_order={"a": "0", "b": "1", "c": "2"}
        )
        self.assertEqual(observed, {"a": 1, "b": 3, "c": 3})

    def test_quota_fails_when_total_capacity_is_insufficient(self):
        module = load_module()
        with self.assertRaisesRegex(ValueError, "INSUFFICIENT_FRAME_CAPACITY"):
            module.waterfill_quotas({"a": 1}, target=2, tie_order={"a": "0"})


class StateAndSchemaTests(unittest.TestCase):
    def test_descriptor_support_mismatch_is_fatal(self):
        module = load_module()
        with self.assertRaisesRegex(ValueError, "descriptor support mismatch"):
            module.validate_descriptor_support(
                "pair_a", "both", {"megadescriptor_l_384": 0.9}
            )

    def test_local_failure_is_retained_but_valid_zero_is_not_failure(self):
        module = load_module()
        self.assertEqual(
            module.development_evidence_state(
                quality_failure=False,
                local_failure=True,
                quality_stress=False,
                local_bottom=False,
                descriptor_disagreement_top=False,
            ),
            "measurement_failure",
        )
        self.assertEqual(
            module.development_evidence_state(
                quality_failure=False,
                local_failure=False,
                quality_stress=False,
                local_bottom=True,
                descriptor_disagreement_top=False,
            ),
            "evidence_stress",
        )

    def test_restricted_master_schema_cannot_contain_selection_or_outcome_fields(self):
        module = load_module()
        allowed = module.RESTRICTED_MASTER_FIELDNAMES
        forbidden_fragments = ("selected", "packet", "review", "outcome", "identity", "label")
        self.assertFalse([name for name in allowed if any(fragment in name.lower() for fragment in forbidden_fragments)])

    def test_hmac_digest_is_stable_and_namespaced(self):
        module = load_module()
        first = module.seeded_digest(
            seed_hex="00" * 32,
            contract_version="contract",
            analytical_role="development",
            sampling_stage="allocation_tie_break",
            cell_id="cell_a",
            ordering_unit_id="",
        )
        second = module.seeded_digest(
            seed_hex="00" * 32,
            contract_version="contract",
            analytical_role="calibration",
            sampling_stage="allocation_tie_break",
            cell_id="cell_a",
            ordering_unit_id="",
        )
        self.assertEqual(first, "a4862037bbb033d209577af1421865503e335db6b5b23e83f6892c80606ef670")
        self.assertNotEqual(first, second)


if __name__ == "__main__":
    unittest.main()
