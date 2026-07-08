# PF-ERI Advanced Methods and Claim Gates

## Final Framing

PF-ERI is a selective evidence inference layer for wildlife Re-ID candidate pairs after strong descriptor retrieval. It does not introduce a new descriptor and does not assign identity.

## Mathematical Target

For candidate pair `p=(x_i,x_j)`, the descriptor queue provides similarity context `s_d(p)`. PF-ERI estimates evidence risk `R_hat(p)=P(y=1|z(p),s_d(p))`, where `y=1` means not-ready-or-uncertain. A selective gate admits a pair when `R_hat(p)<=tau`. Coverage is the admitted fraction, and selective risk is the not-ready-or-uncertain rate among admitted pairs.

## Loss and Risk Definitions

`L(p)=1` when a pair admitted for review is not-ready-or-uncertain, and `L(p)=0` otherwise. For gate `g_tau(p)=1[R_hat(p)<=tau]`, coverage is `E[g_tau(p)]` and selective risk is `E[L(p) | g_tau(p)=1]`. Reported alpha-level routing is empirical calibration/evaluation risk unless a finite-sample upper-bound diagnostic is explicitly satisfied.

## Calibration Procedure

Thresholds are selected on calibration folds by maximizing admitted coverage subject to empirical selective risk no greater than target `alpha`. Evaluation folds are reported separately and are not used to choose thresholds. Current Hoeffding upper-risk diagnostics exceed alpha, so finite-sample distribution-free language remains blocked.

## Uncertainty Procedure

Uncertainty is reported with query-image cluster bootstrap intervals for CzechLynx reviewed pairs. Component-group intervals are diagnostic when sparse, and identity-cluster bootstrap is blocked until resolved identity labels are available.

## Algorithm Steps

1. Build strong descriptor candidate queues with MegaDescriptor and DINOv2 context.
2. Extract image evidence, pair comparability, descriptor-conflict, and source/domain diagnostic features.
3. Train/evaluate reviewability models on CzechLynx known-ID reviewed pairs.
4. Choose empirical calibration thresholds for selective evidence routing.
5. Report calibration/evaluation risk-coverage and cluster-aware uncertainty.
6. Allocate review budget by maximizing predicted admissible evidence under a predicted-risk constraint.
7. Validate label reliability with an external blind-review packet and report disagreement appendices.
8. Keep Bobcat outputs as unlabeled transfer-stress/workflow diagnostics.

## Claim Status Counts

`{'allowed': 4, 'allowed_with_caveat': 4, 'blocked': 6, 'exploratory': 2}`

## Allowed Claims

