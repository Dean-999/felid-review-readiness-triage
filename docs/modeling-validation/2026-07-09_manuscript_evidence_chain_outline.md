# Manuscript Evidence-Chain Outline

Date: 2026-07-09

Status: `STORY_HARDENING_ISSUE1_COMPLETE`

Parent issue pack:

```text
docs/project-governance/executable-plans/plans/2026-07-09-story-hardening-issue-pack.md
```

Figure 1 concept outputs:

```text
archive/pferi_v1/outputs/modeling-validation/story-hardening-issue1/figure1_pair_level_evidence_admission_chain.svg
archive/pferi_v1/outputs/modeling-validation/story-hardening-issue1/figure1_pair_level_evidence_admission_chain.pdf
archive/pferi_v1/outputs/modeling-validation/story-hardening-issue1/figure1_pair_level_evidence_admission_chain.png
```

## Purpose

This document completes Issue 1 of the story hardening issue pack. It gives the
manuscript-facing opening logic and Figure 1 concept for the project. The goal
is to make the field need visible before any model result appears: photographic
wildlife Re-ID is an evidence chain, and candidate retrieval is only one step in
that chain.

The binding sentence is:

```text
Similarity is not admissibility.
```

## Manuscript Title Direction

The title should name the scientific object rather than the implementation
stack. A strong working title is:

```text
Similarity Is Not Admissibility: Pair-Level Evidence Admission for Wildlife
Re-Identification Candidate Review
```

This title is deliberately not a descriptor title, not a Bobcat identity title,
and not a generic uncertainty-model title. It tells the reader that the paper is
about the evidential status of retrieved candidate pairs.

## Opening Thesis

Photographic wildlife re-identification workflows convert images into
individual-level evidence. In that process, a descriptor-retrieved candidate
pair is not merely a ranked database item. It is a potential unit of evidence
that may be inspected by experts, entered into individual encounter histories,
and used downstream in ecological inference. Because downstream inference can be
sensitive to individual-identification errors, the evidential status of a
candidate pair matters before any final identity decision is made.

Modern descriptors and matching platforms are essential because they make large
image archives searchable. They can answer which candidate images look visually
similar to a query image, and they can reduce the burden of exhaustive manual
comparison. However, visual similarity is not the same as evidential
admissibility. A pair can receive a high descriptor score while lacking
comparable flank views, sufficient visible pattern, overlapping body regions, or
reliable weakest-image evidence. Conversely, the reason to defer a pair may be
not that the descriptor failed, but that the pair does not contain enough
comparable evidence to support trustworthy individual-level review.

PF-ERI addresses this missing post-retrieval step. It formalizes pair-level
evidence admission for descriptor-retrieved wildlife Re-ID candidate pairs. The
method asks whether a candidate pair contains enough comparable, reviewable, and
trustworthy visual evidence to enter an individual-level evidence chain. This
framing preserves the value of strong descriptors while separating their
retrieval function from the downstream decision that a pair is admissible for
expert review or cautious ecological use.

## Introduction Outline In Prose

The introduction should begin from the ecological measurement problem, not from
the algorithm. The first paragraph should establish that individual photographic
identification is often used as a measurement step in wildlife ecology and
conservation. The paragraph should explain that when images are used to support
individual histories, mark-recapture reasoning, abundance estimation, or
longitudinal monitoring, the trustworthiness of image-based individual evidence
becomes part of the scientific measurement system. This opening should make
clear that the problem is not only computational ranking; it is the admission of
visual evidence into an ecological evidence chain.

The second paragraph should narrow from ecological inference to the known
failure modes of photographic evidence. Camera-trap and field photographs vary
in blur, illumination, occlusion, viewpoint, visible body region, and pattern
visibility. Some images may be species-identifiable but not useful for
individual comparison. Some candidate pairs may appear similar while lacking the
shared visual evidence needed for a responsible individual-level judgment. This
paragraph should introduce unclassifiable photographs, observer disagreement,
and individual-identification error as field-recognized problems rather than as
model-specific inconveniences.

The third paragraph should introduce strong descriptor retrieval as a necessary
but incomplete solution. Descriptor systems, matching platforms, and
human-in-the-loop candidate queues make large image archives operationally
searchable. They answer which images are close in representation space or
visually plausible enough to inspect. The paragraph should then draw the central
distinction: a candidate score says that a pair is worth considering, whereas
evidence admission asks whether the pair is fit to support individual-level
review. This is the first place where the sentence `Similarity is not
admissibility` should appear in the manuscript.

