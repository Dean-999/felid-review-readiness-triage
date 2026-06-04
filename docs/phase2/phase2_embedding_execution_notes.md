# Phase 2 Embedding Execution Notes

## Purpose

This document records the fixed embedding baseline for the CzechLynx pilot Phase 2 similarity measurement step.

Embeddings are used only as validation signals for review-readiness analysis. They are not the project's final product and do not identify individual animals.

## Baseline Used

- Model: torchvision ResNet-50
- Weights: `ResNet50_Weights.IMAGENET1K_V2`
- Feature: penultimate pooled feature vector before the final classification layer
- Expected embedding dimension: 2048
- Loading policy: cached-only pretrained weights; no automatic download during execution

## Model Source

- Library: `torchvision.models.resnet50`
- Pretraining source: ImageNet pretrained weights distributed through torchvision
- Use in this project: fixed feature extractor only

## Preprocessing

The extraction script uses the official preprocessing transform attached to `ResNet50_Weights.IMAGENET1K_V2`.

Images are opened from neutral pilot review paths, converted to RGB, transformed by the torchvision weights transform, and passed through the model in evaluation mode.

## Run Date

- Planned/initial execution date: 2026-06-04

## Device

The extraction script selects an available device in this order:

1. CUDA
2. Apple MPS
3. CPU

The selected device is printed in the extraction summary.

## Outputs Generated

- `data/interim/czechlynx/czechlynx_pilot_embeddings.parquet`
- `data/interim/czechlynx/czechlynx_pair_similarities.csv`

These files are generated local data artifacts and should not be committed.

## Explicit Boundaries

- No model training was performed.
- No model fine-tuning was performed.
- No CzechLynx labels were used to train or tune the embedding model.
- No raw data were modified.
- No final scientific claims should be made from embeddings alone.
- Embeddings are used only as a validation signal for the review-readiness triage workflow.
