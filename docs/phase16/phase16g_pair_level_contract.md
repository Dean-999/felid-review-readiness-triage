# Phase16G Pair-Level Evidence Contract

Date: 2026-06-28

Phase16G defines the pair-level evidence table used after Phase16F constrained
selection and before Phase16H calibrated review-router modeling.

Phase16G is not final model training. It is not identity assignment. It does not
report Bobcat identity accuracy without verified labels or audited same/different
pair labels.

## Correct Phase Boundary

```text
Phase16E full scoring
-> result acceptance
-> Phase16F soft eligibility and constrained selection
-> manual audit calibration
-> final 3000 freeze
-> Phase16G pair-level contract and CzechLynx prototype
-> Phase16H calibrated review-router modeling
```

## Required Column Groups

```text
image_evidence_features
pair_comparability_features
descriptor_features
conflict_features
control_features
label_fields
audit_fields
split_fields
```

## Required Controls

```text
descriptor_only
quality_only
random_same_size
phase16f_selected
low_evidence_stress
```

## Claim Boundary

CzechLynx known-ID pairs may validate false-candidate burden, positive
retention, risk coverage, and descriptor-evidence conflict.

Bobcat pairs remain transfer-stress and review-readiness evidence unless
verified individual labels or audited same/different pair labels exist.