The fourth paragraph should state the gap. Current workflows often treat
pair-level evidence admission as an implicit expert-review judgment or as a
side effect of image quality filtering, descriptor ranking, or downstream
confirmation. That leaves a missing operational layer between candidate
retrieval and ecological use. The missing layer is not another descriptor and
not an automatic identity assignment model. It is a pair-level governance step:
whether the retrieved pair contains admissible individual-level evidence, should
be reviewed cautiously, should be deferred because evidence is weak, or should
be marked non-comparable.

The final introduction paragraph should introduce PF-ERI as the paper's answer
to that gap. The paragraph should define PF-ERI as a post-retrieval pair-level
evidence admission layer and preview the evidence path of the paper. The study
uses strong descriptor candidate queues, CzechLynx known-ID reviewed pairs,
pair-level PF-ERI evidence features, blind reliability-supported reviewability
labels, and empirical risk-aware routing to test whether pair-level
admissibility is distinct from descriptor similarity and image quality. Bobcat
wild and urban data should be introduced only as unlabeled transfer-stress and
workflow-allocation contexts, not as identity-validation data.

## Figure 1 Concept

Figure 1 should be the conceptual anchor for the entire paper. It should appear
before model results and should teach the reader how to interpret every later
analysis. The figure should show that image archives first pass through strong
descriptor retrieval, producing a candidate pair queue. PF-ERI then operates on
the pair, not on a single image and not as a new embedding. It evaluates whether
the pair has enough comparable visual evidence to be admitted to expert review,
routed for conflict review, deferred as low evidence, or marked
non-comparable. Only after that route decision should candidate pairs enter
expert review and cautious ecological inference.

Panel A should show the full evidence chain:

```text
image archive
-> strong descriptor retrieval
-> candidate pair queue
-> PF-ERI pair-level evidence admission
-> expert review
-> cautious ecological inference
```

Panel B should show the conceptual separation between descriptor similarity and
pair-level evidence admissibility. Descriptor score provides similarity context:
which candidates look similar. PF-ERI uses pair-level evidence signals such as
visible pattern, viewpoint comparability, body-region overlap, weakest-image
evidence, and descriptor-evidence conflict to decide whether the pair should be
accepted, reviewed cautiously, deferred, or marked non-comparable.

The figure should use a colorblind-safe palette, vector output, and minimal text
so that it remains readable at journal column width. The current generated
version is a manuscript concept figure, not a final journal submission figure.
It is intentionally schematic and does not report model performance.

## Draft Figure Caption

Figure 1. PF-ERI formalizes pair-level evidence admission after strong
descriptor retrieval. Strong descriptors and matching platforms make wildlife
image archives searchable by returning visually similar candidate pairs. That
retrieval step is necessary, but it does not establish whether a pair contains
comparable visual evidence for trustworthy individual-level review. PF-ERI
operates after retrieval and evaluates the evidential admissibility of each
candidate pair using pair-level evidence conditions, weakest-image evidence,
visual comparability, and descriptor-evidence conflict. The resulting route can
admit a pair for review, send it to conflict review, defer it as low evidence,
or mark it as non-comparable before any downstream ecological use. The figure is
conceptual and does not imply automatic identity assignment, descriptor
replacement, or Bobcat identity validation.

## Required Claim Boundary

This outline supports the following claim:

```text
PF-ERI is a post-retrieval pair-level evidence admission layer for
descriptor-retrieved wildlife Re-ID candidate pairs.
```

It does not support the following claims:

```text
PF-ERI is a new descriptor.
PF-ERI automatically identifies individuals.
PF-ERI validates Bobcat identity accuracy.
PF-ERI replaces expert review.
PF-ERI proves distribution-free cross-domain risk control.
```

## Issue 1 Acceptance Check

The introduction outline follows the required chain from misidentification and
unclassifiable evidence to descriptor candidate retrieval, missing pair-level
evidence admission, PF-ERI, and cautious ecological inference. The Figure 1
concept includes image archive, descriptor retrieval, candidate pair queue,
PF-ERI evidence admission, expert review, and cautious ecological inference.
The outline explicitly explains why PF-ERI remains necessary even if future
descriptors improve. It does not frame the project as catching descriptor
failures. The artifact is linked from the modeling-validation README and the
current project map.
