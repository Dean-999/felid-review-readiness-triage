# Phase 0 Decision Log

## Purpose

This document records why the project was narrowed from a broad ReID-Audit concept to the current review-readiness triage study.

The goal is to show that the final project direction is intentional, defensible, and scientifically bounded.

## Original Project Direction

The original project direction was a broader ReID-Audit concept.

It considered a general open-set, human-in-the-loop animal Re-ID audit workflow. The earlier framing could have included:

- broad animal Re-ID;
- open-set candidate review;
- human-in-the-loop audit;
- possible review interface or website;
- possible RUDI-style module;
- multi-species generalization;
- use of Re-ID as a larger system component.

This direction was scientifically interesting, but too broad for the current stage.

## Problems With the Original Direction

### Problem 1: Overlap With Mature Re-ID Work

Animal Re-ID already has strong datasets, benchmarks, toolkits, and models.

Relevant existing work includes:

- WildlifeDatasets;
- WildlifeTools;
- MegaDescriptor;
- WildlifeReID-10k;
- WildFusion;
- CzechLynx;
- SeaTurtleID2022;
- AnimalCLEF.

A broad Re-ID system would risk looking like a reproduction of existing work rather than a focused contribution.

### Problem 2: High Overclaim Risk

A broad Re-ID workflow could easily create unsupported claims, such as:

- identifying true individuals in uncontrolled field data;
- estimating population size;
- generalizing across species;
- replacing expert review;
- producing universal thresholds.

These claims are not supported by the current data access situation.

### Problem 3: WildTrax Does Not Provide Verified Individual IDs

UWIN/WildTrax field images are valuable, but without verified individual IDs they cannot support strict identity validation.

They are appropriate for field motivation, triage distribution, and failure-mode analysis, but not for Re-ID accuracy claims.

### Problem 4: Marbled Cat Has No Current Known-ID Dataset

Marbled Cat is conservation-relevant, especially for Asian forest felid monitoring, but the current project does not have authorized known-ID Marbled Cat camera-trap data.

It must remain a future application scenario.

### Problem 5: Website or Full Workflow Would Distract From the Research Question

A full review website or user interface could be useful later, but it is not necessary for proving the scientific claim.

The current project should first validate whether review-readiness has measurable Re-ID significance.

## Final Narrowing Decision

The project is narrowed to:

Review-Readiness Triage for Felid Re-ID in Conservation Camera-Trap Images

The final project asks:

Before a felid camera-trap image enters individual-level Re-ID review, is it reliable enough to enter that process?

## What Was Retained

The final project retains:

- Re-ID as a technical measurement tool;
- known-ID validation using CzechLynx;
- field motivation from UWIN/WildTrax;
- open-set caution;
- uncertainty awareness;
- conservation relevance;
- Marbled Cat as a future Asian application case.

## What Was Removed

The final project removes or postpones:

- new Re-ID model development;
- SOTA model claims;
- broad all-animal Re-ID;
- true identity prediction in WildTrax;
- population size estimation;
- universal threshold claims;
- full human review website;
- RUDI module;
- Marbled Cat validation;
- general deployment claims.

## Final Core Questions

### Q1 Reliability

Do images labeled as review-ready show more reliable Re-ID behavior than review-limited or unidentifiable images?

### Q2 Trade-off

After filtering low-readiness images, does pairwise false-match risk proxy decrease, and how much potential known matching evidence is lost?

## Final Data Role Decisions

### Decision 1: CzechLynx

CzechLynx will be used as the quantitative known-ID validation carrier.

Reason:

It provides verified individual IDs and allows construction of same-individual and different-individual pairs.

### Decision 2: UWIN/WildTrax

UWIN/WildTrax will be used as field motivation and field-readiness stress test.

Reason:

The user has UWIN-Atlanta tagging experience and access to field images, but no verified individual IDs.

### Decision 3: Marbled Cat

Marbled Cat will be used only as a future Asian conservation application scenario.

Reason:

It is conservation-relevant, but no current authorized known-ID validation dataset is available.

## Final Claim Boundary Decisions

The project will use the following wording rules:

- Re-ID is a measurement tool, not the final contribution.
- False-match risk must be written as pairwise false-match risk proxy under known-ID validation.
- CzechLynx is a validation carrier, not the whole project.
- WildTrax is field motivation and stress test only.
- Marbled Cat is future application only.
- Candidate evidence is not true identity.

## Mentor Target

The immediate mentor-facing audience is Lukas Picek.

This matters because the mentor’s research area already includes animal Re-ID, WildlifeDatasets, CzechLynx, and biodiversity-focused computer vision. Therefore, the project must not appear to claim novelty in areas that are already mature in his field.

The project should instead be framed as a careful workflow-reliability question:

Given that animal Re-ID tools are already strong, how should conservation workflows decide which field images are reliable enough to enter individual-level Re-ID review?

## Why This Direction Is Stronger

The narrowed direction is stronger because:

1. It avoids duplicating mature Re-ID work.
2. It uses CzechLynx for a measurable known-ID validation problem.
3. It uses UWIN/WildTrax honestly as field motivation.
4. It keeps Marbled Cat as a future application instead of overclaiming.
5. It creates interpretable positive or negative results.
6. It is feasible for a student project.
7. It is relevant to professor/mentor review.
8. It could later become a paper-style methods or workflow note.

## Confidence Audit

### Initial Confidence

Not 100%.

The original broad ReID-Audit direction had several vulnerabilities:

- too broad;
- too close to existing Re-ID work;
- high risk of overclaim;
- unclear data support;
- potential confusion between candidate evidence and true identity;
- too much engineering relative to the research question.

### Repairs Applied

The project was narrowed by:

- keeping only Q1 and Q2;
- using CzechLynx only for known-ID validation;
- using WildTrax only for field motivation and stress testing;
- keeping Marbled Cat only as future application;
- removing website/RUDI/full workflow claims;
- using Re-ID as a measurement tool;
- using conservative false-match risk wording;
- allowing negative results to remain meaningful.

### Final Confidence

After repair, the project has high defensible confidence.

This does not mean the result will necessarily be positive. It means the project remains scientifically valid under both positive and negative outcomes.

If review-ready images show better Re-ID separation, the gate is supported.

If they do not, the project shows that visual readiness alone is insufficient and stronger criteria are required.

## Phase 0 Completion Criteria

Phase 0 is complete when the following files are finalized:

- project_scope.md
- research_questions.md
- data_roles.md
- claims_and_boundaries.md
- evidence_chain.md
- phase0_decision_log.md

Each file must satisfy the following:

- no claim of a new Re-ID model;
- no identity claim on WildTrax;
- no current Marbled Cat validation;
- no population estimation;
- no universal threshold;
- CzechLynx used only as validation carrier;
- Re-ID used only as measurement signal;
- Q1 and Q2 remain the only core questions.

## Next Phase

After Phase 0, the project moves to Phase 1:

Data Access and Triage Rubric

Phase 1 outputs:

- triage_rubric.md
- czechlynx_data_access_notes.md
- czechlynx_sampling_plan.md
- wildtrax_field_triage_plan.md
- marbled_cat_application_readiness_note.md
- phase1_go_no_go_criteria.md

No model code, embedding extraction, or website work should begin before Phase 1 is complete.