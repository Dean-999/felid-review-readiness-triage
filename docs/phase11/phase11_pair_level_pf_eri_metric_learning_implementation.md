# Phase 11 Pair-Level PF-ERI Metric-Learning Implementation

## Implementation Scope

Phase 11 implements the first pair-level PF-ERI metric-learning scaffold. It creates a deterministic pair reliability table and Colab training scripts that can test whether pair-level PF-ERI weights help supervised contrastive learning.

This phase is engineering preparation plus audits only. No local training is run.

## Created Components

- `scripts/build_phase11_pair_level_pf_eri_table.py`
- `scripts/audit_phase11_pair_level_pf_eri_table.py`
- `scripts/audit_phase11_training_package.py`
- `colab/phase11_metric_learning/train_phase11_pair_weighted_metric_learning.py`
- `colab/phase11_metric_learning/evaluate_phase11_retrieval.py`
- `colab/phase11_metric_learning/run_phase11_one_epoch.py`
- Four Phase 11 config files under `colab/phase11_metric_learning/`

## Experiment Groups

The package supports:

- `C3_quality_proxy_matched_identity`
- `H3_pf_eri_quality_hybrid_matched_identity`
- `P11_positive_pair_weighting`
- `P11_positive_weighting_negative_reliability_control`

The two P11 groups use the H3 base image set. This isolates the loss-weighting change from image-selection changes.

## Training Logic

The training script uses fixed MegaDescriptor embeddings and a small projection head. It does not fine-tune an image backbone.

Loss modes:

- `uniform_pair_weight`: baseline supervised contrastive loss.
- `positive_pair_weighting`: positive-pair loss terms are weighted by `pair_reliability_score`.
- `positive_weighting_negative_reliability_control`: positive-pair weighting plus downweighting of unreliable hard negatives.

## Evaluation Logic

The evaluation script reports held-out retrieval metrics:

- `mAP`
- `MRR`
- `top1_accuracy`
- `top5_accuracy`
- `false_top1_rate`
- `false_candidate_burden`
- `query_coverage`
- `candidate_retention`
- `valid_query_count`
- `test_image_count`

## Claim Boundary

Phase 11 can only justify Colab Stage 1 testing. It cannot support a scientific claim unless P11 methods later outperform matched random and quality-proxy controls under held-out split evaluation without query-coverage collapse or worse false-candidate burden.
