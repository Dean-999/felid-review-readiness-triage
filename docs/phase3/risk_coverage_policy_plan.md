# Phase 3 Risk-Coverage Policy Plan

## Purpose

Phase 3 will evaluate possible review-readiness filtering policies after Phase 2 pairwise similarity outputs exist.

This phase is planned but not executed. It will not identify individual animals. It will compare how different triage policies may change the balance between retaining useful known matching evidence and reducing a pairwise false-match risk proxy.

## Relationship to Q2

Q2 asks:

After filtering low-readiness images, does pairwise false-match risk proxy decrease, and how much known matching evidence is lost?

Phase 3 addresses this by applying candidate policies to the 200-image CzechLynx pilot and measuring how many images, identities, and known same-individual pairs remain under each policy. Once Phase 2 similarity scores are available, Phase 3 will compare whether stricter policies reduce high-similarity different-individual pairs.

## Candidate Policies

### No Filter

All 200 pilot images enter candidate Re-ID review.

This policy preserves maximum coverage but may retain images with low pattern visibility, poor side comparability, severe blur, or other conditions that could increase false-match risk.

### Balanced Filter

Review-ready images plus selected review-limited images enter candidate review.

Selection rules for review-limited images should be defined before final analysis. Possible criteria include acceptable pattern visibility, usable side comparability, and no severe exclusion reason. This policy is intended to balance retained evidence and risk reduction.

### Strict Filter

Only review-ready images enter candidate review.

This policy is expected to be the most conservative. It may reduce false-match proxy risk but can also discard substantial known matching evidence.

## Metrics

Phase 3 should report:

- retained image rate;
- retained identity count;
- retained same-individual pair coverage;
- known-match loss;
- pairwise false-match risk proxy;
- false-positive pair count above selected similarity thresholds;
- risk-coverage curve.

All thresholds should be described as pilot-specific and model-specific. They should not be presented as universal felid Re-ID thresholds.

## Phase 2 Inputs to Phase 3

Phase 2 will provide the pair file and later pairwise similarity outputs. Phase 3 will use:

- image-level triage labels;
- pair-level `same_individual` labels from CzechLynx known IDs;
- `pair_readiness_group`;
- similarity scores from the selected fixed embedding baseline;
- selected similarity thresholds for false-positive proxy summaries.

The key Phase 3 comparison is policy-level: how each filtering rule changes retained coverage and the count or rate of high-similarity different-individual pairs.

## Claims Allowed Only After Analysis

After Phase 2 similarity outputs and Phase 3 policy calculations are complete, the project may be able to make cautious pilot-specific statements about:

- whether stricter filtering reduces the pairwise false-match risk proxy;
- how much same-individual evidence is lost under each policy;
- whether a balanced policy appears preferable to no filter or strict filter in this CzechLynx pilot.

These claims must remain conditional on the selected embedding baseline, CzechLynx pilot sample, and second-review consistency results.

## Forbidden Claims

Phase 3 must not claim:

- a real-world false-match rate;
- population size or population trends;
- WildTrax/UWIN identity validation;
- Marbled Cat identity validation;
- a universal threshold across felid species;
- that the project identifies true individual animals;
- that a new Re-ID model was trained or validated for deployment.

## Expected Tables and Figures

### Policy Comparison Table

Rows: no filter, balanced filter, strict filter.

Columns should include retained images, retained image rate, retained identities, retained same-individual pairs, known-match loss, and false-match proxy summaries.

### Risk-Coverage Curve

Plot retained coverage against pairwise false-match risk proxy across policy or threshold settings.

This figure should be interpreted as a pilot decision-support plot, not a deployment guarantee.

### Retained Evidence Bar Chart

Show retained images, retained identities, and retained same-individual pairs by policy.

### False-Match Proxy Table

For selected similarity thresholds, report different-individual pairs above threshold by policy and readiness group.

## Negative-Result Interpretation

Negative or mixed results are informative.

Possible outcomes include:

- strict filtering reduces coverage too much to be useful;
- review-ready images do not show the expected separation advantage;
- review-limited images contain important known matching evidence;
- false-match proxy risk remains high even after filtering;
- the selected embedding baseline is poorly aligned with the visual cues used in triage;
- second-review consistency suggests the rubric needs revision before policy conclusions.

These outcomes should lead to rubric refinement, baseline reassessment, or clearer limits on claims rather than stronger conclusions.

## Risk Audit

Before Phase 3 execution:

- confirm Phase 2 pairwise similarity outputs exist;
- confirm second-review consistency has been completed or explicitly note it as pending;
- verify no raw images are modified or redistributed;
- verify no public image display is included without license confirmation;
- verify policies are defined before inspecting final policy outcomes;
- verify thresholds are labeled pilot-specific and model-specific;
- verify outputs avoid exact coordinates, sensitive camera locations, and raw paths;
- verify conclusions remain framed as CzechLynx pilot validation, not field deployment proof.
