# Table S2. Pair sampling frames and non-overlap checks

Unavailable fields are stated explicitly rather than inferred.

| stage | source_reservoir | selection_rule | pair_count | endpoint_image_count | component_count | pair_overlap_with_earlier_stages | endpoint_overlap | identity_overlap | seed | sampling_probability | audit_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Task15I development | Independent redevelopment reservoir | 400 endpoint-disjoint components; four pairs/component | 1600 | not reported in display source | 400 | none by stage role | zero across outer folds | not an analysis endpoint | frozen in source contract | first-order probability used in weights | PASS |
| Task15L calibration | Independent calibration partition | Frozen double-review calibration sample | 448 | not reported in display source | not applicable | stage-isolated by contract | not reported in display source | not an analysis endpoint | frozen in design artifact | not used for model reselection | PASS |
| Task15M confirmation | Deployment-confirmation queue | Frozen candidate manifest then dual-descriptor Gate 1 | 889 | 815 | not applicable | stage-isolated by contract | 357 endpoints among supported analysis pairs | not an analysis endpoint | frozen upstream | retained for Hajek weighting | PASS_TASK15M_EXECUTION_VALIDATION |
