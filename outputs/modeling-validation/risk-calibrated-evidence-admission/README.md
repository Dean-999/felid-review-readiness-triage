# Risk-Calibrated Evidence Admission

Status: `PASS`

This module calibrates selective evidence-admission thresholds from
CzechLynx reviewed-pair validation outputs.

## Outputs

- Routed pairs: `outputs/modeling-validation/risk-calibrated-evidence-admission/risk_calibrated_pair_routes.csv`
- Thresholds: `outputs/modeling-validation/risk-calibrated-evidence-admission/risk_calibrated_thresholds.csv`
- Risk/coverage curve: `outputs/modeling-validation/risk-calibrated-evidence-admission/risk_coverage_curve.csv`

## Route Counts

`{'accept_review': 128, 'cautious_review': 106, 'conflict_review': 163, 'defer_low_evidence': 3}`

## Boundary

Risk-calibrated evidence admission only; not Re-ID identity accuracy.
