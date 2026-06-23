# Phase 9D Metric Learning Colab Package

This package prepares a controlled Colab experiment for PF-ERI-selected and PF-ERI-weighted metric learning.

It does not prove that PF-ERI improves Re-ID learning. It only defines the experiment needed to test that claim.

## Required Uploads

Upload or mount the repository folder containing:

- `outputs/czechlynx/phase9/pf_eri_metric_learning_prep/phase9d_image_training_manifest_internal.csv`
- `outputs/czechlynx/phase4/czechlynx_phase4c_megadescriptor_embeddings.csv`
- `outputs/czechlynx/phase4/czechlynx_phase4c_resnet50_embeddings.csv`
- image files referenced by `image_path_internal`

Do not upload delayed second-review files.

## Experiment Groups

- `A_all_images_baseline`
- `B_random_same_size_baseline`
- `C_quality_only_selected_baseline`
- `D_pf_eri_selected_training`
- `E_pf_eri_weighted_training`
- `F_pf_eri_reranking_without_training_reference`

## Required Rule

Do not claim success from training loss. Only held-out retrieval metrics count.

## Expected Outputs

Colab should export:

- `phase9d_colab_training_metrics.csv`
- `phase9d_colab_retrieval_metrics.csv`
- `phase9d_colab_model_comparison.csv`
- `phase9d_colab_failure_cases.csv`
- `phase9d_colab_checkpoints_manifest.csv`

Local import destination:

```text
outputs/czechlynx/phase9/pf_eri_metric_learning_results/
```

Do not commit checkpoints, raw images, data folders, or local output CSVs.
