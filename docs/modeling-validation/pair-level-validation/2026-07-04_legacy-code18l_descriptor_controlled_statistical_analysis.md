# legacy-code18l Descriptor-Controlled Statistical Analysis

Date: 2026-07-04

## Question

legacy-code18l tests the hardest remaining challenge:

```text
When descriptor similarity is controlled by sampling, does low PF-ERI
admissibility still concentrate human uncertain / not-ready labels?
```

This directly targets the descriptor-similarity replacement problem.

## Data

Input:

```text
outputs/legacy-code18/legacy-code18l_descriptor_controlled_review_packet/
outputs/legacy-code18/legacy-code18l_streamlit_review/
```

Analysis:

```text
outputs/legacy-code18/legacy-code18l_descriptor_controlled_analysis/
```

Design:

| Descriptor | High-admissibility pairs | Low-admissibility pairs | Reviewers | Label rows |
| --- | ---: | ---: | ---: | ---: |
| MegaDescriptor | 50 | 50 | 3 | 300 |
| DINOv2 | 50 | 50 | 3 | 300 |
| Total | 100 | 100 | 3 | 600 |

Primary binary endpoint:

```text
uncertain_or_not_ready = uncertain OR not_review_ready
```

The positive class is not an identity error. It means the human reviewer did not
consider the pair straightforwardly review-ready.

## Main Result

Majority vote:

| Descriptor | High-admissibility uncertain/not-ready | Low-admissibility uncertain/not-ready | Risk difference | 95% bootstrap CI | Fisher exact p | Odds ratio |
| --- | ---: | ---: | ---: | --- | ---: | ---: |
| MegaDescriptor | 4/50 = 0.08 | 28/50 = 0.56 | +0.48 | [+0.32, +0.64] | 3.05e-07 | 13.09 |
| DINOv2 | 4/50 = 0.08 | 7/50 = 0.14 | +0.06 | [-0.06, +0.18] | 0.525 | 1.78 |
| Pooled | 8/100 = 0.08 | 35/100 = 0.35 | +0.27 | [+0.17, +0.38] | 4.31e-06 | 5.90 |

Interpretation:

```text
The descriptor-controlled packet strongly supports the PF-ERI admissibility
mechanism for MegaDescriptor and in the pooled analysis. DINOv2 is directionally
consistent but not independently significant under majority vote.
```

This is not a weak result. It is a differentiated result: the mechanism is very
strong in one strong descriptor queue, pooled-positive across both, and weaker
under DINOv2.

## Reviewer-Level Pattern

MegaDescriptor:

| Reviewer | High rate | Low rate | Difference | Fisher p |
| --- | ---: | ---: | ---: | ---: |
| reviewer1 | 0.08 | 0.86 | +0.78 | 9.71e-13 |
| reviewer2 | 0.04 | 0.46 | +0.42 | 1.14e-06 |
| reviewer3 | 0.06 | 0.46 | +0.40 | 6.50e-06 |

DINOv2:

| Reviewer | High rate | Low rate | Difference | Fisher p |
| --- | ---: | ---: | ---: | ---: |
| reviewer1 | 0.06 | 0.24 | +0.18 | 0.0226 |
| reviewer2 | 0.06 | 0.20 | +0.14 | 0.0713 |
| reviewer3 | 0.18 | 0.28 | +0.10 | 0.342 |

Interpretation:

```text
All six reviewer-descriptor combinations have the expected direction. The
effect is consistently large for MegaDescriptor and smaller for DINOv2.
```

This consistency matters. Even where DINOv2 is not individually significant,
the direction does not reverse.

## Reviewer Agreement

Binary uncertain/not-ready agreement:

| Descriptor | Reviewer pair | Agreement | Cohen's kappa |
| --- | --- | ---: | ---: |
| MegaDescriptor | r1-r2 | 0.760 | 0.505 |
| MegaDescriptor | r1-r3 | 0.770 | 0.526 |
| MegaDescriptor | r2-r3 | 0.830 | 0.553 |
| DINOv2 | r1-r2 | 0.840 | 0.336 |
| DINOv2 | r1-r3 | 0.760 | 0.228 |
| DINOv2 | r2-r3 | 0.800 | 0.334 |

Interpretation:

```text
MegaDescriptor agreement is moderate and usable. DINOv2 agreement has good raw
agreement but lower kappa, likely because uncertain/not-ready labels are rarer
and the class distribution is imbalanced.
```

The lower DINOv2 kappa does not invalidate the analysis, but it weakens the
descriptor-specific confidence for DINOv2.

## Statistical Meaning

The correct statistical reading is:

1. **MegaDescriptor:** strong evidence.
   Low PF-ERI admissibility increases human uncertain/not-ready labels by 48
   percentage points under descriptor-controlled high-similarity sampling.

2. **Pooled:** strong evidence.
   Across both descriptors, low PF-ERI admissibility increases human
   uncertain/not-ready labels by 27 percentage points.

3. **DINOv2:** mixed but directionally supportive.
   Majority vote difference is +6 points with CI crossing zero, but all three
   reviewers show the expected direction.

## Does This Prove The Project?

It substantially strengthens the project because it addresses the key critique:

```text
PF-ERI may only be descriptor similarity in disguise.
```

legacy-code18l shows that when descriptor similarity is controlled by design,
low-admissibility pairs are more likely to be human-uncertain/not-ready,
especially under MegaDescriptor and in the pooled analysis.

However, under the user's highest standard:

```text
basic completion is not completion
```

the strict answer is:

```text
The mechanism is strongly supported, but the cross-descriptor highest-goal proof
is not fully closed because DINOv2 majority-vote evidence is directional but not
independently significant.
```

## What This Solves

Solved strongly:

```text
uncertain/not-ready frequency is not merely global conservatism;
it concentrates in low-admissibility pairs.
```

Solved strongly for MegaDescriptor:

```text
PF-ERI has descriptor-controlled reviewability signal beyond high descriptor
similarity.
```

Solved in pooled analysis:

```text
Across the full descriptor-controlled packet, low admissibility is associated
with human uncertainty/not-ready.
```

Not fully solved:

```text
DINOv2 independent majority-vote confirmation.
```

## Next Required Action

To fully close the highest-goal proof, do not weaken the claim. Instead:

1. Build a DINOv2-focused confirmatory packet.
2. Oversample DINOv2 high-similarity pairs where PF-ERI admissibility contrast is
   larger and descriptor similarity match delta remains small.
3. Keep three reviewers.
4. Re-run this exact analysis.

Target confirmatory endpoint:

```text
DINOv2 low-admissibility uncertain/not-ready rate exceeds high-admissibility
rate with CI fully above zero.
```

If that passes, the highest-goal cross-descriptor proof becomes much harder to
challenge.

