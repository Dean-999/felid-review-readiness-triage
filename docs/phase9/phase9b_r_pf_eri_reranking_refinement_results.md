# Phase 9B-R PF-ERI Reranking Refinement Results

## 1. Purpose

Phase 9B-R diagnoses why the visual utility component did not help as an additive reranking term and tests transparent no-training refinement variants.

## 2. Relationship to Phase 9B

Phase 9B showed modest held-out mAP improvement for PF-ERI-aware reranking but failed the pre-set positive-retention criterion. The strongest ablation was `full_minus_visual`, so this slice tests whether visual utility should be used as a gate, penalty, interaction, or workflow-safety signal rather than a simple additive term.

## 3. Visual Component Diagnosis

| diagnostic_item | same_mean | different_mean | same_minus_different | same_median | different_median | interpretation |
| --- | --- | --- | --- | --- | --- | --- |
| visual_pair_mean_same_vs_different | 0.6640 | 0.6420 | 0.0220 | 0.6733 | 0.6717 | positive_values_mean_visual_higher_for_true_candidates |
| visual_pair_min_same_vs_different | 0.5789 | 0.5466 | 0.0323 | 0.6217 | 0.5983 | positive_values_mean_visual_higher_for_true_candidates |
| query_image_utility_score_same_vs_different | 0.6526 | 0.6105 | 0.0421 | 0.6717 | 0.6617 | positive_values_mean_visual_higher_for_true_candidates |
| gallery_image_utility_score_same_vs_different | 0.6753 | 0.6735 | 0.0018 | 0.7083 | 0.7083 | positive_values_mean_visual_higher_for_true_candidates |
| visual_failure_penalty_same_vs_different | 0.2198 | 0.2349 | -0.0151 | 0.1000 | 0.1000 | nonpositive_values_mean_visual_not_higher_for_true_candidates |
| visual_pair_mean_bin_(-0.001, 0.522] | 0.0257 | 0.9743 | -0.9487 | 0.3400 | 0.2217 | bin_summary_true_rate_false_rate_descriptor_support |
| visual_pair_mean_bin_(0.522, 0.672] | 0.0290 | 0.9710 | -0.9419 | 0.4047 | 0.2660 | bin_summary_true_rate_false_rate_descriptor_support |
| visual_pair_mean_bin_(0.672, 0.795] | 0.0250 | 0.9750 | -0.9499 | 0.4280 | 0.2838 | bin_summary_true_rate_false_rate_descriptor_support |
| visual_pair_mean_bin_(0.795, 0.925] | 0.0343 | 0.9657 | -0.9315 | 0.5033 | 0.3484 | bin_summary_true_rate_false_rate_descriptor_support |
| phase9b_full_minus_visual_minus_full | 0.3929 | 0.3754 | 0.0175 | 0.5310 | 0.5108 | visual_additive_component_reduced_phase9b_map_and_retention |

## 4. Diagnostic Correlations

| variable | target | spearman_correlation | pearson_correlation | n |
| --- | --- | --- | --- | --- |
| descriptor_confidence_score | descriptor_similarity_norm | 0.9423 | 0.8806 | 100800.0000 |
| query_image_utility_score | descriptor_similarity_norm | 0.5075 | 0.5379 | 100800.0000 |
| visual_pair_min | descriptor_similarity_norm | 0.5025 | 0.5293 | 100800.0000 |
| visual_pair_mean | descriptor_similarity_norm | 0.4924 | 0.5102 | 100800.0000 |
| reciprocal_margin_score | descriptor_similarity_norm | 0.3655 | 0.3520 | 100800.0000 |
| gallery_image_utility_score | descriptor_similarity_norm | 0.3233 | 0.3261 | 100800.0000 |
| margin_confidence_norm | descriptor_similarity_norm | 0.2979 | 0.3073 | 100800.0000 |
| reciprocal_support_bool | same_identity_numeric | 0.1609 | 0.1609 | 100800.0000 |
| reciprocal_margin_score | same_identity_numeric | 0.1050 | 0.1786 | 100800.0000 |
| descriptor_confidence_score | same_identity_numeric | 0.0978 | 0.1522 | 100800.0000 |
| margin_confidence_norm | same_identity_numeric | 0.0734 | 0.1549 | 100800.0000 |
| descriptor_similarity_norm | same_identity_numeric | 0.0729 | 0.0883 | 100800.0000 |

