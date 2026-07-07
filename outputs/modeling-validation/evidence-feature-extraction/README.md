# Evidence Feature Extraction

Status: `PASS`

This module computes the prespecified PF-ERI pair-level evidence
components from the pair-construction scaffold.

## Core Predictors

- `visible_pattern_area_score`
- `viewpoint_side_compatibility`
- `body_part_overlap_score`
- `night_or_motion_blur_risk`
- `cross_descriptor_agreement_score`
- `source_domain_shift_score`

## Counts

- Pair rows: 71695
- Pair families: `{'known_id_validation': 17695, 'transfer_stress': 54000}`
- Descriptor score source counts: `{'descriptor_pair_not_in_returned_topk_scores': 25472, 'descriptor_scores_unavailable_for_current_scope': 45000, 'megadescriptor_and_dinov2_returned_pair_scores': 1223}`

## Boundary

Core feature table supports evidence sufficiency modeling. Same/different labels, review labels, and source names are excluded from the core predictor set.
