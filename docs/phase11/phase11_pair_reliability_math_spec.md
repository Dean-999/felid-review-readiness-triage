# Phase 11 Pair-Level PF-ERI Reliability Math Specification

## Purpose

Phase 11 moves PF-ERI from image-level selection into pair-level metric-learning support. This is necessary because patterned-felid Re-ID is a pairwise retrieval problem: two individually usable images can still be weak evidence if their sides, viewpoint, or visible patterns are not comparable.

This specification defines the first rule-based pair reliability table. It is not a learned model and not a claim that PF-ERI improves Re-ID.

## Inputs

Primary training rows come from:

`outputs/czechlynx/phase10_lite/phase10_lite_plus_matched_training_manifest_k3.csv`

Visual factor annotations come from:

`data/labels/czechlynx/czechlynx_mechanism_visual_factors_full_annotated.csv`

Fixed descriptor support comes from:

`outputs/czechlynx/phase4/czechlynx_phase4c_megadescriptor_embeddings.csv`

## Pair Components

For image pair `(a, b)`, component scores are in `[0, 1]`.

- `side_comparability_score`: same visible flank and weaker side-evidence quality.
- `pattern_pair_score`: `min(pattern_visibility_a, pattern_visibility_b)`.
- `blur_pair_score`: `min(blur_score_a, blur_score_b)`.
- `occlusion_pair_score`: `min(occlusion_score_a, occlusion_score_b)`.
- `body_visibility_pair_score`: `min(body_fraction_score_a, body_fraction_score_b)`.
- `viewpoint_compatibility_score`: penalizes frontal/rear and silhouette-only evidence.

The weaker-image minimum rule is intentional. A pair cannot be strong Re-ID evidence if one member lacks comparable individual-pattern evidence.

## Formula

```text
pair_reliability_score =
  0.30 * side_comparability_score
+ 0.25 * pattern_pair_score
+ 0.15 * blur_pair_score
+ 0.10 * occlusion_pair_score
+ 0.10 * body_visibility_pair_score
+ 0.10 * viewpoint_compatibility_score
```

These weights are pre-specified and interpretable. They are not universal species weights.

## Pair Weights

For same-identity pairs:

```text
positive_pair_weight = pair_reliability_score
negative_pair_weight = 0
```

For different-identity pairs:

```text
positive_pair_weight = 0
negative_pair_weight = 1
```

For unreliable hard negatives:

```text
hard_negative_flag = true
negative_pair_weight = 0.25
```

Hard negatives are defined as different-identity pairs that are in the top decile of descriptor similarity but have pair reliability at or below `0.40`. This is a conservative first control for forcing the model to over-learn visually non-comparable but descriptor-similar pairs.

## Boundaries

This table supports metric-learning experiments. It does not identify animals, does not create a new descriptor, does not validate clouded leopard or marbled cat deployment, and does not show scientific success until held-out training comparisons beat matched random and quality-proxy controls.
