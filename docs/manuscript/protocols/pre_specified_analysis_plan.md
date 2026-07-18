# Phase18N Pre-Specified Analysis Plan

Date locked: 2026-07-10

## Primary Endpoint

The primary endpoint is binary human reviewability / evidential admissibility:

```text
review_ready vs not_review_ready_or_uncertain
```

`not_review_ready` and `uncertain` will be grouped as not-ready/uncertain for the primary analysis. Reason-family analyses will treat `low_evidence`, `non_comparable`, and `both_low_evidence_and_non_comparable` as secondary outcomes.

## Human Label Aggregation

Each pair should have three blinded reviewers.

Primary label:

```text
majority reviewability label
```

Reliability outputs:

```text
percent agreement
Cohen's kappa for reviewer pairs
Fleiss' kappa or equivalent multi-rater agreement
reason-family agreement on not-ready/uncertain pairs
```

Adjudication sensitivity:

```text
reviewer-disagreement pairs should be adjudicated blind
primary model analyses should be repeated on adjudicated labels
```

## Primary Model Comparison

Run the following model families on identical row sets:

```text
descriptor similarity only
quality only
PF-ERI evidence only
descriptor similarity + quality
descriptor similarity + PF-ERI
descriptor similarity + quality + PF-ERI
```

Report:

```text
AUROC
AUPRC
Brier score
ECE-5
95% bootstrap confidence intervals
```

The strict active-control comparison is:

```text
descriptor similarity + quality + PF-ERI
vs
descriptor similarity + quality
```

## Bootstrap And Dependence

Primary uncertainty:

```text
query_image_id clustered bootstrap
5000 iterations
fixed seed 20260710
```

Sensitivity:

```text
unordered-pair dedup sensitivity
descriptor-specific bootstrap
identity-clustered sensitivity if identity cluster fields are available
```

## Quality And Similarity Controls

Required sensitivity analyses:

```text
quality-matched strata
high-quality subset
descriptor high-similarity subset
rank/similarity strata
PF-ERI vs descriptor similarity correlation audit
```

The current quality proxy may have weak variation. If quality cutoffs collapse or produce sparse strata, report that as a limitation and do not convert it into positive evidence.

## Review Utility

Report review-routing utility at fixed review budgets:

```text
50
100
150
200
300
400
600
800
1000
1200
```

For each budget, compare:

```text
PF-ERI priority
descriptor-similarity priority
descriptor + quality priority, if score is available
```

Report:

```text
review-ready rate
not-ready/uncertain burden
same-ID retention as secondary audit
false-candidate burden as secondary audit
deferred not-ready/uncertain concentration
```

Same-ID retention and false-candidate burden are not identity-performance endpoints.

## Success Criteria

Phase18N supports the highest current claim if:

```text
PF-ERI predicts human reviewability in pooled analysis.
PF-ERI remains aligned with reviewability inside similarity-controlled strata.
PF-ERI remains aligned with reviewability under the available quality control, with limitations reported if the quality proxy lacks variation.
Results remain directionally stable under query-clustered bootstrap and unordered-pair dedup sensitivity.
Majority-label and adjudicated-label analyses agree in direction.
PF-ERI routing reduces not-ready/uncertain burden or concentrates weak evidence into deferred routes at finite review budgets.
```

## Failure Criteria

Phase18N weakens the current claim if:

```text
PF-ERI loses reviewability alignment in pooled analysis.
PF-ERI signal disappears inside high-similarity or rank-controlled strata.
Reviewer disagreement makes the reviewability endpoint unstable.
Routing neither reduces not-ready/uncertain burden nor concentrates weak evidence into deferred routes.
```

If these occur, the manuscript should not inflate the claim. The correct response is feature revision, additional measurement design, or a narrower supported setting.

## Reporting Rule

Report mixed descriptor-specific results as boundary conditions. Do not require every descriptor-specific active-control increment to be positive. The confirmatory claim concerns pair-level evidence admission after strong descriptor retrieval, not universal descriptor-specific ranking superiority.
