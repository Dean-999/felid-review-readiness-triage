# Pair-Level Evidence Admission Review

Date: 2026-07-09

Status: `POSITIONING_REVIEW_FOR_MAIN_CLAIM`

## One-Sentence Position

```text
Similarity is not admissibility.
```

PF-ERI should be framed as a pair-level evidence admission layer for
descriptor-retrieved wildlife Re-ID candidate pairs before individual-level
ecological inference. It is not a stronger descriptor, not an identity
classifier, and not a generic uncertainty wrapper around someone else's model.

The project exists because photographic wildlife Re-ID has a step that is often
implicit: before a candidate match can support individual-level review, mark
recapture, abundance estimation, or conservation interpretation, the pair must
be admissible evidence. A visually similar pair is not necessarily a comparable
pair. A high descriptor score is not automatically a trustworthy evidential
comparison.

## Why This Is Not Just Criticizing Other Models

The weak version of this project would be:

```text
Strong descriptors make mistakes, so PF-ERI finds some of those mistakes.
```

That version is vulnerable. A reviewer could respond that stronger descriptors,
pose alignment, metadata priors, active learning, or expert review can reduce
those errors.

The stronger version is:

```text
Every photographic Re-ID workflow that uses candidate pairs for individual-level
evidence needs an evidence admission step. PF-ERI formalizes that step.
```

Under this framing, PF-ERI is not competing with MegaDescriptor, DINOv2,
Wildbook/WBIA, Spotted, or future Re-ID systems. Those systems generate,
improve, rank, constrain, or present candidate matches. PF-ERI asks a downstream
evidence question:

```text
Does this descriptor-retrieved pair contain enough comparable, reviewable, and
trustworthy visual evidence to enter an individual-level evidence chain?
```

That question remains necessary even if the candidate generator improves.

## Field Need

### Identification Errors Affect Ecological Inference

Camera-trap and photographic individual identification errors are not just
benchmark errors. They can propagate into abundance and demographic estimates.
A snow leopard camera-trap study reported that individual identification from
camera-trap photos may be less reliable than commonly assumed and that
misidentification can lead to systematic population overestimation.

That gives PF-ERI a conservation-science rationale:

```text
The cost of admitting a weak pair is not only a wrong candidate list. It can
pollute the individual evidence chain used by downstream inference.
```

The same logic appears in capture-recapture misidentification work: if one
animal is split into multiple apparent identities, population size can be
overestimated. PF-ERI is not a mark-recapture model, but it targets an upstream
evidence failure that those models are sensitive to.

### Best-Practice Literature Already Calls For Error Checking

A best-practice review for camera-trap individual identification argues that
researchers need rigorous methods for checking errors, handling unclassifiable
photographs, and resolving inter-observer discrepancies. It also reports that
many studies do not adequately describe how they avoid individual
misidentification or provide evidence that individuals can be reliably
differentiated.

This is the clearest field-level opening for PF-ERI:

```text
The field already knows that unclassifiable photographs, observer disagreement,
and individual misidentification matter. PF-ERI moves this concern from a
study-level reporting recommendation to a pair-level operational layer.
```

### Observer Variation Is A Real Measurement Problem

Camera-trap image processing is not perfectly objective. Inter-observer studies
report differences in processing rates, detected mammals, species
misidentifications, and extracted wildlife information. For PF-ERI, this means
human reviewability labels cannot be treated casually. Blind review, reviewer
agreement, disagreement appendices, and future latent-label sensitivity are not
decorations. They protect the construct validity of the pair-level evidence
admission target.

### Existing Platforms Present Candidate Matches, But Do Not Fully Solve
Evidence Admission

Wildbook/WBIA-style systems are important because they make candidate matching
usable at scale. Their workflows perform detection, feature extraction,
matching, and candidate display, often with algorithm-specific match scores and
human review.

That does not make PF-ERI redundant. It gives PF-ERI its interface:

```text
candidate match score
-> pair-level evidence admission
-> expert confirmation or defer/non-comparable route
```

The missing distinction is:

```text
candidate match score says this pair is worth considering;
evidence admission says whether this pair is fit to support individual-level
review.
```

### New Human-In-The-Loop Re-ID Work Reinforces The Need

Recent animal Re-ID work continues to emphasize that camera-trap Re-ID is hard
under low image quality, viewpoint variation, illumination shifts, and imbalanced
individual observations. Location-informed and active-learning systems can
reduce expert-review burden by improving which pairs are queried or how visual
similarity is constrained.

PF-ERI should not claim that those systems are wrong. The better claim is that
they strengthen the same thesis:

