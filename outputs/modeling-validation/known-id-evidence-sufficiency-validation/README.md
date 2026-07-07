# Known-ID Evidence Sufficiency Validation

Status: `PASS`

This module trains interpretable L2 logistic validation models on the
CzechLynx Phase18M reviewed identity-balanced pairs using the issue #7
PF-ERI evidence feature definitions.

## Outputs

- Validation table: `outputs/modeling-validation/known-id-evidence-sufficiency-validation/known_id_reviewability_validation_table.csv`
- Metrics: `outputs/modeling-validation/known-id-evidence-sufficiency-validation/known_id_model_metrics.csv`
- Coefficients: `outputs/modeling-validation/known-id-evidence-sufficiency-validation/known_id_model_coefficients.csv`
- Calibration bins: `outputs/modeling-validation/known-id-evidence-sufficiency-validation/known_id_calibration_bins.csv`

## Boundary

Known-ID CzechLynx reviewability validation only.
Bobcat identity metrics remain blocked.
