# Nonlinear Evidence Sensitivity

This report tests whether core PF-ERI evidence features show binned nonlinear or monotonic-style sensitivity in the 400-row CzechLynx known-ID reviewability validation table.

## Feature Estimability

- `visible_pattern_area_score`: not_estimable_constant_feature (unique=1, min=0.74, max=0.74); pooled status `not_estimable_constant_feature`.
- `body_part_overlap_score`: estimable_binned_sensitivity (unique=315, min=0.141993, max=0.78); pooled status `nonlinear_or_nonmonotonic_pattern`.
- `viewpoint_side_compatibility`: not_estimable_constant_feature (unique=1, min=0.7, max=0.7); pooled status `not_estimable_constant_feature`.
- `night_or_motion_blur_risk`: not_estimable_constant_feature (unique=1, min=0.18, max=0.18); pooled status `not_estimable_constant_feature`.
- `cross_descriptor_agreement_score`: estimable_binned_sensitivity (unique=117, min=0.355781, max=0.989782); pooled status `monotonic_supported_sparse_bin_caveat`.
- `source_domain_shift_score`: not_estimable_constant_feature (unique=1, min=0.1, max=0.1); pooled status `not_estimable_constant_feature`.

## Quality-Only Guardrail

- pooled `quality_only` AUROC=0.725004; delta_vs_quality=0.000000.
- pooled `pf_eri_evidence_only` AUROC=0.779782; delta_vs_quality=0.054778.
- pooled `descriptor_plus_pf_eri` AUROC=0.798691; delta_vs_quality=0.073687.

## Interpretation Boundary

Only features with sufficient variation support binned sensitivity claims. Constant features are reported as current design/data limitations, not as null biological effects. Source/domain stress remains diagnostic only because this supervised table has no source variation.
