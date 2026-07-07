# legacy-code18i Human Reviewability Analysis

Date: 2026-07-02

## Question

legacy-code18i asks whether the targeted human review labels support the pair-level
PF-ERI story:

```text
Do strong-descriptor false-candidate pairs show degraded human reviewability,
and do PF-ERI pair-level scores track that degradation?
```

The outcome is human **pair reviewability**, not identity.

## Data Status

Completed review data found:

| Descriptor | Review rows | Completed | Missing | Invalid labels |
| --- | ---: | ---: | ---: | ---: |
| MegaDescriptor | 100 | 100 | 0 | 0 |
| DINOv2 | 100 | 100 | 0 | 0 |

The combined legacy-code18i reviewability set has 200 targeted pair reviews.

## Label Distribution

Labels:

| Descriptor | `review_ready` | `uncertain` | `low_evidence` | `non_comparable` |
| --- | ---: | ---: | ---: | ---: |
| MegaDescriptor | 85 | 15 | 0 | 0 |
| DINOv2 | 88 | 12 | 0 | 0 |
| Pooled | 173 | 27 | 0 | 0 |

Important caution:

```text
No low_evidence or non_comparable labels were assigned.
```

So the human-review result supports **uncertainty / reduced review readiness**
in a subset of false candidates. It does not yet prove that reviewers explicitly
classified those cases as low-evidence or non-comparable.

## Same-ID Controls vs False Candidates

The legacy-code18i MegaDescriptor packet was balanced:

- 50 high-similarity false candidates;
- 50 high-similarity same-ID controls.

Reviewability result:

| Descriptor | Group | n | Review-ready | Review-ready rate | 95% bootstrap CI |
| --- | --- | ---: | ---: | ---: | --- |
| MegaDescriptor | Same-ID controls | 50 | 50 | 1.00 | [1.00, 1.00] |
| MegaDescriptor | False candidates | 50 | 35 | 0.70 | [0.58, 0.82] |
| DINOv2 | Same-ID controls | 50 | 50 | 1.00 | [1.00, 1.00] |
| DINOv2 | False candidates | 50 | 38 | 0.76 | [0.64, 0.88] |
| Pooled | Same-ID controls | 100 | 100 | 1.00 | [1.00, 1.00] |
| Pooled | False candidates | 100 | 73 | 0.73 | not separately bootstrapped in artifact |

Contrast:

| Descriptor | Contrast | Risk difference | 95% bootstrap CI | Odds ratio | Fisher exact p |
| --- | --- | ---: | --- | ---: | ---: |
| MegaDescriptor | same-ID controls - false candidates | +0.30 | [+0.18, +0.44] | 44.10 | 1.78e-05 |
| DINOv2 | same-ID controls - false candidates | +0.24 | [+0.12, +0.36] | 32.79 | 2.31e-04 |
| Pooled | same-ID controls - false candidates | +0.27 | [+0.18, +0.36] | 75.20 | 1.96e-09 |

Interpretation:

```text
High-similarity same-ID controls were consistently review-ready, while
high-similarity false candidates contained a reproducible uncertain subset
across MegaDescriptor and DINOv2.
```

This is useful for the pair-level claim: PF-ERI is not merely rejecting all
high-similarity pairs. The same-ID controls stayed review-ready.

## PF-ERI Score Alignment

Scores were compared between `review_ready` and non-ready labels. Because all
non-ready labels were `uncertain`, this is a review-ready vs uncertain
comparison.

| Descriptor | Score | Ready mean | Uncertain mean | Difference | 95% bootstrap CI | AUC |
| --- | --- | ---: | ---: | ---: | --- | ---: |
| MegaDescriptor | PF-ERI admissibility | 0.730 | 0.669 | +0.062 | [+0.037, +0.090] | 0.871 |
| DINOv2 | PF-ERI admissibility | 0.724 | 0.681 | +0.043 | [+0.025, +0.062] | 0.814 |
| MegaDescriptor | PF-ERI review score | 0.825 | 0.775 | +0.049 | [+0.031, +0.070] | 0.845 |
| DINOv2 | PF-ERI review score | 0.819 | 0.774 | +0.045 | [+0.028, +0.061] | 0.823 |
| MegaDescriptor | Pair geometry | 0.935 | 0.775 | +0.160 | [+0.107, +0.211] | 0.879 |
| DINOv2 | Pair geometry | 0.916 | 0.789 | +0.127 | [+0.072, +0.180] | 0.808 |
| MegaDescriptor | Weakest image quality | 0.547 | 0.531 | +0.016 | [-0.005, +0.045] | 0.556 |
| DINOv2 | Weakest image quality | 0.547 | 0.541 | +0.006 | [-0.002, +0.016] | 0.585 |

Interpretation:

- PF-ERI admissibility is higher in human review-ready pairs.
- PF-ERI review score also tracks human review readiness.
- Pair geometry is the strongest visible component in both targeted samples.
- Weakest image quality alone is weak and its CI crosses zero, which supports
  the earlier control argument that PF-ERI is not merely an image-quality
  filter.
- Conflict was higher in uncertain pairs for MegaDescriptor but not DINOv2, so
  this should remain secondary. legacy-code18h already showed high conflict alone is
  not a general false-risk mechanism.

## What This Supports

Supported, with a targeted-sample boundary:

```text
In both MegaDescriptor and DINOv2 targeted review packets, human reviewability
labels align with PF-ERI pair-level admissibility/review scores. Same-ID
controls remain review-ready, while high-similarity false candidates contain
the uncertain reviewability cases.
```

This strengthens the main legacy-code18 claim:

```text
PF-ERI is a pair-level evidence-governance layer after strong descriptor
retrieval.
```

## What This Does Not Support

Do not claim:

```text
PF-ERI automatically identifies individuals.
PF-ERI has Bobcat identity accuracy.
Human reviewability labels are new identity labels.
The low-evidence/non-comparable mechanism is confirmed by legacy-code18i labels.
DINOv2 human-reviewability behavior is known.
```

The strongest careful wording is:

```text
legacy-code18i provides cross-descriptor human-review evidence that high-similarity
false-candidate subsets include lower review-readiness cases, and that PF-ERI
admissibility scores track this reviewability degradation.
```

## Next Step

1. Add a second reviewer or adjudication pass if this result will be used in a
   paper-level claim.
2. Re-run legacy-code18i analysis with reviewer
   agreement.
3. Refine PF-ERI conflict/admissibility by emphasizing geometry/admissibility
   and avoiding a simplistic "high conflict means false" narrative.

## Outputs

Analysis artifacts:

```text
outputs/legacy-code18/legacy-code18i_reviewability_analysis/megadescriptor_l_384/
outputs/legacy-code18/legacy-code18i_reviewability_analysis/dinov2_vitl14/
```

Files:

- `legacy-code18i_reviewability_analysis_ready.csv`
- `legacy-code18i_reviewability_summary.csv`
- `legacy-code18i_reviewability_crosstabs.csv`
- `legacy-code18i_reviewability_binary_contrasts.csv`
- `legacy-code18i_reviewability_score_contrasts.csv`
- `legacy-code18i_reviewability_analysis_audit.json`

Implementation:

```text
scripts/build_legacy-code18i_reviewability_analysis.py
```
