# legacy-code18k Highest-Goal Validation For Problems 1-6

Date: 2026-07-03

## Highest Goal

legacy-code18k keeps one highest goal:

```text
PF-ERI is an independent pair-level evidence governance layer after strong
descriptor retrieval. It predicts human reviewability / evidential
admissibility beyond descriptor similarity and image quality, and it improves
review-routing utility.
```

There is no downgrade path in this report. If a check is not yet satisfied, the
required action is more evidence, better sampling, adjudication, or PF-ERI
feature refinement.

## Generated Artifacts

Main analysis:

```text
outputs/legacy-code18/legacy-code18k_highest_goal_validation/
```

Key files:

- `legacy-code18k_model_comparison.csv`
- `legacy-code18k_incremental_utility_summary.csv`
- `legacy-code18k_quality_matched_sensitivity.csv`
- `legacy-code18k_rankbin_sensitivity.csv`
- `legacy-code18k_high_similarity_subset.csv`
- `legacy-code18k_cluster_bootstrap.csv`
- `legacy-code18k_review_utility_at_fixed_retention.csv`
- `legacy-code18k_correlation_audit.csv`
- `legacy-code18k_claim_gate.json`

Adjudication packet:

```text
outputs/legacy-code18/legacy-code18k_adjudication_packet/
```

It contains 57 reviewer-disagreement pairs. The blind packet excludes descriptor
name, identity truth, descriptor scores, PF-ERI scores, and reviewer identities.

## Claim Gate

Current gate:

```text
NEEDS_MORE_EVIDENCE
```

This is not a downgraded claim. It means the highest-goal evidence chain is not
closed yet.

Gate checks:

| Check | Result |
| --- | --- |
| Model-comparison rows present | PASS |
| PF-ERI beats quality control in all scopes | PASS |
| PF-ERI adds positive incremental AUC beyond descriptor + quality in all scopes | NOT YET |

## Problem 1: Descriptor Similarity Replacement

Problem statement:

```text
If PF-ERI's effect is fully explained by descriptor similarity, it is not an
independent pair-level governance layer.
```

Why it can invalidate the highest goal:

Descriptor similarity percentile is already a strong reviewability predictor in
the legacy-code18j full-queue sample.

Analysis performed:

- model comparison across descriptor-only, quality-only, PF-ERI-only,
  descriptor+quality, descriptor+PF-ERI, and descriptor+quality+PF-ERI;
- query-cluster bootstrap delta AUC;
- correlation audit between PF-ERI and descriptor similarity;
- rank-bin and high-similarity subset outputs.

Result:

| Scope | PF-ERI vs descriptor delta AUC | Full PF-ERI model vs descriptor+quality delta AUC |
| --- | ---: | ---: |
| MegaDescriptor | -0.0009 | -0.0005 |
| DINOv2 | +0.0229 | +0.0043 |
| Pooled | +0.0104 | +0.0026 |

PF-ERI clearly improves over quality-only, but full incremental utility beyond
descriptor+quality is small and not yet decisive.

Critical correlation:

| Scope | corr(PF-ERI review score, descriptor similarity percentile) |
| --- | ---: |
| MegaDescriptor | 0.991 |
| DINOv2 | 0.993 |
| Pooled | 0.992 |

Remaining gap:

The current PF-ERI review score is too correlated with descriptor similarity to
fully close the independence argument.

Next required action to reach highest goal:

Run a rank-matched/high-similarity confirmatory design and/or rebuild a
PF-ERI-independent review score that emphasizes admissibility, geometry, weakest
evidence, and conflict while reducing descriptor-similarity leakage.

## Problem 2: Image Quality Filter

Problem statement:

```text
If PF-ERI is only an image-quality filter, the innovation is not pair-level
evidence governance.
```

Analysis performed:

- quality-only control;
- low-quality-half and high-quality-half sensitivity;
- quality-matched IQR sensitivity.

Result:

| Scope | PF-ERI AUC | Quality AUC | Difference |
| --- | ---: | ---: | ---: |
| MegaDescriptor | 0.802 | 0.535 | +0.267 |
| DINOv2 | 0.810 | 0.555 | +0.255 |
| Pooled | 0.801 | 0.544 | +0.257 |