```text
wildlife Re-ID remains a human-in-the-loop evidence workflow, and pair-level
admissibility should be explicit.
```

## The Better Research Gap

The old gap:

```text
Strong descriptors can make false or uncertain matches.
```

The improved gap:

```text
Wildlife Re-ID lacks an explicit pair-level evidence admission layer between
candidate retrieval and individual-level ecological inference.
```

This gap is not solved by a stronger descriptor alone because:

- descriptors optimize visual similarity or representation geometry, not
  admissibility of evidence;
- pair comparability depends on the relationship between two images, not only
  each image separately;
- high visual similarity can coexist with weak comparable evidence;
- downstream ecological inference needs auditable evidence, not only an
  embedding score;
- expert review needs route decisions: accept, conflict review, defer, or
  non-comparable.

## PF-ERI's Proper Scientific Object

PF-ERI should be defined around this object:

```text
candidate pair p = (query image, candidate image)
```

The claim-bearing target is:

```text
pair-level evidential admissibility
```

A pair is admissible when it has enough comparable evidence for individual-level
review. A pair can be inadmissible even if:

- the two images look superficially similar;
- a descriptor ranks the candidate highly;
- each single image passes a basic quality threshold;
- a reviewer could still make a speculative judgment.

The route space is part of the contribution:

```text
accept_review_ready
conflict_review
defer_low_evidence
non_comparable
```

These are not arbitrary labels. They are evidence-governance states.

## The Main Innovation Claims

### Claim 1: Pair-Level Evidential Admissibility Is A Distinct Target

Allowed wording:

```text
PF-ERI introduces pair-level evidential admissibility as a post-retrieval target
for wildlife Re-ID candidate review.
```

Why this is defensible:

- the target is not identity assignment;
- the target is not descriptor similarity;
- the target is not single-image quality;
- the target corresponds to a real evidence question in photographic individual
  identification.

Required support:

- a formal definition of admissibility;
- reviewed labels for review-ready vs not-ready/uncertain;
- descriptor-only and quality-only controls;
- claim boundaries blocking identity-performance overreach.

### Claim 2: Descriptor-Evidence Conflict Is A Real Failure Mode

Allowed wording:

```text
PF-ERI identifies descriptor-evidence conflict: high descriptor similarity under
weak pair-level evidence should be routed as review risk rather than accepted as
confidence.
```

Why this is more than "finding errors":

The point is not that descriptors fail sometimes. The point is that descriptor
confidence and evidential admissibility are different axes. A pair can be high
similarity and still weak evidence.

Required support:

- high-similarity subset analysis;
- high-similarity / low-admissibility conflict groups;
- not-ready or uncertain enrichment in conflict groups;
- descriptor-family controls for MegaDescriptor and DINOv2.

### Claim 3: Abstention Is Evidence Governance, Not Model Failure

Allowed wording:

```text
PF-ERI treats defer and non-comparable routes as valid scientific outputs when
candidate pairs lack sufficient evidence for individual-level review.
```

Why this matters:

In ecological evidence workflows, forcing an identity-level comparison on a
non-comparable pair is not a neutral act. It can create false confidence and
contaminate downstream records.

Required support:

- route-level not-ready/uncertain rates;
- enrichment of low-evidence labels in defer/non-comparable groups;
- retained review-ready coverage in accepted groups;
- review-budget results showing reduced low-value burden without hiding the
  claim boundary.

### Claim 4: PF-ERI Supports Evidence Hygiene Before Ecological Inference

Allowed wording:

```text
PF-ERI provides an evidence hygiene layer before descriptor-retrieved candidate
pairs enter individual-level review or downstream ecological inference.
```

This is the broader contribution. It connects the algorithmic layer to the
field need: individual identification errors, unclassifiable photographs, and
observer disagreement are already recognized as threats to photographic wildlife
studies.

Required support:

- literature positioning showing that misidentification and unclassifiable
  photos matter;
- CzechLynx known-ID reviewed validation;
- blind reviewer reliability;
- strict blocked claims for Bobcat identity metrics and universal guarantees.

## What PF-ERI Should Not Claim

PF-ERI should not claim:

- automatic identity assignment;
- Bobcat identity accuracy;
- Bobcat false-match accuracy;
- top-k/mAP improvement as the main endpoint;
- replacement of MegaDescriptor, DINOv2, Wildbook/WBIA, or future Re-ID
  descriptors;
- universal threshold across species, sites, or camera systems;
- distribution-free guarantee across Bobcat/domain shift without the required
  calibration design.

These blocked claims are not weaknesses. They prevent the project from becoming
another overextended Re-ID method paper.

## How To Avoid The "Picks On Other Work" Trap

Bad framing:

