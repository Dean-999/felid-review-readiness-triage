# Phase 9B PF-ERI-Aware Fixed-Descriptor Reranking Results

## 1. Purpose

Phase 9B tests whether PF-ERI image, pair, and candidate utility scores can improve fixed-descriptor candidate reranking without training any model.

## 2. Relationship to PROJECT_RULES.md and Phase 9A

This run follows Level 1 only: no-training reranking with fixed MegaDescriptor and ResNet50 embeddings. It does not implement lightweight learning, metric learning, descriptor expansion, or external dataset validation.

## 3. Phase 8 Boundary

Phase 8 remains the boundary: simple PF-ERI hard filtering reduced false-candidate burden but did not robustly improve fixed-descriptor mAP under held-out query-level evaluation. Phase 9B tests utility-aware reranking as a stronger use of the same signal family.

## 4. Input Inventory

Inspected inputs: `18`. Missing inputs: `0`.

## 5. Candidate Table Construction

The candidate table uses descriptor-generated top-20 query-gallery candidates from fixed embeddings. Public outputs use hardened image tokens and do not export raw paths, original IDs, working IDs, locations, trap/camera fields, or per-identity histories.

## 6. Utility Score Construction

Image utility uses visual PF-ERI and keeps descriptor similarity out of image-level scoring. Pair and candidate utility add descriptor support, reciprocal support, margin confidence, descriptor disagreement, and visual failure penalties.

## 7. Baselines and Methods Compared

raw_megadescriptor_ranking, raw_resnet50_ranking, simple_pf_eri_hard_filtering, quality_only_reranking, image_utility_reranking, pair_utility_reranking, candidate_utility_reranking, candidate_utility_plus_descriptor_reranking, descriptor_only, visual_quality_only, visual_identity_evidence_only, descriptor_confidence_only, reciprocal_margin_only, descriptor_disagreement_only, image_utility_only, pair_utility_only, full_pf_eri_candidate_utility, full_minus_visual, full_minus_descriptor_disagreement, full_minus_reciprocal_margin

## 8. Held-Out Calibration/Evaluation Design

The run reconstructs the existing Phase 8 identity-aware query splits. Weights and thresholds are selected on calibration queries and reported on held-out evaluation queries.

## 9. Random Controls

Random same-size and same-coverage controls used `200` repeats per split and target method.

## 10. Main Held-Out Results

| method_id | mean_mAP | mean_MRR | mean_top1_accuracy | mean_top5_accuracy | mean_false_candidate_burden | mean_query_coverage | mean_positive_retention |
| --- | --- | --- | --- | --- | --- | --- | --- |
| full_minus_visual | 0.3929 | 0.3984 | 0.2782 | 0.6083 | 4.6972 | 1.0000 | 0.5310 |
| descriptor_confidence_only | 0.3816 | 0.3867 | 0.2633 | 0.5947 | 4.7026 | 1.0000 | 0.5213 |
| full_minus_descriptor_disagreement | 0.3797 | 0.3874 | 0.2643 | 0.5768 | 4.7083 | 1.0000 | 0.5108 |
| full_pf_eri_candidate_utility | 0.3754 | 0.3825 | 0.2576 | 0.5768 | 4.7083 | 1.0000 | 0.5108 |
| pair_utility_reranking | 0.3728 | 0.3829 | 0.2647 | 0.5847 | 4.7161 | 1.0000 | 0.4980 |
| candidate_utility_plus_descriptor_reranking | 0.3725 | 0.3827 | 0.2669 | 0.5679 | 4.7187 | 1.0000 | 0.4930 |
| reciprocal_margin_only | 0.3718 | 0.3781 | 0.2762 | 0.5651 | 4.7175 | 1.0000 | 0.4947 |
| full_minus_reciprocal_margin | 0.3662 | 0.3770 | 0.2513 | 0.5808 | 4.7149 | 1.0000 | 0.4997 |

## 11. Direct Comparisons

Candidate utility plus descriptor reranking mean mAP: `0.3725`.
Raw MegaDescriptor mean mAP: `0.3606`.
Simple PF-ERI hard filtering mean mAP: `0.1628`.
Quality-only reranking mean mAP: `0.3452`.

## 12. Feature Ablation Results

| method_id | mean_mAP | mean_MRR | mean_false_candidate_burden | mean_query_coverage | mean_positive_retention |
| --- | --- | --- | --- | --- | --- |
| full_minus_visual | 0.3929 | 0.3984 | 4.6972 | 1.0000 | 0.5310 |
| descriptor_confidence_only | 0.3816 | 0.3867 | 4.7026 | 1.0000 | 0.5213 |
| full_minus_descriptor_disagreement | 0.3797 | 0.3874 | 4.7083 | 1.0000 | 0.5108 |
| full_pf_eri_candidate_utility | 0.3754 | 0.3825 | 4.7083 | 1.0000 | 0.5108 |
| reciprocal_margin_only | 0.3718 | 0.3781 | 4.7175 | 1.0000 | 0.4947 |
| full_minus_reciprocal_margin | 0.3662 | 0.3770 | 4.7149 | 1.0000 | 0.4997 |
| descriptor_only | 0.3606 | 0.3645 | 4.7194 | 1.0000 | 0.4918 |
| descriptor_disagreement_only | 0.3526 | 0.3580 | 4.7192 | 1.0000 | 0.4922 |
| pair_utility_only | 0.3517 | 0.3550 | 4.7335 | 1.0000 | 0.4667 |
| visual_identity_evidence_only | 0.2615 | 0.2647 | 4.8137 | 1.0000 | 0.3289 |
| visual_quality_only | 0.2162 | 0.2194 | 4.8244 | 1.0000 | 0.3098 |
| image_utility_only | 0.2120 | 0.2143 | 4.8335 | 1.0000 | 0.2947 |

## 13. Risk-Coverage and Pareto Interpretation

Pareto-efficient held-out method/split rows: `67` of `400`. Interpret high mAP alongside query coverage, positive retention, and false-candidate burden.

## 14. Success/Failure Decision

Decision: `pf_eri_reranking_enhancement_not_supported`.

## 15. Allowed Claims

- CzechLynx fixed-descriptor PF-ERI-aware reranking can be evaluated without model training.
- Results are bounded to CzechLynx, fixed descriptors, and held-out query-level validation.
- If the decision is negative, PF-ERI remains supported as an evidence utility and review-prioritization framework rather than a proven Re-ID enhancement method.

## 16. Forbidden Claims

- PF-ERI is a new Re-ID descriptor.
- PF-ERI is a trained deep Re-ID model.
- PF-ERI identifies true individuals automatically.
- PF-ERI is validated across felids, Mainland Clouded Leopard, or Marbled Cat.
- PF-ERI is field-deployment ready or supports population, movement, occupancy, abundance, survival, or site-use inference.

## 17. Recommended Next Step

Review the Phase 9B decision before any Phase 9C lightweight learning. Do not train unless the held-out reranking result is judged strong enough and explicit approval is given.

## 18. Confirmation

No training, no external data download, no frozen-data edit, no delayed second-review access, no staging, and no commit were performed.