Quality-matched IQR remains strong:

| Scope | PF-ERI AUC | Quality AUC | Difference |
| --- | ---: | ---: | ---: |
| MegaDescriptor | 0.795 | 0.500 | +0.295 |
| DINOv2 | 0.812 | 0.500 | +0.312 |
| Pooled | 0.796 | 0.500 | +0.296 |

Remaining gap:

This problem is mostly controlled. The remaining issue is not quality; it is
descriptor-similarity dependence.

Next required action:

Keep quality-only and descriptor+quality controls in every future legacy-code18k run.

## Problem 3: Human Label Reliability

Problem statement:

```text
Majority vote is not automatically a stable reference label.
```

Analysis performed:

- generated disagreement adjudication packet;
- retained hidden audit file for later adjudicated re-analysis.

Result:

```text
57 reviewer-disagreement pairs require adjudication.
```

Remaining gap:

Adjudicated labels do not exist yet.

Next required action:

Have an adjudicator label the 57 blind pairs, then rerun legacy-code18k using
adjudicated labels as an additional reference label set.

## Problem 4: Targeted Sample Inflation

Problem statement:

```text
Targeted samples can inflate mechanism effects.
```

Analysis performed:

legacy-code18k uses legacy-code18j full-queue stratified multi-reviewer labels as the main
validation set. legacy-code18i targeted data is not used in the claim gate.

Result:

This problem is structurally controlled in the current analysis.

Remaining gap:

The full-queue validation set has only 100 pairs per descriptor.

Next required action:

If incremental utility remains small, expand a legacy-code18j confirmatory batch with
rank-matched/high-similarity strata, prioritizing samples where descriptor
similarity is controlled by design.

## Problem 5: Row / Query Dependence

Problem statement:

```text
Repeated query images or reciprocal pairs can make row-level confidence too
optimistic.
```

Analysis performed:

- query-image clustered bootstrap;
- unordered-pair dedup sensitivity.

Result:

| Scope | PF-ERI ready-minus-nonready mean difference | Query-cluster 95% CI | Unique queries |
| --- | ---: | --- | ---: |
| MegaDescriptor | +0.192 | [+0.118, +0.256] | 91 |
| DINOv2 | +0.190 | [+0.111, +0.267] | 92 |
| Pooled | +0.191 | [+0.131, +0.245] | 171 |

Dedup sensitivity remains directionally stable.

Remaining gap:

Identity/site/date clustered sensitivity is not implemented because those fields
are not present in the current legacy-code18j majority table.

Next required action:

If identity/site/date fields become available, add stricter ecological-cluster
sensitivity. Current query-cluster evidence is stable.

## Problem 6: Same-ID vs False-Candidate Endpoint Confusion

Problem statement:

```text
Same-ID/false-candidate labels are not the same as reviewability. A false
candidate can be review-ready if it is easy to reject.
```

Analysis performed:

legacy-code18k keeps reviewability as the primary endpoint and outputs same-ID
retention / false-candidate burden only as review-utility metrics.

Result:

PF-ERI predicts human reviewability strongly, but fixed-retention review utility
is not clearly superior to descriptor-only under the current score formulation.

Remaining gap:

Current PF-ERI review score does not yet give a strong fixed-retention advantage
over descriptor similarity.

Next required action:

Optimize or rebuild the routing score for fixed same-ID retention and false
candidate burden, preferably using a descriptor-controlled or rank-matched
validation design.

## Highest-Goal Next Step

The immediate blocker is now precise:

```text
PF-ERI review score is too highly correlated with descriptor similarity.
```

To reach the highest goal, the next implementation should do one of two things:

1. **Descriptor-controlled confirmatory sampling**: add rank-matched and
   high-similarity-only pairs so descriptor similarity is held nearly constant.
2. **PF-ERI score refactor**: build an evidence-only or conflict-aware PF-ERI
   review score that reduces descriptor-similarity leakage, then rerun legacy-code18k.

