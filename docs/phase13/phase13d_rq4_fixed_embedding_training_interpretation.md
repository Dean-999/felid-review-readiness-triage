# Phase 13D RQ4 Fixed-Embedding Training Interpretation

Date: 2026-06-18

## Question

Can simulated PF-ERI pair weighting and fixed-embedding projection-head training be combined to increase RQ4 confidence?

## Short Answer

Yes, they can be combined as a stronger evidence chain:

```text
PF-ERI pair weights define which training signals should matter.
Loss-exposure analysis shows how those weights alter admissible positives and unsafe hard negatives.
Fixed-embedding projection-head training tests whether those altered signals improve held-out retrieval.
```

However, the current Phase 13D implementation does not yet support a positive RQ4 metric-learning claim.

## What Was Implemented

Phase 13D now combines:

1. Simulated loss-exposure diagnostics from the Phase 13C pair manifest.
2. Pair-weighted fixed-embedding projection-head training.
3. Raw fixed-embedding reference evaluation.
4. Matched policy controls:
   - `descriptor_only`
   - `random_control`
   - `quality_control`
   - `pf_eri_positive`
   - `pf_eri_conflict_aware`
5. Multi-split, dual-descriptor aggregation.

The local confidence run used:

- 5 split IDs
- MegaDescriptor and ResNet50
- 10 paired split/descriptor runs
- 3 epochs per run
- 3000 maximum sampled training pairs per run

Audit status:

```text
Phase 13D RQ4 fixed-embedding training audit: PASS=28 FAIL=0
```

## Main Results

Across 10 paired split/descriptor runs:

- `quality_control` vs raw fixed embedding:
  - mean delta mAP: `-0.0319`
  - mean delta top-1: `-0.0365`

- `pf_eri_positive` vs raw fixed embedding:
  - mean delta mAP: `-0.0336`
  - mean delta top-1: `-0.0378`

- `pf_eri_conflict_aware` vs raw fixed embedding:
  - mean delta mAP: `-0.0374`
  - mean delta top-1: `-0.0362`

- `pf_eri_positive` vs quality-control:
  - mean delta mAP: `-0.0018`
  - positive delta fraction: `0.2`

- `pf_eri_conflict_aware` vs quality-control:
  - mean delta mAP: `-0.0056`
  - positive delta fraction: `0.3`

- `pf_eri_conflict_aware` vs random-control:
  - mean delta mAP: `-0.0038`
  - mean delta top-1: `+0.0012`

## Interpretation

This is a useful but not yet positive RQ4 result.

The current projection-head objective fails the raw-reference gate:

```text
All trained projection-head policies underperform the original fixed embeddings.
```

That means the present result should not be reported as:

```text
PF-ERI improves metric learning.
```

The defensible interpretation is:

```text
PF-ERI pair weights can be translated into an auditable training-control mechanism, but the current low-capacity pairwise projection objective does not preserve enough of the strong fixed descriptor geometry to improve retrieval.
```

## Why This Is Not a Downgrade

This result separates three different questions:

1. Does PF-ERI define meaningful training weights?
   - Yes, Phase 13C and Phase 13D exposure analysis show explicit positive weighting and unsafe hard-negative control.

2. Does the current projection-head objective improve retrieval?
   - No, not against raw fixed embeddings.

3. Does this falsify RQ4?
   - No. It falsifies the current small pairwise projection implementation as a sufficient RQ4 model.

The bottleneck is likely the training objective, not necessarily PF-ERI:

- The projection head may distort already strong descriptor geometry.
- The pairwise contrastive objective may overreact to sparse positive pairs.
- Three local epochs may be enough for sanity checking but not enough for stable representation learning.
- The current evaluation is stricter because raw MegaDescriptor / ResNet50 are strong references.
- PF-ERI conflict-aware negative control may protect against unsafe hard negatives but also reduce useful hard-negative pressure.

## Next Upgrade

The next RQ4 step should upgrade the learning objective, not retreat to a weaker claim.

Recommended Phase 13E:

1. Add residual projection:

```text
z = normalize(x + alpha * projection_head(x))
```

This preserves raw descriptor geometry and only learns a small reliability-aware correction.

2. Add raw-geometry regularization:

```text
loss = pair_weighted_loss + lambda * distance(projected_similarity, raw_similarity)
```

This directly addresses the current failure mode: training damages raw retrieval structure.

3. Compare three objectives:

```text
identity projection baseline
plain projection head
residual reliability head
residual reliability head + geometry regularization
```

4. Keep the same controls:

```text
random_control
quality_control
pf_eri_positive
pf_eri_conflict_aware
```

5. Success gate:

PF-ERI should only be treated as positive RQ4 evidence if it beats quality-control and random-control while matching or improving raw fixed embedding on at least one primary retrieval or risk metric.

## Colab Decision

Colab is not required for the current Phase 13D evidence.

Local CPU is enough for:

- fixed-embedding projection-head sanity checks;
- 5 split x 2 descriptor runs;
- policy-contrast summaries;
- failure diagnosis.

Colab becomes useful only for Phase 13E if we run:

- longer epoch sweeps;
- repeated random seeds;
- residual-head hyperparameter grids;
- larger batch objectives;
- eventual backbone fine-tuning.

Backbone fine-tuning should remain a later option, not the next immediate step, because it would make the contribution harder to attribute to PF-ERI rather than to backbone retraining.
