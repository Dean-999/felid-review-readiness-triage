from __future__ import annotations

import unittest

from scripts import build_nonlinear_evidence_sensitivity as nonlinear


class NonlinearEvidenceSensitivityTests(unittest.TestCase):
    def test_constant_feature_is_not_estimable(self) -> None:
        rows = [
            {
                "descriptor_name": "d",
                "review_pair_id": f"p{i}",
                "review_ready_label": "1",
                "not_ready_or_uncertain_label": "0",
                "constant_feature": "0.7",
            }
            for i in range(8)
        ]

        output = nonlinear.summarize_bins("constant_feature", "pooled", rows, "increasing_review_ready")

        self.assertEqual(len(output), 1)
        self.assertEqual(output[0]["unique_feature_values"], 1)
        self.assertEqual(output[0]["sensitivity_status"], "not_estimable_constant_feature")

    def test_increasing_feature_without_violations_is_supported(self) -> None:
        rows = []
        for i in range(100):
            rows.append(
                {
                    "descriptor_name": "d",
                    "review_pair_id": f"p{i:03d}",
                    "review_ready_label": "1" if i >= 40 else "0",
                    "not_ready_or_uncertain_label": "0" if i >= 40 else "1",
                    "feature": str(i / 99),
                }
            )

        output = nonlinear.summarize_bins("feature", "pooled", rows, "increasing_review_ready")

        self.assertEqual(len(output), nonlinear.DEFAULT_BIN_COUNT)
        self.assertEqual(output[0]["sensitivity_status"], "monotonic_supported")
        self.assertGreater(output[0]["directional_endpoint_effect"], 0.0)
        self.assertEqual(output[0]["monotonic_violation_count"], 0)

    def test_increasing_feature_with_drop_is_flagged_nonmonotonic(self) -> None:
        ready_by_index = [1, 1, 1, 0, 0, 0, 1, 1]
        rows = []
        for i, ready in enumerate(ready_by_index):
            rows.append(
                {
                    "descriptor_name": "d",
                    "review_pair_id": f"p{i:02d}",
                    "review_ready_label": str(ready),
                    "not_ready_or_uncertain_label": str(1 - ready),
                    "feature": str(i / 7),
                }
            )

        output = nonlinear.summarize_bins("feature", "pooled", rows, "increasing_review_ready")

        self.assertEqual(output[0]["sensitivity_status"], "nonlinear_or_nonmonotonic_pattern")
        self.assertGreater(output[0]["monotonic_violation_count"], 0)

    def test_tie_aware_bins_do_not_split_identical_feature_values(self) -> None:
        rows = []
        values = [0.1, 0.2, *([0.5] * 8), 0.8, 0.9]
        for i, value in enumerate(values):
            rows.append(
                {
                    "descriptor_name": "d",
                    "review_pair_id": f"p{i:02d}",
                    "review_ready_label": "1",
                    "not_ready_or_uncertain_label": "0",
                    "feature": str(value),
                }
            )

        bins = nonlinear.tie_aware_quantile_bins(rows, "feature", bin_count=4)
        value_to_bin_count: dict[float, int] = {}
        for group in bins:
            seen = {float(row["feature"]) for row in group}
            for value in seen:
                value_to_bin_count[value] = value_to_bin_count.get(value, 0) + 1

        self.assertEqual(value_to_bin_count[0.5], 1)

    def test_family_comparison_contains_quality_guardrail_deltas(self) -> None:
        rows = nonlinear.family_comparison_rows(
            [
                {
                    "scope": "pooled",
                    "model_family": "descriptor_only",
                    "pair_count": "10",
                    "auroc": "0.50",
                    "auprc": "0.60",
                    "brier_score": "0.20",
                    "ece_5bin": "0.10",
                },
                {
                    "scope": "pooled",
                    "model_family": "quality_only",
                    "pair_count": "10",
                    "auroc": "0.70",
                    "auprc": "0.75",
                    "brier_score": "0.18",
                    "ece_5bin": "0.08",
                },
                {
                    "scope": "pooled",
                    "model_family": "pf_eri_evidence_only",
                    "pair_count": "10",
                    "auroc": "0.80",
                    "auprc": "0.84",
                    "brier_score": "0.16",
                    "ece_5bin": "0.06",
                },
                {
                    "scope": "pooled",
                    "model_family": "descriptor_plus_pf_eri",
                    "pair_count": "10",
                    "auroc": "0.82",
                    "auprc": "0.86",
                    "brier_score": "0.15",
                    "ece_5bin": "0.05",
                },
            ]
        )

        pf_eri = next(row for row in rows if row["model_family"] == "pf_eri_evidence_only")
        primary = next(row for row in rows if row["model_family"] == "descriptor_plus_pf_eri")

        self.assertAlmostEqual(pf_eri["auroc_delta_vs_quality_only"], 0.10)
        self.assertAlmostEqual(primary["auroc_delta_vs_quality_only"], 0.12)
        self.assertIn("exceeds image-quality-only", pf_eri["interpretation"])


if __name__ == "__main__":
    unittest.main()
