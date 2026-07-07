# legacy-code18j Full-Queue Multi-Reviewer Analysis

Date: 2026-07-03

## Question

legacy-code18j tests whether the legacy-code18i targeted-review result holds in a smaller
but broader full-queue stratified sample, with three reviewer label sets and a
more explicit not-ready reason protocol.

The endpoint remains:

```text
pair-level reviewability
```

not identity assignment.

## Data

Packet:

```text
outputs/legacy-code18/legacy-code18j_full_queue_review_packet_100/
```

Review outputs:

```text
outputs/legacy-code18/legacy-code18j_streamlit_review_100/
```

Analysis:

```text
outputs/legacy-code18/legacy-code18j_reviewer_agreement_analysis_100/
```

Design:

| Descriptor | Pairs | Reviewers | Label rows |
| --- | ---: | ---: | ---: |
| MegaDescriptor | 100 | 3 | 300 |
| DINOv2 | 100 | 3 | 300 |
| Total | 200 | 3 | 600 |

Sampling was stratified by descriptor, same/different known-ID truth, descriptor
rank bin, and PF-ERI admissibility tertile.

## Label Distribution

Majority vote:

| Descriptor | Review-ready | Not review-ready | Uncertain | Low-evidence reason |
| --- | ---: | ---: | ---: | ---: |
| MegaDescriptor | 69 | 0 | 31 | 6 reason votes |
| DINOv2 | 70 | 6 | 24 | 6 reason votes |

Reviewer-level pattern:

- MegaDescriptor reviewer1: 65 ready, 35 uncertain.
- MegaDescriptor reviewer2: 75 ready, 6 not-ready low-evidence, 19 uncertain.
- MegaDescriptor reviewer3: 69 ready, 31 uncertain.
- DINOv2 reviewer1: 69 ready, 5 not-ready low-evidence, 26 uncertain.
- DINOv2 reviewer2: 70 ready, 5 not-ready low-evidence, 25 uncertain.
- DINOv2 reviewer3: 71 ready, 5 not-ready low-evidence, 24 uncertain.

Interpretation:

```text
The revised protocol succeeded in eliciting explicit low_evidence labels, but
non_comparable remained absent.
```

So legacy-code18j supports low-evidence as a real reviewer-visible reason in this
sample, but still does not support a non-comparable mechanism.

## Reviewer Agreement

Pairwise agreement:

| Descriptor | Reviewer pair | 3-class agreement | 3-class kappa | Binary agreement | Binary kappa |
| --- | --- | ---: | ---: | ---: | ---: |
| MegaDescriptor | r1-r2 | 0.76 | 0.462 | 0.82 | 0.576 |
| MegaDescriptor | r1-r3 | 0.84 | 0.639 | 0.84 | 0.639 |
| MegaDescriptor | r2-r3 | 0.76 | 0.433 | 0.82 | 0.556 |
| DINOv2 | r1-r2 | 0.84 | 0.644 | 0.85 | 0.646 |
| DINOv2 | r1-r3 | 0.82 | 0.596 | 0.84 | 0.619 |
| DINOv2 | r2-r3 | 0.83 | 0.614 | 0.83 | 0.591 |

Interpretation:

- Agreement is acceptable but not perfect.
- DINOv2 is more stable across reviewers.
- MegaDescriptor reviewer2 is more willing to use explicit `not_review_ready`
  than reviewer1/reviewer3, reducing 3-class kappa.
- Binary review-ready vs non-ready kappa is mostly around 0.56-0.65, which is
  usable but not "excellent."

This upgrades legacy-code18i from a single-reviewer result to a multi-reviewer result,
but it does not remove all reviewer-subjectivity concerns.

## Same-ID vs False-Candidate Reviewability

Majority vote:

| Descriptor | Same-ID ready rate | False-candidate ready rate | Difference | Row-level CI |
| --- | ---: | ---: | ---: | --- |
| MegaDescriptor | 0.816 | 0.569 | +0.248 | [+0.070, +0.426] |
| DINOv2 | 0.740 | 0.660 | +0.080 | [-0.100, +0.260] |
| Pooled | not directly stratified table | not directly stratified table | +0.164 | cluster CI below |

Query-cluster sensitivity:

| Descriptor | Scope | Rows | Unique queries | Difference | Query-cluster CI |
| --- | --- | ---: | ---: | ---: | --- |
| MegaDescriptor | row-level | 100 | 91 | +0.248 | [+0.074, +0.424] |
| MegaDescriptor | dedup unordered pair | 99 | 91 | +0.244 | [+0.067, +0.421] |
| DINOv2 | row-level | 100 | 92 | +0.080 | [-0.098, +0.250] |
| DINOv2 | dedup unordered pair | 100 | 92 | +0.080 | [-0.098, +0.250] |
| Pooled | row-level | 200 | 171 | +0.164 | [+0.032, +0.296] |
| Pooled | dedup unordered pair | 199 | 171 | +0.162 | [+0.030, +0.294] |

