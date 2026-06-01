# Research Questions

## Purpose

This document locks the final research questions for the project.

The project keeps only two core questions:

1. Q1 Reliability
2. Q2 Trade-off

All other possible questions are secondary and must not become the main project.

## Research Question 1: Reliability

### Main Question

Do images labeled as review-ready show more reliable Re-ID behavior than review-limited or unidentifiable images?

### Technical Version

Does the review-ready label correspond to stronger same-individual versus different-individual similarity separation in known-ID felid Re-ID data?

### Plain-Language Meaning

If an image is labeled review-ready by a visual rubric, does that label actually correspond to better Re-ID behavior?

In other words, do review-ready images make it easier to separate same-individual pairs from different-individual pairs in embedding similarity space?

### Why This Question Matters

A review-ready label has limited scientific value if it is only a human visual preference.

It becomes more meaningful if the label predicts measurable Re-ID reliability. If review-ready images show stronger same/different separation, then review-readiness can function as a validated pre-Re-ID gate.

If review-ready images do not show stronger separation, that result is still useful. It would show that simple visual readiness is insufficient and that the rubric must be strengthened with criteria such as visible side, diagnostic body region, pattern visibility, metadata completeness, or side-aware comparison.

### Validation Dataset

CzechLynx is the validation dataset for Q1 because it provides known individual IDs.

### Input Groups

Images will be assigned to one of three triage categories:

- review-ready;
- review-limited;
- unidentifiable.

The triage label must be assigned without looking at the individual ID.

### Pair Construction

Pairs should be constructed from CzechLynx images:

- same-individual pairs: two images with the same verified individual ID;
- different-individual pairs: two images with different verified individual IDs.

Pairs may later be stratified by:

- triage category;
- visible side;
- visible region;
- lighting condition;
- blur level;
- occlusion level;
- pattern visibility;
- camera site;
- time split if metadata supports it.

### Primary Metrics

The primary metrics for Q1 are:

- mean same-individual similarity;
- median same-individual similarity;
- mean different-individual similarity;
- median different-individual similarity;
- same/different separation gap;
- overlap between same-individual and different-individual similarity distributions;
- AUC for pairwise same/different separability;
- false positive rate at selected operating points;
- false negative rate at selected operating points.

### Expected Positive Result

A positive result would show:

- review-ready images have higher same-individual similarity;
- review-ready images have lower overlap between same- and different-individual distributions;
- review-ready images produce stronger AUC or pairwise separability;
- review-limited and unidentifiable images show weaker separation.

### Expected Negative or Mixed Result

A negative or mixed result would show:

- review-ready images do not clearly improve similarity separation;
- visual triage alone is not enough;
- additional fields such as side comparability, diagnostic region visibility, and pattern visibility are required;
- Re-ID should be applied only after stronger review-readiness filtering.

A negative result does not invalidate the project. It answers the central reliability question.

### Allowed Claims After Q1

If Q1 succeeds, the project may claim:

- In known-ID CzechLynx validation, review-ready images showed stronger same/different Re-ID similarity separation than lower-readiness images.
- Review-readiness can be evaluated quantitatively rather than treated only as a visual judgment.
- Re-ID embeddings can serve as an auxiliary measurement signal for evaluating the technical meaning of review-readiness.

### Claims Not Allowed After Q1

The project may not claim:

- the system identifies true individuals in WildTrax;
- the result transfers directly to Bobcat, Canada Lynx, or Marbled Cat;
- the same threshold is universal across felids;
- human triage is automatically correct;
- a new Re-ID model was developed.

## Research Question 2: Trade-off

### Main Question

After filtering low-readiness images, does pairwise false-match risk proxy decrease, and how much potential known matching evidence is lost?

### Technical Version

How much safety is gained, and how much matching coverage is lost, when low-readiness images are removed from candidate Re-ID review?

### Plain-Language Meaning

Conservation workflows face a real decision problem.

If all images enter Re-ID review, more possible evidence is preserved, but unsafe matches may increase.

If only the clearest images enter Re-ID review, false-match risk may decrease, but useful same-individual evidence may be lost.

Q2 measures this trade-off.

### Validation Dataset

CzechLynx is used for Q2 because it provides known individual IDs and allows pairwise validation.

### Entry Policies

The project will compare three image-entry policies:

| Policy | Entry Rule | Intended Use |
|---|---|---|
| No filter | All images enter candidate Re-ID review | Baseline only |
| Balanced filter | Review-ready plus selected review-limited images enter | Expert review queue |
| Strict filter | Only review-ready images enter | Conservative reporting |

### Primary Metrics

The primary metrics for Q2 are:

- retained image rate;
- retained identity count;
- retained same-pair coverage;
- known-match loss;
- pairwise false-match risk proxy under known-ID validation;
- false positive pair count above selected similarity operating points;
- risk–coverage curve;
- policy comparison table.

### False-Match Risk Wording Rule

The project must use this phrase:

pairwise false-match risk proxy under known-ID validation

The project must not describe this metric as:

- real-world deployment false-match rate;
- population-level error rate;
- true field false-match rate;
- WildTrax identity error rate.

### Expected Positive Result

A positive result would show:

- stricter filtering reduces pairwise false-match risk proxy;
- stricter filtering also removes some known same-individual evidence;
- the balanced filter may preserve more evidence while reducing some risk;
- the strict filter may be more appropriate for conservation-safe reporting.

### Expected Negative or Mixed Result

A negative or mixed result would show:

- filtering does not reduce risk enough to justify evidence loss;
- the current rubric is not selective enough;
- review-limited images may contain useful matching evidence;
- the gate should be refined rather than accepted as final.

This result would still be scientifically useful.

### Allowed Claims After Q2

If Q2 succeeds, the project may claim:

- Filtering low-readiness images creates a measurable risk–coverage trade-off in known-ID validation.
- Strict filtering can reduce pairwise false-match risk proxy but may reduce retained matching evidence.
- A balanced review policy may be useful for expert review queues, while a strict policy may be more appropriate for conservative reporting.

### Claims Not Allowed After Q2

The project may not claim:

- real-world false-match rate was measured;
- population estimates were improved;
- WildTrax identities were validated;
- Marbled Cat Re-ID was validated;
- one numerical threshold transfers across species.

## Hypotheses

### H1

Review-ready images will show stronger same-individual versus different-individual similarity separation than review-limited or unidentifiable images.

### H2

Strict filtering will reduce pairwise false-match risk proxy but will also reduce retained known matching evidence.

### H3

A balanced policy may preserve more evidence than strict filtering while reducing risk relative to no filtering.

## Minimum Viable Test

The minimum viable test requires:

- a CzechLynx sample with known individual IDs;
- triage labels assigned without viewing IDs;
- one fixed Re-ID embedding baseline;
- pairwise same/different similarity calculation;
- policy comparison across no filter, balanced filter, and strict filter.

## Excluded Questions

The project will not answer:

- Can AI identify every individual felid in the wild?
- How many Bobcats or Canada Lynx individuals appear in WildTrax?
- What is the true population size of any species?
- Does CzechLynx performance transfer directly to Marbled Cat?
- Is one universal Re-ID threshold valid across felids?
- Can this project replace expert review?

## Phase 0 Pass Standard

This document is accepted only if:

- Q1 and Q2 remain the only core questions;
- all metrics are measurable;
- negative results are interpretable;
- the false-match risk wording remains conservative;
- CzechLynx, WildTrax, and Marbled Cat are not mixed into one validation claim.