# Descriptor-Stratified Calibration

Status: `PASS`

This module checks MegaDescriptor and DINOv2 candidate queues separately
so pooled PF-ERI performance cannot hide descriptor-family behavior.

## Outputs

- Calibration metrics: `outputs/modeling-validation/advanced-mathematical-validation/descriptor_stratified_calibration.csv`
- Reliability bins: `outputs/modeling-validation/advanced-mathematical-validation/descriptor_stratified_reliability.csv`
- Risk/coverage: `outputs/modeling-validation/advanced-mathematical-validation/descriptor_stratified_risk_coverage.csv`
- Flags: `outputs/modeling-validation/advanced-mathematical-validation/descriptor_stratified_calibration_flags.csv`

## Boundary

PF-ERI is evaluated after descriptor retrieval; descriptor-stratified diagnostics do not claim descriptor replacement.
