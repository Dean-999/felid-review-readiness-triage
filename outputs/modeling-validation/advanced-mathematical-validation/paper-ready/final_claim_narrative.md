# Final Claim Narrative

## Core Result

On the CzechLynx reviewed validation set, PF-ERI evidence features improve reviewability prediction after descriptor retrieval.

Key model evidence: descriptor_only_AUROC=0.5852218181818182; quality_only_AUROC=0.7250036363636364; pf_eri_evidence_only_AUROC=0.7797818181818181; descriptor_plus_pf_eri_AUROC=0.7986909090909091.

## Label Reliability

Use blind reliability-supported reviewability labels for CzechLynx model validation.

Key reliability evidence: reviewer1_n=280; reviewer1_binary_kappa=0.859305; reviewer1_reason_agreement=0.80597; reviewer2_n=280; reviewer2_binary_kappa=0.785098; reviewer2_reason_agreement=0.736318; reviewer2_provenance=INDEPENDENT_EXTERNAL_BLIND_REVIEW_CONFIRMED.

Reviewer 2 provenance correction: `outputs/modeling-validation/blind-reliability-packet/external-reviews/external_reviewer_2/provenance_correction.md`.

## Main Result Table

Paper-ready CSV: `outputs/modeling-validation/advanced-mathematical-validation/paper-ready/main_model_result_table.csv`

## Confidence and Limitations Appendix

Paper-ready CSV: `outputs/modeling-validation/advanced-mathematical-validation/paper-ready/final_confidence_limitations_table.csv`
Markdown appendix: `outputs/modeling-validation/advanced-mathematical-validation/paper-ready/final_confidence_limitations.md`

## Allowed Claim Wording

- `allowed_selective_evidence_inference_frame`: PF-ERI governs whether retrieved candidate pairs are evidence-admissible and review-ready.
- `allowed_descriptor_controlled_reviewability_signal`: On the CzechLynx reviewed validation set, PF-ERI evidence features improve reviewability prediction after descriptor retrieval.
- `allowed_descriptor_stratified_reporting`: The signal is observed in both descriptor-family queues, with descriptor-specific calibration caveats.
- `allowed_empirical_selective_router`: Empirical CzechLynx calibration/evaluation risk-coverage routing is supported.
- `allowed_cluster_uncertainty_report`: Report cluster-aware uncertainty as validation uncertainty for CzechLynx reviewed pairs.
- `allowed_blind_reliability_supported_labels`: Use blind reliability-supported reviewability labels for CzechLynx model validation.
- `allowed_nonlinear_sensitivity_partial`: Report nonlinear sensitivity only for estimable features and mark constant features as design/data limitations.
- `allowed_predicted_risk_budget_optimization`: PF-ERI supports predicted-risk constrained review-budget allocation.

## Blocked Claim Wording

- `blocked_new_descriptor`: do not claim `new descriptor; new embedding; replaces MegaDescriptor/DINOv2`.
- `blocked_automatic_identity_assignment`: do not claim `automatic ID; individual recognition; assigns identity`.
- `blocked_bobcat_identity_metrics`: do not claim `Bobcat identity accuracy; Bobcat mAP; Bobcat top-k`.
- `blocked_source_heldout_causal_domain_generalization`: do not claim `causal domain generalization proven; source-held-out guarantee`.
- `blocked_validated_reason_classification`: do not claim `validated reason classifier; proven explanation classes`.
- `blocked_unqualified_distribution_free_claim`: do not claim `distribution-free guarantee across Bobcat/domain shift`.

## Required Boundary

PF-ERI is evaluated as a post-retrieval evidence-admissibility and review-routing layer. It does not assign identity, replace strong descriptors, validate Bobcat identity accuracy, or provide unqualified distribution-free risk guarantees across domain shift.
