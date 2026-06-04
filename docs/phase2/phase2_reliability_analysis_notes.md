# Phase 2 Reliability Analysis Notes

## Purpose

This analysis summarizes whether CzechLynx pilot pair similarities show useful reliability signals by review-readiness group.

The analysis evaluates the triage workflow. It does not identify individual animals and does not validate a deployed Re-ID system.

## Input Files

- `data/interim/czechlynx/czechlynx_pair_similarities.csv`
- `data/interim/czechlynx/czechlynx_pilot_pairs.csv`
- `data/interim/czechlynx/czechlynx_pilot_validation_table.csv`

The analysis script reads the pair similarity file directly. Pair construction and embedding output audits are expected to have passed before this analysis is interpreted.

## Baseline Used

The similarity values come from a fixed generic ResNet-50 ImageNet embedding baseline.

This baseline is:

- pretrained before this project;
- not trained or fine-tuned on CzechLynx;
- not wildlife-specialized;
- used only as a measurement signal.

## Metrics Computed

The Phase 2 reliability script computes:

- same-individual and different-individual cosine similarity summaries;
- summary statistics by `pair_readiness_group` and `same_individual`;
- same-minus-different mean similarity separation gaps;
- ROC-AUC for `same_individual` prediction from cosine similarity, if `scikit-learn` is available;
- quantile-based threshold proxy counts;
- optional same/different histogram and readiness-group boxplot if `matplotlib` is available.

## What the Analysis Can Support

The analysis can support cautious pilot-level statements about:

- whether same-individual pairs tend to score higher than different-individual pairs;
- whether separation differs across review-readiness groups;
- whether some triage groups appear noisier or less separable;
- whether Phase 3 risk-coverage policy analysis is worth pursuing.

These are validation signals for the review-readiness rubric, not final scientific conclusions.

## What the Analysis Cannot Claim

The analysis cannot claim:

- individual animals were identified;
- a real-world false-match rate;
- a deployment-ready Re-ID system;
- a new model or improved model;
- a universal threshold across felid species;
- population size or trend;
- WildTrax or Marbled Cat identity validation.

Threshold summaries are pilot-specific and baseline-specific proxies.

## Interpretation Guidance

### Positive Results

If same-individual similarity is higher than different-individual similarity, especially in `ready_ready` pairs, the result supports proceeding with cautious Phase 3 policy evaluation.

This should be framed as evidence that the triage rubric may correspond to stronger known-ID similarity behavior in the CzechLynx pilot.

### Weak Results

If separation is small, inconsistent, or concentrated in only some readiness groups, the result suggests the rubric may need refinement or that the generic baseline may not align well with visually diagnostic lynx features.

Weak results should not be treated as failure. They help identify which triage labels or visual fields need clearer decision rules.

### Negative Results

If same-individual pairs do not score higher than different-individual pairs, or if lower-readiness groups show similar or better separation than `ready_ready`, the result should be treated as a caution against strong filtering claims.

Possible explanations include:

- the baseline is not wildlife-specialized;
- the sample is small;
- the pair sample is imbalanced across readiness groups;
- the triage rubric needs revision;
- field conditions reduce embedding reliability in ways not captured by the current labels.

## Supporting-Field Caveat

Second-review consistency showed that supporting fields were less stable than the main `triage_label`, especially `side_comparability`.

Therefore, Phase 2 interpretation should treat supporting fields such as `side_comparability`, `pattern_visibility`, and `exclusion_reason` as exploratory unless later evidence supports stronger use.

## Boundary Statement

This analysis is a pilot validation step under a fixed generic embedding baseline. It is not a final claim that review-readiness filtering works in deployment.
