# Evidence Chain

## Purpose

This document explains the logic connecting the field problem, the technical gap, the validation dataset, and the conservation relevance of the project.

The evidence chain follows this order:

1. Field problem
2. Existing Re-ID maturity
3. Pre-Re-ID readiness gap
4. Known-ID validation
5. Risk–coverage trade-off
6. Conservation reliability
7. Future Asian felid application

## Evidence Chain Overview

The project begins from a real field workflow problem:

Many camera-trap images are species-identifiable but not necessarily reliable for individual-level Re-ID review.

Animal Re-ID methods are already mature, so the project does not claim to invent Re-ID. Instead, it asks an earlier workflow question:

Should an image be allowed into individual-level Re-ID review at all?

This question can be tested using CzechLynx known-ID data, because verified identities allow same-individual and different-individual pair construction. UWIN/WildTrax field images motivate the problem and stress-test the rubric under real camera-trap conditions. Marbled Cat is included only as a future Asian conservation application scenario.

## Step 1: Field Problem

### Claim

Real camera-trap workflows produce many images that are useful for species-level tagging but not clearly reliable for individual-level evidence.

### Basis

In UWIN-Atlanta tagging work, images may contain recognizable animals such as Bobcat, Canada Lynx, Coyote, Fox, Deer, Raccoon, Opossum, Domestic Cat, or Domestic Dog. However, species-level recognition often relies on general body shape, tail length, size, posture, or context. Individual-level Re-ID requires stronger evidence: visible diagnostic pattern, comparable side or region, sufficient sharpness, limited occlusion, and stable viewpoint.

### Project Implication

The project should not assume that every species-level detection is identity-ready.

## Step 2: Existing Re-ID Maturity

### Claim

Animal Re-ID is already a mature and active field.

### Basis

Existing work includes:

- WildlifeDatasets;
- MegaDescriptor;
- WildlifeReID-10k;
- WildFusion;
- CzechLynx;
- SeaTurtleID2022;
- AnimalCLEF and related challenges.

These tools and datasets already address model training, feature extraction, similarity calculation, image retrieval, open-set evaluation, time-aware evaluation, and benchmark construction.

### Project Implication

The project must not claim novelty in Re-ID modeling.

The contribution must be shifted to review-readiness gate validation.

## Step 3: Pre-Re-ID Readiness Gap

### Claim

Before Re-ID review, camera-trap images may need a quality and comparability gate.

### Basis

Related camera-trap Re-ID work shows that many wild images are not usable for individual identification due to poor imaging conditions, occlusion, viewpoint problems, and burst similarity. Some pipelines therefore include detection, species filtering, viewpoint estimation, quality evaluation, and temporal subsampling before Re-ID curation.

### Project Implication

A review-readiness gate is not arbitrary. It is aligned with realistic camera-trap Re-ID workflows.

## Step 4: Known-ID Validation

### Claim

To test whether review-readiness is technically meaningful, the project needs known individual IDs.

### Basis

CzechLynx provides camera-trap images with identity labels, segmentation masks, skeleton annotations, metadata, and realistic evaluation structures.

### Project Implication

CzechLynx can be used to test whether review-ready images produce stronger same-individual versus different-individual similarity separation.

## Step 5: Risk–Coverage Trade-off

### Claim

Filtering low-readiness images may reduce unsafe matches but may also discard useful matching evidence.

### Basis

If all images enter Re-ID review, coverage is high but false-match risk may increase. If only review-ready images enter, risk may decrease but same-individual evidence may be lost.

### Project Implication

The project should compare entry policies:

- no filter;
- balanced filter;
- strict filter.

The project should report both safety gain and evidence loss.

## Step 6: Conservation Reliability

### Claim

Individual misidentification can affect conservation inference.

### Basis

Camera-trap photo-identification errors can affect abundance, recapture, and movement interpretation. This makes false-match risk a conservation reliability issue rather than only a model metric.

### Project Implication

The project should frame review-readiness as a safeguard against unreliable identity evidence entering downstream monitoring interpretation.

## Step 7: Future Asian Felid Application

### Claim

The same readiness logic could guide future Asian felid monitoring, but only after species-specific data audit and calibration.

### Basis

Marbled Cat is a forest-dependent Asian felid with conservation concern and limited knowledge of status and distribution. Camera-trap monitoring is relevant, but current project validation does not include authorized known-ID Marbled Cat data.

### Project Implication

Marbled Cat belongs in Discussion or Future Application only.

## Final Evidence Chain

The final project logic is:

1. UWIN-Atlanta tagging work shows that field images can be species-level usable but identity-level uncertain.
2. Animal Re-ID is already mature, so the project should not duplicate Re-ID modeling.
3. Existing camera-trap Re-ID workflows show that quality, viewpoint, and comparability filtering can be necessary before identification.
4. CzechLynx provides the known-ID validation needed to test whether review-ready images have stronger Re-ID reliability.
5. Filtering creates a measurable risk–coverage trade-off.
6. Reducing unsafe identity evidence matters because misidentification can affect conservation inference.
7. Marbled Cat provides a future Asian conservation application case, but not current validation.

## Project Narrative

The project narrative should be:

Field workflow problem → AI reliability gap → conservation-safe validation.

Expanded version:

Through UWIN-Atlanta camera-trap tagging, I observed that many images are suitable for species-level tagging but not necessarily reliable for individual-level identification. Since animal Re-ID methods and benchmarks are already mature, this project does not build another Re-ID model. Instead, it studies a pre-Re-ID question: which felid camera-trap images are reliable enough to enter individual-level Re-ID review? Using CzechLynx known-ID data, the project tests whether review-ready images show stronger same-individual versus different-individual similarity separation and measures the trade-off between lower pairwise false-match risk proxy and lost matching evidence. UWIN/WildTrax images provide field motivation and triage stress testing, while Marbled Cat is included only as a future Asian conservation application scenario.

## Evidence Level for Each Claim

| Claim | Evidence Level | Source Role |
|---|---|---|
| Review-ready images may show stronger Re-ID reliability | Quantitative validation | CzechLynx |
| Filtering may reduce pairwise false-match risk proxy | Quantitative validation | CzechLynx |
| Filtering may lose same-individual matching evidence | Quantitative validation | CzechLynx |
| Field camera-trap images contain blur, occlusion, partial views, night IR, and angle problems | Field stress test | UWIN/WildTrax |
| WildTrax identities cannot be validated without verified IDs | Boundary condition | UWIN/WildTrax |
| Marbled Cat is relevant to Asian felid conservation | Future application | Literature |
| Marbled Cat Re-ID is not validated | Boundary condition | No current known-ID Marbled Cat data |

## Mentor-Facing Evidence Summary

The evidence chain is designed to avoid overclaiming. CzechLynx is used only where known-ID validation is required. UWIN/WildTrax is used only to document the field problem. Marbled Cat is used only to show future conservation relevance. Re-ID is treated as a measurement signal rather than the project’s main product.

## Phase 0 Pass Standard

This document is accepted only if:

- the project begins from a real field problem;
- existing Re-ID maturity is acknowledged;
- the project gap is clearly before Re-ID review;
- CzechLynx is the only strict validation source;
- WildTrax is not used for identity claims;
- Marbled Cat is future application only;
- the conservation relevance follows from misidentification risk.