```text
Existing Re-ID systems are flawed, and PF-ERI catches their failures.
```

Better framing:

```text
Existing Re-ID systems generate candidate matches. PF-ERI governs whether those
candidate pairs have admissible evidence for individual-level review.
```

Best framing:

```text
Photographic wildlife Re-ID is an evidence chain. Candidate retrieval is one
step; pair-level evidence admission is another. PF-ERI formalizes the second
step.
```

This converts PF-ERI from a critique into an interface layer.

## Competitive Positioning

| Nearby line of work | What it does | Why PF-ERI is different |
| --- | --- | --- |
| Strong descriptors / benchmarks | Improve embedding and retrieval accuracy. | PF-ERI evaluates admissibility after retrieval. |
| Wildbook/WBIA-style platforms | Detect, match, score, and present candidate matches. | PF-ERI adds pair-level evidence admission before review/use. |
| Spatio-temporal or location-informed Re-ID | Constrain candidate matches with ecological feasibility metadata. | PF-ERI evaluates visual evidence comparability and admissibility. |
| Active learning for Re-ID | Select informative pairs to reduce annotation burden or improve models. | PF-ERI routes evidence-qualified, conflict, deferred, and non-comparable pairs. |
| Generic reject option / selective classification | Abstain from uncertain predictions. | PF-ERI treats abstention as evidence governance, not generic low-confidence rejection. |
| Multi-annotator models | Estimate latent labels and reviewer reliability. | PF-ERI uses them to validate reviewability labels, not as the primary contribution. |

## Claim Hardening Plan

### Hardening 1: Literature-Backed Necessity

Add an introduction section built around:

```text
misidentification -> unclassifiable evidence -> observer disagreement ->
candidate review burden -> need for pair-level admission.
```

This prevents the paper from sounding like it exists only because descriptors
are imperfect.

### Hardening 2: Quality And Descriptor Controls

Keep the main controls visible:

```text
descriptor-only
quality-only
PF-ERI evidence-only
descriptor + PF-ERI
```

Do not bury these controls. They are the cleanest defense against the two main
alternative explanations:

```text
PF-ERI is just descriptor similarity.
PF-ERI is just image quality.
```

### Hardening 3: Conflict Route As Mechanism

Treat descriptor-evidence conflict as a mechanism, not a side metric. The paper
should show:

```text
high descriptor similarity + low pair evidence -> enriched review risk.
```

This is the cleanest version of "Similarity is not admissibility."

### Hardening 4: Blind Reviewability As Measurement Validity

Use blind reliability-supported labels as a construct-validity argument:

```text
reviewability/admissibility is measurable with acceptable reviewer reliability.
```

Future multi-annotator latent-label analysis should be presented as a
sensitivity analysis, not a new core model.

### Hardening 5: Bobcat As Transfer-Stress, Not Identity Validation

Keep Bobcat in the story because it gives ecological realism and same-genus
field stress. Do not use it for identity claims unless audited identity or
same/different labels are added later.

## Stronger Final Thesis

The strongest thesis is:

```text
Similarity is not admissibility. PF-ERI formalizes pair-level evidence admission
for descriptor-retrieved wildlife Re-ID candidate pairs, separating visual
similarity from the evidential conditions needed for trustworthy individual-level
review before ecological inference.
```

This thesis makes the project necessary even in a world with stronger
descriptors. Better candidate generation does not remove the need to decide
whether a pair is admissible evidence.

## Sources

- Johansson et al. 2020. "Identification errors in camera-trap studies result
  in systematic population overestimation." Scientific Reports.
  https://www.nature.com/articles/s41598-020-63367-z
- Clavel et al. 2020. "Best practices for reporting individual identification
  using camera trap photographs." Global Ecology and Conservation.
  https://www.sciencedirect.com/science/article/pii/S2351989420308350
- Mitterwallner et al. 2022. "Inter-observer variance and agreement of wildlife
  information extracted from camera trap images." Biodiversity and Conservation.
  https://link.springer.com/article/10.1007/s10531-022-02472-z
- Wildbook Docs. "Image Analysis Pipeline."
  https://wildbook.docs.wildme.org/introduction/image-analysis-pipeline.html
- Wildbook Docs. "Matching Process."
  https://wildbook.docs.wildme.org/data/matching-process.html
- Kelebek et al. 2026. "Spotted: Location-informed Reidentification of Hyenas
  and Leopards in Camera Trap Surveys." arXiv.
  https://arxiv.org/abs/2607.00804
- Link et al. 2009. "Modeling misidentification errors in capture-recapture
  studies." Biometrics.
  https://pubmed.ncbi.nlm.nih.gov/19294906/
