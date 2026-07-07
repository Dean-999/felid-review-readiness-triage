# Conformal-Inspired Selective Router

Status: `PASS`

This module chooses alpha-level selective evidence admission thresholds
from CzechLynx calibration folds and reports evaluation risk/coverage.

## Loss

nonconformity_loss = 1 if not-ready-or-uncertain, else 0; selective risk is mean loss among admitted pairs.

## Direction

admit if evidence_risk_score <= risk_threshold_tau, equivalently evidence_admission_score >= evidence_score_threshold.

## Finite-Sample Diagnostic

`{"empirical_only_upper_bound_exceeds_alpha": 5}`

Thresholds are selected by empirical calibration selective risk. The
Hoeffding upper-risk column is reported as a diagnostic; rows whose
upper bound exceeds alpha must not be described as finite-sample
upper-bound supported guarantees.

## Outputs

- Thresholds: `outputs/modeling-validation/advanced-mathematical-validation/conformal_selective_thresholds.csv`
- Risk/coverage curve: `outputs/modeling-validation/advanced-mathematical-validation/conformal_selective_risk_coverage.csv`
- Pair routes: `outputs/modeling-validation/advanced-mathematical-validation/conformal_selective_pair_routes.csv`

## Boundary

Conformal-inspired selective risk calibration on CzechLynx reviewed pairs only; not Re-ID identity accuracy.
Bobcat transfer-stress rows are out of scope for distribution-free conformal claims.
