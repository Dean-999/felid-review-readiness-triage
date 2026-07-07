from __future__ import annotations

import unittest

from scripts import build_descriptor_stratified_calibration as strat


class DescriptorStratifiedCalibrationTests(unittest.TestCase):
    def test_descriptor_metric_rows_include_both_descriptors_and_models(self) -> None:
        rows = strat.descriptor_metric_rows()
        keys = {(row["descriptor_name"], row["model_family"]) for row in rows}

        for descriptor in strat.DESCRIPTOR_SCOPES:
            for model in strat.MODEL_FAMILIES:
                self.assertIn((descriptor, model), keys)

    def test_primary_model_improves_over_descriptor_only_for_each_descriptor(self) -> None:
        rows = strat.descriptor_metric_rows()

        for descriptor in strat.DESCRIPTOR_SCOPES:
            primary = next(row for row in rows if row["descriptor_name"] == descriptor and row["model_family"] == strat.PRIMARY_MODEL)
            self.assertGreater(primary["auroc_delta_vs_descriptor_only"], 0.0)

    def test_reliability_rows_are_descriptor_scoped(self) -> None:
        rows = strat.reliability_rows()
        descriptors = {row["descriptor_name"] for row in rows}

        self.assertEqual(descriptors, set(strat.DESCRIPTOR_SCOPES))

    def test_flag_rows_emit_expected_flags_per_descriptor(self) -> None:
        metric_rows = strat.descriptor_metric_rows()
        risk_rows = strat.risk_coverage_rows()
        flags = strat.flag_rows(metric_rows, risk_rows)
        flag_ids = {row["flag_id"] for row in flags}

        self.assertEqual(len(flags), len(strat.DESCRIPTOR_SCOPES) * 4)
        self.assertEqual(
            flag_ids,
            {
                "primary_model_calibration_status",
                "any_model_weak_calibration_ece",
                "alpha_0_15_calibration_selective_risk",
                "alpha_0_15_evaluation_selective_risk",
            },
        )

    def test_flags_surface_descriptor_specific_calibration_risk(self) -> None:
        metric_rows = strat.descriptor_metric_rows()
        risk_rows = strat.risk_coverage_rows()
        flags = strat.flag_rows(metric_rows, risk_rows)
        warning_ids = {(row["descriptor_name"], row["flag_id"]) for row in flags if row["severity"] == "warning"}

        self.assertIn(("dinov2_vitl14", "alpha_0_15_calibration_selective_risk"), warning_ids)
        self.assertIn(("megadescriptor_l_384", "any_model_weak_calibration_ece"), warning_ids)


if __name__ == "__main__":
    unittest.main()
