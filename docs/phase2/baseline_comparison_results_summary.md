# Phase 2 Baseline Comparison Results Summary

## Purpose

This document summarizes the CzechLynx pilot comparison between two fixed pretrained embedding baselines:

1. **ResNet50_ImageNet1K_V2** — a generic ImageNet baseline already completed locally.
2. **MegaDescriptor_S_224** — a wildlife-specialized fixed pretrained baseline run in Colab.

The goal is to test whether a wildlife-specialized baseline improves same/different pairwise separation relative to the generic baseline, using embeddings as measurement signals for review-readiness evaluation.

No model training or fine-tuning was performed. Embeddings are measurement signals only, not individual identification decisions.

## Overall Comparison

| Baseline | Total Pairs | Same Pairs | Different Pairs | Same Mean | Different Mean | Gap | ROC-AUC |
|---|---:|---:|---:|---:|---:|---:|---:|
| ResNet50_ImageNet1K_V2 | 400 | 100 | 300 | 0.579955 | 0.493990 | 0.085966 | 0.618667 |
| MegaDescriptor_S_224 | 400 | 100 | 300 | 0.235992 | 0.118512 | 0.117479 | 0.690400 |

## Interpretation

MegaDescriptor-S-224 improves same/different separation compared with ResNet-50 on this CzechLynx pilot:

- **ROC-AUC improvement:** +0.071733 (0.690400 − 0.618667).
- **Same-minus-different gap improvement:** +0.031513 (0.117479 − 0.085966).
- **Relative gap increase:** approximately 36.7% (0.031513 / 0.085966).

This strengthens Q1 from partial/mixed support to **moderate pilot-level support** for the idea that a wildlife-specialized fixed baseline can provide stronger pairwise measurement separation than a generic ImageNet baseline in this pilot.

Important caveats:

- **Absolute cosine values should not be directly compared across models** because embedding scales differ. AUC, gap, and within-model threshold behavior are the meaningful comparisons.
- The result remains **pilot-level evidence**, not final proof.
- The `ready_ready` readiness group shows a strong signal under MegaDescriptor but remains sparse (3 same-individual pairs and 7 different-individual pairs in the overall pilot design).

## Limitations

1. The analysis uses only the 200-image CzechLynx pilot.
2. `ready_ready` pairs are sparse, limiting subgroup claims.
3. Background, encounter, and camera-trap context effects may influence similarity scores.
4. MegaDescriptor outputs were produced in Colab and require local audit before integration.
5. No field deployment readiness claim is supported by this comparison.

## Decision

Proceed to **Phase 3B** risk–coverage analysis under the MegaDescriptor-S-224 baseline, using MegaDescriptor-specific quantile thresholds rather than ResNet-50 thresholds.

## Outputs and Audit

Colab outputs are stored under:

`outputs/czechlynx/colab_megadescriptor/czechlynx_wildlife_baseline_outputs/`

Local audit script:

`scripts/audit_czechlynx_colab_megadescriptor_outputs.py`

Audit report:

`outputs/czechlynx/qc/megadescriptor_colab_output_audit.txt`

## Forbidden Claims

This comparison does not support claims that:

- the project identifies individual animals;
- MegaDescriptor is validated for field lynx Re-ID deployment;
- either baseline defines a universal felid Re-ID threshold;
- the pilot alone proves review-ready superiority in all conservation settings.
