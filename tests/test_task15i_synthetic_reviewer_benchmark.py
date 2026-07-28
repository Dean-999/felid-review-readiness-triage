from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

import pandas as pd


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_task15i_synthetic_reviewer_benchmark.py"
SPEC = importlib.util.spec_from_file_location("task15i_synthetic", SCRIPT)
assert SPEC and SPEC.loader
benchmark = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(benchmark)


class Task15ISyntheticReviewerBenchmarkTests(unittest.TestCase):
    def test_conservative_double_review_rule_requires_two_ready_labels(self) -> None:
        self.assertEqual(benchmark.conservative_outcome("review_ready", "review_ready"), 0)
        self.assertEqual(benchmark.conservative_outcome("review_ready", "uncertain"), 1)
        self.assertEqual(benchmark.conservative_outcome("not_review_ready", "review_ready"), 1)


    def test_response_schema_rejects_incompatible_reason_codes(self) -> None:
        valid = {
            "review_decision": "review_ready",
            "reason_codes": "none_review_ready",
            "confidence": "medium",
            "technical_problem_flag": "no",
        }
        self.assertEqual(benchmark.validate_response_fields(valid), [])

        invalid = dict(valid, reason_codes="low_evidence")
        self.assertIn("reason_label_contradiction", benchmark.validate_response_fields(invalid))


    def test_p5_design_extends_p3_without_reordering_columns(self) -> None:
        p3 = ["descriptor__z", "quality__z"]
        p5 = [*p3, *benchmark.P5_INCREMENTAL_COLUMNS]
        self.assertEqual(benchmark.assert_nested_columns(p3, p5), 5)

    def test_p5_has_five_incremental_columns_when_failure_is_all_false(self) -> None:
        contract = json.loads(benchmark.FEATURE_CONTRACT.read_text(encoding="utf-8"))
        frame = pd.DataFrame(
            {
                "megadescriptor_within_role_percentile": [0.1, 0.4, 0.6, 0.9],
                "dinov2_within_role_percentile": [0.2, 0.3, 0.7, 0.8],
                "descriptor_support_category": ["both", "both", "both", "both"],
                "endpoint_native_pixel_quality_percentile_min": [0.2, 0.4, 0.6, 0.8],
                "endpoint_sharpness_quality_percentile_min": [0.3, 0.5, 0.7, 0.9],
                "endpoint_exposure_quality_percentile_min": [0.9, 0.7, 0.5, 0.3],
                "endpoint_quality_measurement_failure": [False, False, False, False],
                "endpoint_frozen_quality_stress": [False, False, False, False],
                "local_match_coverage_fraction": [0.05, 0.2, 0.4, 0.8],
                "local_match_measurement_failure": [False, False, False, False],
            }
        )
        pre3 = benchmark.fit_fold_preprocessor(frame, contract, ["descriptor", "independent_quality"])
        pre5 = benchmark.fit_fold_preprocessor(frame, contract, ["descriptor", "independent_quality", "pair_evidence"])
        transformed = benchmark.fixed_p5_transform(pre3, pre5, frame)
        self.assertEqual(list(transformed.columns[-5:]), benchmark.P5_INCREMENTAL_COLUMNS)
        self.assertEqual(len(transformed.columns) - len(pre3.output_columns), 5)
        self.assertTrue((transformed["local_match_measurement_failure==true"] == 0.0).all())