## 5. Refined Methods Tested

raw_megadescriptor, raw_resnet50, phase9b_candidate_utility_plus_descriptor, phase9b_full_minus_visual, descriptor_confidence_plus_disagreement, reciprocal_margin_plus_disagreement, visual_failure_penalty_only, visual_identity_only_no_generic_quality, quality_only_baseline, visual_as_gate_only, visual_as_penalty_only, visual_interaction_with_disagreement, visual_interaction_with_low_margin, candidate_utility_with_retention_constraint, candidate_utility_with_coverage_floor, candidate_utility_pareto_selected

## 6. Held-Out Split Design and Random Controls

The refinement reused the Phase 9B held-out query split roles from the public candidate table. Random same-size and same-coverage controls used `200` repeats.

## 7. Main Refined Metric Results

| method_id | mean_mAP | mean_MRR | mean_top1_accuracy | mean_top5_accuracy | mean_false_candidate_burden | mean_query_coverage | mean_positive_retention |
| --- | --- | --- | --- | --- | --- | --- | --- |
| visual_as_penalty_only | 0.3958 | 0.4035 | 0.2839 | 0.6254 | 4.6925 | 1.0000 | 0.5393 |
| phase9b_full_minus_visual | 0.3929 | 0.3984 | 0.2782 | 0.6083 | 4.6972 | 1.0000 | 0.5310 |
| visual_interaction_with_disagreement | 0.3928 | 0.4007 | 0.2772 | 0.6285 | 4.6903 | 1.0000 | 0.5435 |
| descriptor_confidence_plus_disagreement | 0.3922 | 0.4006 | 0.2839 | 0.6083 | 4.6972 | 1.0000 | 0.5310 |
| visual_interaction_with_low_margin | 0.3860 | 0.3949 | 0.2789 | 0.5955 | 4.7030 | 1.0000 | 0.5209 |
| reciprocal_margin_plus_disagreement | 0.3813 | 0.3865 | 0.2641 | 0.5947 | 4.7026 | 1.0000 | 0.5213 |
| phase9b_candidate_utility_plus_descriptor | 0.3772 | 0.3867 | 0.2703 | 0.5759 | 4.7121 | 1.0000 | 0.5051 |
| candidate_utility_pareto_selected | 0.3681 | 0.3724 | 0.2676 | 0.5618 | 4.3909 | 0.9327 | 0.4787 |
| candidate_utility_with_retention_constraint | 0.3612 | 0.3681 | 0.2639 | 0.5525 | 4.3179 | 0.9192 | 0.4887 |
| raw_megadescriptor | 0.3606 | 0.3645 | 0.2386 | 0.5886 | 4.7194 | 1.0000 | 0.4918 |

## 8. Success Criteria Decision

Decision: `phase9b_r_supports_cautious_phase9c_planning`.
Best refined method: `visual_as_penalty_only` with mAP `0.3958`, MRR `0.4035`, top-1 `0.2839`, top-5 `0.6254`, query coverage `1.0000`, and positive retention `0.5393`.

## 9. Risk-Coverage and Pareto Interpretation

Pareto-efficient held-out method/split rows: `116` of `320`. Interpret mAP gains with positive retention, query coverage, and false-candidate burden.

## 10. Decision on Phase 9C

Do not begin Phase 9C training from this document alone. If the decision permits cautious planning, it still requires explicit approval and a separate feasibility audit.

## 11. Allowed Claims

- Phase 9B-R evaluates no-training PF-ERI reranking refinements under CzechLynx held-out query validation.
- Visual utility appears weaker as a simple additive reranking term than descriptor-confidence, reciprocal/margin, and disagreement components in this fixed-descriptor setting.
- Refined no-training methods can be compared against raw, quality-only, Phase 9B, and random controls.

## 12. Forbidden Claims

- PF-ERI is a new Re-ID descriptor.
- PF-ERI is a new deep Re-ID model.
- PF-ERI performs automatic identity assignment or true individual identification.
- PF-ERI is validated on Mainland Clouded Leopard or Marbled Cat.
- PF-ERI is field deployment ready or supports population estimation, movement, occupancy, abundance, survival, or site-use inference.
- PF-ERI robustly improves Re-ID accuracy beyond the bounded CzechLynx fixed-descriptor setting.

## 13. Confirmation

No training, no external data download, no frozen-data edit, no delayed second-review access, no staging, and no commit were performed.
