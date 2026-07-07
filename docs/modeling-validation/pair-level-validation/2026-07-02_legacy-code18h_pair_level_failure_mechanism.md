# legacy-code18h Pair-Level Failure Mechanism Analysis

Date: 2026-07-02

## Question

The strong-baseline legacy-code18 result showed that PF-ERI review routing can reduce
MegaDescriptor evaluation-split top-5 false-candidate burden. legacy-code18h asks the
mechanistic follow-up question:

```text
Which pair-level evidence signals explain where strong descriptor queues become
risky, and what operating tradeoff does PF-ERI create at fixed positive
retention?
```

This is not another descriptor benchmark. It is a mechanism analysis of
post-retrieval pair evidence.

## Method

Inputs:

- `outputs/legacy-code18/legacy-code18d_strong_pf_eri_pair_features/megadescriptor_l_384/`
- `outputs/legacy-code18/legacy-code18d_strong_pf_eri_pair_features/dinov2_vitl14/`

For each descriptor, legacy-code18h produced:

- conflict/evidence enrichment diagnostics;
- fixed positive-retention operating points;
- 50 high-similarity false-candidate samples and 50 high-similarity same-ID
  controls for later visual review.

Statistical approach:

- binary outcome: `same_identity == no`;
- effect size: false-rate risk difference and odds ratio;
- uncertainty: bootstrap confidence interval for risk difference;
- no normality assumption is used for these binary candidate-pair diagnostics.

Outputs:

```text
outputs/legacy-code18/legacy-code18h_pair_level_failure_mechanism/{descriptor}/
```

## Enrichment Results

Evaluation split:

| Descriptor | Signal | Pair count | False rate | Odds ratio vs absent | Risk difference | 95% CI |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| MegaDescriptor | high similarity | 2,591 | 0.0776 | 0.049 | -0.5569 | [-0.5705, -0.5438] |
| MegaDescriptor | high conflict | 2,256 | 0.1144 | 0.081 | -0.4993 | [-0.5144, -0.4830] |
| MegaDescriptor | low admissibility | 1,104 | 0.9438 | 16.163 | +0.4360 | [+0.4196, +0.4513] |
| MegaDescriptor | high similarity + high conflict | 2,135 | 0.0721 | 0.049 | -0.5438 | [-0.5576, -0.5296] |
| MegaDescriptor | high similarity + low admissibility | 2 | 1.0000 | 4.268 | +0.4605 | [+0.4524, +0.4685] |
| DINOv2 | high similarity | 3,712 | 0.0622 | 0.028 | -0.6429 | [-0.6542, -0.6316] |
| DINOv2 | high conflict | 3,362 | 0.1005 | 0.054 | -0.5747 | [-0.5879, -0.5614] |
| DINOv2 | low admissibility | 1,027 | 0.9474 | 16.540 | +0.4282 | [+0.4123, +0.4438] |
| DINOv2 | high similarity + high conflict | 3,156 | 0.0554 | 0.028 | -0.6218 | [-0.6333, -0.6103] |
| DINOv2 | high similarity + low admissibility | 0 | 0.0000 | 0.824 | -0.5482 | not estimable |

Interpretation:

- The strongest false-risk mechanism is **low admissibility**, not generic high
  conflict.
- Low-admissibility pairs are overwhelmingly false candidates in both
  descriptors: false rate 0.9438 for MegaDescriptor and 0.9474 for DINOv2.
- High similarity, and even high similarity plus high conflict under the current
  score definition, is not a false-risk signal here. It is enriched for true
  same-ID candidates in the top-k candidate graph.
- Therefore the scientific story should not say "high conflict always means
  false." The sharper story is:

```text
PF-ERI identifies a low-admissibility failure mode that strong descriptor
similarity alone does not expose cleanly.
```

## Fixed Positive-Retention Operating Points

Evaluation split, PF-ERI review router:

| Descriptor | Target positive retention | Threshold | Retained pairs | Positive retention | False retention | False removed | Precision retained |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| MegaDescriptor | 0.90 | 0.4669 | 10,771 | 0.9001 | 0.5452 | 0.4548 | 0.5849 |
| MegaDescriptor | 0.95 | 0.3914 | 12,346 | 0.9501 | 0.6945 | 0.3055 | 0.5386 |
| MegaDescriptor | 0.99 | 0.2883 | 14,349 | 0.9901 | 0.9046 | 0.0954 | 0.4830 |
| DINOv2 | 0.90 | 0.4989 | 10,820 | 0.9001 | 0.5566 | 0.4434 | 0.5713 |
| DINOv2 | 0.95 | 0.4189 | 12,345 | 0.9501 | 0.6985 | 0.3015 | 0.5286 |
| DINOv2 | 0.99 | 0.2780 | 14,464 | 0.9901 | 0.9198 | 0.0802 | 0.4701 |

Descriptor-only comparison:

| Descriptor | Target positive retention | False retention | False removed | Precision retained |
| --- | ---: | ---: | ---: | ---: |
| MegaDescriptor | 0.90 | 0.5668 | 0.4332 | 0.5754 |
| MegaDescriptor | 0.95 | 0.7194 | 0.2806 | 0.5299 |
| MegaDescriptor | 0.99 | 0.9199 | 0.0801 | 0.4788 |
| DINOv2 | 0.90 | 0.5759 | 0.4241 | 0.5630 |
| DINOv2 | 0.95 | 0.7288 | 0.2712 | 0.5180 |
| DINOv2 | 0.99 | 0.9358 | 0.0642 | 0.4658 |

Interpretation:

- At 90% positive retention, PF-ERI review routing removes more false
  candidates than descriptor-only for both descriptors.
- The gain is modest but directionally consistent:
  - MegaDescriptor: false removed 0.4548 vs 0.4332.
  - DINOv2: false removed 0.4434 vs 0.4241.
- This supports PF-ERI as a review-burden/risk-routing layer, not a replacement
  ranker.

## Failure Samples

Each descriptor has a 100-row review sample:

```text
legacy-code18h_failure_case_sample.csv
```

Composition:

- 50 high-similarity false candidates prioritized for mechanism review;
- 50 high-similarity same-ID controls.

These samples are not new labels. They are a targeted packet for visual
inspection or future human-review agreement testing.

## Claim Update

Supported:

```text
Low pair-level admissibility is a strong false-candidate risk signal in both
MegaDescriptor and DINOv2 candidate queues. PF-ERI review routing can operate at
fixed positive-retention levels while removing a modestly larger share of false
candidates than descriptor-only ranking.
```

Not supported:

```text
High descriptor-evidence conflict alone is not shown here to be a false-risk
signal. In the current score geometry, high-similarity/high-conflict regions are
mostly same-ID enriched.
```

Implication:

```text
The next model refinement should preserve the useful review-router effect but
separate low-admissibility risk from high-similarity/high-confidence true-match
regions more cleanly.
```

## Recommended Next Step

legacy-code18i should focus on targeted visual review and feature refinement:

1. Build a contact-sheet or Streamlit packet from the legacy-code18h 100-row samples.
2. Ask a human reviewer to label pair-level reviewability, not identity:
   `review_ready`, `low_evidence`, `non_comparable`, or `uncertain`.
3. Compare human reviewability against:
   - low admissibility;
   - PF-ERI review score;
   - descriptor-only rank;
   - same-ID/different-ID ground truth.
4. Refine conflict/admissibility so high-confidence true matches are not
   mislabeled as generic conflict risk.

This would connect the current statistical mechanism result to the central
scientific claim: PF-ERI is an evidence-governance layer for pair-level review
readiness.
