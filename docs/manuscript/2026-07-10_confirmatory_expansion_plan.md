# PF-ERI Confirmatory Expansion Plan

Date: 2026-07-10

## Purpose

The next scientific step is a confirmatory expansion of the reviewed candidate-pair validation set. The goal is not to make PF-ERI look like a stronger descriptor. The goal is to test, under a larger and pre-specified validation contract, whether PF-ERI remains useful as a post-retrieval pair-level evidence admission layer after controlling for descriptor similarity, image quality, and reviewer uncertainty.

The current manuscript can support a serious methods claim on 400 reviewed CzechLynx pairs. The confirmatory expansion should raise confidence by testing the same claim on a larger, stratified, blinded, and analysis-locked sample.

## Primary Confirmatory Claim

PF-ERI evaluates whether descriptor-retrieved wildlife Re-ID candidate pairs contain admissible visual evidence for human review. In a larger reviewed CzechLynx candidate-pair sample, PF-ERI should remain aligned with human reviewability / evidential admissibility after descriptor retrieval, and the signal should not be exhausted by descriptor similarity or image quality.

## Sample Size Target

Target reviewed pairs:

```text
Minimum: 800 pairs
Preferred: 1200 pairs
```

The recommended design is:

```text
2 descriptors x 600 pairs = 1200 reviewed candidate pairs
```

Descriptor strata:

```text
MegaDescriptor: 600 pairs
DINOv2: 600 pairs
```

This gives enough room to test pooled effects and descriptor-specific boundaries without pretending that every descriptor must show the same magnitude of effect.

## Sampling Design

Each descriptor-specific sample should be balanced across:

```text
rank / descriptor-similarity stratum
image-quality stratum
same-ID vs different-ID known CzechLynx audit status
PF-ERI high vs low admission score
query_image_id diversity
identity cluster diversity, if available
```

The sampling goal is not equal prevalence in nature. The goal is inferential coverage across the conditions that could otherwise explain PF-ERI away.

## Required Strata

### Descriptor Rank / Similarity

Use at least three strata:

```text
high similarity / top-rank candidates
middle similarity candidates
lower similarity candidates inside the reviewed candidate queue
```

This tests the strongest objection: PF-ERI may only work because it separates obvious weak candidates from obvious strong ones.

### Image Quality

Use at least three strata:

```text
high quality
medium quality
low quality
```

This tests whether PF-ERI is just a quality filter.

### Identity Audit Status

For CzechLynx, include both:

```text
same-ID candidate pairs
different-ID candidate pairs
```

This preserves the key endpoint distinction. Same-ID status audits candidate coverage; human reviewability remains the primary endpoint.

### PF-ERI Admission Level

Within descriptor and quality strata, include:

```text
high PF-ERI admission
low PF-ERI admission
```

This prevents the confirmatory sample from only reviewing easy high-score pairs.

## Blinding Requirement

Reviewers should see only the image pair and the review questions.

The interface should hide:

```text
descriptor name
descriptor score
PF-ERI score
high/low PF-ERI group
same-ID / different-ID truth
prior reviewer labels
route assignment
```

The visible UI should show only:

```text
query image
candidate image
reviewability / evidential admissibility option
reason option
confidence option
optional comment
```

## Reviewer Design

Minimum:

```text
2 independent blinded reviewers for every pair
```

Preferred:

```text
3 independent blinded reviewers for every pair
```

Adjudication:

```text
Only disagreement pairs go to an adjudicator.
The adjudicator stays blind to descriptor, PF-ERI score, and identity truth.
```

Final label:

```text
primary: majority reviewability label
sensitivity: adjudicated reviewability label
secondary: label uncertainty / disagreement status
```

## Primary Endpoint

The primary endpoint is:

```text
human reviewability / evidential admissibility
```

A pair is review-ready when the image evidence allows a responsible human reviewer to compare the candidate pair, including confident rejection for different-ID pairs.

A pair is not-ready or uncertain when the pair lacks comparable visual evidence or contains unresolved evidence conflict.

Identity accuracy is not the primary endpoint.

## Main Analyses

### Model Comparison

Run the same model families as the current manuscript:

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

### Active-Control Interpretation

The strict active-control comparison is:

```text
descriptor similarity + quality + PF-ERI
vs
descriptor similarity + quality
```

The confirmatory claim does not require universal descriptor-specific improvement. It does require that PF-ERI remains reviewability-relevant under pre-specified quality and similarity controls.

### Sensitivity Analyses

Required:

```text
quality-matched strata
high-quality subset
high-similarity subset
rank/similarity strata
descriptor-specific analyses
pooled analysis
unordered-pair dedup sensitivity
query_image_id clustered bootstrap
identity-clustered sensitivity, if available
reviewer-disagreement sensitivity
adjudicated-label sensitivity
```

### Review Utility

Report:

```text
not-ready / uncertain burden at fixed review budgets
review-ready rate at fixed review budgets
same-ID retention as secondary audit
false-candidate burden as secondary audit
defer / low-evidence concentration
```

Same-ID retention and false-candidate burden remain audit quantities, not identity-performance endpoints.

## Success Criteria

The confirmatory expansion supports the highest claim if:

```text
PF-ERI predicts human reviewability / evidential admissibility in pooled analysis.
PF-ERI remains aligned with reviewability inside quality-controlled strata.
PF-ERI remains aligned with reviewability inside high-similarity or rank-controlled strata.
The result holds under query-clustered bootstrap or dedup sensitivity.
The result holds under majority labels and adjudicated labels.
PF-ERI routing reduces not-ready / uncertain burden or concentrates weak evidence into deferred routes under fixed review budgets.
```

The expansion should not force every descriptor-specific active-control increment to be positive. Mixed descriptor-specific increments should be reported as boundary conditions.

## Failure Criteria

The confirmatory expansion weakens the current claim if:

```text
PF-ERI loses reviewability alignment after descriptor + quality controls.
PF-ERI signal disappears inside high-similarity strata.
PF-ERI signal disappears inside quality-matched or high-quality strata.
Reviewer disagreement overwhelms the reviewability construct.
Routing does not reduce not-ready / uncertain burden and does not concentrate weak evidence into deferred routes.
```

If this happens, the project should not inflate the claim. It should revise the PF-ERI feature design or narrow the supported setting.

## Files To Build Before Review

Recommended new artifacts:

```text
paper/protocols/confirmatory_review_protocol.md
paper/protocols/reviewer_guidelines.md
paper/protocols/pre_specified_analysis_plan.md
paper/review_packets/confirmatory_packet_manifest.csv
paper/review_packets/streamlit_confirmatory_review_app/
paper/results/confirmatory_expansion/
```

## What Else Must Be Done

The confirmatory expansion is the main scientific next step. The paper also needs four submission-readiness steps:

1. Write journal-ready Data Availability and Code Availability statements.
2. Write Ethics and Data Provenance statements for CzechLynx and Bobcat.
3. Convert the manuscript from Markdown into the target journal format.
4. Prepare a supplement with row contracts, reviewer instructions, model formulas, bootstrap details, and blocked claims.

## Recommended Order

First, lock the confirmatory protocol and review interface before collecting more labels. Second, generate the stratified 800-1200 pair packet. Third, complete blinded review and adjudication. Fourth, rerun the Phase18K-style model, sensitivity, and review-utility analyses. Fifth, update the manuscript only after the confirmatory outputs are frozen.

This order protects the project from the strongest criticism: post-hoc sampling or post-hoc analysis choices.