Interpretation:

- The same-ID vs false-candidate reviewability gap persists in the pooled
  full-queue sample.
- MegaDescriptor independently supports the gap.
- DINOv2 has the same direction but the CI crosses zero, so DINOv2 does not
  independently prove the same/false reviewability gap in this 100-pair sample.

This is weaker than legacy-code18i's targeted result for DINOv2, but more realistic
because it samples the full queue rather than only mechanism-selected pairs.

## PF-ERI Score Alignment

Majority vote, review-ready vs non-ready:

| Descriptor | Score | Ready mean | Non-ready mean | Difference | 95% bootstrap CI | AUC |
| --- | --- | ---: | ---: | ---: | --- | ---: |
| MegaDescriptor | PF-ERI admissibility | 0.722 | 0.692 | +0.029 | [+0.011, +0.048] | 0.691 |
| DINOv2 | PF-ERI admissibility | 0.724 | 0.685 | +0.039 | [+0.022, +0.056] | 0.768 |
| MegaDescriptor | PF-ERI review score | 0.663 | 0.471 | +0.192 | [+0.121, +0.257] | 0.802 |
| DINOv2 | PF-ERI review score | 0.695 | 0.506 | +0.190 | [+0.115, +0.258] | 0.810 |
| MegaDescriptor | weakest image quality | 0.545 | 0.542 | +0.003 | [-0.006, +0.013] | 0.535 |
| DINOv2 | weakest image quality | 0.542 | 0.523 | +0.019 | [-0.002, +0.043] | 0.555 |
| MegaDescriptor | descriptor similarity percentile | 0.658 | 0.341 | +0.317 | [+0.204, +0.422] | 0.803 |
| DINOv2 | descriptor similarity percentile | 0.723 | 0.413 | +0.309 | [+0.181, +0.429] | 0.787 |

Interpretation:

- PF-ERI admissibility remains aligned with multi-reviewer human
  reviewability in the full-queue sample.
- PF-ERI review score has a stronger separation than admissibility alone.
- Single-image quality alone remains weak.
- Descriptor similarity percentile is also strongly associated with
  reviewability in the full-queue sample. This is expected because full-queue
  pairs include low-rank/low-similarity candidates, unlike legacy-code18i's
  high-similarity targeted sample.

This means the final story should be precise:

```text
PF-ERI adds reviewability information and quality-only control is weak, but in
the full queue descriptor similarity itself is also a strong reviewability
correlate.
```

## Claim Update

Supported:

```text
In a 200-pair full-queue stratified sample reviewed by three label sets,
PF-ERI admissibility and PF-ERI review score align with human pair
reviewability across both MegaDescriptor and DINOv2.
```

Supported with nuance:

```text
Same-ID pairs are more review-ready than false candidates in the pooled
full-queue sample and clearly under MegaDescriptor; DINOv2 is directionally
consistent but not independently significant in this 100-pair sample.
```

Now supported, but modest:

```text
Low-evidence is a reviewer-visible not-ready reason.
```

Not supported:

```text
Non-comparable is a demonstrated mechanism in legacy-code18j.
```

Still not supported:

```text
Bobcat identity accuracy.
Automatic identity assignment.
Reviewer-perfect or adjudicated ground truth.
```

## Confidence Grade

Before legacy-code18j:

```text
moderate-to-strong targeted evidence
```

After legacy-code18j:

```text
stronger multi-reviewer evidence for PF-ERI reviewability alignment,
moderate full-queue evidence for same/false reviewability separation.
```

The best single sentence is:

```text
legacy-code18j strengthens the project by showing that PF-ERI reviewability scores
align with multi-reviewer full-queue human labels, while also revealing that
same/false reviewability separation is descriptor-dependent and that
non-comparability was not elicited in this sample.
```

## Next Step

If we need one more upgrade, do not enlarge blindly. Instead:

1. Keep the 100-per-descriptor sample as the pragmatic validation set.
2. Add explicit adjudication only for reviewer disagreements.
3. Consider a targeted non-comparable enrichment packet if we need to prove
   non-comparable as a mechanism.
4. Report descriptor similarity as an active control in full-queue analysis.

## Artifacts

```text
outputs/legacy-code18/legacy-code18j_reviewer_agreement_analysis_100/
```

Key files:

- `legacy-code18j_reviewer_agreement.csv`
- `legacy-code18j_reviewability_summary.csv`
- `legacy-code18j_score_contrasts.csv`
- `legacy-code18j_pair_majority_labels.csv`
- `legacy-code18j_majority_sensitivity.csv`
