# Phase 13E RQ4 Failure Diagnosis and Upgrade Plan

Date: 2026-06-18

## Why Phase 13D Underperformed

Phase 13D did not fail because PF-ERI has no signal. It failed because the current learning setup is too blunt for strong fixed descriptors.

The key result is:

```text
All trained projection-head policies underperformed the raw fixed embedding reference across 10 split/descriptor runs.
```

This means the current RQ4 implementation cannot support the claim:

```text
PF-ERI improves metric learning.
```

It can only support the narrower claim:

```text
PF-ERI pair weights can be turned into an auditable training-control mechanism, but the current projection-head objective damages retrieval geometry.
```

## Problems We Should Not Hide

### 1. Plain projection head probably destroys useful descriptor geometry

MegaDescriptor and ResNet50 embeddings are already strong retrieval spaces. A randomly initialized MLP projection head trained for a few epochs can rotate, compress, and distort that space.

Current model:

```text
z = normalize(MLP(x))
```

This discards the raw embedding at evaluation time.

Why this is dangerous:

- If the raw descriptor is already strong, a small dataset may not contain enough signal to relearn the same geometry.
- The projection head may optimize sampled pair loss but reduce global retrieval quality.
- This matches the observed result: training loss decreases, but held-out retrieval gets worse.

External-method lesson:

Contrastive-learning papers commonly use a projection head as a training-space device, while the representation before or outside the projection head can be the stronger evaluation representation. This supports treating a plain projection head as risky for final retrieval unless it is residual or geometry-regularized.

### 2. One margin is not valid across descriptors

Objective diagnostic on calibration pairs:

```text
MegaDescriptor, margin=0.35:
  negative active fraction = 0.0388

ResNet50, margin=0.35:
  negative active fraction = 0.8491
```

This means the same loss is training almost only positives for MegaDescriptor, but training mostly negatives for ResNet50.

That is a logic problem, not a biological result.

Solution:

Use descriptor-specific or split-calibrated margins:

```text
margin = quantile(raw_negative_distance, q)
```

Candidate q values:

```text
0.10, 0.25, 0.50
```

or target a fixed active negative fraction:

```text
active negative fraction = 10-30%
```

### 3. Positive and negative forces are not balanced by effective gradient

The sampler draws roughly all available positives and 1500 negatives, but the hinge loss only activates negatives inside the margin. For MegaDescriptor, most sampled negatives have zero loss.

This creates unstable effective training:

```text
sampled negative count != active negative count
```

Solution:

Report and control:

- active negative fraction;
- positive loss share;
- negative loss share;
- weighted active negative count;
- unsafe active negative count.

If these are not controlled, the result is hard to interpret.

### 4. PF-ERI conflict-aware negative control may remove useful hard negatives

The current conflict-aware policy downweights unsafe hard negatives to 0.35.

This is theoretically sensible if those pairs are unreliable. But in metric learning, some hard negatives are useful. If the unsafe detector is too broad, it can reduce the very signal needed to sharpen identity boundaries.

Observed pattern:

```text
pf_eri_conflict_aware slightly improves top-1 vs random in some runs,
but worsens mAP and false-candidate burden on average.
```

Possible reason:

It softens too many high-similarity negatives without replacing them with reliable hard negatives.

Solution:

Split negatives into three groups:

```text
ordinary negative: weight 1.0
reliable hard negative: weight > 1.0 or keep 1.0
unsafe hard negative: weight < 1.0
```

PF-ERI should not simply suppress hard negatives. It should separate reliable hard negatives from unreliable hard negatives.

### 5. Current positive weighting may overlap too much with quality-control

Phase 13 showed learned PF-ERI often overlaps with quality-control. Phase 13D continues that pattern:

```text
pf_eri_positive vs quality-control mean delta mAP = -0.0018
positive delta fraction = 0.2
```

This means PF-ERI-positive weighting is not yet providing enough independent training signal beyond quality.

Solution:

Make RQ4 more pair-specific:

- emphasize side/flank comparability;
- use descriptor-evidence conflict;
- use reciprocal and margin confidence;
- distinguish positive admissibility from image clarity;
- avoid collapsing PF-ERI into generic quality.

### 6. Evaluation currently measures global retrieval, not risk-controlled retrieval after training

Phase 13D evaluates raw projected similarity top-k retrieval.

But the project’s stronger claim is risk-aware Re-ID enhancement. It may be possible that PF-ERI training does not improve global mAP but improves:

- high-admissibility query subsets;
- conflict-heavy query subsets;
- false top-1 risk at fixed coverage;
- false-candidate burden after PF-ERI reranking;
- calibration of candidate reliability.

Solution:

Phase 13E should evaluate:

```text
raw retrieval
projection retrieval
projection + PF-ERI reranking
risk-coverage after projection
admissibility-stratified retrieval
conflict-stratified retrieval
```

### 7. Split leakage is unlikely but still needs explicit audit