- `allowed_selective_evidence_inference_frame`: PF-ERI governs whether retrieved candidate pairs are evidence-admissible and review-ready. Key evidence: formal target=maximize accepted-pair coverage subject to selective evidence risk
- `allowed_descriptor_controlled_reviewability_signal`: On the CzechLynx reviewed validation set, PF-ERI evidence features improve reviewability prediction after descriptor retrieval. Key evidence: descriptor_only_AUROC=0.5852218181818182; quality_only_AUROC=0.7250036363636364; pf_eri_evidence_only_AUROC=0.7797818181818181; descriptor_plus_pf_eri_AUROC=0.7986909090909091
- `allowed_descriptor_stratified_reporting`: The signal is observed in both descriptor-family queues, with descriptor-specific calibration caveats. Key evidence: MegaDescriptor_full_AUROC=0.8166580041580042; DINOv2_full_AUROC=0.8054147341171395; warnings=megadescriptor_l_384:any_model_weak_calibration_ece=warning; dinov2_vitl14:alpha_0_15_calibration_selective_risk=risk_gt_alpha_or_not_estimable
- `allowed_empirical_selective_router`: Empirical CzechLynx calibration/evaluation risk-coverage routing is supported. Key evidence: alpha=0.15 calibration_risk=0.14583333333333334; evaluation_risk=0.037037037037037035; evaluation_coverage=0.3127413127413127; finite_sample_status=empirical_only_upper_bound_exceeds_alpha
- `allowed_cluster_uncertainty_report`: Report cluster-aware uncertainty as validation uncertainty for CzechLynx reviewed pairs. Key evidence: alpha_0.15_selective_risk=0.07751937984496124 [0.0362206585096886, 0.13048020667122556]; cluster_count=221
- `allowed_blind_reliability_supported_labels`: Use blind reliability-supported reviewability labels for CzechLynx model validation. Key evidence: reviewer1_n=280; reviewer1_binary_kappa=0.859305; reviewer1_reason_agreement=0.80597; reviewer2_n=280; reviewer2_binary_kappa=0.785098; reviewer2_reason_agreement=0.736318; reviewer2_provenance=INDEPENDENT_EXTERNAL_BLIND_REVIEW_CONFIRMED
- `allowed_nonlinear_sensitivity_partial`: Report nonlinear sensitivity only for estimable features and mark constant features as design/data limitations. Key evidence: body_part_overlap_score=nonlinear_or_nonmonotonic_pattern; cross_descriptor_agreement_score=monotonic_supported_sparse_bin_caveat; night_or_motion_blur_risk=not_estimable_constant_feature; source_domain_shift_score=not_estimable_constant_feature; viewpoint_side_compatibility=not_estimable_constant_feature; visible_pattern_area_score=not_estimable_constant_feature
- `allowed_predicted_risk_budget_optimization`: PF-ERI supports predicted-risk constrained review-budget allocation. Key evidence: alpha=0.15 B=100 PF-ERI selected=100 mean_predicted_risk=0.08859433178833984 empirical_risk=0.06; descriptor_unconstrained_predicted_risk=0.1818128331742451

## Exploratory Claims

- `exploratory_component_risk_decomposition`: Use risk families as component attributions and motivation for reason-label enrichment. Caveat: Reason-label enrichment remains required for stronger explanation claims.
- `exploratory_bobcat_transfer_workflow`: Bobcat is an unlabeled transfer-stress/workflow allocation analysis. Caveat: Do not report Bobcat identity metrics until labels exist.

## Blocked Claims

- `blocked_new_descriptor`: prohibit `new descriptor; new embedding; replaces MegaDescriptor/DINOv2`. Safe wording: PF-ERI is downstream of descriptors.
- `blocked_automatic_identity_assignment`: prohibit `automatic ID; individual recognition; assigns identity`. Safe wording: PF-ERI routes candidate pairs for review.
- `blocked_bobcat_identity_metrics`: prohibit `Bobcat identity accuracy; Bobcat mAP; Bobcat top-k`. Safe wording: Bobcat is workflow/transfer-stress only.
- `blocked_source_heldout_causal_domain_generalization`: prohibit `causal domain generalization proven; source-held-out guarantee`. Safe wording: Source/domain results are diagnostics and future validation targets.
- `blocked_validated_reason_classification`: prohibit `validated reason classifier; proven explanation classes`. Safe wording: Risk decomposition is component attribution.
- `blocked_unqualified_distribution_free_claim`: prohibit `distribution-free guarantee across Bobcat/domain shift`. Safe wording: Use empirical calibration/evaluation risk-coverage language with stated assumptions.

## Methods Assumptions

- `target_definition` (locked): The model predicts evidence admissibility/reviewability, not identity.
- `strong_descriptor_position` (locked): PF-ERI operates after strong descriptor retrieval.
- `risk_coverage` (empirical_only): Report empirical calibration/evaluation risk separately from finite-sample diagnostics.
- `uncertainty` (reportable_with_scope): Use cluster-aware uncertainty for CzechLynx reviewability only.
- `budget_optimization` (predicted_risk_only): Human labels are reserved for post-selection empirical audits.
- `reason_labels` (blind_reliability_supported_bounded): Reason labels are blind reliability-supported for reviewability annotation; mechanistic explanation remains component attribution.

## Required Limitation Paragraph

Current evidence supports PF-ERI as a pair-level evidence governance layer for CzechLynx reviewed candidate pairs with blind reliability-supported reviewability labels. Finite-sample distribution-free claims, Bobcat identity metrics, source-held-out causal domain generalization, and complete validated mechanism explanations remain blocked until the corresponding labels and calibration designs exist.
