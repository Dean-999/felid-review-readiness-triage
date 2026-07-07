# legacy-code18k Uncertainty Concentration And Ideal Proof Examples

Date: 2026-07-03

## Question

The system value is not:

```text
PF-ERI produces more uncertain / not-ready labels.
```

The system value is:

```text
PF-ERI concentrates uncertain / not-ready labels in the pairs where evidence is
actually weak, non-admissible, or hard to compare, while preserving review-ready
labels for high-evidence pairs.
```

This is the correct interpretation of PF-ERI as a pair-level evidence governance
layer.

## Generated Artifacts

```text
outputs/legacy-code18/legacy-code18k_uncertainty_concentration/
```

Key files:

- `legacy-code18k_uncertainty_group_rates.csv`
- `legacy-code18k_uncertainty_enrichment_contrasts.csv`
- `legacy-code18k_uncertainty_within_rankbin.csv`
- `legacy-code18k_idealized_proof_examples.csv`
- `legacy-code18k_uncertainty_concentration_audit.json`

## Current Result

### Low Admissibility Concentrates Uncertainty

In the output tables, `admissibility_risk_group=high` means **high evidence
risk**, i.e. low PF-ERI admissibility.

| Scope | High-risk uncertainty rate | Low-risk uncertainty rate | Difference | Risk ratio |
| --- | ---: | ---: | ---: | ---: |
| MegaDescriptor | 0.471 | 0.167 | +0.304 | 2.82 |
| DINOv2 | 0.545 | 0.032 | +0.513 | 16.91 |
| Pooled | 0.507 | 0.104 | +0.403 | 4.86 |

Interpretation:

```text
Uncertain/not-ready labels are strongly enriched where PF-ERI admissibility is
low.
```

This directly supports the evidence-governance interpretation.

### Low Geometry Also Concentrates Uncertainty

In the output tables, `geometry_risk_group=high` means **high geometry risk**,
i.e. low pair geometry compatibility.

| Scope | High-risk uncertainty rate | Low-risk uncertainty rate | Difference | Risk ratio |
| --- | ---: | ---: | ---: | ---: |
| MegaDescriptor | 0.395 | 0.194 | +0.201 | 2.04 |
| DINOv2 | 0.483 | 0.194 | +0.288 | 2.48 |
| Pooled | 0.433 | 0.194 | +0.239 | 2.23 |

Interpretation:

```text
Uncertain/not-ready labels are enriched where pair geometry/comparability is
weak.
```

This is also aligned with PF-ERI's pair-level theory.

### Conflict Is Not The Current Mechanism

High conflict did **not** enrich uncertainty:

| Scope | High-conflict uncertainty rate | Low-conflict uncertainty rate | Difference |
| --- | ---: | ---: | ---: |
| MegaDescriptor | 0.077 | 0.467 | -0.390 |
| DINOv2 | 0.146 | 0.476 | -0.330 |
| Pooled | 0.119 | 0.471 | -0.351 |

Interpretation:

```text
The current human uncertainty mechanism is low admissibility / low geometry, not
high descriptor-evidence conflict.
```

So the next claim should not rely on conflict enrichment unless a later score or
sample design demonstrates it.

### Within-Rank Evidence

The pooled within-rank result remains directionally positive for low
admissibility in all rank bins:

| Rank bin | High-risk uncertainty rate | Low-risk uncertainty rate | Difference |
| --- | ---: | ---: | ---: |
| rank_01 | 0.375 | 0.222 | +0.153 |
| rank_02_05 | 0.563 | 0.000 | +0.563 |
| rank_06_10 | 0.471 | 0.125 | +0.346 |
| rank_11_20 | 0.611 | 0.059 | +0.552 |

Interpretation:

```text
Even within descriptor rank bins, low admissibility concentrates human
uncertainty.
```

This is the most useful current evidence against the idea that PF-ERI is only
descriptor similarity.

## Idealized Example That Would Prove The Project

The ideal proof is a controlled 2x2 pattern:

| Descriptor similarity | PF-ERI evidence state | Expected human label pattern | Meaning |
| --- | --- | --- | --- |
| High | High admissibility / high geometry | Mostly `review_ready` | PF-ERI does not reject good high-similarity pairs |
| High | Low admissibility / poor geometry | Enriched `uncertain` / `not_review_ready` | PF-ERI catches high-similarity but weak-evidence pairs |
| High | High conflict, low admissibility | More defer / uncertainty than matched controls | PF-ERI governs evidence, not similarity alone |
| Low | High admissibility / comparable images | Often `review_ready` for rejection | Reviewability is not identity correctness |

Concrete idealized example:

```text
Pair A:
descriptor_similarity_percentile = 0.92
PF-ERI admissibility = high
geometry = high
human label = review_ready

Pair B:
descriptor_similarity_percentile = 0.92
PF-ERI admissibility = low
geometry = low
human label = uncertain or not_review_ready
```

Because Pair A and Pair B have the same descriptor similarity, the difference
cannot be explained by descriptor similarity. If this pattern repeats across
many matched pairs and both descriptors, it proves PF-ERI's specific value:

```text
PF-ERI identifies when a visually similar candidate pair is evidentially
admissible versus when it is only descriptor-similar but weak for review.
```

## Current Confidence

Supported now:

```text
Uncertain/not-ready labels are strongly concentrated in low-admissibility and
low-geometry PF-ERI regions.
```

Not yet fully closed:

```text
Route-level defer/non-comparable behavior, because current legacy-code18j sampled
pairs are almost all `pf_eri_route=review`.
```

Most important next step:

```text
Build a descriptor-controlled, high-similarity packet that intentionally
contrasts high-admissibility and low-admissibility pairs at matched descriptor
similarity.
```

This is better than simply increasing uncertain/not-ready frequency. The target
is selective concentration, not general conservatism.