Current Phase 13D uses calibration pairs for training and evaluation query tokens for evaluation.

Potential concern:

- if the same identity appears in both calibration and evaluation, this is not held-out-identity metric learning;
- if Phase 12 splits are query/candidate splits rather than strict identity splits, RQ4 claims must be limited.

Solution:

Add an explicit identity-disjoint audit:

```text
train identities ∩ evaluation identities = empty
```

If not empty, call the experiment a calibration/evaluation candidate split, not held-out identity learning.

This is a major claim-boundary issue and should be checked before stronger RQ4 language.

Follow-up audit result:

```text
The current Phase 13D split is not identity-disjoint.
Across split IDs 1-5 and both descriptors, train/evaluation identity overlap is approximately 0.98-1.00 of evaluation identities.
```

Therefore Phase 13D must be interpreted as:

```text
candidate/evidence split sanity testing
```

not:

```text
held-out identity metric-learning validation
```

This is the most important claim-boundary issue found in the diagnosis.

Solution:

Phase 13E must create a strict identity-disjoint training/evaluation protocol before any strong RQ4 claim:

```text
train identities ∩ evaluation identities = empty
```

If there are too few images per identity for strict held-out identity training, use:

```text
identity-disjoint evaluation for retrieval;
within-train identities only for pair-loss fitting;
singletons retained only as evaluation distractors or gallery noise.
```

## External Lessons Used

The external method pattern supports the upgrade:

1. Projection heads can help contrastive training but are not automatically the best final retrieval embedding.
2. Metric learning is sensitive to false negatives and noisy hard negatives.
3. Hard negative mining helps only when negatives are reliable.
4. Strong pretrained embeddings should be adapted conservatively, often with residual, adapter, or regularized corrections rather than full replacement.
5. Wildlife Re-ID baselines such as MegaDescriptor are already strong; a learning contribution must beat raw descriptor and matched controls, not just produce a trained model.

## Recommended Phase 13E Model

### A. Residual Reliability Head

Replace:

```text
z = normalize(MLP(x))
```

with:

```text
delta = MLP(x)
z = normalize(x_projected + alpha * delta)
```

For dimensions:

- if projection dimension equals input dimension, use direct residual;
- otherwise use a learned linear bottleneck and compare against a matched raw linear baseline.

Recommended first version:

```text
projection_dim = input_dim
alpha initialized at 0.05 or 0.10
alpha learnable but clipped or regularized
```

### B. Geometry Preservation

Add a regularization term:

```text
L_total = L_pair_weighted + lambda_geometry * L_geometry
```

where:

```text
L_geometry = mean((cos(z_i, z_j) - cos(x_i, x_j))^2)
```

computed on sampled training pairs or mini-batch pairs.

Purpose:

```text
Do not damage the descriptor geometry unless pair evidence strongly justifies it.
```

### C. Descriptor-Specific Margin Calibration

Replace fixed margin:

```text
margin = 0.35
```

with:

```text
margin = quantile(raw_negative_distance, q)
```

Default:

```text
q = 0.25
```

Report active negative fraction for every run.

### D. Reliable-vs-Unsafe Hard Negative Decomposition

Current negative policy:

```text
unsafe hard negative -> 0.35
all other negatives -> 1.0
```

Upgrade:

```text
ordinary negative -> 1.0
reliable hard negative -> 1.0 to 1.25
unsafe hard negative -> 0.25 to 0.50
```

This avoids treating all hard negatives as bad.

### E. Stronger Evaluation Gates

Phase 13E should require:

1. No worse than raw fixed embedding within a small tolerance:

```text
delta mAP >= -0.005
```

2. Better than quality-control or random-control on at least one primary metric:

```text
mAP, top-1, false top-1, or false burden
```

3. No query coverage loss.

4. Improvement should be repeated across descriptors or clearly descriptor-specific.

## Immediate Implementation Plan

1. Add diagnostic outputs to Phase 13D/13E:
   - raw positive/negative distance distribution;
   - margin value;
   - active negative fraction;
   - positive/negative loss share;
   - identity overlap between train/evaluation.

2. Implement model modes:
   - `identity`
   - `plain_projection`
   - `residual_projection`
   - `residual_projection_geometry`

3. Run a small local grid:

```text
splits: 1,2,3
descriptors: MegaDescriptor, ResNet50
margin_quantile: 0.10, 0.25, 0.50
lambda_geometry: 0.1, 1.0, 5.0
alpha_init: 0.05, 0.10
```

4. Only if residual models pass the raw-reference gate, expand to:

```text
5-10 splits
3 random seeds
longer epochs
```

5. Use Colab only for the expanded grid or full metric-learning phase.

## Current Decision

Do not claim RQ4 success yet.

Do not abandon RQ4.

Proceed to Phase 13E because Phase 13D identified a correctable modeling failure:

```text
The training objective must preserve strong descriptor geometry while allowing PF-ERI to make small reliability-aware corrections.
```
