# legacy-code16g Pair-Level Evidence Contract

Date: 2026-06-28

legacy-code16g defines the pair-level evidence table used after legacy-code16f constrained
selection and before legacy-code16h calibrated review-router modeling.

legacy-code16g is not final model training. It is not identity assignment. It does not
report Bobcat identity accuracy without verified labels or audited same/different
pair labels.

## Correct Phase Boundary

```text
legacy-code16e full scoring
-> result acceptance
-> legacy-code16f soft eligibility and constrained selection
-> manual audit calibration
-> final 3000 freeze
-> legacy-code16g pair-level contract and CzechLynx prototype
-> legacy-code16h calibrated review-router modeling
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
legacy-code16f_selected
low_evidence_stress
```

## Claim Boundary

CzechLynx known-ID pairs may validate false-candidate burden, positive
retention, risk coverage, and descriptor-evidence conflict.

Bobcat pairs remain transfer-stress and review-readiness evidence unless
verified individual labels or audited same/different pair labels exist.
