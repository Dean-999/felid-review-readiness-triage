# Claims and Boundaries

## Purpose

This document defines what the project is allowed to claim, what it may claim only conditionally, and what it must never claim.

This document is a protection against overclaiming.

## Core Boundary

This project does not identify individual animals.

It evaluates whether images are reliable enough to enter individual-level Re-ID review.

## Core Contribution Claim

The project may claim that it evaluates a review-readiness gate for felid conservation camera-trap images before individual-level Re-ID review.

The project may also claim that it quantifies how this gate affects:

- Re-ID reliability;
- pairwise false-match risk proxy under known-ID validation;
- retained matching evidence.

## Allowed Claims

The project may claim:

1. A review-readiness gate can be evaluated quantitatively rather than only visually.
2. CzechLynx known-ID data can be used to test whether review-ready images show stronger same-individual versus different-individual similarity separation.
3. Filtering low-readiness images can be evaluated as a risk–coverage trade-off.
4. Pairwise false-match risk proxy can be measured under known-ID validation.
5. Retained image rate, retained identity count, retained same-pair coverage, and known-match loss can be measured under different entry policies.
6. UWIN/WildTrax images provide real field motivation and stress-test examples.
7. Species-level tagging and individual-level Re-ID readiness are different standards.
8. Marbled Cat is a future Asian conservation application scenario that would require separate known-ID validation.
9. Re-ID embeddings are used as an auxiliary measurement signal.
10. Expert review remains necessary for conservation-safe identity interpretation.

## Conditional Claims

The project may claim the following only after analysis:

### Conditional Claim 1

If review-ready images show stronger same/different separation:

In known-ID CzechLynx validation, review-ready images showed stronger Re-ID similarity separation than lower-readiness images.

### Conditional Claim 2

If strict filtering reduces false-match proxy:

Strict review-readiness filtering reduced pairwise false-match risk proxy under known-ID validation.

### Conditional Claim 3

If strict filtering also loses evidence:

Strict filtering reduced risk but also removed some known same-individual matching evidence.

### Conditional Claim 4

If balanced filtering performs well:

A balanced entry policy may be appropriate for expert review queues because it preserves more matching evidence than strict filtering while reducing risk relative to no filtering.

### Conditional Claim 5

If results are weak:

Visual review-readiness alone was insufficient, and stronger criteria such as visible side, diagnostic region visibility, pattern visibility, metadata completeness, or side-aware comparison are needed.

## Forbidden Claims

The project must not claim:

1. It creates a new state-of-the-art animal Re-ID model.
2. It creates a universal animal identification system.
3. It identifies true individuals in WildTrax data.
4. It estimates population size.
5. It validates Marbled Cat Re-ID.
6. It proves CzechLynx thresholds transfer to Bobcat, Canada Lynx, or Marbled Cat.
7. It provides a universal Re-ID threshold.
8. It replaces expert review.
9. It measures real-world deployment false-match rate.
10. It proves human triage is automatically correct.
11. It performs full open-set field identity discovery.
12. It builds a full Re-ID workflow or human review website as the main contribution.
13. It solves all felid Re-ID.
14. It treats candidate evidence as true individual identity.

## Wording Rules

### False-Match Risk

Correct wording:

- pairwise false-match risk proxy under known-ID validation

Incorrect wording:

- false-match rate;
- real-world false-match rate;
- deployment error rate;
- population-level false-match rate;
- WildTrax false-match rate.

### WildTrax

Correct wording:

- field motivation;
- field-readiness stress test;
- field triage distribution;
- field failure-mode examples.

Incorrect wording:

- WildTrax identity validation;
- WildTrax individual count;
- WildTrax Re-ID accuracy;
- true Bobcat identities;
- true Canada Lynx identities.

### CzechLynx

Correct wording:

- quantitative known-ID validation carrier;
- controlled validation dataset;
- dataset-specific operating point.

Incorrect wording:

- the whole project is Eurasian lynx Re-ID;
- CzechLynx threshold applies to all felids;
- CzechLynx proves field deployment accuracy.

### Marbled Cat

Correct wording:

- future Asian conservation application scenario;
- future readiness checklist;
- would require authorized known-ID data;
- not validated in current study.

Incorrect wording:

- Marbled Cat validation;
- Marbled Cat Re-ID performance;
- Marbled Cat identity prediction;
- Marbled Cat population estimate.

### Re-ID Model

Correct wording:

- Re-ID embeddings are used as an auxiliary measurement signal.
- Re-ID is a measurement tool in this project.
- The project evaluates image entry policy before Re-ID review.

Incorrect wording:

- The project builds a new Re-ID model.
- The model identifies individuals.
- The model is state-of-the-art.

## Evidence Level Labels

Every result must be labeled as one of the following:

### Level 1: Quantitative Validation

Supported only by known-ID CzechLynx analysis.

Examples:

- same/different similarity separation;
- AUC;
- retained same-pair coverage;
- pairwise false-match risk proxy.

### Level 2: Field Stress Test

Supported by UWIN/WildTrax field images.

Examples:

- readiness distribution;
- blur/occlusion/night IR frequency;
- failure-mode examples;
- evidence that real field images are often species-level usable but not identity-ready.

### Level 3: Future Application

Supported by literature and conceptual transfer only.

Examples:

- Marbled Cat future readiness checklist;
- required future data conditions;
- conservation application logic.

## Risk Audit

| Vulnerability | Why It Matters | Repair | Pass Standard | Allowed Claim After Repair | Still Not Allowed |
|---|---|---|---|---|---|
| The project looks like simple manual filtering | Reviewers may say blurry images are obviously bad | Link triage labels to Re-ID same/different separation and risk–coverage metrics | At least one quantitative CzechLynx analysis connects readiness to Re-ID behavior | Review-readiness can be quantitatively evaluated | We invented image filtering |
| Review-ready labels are subjective | Weak reproducibility | Use observable fields: blur, occlusion, visible side, visible region, pattern visibility, metadata completeness | Small second-review subset shows acceptable consistency | Rubric-based readiness is operationally defined | Human triage is automatically correct |
| False-match risk is overclaimed | Without full deployment ground truth, real-world error rate cannot be measured | Always use pairwise false-match risk proxy under known-ID validation | All outputs use proxy wording | Filtering affected pairwise proxy risk in CzechLynx | Real-world false-match rate was measured |
| CzechLynx becomes the whole project | The project may look like single-species Eurasian lynx Re-ID | Describe CzechLynx as validation carrier | Title, abstract, and data roles stay felid workflow-oriented | CzechLynx validates the method under known-ID conditions | This is a universal felid result |
| WildTrax is misused | No verified IDs means no strict identity validation | Use WildTrax only for field triage distribution and failure modes | No WildTrax output reports identity accuracy | WildTrax shows field readiness challenges | WildTrax identities were recognized |
| Marbled Cat becomes speculative | No current known-ID Marbled Cat dataset | Keep it as future application only | Future note says not validated | Marbled Cat is a future application case | Marbled Cat Re-ID was validated |
| Threshold transfer is overstated | Different species and camera systems may behave differently | Treat thresholds as dataset-specific | Every threshold has dataset-specific wording | CzechLynx operating point is reported | Universal threshold exists |
| Negative results weaken the project | The rubric may not predict Re-ID reliability | Treat negative results as evidence that readiness criteria need refinement | Q1/Q2 can be answered even with negative results | Visual readiness alone may be insufficient | The gate works if data do not support it |

## Phase 0 Pass Standard

This document is accepted only if:

- every allowed claim has a support path;
- every forbidden claim is explicitly listed;
- false-match risk wording is conservative;
- WildTrax and Marbled Cat are protected from overclaiming;
- negative results remain scientifically interpretable.